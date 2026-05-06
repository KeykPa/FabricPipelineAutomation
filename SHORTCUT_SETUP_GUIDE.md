# 🔧 Lakehouse Shortcut Setup Guide

## ✅ Solution to 403 Authorization Error

### The Problem
The notebook was trying to access Azure Blob Storage directly using ABFSS protocol, which requires the **workspace managed identity** to have Storage Blob Data Reader permissions. Your user account has the permissions, but the workspace identity doesn't.

### The Solution
Use a **Lakehouse shortcut** instead! This leverages **your Entra ID credentials** through the shortcut, bypassing the workspace identity requirement.

---

## 📋 Setup Steps (3 minutes)

### Step 1: Create Storage Shortcut in Lakehouse

1. **Open your workspace**: https://app.fabric.microsoft.com/groups/00bcfcd2-97d8-48b0-8ae4-67e7395ac373

2. **Navigate to Lakehouse**:
   - Click on **ConferenceDataLakehouse**

3. **Create Shortcut**:
   - In the left panel, click **Files**
   - Click **New shortcut** button
   - Select **Azure Data Lake Storage Gen2**

4. **Configure Connection**:
   - **URL**: `https://westusattendiesstore.dfs.core.windows.net/`
   - **Authentication**: Select **Microsoft Entra ID**
   - Click **Sign in** (uses your logged-in account)
   - Click **Next**

5. **Select Container**:
   - Select the checkbox next to **conference-data**
   - **Shortcut Name**: `conference-data` (keep default)
   - Click **Create**

6. **Verify**:
   - You should see **conference-data** under Files in the lakehouse
   - Expand it to see `conference_attendance.csv` and `conference_attendance.json`

### Step 2: Run the Updated Notebook

The notebook has been updated to use the shortcut path. Just run it!

1. **Open the notebook** in Fabric
2. Click **Run all**
3. It will now read from: `Files/conference-data/conference_attendance.csv`
4. ✅ No more 403 errors!

---

## 🔍 What Changed in the Notebook

### Before (Direct ABFSS - Required Workspace Identity):
```python
storage_account_name = "westusattendiesstore"
container_name = "conference-data"
csv_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/{csv_file}"

# This required workspace managed identity to have Storage Blob Data Reader
df = spark.read.format("csv").load(csv_path)  # ❌ 403 Error
```

### After (Lakehouse Shortcut - Uses Your Credentials):
```python
shortcut_name = "conference-data"
csv_path = f"Files/{shortcut_name}/{csv_file}"

# This uses YOUR Entra ID credentials via the shortcut
df = spark.read.format("csv").load(csv_path)  # ✅ Works!
```

---

## 🎯 Benefits of This Approach

✅ **Uses your existing permissions**: Your user already has Storage Blob Data Reader  
✅ **No workspace identity configuration needed**: Simpler setup  
✅ **Still uses Entra ID**: No storage keys or secrets  
✅ **Better for development**: Easy to see what data you can access  
✅ **Works immediately**: No waiting for RBAC propagation  

---

## 🏢 For Production (Optional)

If you want to use workspace managed identity instead (recommended for production):

1. **Get Workspace Identity Object ID**:
   - Workspace settings → Azure connections → Managed identity
   - Copy the Object ID

2. **Grant Storage Access**:
   ```powershell
   az role assignment create `
     --assignee-object-id <WORKSPACE_IDENTITY_OBJECT_ID> `
     --assignee-principal-type ServicePrincipal `
     --role "Storage Blob Data Reader" `
     --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/westusattendiesdata/providers/Microsoft.Storage/storageAccounts/westusattendiesstore"
   ```

3. **Update Notebook**: Use ABFSS path again (workspace identity will be used automatically)

---

## 📚 Related Documentation

- [ENTRA_AUTH_GUIDE.md](docs/ENTRA_AUTH_GUIDE.md) - Complete Entra ID setup
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Full deployment instructions
- [README.md](README.md) - Project overview

---

**Last Updated**: May 6, 2026  
**Status**: ✅ Notebooks updated to use lakehouse shortcuts with Entra ID
