param location string
param subnetId string
param tags object = {}

resource containerGroup 'Microsoft.ContainerInstance/containerGroups@2023-05-01' = {
  name: 'ci-test'
  location: location
  tags: tags
  properties: {
    containers: [
      {
        name: 'test-client'
        properties: {
          image: 'mcr.microsoft.com/azure-cli'
          resources: {
            requests: {
              cpu: 1
              memoryInGB: 1
            }
          }
          command: ['tail', '-f', '/dev/null']
        }
      }
    ]
    osType: 'Linux'
    restartPolicy: 'Never'
    subnetIds: [
      { id: subnetId }
    ]
  }
}

output containerGroupName string = containerGroup.name
