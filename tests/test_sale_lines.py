"""Focused tests for the ``venta_lineas`` semantic view."""

import re
import unittest
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.semantic.sale_lines import (
    SALE_LINES_VIEW_SQL,
    InvalidSaleLinesRangeError,
    InvalidTopLimitError,
    SaleLinesSummary,
    TenantRequiredError,
    sale_lines_summary,
    top_categories_by_units,
    top_products_by_units,
)
from app.tenant import TenantContext
from scripts.check_sale_lines_view import OracleSummary, _assert_matches_oracle


class _Cursor:
    def __init__(self, row: tuple[object, ...] = (0, None, None)) -> None:
        self.row = row
        self.executed = False

    def execute(self, *_args: object) -> None:
        self.executed = True

    def fetchone(self) -> tuple[object, ...]:
        return self.row

    def fetchall(self) -> list[tuple[object, ...]]:
        return []


class _Connection:
    def __init__(self, cursor: _Cursor) -> None:
        self._cursor = cursor

    def cursor(self) -> _Cursor:
        return self._cursor


class SaleLinesViewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.start = datetime(2026, 9, 1)
        self.end = datetime(2026, 9, 2)
        self.tenant = TenantContext(
            business_id=UUID("11111111-1111-1111-1111-111111111111"),
            establishment_id=UUID("22222222-2222-2222-2222-222222222222"),
            timezone="America/Bogota",
        )

    def test_empty_or_reversed_range_is_rejected_before_sql(self) -> None:
        cursor = _Cursor()
        connection = _Connection(cursor)

        for end in (self.start, datetime(2026, 8, 31)):
            with self.subTest(end=end):
                with self.assertRaises(InvalidSaleLinesRangeError):
                    sale_lines_summary(  # type: ignore[arg-type]
                        connection, self.tenant, self.start, end
                    )
        self.assertFalse(cursor.executed)

    def test_tenant_is_required_before_sql(self) -> None:
        cursor = _Cursor()
        with self.assertRaises(TenantRequiredError):
            sale_lines_summary(  # type: ignore[arg-type]
                _Connection(cursor), None, self.start, self.end
            )
        self.assertFalse(cursor.executed)

    def test_base_tenant_path_uses_sale_pos_and_establishment(self) -> None:
        self.assertRegex(
            SALE_LINES_VIEW_SQL,
            re.compile(
                r"SaleDetail AS sd.*JOIN trade\.Sale AS s.*"
                r"JOIN store\.PointOfSale AS pos.*"
                r"JOIN store\.Establishment AS e",
                re.DOTALL,
            ),
        )

    def test_product_metadata_joins_are_left_and_tenant_scoped(self) -> None:
        self.assertIn("LEFT JOIN catalog.Product AS p", SALE_LINES_VIEW_SQL)
        self.assertIn("p.EstablishmentId = e.Id", SALE_LINES_VIEW_SQL)
        self.assertIn("LEFT JOIN catalog.ProductBusiness AS pb", SALE_LINES_VIEW_SQL)
        self.assertIn("pb.BusinessId = e.BusinessId", SALE_LINES_VIEW_SQL)

    def test_definition_has_no_forbidden_sources_or_text_joins(self) -> None:
        sql = SALE_LINES_VIEW_SQL.lower()
        self.assertNotIn("dataon", sql)
        join_conditions = "\n".join(
            line.strip()
            for line in sql.splitlines()
            if line.strip().startswith(("on ", "and "))
        )
        self.assertNotIn("barcode", join_conditions)
        self.assertNotIn("name", join_conditions)
        self.assertNotIn("p.isactive", sql)
        self.assertNotIn("pb.isdeleted", sql)

    def test_oracle_detects_lost_or_duplicated_lines(self) -> None:
        summary = SaleLinesSummary(2, 4, Decimal("50.00"))
        matching = OracleSummary(2, 4, Decimal("50.00"))
        _assert_matches_oracle(summary, matching)

        for oracle in (
            OracleSummary(3, 4, Decimal("50.00")),
            OracleSummary(2, 5, Decimal("50.00")),
            OracleSummary(2, 4, Decimal("50.01")),
        ):
            with self.subTest(oracle=oracle):
                with self.assertRaises(RuntimeError):
                    _assert_matches_oracle(summary, oracle)

    def test_invalid_top_limits_are_rejected_before_sql(self) -> None:
        for query in (top_products_by_units, top_categories_by_units):
            for limit in (0, -1, 51, True, 1.5):
                cursor = _Cursor()
                with self.subTest(query=query.__name__, limit=limit):
                    with self.assertRaises(InvalidTopLimitError):
                        query(  # type: ignore[arg-type]
                            _Connection(cursor),
                            self.tenant,
                            self.start,
                            self.end,
                            limit,
                        )
                    self.assertFalse(cursor.executed)


if __name__ == "__main__":
    unittest.main()
