"""Reusable definition and deterministic queries for ``productos``."""

from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

import pyodbc

from app.tenant import TenantContext

PRODUCTS_VIEW_SQL = """
SELECT
    p.Id                                                   AS producto_id,
    COALESCE(p.Name, pb.Name)                              AS producto,
    pb.BarCode                                             AS codigo_barras,
    category.Name                                          AS categoria,
    subcategory.Name                                       AS subcategoria,
    brand.Name                                             AS marca,
    p.Price                                                AS precio_actual,
    p.UnitCost                                             AS costo_unitario_actual,
    p.AverageCost                                          AS costo_promedio_actual,
    p.Stock                                                AS stock_actual,
    p.MinimunStock                                         AS stock_minimo,
    CASE WHEN p.IsNotAlterInventory = 0 THEN 1 ELSE 0 END AS controla_inventario
FROM catalog.Product AS p
INNER JOIN store.Establishment AS e
    ON e.Id = p.EstablishmentId
LEFT JOIN catalog.ProductBusiness AS pb
    ON pb.Id = p.ProductBusinessId
    AND pb.BusinessId = e.BusinessId
    AND pb.IsDeleted = 0
LEFT JOIN params.Category AS category
    ON category.Id = pb.CategoryId
LEFT JOIN params.SubCategory AS subcategory
    ON subcategory.Id = pb.SubCategoryId
LEFT JOIN params.Brand AS brand
    ON brand.Id = pb.BrandId
WHERE
    p.EstablishmentId = CAST(? AS uniqueidentifier)
    AND e.BusinessId = CAST(? AS uniqueidentifier)
    AND p.IsActive = 1
""".strip()


class TenantRequiredError(ValueError):
    """Raised when a deterministic products query has no tenant scope."""


class InvalidProductLimitError(ValueError):
    """Raised when a products query receives an unsafe or excessive limit."""


class InventorySummary(NamedTuple):
    productos_activos: int
    productos_controlados: int
    agotados: int
    stock_negativo: int
    bajo_stock: int


class ProductAlert(NamedTuple):
    producto_id: UUID | str
    producto: str
    stock_actual: int
    stock_minimo: int
    precio_actual: Decimal | None


class ProductSample(NamedTuple):
    producto: str
    precio_actual: Decimal | None
    stock_actual: int


def _require_tenant(tenant: TenantContext | None) -> TenantContext:
    if tenant is None:
        raise TenantRequiredError("A server-side TenantContext is required")
    return tenant


def _validate_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        raise InvalidProductLimitError(
            "Product limit must be an integer from 1 through 50"
        )
    return limit


def _execute(
    connection: pyodbc.Connection,
    tenant: TenantContext | None,
    query_body: str,
    query_parameters: tuple[object, ...] = (),
) -> pyodbc.Cursor:
    active_tenant = _require_tenant(tenant)
    sql = f"WITH productos AS (\n{PRODUCTS_VIEW_SQL}\n)\n{query_body}"
    cursor = connection.cursor()
    cursor.execute(
        sql,
        str(active_tenant.establishment_id),
        str(active_tenant.business_id),
        *query_parameters,
    )
    return cursor


def inventory_summary(
    connection: pyodbc.Connection,
    tenant: TenantContext | None,
) -> InventorySummary:
    """Return current inventory counts for active products in one establishment."""

    cursor = _execute(
        connection,
        tenant,
        """
SELECT
    COUNT_BIG(*) AS productos_activos,
    SUM(CASE WHEN controla_inventario = 1 THEN 1 ELSE 0 END)
        AS productos_controlados,
    SUM(
        CASE
            WHEN controla_inventario = 1 AND stock_actual <= 0 THEN 1
            ELSE 0
        END
    ) AS agotados,
    SUM(
        CASE
            WHEN controla_inventario = 1 AND stock_actual < 0 THEN 1
            ELSE 0
        END
    ) AS stock_negativo,
    SUM(
        CASE
            WHEN controla_inventario = 1
             AND stock_actual > 0
             AND stock_actual <= stock_minimo THEN 1
            ELSE 0
        END
    ) AS bajo_stock
FROM productos;
""".strip(),
    )
    row = cursor.fetchone()
    return InventorySummary(*(int(value or 0) for value in row))


def low_stock_products(
    connection: pyodbc.Connection,
    tenant: TenantContext | None,
    limit: int = 20,
) -> list[ProductAlert]:
    """Return controlled products above zero and at or below minimum stock."""

    active_limit = _validate_limit(limit)
    cursor = _execute(
        connection,
        tenant,
        """
SELECT TOP (?)
    producto_id,
    producto,
    stock_actual,
    stock_minimo,
    precio_actual
FROM productos
WHERE controla_inventario = 1
  AND stock_actual > 0
  AND stock_actual <= stock_minimo
ORDER BY (stock_minimo - stock_actual) DESC, producto, producto_id;
""".strip(),
        (active_limit,),
    )
    return [ProductAlert(*row) for row in cursor.fetchall()]


def out_of_stock_products(
    connection: pyodbc.Connection,
    tenant: TenantContext | None,
    limit: int = 20,
) -> list[ProductAlert]:
    """Return controlled products with negative stock first, followed by zero."""

    active_limit = _validate_limit(limit)
    cursor = _execute(
        connection,
        tenant,
        """
SELECT TOP (?)
    producto_id,
    producto,
    stock_actual,
    stock_minimo,
    precio_actual
FROM productos
WHERE controla_inventario = 1
  AND stock_actual <= 0
ORDER BY
    CASE WHEN stock_actual < 0 THEN 0 ELSE 1 END,
    stock_actual,
    producto,
    producto_id;
""".strip(),
        (active_limit,),
    )
    return [ProductAlert(*row) for row in cursor.fetchall()]


def product_samples(
    connection: pyodbc.Connection,
    tenant: TenantContext | None,
    limit: int = 5,
) -> list[ProductSample]:
    """Return a small deterministic sample of current product values.

    Current costs exposed by the view must never be used as historical sale costs,
    profit, or margin.
    """

    active_limit = _validate_limit(limit)
    cursor = _execute(
        connection,
        tenant,
        """
SELECT TOP (?)
    producto,
    precio_actual,
    stock_actual
FROM productos
ORDER BY producto, producto_id;
""".strip(),
        (active_limit,),
    )
    return [ProductSample(*row) for row in cursor.fetchall()]
