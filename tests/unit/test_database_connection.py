from unittest.mock import Mock, patch

from app.core.config import Settings
from app.database.connection import _connection_string, database_connection


def test_connection_string_is_escaped_and_readonly() -> None:
    settings = Settings(
        sql_server="server;name",
        sql_database="sales}db",
        sql_username="readonly-user",
        sql_driver="ODBC Driver 18 for SQL Server",
    )

    connection_string = _connection_string(settings, "secret-password")

    assert "SERVER={server;name}" in connection_string
    assert "DATABASE={sales}}db}" in connection_string
    assert "ApplicationIntent=ReadOnly" in connection_string
    assert "Encrypt=yes" in connection_string
    assert "PWD={secret-password}" in connection_string


def test_database_connection_closes_connection_and_uses_key_vault_password() -> None:
    settings = Settings(
        sql_server="server",
        sql_database="database",
        sql_username="readonly-user",
        azure_key_vault_url="https://vault.example.test/",
    )
    connection = Mock()

    with (
        patch("app.database.connection.KeyVaultSecretProvider") as provider,
        patch("app.database.connection.pyodbc.connect", return_value=connection) as connect,
    ):
        provider.return_value.get_secret_value.return_value = "secret-password"
        with database_connection(settings) as active_connection:
            assert active_connection is connection
            assert connection.timeout == settings.sql_query_timeout_seconds

    provider.return_value.get_secret_value.assert_called_once_with("sql-password")
    assert connect.call_args.kwargs["readonly"] is True
    assert connect.call_args.kwargs["timeout"] == settings.sql_query_timeout_seconds
    connection.close.assert_called_once()


def test_database_connection_closes_on_query_error() -> None:
    settings = Settings(
        sql_server="server",
        sql_database="database",
        sql_username="readonly-user",
        azure_key_vault_url="https://vault.example.test/",
    )
    connection = Mock()

    with (
        patch("app.database.connection.KeyVaultSecretProvider") as provider,
        patch("app.database.connection.pyodbc.connect", return_value=connection),
    ):
        provider.return_value.get_secret_value.return_value = "secret-password"
        try:
            with database_connection(settings):
                raise RuntimeError("test")
        except RuntimeError:
            pass

    connection.close.assert_called_once()
