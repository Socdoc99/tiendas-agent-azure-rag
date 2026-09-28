# Architecture

## Product architecture

Tiendas Agent answers operational questions from the authenticated shop's TiendasON data. SQL Server is the primary source for sales, tickets, products, prices, and inventory. Azure AI Search is retained for a later documentation source and must not block POS analytics.

```text
Browser
  -> FastAPI customer chat
  -> LangGraph
       -> LLMProvider (OpenAIProvider; gpt-5-mini)
       -> query_database(logical_sql)
            -> semantic view (ventas | venta_lineas | productos)
            -> readonly SQL Server
```

The server constructs an immutable `TenantContext` from server-side business and establishment configuration. The compiler injects its parameters into a trusted semantic view. The LLM sees only the logical view names and `query_database` tool contract, never physical tables, schemas, or tenant identifiers.

## Semantic grains

- `ventas`: one row per active ticket; use stored `total_facturado` and ticket count.
- `venta_lineas`: one row per sold product line; use for product/category rankings and units sold.
- `productos`: one row per active current product; use for current price and inventory only.

One logical query may use exactly one semantic view. Queries requiring multiple grains are separate tool calls. The semantic definitions may use trusted physical joins internally.

## Runtime isolation

The query engine validates a single readonly T-SQL `SELECT`, resolves its one semantic view through an allowlist, compiles the trusted definition as a CTE, injects the server-side tenant, binds values as parameters, and fetches at most `SQL_MAX_ROWS + 1` rows to report truncation. SQL uses `ApplicationIntent=ReadOnly` and an ODBC readonly connection.

## Transition state

The repository currently contains the earlier document-RAG application. Keep that implementation isolated from the POS path while importing the validated prototype in small phases. Remove old Foundry runtime code only after the OpenAI replacement and equivalent regression tests pass. Azure AI Search and Blob remain available for a later `search_documents` capability.

## Azure

Reuse the existing sandbox resource group and core data resources. Phase 2A is complete. Phase 2B is blocked by Container Apps capacity in `eastus`; local development continues independently. Phase 9 cannot start until the existing Environment is operational and no deployment is active.
