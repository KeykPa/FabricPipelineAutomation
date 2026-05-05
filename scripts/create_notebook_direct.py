#!/usr/bin/env python3
"""
Create Fabric Notebook directly in workspace using API.
Bypasses Git sync issues by creating notebook via API instead.
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
sys.path.insert(0, os.path.dirname(__file__))
from fix_and_deploy import get_fabric_token


def create_notebook_in_workspace(workspace_id, notebook_name, notebook_content):
    """Create notebook directly in Fabric workspace."""
    token = get_fabric_token()
    if not token:
        print(f"{Fore.RED}✗ Failed to get token{Style.RESET_ALL}")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Step 1: Create notebook item
    create_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks"
    
    payload = {
        "displayName": notebook_name,
        "description": "Conference attendance data pipeline notebook"
    }
    
    print(f"\n{Fore.CYAN}Creating notebook: {notebook_name}{Style.RESET_ALL}")
    
    try:
        response = requests.post(create_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        notebook_id = response.json().get("id")
        print(f"{Fore.GREEN}✓ Notebook created: {notebook_id}{Style.RESET_ALL}")
        
        # Step 2: Upload content using updateDefinition
        print(f"\n{Fore.CYAN}Uploading notebook content...{Style.RESET_ALL}")
        
        update_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/updateDefinition"
        
        # Fabric notebook format
        definition_payload = {
            "definition": {
                "parts": [
                    {
                        "path": "notebook-content.py",
                        "payload": notebook_content,
                        "payloadType": "InlineBase64"
                    }
                ]
            }
        }
        
        import base64
        encoded_content = base64.b64encode(notebook_content.encode('utf-8')).decode('utf-8')
        definition_payload["definition"]["parts"][0]["payload"] = encoded_content
        
        response = requests.post(update_url, headers=headers, json=definition_payload, timeout=60)
        
        if response.status_code == 200 or response.status_code == 202:
            print(f"{Fore.GREEN}✓ Notebook content uploaded{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}! Upload response: {response.status_code}{Style.RESET_ALL}")
            print(f"  {response.text}")
            print(f"{Fore.YELLOW}  Notebook created but content may be empty{Style.RESET_ALL}")
            return True  # Notebook exists, user can add content manually
        
    except requests.exceptions.HTTPError as e:
        print(f"{Fore.RED}✗ HTTP Error: {e}{Style.RESET_ALL}")
        if e.response:
            print(f"  Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        return False


def get_notebook_content():
    """Get the notebook content in Fabric format."""
    # Read from our local notebook
    notebook_file = "LoadConferenceData.Notebook/notebook-content.py"
    
    if os.path.exists(notebook_file):
        with open(notebook_file, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        print(f"{Fore.YELLOW}! Notebook file not found, using embedded content{Style.RESET_ALL}")
        # Return inline version
        return """# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# MARKDOWN ********************

# # Conference Attendance Data Pipeline

# CELL ********************

storage_account_name = "westusattendiesstore"
container_name = "conference-data"
csv_file = "conference_attendance.csv"

print(f"✓ Configuration loaded")
"""


def main():
    WORKSPACE_ID = "7e602ac6-c1c2-4da4-a3d9-e4816740af62"
    NOTEBOOK_NAME = "Load Conference Data"
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}Create Notebook Directly in Fabric Workspace")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    notebook_content = get_notebook_content()
    
    if create_notebook_in_workspace(WORKSPACE_ID, NOTEBOOK_NAME, notebook_content):
        print(f"\n{Fore.GREEN}✓ Success!{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}Next steps:{Style.RESET_ALL}")
        print(f"  1. Open workspace: https://app.fabric.microsoft.com/groups/{WORKSPACE_ID}")
        print(f"  2. Find notebook: '{NOTEBOOK_NAME}'")
        print(f"  3. If empty, copy content from: LoadConferenceData.Notebook/notebook-content.py")
        return 0
    else:
        print(f"\n{Fore.RED}✗ Failed to create notebook{Style.RESET_ALL}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
