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

### Recovery plan

- Recheck the remote ARM deployment and Environment before every Azure operation.
- If the current deployment succeeds, use the existing Environment.
- If it fails specifically because of regional capacity, run `what-if` first and make exactly one Environment attempt in `eastus2` using `appLocation=eastus2`. Keep `dataLocation=eastus` so Search, Storage, Key Vault, ACR, Log Analytics, and Application Insights stay where they already are. Do not create another Resource Group.
- If the result is a different error, stop and inspect it before changing infrastructure.
- The current Environment is still `Updating`, so the eastus2 attempt remains on hold despite the ARM deployment's terminal failure.

## Phases 3–8 — Local application and Azure data-plane work

**Status:** Local implementation complete; Azure data-plane integration pending identity and secret access

The local application now includes the Search index schema and management script, Blob document storage, PDF/DOCX/TXT/MD extraction and chunking, deduplicated ingestion, vector plus keyword retrieval, grounded chat, citation validation, input limits, and a browser chat UI. The application is configured with the approved model values: `text-embedding-3-small` / 1536 dimensions and `gpt-5.6-luna`.

The `.env` file was created locally from the sample and is ignored by Git; it contains model configuration only and no API key. `openai-api-key` existence could not be verified because Key Vault denies metadata and secret reads. The Search index was created, but Search document operations are forbidden; Blob ingestion and live model calls have not been performed. Model-backed operations also require the existing secret to be available.

Do not create a Container App or begin Phase 9 until a Container Apps Environment is operational. Phases 3–8 can continue locally against the deployed core services when their data-plane identity is authorized.

### Local verification

- `.venv\Scripts\python.exe -m pytest -v` — PASS, 16 tests.
- `.venv\Scripts\ruff.exe check .` — PASS.
- `git diff --check` — PASS.

## Phase 3 — Azure AI Search

**Status:** PARTIAL — index created; data-plane document smoke test blocked by RBAC
**Date:** 2026-09-28 14:36 COT

- Created/updated `idx-tiendas-knowledge-v1` in the existing Search service with the approved 1536-dimension vector schema — PASS.
- Search service/index metadata read and schema creation succeeded with the current identity.
- Synthetic document upload was rejected with HTTP 403 Forbidden; the subsequent cleanup request was also denied and no synthetic record was written. Search document query was rejected with HTTP 403 Forbidden.
- Do not report data-plane read/write or `is_active` filter acceptance as verified. The identity needs an appropriate Azure AI Search data-plane role; no role assignment was changed.

## Phase 4 — Document pipeline

**Status:** IMPLEMENTED LOCALLY; live Azure ingestion pending data-plane and Key Vault access
**Date:** 2026-09-28 14:36 COT

- Implemented PDF, DOCX, TXT, and MD extraction, normalization, page-aware token chunking, SHA-256 deduplication, private Blob upload, embeddings, Search upload, update, and delete operations.
- Local parser/chunking and mocked idempotent ingestion tests pass.
- Live ingestion was not run: Search data-plane requests are forbidden, and the Key Vault secret `openai-api-key` could not be read. No sample document was supplied.

## Phase 5 — Hybrid retrieval

**Status:** IMPLEMENTED LOCALLY; live retrieval validation pending Search data-plane access and embeddings
**Date:** 2026-09-28 14:36 COT

- Implemented query embeddings, keyword plus vector Search, active-document filtering, metadata filters, top-k selection, per-document limits, and non-production `/api/v1/debug/search`.
- Unit coverage verifies index schema, filter escaping, and active-document filter construction.
- Live Search document queries currently return HTTP 403; five-question relevance evaluation has not been run.

## Phase 6 — RAG + LLM

**Status:** IMPLEMENTED LOCALLY; live model validation pending Key Vault secret access
**Date:** 2026-09-28 14:36 COT

- Implemented the provider adapter, grounded context builder, citation validation, `/api/v1/chat`, and no-answer behavior without a Foundry dependency.
- Approved models are `gpt-5.6-luna` and `text-embedding-3-small` (1536 dimensions); these values are in `.env.example` and the ignored local `.env`.
- Mocked tests cover valid citations and no-answer behavior. No live model call was made because Key Vault secret retrieval is denied.

## Phase 7 — Guardrails and resilience

**Status:** LOCAL IMPLEMENTATION PASS
**Date:** 2026-09-28 14:36 COT

- Added strict request and metadata validation, upload and history limits, safe error responses, request IDs, provider timeouts, bounded transient retries, citation allowlisting, and prompt-injection instructions for retrieved content.
- Covered by the passing local test suite. Live dependency-failure behavior remains unverified while data-plane access is unavailable.

## Phase 8 — UI

**Status:** LOCAL IMPLEMENTATION PASS
**Date:** 2026-09-28 14:36 COT

- Added the browser chat UI served by FastAPI, with loading/error states and source/page citations. The UI route test passes.
- A complete browser-to-Azure chat has not been demonstrated because Search data-plane and Key Vault access are blocked.

### Next action

- Resolve authorized Search data-plane and Key Vault access, then run a real document ingestion, five retrieval questions, and live chat validation for Phases 3–6. Refresh ARM and Environment states before any infrastructure operation. Phase 9 remains gated until the existing Environment is operational.
