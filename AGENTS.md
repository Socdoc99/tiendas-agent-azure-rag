# Agent operating rules — Tiendas Agent

## Source of truth and document hierarchy

Use each document for its stated purpose:

1. [`CODEX_IMPLEMENTATION_MASTER_TIENDAS_AGENT.md`](CODEX_IMPLEMENTATION_MASTER_TIENDAS_AGENT.md) — master implementation plan and phase scope.
2. `AGENTS.md` — current operating rules for agents working in this repository.
3. [`README.md`](README.md) — product overview and developer entry point.
4. [`docs/`](docs/) — detailed architecture, security, semantic, migration, and operational documentation.
5. Local `README.md` files — concise boundaries and context for their module or directory.
6. `reference/` — historical evidence only, when present; never treat it as current runtime behavior.

Current code and regression tests establish implemented behavior. The master plan establishes intended phase scope. Keep the documents consistent and identify planned work as planned. Do not treat old snapshots or prototype documentation as current behavior.

## Product and current runtime

Tiendas Agent is a customer-facing TiendasON product for authorized shop owners and establishment administrators. The MVP answers questions about sales, tickets, products, prices, and current inventory using TiendasON SQL Server data.

The MVP core is the server-side tenant boundary, semantic layer, and readonly SQL query engine. The POS agent uses LangGraph and exposes `query_database(logical_sql)` as its primary business-data tool. The local POS agent and domain modules are implemented; the HTTP chat and browser UI still serve the earlier document-RAG flow until the planned UI phase connects them. Do not describe that UI migration as complete.

```text
Customer request
  -> server-side immutable TenantContext
  -> LangGraph agent / LLMProvider
  -> query_database(logical_sql)
  -> semantic view (one per query)
  -> validated, tenant-scoped readonly SQL Server query
```

`ventas`, `venta_lineas`, and `productos` are the only semantic views exposed to the model. Azure AI Search is a future documentation-RAG capability; it is not a dependency of POS analytics or readiness. Container Apps application runtime (Phase 2B) remains pending because of regional capacity, but it does not block local work on Phases 3–8. Do not start Phase 9 until the existing Container Apps Environment is operational and its phase gates are met.

Microsoft Foundry is not part of the current POS runtime and there is no fallback to Foundry. Do not change the existing Foundry resources or deployments as part of POS work. The earlier document-RAG path may still contain its own provider code; do not confuse it with the POS provider path or route POS queries through it.

## Model provider and secrets

- The LangGraph agent depends on the `LLMProvider` boundary. `OpenAIProvider` is the current POS provider implementation.
- `OPENAI_CHAT_MODEL` is configurable; `.env.example` currently sets `gpt-5-mini`. Do not change the configured model without an explicit task instruction.
- Resolve the OpenAI API key from Azure Key Vault using the configured secret name (`openai-api-key` by default). Never put secret values in source, `.env.example`, tests, logs, terminal output, or Git. Local `.env` files are ignored and must be configured separately.
- Provider initialization or request failures must be surfaced safely. Never add an automatic fallback to Microsoft Foundry or another model.
- The LLM receives neither SQL credentials nor tenant IDs. Keep prompts and tool outputs free of secrets, physical SQL, PII, and unnecessary tenant details.

## Tenant isolation and query boundary

- Construct immutable `TenantContext` on the server from approved business and establishment configuration. Validate that the establishment belongs to the configured business before running tenant-scoped queries.
- Never accept or allow the browser, user prompt, chat history, or model tool arguments to select or override `BusinessId` or `EstablishmentId`.
- `query_database(logical_sql)` is the agent's only business-data tool. Keep its argument strict and tenant-free. Handle database tool calls sequentially with `parallel_tool_calls=False` and a hard maximum of 10 `query_database` calls per user question.
- Permit exactly one distinct semantic view per logical query: `ventas`, `venta_lineas`, or `productos`. For a question spanning multiple grains, issue separate tool calls. Trusted physical joins internal to a view definition are governed by that view.
- Validate and compile logical SQL before execution. Reject physical table/schema access, DDL/DML, multiple statements, external-access functions, metadata queries, unknown views, and unsupported constructs. Do not bypass the validator/compiler or expose physical SQL to the model.
- SQL Server connections must be readonly (`ApplicationIntent=ReadOnly` and ODBC readonly mode), parameterized, and bounded by a query timeout and `SQL_MAX_ROWS` (default 200). Fetch at most `max_rows + 1` to detect truncation.
- Do not use current product cost to calculate historical profit or margin. Decline unsupported business domains clearly.

Read [`docs/SEMANTIC_MODEL.md`](docs/SEMANTIC_MODEL.md) before changing business metrics, semantic definitions, or query behavior. Read [`docs/SECURITY.md`](docs/SECURITY.md) before changing tenant, SQL, provider, or secret handling.

## Azure resources, identity, and deployment

- Use only the existing Azure resource group and resources for tasks that explicitly require Azure. Do not create or delete resources, change model deployments, or alter tenants/subscriptions unless the task expressly directs that operation.
- Apply RBAC least privilege: grant only the required data-plane action at the narrowest practical scope. Do not infer that subscription `Owner` grants Key Vault, Search, or Blob data-plane access. Do not make RBAC changes unless explicitly requested.
- Phase 2A core infrastructure is deployed; Phase 2B Container Apps is pending regional capacity. Its pending state does not block local development. Azure AI Search is reserved for future documentation RAG, not the POS query path.
- Before any Bicep operation, refresh the remote deployment and Container Apps Environment state. Do not start a parallel deployment while the existing deployment is `Running` or the Environment is `Updating`. Run `az deployment group what-if` before a deployment. Follow the documented single `eastus2` capacity retry only if the existing Environment has reached terminal `Failed` specifically for regional capacity; keep `dataLocation` and existing data resources in place. Never create a new Resource Group for this recovery.
- Do not start Phase 9 until the existing Container Apps Environment is operational and the required preceding phase gates have passed. Consult [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) and the implementation log before cloud work.
- Do not access production business data or run remote smoke scripts without the approved readonly configuration and authorization. Do not expose live business data in output.

## Legacy and historical material

The earlier local `Agente IA TiendasON` prototype is a read-only implementation reference for the tenant, SQL, semantic, query-engine, LangGraph, and chat modules. Never modify that prototype, migrate its Git history, or copy its `.git`, `.env`, credentials, tokens, connection strings, or unrelated Azure resources. Prototype-era Azure VM, nginx, and Foundry Hosted Agent instructions do not describe this repository's current POS runtime.

Treat `reference/` as historical evidence only if it exists in the checkout. Do not use snapshots or old plans as runtime truth when they conflict with current code, tests, or maintained `docs/`. Do not preserve or relocate a legacy `AGENTS.md` into this repository unless a task specifically asks for it; if one is ever retained, mark it clearly as legacy and state that it does not describe the current runtime.

## Stop conditions

Stop before an operation if the required choice could change tenant scope, business data, architecture, model, subscription, permissions, or Azure resources and the approved value is not explicit. Report the exact missing decision and preserve the safe state. Do not work around denied permissions by changing identity configuration or RBAC. Missing Container Apps capacity is not a reason to stop authorized local development on Phases 3–8.

## Development, documentation, and Git workflow

1. Work on `develop`; `main` is stable. Never develop directly on `main` or merge to it unless a separate task explicitly authorizes that release action.
2. Read this file, the master implementation plan, the root README, and the relevant local README and `docs/` before editing. Inspect current implementation and tests; keep changes within the requested scope.
3. Make the smallest change that completes the task. Do not add future-phase behavior or broad refactors without a demonstrated requirement.
4. Run focused tests and the applicable suite for functional changes. The standard suite is `python -m pytest`; run `python -m unittest discover -s tests -v` when the task or project checks require it. Run relevant lint and `git diff --check`. Do not run live SQL, OpenAI, or Azure smoke tests without the approved configuration and authorization.
5. Update `IMPLEMENTATION_LOG.md` for phase results, including scope, verification, Azure changes (if any), blockers, and next action. Do not mark a phase complete on the strength of mocks alone when its stated live gate remains unmet.
6. Keep module `README.md` files short and focused on module responsibilities and links to detailed docs. Update the relevant docs when implementation behavior changes.
7. Review `git diff`, `git diff --check`, and `git status` before committing. Create small, descriptive Conventional Commits only when requested or required by the task. Push to the requested remote/branch when requested; preserve configured remotes and do not change the upstream of `main`.
