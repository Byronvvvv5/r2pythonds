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

@description('Python runtime version for the future API function app.')
param functionRuntimeVersion string = '3.11'

@description('Cosmos DB database name for application metadata.')
param cosmosDatabaseName string = 'r2pythonds'

@description('CPU requested by the container job.')
param containerCpu int = 1

@description('Memory requested by the container job in Gi.')
param containerMemory string = '2Gi'

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

module monitoring './modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    appInsightsName: appInsightsName
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
  }
}

module functionStorage './modules/storage.bicep' = {
  name: 'functionStorage'
  params: {
    location: location
    storageAccountName: functionStorageAccountName
    containerNames: []
    tags: commonTags
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
        partitionKeyPath: '/projectName'
      }
      {
        name: 'artifacts'
        partitionKeyPath: '/runId'
      }
    ]
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
    dataStorageAccountName: storage.outputs.storageAccountName
    rawInputContainerName: 'raw-input'
    processedOutputContainerName: 'processed-output'
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    cosmosEndpoint: cosmos.outputs.cosmosEndpoint
    cosmosDatabaseName: cosmos.outputs.databaseName
    azureSubscriptionId: subscription().subscriptionId
    azureResourceGroupName: resourceGroup().name
    containerJobName: containerApps.outputs.containerJobName
    containerJobImage: containerImage
    containerJobCpu: string(containerCpu)
    containerJobMemory: containerMemory
    functionRuntimeVersion: functionRuntimeVersion
    tags: commonTags
  }
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

module roleAssignments './modules/roleAssignments.bicep' = {
  name: 'roleAssignments'
  params: {
    storageAccountName: storage.outputs.storageAccountName
    cosmosAccountId: cosmos.outputs.cosmosAccountId
    cosmosAccountName: cosmos.outputs.cosmosAccountName
    functionPrincipalId: functionApp.outputs.functionPrincipalId
    containerPrincipalId: containerApps.outputs.containerPrincipalId
  }
}

output storageAccountName string = storage.outputs.storageAccountName
output storageBlobEndpoint string = storage.outputs.blobEndpoint
output storageContainers array = storage.outputs.containerNames
output cosmosAccountName string = cosmos.outputs.cosmosAccountName
output cosmosEndpoint string = cosmos.outputs.cosmosEndpoint
output cosmosDatabaseName string = cosmos.outputs.databaseName
output cosmosContainerNames array = cosmos.outputs.containerNames
output functionAppName string = functionApp.outputs.functionAppName
output functionPrincipalId string = functionApp.outputs.functionPrincipalId
output containerEnvironmentName string = containerApps.outputs.containerEnvironmentName
output containerJobName string = containerApps.outputs.containerJobName
output containerPrincipalId string = containerApps.outputs.containerPrincipalId
output logAnalyticsWorkspaceName string = monitoring.outputs.logAnalyticsWorkspaceName
output applicationInsightsName string = monitoring.outputs.appInsightsName
