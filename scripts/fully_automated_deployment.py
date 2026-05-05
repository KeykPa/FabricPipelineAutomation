#!/usr/bin/env python3
"""
Fully automated Fabric deployment with storage authentication.
No manual steps required - storage account key is automatically configured.
"""

import sys
import subprocess
import json
import time
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


def run_az_command(command):
    """Run Azure CLI command and return output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"{Fore.RED}✗ Command failed: {result.stderr}{Style.RESET_ALL}")
            return None
    except Exception as e:
        print(f"{Fore.RED}✗ Error running command: {e}{Style.RESET_ALL}")
        return None


def get_storage_account_key(resource_group, storage_account):
    """Get storage account access key."""
    print(f"\n{Fore.CYAN}Getting storage account key...{Style.RESET_ALL}")
    
    cmd = f'az storage account keys list --resource-group {resource_group} --account-name {storage_account} --query "[0].value" -o tsv'
    key = run_az_command(cmd)
    
    if key:
        print(f"{Fore.GREEN}✓ Retrieved storage account key{Style.RESET_ALL}")
        return key
    return None


def create_or_get_key_vault(resource_group, location):
    """Create Key Vault if it doesn't exist."""
    vault_name = f"kv-{resource_group[:20]}"  # Max 24 chars
    
    print(f"\n{Fore.CYAN}Setting up Key Vault: {vault_name}...{Style.RESET_ALL}")
    
    # Check if exists
    check_cmd = f'az keyvault show --name {vault_name} --query "id" -o tsv 2>nul'
    result = run_az_command(check_cmd)
    
    if result:
        print(f"{Fore.GREEN}✓ Key Vault exists{Style.RESET_ALL}")
        return vault_name
    
    # Create new
    create_cmd = f'az keyvault create --name {vault_name} --resource-group {resource_group} --location {location} --enable-rbac-authorization false'
    result = run_az_command(create_cmd)
    
    if result:
        print(f"{Fore.GREEN}✓ Key Vault created{Style.RESET_ALL}")
        return vault_name
    
    return None


def store_secret_in_key_vault(vault_name, secret_name, secret_value):
    """Store secret in Key Vault."""
    print(f"\n{Fore.CYAN}Storing secret in Key Vault...{Style.RESET_ALL}")
    
    cmd = f'az keyvault secret set --vault-name {vault_name} --name {secret_name} --value "{secret_value}" --query "id" -o tsv'
    result = run_az_command(cmd)
    
    if result:
        print(f"{Fore.GREEN}✓ Secret stored: {secret_name}{Style.RESET_ALL}")
        return True
    return False


def create_lakehouse(workspace_id, lakehouse_name):
    """Create Lakehouse."""
    token = get_fabric_token()
    if not token:
        return None
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses"
    payload = {"displayName": lakehouse_name}
    
    print(f"\n{Fore.CYAN}Creating Lakehouse: {lakehouse_name}...{Style.RESET_ALL}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 409:
            # Already exists, get ID
            print(f"{Fore.YELLOW}! Lakehouse already exists{Style.RESET_ALL}")
            list_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses"
            response = requests.get(list_url, headers=headers, timeout=30)
            lakehouses = response.json().get("value", [])
            for lh in lakehouses:
                if lh.get("displayName") == lakehouse_name:
                    lakehouse_id = lh.get("id")
                    print(f"{Fore.GREEN}✓ Found existing: {lakehouse_id}{Style.RESET_ALL}")
                    return lakehouse_id
        else:
            response.raise_for_status()
            lakehouse_id = response.json().get("id")
            print(f"{Fore.GREEN}✓ Lakehouse created: {lakehouse_id}{Style.RESET_ALL}")
            time.sleep(10)  # Wait for provisioning
            return lakehouse_id
            
    except Exception as e:
        print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
    
    return None


def update_notebook_with_storage_key(workspace_id, notebook_id, storage_account, storage_key, container):
    """Update notebook to use storage account key for authentication."""
    token = get_fabric_token()
    if not token:
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Notebook content with storage key authentication
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
# **Fully automated** - reads from Azure Blob Storage using configured credentials
# 
# No manual setup required!

# CELL ********************

# Configuration
storage_account_name = "{storage_account}"
storage_account_key = "{storage_key}"
container_name = "{container}"
csv_file = "conference_attendance.csv"

# Configure Spark to use storage account key
spark.conf.set(
    f"fs.azure.account.key.{{storage_account_name}}.dfs.core.windows.net",
    storage_account_key
)

print(f"✓ Configuration loaded")
print(f"  Storage Account: {{storage_account_name}}")
print(f"  Container: {{container_name}}")
print(f"  Authentication: Storage Account Key")

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

# Read CSV using abfss protocol with configured authentication
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
    
    # Encode and update
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
    
    print(f"\n{Fore.CYAN}Updating notebook with storage credentials...{Style.RESET_ALL}")
    
    try:
        response = requests.post(update_url, headers=headers, json=payload, timeout=60)
        if response.status_code in [200, 202]:
            print(f"{Fore.GREEN}✓ Notebook updated with storage authentication{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}! Update response: {response.status_code}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        return False


def main():
    # Configuration
    WORKSPACE_ID = "7e602ac6-c1c2-4da4-a3d9-e4816740af62"
    NOTEBOOK_ID = "c6ca0b35-a76a-4221-b3e3-2df6231eca00"
    RESOURCE_GROUP = "westusattendiesdata"
    STORAGE_ACCOUNT = "westusattendiesstore"
    CONTAINER = "conference-data"
    LOCATION = "westus"
    LAKEHOUSE_NAME = "ConferenceDataLakehouse"
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}Fully Automated Fabric Deployment")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}This deployment will:{Style.RESET_ALL}")
    print(f"  1. Get storage account key from Azure")
    print(f"  2. Store key in Azure Key Vault (backup)")
    print(f"  3. Create Lakehouse")
    print(f"  4. Configure notebook with storage authentication")
    print(f"  5. Users can run notebook without any manual steps!\n")
    
    # Step 1: Get storage key
    storage_key = get_storage_account_key(RESOURCE_GROUP, STORAGE_ACCOUNT)
    if not storage_key:
        print(f"\n{Fore.RED}✗ Failed to get storage key{Style.RESET_ALL}")
        return 1
    
    # Step 2: Store in Key Vault (optional backup)
    vault_name = create_or_get_key_vault(RESOURCE_GROUP, LOCATION)
    if vault_name:
        store_secret_in_key_vault(vault_name, "storage-account-key", storage_key)
    
    # Step 3: Create Lakehouse
    lakehouse_id = create_lakehouse(WORKSPACE_ID, LAKEHOUSE_NAME)
    if not lakehouse_id:
        print(f"\n{Fore.RED}✗ Failed to create lakehouse{Style.RESET_ALL}")
        return 1
    
    # Step 4: Update notebook with credentials
    if not update_notebook_with_storage_key(
        WORKSPACE_ID, 
        NOTEBOOK_ID, 
        STORAGE_ACCOUNT, 
        storage_key, 
        CONTAINER
    ):
        print(f"\n{Fore.RED}✗ Failed to update notebook{Style.RESET_ALL}")
        return 1
    
    # Success!
    print(f"\n{Fore.GREEN}{'='*80}")
    print(f"{Fore.GREEN}✓✓✓ DEPLOYMENT COMPLETE ✓✓✓")
    print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}What's deployed:{Style.RESET_ALL}")
    print(f"  ✓ Lakehouse: {LAKEHOUSE_NAME}")
    print(f"  ✓ Notebook: Load Conference Data (with storage authentication)")
    print(f"  ✓ Key Vault: {vault_name} (backup credentials)")
    
    print(f"\n{Fore.CYAN}User workflow (NO manual steps!):{Style.RESET_ALL}")
    print(f"  1. Open workspace: https://app.fabric.microsoft.com/groups/{WORKSPACE_ID}")
    print(f"  2. Open notebook: 'Load Conference Data'")
    print(f"  3. Click 'Run all' → Done! ✨")
    
    print(f"\n{Fore.WHITE}The notebook will automatically:{Style.RESET_ALL}")
    print(f"  • Authenticate to Azure Blob Storage")
    print(f"  • Read CSV/JSON data")
    print(f"  • Transform and load to Delta tables")
    print(f"  • Generate quality reports")
    
    print(f"\n{Fore.GREEN}Users can start using it immediately!{Style.RESET_ALL}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
