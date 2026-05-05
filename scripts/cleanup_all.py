#!/usr/bin/env python3
"""Clean up Fabric workspace and optionally Azure resources"""

import subprocess
import json
import argparse
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
    print("Error: requests required")
    exit(1)


def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception as e:
        return None


def get_fabric_token():
    return run_command(
        "az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv"
    )


def delete_workspace(workspace_id):
    """Delete Fabric workspace"""
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Deleting Fabric Workspace{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
    
    token = get_fabric_token()
    if not token:
        print(f"{Fore.RED}✗ Failed to get token{Style.RESET_ALL}")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # First, get workspace details
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            print(f"{Fore.YELLOW}! Workspace not found (already deleted?){Style.RESET_ALL}")
            return True
        
        response.raise_for_status()
        workspace = response.json()
        
        print(f"{Fore.WHITE}Workspace: {workspace.get('name')}{Style.RESET_ALL}")
        print(f"  ID: {workspace_id}")
        print()
        
        # Delete the workspace
        delete_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"
        print(f"Deleting workspace...")
        response = requests.delete(delete_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print(f"{Fore.GREEN}✓ Workspace deleted successfully{Style.RESET_ALL}")
            return True
        elif response.status_code == 404:
            print(f"{Fore.YELLOW}! Workspace already deleted{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}✗ Delete failed: {response.status_code}{Style.RESET_ALL}")
            print(f"  {response.text}")
            return False
            
    except Exception as e:
        print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        return False


def delete_azure_resources(resource_group):
    """Delete Azure resource group"""
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Deleting Azure Resources{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}Resource Group: {resource_group}{Style.RESET_ALL}")
    print()
    
    # Check if resource group exists
    cmd = f"az group exists -n {resource_group}"
    result = run_command(cmd)
    
    if result == "false":
        print(f"{Fore.YELLOW}! Resource group not found (already deleted?){Style.RESET_ALL}")
        return True
    
    print(f"Deleting resource group (this may take 2-3 minutes)...")
    cmd = f"az group delete --name {resource_group} --yes --no-wait"
    result = run_command(cmd)
    
    if result is not None:
        print(f"{Fore.GREEN}✓ Resource group deletion initiated{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  (Deletion continues in background){Style.RESET_ALL}")
        return True
    else:
        print(f"{Fore.RED}✗ Failed to delete resource group{Style.RESET_ALL}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Clean up Fabric workspace and Azure resources")
    parser.add_argument("--workspace-id", required=True, help="Fabric workspace ID to delete")
    parser.add_argument("--delete-azure", action="store_true", help="Also delete Azure resource group")
    parser.add_argument("--resource-group", default="westusattendiesdata", help="Azure resource group name")
    
    args = parser.parse_args()
    
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Cleanup Script{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}Configuration:{Style.RESET_ALL}")
    print(f"  Workspace ID: {args.workspace_id}")
    print(f"  Delete Azure: {args.delete_azure}")
    if args.delete_azure:
        print(f"  Resource Group: {args.resource_group}")
    print()
    
    # Delete Fabric workspace
    workspace_deleted = delete_workspace(args.workspace_id)
    
    # Delete Azure resources if requested
    azure_deleted = True
    if args.delete_azure:
        time.sleep(2)
        azure_deleted = delete_azure_resources(args.resource_group)
    
    # Summary
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Cleanup Summary{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
    
    if workspace_deleted:
        print(f"{Fore.GREEN}✓ Fabric workspace deleted{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}✗ Fabric workspace deletion failed{Style.RESET_ALL}")
    
    if args.delete_azure:
        if azure_deleted:
            print(f"{Fore.GREEN}✓ Azure resources deletion initiated{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}✗ Azure resources deletion failed{Style.RESET_ALL}")
    
    print()
    
    if workspace_deleted and azure_deleted:
        print(f"{Fore.GREEN}✓ Cleanup completed successfully!{Style.RESET_ALL}")
        print()
        print(f"{Fore.WHITE}Next steps:{Style.RESET_ALL}")
        print(f"  1. Run: python scripts/setup_azure_resources.py")
        print(f"  2. Run: python scripts/fix_and_deploy.py --workspace-name 'West US Training'")
        print()
        return 0
    else:
        print(f"{Fore.RED}✗ Cleanup had errors{Style.RESET_ALL}")
        return 1


if __name__ == "__main__":
    exit(main())
