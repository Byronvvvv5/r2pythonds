param location string
param functionPlanName string
param functionAppName string
param functionStorageAccountName string
param dataStorageAccountName string
param rawInputContainerName string
param processedOutputContainerName string
param appInsightsConnectionString string
param cosmosEndpoint string
param cosmosDatabaseName string
param azureSubscriptionId string
param azureResourceGroupName string
param containerJobName string
param containerJobImage string
param containerJobCpu string
param containerJobMemory string
param functionRuntimeVersion string
param tags object = {}

resource functionStorageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: functionStorageAccountName
}

resource functionPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: functionPlanName
  location: location
  kind: 'functionapp'
  tags: tags
  sku: {
    tier: 'Dynamic'
    name: 'Y1'
  }
  properties: {}
}

var functionStorageKey = listKeys(functionStorageAccount.id, '2023-05-01').keys[0].value
var functionStorageConnectionString = 'DefaultEndpointsProtocol=https;AccountName=${functionStorageAccount.name};AccountKey=${functionStorageKey};EndpointSuffix=${environment().suffixes.storage}'

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  tags: tags
  properties: {
    serverFarmId: functionPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|${functionRuntimeVersion}'
      minTlsVersion: '1.2'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: functionStorageConnectionString
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'APPINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }
        {
          name: 'DATA_STORAGE_ACCOUNT_NAME'
          value: dataStorageAccountName
        }
        {
          name: 'RAW_INPUT_CONTAINER'
          value: rawInputContainerName
        }
        {
          name: 'PROCESSED_OUTPUT_CONTAINER'
          value: processedOutputContainerName
        }
        {
          name: 'COSMOS_DB_ENDPOINT'
          value: cosmosEndpoint
        }
        {
          name: 'COSMOS_DB_DATABASE_NAME'
          value: cosmosDatabaseName
        }
        {
          name: 'COSMOS_RUNS_CONTAINER'
          value: 'runs'
        }
        {
          name: 'COSMOS_ARTIFACTS_CONTAINER'
          value: 'artifacts'
        }
        {
          name: 'AZURE_SUBSCRIPTION_ID'
          value: azureSubscriptionId
        }
        {
          name: 'AZURE_RESOURCE_GROUP'
          value: azureResourceGroupName
        }
        {
          name: 'CONTAINER_JOB_NAME'
          value: containerJobName
        }
        {
          name: 'CONTAINER_JOB_CONTAINER_NAME'
          value: 'pipeline-runner'
        }
        {
          name: 'CONTAINER_JOB_IMAGE'
          value: containerJobImage
        }
        {
          name: 'CONTAINER_JOB_CPU'
          value: containerJobCpu
        }
        {
          name: 'CONTAINER_JOB_MEMORY'
          value: containerJobMemory
        }
      ]
      ftpsState: 'Disabled'
    }
    reserved: true
  }
}

output functionAppId string = functionApp.id
output functionAppName string = functionApp.name
output functionPrincipalId string = functionApp.identity.principalId