# Deployment

## Existing resources

Use the existing resource group `rg-tiendas-agent-sbx` and already deployed core resources. Phase 2A is complete. Do not create a new resource group, Search service, Storage account, Key Vault, ACR, Foundry account, or Foundry project. Do not alter the existing Foundry model deployment.

## Container Apps gate

The last remote status check recorded on 2026-09-28 returned ARM deployment `tiendas-agent-env-retry` as `Failed` after a provisioning timeout; `cae-tiendas-agent-sbx` still reported `Updating` with `ManagedEnvironmentCapacityHeavyUsageError` in `eastus`. Refresh both statuses before any Bicep operation. Never start a parallel deployment while ARM is `Running` or the Environment is `Updating`.

If the deployment succeeds, reuse the existing Environment. If the Environment reaches terminal `Failed` specifically due to regional capacity, run `az deployment group what-if` and make at most one controlled attempt using `appLocation=eastus2`, `dataLocation=eastus`, the same resource group, and an explicitly named Environment. Keep Search, Storage, Key Vault, ACR, and observability resources in their current locations. Do not start Phase 9 until the Environment is operational and Phases 3–8 have passed their gates.

## Local execution

Install `requirements-dev.txt`, configure a separate local `.env` without copying the prototype's file, and run `uvicorn app.main:app --reload`. SQL credentials must be retrieved from Key Vault at runtime. Do not run live SQL smoke scripts until the approved readonly credentials and demo tenant are configured.

Local deployment readiness and phase status are tracked in `IMPLEMENTATION_LOG.md`. Azure changes require a fresh state check, a non-destructive plan, and a small commit documenting the result.
