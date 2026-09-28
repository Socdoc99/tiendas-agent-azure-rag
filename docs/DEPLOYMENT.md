# Deployment

The target deployment is Azure Container Apps in the existing sandbox resource group `rg-tiendas-agent-sbx`. Core data and observability resources use `dataLocation` (currently `eastus`); Container Apps resources use `appLocation` (defaults to `dataLocation`). Application resources will be declared in `infra/app.bicep`. Do not deploy a Container App until its image has been built and pushed.

Core resource names use the non-personal suffix `k7m4p2`: Search `srch-tiendas-agent-sbx-k7m4p2`, Storage `sttiendasagentsbxk7m4p2`, Key Vault `kv-tiendas-sbx-k7m4p2`, and ACR `acrtiendasagentsbxk7m4p2`. Search is Free (Basic is the only allowed fallback), Storage is Standard LRS, ACR is Basic, and Container Apps uses Consumption with scale-to-zero.

Phase 2A Core Infrastructure is complete: Search, Storage, Key Vault, ACR, Log Analytics, and Application Insights succeeded. Phase 2B Application Runtime is pending: the remote deployment `tiendas-agent-env-retry` reported terminal `Failed` after a timeout, while `cae-tiendas-agent-sbx` still reports `Updating` with `AKSCapacityHeavyUsage` in `eastus`. Refresh both remote states before any infrastructure operation. Do not start a parallel deployment while the Environment remains active.

Phases 3–8 may run locally against the deployed Azure data services while Phase 2B is pending. Phase 9 remains gated on an operational Container Apps Environment. If the active deployment succeeds, reuse the existing Environment. If it ends `Failed` specifically for regional capacity, run `az deployment group what-if` first and make one Environment attempt with `appLocation=eastus2` and `dataLocation=eastus`; keep the existing resource group and data services in place. Stop for any other failure reason.

For local use, install `requirements-dev.txt`, copy `.env.example` to `.env`, and run `uvicorn app.main:app --reload`. Approved model settings are `text-embedding-3-small` with 1536 dimensions and `gpt-5.6-luna`. Runtime API keys belong in Key Vault; do not put them in `.env` or Git. Local Key Vault metadata access is currently denied, so verify the secret through an authorized identity before model-backed ingestion or chat.

Use [`scripts/workflow.bat`](../scripts/workflow.bat) for local setup, checks, API execution, Docker build, and read-only Azure status. It does not apply Azure deployments. Current deployment status is recorded in `IMPLEMENTATION_LOG.md`.
