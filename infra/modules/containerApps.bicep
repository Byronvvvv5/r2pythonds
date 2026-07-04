param location string
param containerEnvironmentName string
param containerJobName string
param logAnalyticsWorkspaceCustomerId string
param logAnalyticsSharedKey string
param appInsightsConnectionString string
param containerImage string
param cpu int
param memory string
param tags object = {}

resource containerEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerEnvironmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspaceCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
  }
}

resource containerJob 'Microsoft.App/jobs@2024-03-01' = {
  name: containerJobName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  tags: tags
  properties: {
    environmentId: containerEnvironment.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 1800
      replicaRetryLimit: 1
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
    }
    template: {
      containers: [
        {
          name: 'pipeline-runner'
          image: containerImage
          env: [
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsightsConnectionString
            }
          ]
          resources: {
            cpu: cpu
            memory: memory
          }
        }
      ]
    }
  }
}

output containerEnvironmentId string = containerEnvironment.id
output containerEnvironmentName string = containerEnvironment.name
output containerJobName string = containerJob.name
output containerPrincipalId string = containerJob.identity.principalId