# Azure Infrastructure

This directory contains the first infrastructure slice for running `r2pythonds` on Azure with Bicep.

## Phase 1 scope

- Blob Storage for pipeline inputs and outputs
- Cosmos DB for run and artifact metadata
- Function App hosting resources for the future API module
- Azure Container Apps Job for the future batch runner module
- Shared monitoring and minimum role assignments

## Structure

- `main.bicep`: resource-group-scoped entrypoint
- `modules/`: service-specific Bicep modules
- `parameters/dev.parameters.json`: initial dev parameter set

## Deploy

Create or select a resource group first, then deploy:

```bash
az group create --name <resource-group> --location westeurope
az deployment group create \
  --resource-group <resource-group> \
  --template-file infra/main.bicep \
  --parameters @infra/parameters/dev.parameters.json
```

Preview changes before deploying:

```bash
az deployment group what-if \
  --resource-group <resource-group> \
  --template-file infra/main.bicep \
  --parameters @infra/parameters/dev.parameters.json
```

## Notes

- The Function App resource is created here, but function code deployment belongs in a later API pipeline.
- The Container Apps Job is created here with a placeholder image so the runner pipeline can take over later.
- The template currently keeps networking simple and public by default. Private endpoints and stricter network rules should be added in a later increment.