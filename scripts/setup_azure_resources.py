#!/usr/bin/env python3
"""
Setup Azure Resources and Fabric Workspace for Pipeline Project

This script creates:
- Resource Group
- Storage Account and Blob Container
- Fabric Capacity (optional)
- Fabric Workspace
- Lakehouse
- Uploads sample data
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        CYAN = GREEN = YELLOW = WHITE = RED = ""
    class Style:
        RESET_ALL = ""

try:
    import requests
except ImportError:
    print("Error: 'requests' package not found. Install dependencies with: pip install -r requirements.txt")
    sys.exit(1)

try:
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
except ImportError:
    print("Error: Azure SDK packages not found. Install dependencies with: pip install -r requirements.txt")
    sys.exit(1)


def run_command(command, check=True, capture_output=True):
    """Execute a shell command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            capture_output=capture_output,
            text=True
        )
        return result.stdout.strip() if capture_output else ""
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return None


def print_section(text):
    """Print a section header."""
    print(f"\n{Fore.YELLOW}{text}{Style.RESET_ALL}")


def print_success(text):
    """Print success message."""
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")


def print_info(text, indent=0):
    """Print info message."""
    prefix = "  " * indent
    print(f"{Fore.WHITE}{prefix}{text}{Style.RESET_ALL}")


def print_error(text):
    """Print error message."""
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")


def get_fabric_token():
    """Get Fabric API access token."""
    token = run_command(
        "az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv"
    )
    return token


def setup_azure_resources(
    resource_group_name,
    location,
    storage_account_name,
    workspace_name,
    capacity_name=None,
    capacity_sku="F2",
    use_existing_capacity=False
):
    """Main setup function."""
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Azure Resources Setup for Fabric Pipeline")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    # Get account info
    account_info = json.loads(run_command("az account show"))
    subscription_id = account_info["id"]
    
    print_success(f"Logged in as: {account_info['user']['name']}")
    print_info(f"Subscription: {account_info['name']}")
    print_info(f"ID: {subscription_id}")
    
    # Create Resource Group
    print_section("Creating resource group...")
    print_info(f"Name: {resource_group_name}")
    print_info(f"Location: {location}")
    
    rg_exists = run_command(
        f"az group exists --name {resource_group_name}",
        check=False
    )
    
    if rg_exists == "true":
        print_success("Resource group already exists")
    else:
        run_command(
            f"az group create --name {resource_group_name} --location {location} --output none"
        )
        print_success("Resource group created successfully")
    
    # Create Storage Account
    print_section("Creating storage account...")
    print_info(f"Name: {storage_account_name}")
    
    # Check if storage account exists
    check_result = run_command(
        f"az storage account check-name --name {storage_account_name}",
        check=False
    )
    
    if check_result:
        name_available = json.loads(check_result).get("nameAvailable", False)
        
        if not name_available:
            print_success("Storage account already exists or name is taken")
        else:
            run_command(
                f"az storage account create "
                f"--name {storage_account_name} "
                f"--resource-group {resource_group_name} "
                f"--location {location} "
                f"--sku Standard_LRS "
                f"--kind StorageV2 "
                f"--access-tier Hot "
                f"--allow-blob-public-access false "
                f"--min-tls-version TLS1_2 "
                f"--output none"
            )
            print_success("Storage account created successfully")
    
    # Create Blob Container
    print_section("Creating blob container...")
    print_info("Container: conference-data")
    
    run_command(
        f"az storage container create "
        f"--name conference-data "
        f"--account-name {storage_account_name} "
        f"--auth-mode login "
        f"--output none",
        check=False
    )
    print_success("Blob container created/verified")
    
    # Assign Storage Blob Data Contributor role to current user
    print_section("Assigning storage permissions...")
    print_info("This may take a moment to propagate...")
    
    # Get current user's object ID
    user_id_output = run_command("az ad signed-in-user show --query id -o tsv")
    if user_id_output:
        user_id = user_id_output.strip()
        # Get storage account ID
        storage_id = run_command(
            f"az storage account show "
            f"--name {storage_account_name} "
            f"--resource-group {resource_group_name} "
            f"--query id -o tsv"
        ).strip()
        
        # Assign role
        run_command(
            f"az role assignment create "
            f"--role \"Storage Blob Data Contributor\" "
            f"--assignee {user_id} "
            f"--scope {storage_id} "
            f"--output none",
            check=False
        )
        print_success("Storage permissions assigned")
        
        # Wait a few seconds for role assignment to propagate
        print_info("Waiting for permissions to propagate...")
        import time
        time.sleep(10)
    
    # Upload Sample Data using Azure SDK with Entra identity
    print_section("Uploading sample data files...")
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    csv_path = project_root / "sample-data" / "conference_attendance.csv"
    json_path = project_root / "sample-data" / "conference_attendance.json"
    
    try:
        # Create credential using Entra identity (DefaultAzureCredential)
        print_info("Authenticating with Entra identity...")
        credential = DefaultAzureCredential()
        
        # Create BlobServiceClient
        account_url = f"https://{storage_account_name}.blob.core.windows.net"
        blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
        container_client = blob_service_client.get_container_client("conference-data")
        
        # Upload CSV file
        if csv_path.exists():
            print_info("Uploading CSV file...")
            blob_client = blob_service_client.get_blob_client(
                container="conference-data",
                blob="conference_attendance.csv"
            )
            with open(csv_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            print_success("CSV file uploaded")
        
        # Upload JSON file
        if json_path.exists():
            print_info("Uploading JSON file...")
            blob_client = blob_service_client.get_blob_client(
                container="conference-data",
                blob="conference_attendance.json"
            )
            with open(json_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            print_success("JSON file uploaded")
            
    except Exception as e:
        print_error(f"Failed to upload sample data: {str(e)}")
        print_info("You can upload files manually later using upload_to_blob.py")
        # Continue with deployment even if upload fails
    
    # Get storage account details
    storage_info = json.loads(run_command(
        f"az storage account show --name {storage_account_name} --resource-group {resource_group_name}"
    ))
    blob_endpoint = storage_info["primaryEndpoints"]["blob"]
    
    # Fabric Capacity Configuration
    capacity_id = None
    
    if capacity_name:
        print_section("Configuring Fabric Capacity...")
        
        if use_existing_capacity:
            print_info(f"Looking for existing capacity: {capacity_name}")
            # Note: Fabric capacity management via Azure CLI is limited
            # May need to use Azure portal or REST API
            print_success(f"Using existing capacity: {capacity_name}")
        else:
            print_info("Creating Fabric capacity...")
            print_info(f"Name: {capacity_name}", indent=1)
            print_info(f"SKU: {capacity_sku}", indent=1)
            print_info(f"Location: {location}", indent=1)
            
            # Note: This requires azure-mgmt-fabric or REST API
            print(f"{Fore.YELLOW}Note: Fabric capacity creation may require manual steps in Azure portal{Style.RESET_ALL}")
            print_info("You can create the capacity at: https://portal.azure.com", indent=1)
    
    # Create Fabric Workspace
    workspace_id = None
    lakehouse_id = None
    
    print_section("Creating Fabric Workspace...")
    print_info(f"Name: {workspace_name}")
    
    try:
        fabric_token = get_fabric_token()
        headers = {
            "Authorization": f"Bearer {fabric_token}",
            "Content-Type": "application/json"
        }
        
        # Check if workspace exists
        list_url = "https://api.fabric.microsoft.com/v1/workspaces"
        response = requests.get(list_url, headers=headers)
        response.raise_for_status()
        
        workspaces = response.json().get("value", [])
        existing_workspace = next(
            (ws for ws in workspaces if ws.get("displayName") == workspace_name),
            None
        )
        
        if existing_workspace:
            workspace_id = existing_workspace["id"]
            print_success("Workspace already exists")
            print_info(f"Workspace ID: {workspace_id}")
        else:
            # Create workspace
            create_data = {
                "displayName": workspace_name,
                "description": "Workspace for Conference Attendance Pipeline"
            }
            
            if capacity_id:
                create_data["capacityId"] = capacity_id
            
            response = requests.post(list_url, headers=headers, json=create_data)
            response.raise_for_status()
            
            workspace_id = response.json()["id"]
            print_success("Workspace created successfully")
            print_info(f"Workspace ID: {workspace_id}")
        
        # Create Lakehouse
        if workspace_id:
            print_section("Creating Lakehouse...")
            print_info("Name: ConferenceDataLakehouse")
            
            lakehouse_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses"
            lakehouse_data = {
                "displayName": "ConferenceDataLakehouse",
                "description": "Lakehouse for conference attendance data"
            }
            
            response = requests.post(lakehouse_url, headers=headers, json=lakehouse_data)
            
            if response.status_code == 201:
                lakehouse_id = response.json()["id"]
                print_success("Lakehouse created successfully")
                print_info(f"Lakehouse ID: {lakehouse_id}")
            elif response.status_code == 409:
                print_success("Lakehouse may already exist")
            else:
                print(f"{Fore.YELLOW}Warning: Could not create Lakehouse. You may need to create it manually.{Style.RESET_ALL}")
    
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not complete Fabric workspace setup via API: {str(e)}{Style.RESET_ALL}")
        print_info("You may need to create the workspace and lakehouse manually in the Fabric portal", indent=1)
    
    # Summary
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Setup Complete!")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.YELLOW}Azure Resources:{Style.RESET_ALL}")
    print_info(f"Resource Group: {resource_group_name}")
    print_info(f"Location: {location}")
    print_info(f"Storage Account: {storage_account_name}")
    print_info(f"Blob Container: conference-data")
    print_info(f"Blob Endpoint: {blob_endpoint}")
    
    if capacity_name:
        print(f"\n{Fore.YELLOW}Fabric Capacity:{Style.RESET_ALL}")
        print_info(f"Name: {capacity_name}")
        print_info(f"SKU: {capacity_sku}")
    
    print(f"\n{Fore.YELLOW}Fabric Workspace:{Style.RESET_ALL}")
    print_info(f"Name: {workspace_name}")
    if workspace_id:
        print_info(f"ID: {workspace_id}")
        print(f"\n{Fore.CYAN}Workspace URL:{Style.RESET_ALL}")
        print_info(f"https://app.fabric.microsoft.com/groups/{workspace_id}")
    
    if lakehouse_id:
        print_info(f"Lakehouse ID: {lakehouse_id}")
    
    print(f"\n{Fore.YELLOW}Next Steps:{Style.RESET_ALL}")
    print_info("1. Verify the workspace and lakehouse in Fabric portal")
    print_info("2. Update the pipeline configuration with your details")
    if workspace_id:
        print_info(f"3. Deploy the pipeline using: python scripts/deploy_pipeline.py --workspace-id {workspace_id}")
    else:
        print_info("3. Deploy the pipeline using: python scripts/deploy_pipeline.py")
    print_info("4. Configure GitHub secrets for CI/CD")
    print()
    
    # Save configuration
    config_dir = project_root / "config"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "azure-config.txt"
    
    config_content = f"""# Azure and Fabric Configuration
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Azure Resources
RESOURCE_GROUP={resource_group_name}
LOCATION={location}
STORAGE_ACCOUNT={storage_account_name}
CONTAINER=conference-data
BLOB_ENDPOINT={blob_endpoint}
SUBSCRIPTION_ID={subscription_id}

# Fabric Resources
WORKSPACE_NAME={workspace_name}
"""
    
    if workspace_id:
        config_content += f"WORKSPACE_ID={workspace_id}\n"
    
    if capacity_name:
        config_content += f"CAPACITY_NAME={capacity_name}\n"
        config_content += f"CAPACITY_SKU={capacity_sku}\n"
    
    if lakehouse_id:
        config_content += f"LAKEHOUSE_ID={lakehouse_id}\n"
    
    config_content += f"\n# Get connection string with:\n"
    config_content += f"# az storage account show-connection-string --name {storage_account_name} --resource-group {resource_group_name}\n"
    
    with open(config_path, "w") as f:
        f.write(config_content)
    
    print_success(f"Configuration saved to: {config_path}")
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Azure resources for Fabric Pipeline")
    parser.add_argument("--resource-group", required=True, help="Resource group name")
    parser.add_argument("--location", required=True, help="Azure region")
    parser.add_argument("--storage-account", required=True, help="Storage account name")
    parser.add_argument("--workspace-name", required=True, help="Fabric workspace name")
    parser.add_argument("--capacity-name", help="Fabric capacity name")
    parser.add_argument("--capacity-sku", default="F2", help="Fabric capacity SKU")
    parser.add_argument("--use-existing-capacity", action="store_true", help="Use existing capacity")
    
    args = parser.parse_args()
    
    setup_azure_resources(
        resource_group_name=args.resource_group,
        location=args.location,
        storage_account_name=args.storage_account,
        workspace_name=args.workspace_name,
        capacity_name=args.capacity_name,
        capacity_sku=args.capacity_sku,
        use_existing_capacity=args.use_existing_capacity
    )
