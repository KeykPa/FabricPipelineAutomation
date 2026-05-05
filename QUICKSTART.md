# Fabric Pipeline Automation - Quick Start Guide

## Platform Requirements

**Cross-Platform Support:** This project works on Windows, Linux, and macOS.

- **Python**: 3.8 or higher
- **Azure CLI**: Latest version
- **Git**: For version control

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd FabricPipeAutomation
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Login to Azure

```bash
az login
```

## Quick Setup

Run the interactive setup script which will guide you through all configuration:

```bash
python scripts/interactive_setup.py
```

The script will ask you for:
- Azure region for resources
- Resource group name
- Storage account name (must be globally unique)
- Fabric workspace name
- Fabric capacity configuration (create new, use existing, or skip)

This will automatically:
- ✓ Create Azure resource group
- ✓ Create storage account and blob container
- ✓ Create Fabric capacity (optional)
- ✓ Create Fabric workspace
- ✓ Create Lakehouse
- ✓ Upload sample conference attendance data

## Manual Commands

If you prefer to run steps individually:

```bash
# Setup Azure resources
python scripts/setup_azure_resources.py \
    --resource-group "rg-fabric-pipeline" \
    --location "eastus" \
    --storage-account "stfabricpipe123" \
    --workspace-name "ConferencePipeline" \
    --capacity-name "fabric-capacity-01" \
    --capacity-sku "F2"

# Upload sample data
python scripts/upload_to_blob.py \
    --storage-account "stfabricpipe123" \
    --file sample-data/conference_attendance.csv

# Deploy pipeline
python scripts/deploy_pipeline.py \
    --workspace-id "<workspace-id-from-setup>" \
    --pipeline-path fabric-pipeline/pipeline-definition.json
```

## VS Code Tasks

If using VS Code, you can run tasks from the Command Palette (Ctrl+Shift+P / Cmd+Shift+P):

1. **Tasks: Run Task** > **Interactive Setup - Complete Project Setup**
2. **Tasks: Run Task** > **Deploy Fabric Pipeline**
3. **Tasks: Run Task** > **Upload Sample Data to Blob**

## What's Next?

After setup completes:

1. **Verify Resources**
   - Check Azure portal for your resource group and resources
   - Visit https://app.fabric.microsoft.com to see your workspace

2. **Configure Pipeline** (if needed)
   - Review `fabric-pipeline/pipeline-definition.json`
   - Update linked service connections if necessary

3. **Run Pipeline**
   - Open your Fabric workspace
   - Navigate to Data Factory > Pipelines
   - Run the ConferenceAttendanceDataPipeline

4. **Analyze Data**
   - Use sample queries from `sql/analytics-queries.sql`
   - Build Power BI reports on top of the Lakehouse

## Troubleshooting

### Common Issues

**"Az login required"**
```bash
az login
# Then run the script again
```

**"Python module not found"**
```bash
pip install -r requirements.txt
```

**"Storage account name already taken"**
- Choose a different globally unique name (try adding random numbers)

**"Fabric workspace creation failed"**
- Verify you have permissions in the subscription
- Check that you have a Fabric capacity or trial available

## Support

For detailed documentation, see [README.md](README.md)

For configuration details, see [config/configuration-template.md](config/configuration-template.md)
