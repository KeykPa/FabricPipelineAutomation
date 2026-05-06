# 🏠 Default Lakehouse Assignment Guide

## ✅ Automation Success Summary

The automation script has successfully completed:

### Automated Steps (✅ Complete)
1. **Data Upload** - CSV files uploaded to OneLake for all 3 workspaces
   - ✅ West US Training: 2,983 bytes
   - ✅ East US Training: 3,131 bytes  
   - ✅ Central US Training: 3,067 bytes

2. **Notebook Execution** - Started for all 3 workspaces
   - ✅ West US Training: Running
   - ✅ East US Training: Running
   - ✅ Central US Training: Running

---

## ⚠️ Manual Step Required: Assign Default Lakehouse

### Why This Is Needed

When notebooks are synced from Git, they may have a reference to a lakehouse from a different workspace. Each notebook needs its default lakehouse set to **the lakehouse in its own workspace**.

**Error you'll see:** 
```
Default Lakehouse "ConferenceDataLakehouse (9baf1ed4-1e35-4972-8169-f1ebaa1d6caa)" is not accessible.
To access Lakehouse data, choose an accessible default Lakehouse and restart the Spark session.
```

---

## 📋 Manual Steps (5 minutes per workspace)

### For Each Workspace:

#### 1. Open the Workspace
Navigate to the workspace in Fabric:
- West US Training: https://app.fabric.microsoft.com/groups/fc615d62-70ff-4e43-9974-643027144ee2
- East US Training: https://app.fabric.microsoft.com/groups/50990989-81b4-4128-95d0-2eee8eff809a
- Central US Training: https://app.fabric.microsoft.com/groups/d2e05386-ef7d-40c2-a06e-bc89eadeb810

#### 2. Open the Notebook
1. Find **"Load Conference Data"** notebook
2. Click to open it

#### 3. Assign Default Lakehouse
1. Look for the **"Add lakehouse"** button or link (usually in the left panel or top ribbon)
2. Click **"Add lakehouse"**
3. Select **"Existing lakehouse"**
4. Choose **"ConferenceDataLakehouse"** from the list
5. Click **"Add"**

Alternatively:
1. Click the **lakehouse icon** in the left sidebar
2. Click **"Add"** or **"+ Add lakehouse"**
3. Select **"Existing lakehouse"**
4. Choose **"ConferenceDataLakehouse"**
5. Click **"Add"**

#### 4. Verify and Run
1. You should now see the lakehouse in the left panel with folders:
   - Files
   - Tables
2. Click **"Run All"** to execute the notebook
3. Wait ~30 seconds for completion
4. Verify the **"conference_attendance"** table is created under **Tables**

---

## 🎯 Repeat for All 3 Workspaces

| Workspace | Notebook | Lakehouse to Add | Status |
|-----------|----------|------------------|--------|
| **West US Training** | Load Conference Data | ConferenceDataLakehouse | ⬜ Not done |
| **East US Training** | Load Conference Data | ConferenceDataLakehouse | ⬜ Not done |
| **Central US Training** | Load Conference Data | ConferenceDataLakehouse | ⬜ Not done |

---

## ✅ After Completion

Once all notebooks have run successfully, you'll see:

1. **Delta Table Created**: `conference_attendance` table in each lakehouse
2. **Data Rows**: 25 records in each workspace
3. **Ready for Reporting**: Semantic models can now connect

---

## 🔮 Future Automation (Optional)

To fully automate default lakehouse assignment in future deployments, we can:

### Option 1: Update Notebook Definition via API
Modify the notebook's `artifact.metadata.json` to include:
```json
{
  "defaultLakehouse": {
    "name": "ConferenceDataLakehouse",
    "id": "<lakehouse-id>",
    "workspaceId": "<workspace-id>"
  }
}
```

### Option 2: Use Fabric Data Pipeline
Create a pipeline that:
1. Checks if lakehouse is assigned
2. Assigns it if not present
3. Executes the notebook
4. Refreshes the semantic model

See: `fabric-pipeline/automated-etl-pipeline.json`

---

## 📞 Troubleshooting

### "Lakehouse not found" when trying to add
- **Solution**: Ensure the lakehouse "ConferenceDataLakehouse" exists in the workspace
- Check in the workspace's item list

### Notebook fails to run after adding lakehouse  
- **Solution**: Restart the Spark session
- Click the **"Stop session"** button, then try **"Run All"** again

### Data file not found
- **Solution**: Check if the CSV was uploaded to OneLake
- Navigate to: Lakehouse → Files → conference-data → conference_attendance.csv
- If missing, check the automation script output

---

## 🎊 Next Steps

After assigning default lakehouses and running all notebooks:

1. **Update Semantic Model Connections** (see [WORKSPACE_PARAMETRIZATION_GUIDE.md](WORKSPACE_PARAMETRIZATION_GUIDE.md))
2. **Refresh Semantic Models**
3. **Verify Reports Display Data**
4. **(Optional) Set up Fabric Data Pipelines for automation**

---

## 📚 Related Documentation

- [WORKSPACE_PARAMETRIZATION_GUIDE.md](WORKSPACE_PARAMETRIZATION_GUIDE.md) - Semantic model configuration
- [MULTI_WORKSPACE_DEPLOYMENT.md](MULTI_WORKSPACE_DEPLOYMENT.md) - Full deployment guide
- [scripts/automate_workspaces.py](scripts/automate_workspaces.py) - Automation script source code
