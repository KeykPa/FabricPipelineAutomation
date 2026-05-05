<#
.SYNOPSIS
    Upload sample data files to Azure Blob Storage

.DESCRIPTION
    This script uploads conference attendance data files to Azure Blob Storage
    for processing by the Fabric pipeline.

.PARAMETER StorageAccountName
    Name of the Azure Storage Account

.PARAMETER ContainerName
    Name of the blob container (default: conference-data)

.PARAMETER FilePath
    Path to the file to upload

.PARAMETER SasToken
    Optional SAS token for authentication

.EXAMPLE
    .\upload-to-blob.ps1 -StorageAccountName "mystorageacct" -FilePath ".\sample-data\conference_attendance.csv"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$StorageAccountName,
    
    [Parameter(Mandatory=$false)]
    [string]$ContainerName = "conference-data",
    
    [Parameter(Mandatory=$true)]
    [string]$FilePath,
    
    [Parameter(Mandatory=$false)]
    [string]$SasToken
)

# Check if Azure CLI is installed
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI is not installed. Please install it from https://aka.ms/installazurecliwindows"
    exit 1
}

# Check if file exists
if (-not (Test-Path $FilePath)) {
    Write-Error "File not found: $FilePath"
    exit 1
}

$fileName = Split-Path $FilePath -Leaf

Write-Host "Starting upload process..." -ForegroundColor Cyan
Write-Host "Storage Account: $StorageAccountName" -ForegroundColor White
Write-Host "Container: $ContainerName" -ForegroundColor White
Write-Host "File: $fileName" -ForegroundColor White

try {
    # Ensure container exists
    Write-Host "`nChecking if container exists..." -ForegroundColor Yellow
    
    $containerExists = az storage container exists `
        --name $ContainerName `
        --account-name $StorageAccountName `
        --query "exists" `
        --output tsv
    
    if ($containerExists -eq "false") {
        Write-Host "Creating container: $ContainerName" -ForegroundColor Yellow
        az storage container create `
            --name $ContainerName `
            --account-name $StorageAccountName `
            --auth-mode login
    }
    
    # Upload the file
    Write-Host "`nUploading file to blob storage..." -ForegroundColor Yellow
    
    if ($SasToken) {
        az storage blob upload `
            --account-name $StorageAccountName `
            --container-name $ContainerName `
            --name $fileName `
            --file $FilePath `
            --sas-token $SasToken `
            --overwrite
    } else {
        az storage blob upload `
            --account-name $StorageAccountName `
            --container-name $ContainerName `
            --name $fileName `
            --file $FilePath `
            --auth-mode login `
            --overwrite
    }
    
    Write-Host "`n✓ Upload completed successfully!" -ForegroundColor Green
    Write-Host "Blob URL: https://$StorageAccountName.blob.core.windows.net/$ContainerName/$fileName" -ForegroundColor Cyan
    
    # List files in container
    Write-Host "`nFiles in container:" -ForegroundColor Yellow
    az storage blob list `
        --account-name $StorageAccountName `
        --container-name $ContainerName `
        --auth-mode login `
        --query "[].{Name:name, Size:properties.contentLength, LastModified:properties.lastModified}" `
        --output table
        
} catch {
    Write-Error "Upload failed: $_"
    exit 1
}

Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Update the pipeline configuration with this blob URL" -ForegroundColor White
Write-Host "2. Deploy the Fabric pipeline using deploy-pipeline.ps1" -ForegroundColor White
Write-Host "3. Execute the pipeline to load data into Lakehouse" -ForegroundColor White
