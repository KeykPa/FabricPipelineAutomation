# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "",
# META       "default_lakehouse_name": "",
# META       "default_lakehouse_workspace_id": ""
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Conference Attendance Data Pipeline
# 
# This notebook loads conference attendance data from Azure Blob Storage and transforms it into Lakehouse Delta tables.
# 
# **What this pipeline does:**
# - Reads CSV/JSON from Azure Blob Storage
# - Transforms and cleans the data
# - Writes to Delta tables in Lakehouse
# - Generates data quality reports

# CELL ********************

# Configuration
storage_account_name = "westusattendiesstore"
container_name = "conference-data"
csv_file = "conference_attendance.csv"
json_file = "conference_attendance.json"

print(f"✓ Configuration loaded")
print(f"  Storage: {storage_account_name}")
print(f"  Container: {container_name}")

# MARKDOWN ********************

# ## Load CSV Data from Blob Storage

# CELL ********************

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

# MARKDOWN ********************

# ## Transform and Clean Data

# CELL ********************

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

# MARKDOWN ********************

# ## Write to Lakehouse Delta Table

# CELL ********************

# Write to Delta table
table_name = "conference_attendance"

df_transformed.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(table_name)

print(f"✓ Data written to table: {table_name}")
print(f"✓ Table location: Tables/{table_name}")

# MARKDOWN ********************

# ## Data Quality Summary

# CELL ********************

# Summary statistics
print("=" * 60)
print("DATA QUALITY SUMMARY")
print("=" * 60)

total_records = df_transformed.count()
unique_attendees = df_transformed.select("Email").distinct().count()
unique_sessions = df_transformed.select("SessionName").distinct().count()
unique_companies = df_transformed.select("Company").distinct().count()

print(f"\n✓ Total Records: {total_records}")
print(f"✓ Unique Attendees: {unique_attendees}")
print(f"✓ Unique Sessions: {unique_sessions}")
print(f"✓ Unique Companies: {unique_companies}")

print("\n--- Attendance Status Distribution ---")
df_transformed.groupBy("AttendanceStatus").count().orderBy(desc("count")).show()

print("\n--- Top Sessions by Attendance ---")
df_transformed.filter(col("AttendanceStatus") == "Attended") \
    .groupBy("SessionName").count() \
    .orderBy(desc("count")).show()

print("\n--- Average Session Ratings ---")
df_transformed.filter(col("SessionRating").isNotNull()) \
    .groupBy("SessionName") \
    .agg(
        avg("SessionRating").alias("AvgRating"),
        count("*").alias("RatingCount")
    ) \
    .orderBy(desc("AvgRating")).show()

# MARKDOWN ********************

# ## Verify Table in Lakehouse

# CELL ********************

# Verify the table
df_verify = spark.table(table_name)

print(f"✓ Table '{table_name}' contains {df_verify.count()} records")
print(f"\nTable Schema:")
df_verify.printSchema()

print("\n" + "=" * 60)
print("✓✓✓ PIPELINE COMPLETE ✓✓✓")
print("=" * 60)
print(f"\nData is available in table: {table_name}")
print("You can now:")
print("  • Query with SQL")
print("  • Create Power BI reports")
print("  • Use in other notebooks")
