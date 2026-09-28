# Deployment

The target deployment is Azure Container Apps in the existing sandbox resource group `rg-tiendas-agent-sbx`, with `eastus` as the base region. Core resources are declared in `infra/core.bicep`; application resources will be declared in `infra/app.bicep`. Do not deploy a Container App until its image has been built and pushed.

Core resource names use the non-personal suffix `k7m4p2`: Search `srch-tiendas-agent-sbx-k7m4p2`, Storage `sttiendasagentsbxk7m4p2`, Key Vault `kv-tiendas-sbx-k7m4p2`, and ACR `acrtiendasagentsbxk7m4p2`. Search is Free (Basic is the only allowed fallback), Storage is Standard LRS, ACR is Basic, and Container Apps uses Consumption with scale-to-zero.

The first core deployment created Search, Storage, Key Vault, ACR, Log Analytics, and Application Insights successfully. Azure rejected the Container Apps Environment in `eastus` with `AKSCapacityHeavyUsage`; see `IMPLEMENTATION_LOG.md` before retrying or choosing another region.

For local use, install `requirements-dev.txt`, copy `.env.example` to `.env`, fill only non-secret settings locally, and run `uvicorn app.main:app --reload`. Runtime API keys belong in Key Vault; do not put them in `.env` for deployed environments.

Use the scripts and resource names documented here after the infrastructure phase updates this file. Current deployment status is recorded in `IMPLEMENTATION_LOG.md`.
