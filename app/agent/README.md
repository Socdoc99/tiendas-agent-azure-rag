# Agent orchestration

**Status: IMPLEMENTED (local graph and chat service).**

`graph.py` builds the LangGraph loop. `instructions.py` contains the Spanish business contract; `tools.py` exposes only `query_database(logical_sql)`. The graph binds strict tool arguments and sets `parallel_tool_calls=False`.

Each question allows at most 10 database queries. The server binds immutable `TenantContext` and settings to the tool. The agent cannot choose the tenant, receive tenant IDs, or access physical SQL directly. The query engine validates the logical query and performs tenant-scoped readonly SQL.

Tool outputs, provider errors, SQL details, tenant identifiers, and tracebacks must not reach the user. The public chat service stores only user/assistant text.

The HTTP route/UI migration is planned for Phase 8. See [semantic rules](../../docs/SEMANTIC_MODEL.md), [security](../../docs/SECURITY.md), and [architecture](../../docs/ARCHITECTURE.md).
