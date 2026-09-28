# Deployment

The target deployment is Azure Container Apps in the existing sandbox resource group `rg-tiendas-agent-sbx`, region `eastus`. Infrastructure is declared in Bicep and is added in Phase 2. Do not deploy a Container App until its image has been built and pushed.

For local use, install `requirements-dev.txt`, copy `.env.example` to `.env`, fill only non-secret settings locally, and run `uvicorn app.main:app --reload`. Runtime API keys belong in Key Vault; do not put them in `.env` for deployed environments.

Use the scripts and resource names documented here after the infrastructure phase updates this file. Current deployment status is recorded in `IMPLEMENTATION_LOG.md`.
