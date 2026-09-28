from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.tenant import (
    InvalidTenantError,
    TenantContext,
    TenantNotConfiguredError,
    validate_tenant,
)

BUSINESS_ID = UUID("11111111-1111-1111-1111-111111111111")
ESTABLISHMENT_ID = UUID("22222222-2222-2222-2222-222222222222")


class FakeCursor:
    def __init__(self, rows: list[tuple | None]) -> None:
        self.rows = iter(rows)
        self.calls: list[tuple[str, tuple]] = []

    def execute(self, sql: str, *parameters: str) -> None:
        self.calls.append((sql, parameters))

    def fetchone(self) -> tuple | None:
        return next(self.rows)


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor

    def cursor(self) -> FakeCursor:
        return self._cursor


def test_tenant_context_is_created_server_side_and_immutable() -> None:
    settings = Settings(
        demo_business_id=str(BUSINESS_ID),
        demo_establishment_id=str(ESTABLISHMENT_ID),
    )

    tenant = TenantContext.from_settings(settings)

    assert tenant.business_id == BUSINESS_ID
    assert tenant.establishment_id == ESTABLISHMENT_ID
    assert tenant.timezone == "America/Bogota"
    with pytest.raises(ValidationError):
        tenant.business_id = UUID("33333333-3333-3333-3333-333333333333")


def test_tenant_context_requires_both_configured_ids() -> None:
    with pytest.raises(TenantNotConfiguredError):
        TenantContext.from_settings(Settings(demo_business_id=str(BUSINESS_ID)))


def test_validate_tenant_checks_business_establishment_relationship() -> None:
    cursor = FakeCursor(
        [
            ("Business", "Establishment"),
            (2,),
            (5, datetime(2026, 1, 1), datetime(2026, 9, 1)),
        ]
    )
    tenant = TenantContext(
        business_id=BUSINESS_ID,
        establishment_id=ESTABLISHMENT_ID,
        timezone="America/Bogota",
    )

    result = validate_tenant(FakeConnection(cursor), tenant)

    assert result.business_name == "Business"
    assert result.establishment_name == "Establishment"
    assert result.point_of_sales_count == 2
    assert result.sales_count == 5
    assert result.last_sale == datetime(2026, 9, 1)
    assert len(cursor.calls) == 3
    for _, parameters in cursor.calls:
        assert parameters == (str(ESTABLISHMENT_ID), str(BUSINESS_ID))


def test_validate_tenant_rejects_mismatched_establishment_before_other_queries() -> None:
    cursor = FakeCursor([None])
    tenant = TenantContext(
        business_id=BUSINESS_ID,
        establishment_id=ESTABLISHMENT_ID,
        timezone="America/Bogota",
    )

    with pytest.raises(InvalidTenantError):
        validate_tenant(FakeConnection(cursor), tenant)
    assert len(cursor.calls) == 1
