# Application modules

**Status: IMPLEMENTED (POS domain modules); PARTIAL (HTTP chat wiring).**

`app/` contains the FastAPI service and the POS agent building blocks. The API and browser still serve the document-RAG flow until Phase 8 connects the POS chat service.

- `agent/` orchestrates the model and the single business-data tool.
- `llm/` defines the model-provider boundary and OpenAI implementation.
- `tenant.py`, `semantic/`, `query_engine/`, and `database/` enforce tenant-scoped readonly SQL.
- `api/`, `services/`, and `static/` currently include the earlier document-RAG routes and UI.

The agent depends on the LLM interface and query engine. Only the query engine may compile SQL; the model provider does not receive database credentials or tenant IDs.

See [architecture](../docs/ARCHITECTURE.md), [security](../docs/SECURITY.md), and the [implementation plan](../CODEX_IMPLEMENTATION_MASTER_TIENDAS_AGENT.md).
