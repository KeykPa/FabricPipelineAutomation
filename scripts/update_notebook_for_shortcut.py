#!/usr/bin/env python3
"""
Update the Fabric notebook to use Lakehouse shortcut instead of direct storage access.
"""

import sys
import subprocess

try:
    import requests
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
    import requests

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        CYAN = GREEN = YELLOW = WHITE = RED = ""
    class Style:
        RESET_ALL = BRIGHT = ""

import os
import base64

sys.path.insert(0, os.path.dirname(__file__))
from fix_and_deploy import get_fabric_token


def update_notebook_content(workspace_id, notebook_id):
    """Update notebook to use lakehouse shortcut."""
    token = get_fabric_token()
    if not token:
        print(f"{Fore.RED}✗ Failed to get token{Style.RESET_ALL}")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Updated notebook content (Fabric Python format)
    notebook_content = '''# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse_name": "ConferenceDataLakehouse",
# META       "default_lakehouse_workspace_id": "7e602ac6-c1c2-4da4-a3d9-e4816740af62"
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Conference Attendance Data Pipeline
# 
# This notebook loads conference attendance data from Azure Blob Storage (via Lakehouse shortcut) and transforms it into Delta tables.
# 
# **Prerequisites:**
# - Lakehouse with storage shortcut to Azure Blob Storage
# - Shortcut name: `conference-data`

# CELL ********************

# Configuration - Using Lakehouse Shortcut
shortcut_folder = "conference-data"  # Name of storage shortcut in Lakehouse
csv_file = "conference_attendance.csv"
json_file = "conference_attendance.json"

print(f"✓ Configuration loaded")
print(f"  Reading from Lakehouse shortcut: {shortcut_folder}")

# MARKDOWN ********************

# ## Load CSV Data from Lakehouse Shortcut

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

# Read CSV from Lakehouse shortcut
csv_path = f"Files/{shortcut_folder}/{csv_file}"
print(f"Reading from: {csv_path}")

df_csv = spark.read \\
    .format("csv") \\
    .option("header", "true") \\
    .schema(csv_schema) \\
    .load(csv_path)

print(f"✓ Loaded {df_csv.count()} records from CSV")
df_csv.show(5, truncate=False)

# MARKDOWN ********************

# ## Transform and Clean Data

# CELL ********************

# Add metadata and clean data
df_transformed = df_csv \\
    .withColumn("LoadDate", current_timestamp()) \\
    .withColumn("SourceFile", lit(csv_file)) \\
    .withColumn("DataFormat", lit("CSV")) \\
    .filter(col("RegistrationID").isNotNull()) \\
    .filter(col("Email").isNotNull())

print(f"✓ Cleaned data: {df_transformed.count()} valid records")
print("\\nData Preview:")
df_transformed.select("RegistrationID", "FirstName", "LastName", "Company", "SessionName", "AttendanceStatus").show(10)

# MARKDOWN ********************

# ## Write to Lakehouse Delta Table

# CELL ********************

# Write to Delta table
table_name = "conference_attendance"

df_transformed.write \\
    .format("delta") \\
    .mode("overwrite") \\
    .option("overwriteSchema", "true") \\
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

print(f"\\n✓ Total Records: {total_records}")
print(f"✓ Unique Attendees: {unique_attendees}")
print(f"✓ Unique Sessions: {unique_sessions}")
print(f"✓ Unique Companies: {unique_companies}")

print("\\n--- Attendance Status Distribution ---")
df_transformed.groupBy("AttendanceStatus").count().orderBy(desc("count")).show()

print("\\n--- Top Sessions by Attendance ---")
df_transformed.filter(col("AttendanceStatus") == "Attended") \\
    .groupBy("SessionName").count() \\
    .orderBy(desc("count")).show()

print("\\n--- Average Session Ratings ---")
df_transformed.filter(col("SessionRating").isNotNull()) \\
    .groupBy("SessionName") \\
    .agg(
        avg("SessionRating").alias("AvgRating"),
        count("*").alias("RatingCount")
    ) \\
    .orderBy(desc("AvgRating")).show()

# MARKDOWN ********************

# ## Verify Table in Lakehouse

# CELL ********************

# Verify the table
df_verify = spark.table(table_name)

print(f"✓ Table '{table_name}' contains {df_verify.count()} records")
print(f"\\nTable Schema:")
df_verify.printSchema()

print("\\n" + "=" * 60)
print("✓✓✓ PIPELINE COMPLETE ✓✓✓")
print("=" * 60)
print(f"\\nData is available in table: {table_name}")
print("You can now:")
print("  • Query with SQL")
print("  • Create Power BI reports")
print("  • Use in other notebooks")
'''
    
    # Encode content
    encoded_content = base64.b64encode(notebook_content.encode('utf-8')).decode('utf-8')
    
    # Update notebook
    update_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/updateDefinition"
    
    payload = {
        "definition": {
            "parts": [
                {
                    "path": "notebook-content.py",
                    "payload": encoded_content,
                    "payloadType": "InlineBase64"
                }
            ]
        }
    }
    
    print(f"\n{Fore.CYAN}Updating notebook content...{Style.RESET_ALL}")
    
    try:
        response = requests.post(update_url, headers=headers, json=payload, timeout=60)
        
        if response.status_code in [200, 202]:
            print(f"{Fore.GREEN}✓ Notebook updated successfully{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}! Update response: {response.status_code}{Style.RESET_ALL}")
            print(f"  {response.text}")
            return False
            
    except Exception as e:
        print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        return False


def main():
    WORKSPACE_ID = "7e602ac6-c1c2-4da4-a3d9-e4816740af62"
    NOTEBOOK_ID = "c6ca0b35-a76a-4221-b3e3-2df6231eca00"  # From previous creation
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}Update Notebook to Use Lakehouse Shortcut")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    if update_notebook_content(WORKSPACE_ID, NOTEBOOK_ID):
        print(f"\n{Fore.GREEN}✓ Success!{Style.RESET_ALL}")
        print(f"\nNotebook updated to read from Lakehouse shortcut")
        print(f"Path: Files/conference-data/conference_attendance.csv")
        return 0
    else:
        print(f"\n{Fore.RED}✗ Failed to update notebook{Style.RESET_ALL}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
