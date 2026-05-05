# Configuration Template

This file contains configuration templates for setting up the Fabric pipeline project.

## Azure Blob Storage Configuration

### Connection String Format
```
DefaultEndpointsProtocol=https;AccountName=<storage-account-name>;AccountKey=<storage-account-key>;EndpointSuffix=core.windows.net
```

### SAS Token Format (if using SAS instead of connection string)
```
?sv=2022-11-02&ss=b&srt=sco&sp=rwdlac&se=2026-12-31T23:59:59Z&st=2026-05-01T00:00:00Z&spr=https&sig=<signature>
```

## Fabric Capacity Configuration

### Capacity SKUs
Choose the appropriate Fabric SKU based on your workload:

- **F2** (2 cores): Starting tier, suitable for development and small workloads
- **F4** (4 cores): Small production workloads
- **F8** (8 cores): Medium production workloads
- **F16** (16 cores): Larger production workloads
- **F32, F64, F128, F256, F512, F1024, F2048**: Enterprise-scale workloads

### Creating Capacity
```bash
az fabric capacity create \
  --resource-group <resource-group-name> \
  --capacity-name <capacity-name> \
  --location <location> \
  --sku name=F2
```

## Fabric Workspace Configuration

### Required Information
- **Workspace Name**: Display name for your workspace (e.g., "ConferencePipeline")
- **Workspace ID**: Found in the workspace URL or obtained from setup script
- **Capacity**: The Fabric capacity to which the workspace is assigned
- **Lakehouse Name**: ConferenceDataLakehouse
- **Lakehouse ID**: Obtained from setup script or Fabric portal

### Creating Workspace via API
```powershell
$fabricToken = az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv

$headers = @{
    "Authorization" = "Bearer $fabricToken"
    "Content-Type" = "application/json"
}

$workspaceBody = @{
    displayName = "ConferencePipeline"
    description = "Workspace for Conference Attendance Pipeline"
    capacityId = "<capacity-id>"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://api.fabric.microsoft.com/v1/workspaces" -Method Post -Headers $headers -Body $workspaceBody
```

## Complete Setup Example

Use the interactive setup script which handles all these configurations:

```powershell
.\scripts\interactive-setup.ps1
```

This script will prompt you for:
1. **Azure Region**: Where to create resources and capacity (e.g., eastus, westeurope)
2. **Resource Group Name**: Container for all Azure resources
3. **Storage Account Name**: Globally unique name for blob storage
4. **Workspace Name**: Name for your Fabric workspace
5. **Capacity Option**: Create new, use existing, or skip
6. **Capacity Name**: Name for new or existing capacity
7. **Capacity SKU**: Size of the capacity (F2, F4, etc.)

## GitHub Secrets

Add these secrets to your GitHub repository:

### AZURE_CREDENTIALS
Service principal credentials in JSON format:
```json
{
  "clientId": "<service-principal-client-id>",
  "clientSecret": "<service-principal-client-secret>",
  "subscriptionId": "<azure-subscription-id>",
  "tenantId": "<azure-tenant-id>"
}
```

### FABRIC_WORKSPACE_ID
```
<your-fabric-workspace-id>
```

### STORAGE_ACCOUNT_NAME
```
<your-storage-account-name>
```

### AZURE_SUBSCRIPTION_ID
```
<your-azure-subscription-id>
```

## Creating a Service Principal

Run these commands in Azure CLI:

```bash
# Create service principal
az ad sp create-for-rbac \
  --name "fabric-pipeline-deployer" \
  --role contributor \
  --scopes /subscriptions/<subscription-id>/resourceGroups/<resource-group-name> \
  --sdk-auth

# Grant Storage Blob Data Contributor role
az role assignment create \
  --assignee <service-principal-client-id> \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/<subscription-id>/resourceGroups/<resource-group-name>/providers/Microsoft.Storage/storageAccounts/<storage-account-name>
```

## Linked Service Configurations

### Azure Blob Storage Linked Service

```json
{
  "name": "AzureBlobStorageLinkedService",
  "properties": {
    "type": "AzureBlobStorage",
    "typeProperties": {
      "connectionString": "<connection-string>",
      "encryptedCredential": "<encrypted-credential>"
    }
  }
}
```

### Fabric Lakehouse Linked Service

```json
{
  "name": "FabricLakehouseLinkedService",
  "properties": {
    "type": "Lakehouse",
    "typeProperties": {
      "workspaceId": "<workspace-id>",
      "artifactId": "<lakehouse-id>"
    }
  }
}
```

## Environment Variables

Create a `.env` file (not committed to Git) with:

```env
AZURE_SUBSCRIPTION_ID=<subscription-id>
AZURE_TENANT_ID=<tenant-id>
AZURE_CLIENT_ID=<client-id>
AZURE_CLIENT_SECRET=<client-secret>
STORAGE_ACCOUNT_NAME=<storage-account-name>
STORAGE_CONTAINER_NAME=conference-data
FABRIC_WORKSPACE_ID=<workspace-id>
FABRIC_LAKEHOUSE_ID=<lakehouse-id>
```

## Pipeline Parameters

Default parameters can be overridden during execution:

```json
{
  "SourceFileName": "conference_attendance.csv",
  "TargetTableName": "conference_attendance"
}
```

## Firewall and Network Configuration

### Storage Account Network Rules
If using private endpoints or firewall rules:

```bash
# Allow Azure services
az storage account update \
  --name <storage-account-name> \
  --resource-group <resource-group-name> \
  --bypass AzureServices

# Add your IP address
az storage account network-rule add \
  --account-name <storage-account-name> \
  --resource-group <resource-group-name> \
  --ip-address <your-ip-address>
```

## Testing Configuration

### Test Connection String
```powershell
# Test blob storage connection
az storage blob list \
  --account-name <storage-account-name> \
  --container-name conference-data \
  --auth-mode login
```

### Test Fabric API Access
```powershell
# Get access token
$token = az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv

# List workspaces
Invoke-RestMethod -Uri "https://api.fabric.microsoft.com/v1/workspaces" -Headers @{"Authorization"="Bearer $token"}
```

## Troubleshooting

### Common Configuration Issues

1. **Authentication Failures**
   - Verify service principal credentials
   - Check token expiration
   - Ensure correct resource scope

2. **Network Access Issues**
   - Check storage account firewall rules
   - Verify VNet/private endpoint configuration
   - Confirm Azure service bypass is enabled

3. **Permission Issues**
   - Verify RBAC role assignments
   - Check Fabric workspace permissions
   - Ensure storage account access levels

## Security Best Practices

1. **Use Azure Key Vault** for storing secrets
2. **Enable soft delete** on storage accounts
3. **Use managed identities** where possible
4. **Implement least privilege** access
5. **Rotate credentials** regularly
6. **Enable audit logging** for all services
7. **Use private endpoints** for production

## Monitoring Configuration

### Application Insights (Optional)
```json
{
  "instrumentationKey": "<app-insights-key>",
  "enableAutoCollect": true
}
```

### Log Analytics Workspace (Optional)
```json
{
  "workspaceId": "<log-analytics-workspace-id>",
  "workspaceKey": "<log-analytics-workspace-key>"
}
```
