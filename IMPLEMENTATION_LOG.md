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

## Phase 2 — Azure Core infrastructure

**Status:** BLOCKED — partial deployment
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
- `cae-tiendas-agent-sbx` failed in `eastus` with `ManagedEnvironmentCapacityHeavyUsageError` / `AKSCapacityHeavyUsage`.
- The core deployment `tiendas-agent-core` is therefore `Failed` overall. No Container App has been created.
- The existing Foundry account and project were `Ignore` in `what-if`; neither was changed. No model deployment was touched.

### Commands and checks

- `az bicep build --file infra/core.bicep --stdout` — PASS.
- `az deployment group validate` — PASS.
- `az deployment group what-if` — 9 creates, 2 existing Foundry resources ignored; Search Free, ACR Basic, Storage Standard LRS, Consumption environment.
- `az deployment group create` — PARTIAL; failed only while allocating the Container Apps Environment in `eastus` due Azure regional capacity.
- Resource state queries confirmed the six listed service resources `Succeeded` and the environment `Failed`.

### Decision required

- The plan's base region is `eastus`. Continue by retrying `eastus` later, or move only the Container Apps Environment to another region. No region change will be made without direction.

### Next action

- Resolve Container Apps Environment region/capacity, then finish Phase 2 before starting Phase 3.
