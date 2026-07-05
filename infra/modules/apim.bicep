param location string
param apimName string
param publisherEmail string
param publisherName string
param functionAppHostname string
param tags object = {}

resource apim 'Microsoft.ApiManagement/service@2024-05-01' = {
  name: apimName
  location: location
  tags: tags
  sku: {
    name: 'Consumption'
    capacity: 0
  }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
  }
}

resource backendApi 'Microsoft.ApiManagement/service/apis@2024-05-01' = {
  parent: apim
  name: 'function-api'
  properties: {
    displayName: 'Function API'
    path: 'api'
    protocols: ['https']
    serviceUrl: 'https://${functionAppHostname}'
    subscriptionRequired: true
  }
}

output apimGatewayUrl string = apim.properties.gatewayUrl
output apimId string = apim.id
