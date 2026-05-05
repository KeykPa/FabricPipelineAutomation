#!/usr/bin/env python3
"""
Complete GitOps Deployment - One Command Setup

This script:
1. Creates Fabric workspace
2. Assigns to capacity  
3. Provides clear instructions for GitHub connection
4. Waits for you to connect GitHub
5. Verifies notebook sync
6. Sets up storage shortcut (manual step with clear instructions)
"""

import sys
import subprocess
import time
import webbrowser

try:
    import requests
except ImportError:
    print("Installing requests...")
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
    import requests

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        CYAN = GREEN = YELLOW = WHITE = RED = BLUE = ""
    class Style:
        RESET_ALL = BRIGHT = ""

# Import functions from fix_and_deploy
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from fix_and_deploy import (
    get_fabric_token,
    create_workspace,
    get_capacity_id,
    assign_workspace_to_capacity
)


def wait_for_user_action(message):
    """Wait for user to complete a manual action."""
    print(f"\n{Fore.YELLOW}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'='*80}{Style.RESET_ALL}\n")
    input(f"{Fore.CYAN}Press ENTER when done...{Style.RESET_ALL}")


def check_workspace_items(workspace_id):
    """Check if workspace has items (notebooks from Git)."""
    token = get_fabric_token()
    if not token:
        return []
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        items = response.json().get("value", [])
        return items
    except:
        return []


def main():
    """Main deployment flow."""
    WORKSPACE_NAME = "West US Training"
    CAPACITY_NAME = "akhfabcapacity"
    GITHUB_ORG = "KeykPa"
    GITHUB_REPO = "FabricPipelineAutomation"
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Complete GitOps Deployment for Microsoft Fabric")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    # Step 1: Create workspace
    print(f"{Fore.CYAN}Step 1: Creating Workspace{Style.RESET_ALL}")
    workspace_id = create_workspace(WORKSPACE_NAME)
    if not workspace_id:
        print(f"{Fore.RED}✗ Failed to create workspace{Style.RESET_ALL}")
        return 1
    
    # Step 2: Get capacity
    print(f"\n{Fore.CYAN}Step 2: Finding Capacity{Style.RESET_ALL}")
    capacity_id = get_capacity_id(CAPACITY_NAME)
    if not capacity_id:
        print(f"{Fore.RED}✗ Failed to find capacity{Style.RESET_ALL}")
        return 1
    
    # Step 3: Assign to capacity
    print(f"\n{Fore.CYAN}Step 3: Assigning to Capacity{Style.RESET_ALL}")
    if not assign_workspace_to_capacity(workspace_id, capacity_id):
        print(f"{Fore.RED}✗ Failed to assign workspace{Style.RESET_ALL}")
        return 1
    
    # Step 4: GitHub Integration (Manual - requires OAuth)
    print(f"\n{Fore.CYAN}Step 4: GitHub Integration Setup{Style.RESET_ALL}")
    print(f"\n{Fore.WHITE}Opening workspace in browser...{Style.RESET_ALL}")
    
    workspace_url = f"https://app.fabric.microsoft.com/groups/{workspace_id}"
    webbrowser.open(workspace_url)
    time.sleep(2)
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}MANUAL STEP: Connect to GitHub")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}In the Fabric workspace tab that just opened:{Style.RESET_ALL}\n")
    print(f"  1. Click the {Fore.YELLOW}Settings icon (⚙️){Style.RESET_ALL} in the top right")
    print(f"  2. Go to {Fore.YELLOW}Git integration{Style.RESET_ALL} tab")
    print(f"  3. Click {Fore.YELLOW}Connect{Style.RESET_ALL}")
    print(f"  4. Select {Fore.YELLOW}GitHub{Style.RESET_ALL}")
    print(f"  5. Authorize Fabric to access GitHub (if prompted)")
    print(f"  6. Select:")
    print(f"     - Organization: {Fore.GREEN}{GITHUB_ORG}{Style.RESET_ALL}")
    print(f"     - Repository: {Fore.GREEN}{GITHUB_REPO}{Style.RESET_ALL}")
    print(f"     - Branch: {Fore.GREEN}main{Style.RESET_ALL}")
    print(f"     - Folder: {Fore.GREEN}/{Style.RESET_ALL} (root)")
    print(f"  7. Click {Fore.YELLOW}Connect and sync{Style.RESET_ALL}")
    print(f"  8. Wait for sync to complete (~30 seconds)")
    print()
    
    wait_for_user_action("Complete the GitHub connection steps above, then press ENTER")
    
    # Step 5: Verify sync
    print(f"\n{Fore.CYAN}Step 5: Verifying Notebook Sync{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Checking for notebooks...{Style.RESET_ALL}")
    
    time.sleep(3)
    items = check_workspace_items(workspace_id)
    
    notebooks = [item for item in items if item.get("type") == "Notebook"]
    
    if notebooks:
        print(f"{Fore.GREEN}✓ Found {len(notebooks)} notebook(s):{Style.RESET_ALL}")
        for nb in notebooks:
            print(f"  - {nb.get('displayName')}")
    else:
        print(f"{Fore.YELLOW}! No notebooks found yet{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  This may take a minute. Refresh the workspace in your browser.{Style.RESET_ALL}")
    
    # Step 6: Create Lakehouse  
    print(f"\n{Fore.CYAN}Step 6: Create Lakehouse{Style.RESET_ALL}\n")
    print(f"{Fore.WHITE}In the workspace:{Style.RESET_ALL}")
    print(f"  1. Click {Fore.YELLOW}New{Style.RESET_ALL} button")
    print(f"  2. Select {Fore.YELLOW}Lakehouse{Style.RESET_ALL}")
    print(f"  3. Name: {Fore.GREEN}ConferenceDataLakehouse{Style.RESET_ALL}")
    print(f"  4. Click {Fore.YELLOW}Create{Style.RESET_ALL}")
    print()
    
    wait_for_user_action("Create the Lakehouse, then press ENTER")
    
    # Step 7: Storage Shortcut
    print(f"\n{Fore.CYAN}Step 7: Create Storage Shortcut{Style.RESET_ALL}\n")
    print(f"{Fore.WHITE}In ConferenceDataLakehouse:{Style.RESET_ALL}")
    print(f"  1. In left panel, click {Fore.YELLOW}Files{Style.RESET_ALL}")
    print(f"  2. Click {Fore.YELLOW}New shortcut{Style.RESET_ALL}")
    print(f"  3. Select {Fore.YELLOW}Azure Data Lake Storage Gen2{Style.RESET_ALL}")
    print(f"  4. Enter connection:")
    print(f"     - URL: {Fore.GREEN}https://westusattendiesstore.dfs.core.windows.net/{Style.RESET_ALL}")
    print(f"     - Auth: {Fore.GREEN}Microsoft Entra ID{Style.RESET_ALL} (your current login)")
    print(f"  5. Click {Fore.YELLOW}Next{Style.RESET_ALL}")
    print(f"  6. Select container: {Fore.GREEN}conference-data{Style.RESET_ALL}")
    print(f"  7. Name: {Fore.GREEN}conference-data{Style.RESET_ALL}")
    print(f"  8. Click {Fore.YELLOW}Create{Style.RESET_ALL}")
    print()
    
    wait_for_user_action("Create the storage shortcut, then press ENTER")
    
    # Final Summary
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}✓ GitOps Deployment Complete!")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.GREEN}Workspace Setup:{Style.RESET_ALL}")
    print(f"  ✓ Workspace: {WORKSPACE_NAME}")
    print(f"  ✓ URL: {workspace_url}")
    print(f"  ✓ Capacity: {CAPACITY_NAME}")
    print(f"  ✓ GitHub: {GITHUB_ORG}/{GITHUB_REPO}")
    print(f"  ✓ Lakehouse: ConferenceDataLakehouse")
    print(f"  ✓ Storage Shortcut: conference-data")
    
    print(f"\n{Fore.CYAN}Next: Run the Pipeline{Style.RESET_ALL}")
    print(f"  1. Open notebook: {Fore.GREEN}Load Conference Data{Style.RESET_ALL}")
    print(f"  2. Click {Fore.YELLOW}Run all{Style.RESET_ALL}")
    print(f"  3. Wait ~2-3 minutes")
    print(f"  4. Verify: Last cell shows success message")
    
    print(f"\n{Fore.CYAN}Then: Create Power BI Report{Style.RESET_ALL}")
    print(f"  Run: {Fore.GREEN}python scripts/create_powerbi_report.py --workspace-id {workspace_id}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}Future Updates:{Style.RESET_ALL}")
    print(f"  • Edit notebooks locally → commit → push")
    print(f"  • In Fabric workspace: Git icon → Update all")
    print(f"  • Or edit in Fabric → Git icon → Commit")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
