# Conference Attendance Pipeline - Microsoft Fabric

Automated conference attendance data pipeline using Microsoft Fabric, Azure Blob Storage, and Power BI.

## 🔐 **Security-First: Entra ID Authentication**

**All authentication uses Entra ID (Azure AD) - no keys, no secrets, no credentials in code.**

- ✅ Azure Storage: RBAC with Entra ID
- ✅ Fabric Workspace: SSO with organizational account
- ✅ Notebooks: `mssparkutils` with user credentials
- ✅ Power BI: OAuth with Entra ID

📖 **Read First**: [Entra ID Authentication Guide](docs/ENTRA_AUTH_GUIDE.md)

---

## 🎯 Overview

This project provides a complete **GitOps-driven** solution for loading, transforming, and visualizing conference attendance data using Microsoft Fabric.

**Key Features:**
- 🔐 **Entra ID Authentication**: Enterprise-grade security throughout
- 📊 **Data Sources**: CSV and JSON from Azure Blob Storage
- 🏗️ **Infrastructure as Code**: Automated Azure resource deployment
- 📓 **PySpark Notebooks**: Data transformation pipeline
- 📈 **Power BI Reports**: Attendance analytics dashboards
- 🔄 **GitHub Integration**: GitOps workflow with Fabric workspace sync

## 🏛️ Architecture

```
Azure Blob Storage
  └── conference-data/
       ├── conference_attendance.csv
       └── conference_attendance.json
            ↓
Fabric Lakehouse (via Shortcut)
  └── Files/conference-data/
            ↓
PySpark Notebook Pipeline
  └── Transform & Load
            ↓
Delta Tables
  └── conference_attendance
            ↓
Semantic Model (Direct Lake)
  └── Power BI Report
```

## 📁 Project Structure

```
FabricPipelineAutomation/
├── notebooks/
│   └── load_conference_data.ipynb    # PySpark data pipeline
├── sample-data/
│   ├── conference_attendance.csv     # Sample CSV data (20 records)
│   └── conference_attendance.json    # Sample JSON data (5 records)
├── scripts/
│   ├── setup_azure_resources.py      # Azure infrastructure deployment
│   ├── deploy_workspaces.py          # 🆕 Multi-workspace Git deployment
│   ├── fix_and_deploy.py             # Single workspace setup
│   ├── create_powerbi_report.py      # Power BI report automation
│   └── cleanup_all.py                # Resource cleanup
├── config/
│   └── workspace-config.yaml         # 🆕 Multi-workspace configuration
├── powerbi-templates/
│   ├── attendance-report-template.json
│   └── README.md
├── docs/
│   └── *.md                          # Documentation
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- **Azure Subscription** with Fabric capacity (F8 or higher)
- **Python 3.10+**
- **Azure CLI** (`az login` completed)
- **Microsoft Fabric** workspace
- **GitHub** account
- **🔐 Entra ID Authentication**: Required RBAC roles (see below)

### ⚠️ **IMPORTANT: Setup Entra ID Authentication First**

**Assign Storage Blob Data Reader to the admin account** that:
- Provisions Azure resources and Fabric workspaces
- Runs notebooks (via `mssparkutils` with user credentials)

**For this sample**: The admin account handles both provisioning and notebook execution.  
**For production**: Use workspace managed identity (see [Entra Auth Guide](docs/ENTRA_AUTH_GUIDE.md)).

---

#### **Option 1: Azure Portal (Recommended)**
1. Open [Azure Portal](https://portal.azure.com)
2. Navigate to: Resource Groups → `westusattendiesdata` → `westusattendiesstore`
3. Click: **Access Control (IAM)**
4. Click: **+ Add** → **Add role assignment**
5. Select role: **Storage Blob Data Reader**
6. Select: **Admin account** (e.g., `admin@MngEnvMCAP882106.onmicrosoft.com`)
   - ℹ️ This account provisions workspaces AND runs notebooks
7. Click: **Review + assign**
8. **Wait 5 minutes** for RBAC propagation

#### **Option 2: Automated Script**
```bash
python scripts/setup_entra_auth.py
```

#### **Option 3: Azure CLI**
```bash
az role assignment create \
  --assignee user@domain.com \
  --role "Storage Blob Data Reader" \
  --scope $(az storage account show --name westusattendiesstore --resource-group westusattendiesdata --query id -o tsv)
```

📖 **Details**: [Entra ID Authentication Guide](docs/ENTRA_AUTH_GUIDE.md)

---

### 1. Clone Repository

```bash
git clone https://github.com/KeykPa/FabricPipelineAutomation.git
cd FabricPipelineAutomation
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Deploy Azure Infrastructure

```bash
python scripts/setup_azure_resources.py
```

This creates:
- Resource Group: `westusattendiesdata`
- Storage Account: `westusattendiesstore`
- Blob Container: `conference-data`
- Sample data upload
- RBAC assignments

### 4. Deploy Fabric Workspace(s) with GitHub Integration

**Option A: Multi-Workspace Deployment (Recommended for Enterprise)**

Configure and deploy multiple workspaces from a single configuration file:

```bash
# 1. Edit configuration
code config/workspace-config.yaml

# 2. Review workspaces to deploy
python scripts/deploy_workspaces.py --list

# 3. Deploy all enabled workspaces
python scripts/deploy_workspaces.py
```

This automated script:
- ✅ Creates workspaces from configuration
- ✅ Assigns to Fabric capacity
- ✅ Opens browser for Git OAuth (per workspace)
- ✅ Verifies notebook sync from GitHub
- ✅ Guides through Lakehouse and shortcut creation

**Perfect for**: Multi-region, Dev/Test/Prod, team workspaces

📖 **Full Guide**: [Multi-Workspace Deployment Guide](docs/MULTI_WORKSPACE_GUIDE.md)

**Option B: Manual Workspace Setup (Single Workspace)**

For manual control or single workspace deployment:

#### Step 1: Create Workspace
1. Open [Microsoft Fabric](https://app.fabric.microsoft.com/)
2. Click **Workspaces** → **New workspace**
3. Name: **"West US Training"**
4. Select your Fabric capacity

#### Step 2: Connect to GitHub
1. In workspace, go to **Workspace settings** (⚙️)
2. Navigate to **Git integration** tab
3. Click **Connect** to Git
4. Select **GitHub**
5. Authorize Fabric to access your GitHub account
6. Select:
   - **Organization**: Your GitHub username
   - **Repository**: `FabricPipelineAutomation`
   - **Branch**: `main`
   - **Folder**: `/` (root)
7. Click **Connect and sync**

#### Step 3: Import from GitHub
1. After connection, click **Source control** (Git icon in workspace)
2. Select **Update all** to import notebooks from GitHub
3. Notebooks will appear in workspace automatically

### 5. Create Storage Shortcut

1. Open **ConferenceDataLakehouse** in workspace (if imported from Git)
2. Navigate to **Files** → **New shortcut**
3. Select **Azure Data Lake Storage Gen2**
4. Connection details:
   - URL: `https://westusattendiesstore.dfs.core.windows.net/`
   - Auth: Microsoft Entra ID
5. Select container: `conference-data`
6. Click **Create**

### 6. Run Pipeline

1. Open **Load Conference Data** notebook
2. Click **"Run all"**
3. Wait for completion (~2-3 minutes)
4. Verify: Last cell shows "✓ Data pipeline completed successfully!"

### 7. Create Power BI Report

```bash
python scripts/create_powerbi_report.py --workspace-id YOUR_WORKSPACE_ID
```

## 📊 Data Schema

### conference_attendance

| Column | Type | Description |
|--------|------|-------------|
| RegistrationID | string | Unique registration identifier |
| FirstName | string | Attendee first name |
| LastName | string | Attendee last name |
| Email | string | Contact email |
| Company | string | Company name |
| JobTitle | string | Job title |
| RegistrationDate | date | Registration date |
| SessionName | string | Session name |
| SessionDate | date | Session date |
| SessionTime | string | Session time |
| AttendanceStatus | string | Status (Attended/No Show/Cancelled) |
| CheckInTime | string | Check-in timestamp |
| CheckOutTime | string | Check-out timestamp |
| SessionRating | integer | Rating (1-5) |
| FeedbackComments | string | Feedback text |
| LoadDate | timestamp | ETL load timestamp |
| SourceFile | string | Source file name |
| DataFormat | string | CSV or JSON |

## 🔄 GitOps Workflow

### Making Changes to Notebooks

1. **Edit locally**: Modify notebooks in `notebooks/` folder
2. **Commit & push**:
   ```bash
   git add notebooks/
   git commit -m "Update data pipeline"
   git push
   ```
3. **Sync in Fabric**:
   - Open workspace → Click Git icon
   - Click **Update all** to pull latest changes

### Pushing Fabric Changes to GitHub

1. **Edit in Fabric**: Make changes in workspace notebooks
2. **Commit from Fabric**:
   - Click Git icon in workspace
   - Review changes
   - Add commit message
   - Click **Commit**
3. **Changes appear** in GitHub automatically

## 🔐 Security

- **Entra Identity**: All scripts use `DefaultAzureCredential`
- **RBAC**: Automatic role assignments
- **No hardcoded secrets**: Authentication via Azure CLI
- **GitHub PAT**: Stored securely in Fabric workspace

## 🧹 Cleanup

```bash
# Delete Fabric workspace
python scripts/cleanup_all.py --workspace-id YOUR_WORKSPACE_ID

# Delete Azure resources
python scripts/cleanup_all.py --workspace-id YOUR_WORKSPACE_ID --delete-azure
```

## 📖 Documentation

- [Next Steps](NEXT_STEPS.md) - Getting started guide
- [Manual Setup](docs/MANUAL_SETUP_GUIDE.md)
- [Power BI Deployment](docs/POWERBI_DEPLOYMENT.md)

## 👤 Author

**Alexei Khalyako**
- Email: alexeikh@hotmail.com
- GitHub: [@KeykPa](https://github.com/KeykPa)

## 📝 License

MIT License - see LICENSE file for details

---

**Built with Microsoft Fabric & Azure**
