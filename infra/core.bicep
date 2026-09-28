targetScope = 'resourceGroup'

@description('Short, non-personal suffix shared by globally named sandbox resources.')
@minLength(6)
@maxLength(6)
param nameSuffix string = 'k7m4p2'

@description('Deployment region. Defaults to the existing resource group region.')
param location string = resourceGroup().location

@description('Use Free first. Basic is the only permitted fallback.')
@allowed([
  'free'
  'basic'
])
param searchSku string = 'free'

param tags object = {
  project: 'tiendas-agent-azure-rag'
  environment: 'sbx'
  managedBy: 'bicep'
}

var names = {
  search: 'srch-tiendas-agent-sbx-${nameSuffix}'
  storage: 'sttiendasagentsbx${nameSuffix}'
  keyVault: 'kv-tiendas-sbx-${nameSuffix}'
  registry: 'acrtiendasagentsbx${nameSuffix}'
  logAnalytics: 'log-tiendas-agent-sbx'
  appInsights: 'appi-tiendas-agent-sbx'
  containerEnvironment: 'cae-tiendas-agent-sbx'
  blobContainer: 'knowledge'
}

module search './modules/search.bicep' = {
  name: 'tiendas-search-core'
  params: {
    name: names.search
    location: location
    skuName: searchSku
    tags: tags
  }
}

module storage './modules/storage.bicep' = {
  name: 'tiendas-storage-core'
  params: {
    name: names.storage
    location: location
    containerName: names.blobContainer
    tags: tags
  }
}

module keyVault './modules/keyvault.bicep' = {
  name: 'tiendas-keyvault-core'
  params: {
    name: names.keyVault
    location: location
    tenantId: subscription().tenantId
    tags: tags
  }
}

module registry './modules/acr.bicep' = {
  name: 'tiendas-acr-core'
  params: {
    name: names.registry
    location: location
    tags: tags
  }
}

module monitoring './modules/monitoring.bicep' = {
  name: 'tiendas-monitoring-core'
  params: {
    location: location
    workspaceName: names.logAnalytics
    appInsightsName: names.appInsights
    environmentName: names.containerEnvironment
    tags: tags
  }
}

output searchName string = names.search
output searchEndpoint string = search.outputs.endpoint
output storageAccountName string = names.storage
output storageAccountUrl string = storage.outputs.accountUrl
output blobContainerName string = names.blobContainer
output keyVaultName string = names.keyVault
output keyVaultUri string = keyVault.outputs.vaultUri
output registryName string = names.registry
output registryLoginServer string = registry.outputs.loginServer
output logAnalyticsWorkspaceId string = monitoring.outputs.workspaceId
output appInsightsResourceId string = monitoring.outputs.appInsightsId
output containerAppsEnvironmentName string = names.containerEnvironment
output containerAppsEnvironmentId string = monitoring.outputs.containerEnvironmentId
output containerAppsEnvironmentDefaultDomain string = monitoring.outputs.containerEnvironmentDefaultDomain
