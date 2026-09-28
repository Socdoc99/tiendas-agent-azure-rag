"""The single LangChain tool available to the business-data agent."""

import json
from collections.abc import Callable

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings
from app.query_engine import (
    MultipleSemanticViewsError,
    QueryExecutionError,
    QueryResult,
    QueryValidationError,
    UnknownSemanticViewError,
    query_database,
)
from app.tenant import TenantContext

QueryExecutor = Callable[..., QueryResult]


class LogicalQueryInput(BaseModel):
    """Only the logical query is visible in the model-facing schema."""

    model_config = ConfigDict(extra="forbid")

    logical_sql: str = Field(
        min_length=1,
        description=("One read-only T-SQL query over exactly one authorized semantic view."),
    )


def _safe_error(error: Exception) -> dict[str, str]:
    if isinstance(error, UnknownSemanticViewError):
        return {
            "error": "unknown_semantic_view",
            "message": "The logical query used an unknown semantic view.",
        }
    if isinstance(error, MultipleSemanticViewsError):
        return {
            "error": "multiple_semantic_views",
            "message": "The logical query mixed semantic views.",
        }
    if isinstance(error, QueryValidationError):
        return {
            "error": "query_validation_error",
            "message": "The logical query was rejected.",
        }
    if isinstance(error, QueryExecutionError):
        return {
            "error": "query_execution_error",
            "message": "The logical query could not be executed.",
        }
    raise error


def create_query_database_tool(
    *,
    tenant: TenantContext,
    settings: Settings,
    query_executor: QueryExecutor = query_database,
) -> StructuredTool:
    """Bind private server context and expose only logical_sql to the model."""

    def execute(logical_sql: str) -> str:
        try:
            result = query_executor(logical_sql, tenant=tenant, settings=settings)
        except (
            QueryValidationError,
            UnknownSemanticViewError,
            MultipleSemanticViewsError,
            QueryExecutionError,
        ) as error:
            return json.dumps(_safe_error(error), ensure_ascii=False)
        return result.model_dump_json()

    return StructuredTool.from_function(
        func=execute,
        name="query_database",
        description=(
            "Execute one read-only logical query against the authorized store's "
            "semantic data layer. Use only ventas, venta_lineas or productos."
        ),
        args_schema=LogicalQueryInput,
    )
