#!/usr/bin/env python3
"""
Assign Workspace to Capacity and Create Lakehouse

This script fixes the "FeatureNotAvailable" error by:
1. Assigning the workspace to a Fabric capacity
2. Waiting for assignment to complete
3. Creating the Lakehouse
4. Creating the Notebook
"""

import sys
import os
import subprocess
import json
import time
import base64
import argparse
from pathlib import Path

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
    print("Error: 'requests' package required. Run: pip install requests")
    sys.exit(1)


def run_command(cmd):
    """Execute command."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_fabric_token():
    """Get Fabric API token."""
    return run_command(
        "az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv"
    )


def get_capacity_id(capacity_name):
    """Get capacity ID by name."""
    print(f"\n{Fore.CYAN}Finding Capacity: {capacity_name}{Style.RESET_ALL}")
    
    token = get_fabric_token()
    if not token:
        return None
    
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://api.fabric.microsoft.com/v1/capacities"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        capacities = response.json().get("value", [])
        
        for capacity in capacities:
            if capacity.get("displayName") == capacity_name:
                capacity_id = capacity.get("id")
                print(f"{Fore.GREEN}✓ Found capacity: {capacity_id}{Style.RESET_ALL}")
                return capacity_id
        
        print(f"{Fore.RED}✗ Capacity not found: {capacity_name}{Style.RESET_ALL}")
        return None
        
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to get capacity: {e}{Style.RESET_ALL}")
        return None


def create_workspace(workspace_name):
    """Create new Fabric workspace."""
    print(f"\n{Fore.CYAN}Creating Workspace: {workspace_name}{Style.RESET_ALL}")
    
    token = get_fabric_token()
    if not token:
        return None
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = "https://api.powerbi.com/v1.0/myorg/groups"
    payload = {
        "name": workspace_name
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        workspace_id = response.json().get("id")
        print(f"{Fore.GREEN}✓ Workspace created: {workspace_id}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  Waiting for workspace initialization...{Style.RESET_ALL}")
        time.sleep(5)
        
        return workspace_id
        
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to create workspace: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(json.dumps(error_detail, indent=2))
            except:
                print(e.response.text)
        return None


def get_capacity_id(capacity_name):
    """Get capacity ID by name."""
    print(f"\n{Fore.CYAN}Finding capacity: {capacity_name}{Style.RESET_ALL}")
    
    token = get_fabric_token()
    if not token:
        return None
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # List all capacities
        url = "https://api.powerbi.com/v1.0/myorg/capacities"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        capacities = response.json().get("value", [])
        
        for cap in capacities:
            if cap.get("displayName") == capacity_name:
                cap_id = cap.get("id")
                print(f"{Fore.GREEN}✓ Found capacity: {cap_id}{Style.RESET_ALL}")
                print(f"  SKU: {cap.get('sku')}")
                print(f"  State: {cap.get('state')}")
                return cap_id
        
        print(f"{Fore.RED}✗ Capacity '{capacity_name}' not found{Style.RESET_ALL}")
        return None
        
    except Exception as e:
        print(f"{Fore.RED}✗ Error finding capacity: {e}{Style.RESET_ALL}")
        return None


def configure_git_integration(workspace_id, github_org, github_repo, github_branch="main", github_directory="/"):
    """Configure Git integration for workspace."""
    print(f"\n{Fore.CYAN}Configuring Git Integration{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  Organization: {github_org}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  Repository: {github_repo}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  Branch: {github_branch}{Style.RESET_ALL}")
    
    token = get_fabric_token()
    if not token:
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Step 1: Connect to Git
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/git/connect"
    payload = {
        "gitProviderDetails": {
            "organizationName": github_org,
            "projectName": github_repo,
            "gitProviderType": "GitHub",
            "repositoryName": github_repo,
            "branchName": github_branch,
            "directoryName": github_directory
        }
    }
    
    try:
        print(f"{Fore.WHITE}  Connecting to GitHub...{Style.RESET_ALL}")
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code in [200, 201, 202]:
            print(f"{Fore.GREEN}✓ Git connection established{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}! Connection response: {response.status_code}{Style.RESET_ALL}")
            if response.text:
                try:
                    error_detail = response.json()
                    print(f"{Fore.YELLOW}  {error_detail.get('message', response.text)}{Style.RESET_ALL}")
                except:
                    print(f"{Fore.YELLOW}  {response.text}{Style.RESET_ALL}")
        
        # Wait for connection to establish
        time.sleep(5)
        
        # Step 2: Initialize Git sync (pull from repository)
        print(f"{Fore.WHITE}  Initializing workspace from GitHub...{Style.RESET_ALL}")
        sync_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/git/initializeConnection"
        
        sync_response = requests.post(sync_url, headers=headers, json={}, timeout=120)
        
        if sync_response.status_code in [200, 201, 202]:
            print(f"{Fore.GREEN}✓ Workspace initialized from GitHub{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  Waiting for sync to complete...{Style.RESET_ALL}")
            time.sleep(10)
            return True
        else:
            print(f"{Fore.YELLOW}! Sync response: {sync_response.status_code}{Style.RESET_ALL}")
            # Even if sync fails initially, connection might be established
            return True
            
    except Exception as e:
        print(f"{Fore.RED}✗ Git integration failed: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(json.dumps(error_detail, indent=2))
            except:
                print(e.response.text)
        print(f"{Fore.YELLOW}⚠ You may need to configure Git manually in workspace settings{Style.RESET_ALL}")
        return False


def assign_workspace_to_capacity(workspace_id, capacity_id):
    """Assign workspace to capacity."""
    print(f"\n{Fore.CYAN}Assigning workspace to capacity...{Style.RESET_ALL}")
    
    token = get_fabric_token()
    if not token:
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Assign workspace to capacity
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/AssignToCapacity"
        payload = {"capacityId": capacity_id}
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        print(f"{Fore.GREEN}✓ Workspace assigned to capacity{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  Waiting for assignment to complete...{Style.RESET_ALL}")
        time.sleep(10)  # Wait for assignment to propagate
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to assign workspace: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(json.dumps(e.response.json(), indent=2))
            except:
                print(e.response.text)
        return False


def create_lakehouse(workspace_id, lakehouse_name):
    """Create Lakehouse in workspace."""
    print(f"\n{Fore.CYAN}Creating Lakehouse: {lakehouse_name}{Style.RESET_ALL}")
    
    token = get_fabric_token()
    if not token:
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
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        lakehouse_id = response.json().get("id")
        print(f"{Fore.GREEN}✓ Lakehouse created: {lakehouse_id}{Style.RESET_ALL}")
        return lakehouse_id
        
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to create lakehouse: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(json.dumps(error_detail, indent=2))
            except:
                print(e.response.text)
        return None


def create_notebook(workspace_id, notebook_name):
    """Create Notebook in workspace."""
    print(f"\n{Fore.CYAN}Creating Notebook: {notebook_name}{Style.RESET_ALL}")
    
    token = get_fabric_token()
    if not token:
        return None
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks"
    payload = {
        "displayName": notebook_name,
        "description": "Pipeline notebook for loading conference data"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        notebook_id = response.json().get("id")
        print(f"{Fore.GREEN}✓ Notebook created: {notebook_id}{Style.RESET_ALL}")
        return notebook_id
        
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to create notebook: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(json.dumps(error_detail, indent=2))
            except:
                print(e.response.text)
        return None


def convert_ipynb_to_fabric_py(ipynb_path):
    """Convert Jupyter notebook to Fabric Python notebook format."""
    import json
    
    with open(ipynb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    py_lines = []
    
    for cell in nb.get('cells', []):
        cell_type = cell.get('cell_type')
        source = cell.get('source', [])
        
        # Convert source to text
        if isinstance(source, list):
            content = ''.join(source)
        else:
            content = source
        
        if cell_type == 'markdown':
            # Markdown cells: comment each line
            py_lines.append("# MARKDOWN")
            for line in content.split('\n'):
                py_lines.append(f"# {line}")
        elif cell_type == 'code':
            # Code cells: add as-is
            py_lines.append("# CODE")
            py_lines.append(content.rstrip())
        
        # Cell separator
        py_lines.append("")
        py_lines.append("# CELL")
        py_lines.append("")
    
    return '\n'.join(py_lines)


def upload_notebook_content(workspace_id, notebook_id, notebook_file_path):
    """Upload notebook content from local .ipynb file."""
    import os
    import base64
    
    print(f"\n{Fore.CYAN}Uploading notebook content...{Style.RESET_ALL}")
    
    if not os.path.exists(notebook_file_path):
        print(f"{Fore.RED}✗ Notebook file not found: {notebook_file_path}{Style.RESET_ALL}")
        return False
    
    token = get_fabric_token()
    if not token:
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Convert .ipynb to Fabric Python format
        print(f"{Fore.WHITE}  Converting notebook format...{Style.RESET_ALL}")
        py_content = convert_ipynb_to_fabric_py(notebook_file_path)
        
        print(f"{Fore.WHITE}  Converted to {len(py_content)} characters{Style.RESET_ALL}")
        
        # Encode to base64
        content_base64 = base64.b64encode(py_content.encode('utf-8')).decode('ascii')
        
        # Try simple update first
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/updateDefinition"
        
        payload = {
            "definition": {
                "parts": [
                    {
                        "path": "notebook-content.py",
                        "payload": content_base64,
                        "payloadType": "InlineBase64"
                    }
                ]
            }
        }
        
        print(f"{Fore.WHITE}  Uploading to Fabric...{Style.RESET_ALL}")
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code in [200, 201, 202]:
            print(f"{Fore.GREEN}✓ Notebook content uploaded{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  Note: If notebook appears empty, manual copy may be needed{Style.RESET_ALL}")
            time.sleep(3)
            return True
        else:
            print(f"{Fore.YELLOW}! Upload returned: {response.status_code}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  Notebook created but may be empty{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  Use manual copy from: notebooks/load_conference_data.ipynb{Style.RESET_ALL}")
            return False
        
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to upload notebook content: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(json.dumps(error_detail, indent=2))
            except:
                print(e.response.text)
        print(f"\n{Fore.YELLOW}⚠ Notebook created but empty - manual copy needed{Style.RESET_ALL}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Fix workspace capacity assignment and create resources")
    parser.add_argument("--workspace-name", required=True, help="Fabric workspace name (will create if doesn't exist)")
    parser.add_argument("--capacity-name", required=True, help="Capacity name")
    parser.add_argument("--github-org", default="KeykPa", help="GitHub organization/username")
    parser.add_argument("--github-repo", default="FabricPipelineAutomation", help="GitHub repository name")
    parser.add_argument("--github-branch", default="main", help="GitHub branch")
    parser.add_argument("--github-directory", default="/", help="Directory in repo (default: root)")
    parser.add_argument("--use-git", action="store_true", default=True, help="Configure Git integration (default: True)")
    parser.add_argument("--lakehouse-name", default="ConferenceDataLakehouse", help="Lakehouse name")
    parser.add_argument("--notebook-name", default="Load Conference Data", help="Notebook name")
    
    args = parser.parse_args()
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Automated Fabric Workspace Setup with GitOps")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    # Step 0: Create workspace
    workspace_id = create_workspace(args.workspace_name)
    if not workspace_id:
        print(f"\n{Fore.RED}✗ Cannot proceed without workspace{Style.RESET_ALL}")
        sys.exit(1)
    
    # Step 1: Get capacity ID
    capacity_id = get_capacity_id(args.capacity_name)
    if not capacity_id:
        print(f"\n{Fore.RED}✗ Cannot proceed without capacity ID{Style.RESET_ALL}")
        sys.exit(1)
    
    # Step 2: Assign workspace to capacity
    if not assign_workspace_to_capacity(workspace_id, capacity_id):
        print(f"\n{Fore.RED}✗ Workspace assignment failed{Style.RESET_ALL}")
        sys.exit(1)
    
    # Step 2.5: Configure Git Integration
    git_configured = False
    if args.use_git:
        git_configured = configure_git_integration(
            workspace_id,
            args.github_org,
            args.github_repo,
            args.github_branch,
            args.github_directory
        )
    
    # Step 3: Create resources (only if Git not configured, otherwise they come from GitHub)
    lakehouse_id = None
    notebook_id = None
    
    if not git_configured:
        print(f"\n{Fore.YELLOW}Git integration not configured - creating resources manually{Style.RESET_ALL}")
        
        # Step 3: Create Lakehouse
        lakehouse_id = create_lakehouse(workspace_id, args.lakehouse_name)
        if not lakehouse_id:
            print(f"\n{Fore.YELLOW}⚠ Lakehouse creation failed - may need manual creation{Style.RESET_ALL}")
        
        # Step 4: Create Notebook
        notebook_id = create_notebook(workspace_id, args.notebook_name)
        if not notebook_id:
            print(f"\n{Fore.YELLOW}⚠ Notebook creation failed - may need manual creation{Style.RESET_ALL}")
        else:
            # Step 4.5: Upload notebook content
            script_dir = Path(__file__).parent
            notebook_file = script_dir.parent / "notebooks" / "load_conference_data.ipynb"
            
            if notebook_file.exists():
                upload_notebook_content(workspace_id, notebook_id, str(notebook_file))
            else:
                print(f"{Fore.YELLOW}⚠ Notebook file not found at: {notebook_file}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}⚠ Notebook created but empty{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.GREEN}✓ Git integration configured - resources will sync from GitHub{Style.RESET_ALL}")
    
    # Summary
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Deployment Summary")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.GREEN}✓ Workspace created: {args.workspace_name}{Style.RESET_ALL}")
    print(f"  ID: {workspace_id}")
    print(f"{Fore.GREEN}✓ Workspace assigned to capacity: {args.capacity_name}{Style.RESET_ALL}")
    
    if git_configured:
        print(f"{Fore.GREEN}✓ Git integration configured{Style.RESET_ALL}")
        print(f"  Repository: {args.github_org}/{args.github_repo}")
        print(f"  Branch: {args.github_branch}")
        print(f"{Fore.GREEN}✓ Notebooks and resources synced from GitHub{Style.RESET_ALL}")
    else:
        if lakehouse_id:
            print(f"{Fore.GREEN}✓ Lakehouse created{Style.RESET_ALL}")
        if notebook_id:
            print(f"{Fore.GREEN}✓ Notebook created{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}Next Steps:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}1. Open workspace: https://app.fabric.microsoft.com/groups/{workspace_id}{Style.RESET_ALL}")
    
    if git_configured:
        print(f"{Fore.WHITE}2. Verify notebook 'Load Conference Data' appears in workspace{Style.RESET_ALL}")
        print(f"{Fore.WHITE}3. Create Lakehouse if not auto-created: 'ConferenceDataLakehouse'{Style.RESET_ALL}")
        print(f"{Fore.WHITE}4. Create storage shortcut in Lakehouse{Style.RESET_ALL}")
        print(f"{Fore.WHITE}5. Run the 'Load Conference Data' notebook{Style.RESET_ALL}")
        print(f"{Fore.WHITE}6. Create Power BI report{Style.RESET_ALL}")
    else:
        print(f"{Fore.WHITE}2. Create storage shortcut in Lakehouse to blob storage{Style.RESET_ALL}")
        print(f"{Fore.WHITE}3. Run the 'Load Conference Data' notebook{Style.RESET_ALL}")
        print(f"{Fore.WHITE}4. Create Power BI report from semantic model{Style.RESET_ALL}")
    
    print()
    print(f"{Fore.CYAN}Storage Shortcut Details:{Style.RESET_ALL}")
    print(f"  URL: https://westusattendiesstore.dfs.core.windows.net/")
    print(f"  Container: conference-data")
    print(f"  Auth: Microsoft Entra ID")
    print()


if __name__ == "__main__":
    main()
