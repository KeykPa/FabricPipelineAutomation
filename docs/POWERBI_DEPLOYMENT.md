# Power BI Report Deployment Guide

## 🎯 Overview

This guide walks you through deploying the Conference Attendance Power BI report to your Fabric workspace.

## 📋 Prerequisites

✅ **Already Completed**:
- Azure resources deployed (Resource Group, Storage Account, Blob Container)
- Fabric workspace created: "West US Training"
- Lakehouse created: "ConferenceDataLakehouse"
- Notebook created: "Load Conference Data"
- Sample data uploaded to blob storage

⚠️ **Still Required**:
- Load data into Lakehouse (run notebook)
- Create Power BI report with visuals

## 🚀 Automated Deployment (3 Steps)

### Step 1: Load Data into Lakehouse

**Option A: Run Notebook in Fabric Workspace** (Recommended for first time)

1. Open workspace: https://app.fabric.microsoft.com/groups/00bcfcd2-97d8-48b0-8ae4-67e7395ac373

2. Find and click **"Load Conference Data"** notebook

3. Click **"Run all"** button

4. Wait for all cells to execute (~ 2-3 minutes)

5. Verify success:
   - Check last cell output shows "Data loaded successfully"
   - In Lakehouse, verify **conference_attendance** table exists

**Option B: Run from Python** (For automation)

```bash
# Coming soon - API endpoint under development
python scripts/run_notebook.py --workspace-id <workspace-id> --notebook-id <notebook-id>
```

### Step 2: Verify Semantic Model Created

After notebook runs successfully, Fabric **automatically creates a semantic model** from your Lakehouse.

To verify:

1. Refresh workspace view

2. Look for item: **"ConferenceDataLakehouse"** with type **"Semantic model"** or **"Dataset"**

3. Click to open - you should see the **conference_attendance** table

**Note**: Semantic model creation may take 1-2 minutes after notebook completes.

### Step 3: Create Power BI Report

Now run the automated script:

```bash
python scripts/create_powerbi_report.py \
    --workspace-id 00bcfcd2-97d8-48b0-8ae4-67e7395ac373 \
    --lakehouse-name ConferenceDataLakehouse \
    --report-name "Conference Attendance Report"
```

This creates a **blank report** bound to your semantic model.

**Output**:
```
✓ Found semantic model: ConferenceDataLakehouse
  ID: <model-id>
✓ Report created!
  ID: <report-id>
  URL: https://app.powerbi.com/groups/.../reports/...
```

## 🎨 Step 4: Add Visuals to Report

The report is created but empty. You need to add visuals:

### Option A: Edit in Power BI Service (Web)

1. Click the report URL from Step 3 output

2. Click **"Edit"** button (top bar)

3. **Add Visuals**:

#### Page 1: Overview

**KPI Cards** (Add 4 cards):
1. Total Registrations: `COUNT(RegistrationID)`
2. Total Attended: `COUNT(RegistrationID)` with filter `AttendanceStatus = "Attended"`
3. Attendance Rate: Create measure:
   ```dax
   Attendance Rate = 
   DIVIDE(
       COUNTROWS(FILTER(conference_attendance, [AttendanceStatus] = "Attended")),
       COUNTROWS(conference_attendance),
       0
   )
   ```
   Format as percentage

4. Avg Session Rating: `AVERAGE(SessionRating)` with filter `SessionRating <> BLANK()`

**Donut Chart**: Attendance by Status
- **Legend**: AttendanceStatus
- **Values**: COUNT(RegistrationID)

**Bar Chart**: Session Popularity
- **Axis**: SessionName
- **Values**: COUNT(RegistrationID)
- Sort by values descending

**Column Chart**: Rating Distribution
- **Axis**: SessionRating
- **Values**: COUNT(RegistrationID)

#### Page 2: Attendee List

**Table**:
- Columns: FirstName, LastName, Email, Company, JobTitle, SessionName, AttendanceStatus, SessionRating
- Enable search, filter, and sort
- **Conditional Formatting**:
  - AttendanceStatus: Green background for "Attended", Red for "No-show"
  - SessionRating: Green for >= 4, Red for <= 2

#### Page 3: Session Analytics

**Matrix**: Session Performance
- **Rows**: SessionName
- **Values**: 
  - Registrations = COUNT(RegistrationID)
  - Attended = COUNTROWS(FILTER(...))
  - Attendance% = DIVIDE([Attended], [Registrations])
  - Avg Rating = AVERAGE(SessionRating)

**Treemap**: Attendees by Company
- **Category**: Company
- **Values**: COUNT(RegistrationID)

4. **Save** the report

### Option B: Edit in Power BI Desktop

1. In workspace, click **"..."** on report → **"Download this file"** → **".pbix"**

2. Open in **Power BI Desktop**

3. Add visuals as described above (easier interface)

4. **File** → **Publish** → Select workspace

5. Overwrite existing report

## 📊 Visual Reference

Full template with layout, colors, and DAX measures:
- See: `powerbi-templates/README.md`
- JSON definition: `powerbi-templates/attendance-report-template.json`

## 🔄 Data Refresh

Configure automatic daily refresh:

1. In workspace, click **semantic model** (ConferenceDataLakehouse)

2. **Settings** → **Scheduled refresh**

3. **Configure**:
   - Frequency: Daily
   - Time: 6:00 AM
   - Time zone: Your local time
   - Email on failure: Your email

4. **Apply**

## ✅ Verification Checklist

- [ ] Notebook executed successfully
- [ ] Semantic model visible in workspace
- [ ] Power BI report created
- [ ] Report contains 3 pages
- [ ] Page 1: Overview with KPIs and charts
- [ ] Page 2: Attendee list table
- [ ] Page 3: Session analytics
- [ ] Visuals display data correctly
- [ ] Filters work (Date, Company, Status)
- [ ] Scheduled refresh configured
- [ ] Report shared with stakeholders

## 🎯 Quick Links

- **Workspace**: https://app.fabric.microsoft.com/groups/00bcfcd2-97d8-48b0-8ae4-67e7395ac373
- **Template Reference**: [powerbi-templates/README.md](../powerbi-templates/README.md)
- **Sample Data**: [sample-data/conference_attendance.csv](../sample-data/conference_attendance.csv)

## 🔧 Troubleshooting

### Semantic Model Not Created

**Symptom**: After running notebook, no semantic model appears

**Solution**:
1. Verify notebook completed all cells
2. Check Lakehouse has `conference_attendance` table
3. Wait 2-3 minutes, refresh workspace
4. If still missing, run notebook again

### Report Shows "No Data"

**Symptom**: Visuals are empty or show "No data to display"

**Solution**:
1. Verify semantic model has data: Click model → Data tab
2. Check table name is exactly `conference_attendance`
3. Refresh semantic model: Settings → Refresh now
4. Re-open report

### Cannot Edit Report

**Symptom**: No "Edit" button in report

**Solution**:
1. Ensure you have "Contributor" or "Admin" role in workspace
2. Try opening direct URL with `/edit`: `https://app.powerbi.com/groups/<workspace-id>/reports/<report-id>/ReportSection?experience=power-bi&clientSideAuth=0`

## 🚀 Next Steps

Once report is deployed:

1. **Customize branding**: Add company logo, colors
2. **Add filters**: Date slicers, dropdowns
3. **Create bookmarks**: Save common views
4. **Set up alerts**: Email on low attendance
5. **Share**: Publish to stakeholders
6. **Embed**: Add to SharePoint or Teams

## 📦 Full Automation (Future)

Currently automating:
- ✅ Azure infrastructure
- ✅ Fabric workspace
- ✅ Lakehouse creation
- ✅ Notebook creation
- ✅ Report scaffolding
- ⚠️ Notebook execution (manual step)
- ⚠️ Visual configuration (manual step)

Future enhancements:
- Notebook API execution (when GA)
- PBIX template upload
- Programmatic visual generation via PBIT

---

**Need help?** Check the main [README.md](../README.md) or [QUICKSTART.md](../QUICKSTART.md)
