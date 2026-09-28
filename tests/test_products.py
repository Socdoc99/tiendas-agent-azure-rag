"""Focused tests for the ``productos`` semantic view."""

import re
import unittest
from decimal import Decimal
from uuid import UUID

from app.semantic.products import (
    PRODUCTS_VIEW_SQL,
    InvalidProductLimitError,
    InventorySummary,
    TenantRequiredError,
    inventory_summary,
    low_stock_products,
    out_of_stock_products,
    product_samples,
)
from app.tenant import TenantContext
from scripts.check_products_view import (
    ProductIdValidation,
    _assert_matches_oracle,
    _assert_unique_product_ids,
)


class _Cursor:
    def __init__(self, row: tuple[object, ...] = (0, 0, 0, 0, 0)) -> None:
        self.row = row
        self.executed = False
        self.sql = ""

    def execute(self, sql: str, *_args: object) -> None:
        self.executed = True
        self.sql = sql

    def fetchone(self) -> tuple[object, ...]:
        return self.row

    def fetchall(self) -> list[tuple[object, ...]]:
        return []


class _Connection:
    def __init__(self, cursor: _Cursor) -> None:
        self._cursor = cursor

    def cursor(self) -> _Cursor:
        return self._cursor


class ProductsViewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tenant = TenantContext(
            business_id=UUID("11111111-1111-1111-1111-111111111111"),
            establishment_id=UUID("22222222-2222-2222-2222-222222222222"),
            timezone="America/Bogota",
        )

    def test_tenant_is_required_before_sql(self) -> None:
        for query in (
            inventory_summary,
            low_stock_products,
            out_of_stock_products,
            product_samples,
        ):
            cursor = _Cursor()
            with self.subTest(query=query.__name__):
                with self.assertRaises(TenantRequiredError):
                    query(_Connection(cursor), None)  # type: ignore[arg-type]
                self.assertFalse(cursor.executed)

    def test_product_and_establishment_are_tenant_scoped(self) -> None:
        self.assertIn(
            "p.EstablishmentId = CAST(? AS uniqueidentifier)", PRODUCTS_VIEW_SQL
        )
        self.assertIn(
            "e.BusinessId = CAST(? AS uniqueidentifier)", PRODUCTS_VIEW_SQL
        )
        self.assertRegex(
            PRODUCTS_VIEW_SQL,
            re.compile(
                r"JOIN store\.Establishment AS e\s+ON e\.Id = p\.EstablishmentId",
                re.DOTALL,
            ),
        )

    def test_only_active_products_are_included(self) -> None:
        self.assertIn("p.IsActive = 1", PRODUCTS_VIEW_SQL)

    def test_product_business_is_optional_tenant_safe_and_not_deleted(self) -> None:
        self.assertIn("LEFT JOIN catalog.ProductBusiness AS pb", PRODUCTS_VIEW_SQL)
        self.assertIn("pb.Id = p.ProductBusinessId", PRODUCTS_VIEW_SQL)
        self.assertIn("pb.BusinessId = e.BusinessId", PRODUCTS_VIEW_SQL)
        self.assertIn("pb.IsDeleted = 0", PRODUCTS_VIEW_SQL)
        self.assertIn("COALESCE(p.Name, pb.Name)", PRODUCTS_VIEW_SQL)

    def test_definition_uses_current_product_values_and_no_history(self) -> None:
        sql = PRODUCTS_VIEW_SQL.lower()
        self.assertIn("p.price", sql)
        self.assertIn("p.unitcost", sql)
        self.assertIn("p.averagecost", sql)
        self.assertIn("p.stock", sql)
        self.assertNotIn("historyinventory", sql)
        self.assertNotIn("dataon", sql)

    def test_inventory_control_flag_matches_is_not_alter_inventory(self) -> None:
        self.assertRegex(
            PRODUCTS_VIEW_SQL,
            r"CASE WHEN p\.IsNotAlterInventory = 0 THEN 1 ELSE 0 END",
        )

    def test_alert_queries_encode_exhausted_negative_and_low_stock_rules(self) -> None:
        low_cursor = _Cursor()
        low_stock_products(_Connection(low_cursor), self.tenant)  # type: ignore[arg-type]
        self.assertIn("controla_inventario = 1", low_cursor.sql)
        self.assertIn("stock_actual > 0", low_cursor.sql)
        self.assertIn("stock_actual <= stock_minimo", low_cursor.sql)

        out_cursor = _Cursor()
        out_of_stock_products(_Connection(out_cursor), self.tenant)  # type: ignore[arg-type]
        self.assertIn("controla_inventario = 1", out_cursor.sql)
        self.assertIn("stock_actual <= 0", out_cursor.sql)
        self.assertIn("stock_actual < 0 THEN 0 ELSE 1", out_cursor.sql)

    def test_invalid_limits_are_rejected_before_sql(self) -> None:
        for query in (low_stock_products, out_of_stock_products, product_samples):
            for limit in (0, -1, 51, True, 1.5):
                cursor = _Cursor()
                with self.subTest(query=query.__name__, limit=limit):
                    with self.assertRaises(InvalidProductLimitError):
                        query(  # type: ignore[arg-type]
                            _Connection(cursor), self.tenant, limit
                        )
                    self.assertFalse(cursor.executed)

    def test_summary_matches_oracle_exactly(self) -> None:
        expected = InventorySummary(10, 8, 3, 1, 2)
        actual = inventory_summary(  # type: ignore[arg-type]
            _Connection(_Cursor(tuple(expected))), self.tenant
        )
        _assert_matches_oracle(actual, expected)

        with self.assertRaises(RuntimeError):
            _assert_matches_oracle(actual, InventorySummary(10, 8, 2, 1, 2))

    def test_duplicate_product_ids_are_rejected(self) -> None:
        _assert_unique_product_ids(ProductIdValidation(5, 5))
        with self.assertRaises(RuntimeError):
            _assert_unique_product_ids(ProductIdValidation(5, 4))

    def test_prices_remain_decimal(self) -> None:
        price = Decimal("123.456789")
        cursor = _Cursor()
        cursor.fetchall = lambda: [
            (UUID("33333333-3333-3333-3333-333333333333"), "Product", 1, 2, price)
        ]
        result = low_stock_products(  # type: ignore[arg-type]
            _Connection(cursor), self.tenant
        )
        self.assertIs(result[0].precio_actual, price)


if __name__ == "__main__":
    unittest.main()
