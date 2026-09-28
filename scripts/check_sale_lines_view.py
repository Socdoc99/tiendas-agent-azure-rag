"""Validate ``venta_lineas`` against sale details without catalog joins."""

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
from app.semantic.sale_lines import (  # noqa: E402
    SaleLinesSummary,
    sale_lines_summary,
    top_categories_by_units,
    top_products_by_units,
)
from app.tenant import TenantContext, validate_tenant  # noqa: E402

ORACLE_SQL = """
SELECT
    COUNT_BIG(sd.Id) AS total_lineas,
    SUM(CAST(sd.Quantity AS bigint)) AS unidades,
    SUM(sd.TotalValue) AS valor_lineas
FROM trade.SaleDetail AS sd
INNER JOIN trade.Sale AS s
    ON s.Id = sd.SaleId
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


METADATA_VALIDATION_SQL = """
SELECT
    SUM(CASE WHEN p.Id IS NOT NULL THEN 1 ELSE 0 END) AS resolved_products,
    SUM(CASE WHEN p.Id IS NULL THEN 1 ELSE 0 END) AS unresolved_products,
    SUM(CASE WHEN p.Id IS NOT NULL AND pb.Id IS NULL THEN 1 ELSE 0 END)
        AS unresolved_product_business,
    SUM(
        CASE
            WHEN p.Id IS NOT NULL AND p.EstablishmentId <> e.Id THEN 1
            WHEN pb.Id IS NOT NULL AND pb.BusinessId <> e.BusinessId THEN 1
            ELSE 0
        END
    ) AS cross_tenant_metadata_leaks
FROM trade.SaleDetail AS sd
INNER JOIN trade.Sale AS s
    ON s.Id = sd.SaleId
INNER JOIN store.PointOfSale AS pos
    ON pos.Id = s.PointOfSaleId
INNER JOIN store.Establishment AS e
    ON e.Id = pos.EstablishmentId
LEFT JOIN catalog.Product AS p
    ON p.Id = sd.ProductId
    AND p.EstablishmentId = e.Id
LEFT JOIN catalog.ProductBusiness AS pb
    ON pb.Id = p.ProductBusinessId
    AND pb.BusinessId = e.BusinessId
WHERE e.Id = CAST(? AS uniqueidentifier)
  AND e.BusinessId = CAST(? AS uniqueidentifier)
  AND s.IsActive = 1
  AND s.SalesDate >= ?
  AND s.SalesDate < ?;
""".strip()


class OracleSummary(NamedTuple):
    total_lineas: int
    unidades: int | None
    valor_lineas: Decimal | None


class MetadataValidation(NamedTuple):
    resolved_products: int
    unresolved_products: int
    unresolved_product_business: int
    cross_tenant_metadata_leaks: int


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
    return OracleSummary(
        total_lineas=int(row[0]),
        unidades=None if row[1] is None else int(row[1]),
        valor_lineas=row[2],
    )


def _metadata_validation(
    connection: pyodbc.Connection,
    tenant: TenantContext,
    start: datetime,
    end: datetime,
) -> MetadataValidation:
    cursor = connection.cursor()
    cursor.execute(
        METADATA_VALIDATION_SQL,
        str(tenant.establishment_id),
        str(tenant.business_id),
        start,
        end,
    )
    row = cursor.fetchone()
    return MetadataValidation(*(int(value or 0) for value in row))


def _assert_matches_oracle(
    summary: SaleLinesSummary,
    oracle: OracleSummary,
) -> None:
    if tuple(summary) != tuple(oracle):
        raise RuntimeError(
            "Semantic view metrics do not match the SaleDetail oracle: "
            f"venta_lineas={summary!r}, oracle={oracle!r}"
        )


def _assert_no_cross_tenant_leaks(validation: MetadataValidation) -> None:
    if validation.cross_tenant_metadata_leaks:
        raise RuntimeError(
            "Cross-tenant product metadata was resolved: "
            f"{validation.cross_tenant_metadata_leaks} line(s)"
        )


def _money(value: Decimal | None) -> str:
    return "None" if value is None else format(value, "f")


def main() -> int:
    settings = get_settings()
    tenant = TenantContext.from_settings(settings)

    with database_connection(settings) as connection:
        tenant_summary = validate_tenant(connection, tenant)
        start, end = _last_complete_day(tenant_summary.last_sale)

        summary = sale_lines_summary(connection, tenant, start, end)
        products = top_products_by_units(connection, tenant, start, end)
        categories = top_categories_by_units(connection, tenant, start, end)
        oracle = _oracle_summary(connection, tenant, start, end)
        metadata = _metadata_validation(connection, tenant, start, end)
        _assert_matches_oracle(summary, oracle)
        _assert_no_cross_tenant_leaks(metadata)

    print("Semantic view: venta_lineas")
    print("Tenant validation: OK")
    print()
    print("Range:")
    print(start.isoformat(sep=" "))
    print("to")
    print(end.isoformat(sep=" "))
    print()
    print(f"Lines: {summary.total_lineas}")
    print(f"Units: {summary.unidades}")
    print(f"Line value: {_money(summary.valor_lineas)}")
    print()
    print("Product metadata coverage:")
    print(f"Resolved products: {metadata.resolved_products}")
    print(f"Unresolved products: {metadata.unresolved_products}")
    print(
        "Unresolved ProductBusiness metadata: "
        f"{metadata.unresolved_product_business}"
    )
    print(f"Cross-tenant metadata leaks: {metadata.cross_tenant_metadata_leaks}")
    print()
    print("Top products:")
    for position, item in enumerate(products, start=1):
        print(
            f"{position}. {item.producto} | units={item.unidades} | "
            f"line value={_money(item.valor_lineas)}"
        )
    print()
    print("Top categories:")
    for position, item in enumerate(categories, start=1):
        print(
            f"{position}. {item.categoria} | units={item.unidades} | "
            f"line value={_money(item.valor_lineas)}"
        )
    print()
    print("Oracle comparison: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
