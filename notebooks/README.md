# Fabric Notebook Pipeline

This notebook provides a simple Python/PySpark pipeline to load conference attendance data from Azure Blob Storage into Fabric Lakehouse tables.

## What It Does

1. **Reads CSV data** from Azure Blob Storage (`conference_attendance.csv`)
2. **Transforms and cleans** the data
3. **Writes to Delta table** in Lakehouse (`conference_attendance`)
4. **Optionally loads JSON** data (`conference_attendance.json`)
5. **Generates data quality reports**

## Setup Instructions

### 1. Upload Notebook to Fabric

1. Go to your workspace: https://app.fabric.microsoft.com/groups/00bcfcd2-97d8-48b0-8ae4-67e7395ac373
2. Click **+ New** → **Notebook**
3. Copy the content from `load_conference_data.py`
4. Paste into the notebook cells
5. Attach the notebook to your Lakehouse: **ConferenceDataLakehouse**

### 2. Configure Storage Access

The notebook uses **abfss://** protocol which requires authentication. You have two options:

#### Option A: Use Lakehouse Shortcuts (Recommended)

1. In your Lakehouse, go to **Files**
2. Create a **Shortcut** to your blob container:
   - Storage Account: `westusattendiesstore`
   - Container: `conference-data`
3. Update the notebook to use the shortcut path

#### Option B: Configure Storage Credentials

Add this cell at the beginning of the notebook:

```python
# Configure storage account access using service principal or managed identity
spark.conf.set(
    f"fs.azure.account.auth.type.{storage_account_name}.dfs.core.windows.net",
    "OAuth"
)
spark.conf.set(
    f"fs.azure.account.oauth.provider.type.{storage_account_name}.dfs.core.windows.net",
    "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider"
)
```

### 3. Update Configuration

In the notebook, update these variables if needed:

```python
storage_account_name = "westusattendiesstore"  # Your storage account
container_name = "conference-data"              # Your container
lakehouse_name = "ConferenceDataLakehouse"      # Your lakehouse
```

### 4. Run the Notebook

1. Click **Run all** to execute all cells
2. Monitor the progress and check for errors
3. Verify the data in the Lakehouse tables

## Expected Output

- **Delta Table**: `conference_attendance` (20 records from CSV)
- **Optional Table**: `conference_attendance_json` (5 records from JSON)
- **Data Quality Reports**: Attendance statistics, session ratings, etc.

## Using the Data

### Query in SQL

```sql
SELECT 
    SessionName,
    COUNT(*) as Attendees,
    AVG(SessionRating) as AvgRating
FROM conference_attendance
WHERE AttendanceStatus = 'Attended'
GROUP BY SessionName
ORDER BY Attendees DESC
```

### Use in Power BI

1. Create a new Power BI report in your workspace
2. Add a data source → **Lakehouse**
3. Select `conference_attendance` table
4. Build visualizations

## Scheduling

To run this pipeline automatically:

1. Go to your workspace
2. Click the notebook → **Schedule**
3. Set frequency (hourly, daily, etc.)
4. The pipeline will run automatically

## Troubleshooting

**Error: "Path does not exist"**
- Verify storage account and container names
- Check that files were uploaded successfully
- Ensure storage credentials are configured

**Error: "Permission denied"**
- Add "Storage Blob Data Reader" role to your identity
- Or use a Lakehouse shortcut instead

**Error: "Table already exists"**
- The notebook uses `mode("overwrite")` by default
- To append instead, change to `mode("append")`

## Alternative: Simpler Lakehouse Upload

If you prefer, you can upload CSV files directly:

1. Go to Lakehouse → **Files**
2. Upload `conference_attendance.csv`
3. Right-click → **Load to Tables**
4. Fabric will auto-create the table

This is the simplest approach but gives you less control over transformations.
