# Agent instructions — Tiendas Agent

## Product and architecture

- The product serves TiendasON customers: shop owners and establishment administrators.
- The MVP core is tenant-scoped POS analytics through `query_database`, semantic views, and readonly SQL Server.
- Azure AI Search is retained for future documentation lookup. Do not make it a dependency of POS analytics or `/ready`.
- Microsoft Foundry must not be a target runtime dependency. Preserve existing Foundry code/resources until the replacement is tested; do not modify Foundry resources or model deployments.

## Validated prototype source

- The local `Agente IA TiendasON` prototype is the implementation source. Inspect and copy only the code/tests needed for each migration phase.
- Never modify the prototype, migrate its Git history, copy its `.git` or `.env`, or copy credentials, tokens, connection strings, or old Azure resources.
- Do not reconstruct behavior from memory. Use source code and regression tests as evidence.

## Tenant and SQL safety

- `TenantContext` is immutable and built server-side from demo/business configuration. Validate that the establishment belongs to the configured business before queries.
- The browser and model cannot provide or override tenant IDs.
- Only semantic views `ventas`, `venta_lineas`, and `productos` are exposed. One query may reference exactly one distinct view.
- Reject physical tables/schemas, DDL/DML, multiple statements, external access, metadata queries, and unknown semantic views.
- Use parameterized SQL, readonly ODBC with `ApplicationIntent=ReadOnly`, query timeout, `SQL_MAX_ROWS=200` by default, and fetch `max_rows + 1` for truncation detection.
- Never use current cost for historical profit/margin. Unsupported domains must be declined plainly.
- Retrieve SQL/OpenAI credentials from Key Vault. Do not put secret values in `.env`, code, tests, logs, or Git.

## Cloud and deployment boundaries

- Use existing Azure resources only. Do not create a Resource Group or recreate core services.
- Before infrastructure changes, refresh the ARM deployment and Container Apps Environment. Never start a parallel deployment while ARM is `Running` or the Environment is `Updating`.
- Require `az deployment group what-if` before future Bicep deployments.
- Do not start Phase 9 until Phases 3–8 pass and the existing Environment is operational.
- Use the existing Foundry account/project read-only; never alter its model deployment.

## Workflow

1. Work on `develop`; `main` is stable and must not receive direct development or merges.
2. Inspect the current code and source prototype before edits.
3. Migrate in small phases and preserve existing behavior unless the master instruction says otherwise.
4. Run focused tests, applicable suite, lint, and `git diff --check`.
5. Update `IMPLEMENTATION_LOG.md` after every phase and distinguish implemented from future work.
6. Use small Conventional Commits and push `origin/develop` when appropriate.

Read `CODEX_IMPLEMENTATION_MASTER_TIENDAS_AGENT.md`, `docs/SEMANTIC_MODEL.md`, `docs/SECURITY.md`, and `docs/MIGRATION.md` before relevant changes.
