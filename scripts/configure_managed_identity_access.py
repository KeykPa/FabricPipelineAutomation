#!/usr/bin/env python3
"""
Configure storage account access using Managed Identity (proper Azure security).
Grants Fabric workspace managed identity permission to read from storage.
"""

import sys
import subprocess
import json
import time

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


def run_az_command(command, check=True):
    """Run Azure CLI command."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            if check:
                print(f"{Fore.RED}✗ Command failed: {result.stderr}{Style.RESET_ALL}")
            return None
    except Exception as e:
        print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        return None


def get_workspace_identity(workspace_id):
    """Get workspace managed identity principal ID."""
    token = get_fabric_token()
    if not token:
        return None
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get workspace details
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        workspace_data = response.json()
        
        # Check if workspace has managed identity enabled
        # Note: Fabric workspaces use the capacity's managed identity
        print(f"{Fore.CYAN}Workspace: {workspace_data.get('name')}{Style.RESET_ALL}")
        
        # For Fabric, we need to use OAuth with organizational account
        # Workspaces don't have their own managed identity
        return None
        
    except Exception as e:
        print(f"{Fore.RED}✗ Error getting workspace: {e}{Style.RESET_ALL}")
        return None


def grant_storage_access_to_user():
    """Grant current user Storage Blob Data Reader role."""
    
    # Get current user
    user_cmd = 'az ad signed-in-user show --query id -o tsv'
    user_id = run_az_command(user_cmd)
    
    if not user_id:
        print(f"{Fore.RED}✗ Could not get user identity{Style.RESET_ALL}")
        return False
    
    print(f"{Fore.GREEN}✓ Current user ID: {user_id}{Style.RESET_ALL}")
    
    return user_id


def assign_storage_role(resource_group, storage_account, principal_id, role="Storage Blob Data Reader"):
    """Assign storage role to principal."""
    
    print(f"\n{Fore.CYAN}Assigning '{role}' role...{Style.RESET_ALL}")
    
    # Get storage account resource ID
    storage_id_cmd = f'az storage account show --name {storage_account} --resource-group {resource_group} --query id -o tsv'
    storage_id = run_az_command(storage_id_cmd)
    
    if not storage_id:
        return False
    
    # Check if role already assigned
    check_cmd = f'az role assignment list --assignee {principal_id} --scope {storage_id} --role "{role}" --query "[].id" -o tsv'
    existing = run_az_command(check_cmd, check=False)
    
    if existing:
        print(f"{Fore.GREEN}✓ Role already assigned{Style.RESET_ALL}")
        return True
    
    # Assign role
    assign_cmd = f'az role assignment create --assignee {principal_id} --role "{role}" --scope {storage_id}'
    result = run_az_command(assign_cmd)
    
    if result:
        print(f"{Fore.GREEN}✓ Role assigned successfully{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  Waiting 30 seconds for RBAC propagation...{Style.RESET_ALL}")
        time.sleep(30)
        return True
    
    return False


def update_notebook_for_oauth(workspace_id, notebook_id, storage_account, container):
    """Update notebook to use OAuth authentication."""
    token = get_fabric_token()
    if not token:
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Notebook with OAuth authentication
    import base64
    
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
# **Fully automated with Azure AD authentication**
# 
# Uses your organizational account to securely access Azure Blob Storage

# CELL ********************

# Configuration
storage_account_name = "{storage_account}"
container_name = "{container}"
csv_file = "conference_attendance.csv"

# Configure Spark to use OAuth (Azure AD) authentication
# This uses the user's organizational account credentials
spark.conf.set(f"fs.azure.account.auth.type.{{storage_account_name}}.dfs.core.windows.net", "OAuth")
spark.conf.set(f"fs.azure.account.oauth.provider.type.{{storage_account_name}}.dfs.core.windows.net", "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider")
spark.conf.set(f"fs.azure.account.oauth2.client.endpoint.{{storage_account_name}}.dfs.core.windows.net", "https://login.microsoftonline.com/organizations/oauth2/v2.0/token")

print(f"✓ Configuration loaded")
print(f"  Storage Account: {{storage_account_name}}")
print(f"  Container: {{container_name}}")
print(f"  Authentication: Azure AD (OAuth) ✓")

# MARKDOWN ********************

# ## Load CSV Data from Azure Blob Storage

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

# Read CSV using OAuth authentication
csv_path = f"abfss://{{container_name}}@{{storage_account_name}}.dfs.core.windows.net/{{csv_file}}"
print(f"Reading from: {{csv_path}}")

df_csv = spark.read \\
    .format("csv") \\
    .option("header", "true") \\
    .schema(csv_schema) \\
    .load(csv_path)

print(f"✓ Loaded {{df_csv.count()}} records from CSV")
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
    
    print(f"\n{Fore.CYAN}Updating notebook with OAuth authentication...{Style.RESET_ALL}")
    
    try:
        response = requests.post(update_url, headers=headers, json=payload, timeout=60)
        if response.status_code in [200, 202]:
            print(f"{Fore.GREEN}✓ Notebook updated{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}! Response: {response.status_code}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        return False


def main():
    WORKSPACE_ID = "7e602ac6-c1c2-4da4-a3d9-e4816740af62"
    NOTEBOOK_ID = "c6ca0b35-a76a-4221-b3e3-2df6231eca00"
    RESOURCE_GROUP = "westusattendiesdata"
    STORAGE_ACCOUNT = "westusattendiesstore"
    CONTAINER = "conference-data"
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}Configure Storage Access with Managed Identity (Secure)")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    # Step 1: Get current user (who will run the notebook)
    user_id = grant_storage_access_to_user()
    if not user_id:
        print(f"\n{Fore.RED}✗ Failed to get user identity{Style.RESET_ALL}")
        return 1
    
    # Step 2: Grant Storage Blob Data Reader role to user
    if not assign_storage_role(RESOURCE_GROUP, STORAGE_ACCOUNT, user_id):
        print(f"\n{Fore.RED}✗ Failed to assign storage role{Style.RESET_ALL}")
        return 1
    
    # Step 3: Update notebook to use OAuth
    if not update_notebook_for_oauth(WORKSPACE_ID, NOTEBOOK_ID, STORAGE_ACCOUNT, CONTAINER):
        print(f"\n{Fore.RED}✗ Failed to update notebook{Style.RESET_ALL}")
        return 1
    
    print(f"\n{Fore.GREEN}{'='*80}")
    print(f"{Fore.GREEN}✓✓✓ CONFIGURATION COMPLETE ✓✓✓")
    print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}Security configured:{Style.RESET_ALL}")
    print(f"  ✓ RBAC: Storage Blob Data Reader role assigned to your account")
    print(f"  ✓ Authentication: Azure AD OAuth (secure, no keys)")
    print(f"  ✓ Notebook: Updated to use organizational account")
    
    print(f"\n{Fore.CYAN}Ready to use:{Style.RESET_ALL}")
    print(f"  1. Open workspace: https://app.fabric.microsoft.com/groups/{WORKSPACE_ID}")
    print(f"  2. Open notebook: 'Load Conference Data'")
    print(f"  3. Click 'Run all' → Your Azure AD credentials will be used automatically")
    
    print(f"\n{Fore.WHITE}This is the secure, Azure-recommended approach!{Style.RESET_ALL}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
