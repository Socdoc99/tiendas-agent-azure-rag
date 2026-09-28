# Database connection

**Status: IMPLEMENTED (SQL Server readonly connector).**

`connection.py` opens SQL Server connections with readonly intent, ODBC readonly mode, and a bounded query timeout. SQL username/password configuration stays outside source; the password is resolved by secret name from Key Vault. No secret values or full connection strings belong in this repository.

Queries must come through the query engine with the validated server-side `TenantContext` whenever tenant-scoped data is accessed. Do not connect directly from the agent or HTTP handler. See [security](../../docs/SECURITY.md) and [architecture](../../docs/ARCHITECTURE.md).
