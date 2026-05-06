# Multi-Workspace Parametrization Guide

## 🎯 Problem

The semantic models and reports synced from Git have **hardcoded connections** to the old workspace's SQL Endpoint. Each workspace needs:

1. **Its own SQL Endpoint connection** in the semantic model
2. **Workspace-specific CSV data** uploaded
3. **Delta tables created** by running the notebook

## 📊 Workspace SQL Endpoint IDs

**Last Updated: 2026-05-06 (Fresh Deployment)**

After deployment, here are the SQL Endpoint IDs for each workspace:

### West US Training
- **Workspace ID**: `a66b6ce9-4716-48ea-aa58-c93d11626d04`
- **Lakehouse ID**: `095eca46-ba23-4e49-b344-c718f55e8e59`
- **SQL Endpoint ID**: `e6d537ff-f837-41b5-b05b-2d9aa5ce861b`
- **Data File**: `west_us_attendance.csv`
- **Records**: 25 (West Coast tech companies)

### East US Training
- **Workspace ID**: `c827aea1-0901-4be3-8b70-be074ac9bd6c`
- **Lakehouse ID**: `6c2b58fd-c022-4238-ac9b-1a144d7d8c26`
- **SQL Endpoint ID**: `e929c471-9c9f-452c-8713-874637d29cc2`
- **Data File**: `east_us_attendance.csv`
- **Records**: 25 (East Coast financial firms)

### Central US Training
- **Workspace ID**: `28dfcaa8-978b-47c8-92c7-1917f5e6a214`
- **Lakehouse ID**: `12711c88-4f94-422d-a5ff-9339cece16c6`
- **SQL Endpoint ID**: `e3b5a3f7-5fb8-4ee7-b28d-637dbe68b435`
- **Data File**: `central_us_attendance.csv`
- **Records**: 25 (Central US industrial companies)

---

## 🔧 Solution: Two Approaches

### Approach 1: Manual Configuration (Quick, Recommended for Now)

For each workspace, manually update the semantic model in Fabric UI:

#### Steps (Per Workspace):

1. **Upload CSV Data**:
   - Open workspace in Fabric
   - Navigate to Lakehouse → Files
   - Create folder: `conference-data`
   - Upload the workspace-specific CSV file
   - Rename to: `conference_attendance.csv`

2. **Run Notebook**:
   - Open "Load Conference Data" notebook
   - Click **Run All**
   - Wait for Delta table creation
   - Verify table: `conference_attendance`

3. **Update Semantic Model**:
   - Open `ConferenceAttendanceSemanticModel`
   - Go to **Settings** → **Data source settings**
   - Update connection:
     - Server: `<generated>.datawarehouse.fabric.microsoft.com`
     - Database: `<SQL Endpoint ID from above>`
   - Click **Apply**
   - Click **Refresh now**

4. **Verify Report**:
   - Open `AttendanceReport`
   - Data should now load correctly
   - Verify it shows ONLY that workspace's data

#### Time: ~5-10 minutes per workspace = 15-30 minutes total

---

### Approach 2: Automated with Git Parametrization (Better Long-Term)

Create workspace-specific semantic model definitions and use Git branches or parameter substitution.

#### Option 2A: Git Branches

Create a branch per workspace with workspace-specific `expressions.tmdl`:

```bash
# Create West US branch
git checkout -b west-us-training
# Update expressions.tmdl with West US SQL Endpoint ID
git commit -m "West US specific semantic model"
git push

# Repeat for East US and Central US
```

Then in `workspace-config.yaml`, point each workspace to its branch:

```yaml
workspaces:
  - name: "West US Training"
    git:
      branch: "west-us-training"
  
  - name: "East US Training"
    git:
      branch: "east-us-training"
  
  - name: "Central US Training"
    git:
      branch: "central-us-training"
```

**Pros**: Fully automated, Git-managed  
**Cons**: Requires separate branches, harder to maintain shared changes

#### Option 2B: Post-Sync Script with TMDL Update

Create a script that:
1. Syncs from Git (main branch)
2. Updates `expressions.tmdl` via Fabric API with workspace-specific SQL Endpoint
3. Commits back to workspace

**Pros**: Single main branch, automated  
**Cons**: Requires Fabric API support for TMDL updates (currently limited)

#### Option 2C: Power BI Parameters

Use Power BI parameters in the semantic model to make the SQL Endpoint configurable:

1. Update `expressions.tmdl` to use a parameter:
   ```
   expression DatabaseQuery =
       let
           ServerAddress = Text.From(ServerParam),
           DatabaseID = Text.From(DatabaseParam),
           database = Sql.Database(ServerAddress, DatabaseID)
       in
           database
   ```

2. Set parameters per workspace via Fabric API

**Pros**: Best practice, reusable  
**Cons**: Requires initial model redesign

---

## 🚀 Recommended Workflow

**For this multi-workspace setup**, I recommend:

### Phase 1: Manual Setup (Now)
Use **Approach 1** to get all 3 workspaces working immediately:
- Upload CSV files manually
- Run notebooks
- Update semantic model connections in UI
- Verify reports

**Time**: 30 minutes total

### Phase 2: Parameterize (Later)
Refactor the semantic model to use **Power BI parameters** (Approach 2C):
- Add ServerParam and DatabaseParam to semantic model
- Update expressions.tmdl to use parameters
- Create deployment script to set parameters via API per workspace
- Test and validate
- Commit to Git

**Benefit**: Future deployments fully automated

---

## 📝 Manual Steps for Each Workspace

### West US Training

```
Workspace: https://app.fabric.microsoft.com/groups/fc615d62-70ff-4e43-9974-643027144ee2

1. Upload Data:
   - File: sample-data/west_us_attendance.csv
   - Path: Lakehouse → Files/conference-data/conference_attendance.csv

2. Run Notebook:
   - Notebook: "Load Conference Data"
   - Action: Run All

3. Update Semantic Model:
   - Model: ConferenceAttendanceSemanticModel
   - SQL Endpoint: 26edfea8-3e0d-4eab-a1cb-e1b54d9f94ee

4. Verify Report:
   - Report: AttendanceReport
   - Expected: 25 West Coast attendees
```

### East US Training

```
Workspace: https://app.fabric.microsoft.com/groups/50990989-81b4-4128-95d0-2eee8eff809a

1. Upload Data:
   - File: sample-data/east_us_attendance.csv
   - Path: Lakehouse → Files/conference-data/conference_attendance.csv

2. Run Notebook:
   - Notebook: "Load Conference Data"
   - Action: Run All

3. Update Semantic Model:
   - Model: ConferenceAttendanceSemanticModel
   - SQL Endpoint: e04e3078-7592-457f-913c-ef742f862576

4. Verify Report:
   - Report: AttendanceReport
   - Expected: 25 East Coast financial firms attendees
```

### Central US Training

```
Workspace: https://app.fabric.microsoft.com/groups/d2e05386-ef7d-40c2-a06e-bc89eadeb810

1. Upload Data:
   - File: sample-data/central_us_attendance.csv
   - Path: Lakehouse → Files/conference-data/conference_attendance.csv

2. Run Notebook:
   - Notebook: "Load Conference Data"
   - Action: Run All

3. Update Semantic Model:
   - Model: ConferenceAttendanceSemanticModel
   - SQL Endpoint: b7cf2b1b-685f-4e37-9afb-abec1aef4d9a

4. Verify Report:
   - Report: AttendanceReport
   - Expected: 25 Central US industrial companies attendees
```

---

## ✅ Verification Checklist

For each workspace, verify:

- [ ] CSV file uploaded to Files/conference-data/
- [ ] Notebook ran successfully
- [ ] Delta table `conference_attendance` exists in Tables/
- [ ] Semantic model connection updated
- [ ] Semantic model refreshed successfully
- [ ] Report loads without errors
- [ ] Report shows ONLY that workspace's data
- [ ] Data count matches (25 records per workspace)
- [ ] Location/Company data is correct for that region

---

## 🔄 Future Automation

To fully automate this for future deployments, we need to:

1. **Refactor Semantic Model**: Add parameters for server and database
2. **Update Deployment Script**: Set parameters via Fabric API after Git sync
3. **Automated Data Upload**: Use OneLake API (already implemented)
4. **Automated Notebook Execution**: Use Fabric Notebook API
5. **Validation**: Automated tests to verify each workspace

This would enable true "one-command" multi-workspace deployment.

---

## 📚 Documentation Updated

- ✅ [MULTI_WORKSPACE_DEPLOYMENT.md](MULTI_WORKSPACE_DEPLOYMENT.md) - Full deployment guide
- ✅ [workspace-config.yaml](config/workspace-config.yaml) - 3 workspaces configured
- ✅ Sample data files created (west_us, east_us, central_us)
- ✅ Deployment script: `deploy_multi_workspace.py`
- ✅ Configuration script: `configure_workspaces.py`
- ✅ This parametrization guide

---

**Next Step**: Complete the manual configuration for all 3 workspaces (30 minutes), then reports will work correctly!
