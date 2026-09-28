# Azure infrastructure

**Status: PARTIAL.** Core Infrastructure is deployed; the Container Apps Application Runtime is pending/blocked by regional capacity in `eastus`.

`core.bicep` separates `dataLocation` (Search, Storage, Key Vault, ACR, and data/monitoring resources) from `appLocation` (Container Apps Environment). Keep data resources in their existing region if an approved ACA capacity retry is needed.

Before any future Bicep deployment, refresh ARM and Container Apps states and run `az deployment group what-if`. **Do not start a parallel Container Apps deployment while an ARM deployment is `Running` or the Environment is `Updating`.** No new resource group is part of this plan.

See [deployment gates](../docs/DEPLOYMENT.md) and [phase status](../IMPLEMENTATION_LOG.md).
