#!/usr/bin/env python3
"""
Interactive Setup Script for Fabric Pipeline Project

This script provides a guided setup experience for configuring Azure resources
and Microsoft Fabric workspace for the conference attendance pipeline.
"""

import sys
import os
import random
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    # Fallback if colorama is not installed
    class Fore:
        CYAN = GREEN = YELLOW = WHITE = RED = ""
    class Style:
        RESET_ALL = ""

from setup_azure_resources import setup_azure_resources


def print_header(text):
    """Print a styled header."""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}{text}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")


def print_success(text):
    """Print success message."""
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")


def print_warning(text):
    """Print warning message."""
    print(f"{Fore.YELLOW}{text}{Style.RESET_ALL}")


def print_info(text, indent=0):
    """Print info message."""
    prefix = "  " * indent
    print(f"{Fore.WHITE}{prefix}{text}{Style.RESET_ALL}")


def get_input(prompt, default=None):
    """Get user input with optional default value."""
    if default:
        full_prompt = f"{prompt} [default: {default}]: "
    else:
        full_prompt = f"{prompt}: "
    
    value = input(full_prompt).strip()
    return value if value else default


def select_option(prompt, options, default=None):
    """Display options and get user selection."""
    print(f"\n{Fore.CYAN}{prompt}{Style.RESET_ALL}")
    for idx, (key, desc) in enumerate(options.items(), 1):
        print(f"{Fore.WHITE}  {idx}. {desc}{Style.RESET_ALL}")
    print()
    
    default_idx = default if default else 1
    choice = get_input(f"Select option (1-{len(options)})", str(default_idx))
    
    try:
        idx = int(choice)
        if 1 <= idx <= len(options):
            return list(options.keys())[idx - 1]
    except (ValueError, IndexError):
        pass
    
    # Return default if invalid
    return list(options.keys())[default_idx - 1]


def main():
    """Main interactive setup function."""
    print_header("Fabric Pipeline Project - Interactive Setup")
    
    # Check for Azure CLI
    if os.system("az --version > nul 2>&1" if os.name == "nt" else "az --version > /dev/null 2>&1") != 0:
        print(f"{Fore.RED}Error: Azure CLI is not installed.{Style.RESET_ALL}")
        print("Please install it from: https://docs.microsoft.com/cli/azure/install-azure-cli")
        sys.exit(1)
    
    print_info("Checking Azure authentication...")
    
    # Check if logged in
    result = os.popen("az account show 2>&1").read()
    if "az login" in result or "Please run" in result:
        print_warning("Not logged in to Azure. Please run 'az login' first.")
        sys.exit(1)
    
    print_success("Azure CLI authentication verified")
    print()
    
    # Collect configuration
    print_info("Please provide the following configuration details:")
    print()
    
    # 1. Azure Region
    regions = {
        "eastus": "East US (eastus)",
        "eastus2": "East US 2 (eastus2)",
        "westus": "West US (westus)",
        "westus2": "West US 2 (westus2)",
        "centralus": "Central US (centralus)",
        "northeurope": "North Europe (northeurope)",
        "westeurope": "West Europe (westeurope)",
        "southeastasia": "Southeast Asia (southeastasia)",
        "australiaeast": "Australia East (australiaeast)"
    }
    
    location = select_option("Available Azure Regions:", regions, default=1)
    print_success(f"Selected region: {location}")
    
    # 2. Resource Group
    print()
    print_info("Resource Group Configuration:", indent=0)
    default_rg = f"rg-fabric-pipeline-{location}"
    resource_group = get_input("Enter Resource Group name", default_rg)
    print_success(f"Resource Group: {resource_group}")
    
    # 3. Storage Account
    print()
    print_info("Storage Account Configuration:", indent=0)
    print_info("(Name must be globally unique, 3-24 lowercase letters and numbers)", indent=1)
    default_storage = f"stfabric{random.randint(1000, 9999)}"
    storage_account = get_input("Enter Storage Account name", default_storage)
    print_success(f"Storage Account: {storage_account}")
    
    # 4. Workspace Name
    print()
    print_info("Fabric Workspace Configuration:", indent=0)
    default_workspace = "ConferencePipeline"
    workspace_name = get_input("Enter Fabric Workspace name", default_workspace)
    print_success(f"Workspace Name: {workspace_name}")
    
    # 5. Capacity Configuration
    print()
    capacity_options = {
        "create": "Create new capacity (requires Microsoft Fabric subscription)",
        "existing": "Use existing capacity",
        "skip": "Skip capacity setup (use Trial or assign later)"
    }
    
    capacity_choice = select_option(
        "Fabric Capacity Configuration - What would you like to do?",
        capacity_options,
        default=3
    )
    
    capacity_name = None
    capacity_sku = "F2"
    use_existing = False
    
    if capacity_choice == "create":
        print()
        default_capacity = f"fabric-capacity-{random.randint(100, 999)}"
        capacity_name = get_input("Enter Capacity name", default_capacity)
        
        print()
        sku_options = {
            "F2": "F2  (2 cores) - Starting tier",
            "F4": "F4  (4 cores)",
            "F8": "F8  (8 cores)",
            "F16": "F16 (16 cores)"
        }
        capacity_sku = select_option("Available Capacity SKUs:", sku_options, default=1)
        print_success(f"Capacity: {capacity_name} (SKU: {capacity_sku})")
        
    elif capacity_choice == "existing":
        print()
        capacity_name = get_input("Enter existing Capacity name", None)
        use_existing = True
        print_success(f"Will use existing capacity: {capacity_name}")
    else:
        print_warning("Skipping capacity setup - you can assign workspace to Trial or capacity later")
    
    # Configuration Summary
    print_header("Configuration Summary")
    print_info(f"Resource Group:   {resource_group}")
    print_info(f"Location:         {location}")
    print_info(f"Storage Account:  {storage_account}")
    print_info(f"Workspace Name:   {workspace_name}")
    if capacity_name:
        print_info(f"Capacity Name:    {capacity_name}")
        if not use_existing:
            print_info(f"Capacity SKU:     {capacity_sku}")
    print()
    
    # Confirm
    confirm = get_input("Proceed with setup? (y/n)", "y").lower()
    if confirm != "y":
        print_warning("Setup cancelled.")
        sys.exit(0)
    
    print()
    print_success("Starting setup process...")
    print()
    
    # Call the main setup function
    try:
        setup_azure_resources(
            resource_group_name=resource_group,
            location=location,
            storage_account_name=storage_account,
            workspace_name=workspace_name,
            capacity_name=capacity_name,
            capacity_sku=capacity_sku,
            use_existing_capacity=use_existing
        )
    except Exception as e:
        print(f"\n{Fore.RED}Error during setup: {str(e)}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
