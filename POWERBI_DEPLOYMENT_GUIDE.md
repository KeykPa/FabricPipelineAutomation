# Power BI Report Deployment Guide

## Quick Steps to Complete the Pipeline

### Step 1: Run the Notebook (Manual - 2 minutes)

Since the Fabric API for running notebooks has limitations, run it manually:

1. **Open the notebook:**
   ```
   https://app.fabric.microsoft.com/groups/7e602ac6-c1c2-4da4-a3d9-e4816740af62/synapsenotebooks/9cf234dd-0d01-4916-8862-8d62bbde8d98
   ```

2. **Click "Run all"** button

3. **Wait for completion** (~1-2 minutes)
   - You'll see: "✓✓✓ PIPELINE COMPLETE ✓✓✓"
   - Table created: `conference_attendance`

### Step 2: Create Semantic Model & Power BI Report (Automated)

Once the notebook completes, run this script:

```powershell
python scripts/deploy_end_to_end.py `
  --workspace-id 7e602ac6-c1c2-4da4-a3d9-e4816740af62 `
  --notebook-id 9cf234dd-0d01-4916-8862-8d62bbde8d98 `
  --skip-notebook
```

This will:
- ✅ Find the auto-created semantic model from the lakehouse
- ✅ Create a Power BI report bound to the model
- ✅ Give you the report URL

### Step 3: Add Visuals to Report

Open the report URL and add visuals:

**Page 1 - Overview:**
- **Card**: Total Registrations
  - Field: `RegistrationID` (Count)
  
- **Card**: Total Attended  
  - Field: `RegistrationID` (Count)
  - Filter: `AttendanceStatus = "Attended"`
  
- **Card**: Attendance Rate
  - DAX Measure:
    ```dax
    Attendance Rate = 
    DIVIDE(
        CALCULATE(COUNT(conference_attendance[RegistrationID]), 
                 conference_attendance[AttendanceStatus] = "Attended"),
        COUNT(conference_attendance[RegistrationID]),
        0
    )
    ```

- **Donut Chart**: Attendance by Status
  - Legend: `AttendanceStatus`
  - Values: `RegistrationID` (Count)

- **Bar Chart**: Top Sessions
  - Axis: `SessionName`
  - Values: `RegistrationID` (Count)
  - Sort by: Values descending

**Page 2 - Attendee List:**
- **Table**: 
  - Columns: `FirstName`, `LastName`, `Email`, `Company`, `JobTitle`, `SessionName`, `AttendanceStatus`, `SessionRating`

**Page 3 - Session Analytics:**
- **Matrix**: Session Performance
  - Rows: `SessionName`
  - Values: 
    - Registrations (Count of `RegistrationID`)
    - Attended (Count where `AttendanceStatus = "Attended"`)
    - Avg Rating (Average of `SessionRating`)

## Alternative: Fully Manual Approach

If you prefer to do everything manually:

### 1. Run Notebook
   - Open workspace → Load Conference Data notebook → Run all

### 2. Create Report in Power BI Service
   - In workspace, click **New** → **Report**
   - Select data source: **ConferenceDataLakehouse** (default semantic model)
   - Click **Create**

### 3. Add Visuals
   - Follow visual templates above

---

## Files Updated

- ✅ `scripts/deploy_end_to_end.py` - End-to-end automation script
- ✅ `LoadConferenceData.Notebook/.platform` - Updated with new notebook ID
- ✅ Data files uploaded to OneLake: `Files/conference-data/`

## Current Status

| Component | Status | ID |
|-----------|--------|-----|
| Lakehouse | ✅ Created | `9baf1ed4-1e35-4972-8169-f1ebaa1d6caa` |
| Data Files | ✅ Uploaded | `Files/conference-data/` |
| Notebook | ✅ Synced from Git | `9cf234dd-0d01-4916-8862-8d62bbde8d98` |
| Delta Table | ⏳ Pending | Run notebook |
| Semantic Model | ⏳ Auto-created | After table creation |
| Power BI Report | ⏳ To create | After semantic model |

---

**Next Action:** Run the notebook in Fabric UI, then execute the automation script!
