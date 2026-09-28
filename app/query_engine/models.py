"""Small public and internal contracts for the logical query engine."""

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class QueryValidationError(ValueError):
    """Raised when caller-provided logical SQL is outside the safe subset."""


class UnknownSemanticViewError(QueryValidationError):
    """Raised when logical SQL refers to a table outside the semantic registry."""


class MultipleSemanticViewsError(QueryValidationError):
    """Raised when one statement mixes semantic grains in the MVP."""


class QueryExecutionError(RuntimeError):
    """Raised with a safe message when SQL Server cannot execute a query."""


JsonScalar = str | int | float | bool | None


class QueryResult(BaseModel):
    """Serializable result exposed to the future LLM tool."""

    model_config = ConfigDict(frozen=True)

    columns: list[str]
    rows: list[list[JsonScalar]]
    row_count: int
    truncated: bool


@dataclass(frozen=True)
class CompiledQuery:
    """Internal executable SQL; never include this object in the tool response."""

    sql: str
    parameters: tuple[str, str]
    semantic_view: str


def normalize_value(value: object) -> JsonScalar:
    """Convert database values to JSON-safe scalars without losing precision."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    return str(value)
