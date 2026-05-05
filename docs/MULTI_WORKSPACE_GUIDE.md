# Multi-Workspace Git Integration Guide

## Overview

This system enables **centralized configuration** for deploying multiple Microsoft Fabric workspaces with Git integration, while maintaining workspace-level isolation.

## Architecture

```
┌─────────────────────────────────────────────────┐
│    config/workspace-config.yaml                 │
│    (Single source of truth)                     │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│    scripts/deploy_workspaces.py                 │
│    (Automated deployment orchestrator)          │
└──────────────────┬──────────────────────────────┘
                   │
         ┌─────────┼─────────┐
         ↓         ↓         ↓
    Workspace  Workspace  Workspace
    (Region 1) (Region 2)  (Dev)
         │         │         │
         ↓         ↓         ↓
    GitHub     GitHub     GitHub
    Repo       Repo       Repo
```

## Features

✅ **Single Configuration File**: Define all workspaces in one YAML file  
✅ **Multi-Workspace Support**: Deploy 1 to N workspaces  
✅ **Git Integration**: Automated GitHub/Azure DevOps connection  
✅ **Interactive OAuth**: Handles OAuth flows that can't be automated  
✅ **Flexible Deployment**: Enable/disable workspaces individually  
✅ **Environment Isolation**: Different repos/branches per workspace  
✅ **Artifact Verification**: Confirms notebooks synced from Git  
✅ **Idempotent**: Safely re-run without duplicating resources  

## Quick Start

### 1. Review Configuration

Edit `config/workspace-config.yaml`:

```yaml
workspaces:
  - name: "West US Training"
    enabled: true  # ← Set to true for deployment
    git:
      organization: "KeykPa"
      repository: "FabricPipelineAutomation"
      branch: "main"
    lakehouse:
      name: "ConferenceDataLakehouse"
```

### 2. List Configured Workspaces

```bash
python scripts/deploy_workspaces.py --list
```

### 3. Deploy Workspaces

```bash
python scripts/deploy_workspaces.py
```

This will:
1. Create each enabled workspace
2. Assign to Fabric capacity
3. **Open browser** for Git OAuth connection (interactive)
4. Verify artifacts synced from GitHub
5. Guide through Lakehouse creation
6. Provide next steps

## Configuration Guide

### Workspace Definition

```yaml
workspaces:
  - name: "My Workspace"           # Required: Workspace display name
    description: "Purpose..."       # Optional: Description
    enabled: true                   # Required: Enable for deployment
    
    git:
      provider: "GitHub"            # GitHub or AzureDevOps
      organization: "MyOrg"         # GitHub org or Azure DevOps org
      repository: "MyRepo"          # Repository name
      branch: "main"                # Git branch
      directory: "/"                # Folder within repo
    
    lakehouse:
      name: "MyLakehouse"
      storage_shortcut:
        name: "data"
        url: "https://storage.dfs.core.windows.net/"
        container: "container-name"
        auth_type: "MicrosoftEntraID"
    
    expected_artifacts:             # Verify these sync from Git
      - type: "Notebook"
        name: "My Notebook"
    
    powerbi:
      create_report: true
      report_name: "My Report"
```

### Deployment Options

```yaml
deployment:
  skip_existing_workspaces: true   # Use existing if workspace exists
  workspace_creation_wait: 5       # Seconds to wait after creation
  git_sync_wait: 30                # Seconds to wait for Git sync
  auto_open_browser: true          # Open browser for Git OAuth
  auto_create_lakehouse: false     # Manual lakehouse creation
  auto_run_notebooks: false        # Don't auto-run notebooks
  auto_create_reports: false       # Don't auto-create reports
```

## Use Cases

### Single Workspace (Default)

Only one workspace enabled - perfect for single environment deployment:

```yaml
workspaces:
  - name: "Production"
    enabled: true
  
  - name: "Development"
    enabled: false  # ← Disabled
```

Run: `python scripts/deploy_workspaces.py`
Result: Deploys only "Production" workspace

### Multi-Region Deployment

Deploy same pipeline to multiple regions:

```yaml
workspaces:
  - name: "West US Production"
    enabled: true
    git:
      repository: "FabricPipeline"
      branch: "main"
    lakehouse:
      storage_shortcut:
        url: "https://westusstorage.dfs.core.windows.net/"
  
  - name: "East US Production"
    enabled: true
    git:
      repository: "FabricPipeline"
      branch: "main"
    lakehouse:
      storage_shortcut:
        url: "https://eastusstorage.dfs.core.windows.net/"
```

### Dev/Test/Prod Environments

Different branches for each environment:

```yaml
workspaces:
  - name: "Development"
    enabled: true
    git:
      branch: "dev"
  
  - name: "Testing"
    enabled: true
    git:
      branch: "test"
  
  - name: "Production"
    enabled: true
    git:
      branch: "main"
```

### Multi-Team Workspaces

Different teams, different repos:

```yaml
workspaces:
  - name: "Sales Analytics"
    enabled: true
    git:
      repository: "SalesDataPipeline"
  
  - name: "Marketing Analytics"
    enabled: true
    git:
      repository: "MarketingDataPipeline"
```

## Workflow

### Initial Deployment

```bash
# 1. Edit configuration
code config/workspace-config.yaml

# 2. Review what will be deployed
python scripts/deploy_workspaces.py --list

# 3. Deploy
python scripts/deploy_workspaces.py
```

### Adding New Workspace

1. Add to `workspace-config.yaml`:
   ```yaml
   - name: "New Workspace"
     enabled: true
     git: { ... }
   ```

2. Run deployment:
   ```bash
   python scripts/deploy_workspaces.py
   ```
   
   Existing workspaces are skipped (idempotent)

### Updating Workspace Configuration

1. Edit workspace definition in YAML
2. Update manually in Fabric portal (Git settings persist)
3. Or delete workspace and re-deploy

## Git Integration Details

### Why Interactive?

The OAuth flow for Git integration **cannot be fully automated**:
- Requires user consent in browser
- Security feature by design
- 30 seconds per workspace

### What's Automated?

✅ Workspace creation  
✅ Capacity assignment  
✅ Opening browser to correct page  
✅ Displaying exact configuration values  
✅ Verifying sync completion  
✅ Lakehouse setup guidance  

### What's Manual?

⚠️ Clicking "Connect" in Fabric UI  
⚠️ OAuth authorization (one-time per Git provider)  
⚠️ Selecting repository from dropdown  
⚠️ Clicking "Connect and sync"  
⚠️ Creating Lakehouse (for now)  

## Deployment Modes

### Mode 1: Single Workspace

**Use when**: Standard deployment, one environment

```yaml
workspaces:
  - name: "Production"
    enabled: true
```

**Time**: ~2 minutes (including OAuth)

### Mode 2: Multi-Workspace Batch

**Use when**: Multi-region, multi-environment

```yaml
workspaces:
  - name: "Workspace 1"
    enabled: true
  - name: "Workspace 2"
    enabled: true
  - name: "Workspace 3"
    enabled: true
```

**Time**: ~2 minutes per workspace (sequential)

### Mode 3: Selective Deployment

**Use when**: Testing, partial rollout

```yaml
workspaces:
  - name: "Dev"
    enabled: true    # ← Deploy this
  - name: "Test"
    enabled: false   # ← Skip
  - name: "Prod"
    enabled: false   # ← Skip
```

Toggle `enabled` flags as needed

## Troubleshooting

### Workspace Already Exists

**Issue**: "PowerBIEntityAlreadyExists" error

**Solution**: Set `skip_existing_workspaces: true` in config

### Git Sync Not Working

**Issue**: No artifacts appear after sync

**Solutions**:
1. Wait longer (can take 60+ seconds)
2. Refresh workspace in browser
3. Check Git integration status in workspace settings
4. Verify branch name is correct

### Notebook Still Empty

**Issue**: Notebook appears but has no content

**Solution**: Use Git sync method (this script) - avoids API upload issues

### OAuth Authorization Fails

**Issue**: GitHub connection denied

**Solutions**:
1. Check tenant admin enabled Git integration
2. Verify GitHub token has correct permissions
3. Try Azure DevOps instead

## Advanced Configuration

### Custom Config File

```bash
python scripts/deploy_workspaces.py --config path/to/custom-config.yaml
```

### Environment Variables

```bash
# Override Azure subscription
export AZURE_SUBSCRIPTION_ID="..."

# Override Git token
export GITHUB_TOKEN="..."
```

### Logging

```yaml
logging:
  level: "DEBUG"  # DEBUG, INFO, WARNING, ERROR
  file: "logs/deployment.log"
  console_colors: true
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Deploy Fabric Workspaces

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Deploy Workspaces
        run: |
          # Note: OAuth steps still require manual intervention
          # This automates the workspace creation part
          python scripts/deploy_workspaces.py --list
```

### Azure DevOps Pipeline Example

```yaml
trigger:
  branches:
    include:
      - main

pool:
  vmImage: 'ubuntu-latest'

steps:
- task: AzureCLI@2
  inputs:
    azureSubscription: 'FabricServiceConnection'
    scriptType: 'bash'
    scriptLocation: 'inlineScript'
    inlineScript: |
      python scripts/deploy_workspaces.py --list
```

## Best Practices

1. **Version Control Configuration**: Commit `workspace-config.yaml` to Git
2. **Use Branches**: Different Git branches for Dev/Test/Prod
3. **Naming Conventions**: Consistent workspace names (e.g., "Team - Environment - Purpose")
4. **Documentation**: Add descriptions to each workspace
5. **Capacity Planning**: Ensure capacity has enough resources
6. **Access Control**: Configure workspace roles after deployment
7. **Monitoring**: Track deployment results, verify artifacts

## Comparison: Single vs Multi-Workspace

| Feature | Single Workspace | Multi-Workspace |
|---------|------------------|-----------------|
| **Setup Time** | 2 minutes | 2 min × N workspaces |
| **Configuration** | Simple | Structured YAML |
| **Management** | Manual | Centralized config |
| **Scaling** | Repeat process | Add YAML entry |
| **Consistency** | Manual effort | Automated |
| **Audit Trail** | None | Config file history |

## Next Steps After Deployment

1. **Run Notebooks**:
   ```bash
   # In each workspace, click "Run all" on notebooks
   ```

2. **Create Power BI Reports**:
   ```bash
   python scripts/create_powerbi_report.py --workspace-id <id>
   ```

3. **Configure Access**:
   - Workspace Settings → Access
   - Add users/groups with appropriate roles

4. **Set Up Monitoring**:
   - Enable workspace insights
   - Configure alerts

5. **Test GitOps Workflow**:
   - Edit notebook locally
   - Commit and push
   - In Fabric: Git → Update all

## Support

- Configuration issues: Check `workspace-config.yaml` syntax
- Deployment issues: Review console output and error messages
- Git issues: Verify tenant admin settings
- Capacity issues: Check Fabric capacity status

## Files

- `config/workspace-config.yaml` - Configuration
- `scripts/deploy_workspaces.py` - Deployment orchestrator
- `scripts/fix_and_deploy.py` - Core deployment functions
- `scripts/list_workspaces.py` - List existing workspaces
