<#
.SYNOPSIS
    Deploy Fabric pipeline to a workspace

.DESCRIPTION
    This script deploys the conference attendance pipeline to a Microsoft Fabric workspace
    using the Fabric REST API.

.PARAMETER WorkspaceId
    The ID of the Fabric workspace

.PARAMETER PipelinePath
    Path to the pipeline definition JSON file

.PARAMETER TenantId
    Azure AD Tenant ID (optional, will use current context if not provided)

.EXAMPLE
    .\deploy-pipeline.ps1 -WorkspaceId "12345678-1234-1234-1234-123456789012" -PipelinePath ".\fabric-pipeline\pipeline-definition.json"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$WorkspaceId,
    
    [Parameter(Mandatory=$true)]
    [string]$PipelinePath,
    
    [Parameter(Mandatory=$false)]
    [string]$TenantId
)

# Check if Azure CLI is installed
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI is not installed. Please install it from https://aka.ms/installazurecliwindows"
    exit 1
}

# Check if pipeline file exists
if (-not (Test-Path $PipelinePath)) {
    Write-Error "Pipeline file not found: $PipelinePath"
    exit 1
}

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Fabric Pipeline Deployment Script" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Validate JSON
Write-Host "Validating pipeline definition..." -ForegroundColor Yellow
try {
    $pipelineContent = Get-Content -Path $PipelinePath -Raw | ConvertFrom-Json
    Write-Host "✓ Pipeline JSON is valid" -ForegroundColor Green
} catch {
    Write-Error "Invalid JSON in pipeline file: $_"
    exit 1
}

# Check Azure login status
Write-Host "`nChecking Azure authentication..." -ForegroundColor Yellow
$accountInfo = az account show 2>$null | ConvertFrom-Json

if (-not $accountInfo) {
    Write-Host "Not logged in to Azure. Initiating login..." -ForegroundColor Yellow
    az login
    $accountInfo = az account show | ConvertFrom-Json
}

Write-Host "✓ Logged in as: $($accountInfo.user.name)" -ForegroundColor Green
Write-Host "  Subscription: $($accountInfo.name)" -ForegroundColor White
Write-Host "  Tenant: $($accountInfo.tenantId)" -ForegroundColor White

# Get Fabric API token
Write-Host "`nObtaining Fabric API access token..." -ForegroundColor Yellow
try {
    $tokenResponse = az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv
    
    if (-not $tokenResponse) {
        throw "Failed to obtain access token"
    }
    
    Write-Host "✓ Access token obtained" -ForegroundColor Green
} catch {
    Write-Error "Failed to get Fabric API token: $_"
    exit 1
}

# Prepare API request
$headers = @{
    "Authorization" = "Bearer $tokenResponse"
    "Content-Type" = "application/json"
}

$fabricApiUrl = "https://api.fabric.microsoft.com/v1"
$pipelineDefinition = Get-Content -Path $PipelinePath -Raw

# Deploy pipeline
Write-Host "`nDeploying pipeline to workspace..." -ForegroundColor Yellow
Write-Host "  Workspace ID: $WorkspaceId" -ForegroundColor White
Write-Host "  Pipeline: $($pipelineContent.name)" -ForegroundColor White

try {
    # Check if pipeline already exists
    $listPipelinesUri = "$fabricApiUrl/workspaces/$WorkspaceId/dataPipelines"
    
    Write-Host "`nChecking for existing pipelines..." -ForegroundColor Yellow
    $existingPipelines = Invoke-RestMethod -Uri $listPipelinesUri -Method Get -Headers $headers -ErrorAction Stop
    
    $existingPipeline = $existingPipelines.value | Where-Object { $_.displayName -eq $pipelineContent.name }
    
    if ($existingPipeline) {
        Write-Host "✓ Found existing pipeline: $($existingPipeline.id)" -ForegroundColor Yellow
        Write-Host "  Updating existing pipeline..." -ForegroundColor Yellow
        
        $updateUri = "$fabricApiUrl/workspaces/$WorkspaceId/dataPipelines/$($existingPipeline.id)"
        $response = Invoke-RestMethod -Uri $updateUri -Method Patch -Headers $headers -Body $pipelineDefinition
        
        Write-Host "✓ Pipeline updated successfully!" -ForegroundColor Green
    } else {
        Write-Host "  Creating new pipeline..." -ForegroundColor Yellow
        
        $createUri = "$fabricApiUrl/workspaces/$WorkspaceId/dataPipelines"
        $response = Invoke-RestMethod -Uri $createUri -Method Post -Headers $headers -Body $pipelineDefinition
        
        Write-Host "✓ Pipeline created successfully!" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "Pipeline Details:" -ForegroundColor Cyan
    Write-Host "  Name: $($pipelineContent.name)" -ForegroundColor White
    Write-Host "  Description: $($pipelineContent.properties.description)" -ForegroundColor White
    
} catch {
    $errorDetails = $_.Exception.Message
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $reader.BaseStream.Position = 0
        $errorBody = $reader.ReadToEnd()
        $errorDetails += "`n$errorBody"
    }
    
    Write-Error "Failed to deploy pipeline: $errorDetails"
    exit 1
}

# Summary
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Deployment Summary" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ Pipeline deployed successfully to Fabric workspace" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Navigate to: https://app.fabric.microsoft.com" -ForegroundColor White
Write-Host "2. Open your workspace" -ForegroundColor White
Write-Host "3. Go to Data Factory > Pipelines" -ForegroundColor White
Write-Host "4. Find '$($pipelineContent.name)'" -ForegroundColor White
Write-Host "5. Configure linked services and connections" -ForegroundColor White
Write-Host "6. Run the pipeline to test" -ForegroundColor White
Write-Host ""
