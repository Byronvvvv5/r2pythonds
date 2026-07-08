targetScope = 'resourceGroup'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Separate location for cosmos due to zoneredundancy')
param cosmosLocation string = 'germanywestcentral'

@description('Short environment name such as dev, test, or prod.')
param environmentName string

@description('Workload name used in resource naming.')
param workloadName string = 'r2pythonds'

@description('Tags applied to all supported resources.')
param tags object = {}

@description('Container image used by the initial batch job placeholder.')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Cosmos DB database name for application metadata.')
param cosmosDatabaseName string = 'r2pythonds'

@description('CPU requested by the container job.')
param containerCpu int = 1

@description('Memory requested by the container job in Gi.')
param containerMemory string = '2Gi'

@description('Publisher email for API management')
param apimPublisherEmail string

@description('Publisher name for API management')
param apimPublisherName string

@description('Enable private networking (VNet, private endpoints, DNS) for Stage 1 data isolation.')
param enablePrivateNetworking bool = false

@description('Add inbound private endpoint for the Function App HTTP surface. Requires enablePrivateNetworking: true.')
param enableFunctionInboundPrivate bool = false

@description('Deploy a test VM inside the VNet for internal-path validation. Requires enablePrivateNetworking: true.')
param deployTestVm bool = false

@secure()
@description('SSH public key for the test VM, e.g. contents of ~/.ssh/id_rsa.pub. Required when deployTestVm is true.')
param testVmAdminPublicKey string = ''

@description('Source IP in CIDR notation allowed to SSH to the test VM, e.g. 203.0.113.10/32.')
param testVmAllowSshFromIp string = ''

var normalizedWorkloadName = toLower(replace(replace(workloadName, '-', ''), '_', ''))
var uniqueSuffix = toLower(uniqueString(subscription().subscriptionId, resourceGroup().id, environmentName, workloadName))
var storageAccountName = take('${normalizedWorkloadName}${environmentName}${uniqueSuffix}', 24)
var functionStorageAccountName = take('${normalizedWorkloadName}func${environmentName}${uniqueSuffix}', 24)
var cosmosAccountName = take('${normalizedWorkloadName}-${environmentName}-${uniqueSuffix}-cosmos', 44)
var functionPlanName = '${normalizedWorkloadName}-${environmentName}-func-plan'
var functionAppName = take('${normalizedWorkloadName}-${environmentName}-${uniqueSuffix}-func', 60)
var logAnalyticsWorkspaceName = take('${normalizedWorkloadName}-${environmentName}-${uniqueSuffix}-log', 63)
var appInsightsName = take('${normalizedWorkloadName}-${environmentName}-${uniqueSuffix}-appi', 260)
var containerEnvironmentName = take('${normalizedWorkloadName}-${environmentName}-${uniqueSuffix}-cae', 32)
var containerJobName = take('${normalizedWorkloadName}-${environmentName}-${uniqueSuffix}-job', 32)
var commonTags = union({
  workload: workloadName
  environment: environmentName
  managedBy: 'bicep'
}, tags)
var apimName = take('${normalizedWorkloadName}-${environmentName}-${uniqueSuffix}-apim', 50)
var vnetName = '${normalizedWorkloadName}-${environmentName}-vnet'

module monitoring './modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    appInsightsName: appInsightsName
    tags: commonTags
  }
}

module networking './modules/networking.bicep' = if (enablePrivateNetworking) {
  name: 'networking'
  params: {
    location: location
    vnetName: vnetName
    tags: commonTags
  }
}

module privateDns './modules/privateDns.bicep' = if (enablePrivateNetworking) {
  name: 'privateDns'
  params: {
    vnetId: networking.outputs.vnetId
    tags: commonTags
  }
}

module storage './modules/storage.bicep' = {
  name: 'storage'
  params: {
    location: location
    storageAccountName: storageAccountName
    containerNames: [
      'raw-input'
      'processed-output'
    ]
    tags: commonTags
    disablePublicNetworkAccess: enablePrivateNetworking
  }
}

module functionStorage './modules/storage.bicep' = {
  name: 'functionStorage'
  params: {
    location: location
    storageAccountName: functionStorageAccountName
    containerNames: [
      'deploymentpackage'
    ]
    tags: commonTags
    disablePublicNetworkAccess: enablePrivateNetworking
  }
}

module cosmos './modules/cosmos.bicep' = {
  name: 'cosmos'
  params: {
    location: cosmosLocation
    cosmosAccountName: cosmosAccountName
    databaseName: cosmosDatabaseName
    containers: [
      {
        name: 'runs'
        partitionKeyPath: '/runId'
      }
      {
        name: 'artifacts'
        partitionKeyPath: '/runId'
      }
    ]
    tags: commonTags
    disablePublicNetworkAccess: enablePrivateNetworking
  }
}

module peStorageBlob './modules/privateEndpoint.bicep' = if (enablePrivateNetworking) {
  name: 'peStorageBlob'
  params: {
    location: location
    name: 'pep-${storageAccountName}-blob'
    subnetId: networking.outputs.privateEndpointSubnetId
    targetResourceId: storage.outputs.storageAccountId
    groupId: 'blob'
    privateDnsZoneId: privateDns.outputs.blobDnsZoneId
    tags: commonTags
  }
}

module peFuncStorageBlob './modules/privateEndpoint.bicep' = if (enablePrivateNetworking) {
  name: 'peFuncStorageBlob'
  params: {
    location: location
    name: 'pep-${functionStorageAccountName}-blob'
    subnetId: networking.outputs.privateEndpointSubnetId
    targetResourceId: functionStorage.outputs.storageAccountId
    groupId: 'blob'
    privateDnsZoneId: privateDns.outputs.blobDnsZoneId
    tags: commonTags
  }
}

module peFuncStorageQueue './modules/privateEndpoint.bicep' = if (enablePrivateNetworking) {
  name: 'peFuncStorageQueue'
  params: {
    location: location
    name: 'pep-${functionStorageAccountName}-queue'
    subnetId: networking.outputs.privateEndpointSubnetId
    targetResourceId: functionStorage.outputs.storageAccountId
    groupId: 'queue'
    privateDnsZoneId: privateDns.outputs.queueDnsZoneId
    tags: commonTags
  }
}

module peFuncStorageTable './modules/privateEndpoint.bicep' = if (enablePrivateNetworking) {
  name: 'peFuncStorageTable'
  params: {
    location: location
    name: 'pep-${functionStorageAccountName}-table'
    subnetId: networking.outputs.privateEndpointSubnetId
    targetResourceId: functionStorage.outputs.storageAccountId
    groupId: 'table'
    privateDnsZoneId: privateDns.outputs.tableDnsZoneId
    tags: commonTags
  }
}

module peCosmosSql './modules/privateEndpoint.bicep' = if (enablePrivateNetworking) {
  name: 'peCosmosSql'
  params: {
    location: location
    name: 'pep-${cosmosAccountName}-sql'
    subnetId: networking.outputs.privateEndpointSubnetId
    targetResourceId: cosmos.outputs.cosmosAccountId
    groupId: 'Sql'
    privateDnsZoneId: privateDns.outputs.documentsDnsZoneId
    tags: commonTags
  }
}

module peFunctionApp './modules/privateEndpoint.bicep' = if (enableFunctionInboundPrivate) {
  name: 'peFunctionApp'
  params: {
    location: location
    name: 'pep-${functionAppName}-sites'
    subnetId: networking.outputs.privateEndpointSubnetId
    targetResourceId: functionApp.outputs.functionAppId
    groupId: 'sites'
    privateDnsZoneId: privateDns.outputs.functionAppDnsZoneId
    tags: commonTags
  }
}

module testVm './modules/testVm.bicep' = if (deployTestVm && enablePrivateNetworking) {
  name: 'testVm'
  params: {
    location: location
    subnetId: networking.outputs.testSubnetId
    adminPublicKey: testVmAdminPublicKey
    allowSshFromIp: testVmAllowSshFromIp
    tags: commonTags
  }
}

module functionApp './modules/functionApp.bicep' = {
  name: 'functionApp'
  params: {
    location: location
    functionPlanName: functionPlanName
    functionAppName: functionAppName
    functionStorageAccountName: functionStorage.outputs.storageAccountName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    tags: commonTags

    dataStorageAccountName: storage.outputs.storageAccountName
    rawInputContainerName: 'raw-input'
    processedOutputContainerName: 'processed-output'

    cosmosEndpoint: cosmos.outputs.cosmosEndpoint
    cosmosDatabaseName: cosmos.outputs.databaseName

    azureSubscriptionId: subscription().subscriptionId
    azureResourceGroupName: resourceGroup().name

    containerJobName: containerJobName
    containerJobImage: containerImage
    containerJobCpu: containerCpu
    containerJobMemory: containerMemory
    storageAccountURL: storage.outputs.blobEndpoint
    vnetIntegrationSubnetId: enablePrivateNetworking ? networking.outputs.functionOutboundSubnetId : ''
    disablePublicInboundAccess: enableFunctionInboundPrivate
  }
  dependsOn: [
    functionStorage
    cosmos
    storage
    monitoring
  ]
}

module containerApps './modules/containerApps.bicep' = {
  name: 'containerApps'
  params: {
    location: location
    containerEnvironmentName: containerEnvironmentName
    containerJobName: containerJobName
    logAnalyticsWorkspaceCustomerId: monitoring.outputs.logAnalyticsWorkspaceCustomerId
    logAnalyticsSharedKey: monitoring.outputs.logAnalyticsSharedKey
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    containerImage: containerImage
    cpu: containerCpu
    memory: containerMemory
    tags: commonTags
  }
}

module apim 'modules/apim.bicep' = {
  name: 'apim'
  params: {
    location: location
    apimName: apimName
    publisherEmail: apimPublisherEmail
    publisherName: apimPublisherName
    functionAppHostname: functionApp.outputs.functionAppHostname
    tags: tags
  }
  dependsOn: [
    functionApp
  ]
}

module roleAssignments './modules/roleAssignments.bicep' = {
  name: 'roleAssignments'
  params: {
    storageAccountName: storageAccountName
    functionStorageAccountName: functionStorageAccountName
    cosmosAccountId: cosmos.outputs.cosmosAccountId
    cosmosAccountName: cosmos.outputs.cosmosAccountName
    functionPrincipalId: functionApp.outputs.functionAppPrincipalId
    containerPrincipalId: containerApps.outputs.containerPrincipalId
  }
  dependsOn: [
    storage
    functionStorage
    cosmos
    functionApp
    containerApps
  ]
}

output storageAccountName string = storage.outputs.storageAccountName
output storageBlobEndpoint string = storage.outputs.blobEndpoint
output storageContainers array = storage.outputs.containerNames
output cosmosAccountName string = cosmos.outputs.cosmosAccountName
output cosmosEndpoint string = cosmos.outputs.cosmosEndpoint
output cosmosDatabaseName string = cosmos.outputs.databaseName
output cosmosContainerNames array = cosmos.outputs.containerNames
output functionAppName string = functionApp.outputs.functionAppName
output functionPrincipalId string = functionApp.outputs.functionAppPrincipalId
output containerEnvironmentName string = containerApps.outputs.containerEnvironmentName
output containerJobName string = containerApps.outputs.containerJobName
output containerPrincipalId string = containerApps.outputs.containerPrincipalId
output logAnalyticsWorkspaceName string = monitoring.outputs.logAnalyticsWorkspaceName
output applicationInsightsName string = monitoring.outputs.appInsightsName
