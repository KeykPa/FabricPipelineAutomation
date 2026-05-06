# Multi-Workspace Deployment Guide

## 🎯 Overview

This guide covers the **complete end-to-end deployment** of multiple Microsoft Fabric workspaces, each with:
- Individual OneLake data storage
- Dedicated notebooks for data processing
- Separate semantic models per workspace
- Individual Power BI reports with workspace-specific data

## 🏗️ Multi-Workspace Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Repository                         │
│              (Single Source of Truth)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ - LoadConferenceData.Notebook/                        │  │
│  │ - ConferenceAttendanceSemanticModel.SemanticModel/   │  │
│  │ - AttendanceReport.Report/                           │  │
│  │ - sample-data/ (3 different CSVs)                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │ Git Sync
          ┌───────────────┼───────────────┐
          ↓               ↓               ↓
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │ West US     │ │ East US     │ │ Central US  │
   │ Training    │ │ Training    │ │ Training    │
   └─────┬───────┘ └─────┬───────┘ └─────┬───────┘
         │               │               │
         ↓               ↓               ↓
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │ OneLake     │ │ OneLake     │ │ OneLake     │
   │ west-us.csv │ │ east-us.csv │ │ central.csv │
   └─────┬───────┘ └─────┬───────┘ └─────┬───────┘
         │               │               │
         ↓               ↓               ↓
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │ Notebook    │ │ Notebook    │ │ Notebook    │
   │ (Synced)    │ │ (Synced)    │ │ (Synced)    │
   └─────┬───────┘ └─────┬───────┘ └─────┬───────┘
         │               │               │
         ↓               ↓               ↓
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │ Delta Table │ │ Delta Table │ │ Delta Table │
   │ (West Data) │ │ (East Data) │ │ (Central)   │
   └─────┬───────┘ └─────┬───────┘ └─────┬───────┘
         │               │               │
         ↓               ↓               ↓
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │ Semantic    │ │ Semantic    │ │ Semantic    │
   │ Model       │ │ Model       │ │ Model       │
   │ (Synced)    │ │ (Synced)    │ │ (Synced)    │
   └─────┬───────┘ └─────┬───────┘ └─────┬───────┘
         │               │               │
         ↓               ↓               ↓
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │ Report      │ │ Report      │ │ Report      │
   │ (West Data) │ │ (East Data) │ │ (Central)   │
   └─────────────┘ └─────────────┘ └─────────────┘
```

## 📋 Prerequisites

### Required Software
- ✅ Python 3.10+
- ✅ Azure CLI (logged in with `az login`)
- ✅ Git
- ✅ Microsoft Fabric capacity (F2 or higher)

### Required Azure Resources
- ✅ Azure subscription
- ✅ Fabric capacity provisioned
- ✅ Entra ID user with proper RBAC roles

### Required Permissions
Your Entra ID user needs:
- **Fabric Capacity**: Admin or Contributor
- **Azure Storage**: Storage Blob Data Reader + Storage Blob Data Contributor
- **Resource Group**: Contributor or Owner

## 🚀 Deployment Process

### Part 1: AUTOMATED Steps

These steps are fully automated by the deployment scripts:

#### 1.1 Azure Infrastructure
✅ **Automated**: Resource group creation  
✅ **Automated**: Storage account provisioning  
✅ **Automated**: Blob container creation  
✅ **Automated**: Individual CSV files upload (3 different datasets)  

#### 1.2 Fabric Workspaces
✅ **Automated**: Workspace creation (3 workspaces)  
✅ **Automated**: Capacity assignment  
✅ **Automated**: OneLake lakehouse creation  
✅ **Automated**: Data file upload to OneLake Files/  
✅ **Automated**: Notebook creation (synced from Git)  

#### 1.3 Git Integration
✅ **Automated**: Workspace Git connection initiated  
✅ **Automated**: Repository and branch configuration  
⚠️ **MANUAL**: OAuth browser authentication (cannot be automated)  
✅ **Automated**: Artifact verification after sync  

#### 1.4 Data Processing
✅ **Automated**: Delta table creation trigger  
⚠️ **MANUAL**: Notebook execution to create tables (or use automated API)  

#### 1.5 Semantic Models & Reports
✅ **Automated**: Semantic model synced from Git  
✅ **Automated**: Power BI report synced from Git  
⚠️ **MANUAL**: Report visual configuration (if not in Git)  
✅ **Automated**: Data binding to lakehouse SQL endpoint  

---

### Part 2: MANUAL Steps Required

These steps **cannot be automated** due to OAuth/security requirements:

#### 2.1 Git OAuth Connection (Per Workspace)
**Why Manual**: OAuth flow requires interactive browser authentication

**Steps**:
1. Script opens browser automatically
2. Click **Authorize** on Git provider (GitHub/Azure DevOps)
3. Grant Fabric permission to access repository
4. Browser redirects back to Fabric
5. Wait for Git sync to complete (30-60 seconds)

**Frequency**: Once per workspace during initial setup

#### 2.2 Lakehouse Shortcut Creation (Optional)
**Why Manual**: Cloud connection OAuth cannot be fully automated via API

**Steps**:
1. Navigate to Lakehouse → Files
2. Click **New shortcut**
3. Select **Azure Data Lake Storage Gen2**
4. Enter storage URL and authenticate
5. Grant Fabric workspace managed identity access

**Alternative**: Use direct OneLake upload (fully automated, **recommended**)

**Frequency**: Once per workspace (only if using shortcuts)

#### 2.3 Notebook Execution (Optional)
**Why Manual**: Safe execution with user oversight

**Steps**:
1. Open notebook in Fabric workspace
2. Click **Run All**
3. Monitor execution
4. Verify Delta table creation

**Alternative**: Use Fabric Notebook API to trigger runs (automated, but beta)

**Frequency**: Once per workspace after deployment, then scheduled

#### 2.4 Report Visual Configuration (If Needed)
**Why Manual**: If report visuals not already in Git

**Steps**:
1. Open report in Fabric workspace
2. Add visuals (charts, KPIs, tables)
3. Configure data fields
4. Commit changes to Git

**Alternative**: Deploy complete report definition from Git (fully automated)

**Frequency**: Once during initial setup, then Git-managed

---

## 📊 Data Preparation

### Creating Individual Dataset Files

Each workspace gets its own conference attendance data:

```python
# West US Training data
# sample-data/west_us_attendance.csv
EventDate,AttendeeID,Name,Company,SessionID,SessionName,CheckInTime,Location
2024-05-01,W001,Alice Johnson,Microsoft,S01,Azure AI Overview,09:00,West US
2024-05-01,W002,Bob Smith,Amazon,S01,Azure AI Overview,09:05,West US
...

# East US Training data  
# sample-data/east_us_attendance.csv
EventDate,AttendeeID,Name,Company,SessionID,SessionName,CheckInTime,Location
2024-05-02,E001,Carol White,Google,S02,Fabric Pipelines,10:00,East US
2024-05-02,E002,David Lee,Meta,S02,Fabric Pipelines,10:05,East US
...

# Central US Training data
# sample-data/central_us_attendance.csv
EventDate,AttendeeID,Name,Company,SessionID,SessionName,CheckInTime,Location
2024-05-03,C001,Emily Brown,Oracle,S03,Power BI Advanced,11:00,Central US
2024-05-03,C002,Frank Miller,IBM,S03,Power BI Advanced,11:05,Central US
...
```

## 🔧 Configuration

### Workspace Configuration File

Edit `config/workspace-config.yaml`:

```yaml
workspaces:
  - name: "West US Training"
    enabled: true
    data_file: "west_us_attendance.csv"  # Specific CSV for this workspace
    git:
      organization: "KeykPa"
      repository: "FabricPipelineAutomation"
      branch: "main"
    lakehouse:
      name: "ConferenceDataLakehouse"
    powerbi:
      semantic_model: "ConferenceAttendanceSemanticModel"
      report_name: "WestUSAttendanceReport"

  - name: "East US Training"
    enabled: true
    data_file: "east_us_attendance.csv"
    git:
      organization: "KeykPa"
      repository: "FabricPipelineAutomation"
      branch: "main"
    lakehouse:
      name: "ConferenceDataLakehouse"
    powerbi:
      semantic_model: "ConferenceAttendanceSemanticModel"
      report_name: "EastUSAttendanceReport"

  - name: "Central US Training"
    enabled: true
    data_file: "central_us_attendance.csv"
    git:
      organization: "KeykPa"
      repository: "FabricPipelineAutomation"
      branch: "main"
    lakehouse:
      name: "ConferenceDataLakehouse"
    powerbi:
      semantic_model: "ConferenceAttendanceSemanticModel"
      report_name: "CentralUSAttendanceReport"
```

## 🎬 Deployment Commands

### Step 1: Create Sample Data Files

```bash
python scripts/create_sample_data_multiregion.py
```

This creates 3 CSV files with unique data for each training location.

### Step 2: Clean Up Existing Environment (Optional)

```bash
python scripts/cleanup_all.py --confirm
```

⚠️ **WARNING**: This deletes all existing workspaces and data!

### Step 3: Deploy Multi-Workspace Setup

```bash
python scripts/deploy_multi_workspace.py
```

**What Happens**:
1. ✅ Validates configuration
2. ✅ Creates 3 workspaces
3. ✅ Assigns to Fabric capacity
4. ⚠️ **MANUAL**: Opens browser for Git OAuth (3 times, one per workspace)
5. ✅ Waits for Git sync to complete
6. ✅ Creates lakehouses in each workspace
7. ✅ Uploads workspace-specific CSV to OneLake
8. ✅ Verifies notebook synced from Git
9. ✅ Verifies semantic model synced from Git
10. ✅ Verifies report synced from Git
11. ⚠️ **MANUAL**: Run notebook in each workspace to create Delta tables
12. ✅ Reports ready with workspace-specific data

### Step 4: Run Notebooks (Manual or Automated)

**Option A - Manual (Recommended for first run)**:
1. Open "West US Training" workspace
2. Click "Load Conference Data" notebook
3. Click **Run All**
4. Repeat for other 2 workspaces

**Option B - Automated (Beta API)**:
```bash
python scripts/run_notebooks_all_workspaces.py
```

### Step 5: Verify Deployment

```bash
python scripts/verify_multi_workspace.py
```

Checks:
- ✅ All workspaces created
- ✅ Git sync successful
- ✅ Lakehouses exist
- ✅ Data files uploaded
- ✅ Notebooks synced
- ✅ Delta tables created
- ✅ Semantic models exist
- ✅ Reports exist

## 📝 Post-Deployment

### What's Deployed Per Workspace

Each workspace contains:
1. **Lakehouse**: `ConferenceDataLakehouse`
   - Files: `conference-data/[region]_us_attendance.csv`
   - Tables: `conference_attendance` (Delta table)

2. **Notebook**: `Load Conference Data` (synced from Git)
   - Reads CSV from Files/
   - Creates Delta table
   - Runs on-demand or scheduled

3. **Semantic Model**: `ConferenceAttendanceSemanticModel` (synced from Git)
   - Direct Lake mode
   - Points to lakehouse SQL endpoint
   - Workspace-specific data

4. **Report**: `AttendanceReport` (synced from Git)
   - Bound to workspace semantic model
   - Shows only that workspace's data
   - Custom visuals per region possible

### Git Workflow

**Making Changes**:
1. Edit artifacts in Fabric UI (notebook, report, etc.)
2. In workspace → Source Control → Commit changes
3. Push to Git
4. Changes propagate to all workspaces on next sync

**Or**:
1. Edit files locally in repo
2. Push to Git
3. Workspaces pull changes automatically

### Data Updates

**Adding New Data**:
1. Upload new CSV to OneLake Files/ (per workspace)
2. Run notebook to process
3. Delta table updates
4. Semantic model refreshes
5. Report shows new data

**Scheduled Refresh**:
1. Configure notebook schedule in Fabric
2. Notebook runs automatically
3. Tables update on schedule

## 🔍 Verification Checklist

After deployment, verify each workspace:

- [ ] Workspace exists and is connected to capacity
- [ ] Git integration active (Source Control tab shows status)
- [ ] Lakehouse created with correct name
- [ ] CSV file exists in Files/conference-data/
- [ ] Notebook exists and is synced from Git
- [ ] Notebook has lakehouse attached
- [ ] Delta table `conference_attendance` exists
- [ ] Semantic model exists and points to lakehouse
- [ ] Report exists and shows data
- [ ] Report shows ONLY that workspace's data (verify by location/IDs)

## 🐛 Troubleshooting

### Git Sync Failed
**Problem**: "Missing or corrupted files" error  
**Solution**: Delete workspace, ensure Git repo has correct .platform files, redeploy

### Notebook Can't Find Data
**Problem**: "Path not found" error in notebook  
**Solution**: Verify CSV uploaded to correct OneLake path (Files/conference-data/)

### Semantic Model Shows Wrong Data
**Problem**: Report shows data from different workspace  
**Solution**: Each semantic model MUST point to its own lakehouse SQL endpoint. Verify in model settings.

### Report Shows No Data
**Problem**: Report is empty  
**Solution**: 
1. Check if notebook ran successfully
2. Verify Delta table exists
3. Refresh semantic model
4. Check report data binding

## 📚 Documentation References

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Single workspace deployment
- [docs/MULTI_WORKSPACE_GUIDE.md](docs/MULTI_WORKSPACE_GUIDE.md) - Multi-workspace Git integration
- [ENTRA_AUTH_SETUP.md](ENTRA_AUTH_SETUP.md) - Authentication setup
- [docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md) - GitHub repository configuration

## 🎯 Summary: Automated vs Manual Steps

### Fully Automated ✅
- Azure resource provisioning
- Workspace creation
- OneLake data upload
- Lakehouse creation
- Git connection configuration
- Artifact verification
- Semantic model deployment (via Git)
- Report deployment (via Git)

### Requires Manual Interaction ⚠️
- **Git OAuth**: Browser authentication (3 times, once per workspace)
- **Notebook Run**: Execute notebooks to create tables (or use beta API)
- **Report Visuals**: Configure if not in Git (one-time setup)

### Total Manual Time Estimate
- **Initial Setup**: ~10-15 minutes (OAuth + first notebook run)
- **Per Workspace**: ~3-5 minutes (OAuth + verify)
- **Ongoing**: 0 minutes (fully automated via Git)

---

**🎉 End Result**: 3 fully functional workspaces, each with isolated data, synced to Git, and ready for production use!
