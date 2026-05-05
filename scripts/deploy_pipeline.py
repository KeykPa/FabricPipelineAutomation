#!/usr/bin/env python3
"""
Deploy Fabric Pipeline to a Workspace

This script deploys the conference attendance pipeline to a Microsoft Fabric workspace
using the Fabric REST API.
"""

import sys
import os
import json
import argparse
import subprocess
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
    print("Error: 'requests' package not found. Install dependencies with: pip install -r requirements.txt")
    sys.exit(1)


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


def deploy_pipeline(workspace_id, pipeline_path, tenant_id=None):
    """Deploy pipeline to Fabric workspace."""
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Fabric Pipeline Deployment")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    # Check Azure CLI
    if os.system("az --version > nul 2>&1" if os.name == "nt" else "az --version > /dev/null 2>&1") != 0:
        print(f"{Fore.RED}Error: Azure CLI is not installed.{Style.RESET_ALL}")
        print("Install from: https://docs.microsoft.com/cli/azure/install-azure-cli")
        sys.exit(1)
    
    # Check if pipeline file exists
    pipeline_path = Path(pipeline_path)
    if not pipeline_path.exists():
        print(f"{Fore.RED}Error: Pipeline file not found: {pipeline_path}{Style.RESET_ALL}")
        sys.exit(1)
    
    # Validate JSON
    print(f"{Fore.YELLOW}Validating pipeline definition...{Style.RESET_ALL}")
    try:
        with open(pipeline_path, 'r') as f:
            pipeline_content = json.load(f)
        print(f"{Fore.GREEN}✓ Pipeline JSON is valid{Style.RESET_ALL}")
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}Error: Invalid JSON in pipeline file: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)
    
    # Check Azure login
    print(f"\n{Fore.YELLOW}Checking Azure authentication...{Style.RESET_ALL}")
    account_info_str = run_command("az account show")
    
    if not account_info_str:
        print(f"{Fore.RED}Error: Not logged in to Azure.{Style.RESET_ALL}")
        print("Please run 'az login' first.")
        sys.exit(1)
    
    account_info = json.loads(account_info_str)
    print(f"{Fore.GREEN}✓ Logged in as: {account_info['user']['name']}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  Subscription: {account_info['name']}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  Tenant: {account_info['tenantId']}{Style.RESET_ALL}")
    
    # Get Fabric API token
    print(f"\n{Fore.YELLOW}Obtaining Fabric API access token...{Style.RESET_ALL}")
    token = run_command(
        "az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv"
    )
    
    if not token:
        print(f"{Fore.RED}Error: Failed to obtain access token{Style.RESET_ALL}")
        sys.exit(1)
    
    print(f"{Fore.GREEN}✓ Access token obtained{Style.RESET_ALL}")
    
    # Prepare API request
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    fabric_api_url = "https://api.fabric.microsoft.com/v1"
    
    # Deploy pipeline
    print(f"\n{Fore.YELLOW}Deploying pipeline to workspace...{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  Workspace ID: {workspace_id}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  Pipeline: {pipeline_content.get('displayName', 'Unknown')}{Style.RESET_ALL}")
    
    try:
        # Check if pipeline already exists
        list_url = f"{fabric_api_url}/workspaces/{workspace_id}/dataPipelines"
        
        print(f"\n{Fore.YELLOW}Checking for existing pipelines...{Style.RESET_ALL}")
        response = requests.get(list_url, headers=headers)
        response.raise_for_status()
        
        existing_pipelines = response.json().get("value", [])
        existing_pipeline = next(
            (p for p in existing_pipelines if p.get("displayName") == pipeline_content.get("displayName")),
            None
        )
        
        if existing_pipeline:
            pipeline_id = existing_pipeline["id"]
            print(f"{Fore.YELLOW}✓ Found existing pipeline: {pipeline_id}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  Updating existing pipeline...{Style.RESET_ALL}")
            
            update_url = f"{fabric_api_url}/workspaces/{workspace_id}/dataPipelines/{pipeline_id}"
            
            with open(pipeline_path, 'r') as f:
                pipeline_json = f.read()
            
            response = requests.patch(update_url, headers=headers, data=pipeline_json)
            response.raise_for_status()
            
            print(f"{Fore.GREEN}✓ Pipeline updated successfully!{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}  Creating new pipeline...{Style.RESET_ALL}")
            
            with open(pipeline_path, 'r') as f:
                pipeline_json = f.read()
            
            response = requests.post(list_url, headers=headers, data=pipeline_json)
            response.raise_for_status()
            
            print(f"{Fore.GREEN}✓ Pipeline created successfully!{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}Pipeline Details:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  Name: {pipeline_content.get('displayName', 'Unknown')}{Style.RESET_ALL}")
        if 'description' in pipeline_content:
            print(f"{Fore.WHITE}  Description: {pipeline_content['description']}{Style.RESET_ALL}")
        
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                error_msg += f"\n{json.dumps(error_details, indent=2)}"
            except:
                error_msg += f"\n{e.response.text}"
        
        print(f"\n{Fore.RED}Error: Failed to deploy pipeline: {error_msg}{Style.RESET_ALL}")
        sys.exit(1)
    
    # Summary
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Deployment Summary")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.GREEN}✓ Pipeline deployed successfully to Fabric workspace{Style.RESET_ALL}\n")
    
    print(f"{Fore.YELLOW}Next Steps:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}1. Navigate to: https://app.fabric.microsoft.com{Style.RESET_ALL}")
    print(f"{Fore.WHITE}2. Open your workspace{Style.RESET_ALL}")
    print(f"{Fore.WHITE}3. Go to Data Factory > Pipelines{Style.RESET_ALL}")
    print(f"{Fore.WHITE}4. Find '{pipeline_content.get('displayName', 'Unknown')}'{Style.RESET_ALL}")
    print(f"{Fore.WHITE}5. Configure linked services and connections{Style.RESET_ALL}")
    print(f"{Fore.WHITE}6. Run the pipeline to test{Style.RESET_ALL}")
    print()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Deploy Fabric pipeline to a workspace"
    )
    parser.add_argument(
        "--workspace-id",
        required=True,
        help="The ID of the Fabric workspace"
    )
    parser.add_argument(
        "--pipeline-path",
        required=True,
        help="Path to the pipeline definition JSON file"
    )
    parser.add_argument(
        "--tenant-id",
        help="Azure AD Tenant ID (optional)"
    )
    
    args = parser.parse_args()
    
    deploy_pipeline(
        workspace_id=args.workspace_id,
        pipeline_path=args.pipeline_path,
        tenant_id=args.tenant_id
    )


if __name__ == "__main__":
    main()
