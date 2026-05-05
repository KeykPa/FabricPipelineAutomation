# Fabric Pipeline Deployment Guide

## ✅ What's Already Deployed

Your infrastructure is ready with **Entra identity authentication**:

- **Resource Group**: `westusattendiesdata` (West US)
- **Storage Account**: `westusattendiesstore`
- **Blob Container**: `conference-data` (with CSV + JSON files uploaded)
- **Fabric Workspace**: `West US Training`
- **Workspace ID**: `00bcfcd2-97d8-48b0-8ae4-67e7395ac373`
- **Capacity**: `akhfabcapacity`

**Access your workspace**: https://app.fabric.microsoft.com/groups/00bcfcd2-97d8-48b0-8ae4-67e7395ac373

## 🎯 Next Steps: Load Data into Lakehouse

You have **3 options** to load your CSV/JSON data into Lakehouse tables:

---

### **Option 1: Notebook Pipeline (Recommended)** 🚀

**Best for**: Automated ETL with transformations and data quality checks

**Steps**:

1. **Create a Lakehouse**:
   - Go to your workspace
   - Click **+ New** → **Lakehouse**
   - Name it: `ConferenceDataLakehouse`

2. **Upload the Notebook**:
   - Click **+ New** → **Notebook**
   - Copy content from `notebooks/load_conference_data.py`
   - Paste into notebook cells

3. **Attach to Lakehouse**:
   - In the notebook, click **Add lakehouse**
   - Select `ConferenceDataLakehouse`

4. **Configure Storage Access**:
   
   Add this at the top of the notebook:
   ```python
   # Your values
   storage_account_name = "westusattendiesstore"
   container_name = "conference-data"
   ```

5. **Set Up Authentication**:

   **Option A - Lakehouse Shortcut (Easiest)**:
   - In Lakehouse → **Files** → **New shortcut**
   - Select **Azure Data Lake Storage Gen2**
   - URL: `https://westusattendiesstore.dfs.core.windows.net/conference-data`
   - Use your Entra identity to authenticate
   - Update notebook path to use the shortcut

   **Option B - Direct Access**:
   - Ensure your user has "Storage Blob Data Reader" role
   - The notebook will use DefaultAzureCredential automatically

6. **Run the Notebook**:
   - Click **Run all**
   - Monitor execution
   - Verify table: `conference_attendance`

7. **Schedule** (optional):
   - Click the notebook name → **Settings**
   - Set up recurring schedule

**Pros**: Full control, transformations, data quality checks  
**Cons**: Requires notebook setup

---

### **Option 2: Direct File Upload** 📁

**Best for**: Quick testing, no transformations needed

**Steps**:

1. **Create a Lakehouse**:
   - Go to your workspace
   - Click **+ New** → **Lakehouse**
   - Name it: `ConferenceDataLakehouse`

2. **Download sample files** from the project:
   - `sample-data/conference_attendance.csv`

3. **Upload to Lakehouse**:
   - Go to Lakehouse → **Files**
   - Click **Upload** → **Upload files**
   - Select `conference_attendance.csv`

4. **Load to Table**:
   - Right-click the uploaded CSV file
   - Select **Load to Tables**
   - Fabric auto-creates the table

**Pros**: Simplest, no code required  
**Cons**: Limited transformations, manual process

---

### **Option 3: Data Pipeline (Manual Creation)** 🔄

**Best for**: GUI-based workflow, scheduled loads

Since the API deployment didn't work, create manually:

**Steps**:

1. **Create Data Pipeline**:
   - Go to your workspace
   - Click **+ New** → **Data pipeline**
   - Name it: `ConferenceAttendancePipeline`

2. **Add Copy Activity**:
   - Drag **Copy data** activity to canvas
   - **Source**:
     - Type: Azure Blob Storage
     - Account: `westusattendiesstore`
     - Container: `conference-data`
     - File: `conference_attendance.csv`
   - **Destination**:
     - Type: Lakehouse
     - Lakehouse: `ConferenceDataLakehouse`
     - Table: `conference_attendance`

3. **Configure Authentication**:
   - Use **Azure AD authentication** (Entra identity)
   - Grant pipeline access to storage account

4. **Test Run**:
   - Click **Validate** → **Debug**
   - Check execution results

5. **Schedule**:
   - Click **Schedule**
   - Set frequency (daily, hourly, etc.)

**Pros**: Visual designer, built-in scheduling  
**Cons**: Requires manual setup in portal

---

## 🔐 Authentication & Permissions

All scripts use **Entra identity (DefaultAzureCredential)**:

- ✅ `upload_to_blob.py` - uses Azure SDK with Entra identity
- ✅ `setup_azure_resources.py` - uses Azure SDK with Entra identity  
- ✅ Azure CLI integration for resource management

**Required Roles**:
- **Storage Blob Data Contributor** on `westusattendiesstore` (already assigned ✓)
- **Contributor** on workspace (for creating items)

---

## 📊 Query Your Data

Once loaded, query with SQL:

```sql
-- Top sessions by attendance
SELECT 
    SessionName,
    COUNT(*) as TotalAttendees,
    AVG(CAST(SessionRating AS FLOAT)) as AvgRating
FROM conference_attendance
WHERE AttendanceStatus = 'Attended'
GROUP BY SessionName
ORDER BY TotalAttendees DESC;
```

---

## 🎨 Build Power BI Reports

1. In your workspace → **+ New** → **Report**
2. Select data source → **Lakehouse**
3. Choose `conference_attendance` table
4. Build visualizations:
   - Attendance by session
   - Company participation
   - Session ratings
   - Time-based trends

---

## 📝 Summary

**Recommended Path**:
1. Create Lakehouse: `ConferenceDataLakehouse`
2. Upload & run notebook: `notebooks/load_conference_data.py`
3. Verify table: `conference_attendance`
4. Build Power BI report

**Your data is ready** in blob storage using Entra identity authentication. Choose the option that works best for your use case! 🎉
