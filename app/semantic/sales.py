"""Reusable definition and deterministic queries for the ``ventas`` view."""

from datetime import date, datetime
from decimal import Decimal
from typing import NamedTuple

import pyodbc

from app.tenant import TenantContext

SALES_VIEW_SQL = """
SELECT
    s.Id        AS venta_id,
    s.SalesDate AS fecha,
    s.Subtotal  AS subtotal,
    s.Discount  AS descuento,
    s.TotalSale AS total_facturado,
    s.SaleType  AS tipo_venta_codigo,
    pos.Name    AS punto_venta
FROM trade.Sale AS s
INNER JOIN store.PointOfSale AS pos
    ON pos.Id = s.PointOfSaleId
INNER JOIN store.Establishment AS e
    ON e.Id = pos.EstablishmentId
WHERE
    e.Id = CAST(? AS uniqueidentifier)
    AND e.BusinessId = CAST(? AS uniqueidentifier)
    AND s.IsActive = 1
""".strip()


class InvalidSalesRangeError(ValueError):
    """Raised when a sales range is empty or reversed."""


class TenantRequiredError(ValueError):
    """Raised when a deterministic sales query has no tenant scope."""


class SalesSummary(NamedTuple):
    total_facturado: Decimal | None
    tickets: int
    ticket_promedio: Decimal | None


class DailySales(NamedTuple):
    dia: date
    total_facturado: Decimal
    tickets: int


class HourlySales(NamedTuple):
    hora: int
    total_facturado: Decimal
    tickets: int


def _validate_inputs(
    tenant: TenantContext | None,
    start: datetime,
    end: datetime,
) -> TenantContext:
    if tenant is None:
        raise TenantRequiredError("A server-side TenantContext is required")
    if start >= end:
        raise InvalidSalesRangeError("Sales range must satisfy start < end")
    return tenant


def _execute(
    connection: pyodbc.Connection,
    tenant: TenantContext | None,
    start: datetime,
    end: datetime,
    query_body: str,
) -> pyodbc.Cursor:
    active_tenant = _validate_inputs(tenant, start, end)
    sql = f"WITH ventas AS (\n{SALES_VIEW_SQL}\n)\n{query_body}"
    cursor = connection.cursor()
    cursor.execute(
        sql,
        str(active_tenant.establishment_id),
        str(active_tenant.business_id),
        start,
        end,
    )
    return cursor


def sales_summary(
    connection: pyodbc.Connection,
    tenant: TenantContext | None,
    start: datetime,
    end: datetime,
) -> SalesSummary:
    """Return canonical header metrics for a semi-open business-date range."""

    cursor = _execute(
        connection,
        tenant,
        start,
        end,
        """
SELECT
    SUM(total_facturado) AS total_facturado,
    COUNT_BIG(*) AS tickets,
    SUM(total_facturado) / NULLIF(COUNT_BIG(*), 0) AS ticket_promedio
FROM ventas
WHERE fecha >= ?
  AND fecha < ?;
""".strip(),
    )
    row = cursor.fetchone()
    return SalesSummary(
        total_facturado=row[0],
        tickets=int(row[1]),
        ticket_promedio=row[2],
    )


def sales_by_day(
    connection: pyodbc.Connection,
    tenant: TenantContext | None,
    start: datetime,
    end: datetime,
) -> list[DailySales]:
    """Return sales grouped by local business date."""

    cursor = _execute(
        connection,
        tenant,
        start,
        end,
        """
SELECT
    CAST(fecha AS date) AS dia,
    SUM(total_facturado) AS total_facturado,
    COUNT_BIG(*) AS tickets
FROM ventas
WHERE fecha >= ?
  AND fecha < ?
GROUP BY CAST(fecha AS date)
ORDER BY dia;
""".strip(),
    )
    return [
        DailySales(dia=row[0], total_facturado=row[1], tickets=int(row[2]))
        for row in cursor.fetchall()
    ]


def sales_by_hour(
    connection: pyodbc.Connection,
    tenant: TenantContext | None,
    start: datetime,
    end: datetime,
) -> list[HourlySales]:
    """Return sales grouped by local business hour (0 through 23)."""

    cursor = _execute(
        connection,
        tenant,
        start,
        end,
        """
SELECT
    DATEPART(HOUR, fecha) AS hora,
    SUM(total_facturado) AS total_facturado,
    COUNT_BIG(*) AS tickets
FROM ventas
WHERE fecha >= ?
  AND fecha < ?
GROUP BY DATEPART(HOUR, fecha)
ORDER BY hora;
""".strip(),
    )
    return [
        HourlySales(hora=int(row[0]), total_facturado=row[1], tickets=int(row[2]))
        for row in cursor.fetchall()
    ]
