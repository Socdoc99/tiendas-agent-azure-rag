# Tiendas Agent

Tiendas Agent is a customer-facing TiendasON assistant for an authorized shop owner or establishment administrator to ask questions about their own sales, tickets, products, prices, and inventory.

## Product direction

The MVP's primary data source is TiendasON's operational SQL Server, queried through a tenant-scoped semantic layer and a readonly query engine. Azure AI Search remains deployed for a later documentation feature; it is not part of POS analytics' critical path. Microsoft Foundry is not a runtime dependency for the target architecture.

```text
Customer chat -> FastAPI -> LangGraph agent -> query_database
                                      -> semantic views -> readonly SQL Server
```

The locally validated prototype `Agente IA TiendasON` is the source of implementation for the tenant, database, semantic, query engine, agent, chat, and UI modules. The prototype is read-only reference material and must not be modified. Never copy its `.git`, `.env`, credentials, or tokens.

## Current migration status

- Phases 0, 1, and 2A are complete; Phase 2B Container Apps is pending regional capacity.
- Architecture rebaseline is recorded in [`IMPLEMENTATION_LOG.md`](IMPLEMENTATION_LOG.md).
- Phase 3 imports the domain layer from the prototype. Later phases migrate orchestration, replace Foundry with OpenAI, validate readonly SQL, add evaluation, and migrate the customer UI.
- The repository still contains the previous document-RAG implementation. Keep it out of the POS query path and do not remove it until the replacement is tested.
- Do not begin Phase 9 until the existing Container Apps Environment is operational.

## Local development

Use Python 3.11 or newer. Never copy the prototype's local `.env`; configure this checkout separately. SQL connection credentials must come from Key Vault at runtime. Demo tenant IDs are server-side configuration and must never be accepted from a chat request or model tool arguments.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Run focused tests with `python -m pytest`. Do not run database smoke scripts until the approved SQL credentials and tenant configuration are present. Such scripts are read-only but query live business data.

## Azure boundaries

Use the existing `rg-tiendas-agent-sbx` and existing data resources. Do not recreate resources or change the existing Foundry account, project, or model deployment. Refresh the ARM deployment and Container Apps Environment state before any infrastructure change; do not deploy while the deployment is `Running` or the Environment is `Updating`. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Semantic model](docs/SEMANTIC_MODEL.md)
- [Security](docs/SECURITY.md)
- [Migration](docs/MIGRATION.md)
- [Roadmap](docs/ROADMAP.md)
- [Implementation log](IMPLEMENTATION_LOG.md)
- [Master implementation instruction](CODEX_IMPLEMENTATION_MASTER_TIENDAS_AGENT.md)
