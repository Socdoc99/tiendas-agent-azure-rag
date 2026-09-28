"""Reusable definition and deterministic queries for ``venta_lineas``."""

from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

import pyodbc

from app.tenant import TenantContext

SALE_LINES_VIEW_SQL = """
SELECT
    sd.Id                         AS linea_id,
    s.Id                          AS venta_id,
    s.SalesDate                   AS fecha,
    sd.ProductId                  AS producto_id,
    COALESCE(p.Name, pb.Name)      AS producto,
    pb.BarCode                    AS codigo_barras,
    category.Name                 AS categoria,
    subcategory.Name              AS subcategoria,
    brand.Name                    AS marca,
    manufacturer.Name             AS fabricante,
    sd.Quantity                   AS cantidad,
    sd.UnitPrice                  AS precio_unitario,
    sd.DiscountValue              AS descuento_linea,
    sd.AppliedTaxValue            AS impuesto_linea,
    sd.TotalValue                 AS valor_linea
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
LEFT JOIN params.Category AS category
    ON category.Id = pb.CategoryId
LEFT JOIN params.SubCategory AS subcategory
    ON subcategory.Id = pb.SubCategoryId
LEFT JOIN params.Brand AS brand
    ON brand.Id = pb.BrandId
LEFT JOIN params.Manufacturer AS manufacturer
    ON manufacturer.Id = pb.ManufacturerId
WHERE
    e.Id = CAST(? AS uniqueidentifier)
    AND e.BusinessId = CAST(? AS uniqueidentifier)
    AND s.IsActive = 1
""".strip()


class InvalidSaleLinesRangeError(ValueError):
    """Raised when a sale-lines range is empty or reversed."""


class TenantRequiredError(ValueError):
    """Raised when a deterministic sale-lines query has no tenant scope."""


class InvalidTopLimitError(ValueError):
    """Raised when a top query receives an unsafe or excessive limit."""


class SaleLinesSummary(NamedTuple):
    total_lineas: int
    unidades: int | None
    valor_lineas: Decimal | None


class TopProduct(NamedTuple):
    producto_id: UUID | str | None
    producto: str | None
    unidades: int
    valor_lineas: Decimal | None


class TopCategory(NamedTuple):
    categoria: str | None
    unidades: int
    valor_lineas: Decimal | None


def _validate_inputs(
    tenant: TenantContext | None,
    start: datetime,
    end: datetime,
) -> TenantContext:
    if tenant is None:
        raise TenantRequiredError("A server-side TenantContext is required")
    if start >= end:
        raise InvalidSaleLinesRangeError(
            "Sale-lines range must satisfy start < end"
        )
    return tenant


def _validate_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        raise InvalidTopLimitError("Top limit must be an integer from 1 through 50")
    return limit


def _execute(
    connection: pyodbc.Connection,
    tenant: TenantContext | None,
    start: datetime,
    end: datetime,
    query_body: str,
    query_parameters: tuple[object, ...] = (),
) -> pyodbc.Cursor:
    active_tenant = _validate_inputs(tenant, start, end)
    sql = f"WITH venta_lineas AS (\n{SALE_LINES_VIEW_SQL}\n)\n{query_body}"
    cursor = connection.cursor()
    cursor.execute(
        sql,
        str(active_tenant.establishment_id),
        str(active_tenant.business_id),
        *query_parameters,
        start,
        end,
    )
    return cursor


def sale_lines_summary(
    connection: pyodbc.Connection,
    tenant: TenantContext | None,
    start: datetime,
    end: datetime,
) -> SaleLinesSummary:
    """Return stored line metrics for a semi-open business-date range."""

    cursor = _execute(
        connection,
        tenant,
        start,
        end,
        """
SELECT
    COUNT_BIG(*) AS total_lineas,
    SUM(CAST(cantidad AS bigint)) AS unidades,
    SUM(valor_linea) AS valor_lineas
FROM venta_lineas
WHERE fecha >= ?
  AND fecha < ?;
""".strip(),
    )
    row = cursor.fetchone()
    return SaleLinesSummary(
        total_lineas=int(row[0]),
        unidades=None if row[1] is None else int(row[1]),
        valor_lineas=row[2],
    )


def top_products_by_units(
    connection: pyodbc.Connection,
    tenant: TenantContext | None,
    start: datetime,
    end: datetime,
    limit: int = 10,
) -> list[TopProduct]:
    """Return products ordered by historical units from sale lines."""

    active_limit = _validate_limit(limit)
    cursor = _execute(
        connection,
        tenant,
        start,
        end,
        """
SELECT TOP (?)
    producto_id,
    producto,
    SUM(CAST(cantidad AS bigint)) AS unidades,
    SUM(valor_linea) AS valor_lineas
FROM venta_lineas
WHERE fecha >= ?
  AND fecha < ?
GROUP BY producto_id, producto
ORDER BY unidades DESC;
""".strip(),
        (active_limit,),
    )
    return [
        TopProduct(
            producto_id=row[0],
            producto=row[1],
            unidades=int(row[2]),
            valor_lineas=row[3],
        )
        for row in cursor.fetchall()
    ]


def top_categories_by_units(
    connection: pyodbc.Connection,
    tenant: TenantContext | None,
    start: datetime,
    end: datetime,
    limit: int = 10,
) -> list[TopCategory]:
    """Return categories, including NULL, ordered by sale-line units."""

    active_limit = _validate_limit(limit)
    cursor = _execute(
        connection,
        tenant,
        start,
        end,
        """
SELECT TOP (?)
    categoria,
    SUM(CAST(cantidad AS bigint)) AS unidades,
    SUM(valor_linea) AS valor_lineas
FROM venta_lineas
WHERE fecha >= ?
  AND fecha < ?
GROUP BY categoria
ORDER BY unidades DESC;
""".strip(),
        (active_limit,),
    )
    return [
        TopCategory(
            categoria=row[0],
            unidades=int(row[1]),
            valor_lineas=row[2],
        )
        for row in cursor.fetchall()
    ]
