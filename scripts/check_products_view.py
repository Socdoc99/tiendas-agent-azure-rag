"""Validate ``productos`` against active products without using its CTE."""

import sys
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pyodbc  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.database.connection import database_connection  # noqa: E402
from app.semantic.products import (  # noqa: E402
    PRODUCTS_VIEW_SQL,
    InventorySummary,
    inventory_summary,
    low_stock_products,
    out_of_stock_products,
    product_samples,
)
from app.tenant import TenantContext, validate_tenant  # noqa: E402

ORACLE_SQL = """
SELECT
    COUNT_BIG(*) AS productos_activos,
    SUM(CASE WHEN p.IsNotAlterInventory = 0 THEN 1 ELSE 0 END)
        AS productos_controlados,
    SUM(
        CASE
            WHEN p.IsNotAlterInventory = 0 AND p.Stock <= 0 THEN 1
            ELSE 0
        END
    ) AS agotados,
    SUM(
        CASE
            WHEN p.IsNotAlterInventory = 0 AND p.Stock < 0 THEN 1
            ELSE 0
        END
    ) AS stock_negativo,
    SUM(
        CASE
            WHEN p.IsNotAlterInventory = 0
             AND p.Stock > 0
             AND p.Stock <= p.MinimunStock THEN 1
            ELSE 0
        END
    ) AS bajo_stock
FROM catalog.Product AS p
INNER JOIN store.Establishment AS e
    ON e.Id = p.EstablishmentId
WHERE p.EstablishmentId = CAST(? AS uniqueidentifier)
  AND e.BusinessId = CAST(? AS uniqueidentifier)
  AND p.IsActive = 1;
""".strip()


VIEW_VALIDATION_SQL = f"""
WITH productos AS (
{PRODUCTS_VIEW_SQL}
)
SELECT COUNT_BIG(*), COUNT_BIG(DISTINCT producto_id)
FROM productos;
""".strip()


METADATA_VALIDATION_SQL = """
SELECT
    SUM(CASE WHEN pb.Id IS NOT NULL THEN 1 ELSE 0 END) AS resolved,
    SUM(CASE WHEN pb.Id IS NULL THEN 1 ELSE 0 END) AS unresolved,
    SUM(
        CASE
            WHEN pb.Id IS NOT NULL AND pb.BusinessId <> e.BusinessId THEN 1
            ELSE 0
        END
    ) AS cross_tenant_metadata_leaks
FROM catalog.Product AS p
INNER JOIN store.Establishment AS e
    ON e.Id = p.EstablishmentId
LEFT JOIN catalog.ProductBusiness AS pb
    ON pb.Id = p.ProductBusinessId
    AND pb.BusinessId = e.BusinessId
    AND pb.IsDeleted = 0
WHERE p.EstablishmentId = CAST(? AS uniqueidentifier)
  AND e.BusinessId = CAST(? AS uniqueidentifier)
  AND p.IsActive = 1;
""".strip()


class MetadataValidation(NamedTuple):
    resolved: int
    unresolved: int
    cross_tenant_metadata_leaks: int


class ProductIdValidation(NamedTuple):
    products: int
    distinct_product_ids: int


def _oracle_summary(
    connection: pyodbc.Connection,
    tenant: TenantContext,
) -> InventorySummary:
    cursor = connection.cursor()
    cursor.execute(
        ORACLE_SQL,
        str(tenant.establishment_id),
        str(tenant.business_id),
    )
    return InventorySummary(*(int(value or 0) for value in cursor.fetchone()))


def _view_validation(
    connection: pyodbc.Connection,
    tenant: TenantContext,
) -> ProductIdValidation:
    cursor = connection.cursor()
    cursor.execute(
        VIEW_VALIDATION_SQL,
        str(tenant.establishment_id),
        str(tenant.business_id),
    )
    row = cursor.fetchone()
    return ProductIdValidation(int(row[0]), int(row[1]))


def _metadata_validation(
    connection: pyodbc.Connection,
    tenant: TenantContext,
) -> MetadataValidation:
    cursor = connection.cursor()
    cursor.execute(
        METADATA_VALIDATION_SQL,
        str(tenant.establishment_id),
        str(tenant.business_id),
    )
    return MetadataValidation(*(int(value or 0) for value in cursor.fetchone()))


def _assert_matches_oracle(
    summary: InventorySummary,
    oracle: InventorySummary,
) -> None:
    if summary != oracle:
        raise RuntimeError(
            "Semantic view metrics do not match the direct Product oracle: "
            f"productos={summary!r}, oracle={oracle!r}"
        )


def _assert_unique_product_ids(validation: ProductIdValidation) -> None:
    if validation.products != validation.distinct_product_ids:
        raise RuntimeError(
            "The productos semantic view contains duplicate product IDs: "
            f"rows={validation.products}, "
            f"distinct_ids={validation.distinct_product_ids}"
        )


def _assert_no_cross_tenant_leaks(validation: MetadataValidation) -> None:
    if validation.cross_tenant_metadata_leaks:
        raise RuntimeError(
            "Cross-tenant ProductBusiness metadata was resolved: "
            f"{validation.cross_tenant_metadata_leaks} product(s)"
        )


def _money(value: Decimal | None) -> str:
    return "None" if value is None else format(value, "f")


def main() -> int:
    settings = get_settings()
    tenant = TenantContext.from_settings(settings)

    with database_connection(settings) as connection:
        validate_tenant(connection, tenant)
        summary = inventory_summary(connection, tenant)
        low_stock = low_stock_products(connection, tenant)
        out_of_stock = out_of_stock_products(connection, tenant)
        samples = product_samples(connection, tenant)
        oracle = _oracle_summary(connection, tenant)
        ids = _view_validation(connection, tenant)
        metadata = _metadata_validation(connection, tenant)

        _assert_matches_oracle(summary, oracle)
        _assert_unique_product_ids(ids)
        _assert_no_cross_tenant_leaks(metadata)

    print("Semantic view: productos")
    print("Tenant validation: OK")
    print()
    print(f"Active products: {summary.productos_activos}")
    print(f"Inventory-controlled products: {summary.productos_controlados}")
    print(f"Out of stock: {summary.agotados}")
    print(f"Negative stock: {summary.stock_negativo}")
    print(f"Low stock: {summary.bajo_stock}")
    print()
    print("ProductBusiness metadata:")
    print(f"Resolved: {metadata.resolved}")
    print(f"Unresolved: {metadata.unresolved}")
    print(f"Cross-tenant metadata leaks: {metadata.cross_tenant_metadata_leaks}")
    print()
    print("Low stock examples:")
    for item in low_stock:
        print(
            f"{item.producto} | stock={item.stock_actual} | "
            f"minimum={item.stock_minimo} | price={_money(item.precio_actual)}"
        )
    print()
    print("Out of stock examples:")
    for item in out_of_stock:
        print(
            f"{item.producto} | stock={item.stock_actual} | "
            f"minimum={item.stock_minimo} | price={_money(item.precio_actual)}"
        )
    print()
    print("Current product samples:")
    for item in samples:
        print(
            f"{item.producto} | price={_money(item.precio_actual)} | "
            f"stock={item.stock_actual}"
        )
    print()
    print("Oracle comparison: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
