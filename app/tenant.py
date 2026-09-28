"""Tenant resolution and readonly validation queries."""

from datetime import datetime
from typing import NamedTuple
from uuid import UUID

import pyodbc
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings


class TenantContext(BaseModel):
    """Immutable server-side scope for one establishment."""

    model_config = ConfigDict(frozen=True)

    business_id: UUID
    establishment_id: UUID
    timezone: str = Field(min_length=1)

    @classmethod
    def from_settings(cls, settings: Settings) -> "TenantContext":
        """Build the tenant scope from server-side environment settings."""

        if not settings.demo_business_id.strip():
            raise TenantNotConfiguredError("DEMO_BUSINESS_ID is not configured")
        if not settings.demo_establishment_id.strip():
            raise TenantNotConfiguredError("DEMO_ESTABLISHMENT_ID is not configured")

        try:
            return cls(
                business_id=settings.demo_business_id,
                establishment_id=settings.demo_establishment_id,
                timezone=settings.business_timezone,
            )
        except ValidationError as error:
            raise InvalidTenantError("The configured tenant is invalid") from error


class TenantNotConfiguredError(RuntimeError):
    """Raised when the demo tenant has not been selected."""


class InvalidTenantError(RuntimeError):
    """Raised when an establishment does not belong to the configured business."""


class TenantCandidate(NamedTuple):
    business_id: UUID
    establishment_id: UUID
    business_name: str
    establishment_name: str
    sales_count: int
    last_sale: datetime | None


class TenantSummary(NamedTuple):
    business_name: str
    establishment_name: str
    point_of_sales_count: int
    sales_count: int
    first_sale: datetime | None
    last_sale: datetime | None


def find_tenant_candidates(
    connection: pyodbc.Connection,
) -> list[TenantCandidate]:
    """Return active, non-sensitive demo candidates ordered by recent activity."""

    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT TOP (10)
            b.Id,
            e.Id,
            b.Name,
            e.Name,
            COUNT_BIG(s.Id) AS SalesCount,
            MAX(s.SalesDate) AS LastSale
        FROM store.Establishment AS e
        INNER JOIN store.Business AS b
            ON b.Id = e.BusinessId
        LEFT JOIN store.PointOfSale AS pos
            ON pos.EstablishmentId = e.Id
        LEFT JOIN trade.Sale AS s
            ON s.PointOfSaleId = pos.Id
            AND s.IsActive = 1
        WHERE b.IsActive = 1
          AND e.IsActive = 1
        GROUP BY b.Id, e.Id, b.Name, e.Name
        HAVING COUNT_BIG(s.Id) > 0
        ORDER BY LastSale DESC, SalesCount DESC;
        """
    )
    return [
        TenantCandidate(
            business_id=UUID(str(row[0])),
            establishment_id=UUID(str(row[1])),
            business_name=str(row[2]),
            establishment_name=str(row[3]),
            sales_count=int(row[4]),
            last_sale=row[5],
        )
        for row in cursor.fetchall()
    ]


def validate_tenant(
    connection: pyodbc.Connection,
    tenant: TenantContext,
) -> TenantSummary:
    """Validate the exact tenant pair before resolving its POS and active sales."""

    establishment_id = str(tenant.establishment_id)
    business_id = str(tenant.business_id)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT b.Name, e.Name
        FROM store.Establishment AS e
        INNER JOIN store.Business AS b
            ON b.Id = e.BusinessId
        WHERE e.Id = CAST(? AS uniqueidentifier)
          AND e.BusinessId = CAST(? AS uniqueidentifier);
        """,
        establishment_id,
        business_id,
    )
    tenant_row = cursor.fetchone()
    if tenant_row is None:
        raise InvalidTenantError(
            "The configured establishment does not belong to the configured business"
        )

    cursor.execute(
        """
        SELECT COUNT_BIG(*)
        FROM store.PointOfSale AS pos
        INNER JOIN store.Establishment AS e
            ON e.Id = pos.EstablishmentId
        WHERE e.Id = CAST(? AS uniqueidentifier)
          AND e.BusinessId = CAST(? AS uniqueidentifier);
        """,
        establishment_id,
        business_id,
    )
    point_of_sales_count = int(cursor.fetchone()[0])

    cursor.execute(
        """
        SELECT
            COUNT_BIG(s.Id),
            MIN(s.SalesDate),
            MAX(s.SalesDate)
        FROM trade.Sale AS s
        INNER JOIN store.PointOfSale AS pos
            ON pos.Id = s.PointOfSaleId
        INNER JOIN store.Establishment AS e
            ON e.Id = pos.EstablishmentId
        WHERE e.Id = CAST(? AS uniqueidentifier)
          AND e.BusinessId = CAST(? AS uniqueidentifier)
          AND s.IsActive = 1;
        """,
        establishment_id,
        business_id,
    )
    sales_row = cursor.fetchone()

    return TenantSummary(
        business_name=str(tenant_row[0]),
        establishment_name=str(tenant_row[1]),
        point_of_sales_count=point_of_sales_count,
        sales_count=int(sales_row[0]),
        first_sale=sales_row[1],
        last_sale=sales_row[2],
    )
