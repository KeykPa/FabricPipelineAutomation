#!/usr/bin/env python3
"""
Complete End-to-End Deployment

This script automates the ENTIRE deployment:
1. Azure resources (storage, blob container)
2. Fabric workspace and capacity
3. Lakehouse creation
4. Notebook upload
5. Sample data upload

Run this ONE command to deploy everything!
"""

import sys
import os
import argparse
from pathlib import Path

# Import other setup scripts
sys.path.insert(0, str(Path(__file__).parent))

from setup_azure_resources import setup_azure_resources
from deploy_fabric_workspace import deploy_complete_workspace

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        CYAN = GREEN = YELLOW = WHITE = RED = ""
    class Style:
        RESET_ALL = ""


def print_header(text):
    """Print header."""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}{text}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")


def deploy_everything(
    resource_group_name,
    location,
    storage_account_name,
    workspace_name,
    capacity_name=None,
    capacity_sku=None,
    use_existing_capacity=False
):
    """Deploy everything end-to-end."""
    
    print_header("🚀 COMPLETE END-TO-END DEPLOYMENT 🚀")
    
    print(f"{Fore.WHITE}This will deploy:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  ✓ Azure Resource Group{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  ✓ Azure Storage Account{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  ✓ Blob Container with sample data{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  ✓ Fabric Workspace (assigned to capacity){Style.RESET_ALL}")
    print(f"{Fore.WHITE}  ✓ Fabric Lakehouse{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  ✓ Fabric Notebook (ready to run){Style.RESET_ALL}")
    print()
    
    # Step 1: Setup Azure Resources
    print_header("STEP 1: Azure Infrastructure Setup")
    
    workspace_id = setup_azure_resources(
        resource_group_name=resource_group_name,
        location=location,
        storage_account_name=storage_account_name,
        workspace_name=workspace_name,
        capacity_name=capacity_name,
        capacity_sku=capacity_sku,
        use_existing_capacity=use_existing_capacity
    )
    
    if not workspace_id:
        print(f"{Fore.RED}✗ Azure setup failed. Check errors above.{Style.RESET_ALL}")
        return False
    
    print(f"{Fore.GREEN}✓ Azure infrastructure deployed!{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  Workspace ID: {workspace_id}{Style.RESET_ALL}")
    
    # Step 1.5: Assign workspace to capacity (CRITICAL - enables Data Engineering API)
    print_header("STEP 2: Assign Workspace to Capacity")
    
    if capacity_name:
        import subprocess
        result = subprocess.run(
            f'python scripts/fix_and_deploy.py --workspace-id {workspace_id} --capacity-name "{capacity_name}" --lakehouse-name ConferenceDataLakehouse',
            shell=True,
            capture_output=True
        )
        
        if result.returncode != 0:
            print(f"{Fore.YELLOW}⚠ Automated creation had issues{Style.RESET_ALL}")
            print(f"{Fore.WHITE}See MANUAL_SETUP_GUIDE.md for manual steps{Style.RESET_ALL}")
            return False
        
        print(f"{Fore.GREEN}✓ Lakehouse and Notebook created!{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}⚠ No capacity specified - skipping Lakehouse creation{Style.RESET_ALL}")
        return False
    
    # Final Summary
    print_header("🎉 DEPLOYMENT COMPLETE! 🎉")
    
    print(f"{Fore.GREEN}✓ Everything deployed successfully!{Style.RESET_ALL}")
    print()
    print(f"{Fore.CYAN}Azure Infrastructure:{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  ✓ Resource Group: {resource_group_name}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  ✓ Storage Account: {storage_account_name}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  ✓ Sample data uploaded to blob storage{Style.RESET_ALL}")
    print()
    print(f"{Fore.CYAN}Fabric Resources:{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  ✓ Workspace: {workspace_name} (ID: {workspace_id}){Style.RESET_ALL}")
    print(f"{Fore.GREEN}  ✓ Lakehouse: ConferenceDataLakehouse{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  ✓ Notebook: Load Conference Data{Style.RESET_ALL}")
    print()
    
    print(f"{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}NEXT STEPS: Power BI Report Deployment")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}Step 1: Load Data into Lakehouse{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  a) Open workspace: https://app.fabric.microsoft.com/groups/{workspace_id}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  b) Open 'Load Conference Data' notebook{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  c) Create storage shortcut in Lakehouse:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}       • Lakehouse → Files → New shortcut → ADLS Gen2{Style.RESET_ALL}")
    print(f"{Fore.WHITE}       • URL: https://{storage_account_name}.dfs.core.windows.net/conference-data{Style.RESET_ALL}")
    print(f"{Fore.WHITE}       • Auth: Use Entra ID{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  d) Click 'Run all' in notebook{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  e) Wait for completion (2-3 minutes){Style.RESET_ALL}")
    print()
    
    print(f"{Fore.WHITE}Step 2: Create Power BI Report{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  After notebook completes, run:{Style.RESET_ALL}")
    print()
    print(f"{Fore.CYAN}  python scripts/create_powerbi_report.py \\{Style.RESET_ALL}")
    print(f"{Fore.CYAN}      --workspace-id {workspace_id} \\{Style.RESET_ALL}")
    print(f"{Fore.CYAN}      --lakehouse-name ConferenceDataLakehouse \\{Style.RESET_ALL}")
    print(f"{Fore.CYAN}      --report-name \"Conference Attendance Report\"{Style.RESET_ALL}")
    print()
    
    print(f"{Fore.WHITE}Step 3: Add Visuals to Report{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Open report in Power BI Service{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Click 'Edit' and add visuals{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • See template: powerbi-templates/README.md{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Full guide: docs/POWERBI_DEPLOYMENT.md{Style.RESET_ALL}")
    print()
    
    print(f"{Fore.CYAN}📊 Report Features:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Attendance overview with KPIs{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Searchable attendee list{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Session analytics and ratings{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Company and job title breakdowns{Style.RESET_ALL}")
    print()
    
    print(f"{Fore.CYAN}💡 All authentication uses Entra identity (DefaultAzureCredential){Style.RESET_ALL}")
    print(f"{Fore.CYAN}🔧 Full automation achieved for infrastructure + workspace + lakehouse!{Style.RESET_ALL}")
    print()
    
    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Complete end-to-end deployment of Fabric pipeline project"
    )
    parser.add_argument(
        "--resource-group",
        required=True,
        help="Azure resource group name"
    )
    parser.add_argument(
        "--location",
        required=True,
        help="Azure region (e.g., westus, eastus)"
    )
    parser.add_argument(
        "--storage-account",
        required=True,
        help="Storage account name (globally unique)"
    )
    parser.add_argument(
        "--workspace-name",
        required=True,
        help="Fabric workspace name"
    )
    parser.add_argument(
        "--capacity-name",
        help="Fabric capacity name (optional)"
    )
    parser.add_argument(
        "--capacity-sku",
        choices=["F2", "F4", "F8", "F16", "F32", "F64", "F128", "F256", "F512", "F1024", "F2048"],
        help="Fabric capacity SKU (optional)"
    )
    parser.add_argument(
        "--use-existing-capacity",
        action="store_true",
        help="Use existing capacity instead of creating new"
    )
    
    args = parser.parse_args()
    
    success = deploy_everything(
        resource_group_name=args.resource_group,
        location=args.location,
        storage_account_name=args.storage_account,
        workspace_name=args.workspace_name,
        capacity_name=args.capacity_name,
        capacity_sku=args.capacity_sku,
        use_existing_capacity=args.use_existing_capacity
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
