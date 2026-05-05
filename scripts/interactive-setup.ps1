# Interactive Setup Script for Fabric Pipeline Project

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Fabric Pipeline Project - Interactive Setup" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Check if Azure CLI is installed
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI is not installed. Please install it from https://aka.ms/installazurecliwindows"
    exit 1
}

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
Write-Host ""

# Collect Configuration Information
Write-Host "Please provide the following configuration details:" -ForegroundColor Yellow
Write-Host ""

# Azure Region
Write-Host "Available Azure Regions:" -ForegroundColor Cyan
Write-Host "  1. East US (eastus)" -ForegroundColor White
Write-Host "  2. East US 2 (eastus2)" -ForegroundColor White
Write-Host "  3. West US (westus)" -ForegroundColor White
Write-Host "  4. West US 2 (westus2)" -ForegroundColor White
Write-Host "  5. Central US (centralus)" -ForegroundColor White
Write-Host "  6. North Europe (northeurope)" -ForegroundColor White
Write-Host "  7. West Europe (westeurope)" -ForegroundColor White
Write-Host "  8. Southeast Asia (southeastasia)" -ForegroundColor White
Write-Host "  9. Australia East (australiaeast)" -ForegroundColor White
Write-Host ""

$locationChoice = Read-Host "Select region (1-9) or enter custom region name [default: 1]"
$Location = switch ($locationChoice) {
    "2" { "eastus2" }
    "3" { "westus" }
    "4" { "westus2" }
    "5" { "centralus" }
    "6" { "northeurope" }
    "7" { "westeurope" }
    "8" { "southeastasia" }
    "9" { "australiaeast" }
    "" { "eastus" }
    "1" { "eastus" }
    default { $locationChoice }
}

Write-Host "✓ Selected region: $Location" -ForegroundColor Green
Write-Host ""

# Resource Group
Write-Host "Resource Group Configuration:" -ForegroundColor Cyan
$defaultRG = "rg-fabric-pipeline-" + $Location
$ResourceGroupName = Read-Host "Enter Resource Group name [default: $defaultRG]"
if ([string]::IsNullOrWhiteSpace($ResourceGroupName)) {
    $ResourceGroupName = $defaultRG
}
Write-Host "✓ Resource Group: $ResourceGroupName" -ForegroundColor Green
Write-Host ""

# Storage Account
Write-Host "Storage Account Configuration:" -ForegroundColor Cyan
Write-Host "  (Name must be globally unique, 3-24 lowercase letters and numbers)" -ForegroundColor White
$defaultStorage = "stfabric" + (Get-Random -Minimum 1000 -Maximum 9999)
$StorageAccountName = Read-Host "Enter Storage Account name [default: $defaultStorage]"
if ([string]::IsNullOrWhiteSpace($StorageAccountName)) {
    $StorageAccountName = $defaultStorage
}
Write-Host "✓ Storage Account: $StorageAccountName" -ForegroundColor Green
Write-Host ""

# Fabric Workspace
Write-Host "Fabric Workspace Configuration:" -ForegroundColor Cyan
$defaultWorkspace = "ConferencePipeline"
$WorkspaceName = Read-Host "Enter Fabric Workspace name [default: $defaultWorkspace]"
if ([string]::IsNullOrWhiteSpace($WorkspaceName)) {
    $WorkspaceName = $defaultWorkspace
}
Write-Host "✓ Workspace Name: $WorkspaceName" -ForegroundColor Green
Write-Host ""

# Fabric Capacity
Write-Host "Fabric Capacity Configuration:" -ForegroundColor Cyan
Write-Host "  Do you want to create a new Fabric capacity or use an existing one?" -ForegroundColor White
Write-Host "  1. Create new capacity (requires Microsoft Fabric subscription)" -ForegroundColor White
Write-Host "  2. Use existing capacity" -ForegroundColor White
Write-Host "  3. Skip capacity setup (use Trial or assign later)" -ForegroundColor White
Write-Host ""

$capacityChoice = Read-Host "Select option (1-3) [default: 3]"

$CapacityName = $null
$UseExistingCapacity = $false
$CapacitySku = "F2"

if ($capacityChoice -eq "1") {
    # Create new capacity
    $defaultCapacity = "fabric-capacity-" + (Get-Random -Minimum 100 -Maximum 999)
    $CapacityName = Read-Host "Enter Capacity name [default: $defaultCapacity]"
    if ([string]::IsNullOrWhiteSpace($CapacityName)) {
        $CapacityName = $defaultCapacity
    }
    
    Write-Host ""
    Write-Host "Available Capacity SKUs:" -ForegroundColor Cyan
    Write-Host "  1. F2  (2 cores) - Starting tier" -ForegroundColor White
    Write-Host "  2. F4  (4 cores)" -ForegroundColor White
    Write-Host "  3. F8  (8 cores)" -ForegroundColor White
    Write-Host "  4. F16 (16 cores)" -ForegroundColor White
    Write-Host ""
    
    $skuChoice = Read-Host "Select SKU (1-4) [default: 1]"
    $CapacitySku = switch ($skuChoice) {
        "2" { "F4" }
        "3" { "F8" }
        "4" { "F16" }
        default { "F2" }
    }
    
    Write-Host "✓ Capacity: $CapacityName (SKU: $CapacitySku)" -ForegroundColor Green
    
} elseif ($capacityChoice -eq "2") {
    # Use existing capacity
    $UseExistingCapacity = $true
    $CapacityName = Read-Host "Enter existing Capacity name"
    Write-Host "✓ Will use existing capacity: $CapacityName" -ForegroundColor Green
} else {
    Write-Host "✓ Skipping capacity setup - you can assign workspace to Trial or capacity later" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Configuration Summary" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "Resource Group:   $ResourceGroupName" -ForegroundColor White
Write-Host "Location:         $Location" -ForegroundColor White
Write-Host "Storage Account:  $StorageAccountName" -ForegroundColor White
Write-Host "Workspace Name:   $WorkspaceName" -ForegroundColor White
if ($CapacityName) {
    Write-Host "Capacity Name:    $CapacityName" -ForegroundColor White
    if (-not $UseExistingCapacity) {
        Write-Host "Capacity SKU:     $CapacitySku" -ForegroundColor White
    }
}
Write-Host ""

$confirm = Read-Host "Proceed with setup? (y/n) [default: y]"
if ($confirm -eq "n") {
    Write-Host "Setup cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Starting setup process..." -ForegroundColor Green
Write-Host ""

# Build parameters for the setup script
$setupParams = @{
    ResourceGroupName = $ResourceGroupName
    Location = $Location
    StorageAccountName = $StorageAccountName
    WorkspaceName = $WorkspaceName
}

if ($CapacityName) {
    $setupParams.CapacityName = $CapacityName
    if ($UseExistingCapacity) {
        $setupParams.UseExistingCapacity = $true
    } else {
        $setupParams.CapacitySku = $CapacitySku
    }
}

# Call the main setup script
$setupScriptPath = Join-Path $PSScriptRoot "setup-azure-resources.ps1"
& $setupScriptPath @setupParams
