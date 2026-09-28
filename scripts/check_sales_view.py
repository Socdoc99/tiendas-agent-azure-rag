"""Validate the virtual ``ventas`` view against canonical sale headers."""

import sys
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pyodbc  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.database.connection import database_connection  # noqa: E402
from app.semantic.sales import (  # noqa: E402
    SalesSummary,
    sales_by_day,
    sales_by_hour,
    sales_summary,
)
from app.tenant import TenantContext, validate_tenant  # noqa: E402

ORACLE_SQL = """
SELECT
    SUM(s.TotalSale) AS total_facturado,
    COUNT_BIG(*) AS tickets
FROM trade.Sale AS s
INNER JOIN store.PointOfSale AS pos
    ON pos.Id = s.PointOfSaleId
INNER JOIN store.Establishment AS e
    ON e.Id = pos.EstablishmentId
WHERE e.Id = CAST(? AS uniqueidentifier)
  AND e.BusinessId = CAST(? AS uniqueidentifier)
  AND s.IsActive = 1
  AND s.SalesDate >= ?
  AND s.SalesDate < ?;
""".strip()


class OracleSummary(NamedTuple):
    total_facturado: Decimal | None
    tickets: int


def _last_complete_day(last_sale: datetime | None) -> tuple[datetime, datetime]:
    if last_sale is None:
        raise RuntimeError("The configured tenant has no active sales")
    end = datetime.combine(last_sale.date(), time.min)
    return end - timedelta(days=1), end


def _oracle_summary(
    connection: pyodbc.Connection,
    tenant: TenantContext,
    start: datetime,
    end: datetime,
) -> OracleSummary:
    cursor = connection.cursor()
    cursor.execute(
        ORACLE_SQL,
        str(tenant.establishment_id),
        str(tenant.business_id),
        start,
        end,
    )
    row = cursor.fetchone()
    total: Decimal | None = row[0]
    tickets = int(row[1])
    return OracleSummary(total, tickets)


def _assert_matches_oracle(
    summary: SalesSummary,
    oracle: OracleSummary,
) -> None:
    if (
        summary.total_facturado != oracle.total_facturado
        or summary.tickets != oracle.tickets
    ):
        raise RuntimeError(
            "Semantic view total or tickets do not match the canonical Sale "
            "header oracle: "
            f"ventas={summary!r}, oracle={oracle!r}"
        )


def _money(value: Decimal | None) -> str:
    return "None" if value is None else format(value, "f")


def main() -> int:
    settings = get_settings()
    tenant = TenantContext.from_settings(settings)

    with database_connection(settings) as connection:
        tenant_summary = validate_tenant(connection, tenant)
        start, end = _last_complete_day(tenant_summary.last_sale)

        summary = sales_summary(connection, tenant, start, end)
        daily = sales_by_day(connection, tenant, start, end)
        hourly = sales_by_hour(connection, tenant, start, end)
        oracle = _oracle_summary(connection, tenant, start, end)
        _assert_matches_oracle(summary, oracle)

    print("Semantic view: ventas")
    print("Tenant validation: OK")
    print()
    print("Range:")
    print(start.isoformat(sep=" "))
    print("to")
    print(end.isoformat(sep=" "))
    print()
    print(f"Sales total: {_money(summary.total_facturado)}")
    print(f"Tickets: {summary.tickets}")
    print(f"Average ticket: {_money(summary.ticket_promedio)}")
    print()
    print("Sales by day:")
    for item in daily:
        print(
            f"{item.dia.isoformat()}: {_money(item.total_facturado)} "
            f"({item.tickets} tickets)"
        )
    print()
    print("Sales by hour:")
    for item in hourly:
        print(
            f"{item.hora:02d}: {_money(item.total_facturado)} "
            f"({item.tickets} tickets)"
        )
    print()
    print("Oracle comparison: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
