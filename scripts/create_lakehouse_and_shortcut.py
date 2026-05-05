#!/usr/bin/env python3
"""
Create Lakehouse and configure storage shortcut for Azure Blob Storage access.
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
import json
import time

sys.path.insert(0, os.path.dirname(__file__))
from fix_and_deploy import get_fabric_token


def create_lakehouse(workspace_id, lakehouse_name):
    """Create Lakehouse in workspace."""
    token = get_fabric_token()
    if not token:
        print(f"{Fore.RED}✗ Failed to get token{Style.RESET_ALL}")
        return None
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Create Lakehouse
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses"
    
    payload = {
        "displayName": lakehouse_name,
        "description": "Conference data lakehouse"
    }
    
    print(f"\n{Fore.CYAN}Creating Lakehouse: {lakehouse_name}{Style.RESET_ALL}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        lakehouse_id = response.json().get("id")
        print(f"{Fore.GREEN}✓ Lakehouse created: {lakehouse_id}{Style.RESET_ALL}")
        
        # Wait for provisioning
        print(f"{Fore.CYAN}Waiting for lakehouse to provision...{Style.RESET_ALL}")
        time.sleep(10)
        
        return lakehouse_id
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 409:
            print(f"{Fore.YELLOW}! Lakehouse already exists{Style.RESET_ALL}")
            # Try to find existing lakehouse
            list_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses"
            response = requests.get(list_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            lakehouses = response.json().get("value", [])
            for lh in lakehouses:
                if lh.get("displayName") == lakehouse_name:
                    lakehouse_id = lh.get("id")
                    print(f"{Fore.GREEN}✓ Found existing: {lakehouse_id}{Style.RESET_ALL}")
                    return lakehouse_id
        
        print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        if e.response:
            print(f"  Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        return None


def main():
    WORKSPACE_ID = "7e602ac6-c1c2-4da4-a3d9-e4816740af62"
    LAKEHOUSE_NAME = "ConferenceDataLakehouse"
    STORAGE_ACCOUNT = "westusattendiesstore"
    CONTAINER = "conference-data"
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}Create Lakehouse and Configure Storage Shortcut")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    # Step 1: Create Lakehouse
    lakehouse_id = create_lakehouse(WORKSPACE_ID, LAKEHOUSE_NAME)
    
    if not lakehouse_id:
        print(f"\n{Fore.RED}✗ Failed to create lakehouse{Style.RESET_ALL}")
        return 1
    
    # Step 2: Manual shortcut creation (API doesn't support this well)
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}⚠  Storage Shortcut - Manual Steps Required{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    print(f"The Lakehouse API doesn't fully support shortcut creation.")
    print(f"Please follow these steps in the Fabric UI:\n")
    
    print(f"{Fore.CYAN}1. Open Lakehouse:{Style.RESET_ALL}")
    print(f"   https://app.fabric.microsoft.com/groups/{WORKSPACE_ID}/lakehouses/{lakehouse_id}")
    
    print(f"\n{Fore.CYAN}2. Create Storage Shortcut:{Style.RESET_ALL}")
    print(f"   • Click '...' menu on 'Files' in left panel")
    print(f"   • Select 'New shortcut'")
    print(f"   • Choose 'Azure Data Lake Storage Gen2'")
    
    print(f"\n{Fore.CYAN}3. Configure Connection:{Style.RESET_ALL}")
    print(f"   • URL: https://{STORAGE_ACCOUNT}.dfs.core.windows.net/")
    print(f"   • Authentication: Organizational account")
    print(f"   • Click 'Next'")
    
    print(f"\n{Fore.CYAN}4. Select Container:{Style.RESET_ALL}")
    print(f"   • Navigate to: {CONTAINER}/")
    print(f"   • Shortcut Name: {CONTAINER}")
    print(f"   • Click 'Create'")
    
    print(f"\n{Fore.CYAN}5. Verify:{Style.RESET_ALL}")
    print(f"   • In Lakehouse, expand 'Files'")
    print(f"   • You should see '{CONTAINER}' folder")
    print(f"   • Inside: conference_attendance.csv and .json files")
    
    print(f"\n{Fore.GREEN}After creating the shortcut, the notebook will be able to read the data!{Style.RESET_ALL}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
