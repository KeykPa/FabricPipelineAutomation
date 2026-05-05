# Databricks notebook source
# MAGIC %md
# MAGIC # Conference Attendance Data Pipeline
# MAGIC 
# MAGIC This notebook loads conference attendance data from Azure Blob Storage
# MAGIC and transforms it into Lakehouse Delta tables.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Storage account configuration
storage_account_name = "westusattendiesstore"
container_name = "conference-data"
lakehouse_name = "ConferenceDataLakehouse"

# File paths
csv_file = "conference_attendance.csv"
json_file = "conference_attendance.json"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Load CSV Data

# COMMAND ----------

from pyspark.sql.functions import *
from pyspark.sql.types import *

# Define schema for CSV
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

# Read CSV from blob storage using abfss protocol
csv_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/{csv_file}"

print(f"Reading CSV from: {csv_path}")

df_csv = spark.read \
    .format("csv") \
    .option("header", "true") \
    .option("inferSchema", "false") \
    .schema(csv_schema) \
    .load(csv_path)

print(f"✓ Loaded {df_csv.count()} records from CSV")
df_csv.show(5)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Transform CSV Data

# COMMAND ----------

# Add processing metadata
df_csv_transformed = df_csv \
    .withColumn("LoadDate", current_timestamp()) \
    .withColumn("SourceFile", lit(csv_file)) \
    .withColumn("DataFormat", lit("CSV"))

# Clean and validate data
df_csv_clean = df_csv_transformed \
    .filter(col("RegistrationID").isNotNull()) \
    .filter(col("Email").isNotNull())

print(f"✓ Transformed data: {df_csv_clean.count()} valid records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Write to Lakehouse Table (CSV Data)

# COMMAND ----------

# Write to Delta table in Lakehouse
table_name = "conference_attendance"

df_csv_clean.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(table_name)

print(f"✓ Data written to table: {table_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Load JSON Data (Optional)

# COMMAND ----------

# Read JSON from blob storage
json_path = f"abfss://{container_name}@{storage_account_name}.dfs.core.windows.net/{json_file}"

print(f"Reading JSON from: {json_path}")

try:
    df_json = spark.read \
        .format("json") \
        .option("multiline", "true") \
        .load(json_path)
    
    # Flatten nested JSON structure
    df_json_flat = df_json.select(
        col("attendanceRecords.registrationID").alias("RegistrationID"),
        col("attendanceRecords.attendee.firstName").alias("FirstName"),
        col("attendanceRecords.attendee.lastName").alias("LastName"),
        col("attendanceRecords.attendee.email").alias("Email"),
        col("attendanceRecords.attendee.company").alias("Company"),
        col("attendanceRecords.attendee.jobTitle").alias("JobTitle"),
        col("attendanceRecords.registration.date").alias("RegistrationDate"),
        col("attendanceRecords.registration.sessionName").alias("SessionName"),
        col("attendanceRecords.registration.sessionDate").alias("SessionDate"),
        col("attendanceRecords.registration.sessionTime").alias("SessionTime"),
        col("attendanceRecords.attendance.status").alias("AttendanceStatus"),
        col("attendanceRecords.attendance.checkInTime").alias("CheckInTime"),
        col("attendanceRecords.attendance.checkOutTime").alias("CheckOutTime"),
        col("attendanceRecords.attendance.sessionRating").alias("SessionRating"),
        col("attendanceRecords.attendance.feedbackComments").alias("FeedbackComments")
    )
    
    print(f"✓ Loaded {df_json_flat.count()} records from JSON")
    
    # Write to separate table
    df_json_flat.write \
        .format("delta") \
        .mode("overwrite") \
        .saveAsTable("conference_attendance_json")
    
    print("✓ JSON data written to table: conference_attendance_json")
    
except Exception as e:
    print(f"Note: JSON load failed or skipped: {str(e)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Data Quality Summary

# COMMAND ----------

# Show summary statistics
print("=== Data Quality Summary ===")
print(f"\nTotal Records: {df_csv_clean.count()}")
print(f"\nUnique Attendees: {df_csv_clean.select('Email').distinct().count()}")
print(f"\nUnique Sessions: {df_csv_clean.select('SessionName').distinct().count()}")
print(f"\nUnique Companies: {df_csv_clean.select('Company').distinct().count()}")

print("\n=== Attendance Status Distribution ===")
df_csv_clean.groupBy("AttendanceStatus").count().orderBy(desc("count")).show()

print("\n=== Top Sessions by Attendance ===")
df_csv_clean.filter(col("AttendanceStatus") == "Attended") \
    .groupBy("SessionName") \
    .count() \
    .orderBy(desc("count")) \
    .show()

print("\n=== Average Session Ratings ===")
df_csv_clean.filter(col("SessionRating").isNotNull()) \
    .groupBy("SessionName") \
    .agg(
        avg("SessionRating").alias("AvgRating"),
        count("*").alias("RatingCount")
    ) \
    .orderBy(desc("AvgRating")) \
    .show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Verify Table in Lakehouse

# COMMAND ----------

# Read back from table to verify
df_verify = spark.table(table_name)

print(f"✓ Table '{table_name}' contains {df_verify.count()} records")
print(f"\nTable Schema:")
df_verify.printSchema()

print(f"\nSample Data:")
df_verify.select(
    "RegistrationID",
    "FirstName", 
    "LastName",
    "Company",
    "SessionName",
    "AttendanceStatus"
).show(10)

# COMMAND ----------

print("✓✓✓ Pipeline Complete! ✓✓✓")
print(f"\nData is now available in Lakehouse table: {table_name}")
print(f"You can query it with SQL or use it in Power BI reports.")
