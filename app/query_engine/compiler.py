"""Compile validated logical SQL to tenant-scoped executable T-SQL."""

from sqlglot import exp, parse_one

from app.query_engine.models import CompiledQuery, QueryValidationError
from app.query_engine.registry import SEMANTIC_VIEWS
from app.query_engine.validator import validate_logical_sql
from app.tenant import TenantContext


def compile_query(logical_sql: str, tenant: TenantContext | None) -> CompiledQuery:
    """Inject the one trusted semantic view as the first CTE."""

    if tenant is None or not isinstance(tenant, TenantContext):
        raise QueryValidationError("A server-side TenantContext is required")

    validated = validate_logical_sql(logical_sql)
    semantic_view = SEMANTIC_VIEWS[validated.semantic_view]
    physical_query = parse_one(semantic_view.sql, read="tsql")
    physical_cte = exp.CTE(
        this=physical_query,
        alias=exp.TableAlias(this=exp.to_identifier(semantic_view.name)),
    )

    expression = validated.expression.copy()
    user_with = expression.args.get("with_")
    if user_with is None:
        expression.set("with_", exp.With(expressions=[physical_cte]))
    else:
        user_with.set(
            "expressions",
            [physical_cte, *(cte.copy() for cte in user_with.expressions)],
        )

    return CompiledQuery(
        sql=expression.sql(dialect="tsql"),
        parameters=semantic_view.tenant_parameters(tenant),
        semantic_view=semantic_view.name,
    )
