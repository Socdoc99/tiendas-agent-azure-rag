"""Readonly execution entrypoint for logical semantic SQL."""

import pyodbc

from app.core.config import Settings
from app.database.connection import database_connection
from app.query_engine.compiler import compile_query
from app.query_engine.models import QueryExecutionError, QueryResult, normalize_value
from app.tenant import TenantContext


def query_database(
    logical_sql: str,
    tenant: TenantContext,
    settings: Settings,
) -> QueryResult:
    """Validate, compile, and execute logical SQL for one server-side tenant."""

    compiled = compile_query(logical_sql, tenant)
    if settings.sql_max_rows < 1:
        raise QueryExecutionError("SQL_MAX_ROWS must be greater than zero")

    try:
        with database_connection(settings) as connection:
            cursor = connection.cursor()
            cursor.execute(compiled.sql, *compiled.parameters)
            columns = [str(column[0]) for column in cursor.description]
            fetched = cursor.fetchmany(settings.sql_max_rows + 1)
    except pyodbc.Error as error:
        raise QueryExecutionError("The database query could not be executed") from error

    truncated = len(fetched) > settings.sql_max_rows
    visible_rows = fetched[: settings.sql_max_rows]
    rows = [[normalize_value(value) for value in row] for row in visible_rows]
    return QueryResult(
        columns=columns,
        rows=rows,
        row_count=len(rows),
        truncated=truncated,
    )
