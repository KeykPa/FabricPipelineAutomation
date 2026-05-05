#!/usr/bin/env python3
"""
Check Fabric Tenant Capabilities

This script diagnoses why the Fabric API returns "FeatureNotAvailable"
by checking tenant settings, capacity configuration, and permissions.
"""

import sys
import subprocess
import json

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
    """Execute command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return None


def get_fabric_token():
    """Get Fabric API access token."""
    return run_command(
        "az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv"
    )


def check_workspace_permissions(workspace_id):
    """Check workspace permissions for current user."""
    print(f"\n{Fore.CYAN}Checking Workspace Permissions...{Style.RESET_ALL}")
    
    token = get_fabric_token()
    if not token:
        print(f"{Fore.RED}✗ Failed to get token{Style.RESET_ALL}")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Get workspace details
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        workspace = response.json()
        print(f"{Fore.GREEN}✓ Workspace accessible{Style.RESET_ALL}")
        print(f"  Name: {workspace.get('displayName')}")
        print(f"  Type: {workspace.get('type')}")
        print(f"  Capacity ID: {workspace.get('capacityId')}")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}✗ Cannot access workspace: {e}{Style.RESET_ALL}")
        return False


def check_tenant_settings():
    """Check Fabric tenant settings."""
    print(f"\n{Fore.CYAN}Checking Tenant Settings...{Style.RESET_ALL}")
    
    print(f"{Fore.YELLOW}⚠ Tenant settings must be checked manually:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}1. Go to: https://app.fabric.microsoft.com/admin{Style.RESET_ALL}")
    print(f"{Fore.WHITE}2. Check 'Tenant settings' section{Style.RESET_ALL}")
    print(f"{Fore.WHITE}3. Verify these are enabled:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Users can create Fabric items{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Users can use public APIs{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Service principals can use Fabric APIs{Style.RESET_ALL}")
    print()


def check_capacity_features(capacity_id=None):
    """Check capacity configuration."""
    print(f"\n{Fore.CYAN}Checking Capacity Features...{Style.RESET_ALL}")
    
    if not capacity_id:
        print(f"{Fore.YELLOW}⚠ No capacity ID provided{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Check capacity settings manually in Admin Portal{Style.RESET_ALL}")
        return
    
    print(f"{Fore.WHITE}Capacity ID: {capacity_id}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}⚠ Check these capacity settings in Admin Portal:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Data Engineering/Science enabled{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Spark compute configured{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Capacity SKU supports Data Engineering{Style.RESET_ALL}")
    print()


def main():
    """Main diagnostic function."""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Fabric Tenant Capability Diagnostics")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    workspace_id = "00bcfcd2-97d8-48b0-8ae4-67e7395ac373"
    
    # Check workspace
    has_workspace_access = check_workspace_permissions(workspace_id)
    
    # Check tenant settings
    check_tenant_settings()
    
    # Check capacity
    check_capacity_features("akhfabcapacity")
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Diagnosis Summary")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.YELLOW}The 'FeatureNotAvailable' error suggests:{Style.RESET_ALL}")
    print()
    print(f"{Fore.WHITE}1. {Fore.CYAN}Tenant Restriction:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Your tenant may not have Fabric Data Engineering licensed{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Admin may have disabled Data Engineering features{Style.RESET_ALL}")
    print()
    print(f"{Fore.WHITE}2. {Fore.CYAN}Capacity Limitation:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • The capacity SKU may not support Data Engineering{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Trial capacities may have feature restrictions{Style.RESET_ALL}")
    print()
    print(f"{Fore.WHITE}3. {Fore.CYAN}API Permissions:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Fabric REST APIs may be disabled for your account{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Service principal API access may be restricted{Style.RESET_ALL}")
    print()
    
    print(f"{Fore.CYAN}Recommended Actions:{Style.RESET_ALL}")
    print()
    print(f"{Fore.GREEN}Option 1: Contact Fabric Administrator{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Ask them to enable Data Engineering for your tenant{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Verify Fabric trial/license includes Data Engineering{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Check tenant API settings are enabled{Style.RESET_ALL}")
    print()
    print(f"{Fore.GREEN}Option 2: Use Manual Creation (Works Now){Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Create Lakehouse/Notebook through Fabric UI{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • See: MANUAL_SETUP_GUIDE.md{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Time: ~5 minutes{Style.RESET_ALL}")
    print()
    print(f"{Fore.GREEN}Option 3: Try Different Capacity{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Create workspace in a Fabric F64+ capacity{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Ensure capacity has full Data Engineering enabled{Style.RESET_ALL}")
    print()


if __name__ == "__main__":
    main()
