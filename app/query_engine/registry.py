"""Registry of trusted physical definitions behind logical semantic views."""

from collections.abc import Callable
from dataclasses import dataclass

from app.semantic.products import PRODUCTS_VIEW_SQL
from app.semantic.sale_lines import SALE_LINES_VIEW_SQL
from app.semantic.sales import SALES_VIEW_SQL
from app.tenant import TenantContext

TenantParameters = Callable[[TenantContext], tuple[str, str]]


def _tenant_parameters(tenant: TenantContext) -> tuple[str, str]:
    return str(tenant.establishment_id), str(tenant.business_id)


@dataclass(frozen=True)
class SemanticView:
    name: str
    sql: str
    tenant_parameters: TenantParameters


SEMANTIC_VIEWS = {
    "ventas": SemanticView("ventas", SALES_VIEW_SQL, _tenant_parameters),
    "venta_lineas": SemanticView(
        "venta_lineas", SALE_LINES_VIEW_SQL, _tenant_parameters
    ),
    "productos": SemanticView("productos", PRODUCTS_VIEW_SQL, _tenant_parameters),
}
