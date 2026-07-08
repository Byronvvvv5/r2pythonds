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
param containerJobCpu int
param containerJobMemory string
param tags object = {}
param storageAccountURL string
param vnetIntegrationSubnetId string = ''
param disablePublicInboundAccess bool = false

resource functionStorage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: functionStorageAccountName
}

resource functionPlan 'Microsoft.Web/serverFarms@2023-12-01' = {
  name: functionPlanName
  location: location
  tags: tags
  sku: {
    name: 'FC1'
    tier: 'FlexConsumption'
  }
  kind: 'functionapp,linux'
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: functionPlan.id
    virtualNetworkSubnetId: vnetIntegrationSubnetId
    publicNetworkAccess: disablePublicInboundAccess ? 'Disabled' : 'Enabled' 
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${functionStorage.properties.primaryEndpoints.blob}deploymentpackage'
          authentication: {
            type: 'SystemAssignedIdentity'
          }
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: 100
        instanceMemoryMB: 2048
      }
      runtime: {
        name: 'python'
        version: '3.10'
      }
    }
    siteConfig: {
      minTlsVersion: '1.2'
      appSettings: [
        {
          name: 'WEBSITE_DNS_SERVER'
          value: '168.63.129.16'  // Azure's internal DNS, picks up private zones
        }
        {
          name: 'AzureWebJobsStorage__accountName'
          value: functionStorageAccountName
        }
        {
          name: 'AzureWebJobsStorage__credential'
          value: 'managedidentity'
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
        { 
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }
        {
          name: 'STORAGE_ACCOUNT_URL'
          value: storageAccountURL
        }
      ]
    }
  }
}

output functionAppId string = functionApp.id
output functionAppName string = functionApp.name
output functionAppPrincipalId string = functionApp.identity.principalId
output functionAppHostname string = functionApp.properties.defaultHostName
