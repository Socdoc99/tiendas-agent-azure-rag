@description('Globally unique Azure AI Search service name.')
param name string

param location string

@allowed([
  'free'
  'basic'
])
param skuName string = 'free'

param tags object = {}

resource searchService 'Microsoft.Search/searchServices@2025-05-01' = {
  name: name
  location: location
  sku: {
    name: skuName
  }
  properties: {
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    disableLocalAuth: false
    hostingMode: 'Default'
    partitionCount: 1
    publicNetworkAccess: 'Enabled'
    replicaCount: 1
    semanticSearch: 'disabled'
  }
  tags: tags
}

output serviceId string = searchService.id
output endpoint string = searchService.properties.endpoint
