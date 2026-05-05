#!/usr/bin/env python3
"""
Update notebook to use mssparkutils (Fabric's built-in storage access).
This is the simplest, most reliable method for Fabric notebooks.
"""

import sys
import subprocess
import base64

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
sys.path.insert(0, os.path.dirname(__file__))
from fix_and_deploy import get_fabric_token


def update_notebook_with_mssparkutils(workspace_id, notebook_id, storage_account, container):
    """Update notebook to use mssparkutils (Fabric-native storage access)."""
    token = get_fabric_token()
    if not token:
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Notebook using mssparkutils
    notebook_content = f'''# Fabric notebook source

# METADATA ********************

# META {{
# META   "kernel_info": {{
# META     "name": "synapse_pyspark"
# META   }},
# META   "dependencies": {{
# META     "lakehouse": {{
# META       "default_lakehouse_name": "ConferenceDataLakehouse",
# META       "default_lakehouse_workspace_id": "{workspace_id}"
# META     }}
# META   }}
# META }}

# MARKDOWN ********************

# # Conference Attendance Data Pipeline
# 
# **Fully automated using Fabric's mssparkutils**
# 
# No manual configuration required - uses your Fabric credentials automatically!

# CELL ********************

# Configuration
storage_account_name = "{storage_account}"
container_name = "{container}"
csv_file = "conference_attendance.csv"

print(f"✓ Configuration loaded")
print(f"  Storage Account: {{storage_account_name}}")
print(f"  Container: {{container_name}}")
print(f"  Authentication: mssparkutils (Fabric built-in) ✓")

# MARKDOWN ********************

# ## Load CSV Data Using mssparkutils

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

# Use mssparkutils to read from Azure Storage
# mssparkutils handles authentication automatically
from notebookutils import mssparkutils

# Construct the path
storage_path = f"abfss://{{container_name}}@{{storage_account_name}}.dfs.core.windows.net/{{csv_file}}"

print(f"Reading from: {{storage_path}}")
print(f"Using mssparkutils for authentication...")

try:
    # Read CSV using mssparkutils
    df_csv = spark.read \\
        .format("csv") \\
        .option("header", "true") \\
        .schema(csv_schema) \\
        .load(storage_path)
    
    record_count = df_csv.count()
    print(f"✓ Loaded {{record_count}} records from CSV")
    df_csv.show(5, truncate=False)
    
except Exception as e:
    print(f"✗ Error reading file: {{str(e)}}")
    print(f"\\nAlternative: Using mssparkutils.fs.mount() to mount storage...")
    
    # Alternative: Mount the storage account
    mount_point = f"/mnt/{{container_name}}"
    
    try:
        # Try to mount
        mssparkutils.fs.mount(
            f"abfss://{{container_name}}@{{storage_account_name}}.dfs.core.windows.net",
            mount_point
        )
        print(f"✓ Storage mounted at {{mount_point}}")
        
        # Read from mount point
        df_csv = spark.read \\
            .format("csv") \\
            .option("header", "true") \\
            .schema(csv_schema) \\
            .load(f"{{mount_point}}/{{csv_file}}")
        
        record_count = df_csv.count()
        print(f"✓ Loaded {{record_count}} records from CSV")
        df_csv.show(5, truncate=False)
        
    except Exception as mount_error:
        print(f"✗ Mount also failed: {{str(mount_error)}}")
        print(f"\\nPlease ensure you have 'Storage Blob Data Reader' role on the storage account.")
        raise

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

print(f"✓ Cleaned data: {{df_transformed.count()}} valid records")
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

print(f"✓ Data written to table: {{table_name}}")
print(f"✓ Table location: Tables/{{table_name}}")

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

print(f"\\n✓ Total Records: {{total_records}}")
print(f"✓ Unique Attendees: {{unique_attendees}}")
print(f"✓ Unique Sessions: {{unique_sessions}}")
print(f"✓ Unique Companies: {{unique_companies}}")

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

print(f"✓ Table '{{table_name}}' contains {{df_verify.count()}} records")
print(f"\\nTable Schema:")
df_verify.printSchema()

print("\\n" + "=" * 60)
print("✓✓✓ PIPELINE COMPLETE ✓✓✓")
print("=" * 60)
print(f"\\nData is available in table: {{table_name}}")
print("You can now:")
print("  • Query with SQL")
print("  • Create Power BI reports")
print("  • Use in other notebooks")
'''
    
    encoded = base64.b64encode(notebook_content.encode('utf-8')).decode('utf-8')
    update_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/updateDefinition"
    
    payload = {
        "definition": {
            "parts": [{
                "path": "notebook-content.py",
                "payload": encoded,
                "payloadType": "InlineBase64"
            }]
        }
    }
    
    print(f"\n{Fore.CYAN}Updating notebook with mssparkutils...{Style.RESET_ALL}")
    
    try:
        response = requests.post(update_url, headers=headers, json=payload, timeout=60)
        if response.status_code in [200, 202]:
            print(f"{Fore.GREEN}✓ Notebook updated successfully{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}! Response: {response.status_code} - {response.text}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        return False


def main():
    WORKSPACE_ID = "7e602ac6-c1c2-4da4-a3d9-e4816740af62"
    NOTEBOOK_ID = "c6ca0b35-a76a-4221-b3e3-2df6231eca00"
    STORAGE_ACCOUNT = "westusattendiesstore"
    CONTAINER = "conference-data"
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}Update Notebook to Use mssparkutils (Fabric Native)")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}mssparkutils advantages:{Style.RESET_ALL}")
    print(f"  • Built into Fabric - no configuration needed")
    print(f"  • Uses your Fabric credentials automatically")
    print(f"  • Supports automatic mounting of storage")
    print(f"  • Most reliable method for Fabric notebooks\n")
    
    if not update_notebook_with_mssparkutils(WORKSPACE_ID, NOTEBOOK_ID, STORAGE_ACCOUNT, CONTAINER):
        print(f"\n{Fore.RED}✗ Failed to update notebook{Style.RESET_ALL}")
        return 1
    
    print(f"\n{Fore.GREEN}{'='*80}")
    print(f"{Fore.GREEN}✓ Notebook Updated!{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}Next step:{Style.RESET_ALL}")
    print(f"  You need Storage Blob Data Reader role on the storage account.")
    print(f"  Run this command:")
    print(f"\n  {Fore.WHITE}az login{Style.RESET_ALL}  # Re-authenticate")
    print(f"  {Fore.WHITE}az role assignment create \\\\")
    print(f"    --assignee $(az ad signed-in-user show --query id -o tsv) \\\\")
    print(f"    --role 'Storage Blob Data Reader' \\\\")
    print(f"    --scope $(az storage account show --name {STORAGE_ACCOUNT} --resource-group westusattendiesdata --query id -o tsv){Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}Then test:{Style.RESET_ALL}")
    print(f"  1. Open: https://app.fabric.microsoft.com/groups/{WORKSPACE_ID}")
    print(f"  2. Open notebook: 'Load Conference Data'")
    print(f"  3. Click 'Run all'\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
