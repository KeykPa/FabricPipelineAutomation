# Quick Notebook Setup (2 Minutes)

## ✅ Deployment Successful!

**New Workspace Created:**
- Name: **West US Training**
- ID: `07fafa98-29b0-49a0-9464-a80f2f6af2e2`
- Link: https://app.fabric.microsoft.com/groups/07fafa98-29b0-49a0-9464-a80f2f6af2e2

**Resources Created:**
- ✅ Lakehouse: ConferenceDataLakehouse
- ✅ Notebook: Load Conference Data (EMPTY - needs manual setup)

---

## 🔧 Final Setup Steps

### Step 1: Add Notebook Content (2 minutes)

The Fabric API doesn't properly upload notebook content, so we need to manually copy it.

**Option A: Import the notebook file (FASTEST - 30 seconds)**
1. Open workspace: https://app.fabric.microsoft.com/groups/07fafa98-29b0-49a0-9464-a80f2f6af2e2
2. Click **"New"** button → **"Import notebook"**
3. Upload file: `C:\Users\akhalyako\OneDrive - Microsoft\VSCode\FabricPipeAutomation\notebooks\load_conference_data.ipynb`
4. Name it "Load Conference Data v2" (or delete empty one first)

**Option B: Use VS Code notebook (1 minute)**
1. In VS Code, open: `notebooks/load_conference_data.ipynb`
2. Select all cells (Ctrl+A)
3. Copy (Ctrl+C)
4. Open Fabric notebook: https://app.fabric.microsoft.com/groups/07fafa98-29b0-49a0-9464-a80f2f6af2e2
5. Click "Load Conference Data" notebook
6. Paste cells (Ctrl+V)

**Option C: Manual cell-by-cell (5 minutes)**
See detailed guide: `docs/MANUAL_NOTEBOOK_CONTENT.md`

---

### Step 2: Create Storage Shortcut (1 minute)

1. In workspace, click **ConferenceDataLakehouse**
2. In left panel, click **"Files"**
3. Click **"New shortcut"**
4. Select **"Azure Data Lake Storage Gen2"**
5. Enter connection:
   - **URL**: `https://westusattendiesstore.dfs.core.windows.net/`
   - **Authentication**: Use Microsoft Entra ID (your current login)
6. Click **Next**
7. Select container: **conference-data**
8. Name: **conference-data**
9. Click **Create**

---

### Step 3: Run Notebook (2 minutes)

1. Open **"Load Conference Data"** notebook
2. Click **"Run all"** button
3. Wait for completion (~2-3 min)
4. Verify last cell shows: "✓ Data pipeline completed successfully!"

---

### Step 4: Create Power BI Report (3 minutes)

After notebook completes:

1. Run this command:
   ```powershell
   python scripts/create_powerbi_report.py --workspace-id 07fafa98-29b0-49a0-9464-a80f2f6af2e2
   ```

2. Script will:
   - Find the auto-created semantic model
   - Create a blank Power BI report
   - Provide instructions for adding visuals

3. Add visuals following guide: `powerbi-templates/README.md`

---

## 📊 Final Architecture

```
Azure Blob Storage (westusattendiesstore)
  └── conference-data container
       ├── conference_attendance.csv
       └── conference_attendance.json
            ↓ (Storage Shortcut)
Fabric Lakehouse (ConferenceDataLakehouse)
  └── Files/conference-data/
       ├── *.csv
       └── *.json
            ↓ (PySpark Notebook)
  └── Tables/
       └── conference_attendance (Delta)
            ↓ (Auto-generated)
Semantic Model
  └── Direct Lake connection
       ↓
Power BI Report
  └── Attendance Dashboard
```

---

## ⏱️ Total Time Estimate

- ✅ Azure deployment: DONE
- ✅ Fabric workspace: DONE  
- ⚠️ Notebook import: 1 minute
- ⚠️ Storage shortcut: 1 minute
- ⚠️ Run notebook: 2 minutes
- ⚠️ Create report: 3 minutes
- ⚠️ Add visuals: 5 minutes

**Total remaining: ~12 minutes**

---

## 🎯 Next Action

**Start here:**  
Open: https://app.fabric.microsoft.com/groups/07fafa98-29b0-49a0-9464-a80f2f6af2e2

Then choose your preferred method to add notebook content (Option A is fastest).
