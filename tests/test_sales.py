"""Focused tests for the ``ventas`` semantic view."""

import unittest
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.semantic.sales import (
    SALES_VIEW_SQL,
    InvalidSalesRangeError,
    SalesSummary,
    TenantRequiredError,
    sales_summary,
)
from app.tenant import TenantContext
from scripts.check_sales_view import OracleSummary, _assert_matches_oracle


class _Cursor:
    def __init__(self, row: tuple[Decimal, int, Decimal]) -> None:
        self.row = row
        self.executed = False

    def execute(self, *_args: object) -> None:
        self.executed = True

    def fetchone(self) -> tuple[Decimal, int, Decimal]:
        return self.row


class _Connection:
    def __init__(self, cursor: _Cursor) -> None:
        self._cursor = cursor

    def cursor(self) -> _Cursor:
        return self._cursor


class SalesViewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.start = datetime(2026, 9, 1)
        self.end = datetime(2026, 9, 2)
        self.tenant = TenantContext(
            business_id=UUID("11111111-1111-1111-1111-111111111111"),
            establishment_id=UUID("22222222-2222-2222-2222-222222222222"),
            timezone="America/Bogota",
        )

    def test_empty_or_reversed_range_is_rejected_before_sql(self) -> None:
        cursor = _Cursor((Decimal("0"), 0, Decimal("0")))
        connection = _Connection(cursor)

        for end in (self.start, datetime(2026, 8, 31)):
            with self.subTest(end=end):
                with self.assertRaises(InvalidSalesRangeError):
                    sales_summary(connection, self.tenant, self.start, end)  # type: ignore[arg-type]
        self.assertFalse(cursor.executed)

    def test_tenant_is_required_before_sql(self) -> None:
        cursor = _Cursor((Decimal("0"), 0, Decimal("0")))
        connection = _Connection(cursor)

        with self.assertRaises(TenantRequiredError):
            sales_summary(connection, None, self.start, self.end)  # type: ignore[arg-type]
        self.assertFalse(cursor.executed)

    def test_sales_definition_does_not_query_sale_detail(self) -> None:
        self.assertNotIn("SaleDetail", SALES_VIEW_SQL)

    def test_smoke_metrics_match_oracle(self) -> None:
        expected = SalesSummary(Decimal("125.50"), 2, Decimal("62.75"))
        cursor = _Cursor(tuple(expected))
        actual = sales_summary(
            _Connection(cursor),  # type: ignore[arg-type]
            self.tenant,
            self.start,
            self.end,
        )

        oracle = OracleSummary(expected.total_facturado, expected.tickets)
        _assert_matches_oracle(actual, oracle)

    def test_smoke_metrics_reject_oracle_difference(self) -> None:
        summary = SalesSummary(Decimal("125.50"), 2, Decimal("62.75"))
        oracle = OracleSummary(Decimal("125.49"), 2)

        with self.assertRaises(RuntimeError):
            _assert_matches_oracle(summary, oracle)


if __name__ == "__main__":
    unittest.main()
