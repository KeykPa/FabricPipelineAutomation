# Manual Setup Guide for Fabric Lakehouse & Notebook

## ⚠ Why Manual Setup is Needed

The Fabric API returned error **"FeatureNotAvailable"** because the **Data Engineering workload** is not enabled on your capacity. This configuration **cannot be automated via API** and requires manual setup through the Fabric Admin Portal.

## ✅ What's Already Deployed

Your Azure infrastructure is **completely ready**:

- ✅ **Resource Group**: `westusattendiesdata`
- ✅ **Storage Account**: `westusattendiesstore`
- ✅ **Blob Container**: `conference-data`
- ✅ **Sample Data**: CSV and JSON files uploaded using Entra identity
- ✅ **Fabric Workspace**: `West US Training` (ID: 00bcfcd2-97d8-48b0-8ae4-67e7395ac373)

**All authentication uses Entra identity - secure and enterprise-ready!**

---

## 🎯 Option 1: Enable Data Engineering (Recommended for API Automation)

### Step 1: Open Fabric Admin Portal

Go to: **https://app.fabric.microsoft.com/admin**

### Step 2: Navigate to Your Capacity

1. Click **Settings** (gear icon) → **Admin portal**
2. Select **Capacity settings**
3. Click **Fabric capacity** tab
4. Find and select your capacity: **akhfabcapacity**

### Step 3: Enable Data Engineering Workload

1. Scroll to **Data Engineering/Science Settings**
2. Click **Open Spark Compute**
3. Configure the following:
   - ✅ **Enable Starter Pool** (recommended for development)
   - Set **Node size** and **autoscaling** preferences
   - Configure **Max nodes** based on workload needs
4. Click **Save**

### Step 4: Wait for Propagation

- Wait **2-3 minutes** for settings to propagate
- Capacity workload changes take a moment to activate

### Step 5: Re-run Automated Deployment

Once Data Engineering is enabled, run:

```bash
python scripts/deploy_fabric_workspace.py \
    --workspace-id 00bcfcd2-97d8-48b0-8ae4-67e7395ac373 \
    --storage-account westusattendiesstore
```

This will now successfully create the Lakehouse and Notebook via API!

---

## 🎯 Option 2: Manual Creation (Fastest for Immediate Setup)

If you want to get started **right now** without enabling the API:

### Step 1: Create Lakehouse

1. **Go to your workspace**:  
   https://app.fabric.microsoft.com/groups/00bcfcd2-97d8-48b0-8ae4-67e7395ac373

2. **Create Lakehouse**:
   - Click **+ New** → **Lakehouse**
   - Name: `ConferenceDataLakehouse`
   - Click **Create**

### Step 2: Create Storage Shortcut

1. **In the Lakehouse**, go to **Files** section
2. Click **New shortcut**
3. Select: **Azure Data Lake Storage Gen2**
4. Configure:
   - **URL**: `https://westusattendiesstore.dfs.core.windows.net/conference-data`
   - **Connection**: New connection
   - **Authentication**: **Organizational account** (uses your Entra identity)
5. Click **Next** → **Create**

**Result**: Your Lakehouse can now access the blob storage data directly!

### Step 3: Create Notebook

1. **In the workspace**, click **+ New** → **Notebook**
2. **Name it**: `Load Conference Data`
3. **Attach to Lakehouse**:
   - Click **Add lakehouse** (left panel)
   - Select `ConferenceDataLakehouse`

### Step 4: Add Notebook Code

Copy the code from: **`notebooks/load_conference_data.ipynb`** in this project.

**Quick version - paste this into a new cell:**

```python
# Configuration
storage_account_name = "westusattendiesstore"
container_name = "conference-data"
csv_file = "conference_attendance.csv"
json_file = "conference_attendance.json"

# Read CSV
from pyspark.sql.types import *
csv_schema = StructType([
    StructField("RegistrationID", StringType(), True),
    StructField("FirstName", StringType(), True),
    StructField("LastName", StringType(), True),
    StructField("Email", StringType(), True),
    StructField("Company", StringType(), True),
    StructField("JobTitle", StringType(), True),
    StructField("RegistrationDate", StringType(), True),
    StructField("SessionName", StringType(), True),
    StructField("SessionDate", StringType(), True),
    StructField("SessionTime", StringType(), True),
    StructField("AttendanceStatus", StringType(), True),
    StructField("CheckInTime", StringType(), True),
    StructField("CheckOutTime", StringType(), True),
    StructField("SessionRating", IntegerType(), True),
    StructField("FeedbackComments", StringType(), True)
])

csv_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/{csv_file}"
df_csv = spark.read.format("csv").option("header", "true").schema(csv_schema).load(csv_path)

# Write to Delta Table
df_csv.write.format("delta").mode("overwrite").saveAsTable("conference_attendance")

print("✓ Data loaded successfully!")
print(f"Total records: {df_csv.count()}")
```

### Step 5: Run the Notebook

1. Click **Run all**
2. Wait for completion (~30 seconds)
3. Verify table created: `conference_attendance`

---

## 🔍 Verify Your Setup

### Query the Data

In a new notebook cell or SQL endpoint:

```sql
SELECT 
    AttendanceStatus,
    COUNT(*) as Count
FROM conference_attendance
GROUP BY AttendanceStatus
ORDER BY Count DESC
```

### Expected Output:

| AttendanceStatus | Count |
|------------------|-------|
| Attended         | 10    |
| Registered       | 5     |
| No-show          | 3     |
| Cancelled        | 2     |

---

## 📊 Next Steps

### Power BI Integration

1. **In your workspace**, click **+ New** → **Semantic model**
2. Select source: **OneLake data hub**
3. Choose: `ConferenceDataLakehouse` → `conference_attendance` table
4. Build reports!

### Schedule the Notebook

1. Open the notebook
2. Click **Notebook schedules** (top menu)
3. Set recurring schedule (daily, weekly, etc.)

### Add More Data

Upload additional CSV/JSON files to blob storage:

```bash
python scripts/upload_to_blob.py \
    --storage-account westusattendiesstore \
    --container conference-data \
    --file your-new-data.csv
```

Then re-run the notebook to refresh tables.

---

## 🆘 Troubleshooting

### "Cannot access blob storage"

- Ensure your Entra identity has **Storage Blob Data Reader** role
- The setup script already assigned **Storage Blob Data Contributor** to your account
- Wait a few minutes for role propagation

### "Table not found"

- Verify notebook ran successfully
- Check Lakehouse → **Tables** section
- Table name: `conference_attendance`

### "Shortcut creation failed"

- Ensure Data Engineering workload is enabled
- Use **Organizational account** authentication (not SAS or key)
- Verify storage account name and container are correct

---

## 📚 Documentation References

- [Fabric Lakehouse Overview](https://learn.microsoft.com/fabric/data-engineering/lakehouse-overview)
- [OneLake Shortcuts](https://learn.microsoft.com/fabric/onelake/onelake-shortcuts)
- [Fabric Notebooks](https://learn.microsoft.com/fabric/data-engineering/how-to-use-notebook)
- [Data Engineering Settings](https://learn.microsoft.com/fabric/data-engineering/capacity-settings-management)

---

## 🎉 Summary

**Current Status:**
- ✅ Azure infrastructure fully deployed
- ✅ Sample data uploaded to blob storage
- ✅ Fabric workspace created
- ⚠️ Lakehouse & Notebook need manual creation (API not enabled)

**Time Required:**
- Option 1 (Enable API): 10-15 minutes total (5 min enable + 5 min wait + automated deployment)
- Option 2 (Manual): 5-10 minutes (create resources manually, immediate)

**Recommendation:**
- Use **Option 2** for immediate setup
- Then enable Data Engineering workload for future automation

**All authentication uses Entra identity - no keys or connection strings needed!** 🔐
