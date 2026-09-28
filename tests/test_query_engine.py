"""Focused security, compilation, and execution tests for logical SQL."""

import json
import unittest
from contextlib import contextmanager
from datetime import date, datetime, time
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

from sqlglot import parse_one

from app.core.config import Settings
from app.query_engine import (
    MultipleSemanticViewsError,
    QueryValidationError,
    UnknownSemanticViewError,
    query_database,
)
from app.query_engine.compiler import compile_query
from app.query_engine.models import normalize_value
from app.query_engine.validator import validate_logical_sql
from app.tenant import TenantContext


class _Cursor:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows
        self.description = [("value",)]
        self.sql = ""
        self.parameters: tuple[object, ...] = ()
        self.fetch_size = 0

    def execute(self, sql: str, *parameters: object) -> None:
        self.sql = sql
        self.parameters = parameters

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        self.fetch_size = size
        return self._rows[:size]


class _Connection:
    def __init__(self, cursor: _Cursor) -> None:
        self._cursor = cursor

    def cursor(self) -> _Cursor:
        return self._cursor


class QueryEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tenant = TenantContext(
            business_id=UUID("11111111-1111-1111-1111-111111111111"),
            establishment_id=UUID("22222222-2222-2222-2222-222222222222"),
            timezone="America/Bogota",
        )
        self.settings = Settings(
            sql_server="server",
            sql_database="database",
            sql_username="user",
            sql_max_rows=2,
        )

    def test_accepts_supported_readonly_query_shapes(self) -> None:
        queries = (
            "SELECT SUM(total_facturado), COUNT(*) FROM ventas",
            "SELECT producto, SUM(cantidad) FROM venta_lineas GROUP BY producto",
            "SELECT producto FROM productos",
            "SELECT * FROM ventas WHERE fecha >= '2026-09-01'",
            "SELECT * FROM productos ORDER BY producto",
            "SELECT * FROM (SELECT * FROM ventas) AS x",
            (
                "WITH diario AS ("
                "SELECT CAST(fecha AS date) AS dia FROM ventas"
                ") SELECT * FROM diario"
            ),
            "WITH Diario AS (SELECT fecha FROM ventas) SELECT * FROM diario",
            "SELECT venta_id FROM ventas UNION ALL SELECT venta_id FROM ventas",
        )

        for query in queries:
            with self.subTest(query=query):
                self.assertIn(
                    validate_logical_sql(query).semantic_view,
                    {"ventas", "venta_lineas", "productos"},
                )

    def test_rejects_unsafe_and_unknown_sql(self) -> None:
        queries = (
            "SELECT * FROM trade.Sale",
            "SELECT * FROM catalog.Product",
            "SELECT * FROM dbo.ventas",
            "SELECT * FROM sys.tables",
            "SELECT * FROM INFORMATION_SCHEMA.TABLES",
            "SELECT * FROM otra_tabla",
            "INSERT INTO ventas VALUES (1)",
            "UPDATE ventas SET subtotal = 0",
            "DELETE FROM ventas",
            "MERGE INTO ventas USING productos ON 1 = 1 WHEN MATCHED THEN DELETE",
            "DROP TABLE ventas",
            "ALTER TABLE ventas ADD x int",
            "CREATE TABLE x (id int)",
            "TRUNCATE TABLE ventas",
            "EXEC sp_who",
            "DECLARE @x int",
            "SET NOCOUNT ON",
            "USE master",
            "SELECT * FROM ventas; SELECT * FROM ventas",
            "SELECT * INTO #x FROM ventas",
            "SELECT @x FROM ventas",
            "SELECT ? FROM ventas",
            "SELECT * FROM #ventas",
            "SELECT * FROM OPENROWSET('SQLNCLI', 'x', 'SELECT 1')",
            "SELECT * FROM OPENQUERY(server, 'SELECT 1')",
            (
                "SELECT OPENDATASOURCE('SQLNCLI', 'x').db.dbo.fn() "
                "FROM ventas"
            ),
            "SELECT dbo.fn(fecha) FROM ventas",
            "SELECT NEXT VALUE FOR dbo.sequence FROM ventas",
            "SELECT DB_NAME() FROM ventas",
            "SELECT SERVERPROPERTY('ProductVersion') FROM ventas",
            "SELECT CURRENT_USER FROM ventas",
            "SELECT OBJECT_ID('trade.Sale') FROM ventas",
            "SELECT @@VERSION FROM ventas",
        )

        for query in queries:
            with self.subTest(query=query):
                with self.assertRaises(QueryValidationError):
                    validate_logical_sql(query)

    def test_rejects_reserved_cte_shadowing(self) -> None:
        for name in ("ventas", "venta_lineas", "productos"):
            with self.subTest(name=name):
                with self.assertRaises(QueryValidationError):
                    validate_logical_sql(
                        f"WITH {name} AS (SELECT 1 AS x) SELECT * FROM {name}"
                    )

    def test_requires_one_known_semantic_view(self) -> None:
        with self.assertRaises(UnknownSemanticViewError):
            validate_logical_sql("SELECT 1")

        with self.assertRaises(MultipleSemanticViewsError):
            validate_logical_sql(
                "SELECT * FROM ventas JOIN venta_lineas ON 1 = 1"
            )

    def test_cte_names_are_allowed_only_inside_their_ast_scope(self) -> None:
        with self.assertRaises(UnknownSemanticViewError):
            validate_logical_sql(
                "SELECT * FROM local_only WHERE EXISTS ("
                "WITH local_only AS (SELECT * FROM ventas) "
                "SELECT * FROM local_only)"
            )

        with self.assertRaises(UnknownSemanticViewError):
            validate_logical_sql(
                "WITH local_name AS (SELECT * FROM ventas) "
                "SELECT * FROM physical_table AS local_name"
            )

    def test_compiler_injects_only_used_view_and_server_tenant(self) -> None:
        compiled = compile_query(
            "SELECT SUM(total_facturado) FROM ventas", self.tenant
        )

        self.assertEqual(compiled.semantic_view, "ventas")
        self.assertIn("WITH ventas AS", compiled.sql)
        self.assertIn("trade.Sale", compiled.sql)
        self.assertNotIn("trade.SaleDetail", compiled.sql)
        self.assertNotIn("catalog.Product AS p", compiled.sql)
        self.assertEqual(compiled.sql.count("?"), 2)
        self.assertNotIn(str(self.tenant.business_id), compiled.sql)
        self.assertNotIn(str(self.tenant.establishment_id), compiled.sql)
        self.assertEqual(
            compiled.parameters,
            (str(self.tenant.establishment_id), str(self.tenant.business_id)),
        )
        parse_one(compiled.sql, read="tsql")

    def test_compiler_preserves_user_ctes_after_trusted_cte(self) -> None:
        compiled = compile_query(
            "WITH diario AS (SELECT fecha FROM ventas) SELECT * FROM diario",
            self.tenant,
        )

        self.assertLess(compiled.sql.index("ventas AS"), compiled.sql.index("diario AS"))
        self.assertIn("SELECT * FROM diario", compiled.sql)

    def test_compiler_requires_server_side_tenant(self) -> None:
        with self.assertRaises(QueryValidationError):
            compile_query("SELECT * FROM ventas", None)

    def test_executor_limits_rows_and_marks_truncation(self) -> None:
        for source_rows, expected_rows, truncated in (
            ([(1,), (2,)], [[1], [2]], False),
            ([(1,), (2,), (3,)], [[1], [2]], True),
        ):
            cursor = _Cursor(source_rows)

            @contextmanager
            def fake_connection(_settings: Settings, _cursor: _Cursor = cursor):
                yield _Connection(_cursor)

            with self.subTest(source_rows=source_rows), patch(
                "app.query_engine.executor.database_connection", fake_connection
            ):
                result = query_database(
                    "SELECT producto_id AS value FROM productos",
                    self.tenant,
                    self.settings,
                )

            self.assertEqual(result.rows, expected_rows)
            self.assertEqual(result.row_count, len(expected_rows))
            self.assertEqual(result.truncated, truncated)
            self.assertEqual(cursor.fetch_size, self.settings.sql_max_rows + 1)
            self.assertEqual(cursor.parameters, compile_query(
                "SELECT producto_id AS value FROM productos", self.tenant
            ).parameters)

    def test_executor_normalizes_values_to_json_without_decimal_float(self) -> None:
        identifier = UUID("33333333-3333-3333-3333-333333333333")
        values = (
            Decimal("123.4567890123456789"),
            datetime(2026, 9, 1, 12, 30, 45),
            date(2026, 9, 1),
            time(12, 30, 45),
            identifier,
        )
        cursor = _Cursor([values])
        cursor.description = [(name,) for name in ("money", "dt", "d", "t", "id")]

        @contextmanager
        def fake_connection(_settings: Settings):
            yield _Connection(cursor)

        with patch("app.query_engine.executor.database_connection", fake_connection):
            result = query_database(
                "SELECT * FROM productos", self.tenant, self.settings
            )

        self.assertEqual(
            result.rows[0],
            [
                "123.4567890123456789",
                "2026-09-01T12:30:45",
                "2026-09-01",
                "12:30:45",
                str(identifier),
            ],
        )
        self.assertEqual(normalize_value(Decimal("0.10")), "0.10")
        json.dumps(result.model_dump())


if __name__ == "__main__":
    unittest.main()
