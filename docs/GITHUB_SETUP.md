# GitHub Repository Setup Guide

## Step 1: Create GitHub Repository

1. **Go to GitHub**: https://github.com/new

2. **Fill in details**:
   - **Repository name**: `FabricPipelineAutomation`
   - **Description**: `Conference attendance pipeline using Microsoft Fabric, Azure, and Power BI`
   - **Visibility**: ☑️ Public (or Private if you prefer)
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)

3. **Click**: "Create repository"

## Step 2: Push Local Code to GitHub

After creating the repository, run these commands in your terminal:

```powershell
# The remote is already configured, just need to push
git branch -M main
git push -u origin main
```

If it asks for credentials, use:
- **Username**: `alexeikh` (or your GitHub username)
- **Password**: Your GitHub Personal Access Token (the one you provided)

## Step 3: Verify Repository

1. Open: https://github.com/alexeikh/FabricPipelineAutomation
2. You should see all files including:
   - README.md
   - notebooks/load_conference_data.ipynb
   - scripts/
   - sample-data/
   - powerbi-templates/

## Step 4: Connect Fabric Workspace to GitHub

### Option A: Via Fabric Portal (Recommended)

1. Open [Microsoft Fabric](https://app.fabric.microsoft.com/)

2. **Delete the current workspace** (since it's empty and has issues):
   - Go to: https://app.fabric.microsoft.com/groups/07fafa98-29b0-49a0-9464-a80f2f6af2e2
   - Click workspace settings (⚙️)
   - Click "Remove this workspace"

3. **Create new workspace with Git integration**:
   - Click **Workspaces** → **New workspace**
   - Name: **"West US Training"**
   - Click **Advanced** section
   - Under **Git integration**, click **Add**
   - Select **GitHub**
   - Authorize Fabric to access GitHub (if not already done)
   - Select:
     - **Organization/Owner**: `alexeikh`
     - **Repository**: `FabricPipelineAutomation`
     - **Branch**: `main`
     - **Folder**: `/` (root folder)
   - Click **Create**

4. **Workspace will auto-import**:
   - Notebooks from `notebooks/` folder will appear automatically
   - Lakehouse definition will be imported
   - You'll see: "Load Conference Data" notebook ready to use

5. **Assign to capacity**:
   - In workspace settings
   - Go to **License** tab
   - Select your Fabric capacity (e.g., "akhfabcapacity")
   - Click **Apply**

### Option B: Connect Existing Workspace to Git

1. Open your existing workspace
2. Go to **Workspace settings** (⚙️)
3. Navigate to **Git integration** tab
4. Click **Connect**
5. Select **GitHub**
6. Select repository: `FabricPipelineAutomation`
7. Click **Connect and sync**
8. Click **Update all** to import from GitHub

## Step 5: Create Lakehouse (if not auto-created)

If the Lakehouse wasn't auto-created from Git:

1. In workspace, click **New** → **Lakehouse**
2. Name: `ConferenceDataLakehouse`
3. Click **Create**

## Step 6: Create Storage Shortcut

1. Open **ConferenceDataLakehouse**
2. Click **Files** in left panel
3. Click **New shortcut**
4. Select **Azure Data Lake Storage Gen2**
5. Enter:
   - **URL**: `https://westusattendiesstore.dfs.core.windows.net/`
   - **Authentication**: Microsoft Entra ID (use your current login)
6. Click **Next**
7. Select container: **conference-data**
8. Name the shortcut: **conference-data**
9. Click **Create**

## Step 7: Run the Pipeline

1. Open **Load Conference Data** notebook (should be imported from Git)
2. Click **"Run all"**
3. Wait 2-3 minutes
4. Verify completion: Last cell shows "✓ Data pipeline completed successfully!"

## Step 8: Create Power BI Report

Run from your local terminal:

```powershell
# Get your workspace ID from the URL
# Example: https://app.fabric.microsoft.com/groups/YOUR-WORKSPACE-ID

python scripts/create_powerbi_report.py --workspace-id YOUR-WORKSPACE-ID
```

## 🔄 Future Updates: GitOps Workflow

### Making Changes

**Option 1: Edit locally, push to GitHub, sync to Fabric**
```powershell
# 1. Edit notebooks in VS Code
# 2. Commit and push
git add notebooks/
git commit -m "Updated data pipeline"
git push

# 3. In Fabric workspace, click Git icon → "Update all"
```

**Option 2: Edit in Fabric, commit to GitHub**
1. Edit notebook in Fabric portal
2. Click Git icon in workspace
3. Review changes
4. Add commit message
5. Click "Commit"
6. Changes pushed to GitHub automatically

## ✅ Benefits of This Approach

- ✅ **Notebooks automatically deployed** from GitHub
- ✅ **Version control** for all changes
- ✅ **No manual copy-paste** needed
- ✅ **Team collaboration** via Git
- ✅ **CI/CD ready** for future automation

## 🎯 Next Steps

After everything is set up:

1. **Test the pipeline**: Run notebook, verify data loads
2. **Create Power BI report**: Use script or manual creation
3. **Set up monitoring**: Add alerts and notifications
4. **Document customizations**: Update README with your specifics
5. **Share with team**: Invite collaborators to GitHub repo

---

**Need Help?**
- Check [README.md](../README.md) for full documentation
- See [NEXT_STEPS.md](../NEXT_STEPS.md) for detailed guide
- Open an issue on GitHub if you encounter problems
