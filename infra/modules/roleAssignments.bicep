param storageAccountName string
param cosmosAccountId string
param cosmosAccountName string
param functionPrincipalId string
param containerPrincipalId string

var storageBlobDataContributorRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource functionStorageAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionPrincipalId, storageBlobDataContributorRoleDefinitionId)
  scope: storageAccount
  properties: {
    principalId: functionPrincipalId
    roleDefinitionId: storageBlobDataContributorRoleDefinitionId
    principalType: 'ServicePrincipal'
  }
}

resource containerStorageAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, containerPrincipalId, storageBlobDataContributorRoleDefinitionId)
  scope: storageAccount
  properties: {
    principalId: containerPrincipalId
    roleDefinitionId: storageBlobDataContributorRoleDefinitionId
    principalType: 'ServicePrincipal'
  }
}

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: cosmosAccountName
}

resource functionCosmosAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  name: guid(cosmosAccountId, functionPrincipalId, 'cosmos-function-assignment')
  parent: cosmosAccount
  properties: {
    principalId: functionPrincipalId
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    scope: cosmosAccount.id
  }
}

resource containerCosmosAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  name: guid(cosmosAccountId, containerPrincipalId, 'cosmos-container-assignment')
  parent: cosmosAccount
  properties: {
    principalId: containerPrincipalId
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    scope: cosmosAccount.id
  }
}

output storageRoleDefinitionId string = storageBlobDataContributorRoleDefinitionId
output cosmosDataRoleDefinitionId string = '${cosmosAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'