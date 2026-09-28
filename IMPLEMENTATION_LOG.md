# Implementation log

## Phase 0 — Preflight

**Status:** PASS
**Date:** 2026-09-28 11:46 COT

### Changes

- Created `IMPLEMENTATION_LOG.md`.

### Azure resources

- Created or modified: none.
- Subscription: `Azure subscription 1` (`6be99cce-254f-4377-9907-416ffe20833c`).
- Resource group: `rg-tiendas-agent-sbx`, `eastus`, `Succeeded`.
- Foundry account: `ai-tiendas-agent-sbx-k7m4p2`, `AIServices`, `Succeeded`.
- Foundry project: `tiendason-agent-sbx`, `Succeeded`.
- Providers: `Microsoft.CognitiveServices`, `Microsoft.ContainerRegistry`, `Microsoft.Compute`, `Microsoft.ManagedIdentity`, and `Microsoft.Network` are all `Registered`.
- RBAC: `Owner` at subscription scope for `santiago9902@hotmail.com` (two matching assignments returned by Azure).
- Foundry/model deployment: read-only checks only; no model deployment was touched.

### Toolchain

- Azure CLI: `2.90.0`.
- Azure Developer CLI: `1.34.2`.
- `microsoft.foundry`: `1.0.0-beta.2`, installed and up to date.
- `azd ai agent version`: `1.0.0-beta.16`.
- `azd ai project version`: `1.0.0-beta.11`.
- `azd ai connection version`: `dev`.
- Docker client and server: `29.8.0`.
- Python: `3.11.9` (`py -3.11`).

### Commands and checks

- `az login --tenant 8d436e95-814f-4786-bc1b-9f0d627ca3bd --scope https://management.core.windows.net//.default` — PASS via interactive browser login as `santiago9902@hotmail.com`.
- Device-code login returned `AADSTS530035`; no tenant security setting was changed. The normal Windows interactive login succeeded.
- `az account set --subscription 6be99cce-254f-4377-9907-416ffe20833c` and `az account show` — PASS.
- `azd auth logout`, `azd auth login --tenant-id 8d436e95-814f-4786-bc1b-9f0d627ca3bd`, and `azd auth login --check-status` — PASS as `santiago9902@hotmail.com`.
- `azd config set defaults.subscription 6be99cce-254f-4377-9907-416ffe20833c` — PASS; value verified.
- `az group show`, `az cognitiveservices account show`, `az cognitiveservices account project show`, provider queries, and `az role assignment list` — PASS.
- `docker version`, `py -3.11 --version`, and `git status` — PASS; repository was clean on `develop` before this log was added.

### Decisions and issues

- The alternative account `santiago.ospina@onoff.com.co` is not present in the tenant. No guest user was added; the target Hotmail account authenticated successfully instead.
- The Foundry account and project remain read-only, and no model setting or deployment changed.

### Next action

- Phase 1: bootstrap the application and verify its local tests, lint, and Docker build.

## Phase 1 — Application bootstrap

**Status:** PASS
**Date:** 2026-09-28 11:53 COT

### Changes

- Added the FastAPI application, settings, structured request logging, typed service errors, health/readiness routes, and Pydantic request/metadata/search schemas.
- Added dependency manifests, `.env.example`, Git/Docker ignore rules, Dockerfile, Makefile, initial README, and architecture/security/deployment/data/runbook docs.
- Docker runs the service as an unprivileged `app` user.
- Added unit coverage for health/readiness and request/document schemas.

### Azure resources

- Created or modified: none.
- The model names remain unset and are required runtime configuration; no model name was invented.

### Tests and validation

- `.venv\\Scripts\\python.exe -m pytest -v` — PASS, 5 tests.
- `.venv\\Scripts\\ruff.exe check .` — PASS.
- `git diff --check` — PASS.
- `docker build -t tiendas-agent-azure-rag:phase1 .` — PASS using Python 3.12 image.
- Ran the image as a container; `/health` returned `{"status":"ok"}` and the container user was `app` — PASS.

### Decisions and issues

- Local tests run on Python 3.11.9; the container uses Python 3.12 as specified by the plan.
- `/ready` currently checks required configuration only. Low-cost connectivity checks for Azure services are added with their integration phases.

### Next action

- Phase 2: declare the core Azure resources in Bicep and validate the deployment plan against the existing resource group before deployment.

## Phase 2A — Core Infrastructure

**Status:** PASS
**Date:** 2026-09-28 12:04 COT

### Changes

- Added `infra/core.bicep` and modules for Azure AI Search, private Blob Storage, Key Vault, ACR, monitoring, and a Consumption Container Apps Environment.
- Registered the providers required by this phase: `Microsoft.Search`, `Microsoft.Storage`, `Microsoft.KeyVault`, `Microsoft.App`, `Microsoft.OperationalInsights`, and `Microsoft.Insights`. ACR and Authorization were already registered.
- Installed Bicep CLI `0.47.16` locally.

### Azure resources

- Successfully created in the existing resource group:
  - `srch-tiendas-agent-sbx-k7m4p2` — Azure AI Search Free, `Succeeded`.
  - `sttiendasagentsbxk7m4p2` and private `knowledge` container — Standard LRS, `Succeeded`.
  - `kv-tiendas-sbx-k7m4p2` — Standard, RBAC enabled, `Succeeded`.
  - `acrtiendasagentsbxk7m4p2` — Basic, admin account disabled, `Succeeded`.
  - `log-tiendas-agent-sbx` — 30-day retention and 1 GB/day ingestion cap, `Succeeded`.
- `appi-tiendas-agent-sbx` — workspace-based, `Succeeded`.
- The Search, Storage, Key Vault, ACR, Log Analytics, and Application Insights resources are in the existing resource group and remain the targets for local execution.
- The existing Foundry account and project were `Ignore` in `what-if`; neither was changed. No model deployment was touched.

### Commands and checks

- `az bicep build --file infra/core.bicep --stdout` — PASS.
- `az deployment group validate` — PASS.
- `az deployment group what-if` — 9 creates, 2 existing Foundry resources ignored; Search Free, ACR Basic, Storage Standard LRS, Consumption environment.
- `az deployment group create` — PARTIAL; failed only while allocating the Container Apps Environment in `eastus` due Azure regional capacity.
- Resource state queries confirmed the six core services listed above as `Succeeded`.

### Exit criteria

- Core data and observability resources are deployed successfully.
- The Foundry account/project and model deployment were not changed.
- This phase is separate from the Container Apps runtime Environment.

## Phase 2B — Application Runtime

**Status:** PENDING — regional capacity
**Last remote check:** 2026-09-28

### Azure resources

- ARM deployment `tiendas-agent-env-retry` now reports terminal `Failed`; the deployment operation timed out (`DeploymentFailed`).
- Existing `cae-tiendas-agent-sbx` in `eastus` still reports `Updating`, with the earlier `ManagedEnvironmentCapacityHeavyUsageError` / `AKSCapacityHeavyUsage` capacity error.
- No parallel deployment has been started. Do not start one while the deployment is `Running` or the Environment is `Updating`.
- No Container App has been created.
- Key Vault metadata listing and secret retrieval were denied by RBAC (`ForbiddenByRbac`, missing `Microsoft.KeyVault/vaults/secrets/readMetadata/action`). This does not establish whether `openai-api-key` exists. No secret value was returned or exposed, and no RBAC was changed.
- Resource-scope RBAC queries resolved the signed-in guest by object ID and found only two inherited `Owner` assignments at subscription scope. No Search, Storage Blob, or Key Vault data-plane role is assigned at those scopes.

### Recovery plan

- Recheck the remote ARM deployment and Environment before every Azure operation.
- If the current deployment succeeds, use the existing Environment.
- If it fails specifically because of regional capacity, run `what-if` first and make exactly one Environment attempt in `eastus2` using `appLocation=eastus2`. Keep `dataLocation=eastus` so Search, Storage, Key Vault, ACR, Log Analytics, and Application Insights stay where they already are. Do not create another Resource Group.
- If the result is a different error, stop and inspect it before changing infrastructure.
- The current Environment is still `Updating`, so the eastus2 attempt remains on hold despite the ARM deployment's terminal failure.

## Previous document-RAG track — retained, not MVP core

**Status:** Code/tests retained during migration; this track is superseded as the primary product architecture

The repository contains a document-RAG implementation: Search index management, Blob document storage, extraction and chunking, ingestion, hybrid retrieval, grounded chat, and a browser chat UI. Retain this code until the POS replacement is functional and regression-tested, but do not make it the POS query path. Its former model settings (`text-embedding-3-small` / 1536 dimensions and `gpt-5.6-luna`) do not define the new POS runtime model.

The `.env` file remains local and ignored by Git; it contains no API key. `openai-api-key` existence could not be verified because Key Vault denies metadata and secret reads. Search document operations were forbidden; Blob ingestion and live model calls were not performed.

Do not create a Container App or begin Phase 9 until a Container Apps Environment is operational. The POS phases continue locally and do not depend on Search/Blob.

### Local verification

- `.venv\Scripts\python.exe -m pytest -v` — PASS, 16 tests.
- `.venv\Scripts\ruff.exe check .` — PASS.
- `git diff --check` — PASS.

## Previous Phase 3 — Azure AI Search

**Status:** PARTIAL — index created; data-plane document smoke test blocked by RBAC
**Date:** 2026-09-28 14:36 COT

- Created/updated `idx-tiendas-knowledge-v1` in the existing Search service with the approved 1536-dimension vector schema — PASS.
- Search service/index metadata read and schema creation succeeded with the current identity.
- Synthetic document upload was rejected with HTTP 403 Forbidden; the subsequent cleanup request was also denied and no synthetic record was written. Search document query was rejected with HTTP 403 Forbidden.
- Do not report data-plane read/write or `is_active` filter acceptance as verified. The identity needs an appropriate Azure AI Search data-plane role; no role assignment was changed.
- To complete this phase, grant the executing identity `Search Index Data Contributor` on the Search service (or equivalent read and write roles).

## Previous Phase 4 — Document pipeline

**Status:** IMPLEMENTED LOCALLY; live Azure ingestion pending data-plane and Key Vault access
**Date:** 2026-09-28 14:36 COT

- Implemented PDF, DOCX, TXT, and MD extraction, normalization, page-aware token chunking, SHA-256 deduplication, private Blob upload, embeddings, Search upload, update, and delete operations.
- Local parser/chunking and mocked idempotent ingestion tests pass.
- Live ingestion was not run: Search data-plane requests are forbidden, and the Key Vault secret `openai-api-key` could not be read. No sample document was supplied.
- For live ingestion, the identity also needs `Storage Blob Data Contributor` on the Storage account and `Key Vault Secrets User` on the vault; no assignments were made.

## Previous Phase 5 — Hybrid retrieval

**Status:** IMPLEMENTED LOCALLY; live retrieval validation pending Search data-plane access and embeddings
**Date:** 2026-09-28 14:36 COT

- Implemented query embeddings, keyword plus vector Search, active-document filtering, metadata filters, top-k selection, per-document limits, and non-production `/api/v1/debug/search`.
- Unit coverage verifies index schema, filter escaping, and active-document filter construction.
- Live Search document queries currently return HTTP 403; five-question relevance evaluation has not been run.

## Previous Phase 6 — RAG + LLM

**Status:** IMPLEMENTED LOCALLY; live model validation pending Key Vault secret access
**Date:** 2026-09-28 14:36 COT

- Implemented the provider adapter, grounded context builder, citation validation, `/api/v1/chat`, and no-answer behavior without a Foundry dependency.
- Approved models are `gpt-5.6-luna` and `text-embedding-3-small` (1536 dimensions); these values are in `.env.example` and the ignored local `.env`.
- Mocked tests cover valid citations and no-answer behavior. No live model call was made because Key Vault secret retrieval is denied.

## Previous Phase 7 — Guardrails and resilience

**Status:** LOCAL IMPLEMENTATION PASS
**Date:** 2026-09-28 14:36 COT

- Added strict request and metadata validation, upload and history limits, safe error responses, request IDs, provider timeouts, bounded transient retries, citation allowlisting, and prompt-injection instructions for retrieved content.
- Covered by the passing local test suite. Live dependency-failure behavior remains unverified while data-plane access is unavailable.

## Previous Phase 8 — Document chat UI

**Status:** LOCAL IMPLEMENTATION PASS
**Date:** 2026-09-28 14:36 COT

- Added the browser chat UI served by FastAPI, with loading/error states and source/page citations. The UI route test passes.
- A complete browser-to-Azure chat has not been demonstrated because Search data-plane and Key Vault access are blocked.

## Architecture Rebaseline — POS analytics is the MVP core

**Status:** COMPLETE
**Date:** 2026-09-28 15:00 COT

- Product scope reset to customer-facing analytics for an authorized TiendasON business/establishment.
- The local `Agente IA TiendasON` prototype was found, inspected read-only, and is clean on its `main` branch. It is the source of implementation for tenant, readonly database, semantic views, query engine, agent, chat, and UI.
- The prototype was unchanged during discovery. Phase 3 later copied only the listed application modules, regression tests, and readonly oracle scripts; no Git history, `.git`, `.env`, credentials, or legacy Azure resources were copied.
- SQL Server plus the `ventas`, `venta_lineas`, and `productos` semantic views is the target core. Azure AI Search/RAG is a later document capability and is not required by the POS path.
- Microsoft Foundry remains outside the target runtime; existing Foundry account/project/model deployments were not touched.
- Current target branch was `develop`, synchronized with `origin/develop` at commit `ec5a45d` before this rebaseline.
- Updated README, AGENTS, architecture, security, deployment, semantic model, migration, roadmap, data model, runbook, and master implementation instructions.

## Phase 3 — TiendasON domain import

**Status:** PASS — local regression suite; live SQL validation pending authorized configuration
**Date:** 2026-09-28 15:53 COT

### Changes

- Imported `app/tenant.py`, `app/database/`, `app/semantic/`, and `app/query_engine/` from the clean local prototype; adapted imports to the target settings module.
- Imported the prototype's focused query-engine and three semantic-view regression suites plus their readonly oracle-check scripts.
- Added SQL Server, business timezone, demo tenant, timeout, row-cap, and query-budget settings. SQL password is retrieved by secret name from Key Vault; it is not stored in Settings or `.env`.
- Added `pyodbc` and `sqlglot` dependencies and tenant/database connection tests.
- Updated README, AGENTS, architecture, security, deployment, data model, runbook, semantic model, migration plan, roadmap, and master implementation instructions for the POS analytics rebaseline.

### Verification

- Source regression tests: query engine + `ventas` + `venta_lineas` + `productos` — PASS, 33 tests.
- Tenant/database focused tests — PASS, 7 tests.
- Full `.venv\Scripts\python.exe -m pytest -q` — PASS, 56 tests.
- `.venv\Scripts\ruff.exe check .` — PASS.
- `git diff --check` — PASS.
- Verified immutable TenantContext, tenant/business membership query, per-view tenant-scoped physical SQL, strict one-view validator/compiler, readonly ODBC flags, Key Vault password retrieval, connection close, row cap, and truncation handling through source and unit tests.

### Azure and source boundaries

- Azure resources changed: none. No SQL connection or live business query was run.
- Prototype remains clean and unmodified on `main`; `.git`, `.env`, and secret values were not copied.
- SQL Server, Key Vault SQL secret, and demo tenant values are not configured in this checkout; live data verification remains pending.
- Phase 3 code commit: `0014ca5` (`feat: migrate TiendasON semantic query engine`).

### Next action

- Phase 4: import the validated agent/chat orchestration with mocks, keeping database tool arguments tenant-free and parallel calls disabled.

## Phase 4 — Agent orchestration and chat contracts

**Status:** PASS — local fake-model regression tests; no live model, SQL, or Azure call
**Date:** 2026-09-28

### Changes

- Imported the prototype's Spanish business instructions, strict `query_database` tool, LangGraph agent loop, safe query diagnostics, chat request/response models, conversation service, and process-local conversation store.
- The graph accepts an injected model and rejects missing providers explicitly; the OpenAI provider is deferred to Phase 5. No Foundry/OpenAI path was called.
- Preserved sequential tool handling, `parallel_tool_calls=False`, the maximum of 10 queries per question, server-side tenant/settings injection, and public-only conversation history.
- Added LangGraph and timezone-data dependencies for Python 3.11/Windows; added graph, instructions, and chat-service regression tests.

### Verification

- Focused agent, instructions, chat, domain/query, tenant and database suites: PASS.
- Full `.venv\Scripts\python.exe -m pytest -q`: PASS, 78 tests.
- `.venv\Scripts\ruff.exe check .`: PASS after formatting.
- `git diff --check`: PASS.
- Tests prove graph construction with a fake model, strict tool schema, no unsupported tool execution, sequential queries, budget enforcement, tenant-free model arguments, accepted public history, rejection of tool messages, and no persistence of failed turns.

### Boundaries

- No actual SQL connection, model call, Key Vault access, or Azure resource operation was performed.
- API/UI routing remains unchanged and is deferred to Phase 8. Model configuration remains unchanged.

### Next action

- Phase 5: implement the decoupled `LLMProvider` and OpenAI provider; check Key Vault secret existence without revealing its value before any real call.

## Phase 5 — Foundry to OpenAI provider

**Status:** PASS locally; real OpenAI smoke BLOCKED BY RBAC
**Date:** 2026-09-28

### Implementation

- Added `app/llm/` with an `LLMProvider` protocol, safe provider error, and `OpenAIProvider` backed by the existing Key Vault secret provider.
- LangGraph now depends on the `LLMProvider` interface and accepts an injected provider or model; the application composition point can supply `OpenAIProvider`. It binds only `query_database` with strict schema and parallel tool calls disabled, enforces the existing 10-query limit, and maps provider initialization/request errors to controlled messages. No model fallback is implemented.
- Set `OPENAI_CHAT_MODEL=gpt-5-mini` in `.env.example` and configured `OPENAI_API_KEY_SECRET_NAME=openai-api-key`; the model remains environment-configurable. Added `langchain-openai` dependency. No API key is included in code, examples, tests, docs, or logs.
- Added small local architecture guides for the existing `app`, `agent`, `llm`, `semantic`, `query_engine`, `database`, `infra`, `scripts`, and `tests` directories. Did not create guides for absent `evaluation`, `reference`, or `app/rag` directories.
- Target repo contains no Foundry runtime code under `app/` or `tests/`. The existing Foundry Azure resources and source prototype implementation remain untouched; there is no Foundry fallback in the POS provider path.

### Key Vault and smoke status

- `KEY_VAULT_SECRET_CHECK=BLOCKED_BY_RBAC` for `kv-tiendas-sbx-k7m4p2`. Azure CLI is authenticated as `santiago9902@hotmail.com`; the vault uses RBAC. Visible assignments are `Owner` at subscription scope, whose role definition has no `dataActions`.
- Metadata-only `az keyvault secret list --query "[?name=='openai-api-key'].name"` was denied: `Microsoft.KeyVault/vaults/secrets/readMetadata/action` at vault scope. An identifier-only `az keyvault secret show --query id` was also denied: `Microsoft.KeyVault/vaults/secrets/getSecret/action`. Secret existence is unverified; no secret value was returned or displayed.
- Minimum permission for runtime retrieval is `Microsoft.KeyVault/vaults/secrets/getSecret/action` at the individual secret scope. Metadata-only list verification requires `readMetadata/action` at vault scope. A custom role can grant only the required action/scope; built-in `Key Vault Secrets User` includes both actions and is broader when assigned at vault scope. No RBAC assignment, Entra configuration, or security default was changed.
- `OPENAI_REAL_SMOKE=BLOCKED_BY_RBAC`; no real OpenAI call was attempted.

### Verification

- Provider-focused tests cover configured model/secret-name resolution, model construction without a request, missing model/Key Vault configuration, secret-resolution failure sanitization, provider injection, required tool contract, and safe model-request failure.
- `python -m unittest discover -s tests -v`: PASS, 50 tests.
- `.venv\Scripts\python.exe -m pytest -q`: PASS, 85 tests.
- `.venv\Scripts\ruff.exe check .`: PASS.
- `git diff --check`: PASS.
- No SQL, semantic view, tenant isolation, Azure resource, or model deployment was changed. Did not proceed to Phase 6.

### Principal files

- Added: `app/llm/{__init__.py,base.py,openai_provider.py}`, `tests/test_openai_provider.py`, and local module README guides.
- Modified: `app/agent/graph.py`, `.env.example`, `pyproject.toml`, `requirements.txt`, `README.md`, `docs/ARCHITECTURE.md`, `docs/MIGRATION.md`, `docs/ROADMAP.md`, and this log. `Settings.openai_chat_model` remains optional/configurable; no model is hardcoded in application logic.
