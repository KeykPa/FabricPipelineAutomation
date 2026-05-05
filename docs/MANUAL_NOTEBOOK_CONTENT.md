# Manual Notebook Setup - Copy These Cells

## Instructions:
1. Open: https://app.fabric.microsoft.com/groups/00bcfcd2-97d8-48b0-8ae4-67e7395ac373
2. Click "Load Conference Data" notebook
3. Copy each cell below into the notebook

---

## Cell 1 (Markdown):
```markdown
# Conference Attendance Data Pipeline

This notebook loads conference attendance data from Azure Blob Storage and transforms it into Lakehouse Delta tables.

**What this pipeline does:**
- Reads CSV/JSON from Azure Blob Storage
- Transforms and cleans the data
- Writes to Delta tables in Lakehouse
- Generates data quality reports
```

## Cell 2 (Code):
```python
# Configuration
storage_account_name = "westusattendiesstore"
container_name = "conference-data"
csv_file = "conference_attendance.csv"
json_file = "conference_attendance.json"

print(f"✓ Configuration loaded")
print(f"  Storage: {storage_account_name}")
print(f"  Container: {container_name}")
```

## Cell 3 (Markdown):
```markdown
## Load CSV Data from Blob Storage
```

## Cell 4 (Code):
```python
from pyspark.sql.functions import *
from pyspark.sql.types import *

# Define schema
csv_schema = StructType([
    StructField("RegistrationID", StringType(), True),
    StructField("FirstName", StringType(), True),
    StructField("LastName", StringType(), True),
    StructField("Email", StringType(), True),
    StructField("Company", StringType(), True),
    StructField("JobTitle", StringType(), True),
    StructField("RegistrationDate", DateType(), True),
    StructField("SessionName", StringType(), True),
    StructField("SessionDate", DateType(), True),
    StructField("SessionTime", StringType(), True),
    StructField("AttendanceStatus", StringType(), True),
    StructField("CheckInTime", StringType(), True),
    StructField("CheckOutTime", StringType(), True),
    StructField("SessionRating", IntegerType(), True),
    StructField("FeedbackComments", StringType(), True)
])

# Read CSV using abfss protocol
csv_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/{csv_file}"
print(f"Reading from: {csv_path}")

df_csv = spark.read \
    .format("csv") \
    .option("header", "true") \
    .schema(csv_schema) \
    .load(csv_path)

print(f"✓ Loaded {df_csv.count()} records from CSV")
df_csv.show(5, truncate=False)
```

## Cell 5 (Markdown):
```markdown
## Transform and Clean Data
```

## Cell 6 (Code):
```python
# Add metadata and clean data
df_transformed = df_csv \
    .withColumn("LoadDate", current_timestamp()) \
    .withColumn("SourceFile", lit(csv_file)) \
    .withColumn("DataFormat", lit("CSV")) \
    .filter(col("RegistrationID").isNotNull()) \
    .filter(col("Email").isNotNull())

print(f"✓ Cleaned data: {df_transformed.count()} valid records")
print("\nData Preview:")
df_transformed.select("RegistrationID", "FirstName", "LastName", "Company", "SessionName", "AttendanceStatus").show(10)
```

## Cell 7 (Markdown):
```markdown
## Write to Lakehouse Delta Table
```

## Cell 8 (Code):
```python
# Write to Delta table
table_name = "conference_attendance"

df_transformed.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(table_name)

print(f"✓ Data written to table: {table_name}")
print(f"✓ Table location: Tables/{table_name}")
```

## Cell 9 (Markdown):
```markdown
## Data Quality Summary
```

## Cell 10 (Code):
```python
# Summary statistics
print("=" * 60)
print("DATA QUALITY SUMMARY")
print("=" * 60)

# Read back from table
df_table = spark.read.table(table_name)

print(f"\nTotal Records: {df_table.count()}")
print("\nAttendance Status Distribution:")
df_table.groupBy("AttendanceStatus").count().orderBy(desc("count")).show()

print("\nSession Ratings:")
df_table.filter(col("SessionRating").isNotNull()) \
    .groupBy("SessionRating").count() \
    .orderBy("SessionRating").show()

print("\nTop 5 Sessions by Registration:")
df_table.groupBy("SessionName").count() \
    .orderBy(desc("count")).limit(5).show(truncate=False)
```

## Cell 11 (Markdown):
```markdown
## Verification
```

## Cell 12 (Code):
```python
# Final verification
print("✓ Data pipeline completed successfully!")
print(f"\nFinal record count: {spark.read.table(table_name).count()}")
print(f"Table: {table_name}")
print("\nYou can now build Power BI reports on this data!")
```

---

## After copying all cells:
1. Click "Run all" button
2. Wait for completion (~2-3 min)
3. Verify last cell shows success message
