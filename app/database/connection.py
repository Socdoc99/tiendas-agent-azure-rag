"""Readonly SQL Server connection management."""

from collections.abc import Iterator
from contextlib import contextmanager

import pyodbc

from app.core.config import Settings, get_settings
from app.services.secret_provider import KeyVaultSecretProvider


def _odbc_value(value: str) -> str:
    """Escape an ODBC connection-string value without logging it."""

    return "{" + value.replace("}", "}}") + "}"


def _connection_string(settings: Settings, password: str) -> str:
    return ";".join(
        (
            f"DRIVER={_odbc_value(settings.sql_driver)}",
            f"SERVER={_odbc_value(settings.sql_server)}",
            f"DATABASE={_odbc_value(settings.sql_database)}",
            f"UID={_odbc_value(settings.sql_username)}",
            f"PWD={_odbc_value(password)}",
            "Encrypt=yes",
            "TrustServerCertificate=yes",
            "ApplicationIntent=ReadOnly",
        )
    )


@contextmanager
def database_connection(
    settings: Settings | None = None,
) -> Iterator[pyodbc.Connection]:
    """Open and always close a readonly SQL Server connection."""

    active_settings = settings or get_settings()
    required = (
        active_settings.sql_server,
        active_settings.sql_database,
        active_settings.sql_username,
        active_settings.azure_key_vault_url,
    )
    if not all(value.strip() for value in required):
        raise RuntimeError("SQL Server and Key Vault settings are required")
    password = KeyVaultSecretProvider(active_settings).get_secret_value(
        active_settings.sql_password_secret_name
    )
    connection = pyodbc.connect(
        _connection_string(active_settings, password),
        timeout=active_settings.sql_query_timeout_seconds,
        readonly=True,
    )
    connection.timeout = active_settings.sql_query_timeout_seconds
    try:
        yield connection
    finally:
        connection.close()
