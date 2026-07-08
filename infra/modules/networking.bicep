param location string
param vnetName string
param vnetAddressPrefix string = '10.0.0.0/16'
param privateEndpointSubnetPrefix string = '10.0.1.0/24'
param functionOutboundSubnetPrefix string = '10.0.2.0/24'
param tags object = {}

resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: privateEndpointSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
      {
        name: 'snet-function-outbound'
        properties: {
          addressPrefix: functionOutboundSubnetPrefix
          // Flex Consumption (FC1) runs on Container Apps infrastructure
          delegations: [
            {
              name: 'delegation-flex-consumption'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output vnetName string = vnet.name
output privateEndpointSubnetId string = '${vnet.id}/subnets/snet-private-endpoints'
output functionOutboundSubnetId string = '${vnet.id}/subnets/snet-function-outbound'
