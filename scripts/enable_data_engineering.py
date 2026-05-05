#!/usr/bin/env python3
"""
Enable Data Engineering Workload Helper

This script provides instructions for enabling the Data Engineering workload
on your Fabric capacity. Unfortunately, this CANNOT be automated via API
and must be done manually through the Admin Portal.
"""

import sys

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


def main():
    """Show instructions for enabling Data Engineering."""
    
    print_header("⚠ Data Engineering Workload Not Enabled")
    
    print(f"{Fore.WHITE}Your Fabric capacity does not have the Data Engineering workload enabled.{Style.RESET_ALL}")
    print(f"{Fore.WHITE}This is required to create Lakehouses and Notebooks via API.{Style.RESET_ALL}")
    print()
    
    print(f"{Fore.YELLOW}Why This Cannot Be Automated:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}• Fabric API does not support enabling workloads programmatically{Style.RESET_ALL}")
    print(f"{Fore.WHITE}• This is an admin-level capacity configuration{Style.RESET_ALL}")
    print(f"{Fore.WHITE}• Must be done through the Fabric Admin Portal{Style.RESET_ALL}")
    print()
    
    print_header("📋 Manual Steps to Enable Data Engineering")
    
    print(f"{Fore.CYAN}Step 1: Open Fabric Admin Portal{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   Go to: {Fore.GREEN}https://app.fabric.microsoft.com/admin{Style.RESET_ALL}")
    print()
    
    print(f"{Fore.CYAN}Step 2: Navigate to Capacity Settings{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Click: Settings (gear icon) → Admin portal{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Select: Capacity settings{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Click: Fabric capacity tab{Style.RESET_ALL}")
    print()
    
    print(f"{Fore.CYAN}Step 3: Select Your Capacity{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Find and click your capacity (e.g., 'akhfabcapacity'){Style.RESET_ALL}")
    print()
    
    print(f"{Fore.CYAN}Step 4: Configure Data Engineering Settings{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Scroll to: Data Engineering/Science Settings{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Click: Open Spark Compute{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Configure settings:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}     - Enable Starter Pool (recommended for development){Style.RESET_ALL}")
    print(f"{Fore.WHITE}     - Set node size and autoscaling preferences{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Click: Save{Style.RESET_ALL}")
    print()
    
    print(f"{Fore.CYAN}Step 5: Verify Configuration{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Wait 2-3 minutes for settings to propagate{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Re-run the deployment script{Style.RESET_ALL}")
    print()
    
    print_header("📝 Alternative: Manual Lakehouse & Notebook Creation")
    
    print(f"{Fore.YELLOW}If you prefer to create resources manually:{Style.RESET_ALL}")
    print()
    
    print(f"{Fore.CYAN}1. Create Lakehouse:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Go to your workspace{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Click: + New → Lakehouse{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Name: ConferenceDataLakehouse{Style.RESET_ALL}")
    print()
    
    print(f"{Fore.CYAN}2. Create Notebook:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • In workspace, click: + New → Notebook{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Name: Load Conference Data{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Copy cells from: notebooks/load_conference_data.ipynb{Style.RESET_ALL}")
    print()
    
    print(f"{Fore.CYAN}3. Create Storage Shortcut:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • In Lakehouse → Files → New shortcut{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Type: Azure Data Lake Storage Gen2{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • URL: https://westusattendiesstore.dfs.core.windows.net/conference-data{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Authentication: Use Entra identity{Style.RESET_ALL}")
    print()
    
    print(f"{Fore.CYAN}4. Run the Notebook:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Attach notebook to lakehouse{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Update storage account name in notebook{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Click: Run all{Style.RESET_ALL}")
    print()
    
    print_header("✅ What You Have Already")
    
    print(f"{Fore.GREEN}✓ Azure Resources:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Resource Group: westusattendiesdata{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Storage Account: westusattendiesstore{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Sample data uploaded (CSV + JSON){Style.RESET_ALL}")
    print()
    
    print(f"{Fore.GREEN}✓ Fabric Workspace:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Name: West US Training{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • ID: 00bcfcd2-97d8-48b0-8ae4-67e7395ac373{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • URL: https://app.fabric.microsoft.com/groups/00bcfcd2-97d8-48b0-8ae4-67e7395ac373{Style.RESET_ALL}")
    print()
    
    print(f"{Fore.CYAN}💡 Tip: Once Data Engineering is enabled, re-run:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   python scripts/deploy_fabric_workspace.py --workspace-id 00bcfcd2-97d8-48b0-8ae4-67e7395ac373 --storage-account westusattendiesstore{Style.RESET_ALL}")
    print()


if __name__ == "__main__":
    main()
