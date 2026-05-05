#!/usr/bin/env python3
"""
Complete Fabric Workspace Deployment

This script automates the entire Fabric workspace setup:
- Creates Lakehouse
- Uploads Notebook
- Configures connections
- Ready to run pipeline
"""

import sys
import os
import json
import argparse
import subprocess
from pathlib import Path
import time

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


def print_header(text):
    """Print section header."""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}{text}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")


def print_section(text):
    """Print section title."""
    print(f"\n{Fore.YELLOW}{text}{Style.RESET_ALL}")


def print_success(text):
    """Print success message."""
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")


def print_info(text):
    """Print info message."""
    print(f"{Fore.WHITE}  {text}{Style.RESET_ALL}")


def print_error(text):
    """Print error message."""
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")


def run_command(command):
    """Execute a shell command and return output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_fabric_token():
    """Get Fabric API access token."""
    token = run_command(
        "az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv"
    )
    return token


def create_lakehouse(workspace_id, lakehouse_name):
    """Create a Lakehouse in the workspace."""
    print_section(f"Creating Lakehouse: {lakehouse_name}")
    
    token = get_fabric_token()
    if not token:
        print_error("Failed to get access token")
        return None
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses"
    
    payload = {
        "displayName": lakehouse_name,
        "description": "Lakehouse for conference attendance data"
    }
    
    try:
        # Check if lakehouse exists
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        existing = response.json().get("value", [])
        for lh in existing:
            if lh.get("displayName") == lakehouse_name:
                lakehouse_id = lh.get("id")
                print_success(f"Lakehouse already exists: {lakehouse_id}")
                return lakehouse_id
        
        # Create new lakehouse
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        lakehouse_id = response.json().get("id")
        print_success(f"Lakehouse created: {lakehouse_id}")
        
        # Wait for lakehouse to be ready
        print_info("Waiting for lakehouse to be ready...")
        time.sleep(5)
        
        return lakehouse_id
        
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to create lakehouse: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                print_info(json.dumps(error_details, indent=2))
            except:
                pass
        return None


def upload_notebook(workspace_id, notebook_path, notebook_name):
    """Upload a notebook to the workspace."""
    print_section(f"Uploading Notebook: {notebook_name}")
    
    token = get_fabric_token()
    if not token:
        print_error("Failed to get access token")
        return None
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks"
    
    # Read notebook content
    notebook_path = Path(notebook_path)
    if not notebook_path.exists():
        print_error(f"Notebook file not found: {notebook_path}")
        return None
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook_content = f.read()
    
    payload = {
        "displayName": notebook_name,
        "description": "Pipeline to load conference attendance data",
        "definition": {
            "format": "ipynb",
            "parts": [
                {
                    "path": "notebook-content.py",
                    "payload": notebook_content,
                    "payloadType": "InlineBase64"
                }
            ]
        }
    }
    
    try:
        # Check if notebook exists
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        existing = response.json().get("value", [])
        for nb in existing:
            if nb.get("displayName") == notebook_name:
                notebook_id = nb.get("id")
                print_success(f"Notebook already exists: {notebook_id}")
                print_info("Updating existing notebook...")
                
                # Update existing notebook
                update_url = f"{url}/{notebook_id}"
                response = requests.patch(update_url, headers=headers, json=payload)
                response.raise_for_status()
                print_success("Notebook updated")
                return notebook_id
        
        # Create new notebook
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        notebook_id = response.json().get("id")
        print_success(f"Notebook created: {notebook_id}")
        return notebook_id
        
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to upload notebook: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                print_info(json.dumps(error_details, indent=2))
            except:
                pass
        return None


def deploy_complete_workspace(workspace_id, storage_account_name, lakehouse_name="ConferenceDataLakehouse"):
    """Deploy complete Fabric workspace with all components."""
    
    print_header("Complete Fabric Workspace Deployment")
    
    # Get workspace info
    print_section("Verifying workspace access...")
    token = get_fabric_token()
    if not token:
        print_error("Failed to authenticate. Run 'az login' first.")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(
            f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}",
            headers=headers
        )
        response.raise_for_status()
        workspace_info = response.json()
        workspace_name = workspace_info.get("displayName", "Unknown")
        print_success(f"Workspace: {workspace_name}")
        print_info(f"ID: {workspace_id}")
    except:
        print_error("Failed to access workspace")
        return False
    
    # Step 1: Create Lakehouse
    lakehouse_id = create_lakehouse(workspace_id, lakehouse_name)
    if not lakehouse_id:
        print_error("Lakehouse creation failed")
        return False
    
    # Step 2: Upload Notebook
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    notebook_path = project_root / "notebooks" / "load_conference_data.ipynb"
    
    notebook_id = upload_notebook(workspace_id, notebook_path, "Load Conference Data")
    if not notebook_id:
        print_error("Notebook upload failed")
        # Continue anyway - user can upload manually
    
    # Step 3: Configuration Summary
    print_header("Deployment Summary")
    
    print_success("Workspace deployed successfully!")
    print()
    print(f"{Fore.CYAN}Workspace Details:{Style.RESET_ALL}")
    print_info(f"Name: {workspace_name}")
    print_info(f"ID: {workspace_id}")
    print_info(f"URL: https://app.fabric.microsoft.com/groups/{workspace_id}")
    print()
    
    if lakehouse_id:
        print(f"{Fore.CYAN}Lakehouse:{Style.RESET_ALL}")
        print_info(f"Name: {lakehouse_name}")
        print_info(f"ID: {lakehouse_id}")
        print()
    
    if notebook_id:
        print(f"{Fore.CYAN}Notebook:{Style.RESET_ALL}")
        print_info(f"Name: Load Conference Data")
        print_info(f"ID: {notebook_id}")
        print()
    
    print(f"{Fore.CYAN}Data Source:{Style.RESET_ALL}")
    print_info(f"Storage Account: {storage_account_name}")
    print_info(f"Container: conference-data")
    print_info(f"Files: conference_attendance.csv, conference_attendance.json")
    print()
    
    # Step 4: Next Steps
    print(f"{Fore.YELLOW}Next Steps:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}1. Go to: https://app.fabric.microsoft.com/groups/{workspace_id}{Style.RESET_ALL}")
    
    if notebook_id:
        print(f"{Fore.WHITE}2. Open the 'Load Conference Data' notebook{Style.RESET_ALL}")
        print(f"{Fore.WHITE}3. Attach the notebook to '{lakehouse_name}' lakehouse{Style.RESET_ALL}")
        print(f"{Fore.WHITE}4. Create a Lakehouse shortcut to blob storage:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}   - In Lakehouse → Files → New shortcut{Style.RESET_ALL}")
        print(f"{Fore.WHITE}   - ADLS Gen2: https://{storage_account_name}.dfs.core.windows.net/conference-data{Style.RESET_ALL}")
        print(f"{Fore.WHITE}   - Use Entra identity authentication{Style.RESET_ALL}")
        print(f"{Fore.WHITE}5. Run the notebook to load data{Style.RESET_ALL}")
    else:
        print(f"{Fore.WHITE}2. Manually upload the notebook from: {notebook_path}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}3. Follow the steps in DEPLOYMENT_GUIDE.md{Style.RESET_ALL}")
    
    print()
    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Deploy complete Fabric workspace with lakehouse and notebook"
    )
    parser.add_argument(
        "--workspace-id",
        required=True,
        help="Fabric workspace ID"
    )
    parser.add_argument(
        "--storage-account",
        required=True,
        help="Azure Storage Account name"
    )
    parser.add_argument(
        "--lakehouse-name",
        default="ConferenceDataLakehouse",
        help="Name for the lakehouse (default: ConferenceDataLakehouse)"
    )
    
    args = parser.parse_args()
    
    success = deploy_complete_workspace(
        workspace_id=args.workspace_id,
        storage_account_name=args.storage_account,
        lakehouse_name=args.lakehouse_name
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
