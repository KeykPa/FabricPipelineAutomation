# Automated End-to-End Deployment Guide

## 🚀 One-Command Deployment

This project now supports **fully automated deployment** of the entire infrastructure and pipeline!

## Prerequisites

1. **Python 3.8+**
2. **Azure CLI** (logged in: `az login`)
3. **Dependencies installed**: `pip install -r requirements.txt`

## Option 1: Complete Automated Deployment (Recommended)

Deploy **everything** with one command:

```bash
python scripts/deploy_all.py \
    --resource-group "westusattendiesdata" \
    --location "westus" \
    --storage-account "westusattendiesstore" \
    --workspace-name "West US Training" \
    --use-existing-capacity \
    --capacity-name "akhfabcapacity"
```

### What This Deploys Automatically:

✅ **Azure Infrastructure:**
- Resource Group
- Storage Account
- Blob Container
- Sample data files (CSV + JSON) uploaded using **Entra identity**

✅ **Fabric Workspace:**
- Workspace creation
- Connected to your capacity
- **Lakehouse** created automatically
- **Notebook** uploaded and ready to run

✅ **All Using Entra Identity Authentication:**
- DefaultAzureCredential for all Azure SDK operations
- No connection strings or keys stored
- Secure, enterprise-ready authentication

### After Deployment:

1. **Go to your workspace** (URL printed by the script)
2. **Open the notebook** "Load Conference Data"
3. **Create a Lakehouse shortcut** (one-time setup):
   - In Lakehouse → Files → New shortcut
   - Type: Azure Data Lake Storage Gen2
   - URL: `https://westusattendiesstore.dfs.core.windows.net/conference-data`
   - Authentication: Use your Entra identity
4. **Run the notebook** to load data
5. **Build Power BI reports** on your data

## Option 2: Step-by-Step Deployment

If you prefer to run steps individually:

### Step 1: Deploy Azure + Fabric Workspace

```bash
python scripts/setup_azure_resources.py \
    --resource-group "westusattendiesdata" \
    --location "westus" \
    --storage-account "westusattendiesstore" \
    --workspace-name "West US Training" \
    --use-existing-capacity \
    --capacity-name "akhfabcapacity"
```

This creates Azure resources and the Fabric workspace. Save the **Workspace ID** from the output.

### Step 2: Deploy Lakehouse & Notebook

```bash
python scripts/deploy_fabric_workspace.py \
    --workspace-id "<your-workspace-id>" \
    --storage-account "westusattendiesstore" \
    --lakehouse-name "ConferenceDataLakehouse"
```

This automatically:
- Creates the Lakehouse
- Uploads the notebook
- Configures everything

## What Gets Created

### 📁 File Structure:
```
Azure Blob Storage
└── conference-data/
    ├── conference_attendance.csv (20 records)
    └── conference_attendance.json (5 records)

Fabric Workspace
├── Lakehouse: ConferenceDataLakehouse
└── Notebook: Load Conference Data (ready to run)
```

### 📊 Notebook Pipeline:
The notebook automatically:
1. Reads CSV/JSON from blob storage
2. Transforms and cleans data
3. Writes to Delta table: `conference_attendance`
4. Generates data quality reports
5. Shows summary statistics

## Configuration Files

The deployment automatically creates:
- `config/azure-config.txt` - All deployment settings
- Configuration saved for reference

## Authentication

**All scripts use Entra identity (DefaultAzureCredential):**
- ✅ `deploy_all.py`
- ✅ `setup_azure_resources.py`
- ✅ `deploy_fabric_workspace.py`
- ✅ `upload_to_blob.py`

**No manual authentication setup needed!** Just run `az login` before deployment.

## GitHub Actions Automation

The project includes automated CI/CD via GitHub Actions. Set these secrets:

```yaml
AZURE_CREDENTIALS: <service-principal-json>
FABRIC_WORKSPACE_ID: <workspace-id-from-deployment>
STORAGE_ACCOUNT_NAME: westusattendiesstore
AZURE_SUBSCRIPTION_ID: <your-subscription-id>
```

Then push code → automatic deployment!

## Troubleshooting

### "Lakehouse creation failed"
- Verify you have Contributor access to the workspace
- Check that Data Engineering workload is enabled in your capacity

### "Notebook upload failed"
- Verify Fabric API permissions
- You can upload the notebook manually from `notebooks/load_conference_data.ipynb`

### "Storage access denied"
- Ensure you have "Storage Blob Data Reader" role
- Or create a Lakehouse shortcut (recommended)

## Manual Steps (One-Time)

After automated deployment, you only need to:

1. **Create Lakehouse shortcut** to blob storage (2 minutes)
2. **Run the notebook** to load data (1 minute)

That's it! Everything else is automated.

## Summary

**Before (Manual):**
- 15+ manual steps
- Multiple portals
- 30-60 minutes

**Now (Automated):**
- 1 command
- Everything deployed
- 5-10 minutes

🎉 **Complete infrastructure-as-code for Fabric pipelines!**
