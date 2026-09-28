"""AST-based validation for caller-provided T-SQL."""

from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError, TokenError
from sqlglot.optimizer.scope import Scope, traverse_scope

from app.query_engine.models import (
    MultipleSemanticViewsError,
    QueryValidationError,
    UnknownSemanticViewError,
)
from app.query_engine.registry import SEMANTIC_VIEWS

_EXTERNAL_ACCESS_FUNCTIONS = {
    "OPENROWSET",
    "OPENQUERY",
    "OPENDATASOURCE",
    "OPENXML",
}

_SYSTEM_METADATA_FUNCTIONS = {
    "APP_NAME",
    "CURRENT_USER",
    "DATABASEPROPERTYEX",
    "DB_ID",
    "DB_NAME",
    "FILE_ID",
    "FILE_IDEX",
    "FILE_NAME",
    "FILEGROUP_ID",
    "FILEGROUP_NAME",
    "FILEGROUPPROPERTY",
    "FILEPROPERTY",
    "FULLTEXTSERVICEPROPERTY",
    "HOST_ID",
    "HOST_NAME",
    "OBJECT_DEFINITION",
    "OBJECT_ID",
    "OBJECT_NAME",
    "ORIGINAL_LOGIN",
    "SCHEMA_ID",
    "SCHEMA_NAME",
    "SERVERPROPERTY",
    "SESSION_USER",
    "SUSER_ID",
    "SUSER_NAME",
    "SYSTEM_USER",
    "USER_ID",
    "USER_NAME",
}


@dataclass(frozen=True)
class ValidatedQuery:
    expression: exp.Query
    semantic_view: str


def _function_name(function: exp.Func) -> str:
    if isinstance(function, exp.Anonymous):
        return function.name.upper()
    return function.sql_name().upper()


def validate_logical_sql(logical_sql: str) -> ValidatedQuery:
    """Parse and enforce the readonly semantic SQL subset."""

    if not isinstance(logical_sql, str) or not logical_sql.strip():
        raise QueryValidationError("Logical SQL must be a non-empty string")

    try:
        statements = parse(logical_sql, read="tsql")
    except (ParseError, TokenError) as error:
        raise QueryValidationError("Logical SQL could not be parsed") from error

    if len(statements) != 1:
        raise QueryValidationError("Exactly one SQL statement is required")

    expression = statements[0]
    if not isinstance(expression, exp.Query):
        raise QueryValidationError("Only SELECT queries are allowed")
    if expression.find(exp.Into):
        raise QueryValidationError("SELECT INTO is not allowed")
    if expression.find(exp.Parameter) or expression.find(exp.Placeholder):
        raise QueryValidationError("Caller-provided SQL parameters are not allowed")
    if expression.find(exp.NextValueFor):
        raise QueryValidationError("Sequence access is not allowed")

    for function in expression.find_all(exp.Func):
        function_name = _function_name(function)
        if function_name in _EXTERNAL_ACCESS_FUNCTIONS:
            raise QueryValidationError("External data access is not allowed")
        if function_name in _SYSTEM_METADATA_FUNCTIONS:
            raise QueryValidationError("System metadata access is not allowed")

    for dot in expression.find_all(exp.Dot):
        if isinstance(dot.expression, exp.Func):
            raise QueryValidationError("Schema-qualified functions are not allowed")

    for cte in expression.find_all(exp.CTE):
        name = cte.alias.lower()
        if not name:
            raise QueryValidationError("Every CTE must have a name")
        if name in SEMANTIC_VIEWS:
            raise QueryValidationError(
                "CTE names cannot shadow reserved semantic views"
            )

    used_views: set[str] = set()
    for scope in traverse_scope(expression):
        for table in scope.tables:
            cte_source = next(
                (
                    candidate
                    for alias, candidate in scope.cte_sources.items()
                    if alias.lower() == table.name.lower()
                ),
                None,
            )
            if isinstance(cte_source, Scope):
                continue
            if table.catalog or table.db:
                raise UnknownSemanticViewError(
                    "Qualified, cross-database, and physical tables are not allowed"
                )
            if not isinstance(table.this, exp.Identifier):
                raise QueryValidationError("Table-valued functions are not allowed")
            if table.this.args.get("temporary") or table.this.args.get("global_"):
                raise QueryValidationError("Temporary tables are not allowed")

            name = table.name.lower()
            if name in SEMANTIC_VIEWS:
                used_views.add(name)
            else:
                raise UnknownSemanticViewError(
                    "Only registered semantic views and local CTEs are allowed"
                )

    if not used_views:
        raise UnknownSemanticViewError(
            "The query must reference one registered semantic view"
        )
    if len(used_views) > 1:
        raise MultipleSemanticViewsError(
            "The MVP allows exactly one distinct semantic view per statement"
        )

    return ValidatedQuery(expression=expression, semantic_view=used_views.pop())
