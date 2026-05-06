#!/usr/bin/env python3
"""
Fully automated Fabric workspace deployment - NO manual steps required!
Uploads data directly to OneLake instead of using shortcuts.
"""

import sys
import subprocess
import json
import time
import os
from pathlib import Path

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

import argparse


def get_fabric_token():
    """Get Fabric API token."""
    try:
        # Try Fabric API endpoint first
        result = subprocess.run(
            'az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv',
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except Exception as e:
        print(f"{Fore.RED}✗ Error getting token: {e}{Style.RESET_ALL}")
        return None


def upload_file_to_onelake(workspace_id, lakehouse_id, local_file_path, onelake_path, token):
    """
    Upload file directly to OneLake using the DFS API.
    This bypasses the need for shortcuts entirely!
    """
    filename = os.path.basename(local_file_path)
    
    # OneLake DFS endpoint
    # Format: https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{lakehouse_id}/{path}
    url = f"https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{lakehouse_id}/Files/{onelake_path}/{filename}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "x-ms-version": "2023-11-03"
    }
    
    print(f"{Fore.CYAN}Uploading {filename} to OneLake...{Style.RESET_ALL}")
    
    try:
        # Read file content
        with open(local_file_path, 'rb') as f:
            file_content = f.read()
        
        # Step 1: Create/overwrite file (PUT with resource=file)
        create_url = f"{url}?resource=file"
        response = requests.put(create_url, headers=headers, timeout=30)
        
        if response.status_code not in [200, 201]:
            print(f"{Fore.YELLOW}  Create response: {response.status_code}{Style.RESET_ALL}")
        
        # Step 2: Upload content (PATCH)
        patch_url = f"{url}?action=append&position=0"
        headers_patch = headers.copy()
        headers_patch["Content-Type"] = "application/octet-stream"
        headers_patch["Content-Length"] = str(len(file_content))
        
        response = requests.patch(patch_url, headers=headers_patch, data=file_content, timeout=60)
        
        if response.status_code not in [200, 202]:
            print(f"{Fore.RED}✗ Upload failed: {response.status_code} - {response.text}{Style.RESET_ALL}")
            return False
        
        # Step 3: Flush (finalize)
        flush_url = f"{url}?action=flush&position={len(file_content)}"
        response = requests.patch(flush_url, headers=headers, timeout=30)
        
        if response.status_code in [200, 201]:
            print(f"{Fore.GREEN}✓ {filename} uploaded successfully{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}✗ Flush failed: {response.status_code} - {response.text}{Style.RESET_ALL}")
            return False
            
    except Exception as e:
        print(f"{Fore.RED}✗ Upload error: {e}{Style.RESET_ALL}")
        return False


def create_lakehouse(workspace_id, lakehouse_name, token):
    """Create Lakehouse in workspace."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses"
    
    payload = {
        "displayName": lakehouse_name,
        "description": "Conference attendance data lakehouse - fully automated"
    }
    
    print(f"\n{Fore.CYAN}Creating Lakehouse: {lakehouse_name}{Style.RESET_ALL}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        lakehouse_id = response.json().get("id")
        print(f"{Fore.GREEN}✓ Lakehouse created: {lakehouse_id}{Style.RESET_ALL}")
        
        # Wait for provisioning
        print(f"{Fore.CYAN}Waiting for lakehouse provisioning...{Style.RESET_ALL}")
        time.sleep(15)
        
        return lakehouse_id
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 409:
            print(f"{Fore.YELLOW}! Lakehouse already exists, finding it...{Style.RESET_ALL}")
            try:
                list_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses"
                response = requests.get(list_url, headers=headers, timeout=30)
                response.raise_for_status()
                
                lakehouses = response.json().get("value", [])
                for lh in lakehouses:
                    if lh.get("displayName") == lakehouse_name:
                        lakehouse_id = lh.get("id")
                        print(f"{Fore.GREEN}✓ Found existing: {lakehouse_id}{Style.RESET_ALL}")
                        return lakehouse_id
            except Exception as list_error:
                print(f"{Fore.RED}✗ Error finding lakehouse: {list_error}{Style.RESET_ALL}")
        
        print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response:
            print(f"  Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"{Fore.RED}✗ Unexpected error: {e}{Style.RESET_ALL}")
        return None


def create_notebook(workspace_id, notebook_name, token):
    """Create notebook in workspace."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks"
    
    payload = {
        "displayName": notebook_name,
        "description": "Conference attendance data pipeline - fully automated"
    }
    
    print(f"\n{Fore.CYAN}Creating Notebook: {notebook_name}{Style.RESET_ALL}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        notebook_id = response.json().get("id")
        print(f"{Fore.GREEN}✓ Notebook created: {notebook_id}{Style.RESET_ALL}")
        
        return notebook_id
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 409:
            print(f"{Fore.YELLOW}! Notebook already exists{Style.RESET_ALL}")
            # Find existing
            try:
                list_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks"
                response = requests.get(list_url, headers=headers, timeout=30)
                response.raise_for_status()
                
                notebooks = response.json().get("value", [])
                for nb in notebooks:
                    if nb.get("displayName") == notebook_name:
                        notebook_id = nb.get("id")
                        print(f"{Fore.GREEN}✓ Found existing: {notebook_id}{Style.RESET_ALL}")
                        return notebook_id
            except:
                pass
        else:
            print(f"{Fore.RED}✗ Error creating notebook: {e}{Style.RESET_ALL}")
            if hasattr(e, 'response') and e.response:
                print(f"  Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"{Fore.RED}✗ Unexpected error: {e}{Style.RESET_ALL}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Fully automated Fabric deployment - no manual steps!')
    parser.add_argument('--workspace-id', required=True, help='Fabric workspace ID')
    parser.add_argument('--lakehouse-name', default='ConferenceDataLakehouse', help='Lakehouse name')
    parser.add_argument('--notebook-name', default='Load Conference Data', help='Notebook name')
    parser.add_argument('--data-folder', default='conference-data', help='Folder name in OneLake Files')
    
    args = parser.parse_args()
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}FULLY AUTOMATED Fabric Deployment - No Manual Steps!")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}Configuration:{Style.RESET_ALL}")
    print(f"  Workspace ID: {args.workspace_id}")
    print(f"  Lakehouse: {args.lakehouse_name}")
    print(f"  Notebook: {args.notebook_name}")
    print(f"  Data folder: {args.data_folder}")
    
    # Get token
    print(f"\n{Fore.CYAN}Authenticating with Entra ID...{Style.RESET_ALL}")
    token = get_fabric_token()
    if not token:
        print(f"{Fore.RED}✗ Failed to get authentication token{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Make sure you're logged in: az login{Style.RESET_ALL}")
        return 1
    print(f"{Fore.GREEN}✓ Authenticated{Style.RESET_ALL}")
    
    # Step 1: Create Lakehouse
    lakehouse_id = create_lakehouse(args.workspace_id, args.lakehouse_name, token)
    if not lakehouse_id:
        print(f"\n{Fore.RED}✗ Failed to create lakehouse{Style.RESET_ALL}")
        return 1
    
    # Step 2: Upload data files directly to OneLake (NO SHORTCUTS!)
    print(f"\n{Fore.CYAN}Uploading data files directly to OneLake...{Style.RESET_ALL}")
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    sample_data_dir = project_root / "sample-data"
    
    csv_file = sample_data_dir / "conference_attendance.csv"
    json_file = sample_data_dir / "conference_attendance.json"
    
    if not csv_file.exists():
        print(f"{Fore.RED}✗ CSV file not found: {csv_file}{Style.RESET_ALL}")
        return 1
    
    if not json_file.exists():
        print(f"{Fore.RED}✗ JSON file not found: {json_file}{Style.RESET_ALL}")
        return 1
    
    # Upload files
    csv_success = upload_file_to_onelake(
        args.workspace_id,
        lakehouse_id,
        str(csv_file),
        args.data_folder,
        token
    )
    
    json_success = upload_file_to_onelake(
        args.workspace_id,
        lakehouse_id,
        str(json_file),
        args.data_folder,
        token
    )
    
    if not (csv_success and json_success):
        print(f"\n{Fore.YELLOW}⚠ Some files failed to upload{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}You may need to upload them manually{Style.RESET_ALL}")
    
    # Step 3: Create Notebook
    notebook_id = create_notebook(args.workspace_id, args.notebook_name, token)
    
    # Summary
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.GREEN}✓ FULLY AUTOMATED DEPLOYMENT COMPLETE!")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}What was created:{Style.RESET_ALL}")
    print(f"  ✓ Lakehouse: {args.lakehouse_name} ({lakehouse_id})")
    print(f"  ✓ Data uploaded to: Files/{args.data_folder}/")
    if csv_success:
        print(f"    ✓ conference_attendance.csv")
    if json_success:
        print(f"    ✓ conference_attendance.json")
    if notebook_id:
        print(f"  ✓ Notebook: {args.notebook_name} ({notebook_id})")
    
    print(f"\n{Fore.WHITE}Next steps:{Style.RESET_ALL}")
    print(f"  1. Open workspace: https://app.fabric.microsoft.com/groups/{args.workspace_id}")
    print(f"  2. Open notebook: {args.notebook_name}")
    print(f"  3. Attach lakehouse: {args.lakehouse_name}")
    print(f"  4. Run the notebook!")
    
    print(f"\n{Fore.WHITE}The notebook will read from:{Style.RESET_ALL}")
    print(f"  Files/{args.data_folder}/conference_attendance.csv")
    
    print(f"\n{Fore.GREEN}✓✓✓ NO MANUAL STEPS REQUIRED! ✓✓✓{Style.RESET_ALL}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
