# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "9baf1ed4-1e35-4972-8169-f1ebaa1d6caa",
# META       "default_lakehouse_name": "ConferenceDataLakehouse",
# META       "default_lakehouse_workspace_id": "7e602ac6-c1c2-4da4-a3d9-e4816740af62"
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Conference Attendance Data Pipeline
# 
# This notebook loads conference attendance data from OneLake Files and transforms it into Lakehouse Delta tables.
# 
# **✅ Data files are already uploaded to OneLake:**
# - `Files/conference-data/conference_attendance.csv`
# - `Files/conference-data/conference_attendance.json`
# 
# **What this pipeline does:**
# - ✅ Reads CSV/JSON from OneLake Files
# - ✅ Transforms and cleans the data  
# - ✅ Writes to Delta tables in Lakehouse
# - ✅ Generates data quality reports

# MARKDOWN ********************

# ## Configuration

# CELL ********************

# File paths in OneLake (files already uploaded!)
data_folder = "conference-data"
csv_file = "conference_attendance.csv"
json_file = "conference_attendance.json"

# OneLake file paths
csv_path = f"Files/{data_folder}/{csv_file}"
json_path = f"Files/{data_folder}/{json_file}"

print("=" * 60)
print("✓ Configuration loaded")
print("=" * 60)
print(f"  Data folder: {data_folder}")
print(f"  CSV Path: {csv_path}")
print(f"  JSON Path: {json_path}")
print("=" * 60)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 1. Load CSV Data

# CELL ********************

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

# Read CSV from OneLake Files
print(f"Reading from: {csv_path}")

try:
    df_csv = spark.read \
        .format("csv") \
        .option("header", "true") \
        .option("inferSchema", "false") \
        .schema(csv_schema) \
        .load(csv_path)
    
    print(f"✓ Loaded {df_csv.count()} records from CSV")
    df_csv.show(5)
    
except Exception as e:
    print(f"✗ Error reading file: {e}")
    raise

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

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

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

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

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

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

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

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

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
