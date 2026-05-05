<#
.SYNOPSIS
    Setup Azure resources and Fabric workspace for the Pipeline project

.DESCRIPTION
    This script creates the required Azure resources:
    - Resource Group
    - Storage Account
    - Blob Container
    - Fabric Capacity (optional)
    - Fabric Workspace
    - Uploads sample data

.PARAMETER ResourceGroupName
    Name of the resource group to create

.PARAMETER Location
    Azure region (default: eastus)

.PARAMETER StorageAccountName
    Name of the storage account (must be globally unique)

.PARAMETER WorkspaceName
    Name of the Fabric workspace to create

.PARAMETER CapacityName
    Name of the Fabric capacity (F SKU) to create or use

.PARAMETER CapacitySku
    Fabric capacity SKU (default: F2). Options: F2, F4, F8, F16, F32, F64, F128, F256, F512, F1024, F2048

.PARAMETER UseExistingCapacity
    Use an existing capacity instead of creating a new one

.EXAMPLE
    .\setup-azure-resources.ps1 -ResourceGroupName "rg-fabric-pipeline" -Location "eastus" -StorageAccountName "stfabricpipe123" -WorkspaceName "ConferencePipeline" -CapacityName "fabric-capacity-01"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$Location,
    
    [Parameter(Mandatory=$true)]
    [string]$StorageAccountName,
    
    [Parameter(Mandatory=$true)]
    [string]$WorkspaceName,
    
    [Parameter(Mandatory=$false)]
    [string]$CapacityName,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("F2", "F4", "F8", "F16", "F32", "F64", "F128", "F256", "F512", "F1024", "F2048")]
    [string]$CapacitySku = "F2",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseExistingCapacity
)

# Check if Azure CLI is installed
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI is not installed. Please install it from https://aka.ms/installazurecliwindows"
    exit 1
}

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Azure Resources Setup for Fabric Pipeline" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Check login status
Write-Host "Checking Azure authentication..." -ForegroundColor Yellow
$account = az account show 2>$null | ConvertFrom-Json

if (-not $account) {
    Write-Host "Not logged in. Initiating Azure login..." -ForegroundColor Yellow
    az login
    $account = az account show | ConvertFrom-Json
}

Write-Host "✓ Logged in as: $($account.user.name)" -ForegroundColor Green
Write-Host "  Subscription: $($account.name)" -ForegroundColor White
Write-Host "  ID: $($account.id)" -ForegroundColor White
Write-Host ""

# Create Resource Group
Write-Host "Creating resource group..." -ForegroundColor Yellow
Write-Host "  Name: $ResourceGroupName" -ForegroundColor White
Write-Host "  Location: $Location" -ForegroundColor White

$rgExists = az group exists --name $ResourceGroupName

if ($rgExists -eq "true") {
    Write-Host "✓ Resource group already exists" -ForegroundColor Yellow
} else {
    az group create --name $ResourceGroupName --location $Location --output none
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Resource group created successfully" -ForegroundColor Green
    } else {
        Write-Error "Failed to create resource group"
        exit 1
    }
}

# Create Storage Account
Write-Host "`nCreating storage account..." -ForegroundColor Yellow
Write-Host "  Name: $StorageAccountName" -ForegroundColor White

$storageExists = az storage account check-name --name $StorageAccountName --query "nameAvailable" -o tsv

if ($storageExists -eq "false") {
    Write-Host "✓ Storage account already exists or name is taken" -ForegroundColor Yellow
} else {
    az storage account create `
        --name $StorageAccountName `
        --resource-group $ResourceGroupName `
        --location $Location `
        --sku Standard_LRS `
        --kind StorageV2 `
        --access-tier Hot `
        --allow-blob-public-access false `
        --min-tls-version TLS1_2 `
        --output none
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Storage account created successfully" -ForegroundColor Green
    } else {
        Write-Error "Failed to create storage account"
        exit 1
    }
}

# Wait a moment for storage account to be ready
Start-Sleep -Seconds 5

# Create Blob Container
Write-Host "`nCreating blob container..." -ForegroundColor Yellow
Write-Host "  Container: conference-data" -ForegroundColor White

az storage container create `
    --name conference-data `
    --account-name $StorageAccountName `
    --auth-mode login `
    --output none

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Blob container created successfully" -ForegroundColor Green
} else {
    Write-Host "✓ Blob container may already exist" -ForegroundColor Yellow
}

# Upload Sample Data
Write-Host "`nUploading sample data files..." -ForegroundColor Yellow

$csvPath = Join-Path $PSScriptRoot "..\sample-data\conference_attendance.csv"
$jsonPath = Join-Path $PSScriptRoot "..\sample-data\conference_attendance.json"

if (Test-Path $csvPath) {
    Write-Host "  Uploading CSV file..." -ForegroundColor White
    az storage blob upload `
        --account-name $StorageAccountName `
        --container-name conference-data `
        --name conference_attendance.csv `
        --file $csvPath `
        --auth-mode login `
        --overwrite `
        --output none
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ CSV file uploaded" -ForegroundColor Green
    }
} else {
    Write-Warning "CSV sample file not found: $csvPath"
}

if (Test-Path $jsonPath) {
    Write-Host "  Uploading JSON file..." -ForegroundColor White
    az storage blob upload `
        --account-name $StorageAccountName `
        --container-name conference-data `
        --name conference_attendance.json `
        --file $jsonPath `
        --auth-mode login `
        --overwrite `
        --output none
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ JSON file uploaded" -ForegroundColor Green
    }
} else {
    Write-Warning "JSON sample file not found: $jsonPath"
}

# Get storage account details
Write-Host "`nRetrieving storage account details..." -ForegroundColor Yellow

$storageAccount = az storage account show `
    --name $StorageAccountName `
    --resource-group $ResourceGroupName | ConvertFrom-Json

$blobEndpoint = $storageAccount.primaryEndpoints.blob

# List uploaded files
Write-Host "`nVerifying uploaded files..." -ForegroundColor Yellow
az storage blob list `
    --account-name $StorageAccountName `
    --container-name conference-data `
    --auth-mode login `
    --query "[].{Name:name, Size:properties.contentLength, LastModified:properties.lastModified}" `
    --output table

# Create or Configure Fabric Capacity
Write-Host "`nConfiguring Fabric Capacity..." -ForegroundColor Yellow

$capacityId = $null
$subscriptionId = $account.id

if ($UseExistingCapacity -and $CapacityName) {
    Write-Host "  Looking for existing capacity: $CapacityName" -ForegroundColor White
    
    $existingCapacity = az fabric capacity show `
        --resource-group $ResourceGroupName `
        --capacity-name $CapacityName 2>$null | ConvertFrom-Json
    
    if ($existingCapacity) {
        $capacityId = $existingCapacity.id
        Write-Host "✓ Using existing capacity: $CapacityName" -ForegroundColor Green
    } else {
        Write-Warning "Capacity '$CapacityName' not found. Will create a new one."
        $UseExistingCapacity = $false
    }
}

if (-not $UseExistingCapacity -and $CapacityName) {
    Write-Host "  Creating Fabric capacity..." -ForegroundColor White
    Write-Host "    Name: $CapacityName" -ForegroundColor White
    Write-Host "    SKU: $CapacitySku" -ForegroundColor White
    Write-Host "    Location: $Location" -ForegroundColor White
    
    az fabric capacity create `
        --resource-group $ResourceGroupName `
        --capacity-name $CapacityName `
        --location $Location `
        --sku name=$CapacitySku `
        --administration members="[`"$($account.user.name)`"]" `
        --output none
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Fabric capacity created successfully" -ForegroundColor Green
        
        $newCapacity = az fabric capacity show `
            --resource-group $ResourceGroupName `
            --capacity-name $CapacityName | ConvertFrom-Json
        
        $capacityId = $newCapacity.id
    } else {
        Write-Warning "Failed to create Fabric capacity. You may need to create it manually."
    }
}

# Create Fabric Workspace
Write-Host "`nCreating Fabric Workspace..." -ForegroundColor Yellow
Write-Host "  Name: $WorkspaceName" -ForegroundColor White

# Get Fabric API token
$fabricToken = az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv

$headers = @{
    "Authorization" = "Bearer $fabricToken"
    "Content-Type" = "application/json"
}

# Check if workspace exists
$listWorkspacesUri = "https://api.fabric.microsoft.com/v1/workspaces"
$existingWorkspaces = Invoke-RestMethod -Uri $listWorkspacesUri -Method Get -Headers $headers

$workspace = $existingWorkspaces.value | Where-Object { $_.displayName -eq $WorkspaceName }

if ($workspace) {
    Write-Host "✓ Workspace already exists" -ForegroundColor Yellow
    Write-Host "  Workspace ID: $($workspace.id)" -ForegroundColor White
    $workspaceId = $workspace.id
} else {
    # Create workspace
    $createWorkspaceUri = "https://api.fabric.microsoft.com/v1/workspaces"
    
    $workspaceBody = @{
        displayName = $WorkspaceName
        description = "Workspace for Conference Attendance Pipeline"
    }
    
    if ($capacityId) {
        $workspaceBody.capacityId = $capacityId
    }
    
    $workspaceJson = $workspaceBody | ConvertTo-Json
    
    try {
        $newWorkspace = Invoke-RestMethod -Uri $createWorkspaceUri -Method Post -Headers $headers -Body $workspaceJson
        $workspaceId = $newWorkspace.id
        Write-Host "✓ Workspace created successfully" -ForegroundColor Green
        Write-Host "  Workspace ID: $workspaceId" -ForegroundColor White
    } catch {
        Write-Warning "Failed to create workspace via API. You may need to create it manually."
        Write-Warning "Error: $_"
    }
}

# Create Lakehouse in the workspace
if ($workspaceId) {
    Write-Host "`nCreating Lakehouse..." -ForegroundColor Yellow
    Write-Host "  Name: ConferenceDataLakehouse" -ForegroundColor White
    
    $createLakehouseUri = "https://api.fabric.microsoft.com/v1/workspaces/$workspaceId/lakehouses"
    
    $lakehouseBody = @{
        displayName = "ConferenceDataLakehouse"
        description = "Lakehouse for conference attendance data"
    } | ConvertTo-Json
    
    try {
        $newLakehouse = Invoke-RestMethod -Uri $createLakehouseUri -Method Post -Headers $headers -Body $lakehouseBody
        $lakehouseId = $newLakehouse.id
        Write-Host "✓ Lakehouse created successfully" -ForegroundColor Green
        Write-Host "  Lakehouse ID: $lakehouseId" -ForegroundColor White
    } catch {
        Write-Warning "Failed to create Lakehouse. You may need to create it manually."
        Write-Warning "Error: $_"
    }
}

# Summary
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "Azure Resources:" -ForegroundColor Yellow
Write-Host "  Resource Group: $ResourceGroupName" -ForegroundColor White
Write-Host "  Location: $Location" -ForegroundColor White
Write-Host "  Storage Account: $StorageAccountName" -ForegroundColor White
Write-Host "  Blob Container: conference-data" -ForegroundColor White
Write-Host "  Blob Endpoint: $blobEndpoint" -ForegroundColor White
Write-Host ""
if ($CapacityName) {
    Write-Host "Fabric Capacity:" -ForegroundColor Yellow
    Write-Host "  Name: $CapacityName" -ForegroundColor White
    Write-Host "  SKU: $CapacitySku" -ForegroundColor White
    if ($capacityId) {
        Write-Host "  ID: $capacityId" -ForegroundColor White
    }
    Write-Host ""
}
Write-Host "Fabric Workspace:" -ForegroundColor Yellow
Write-Host "  Name: $WorkspaceName" -ForegroundColor White
if ($workspaceId) {
    Write-Host "  ID: $workspaceId" -ForegroundColor White
}
if ($lakehouseId) {
    Write-Host "  Lakehouse ID: $lakehouseId" -ForegroundColor White
}
Write-Host ""
Write-Host "Workspace URL:" -ForegroundColor Cyan
Write-Host "https://app.fabric.microsoft.com/groups/$workspaceId" -ForegroundColor White
Write-Host ""
Write-Host "Connection String (run this to get it):" -ForegroundColor Yellow
Write-Host "az storage account show-connection-string --name $StorageAccountName --resource-group $ResourceGroupName" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Verify the workspace and lakehouse in Fabric portal" -ForegroundColor White
Write-Host "2. Update the pipeline configuration with your details" -ForegroundColor White
Write-Host "3. Deploy the pipeline using: .\scripts\deploy-pipeline.ps1 -WorkspaceId $workspaceId" -ForegroundColor White
Write-Host "4. Configure GitHub secrets for CI/CD" -ForegroundColor White
Write-Host ""

# Save configuration to file
$configPath = Join-Path $PSScriptRoot "..\config\azure-config.txt"
$configContent = @"
# Azure and Fabric Configuration
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# Azure Resources
RESOURCE_GROUP=$ResourceGroupName
LOCATION=$Location
STORAGE_ACCOUNT=$StorageAccountName
CONTAINER=conference-data
BLOB_ENDPOINT=$blobEndpoint
SUBSCRIPTION_ID=$subscriptionId

# Fabric Resources
WORKSPACE_NAME=$WorkspaceName
"@

if ($workspaceId) {
    $configContent += "WORKSPACE_ID=$workspaceId`n"
}

if ($CapacityName) {
    $configContent += "CAPACITY_NAME=$CapacityName`n"
    $configContent += "CAPACITY_SKU=$CapacitySku`n"
}

if ($capacityId) {
    $configContent += "CAPACITY_ID=$capacityId`n"
}

if ($lakehouseId) {
    $configContent += "LAKEHOUSE_ID=$lakehouseId`n"
}

$configContent += @"

# Get connection string with:
# az storage account show-connection-string --name $StorageAccountName --resource-group $ResourceGroupName
"@

Set-Content -Path $configPath -Value $configContent
Write-Host "Configuration saved to: $configPath" -ForegroundColor Green
Write-Host ""
