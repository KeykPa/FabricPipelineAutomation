#!/usr/bin/env python3
"""
Quick GitOps Deployment - Use Existing Workspace

This script connects an existing workspace to GitHub and guides through the setup.
"""

import sys
import subprocess
import time
import webbrowser

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
        CYAN = GREEN = YELLOW = WHITE = RED = BLUE = ""
    class Style:
        RESET_ALL = BRIGHT = ""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from fix_and_deploy import get_fabric_token


def wait_for_user_action(message):
    """Wait for user to complete a manual action."""
    print(f"\n{Fore.YELLOW}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'='*80}{Style.RESET_ALL}\n")
    input(f"{Fore.CYAN}Press ENTER when done...{Style.RESET_ALL}")


def check_workspace_items(workspace_id):
    """Check if workspace has items."""
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
    WORKSPACE_ID = "7e602ac6-c1c2-4da4-a3d9-e4816740af62"
    WORKSPACE_NAME = "West US Training"
    GITHUB_ORG = "KeykPa"
    GITHUB_REPO = "FabricPipelineAutomation"
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}GitOps Deployment - Connect Existing Workspace to GitHub")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.GREEN}Using existing workspace:{Style.RESET_ALL}")
    print(f"  Name: {WORKSPACE_NAME}")
    print(f"  ID: {WORKSPACE_ID}")
    print()
    
    # Step 1: GitHub Integration
    print(f"{Fore.CYAN}Step 1: GitHub Integration Setup{Style.RESET_ALL}")
    print(f"\n{Fore.WHITE}Opening workspace in browser...{Style.RESET_ALL}")
    
    workspace_url = f"https://app.fabric.microsoft.com/groups/{WORKSPACE_ID}"
    webbrowser.open(workspace_url)
    time.sleep(2)
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}STEP: Connect to GitHub")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}In the Fabric workspace tab that just opened:{Style.RESET_ALL}\n")
    print(f"  1. Click the {Fore.YELLOW}Settings icon (⚙️){Style.RESET_ALL} in the top right")
    print(f"  2. Go to {Fore.YELLOW}Git integration{Style.RESET_ALL} tab")
    print(f"  3. If already connected → {Fore.GREEN}Skip to next step{Style.RESET_ALL}")
    print(f"  4. If not connected:")
    print(f"     a. Click {Fore.YELLOW}Connect{Style.RESET_ALL}")
    print(f"     b. Select {Fore.YELLOW}GitHub{Style.RESET_ALL}")
    print(f"     c. Authorize Fabric (if prompted)")
    print(f"     d. Select:")
    print(f"        - Organization: {Fore.GREEN}{GITHUB_ORG}{Style.RESET_ALL}")
    print(f"        - Repository: {Fore.GREEN}{GITHUB_REPO}{Style.RESET_ALL}")
    print(f"        - Branch: {Fore.GREEN}main{Style.RESET_ALL}")
    print(f"        - Folder: {Fore.GREEN}/{Style.RESET_ALL} (root)")
    print(f"     e. Click {Fore.YELLOW}Connect and sync{Style.RESET_ALL}")
    print(f"     f. Wait for sync (~30 seconds)")
    print()
    
    wait_for_user_action("Complete GitHub connection, then press ENTER")
    
    # Step 2: Verify sync
    print(f"\n{Fore.CYAN}Step 2: Verifying Notebook Sync{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Checking for notebooks...{Style.RESET_ALL}")
    
    time.sleep(3)
    items = check_workspace_items(WORKSPACE_ID)
    
    notebooks = [item for item in items if item.get("type") == "Notebook"]
    lakehouses = [item for item in items if item.get("type") == "Lakehouse"]
    
    if notebooks:
        print(f"{Fore.GREEN}✓ Found {len(notebooks)} notebook(s):{Style.RESET_ALL}")
        for nb in notebooks:
            print(f"  - {nb.get('displayName')}")
    else:
        print(f"{Fore.YELLOW}! No notebooks found yet{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  Wait a bit longer and refresh the workspace.{Style.RESET_ALL}")
    
    if lakehouses:
        print(f"{Fore.GREEN}✓ Found {len(lakehouses)} lakehouse(s):{Style.RESET_ALL}")
        for lh in lakehouses:
            print(f"  - {lh.get('displayName')}")
    
    # Step 3: Create/Verify Lakehouse  
    if not lakehouses:
        print(f"\n{Fore.CYAN}Step 3: Create Lakehouse{Style.RESET_ALL}\n")
        print(f"{Fore.WHITE}In the workspace:{Style.RESET_ALL}")
        print(f"  1. Click {Fore.YELLOW}New{Style.RESET_ALL} button")
        print(f"  2. Select {Fore.YELLOW}Lakehouse{Style.RESET_ALL}")
        print(f"  3. Name: {Fore.GREEN}ConferenceDataLakehouse{Style.RESET_ALL}")
        print(f"  4. Click {Fore.YELLOW}Create{Style.RESET_ALL}")
        print()
        
        wait_for_user_action("Create the Lakehouse, then press ENTER")
    else:
        print(f"\n{Fore.GREEN}✓ Lakehouse already exists{Style.RESET_ALL}")
        lakehouse_name = lakehouses[0].get('displayName')
        print(f"  Using: {lakehouse_name}")
    
    # Step 4: Storage Shortcut
    print(f"\n{Fore.CYAN}Step 4: Create Storage Shortcut{Style.RESET_ALL}\n")
    print(f"{Fore.WHITE}In the Lakehouse:{Style.RESET_ALL}")
    print(f"  1. Open the Lakehouse (click on it in workspace)")
    print(f"  2. In left panel, click {Fore.YELLOW}Files{Style.RESET_ALL}")
    print(f"  3. Click {Fore.YELLOW}New shortcut{Style.RESET_ALL}")
    print(f"  4. Select {Fore.YELLOW}Azure Data Lake Storage Gen2{Style.RESET_ALL}")
    print(f"  5. Connection:")
    print(f"     - URL: {Fore.GREEN}https://westusattendiesstore.dfs.core.windows.net/{Style.RESET_ALL}")
    print(f"     - Auth: {Fore.GREEN}Microsoft Entra ID{Style.RESET_ALL}")
    print(f"  6. Click {Fore.YELLOW}Next{Style.RESET_ALL}")
    print(f"  7. Select: {Fore.GREEN}conference-data{Style.RESET_ALL}")
    print(f"  8. Name: {Fore.GREEN}conference-data{Style.RESET_ALL}")
    print(f"  9. Click {Fore.YELLOW}Create{Style.RESET_ALL}")
    print()
    
    wait_for_user_action("Create storage shortcut, then press ENTER")
    
    # Final Summary
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}✓ GitOps Setup Complete!")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.GREEN}Workspace Configuration:{Style.RESET_ALL}")
    print(f"  ✓ Workspace: {WORKSPACE_NAME}")
    print(f"  ✓ URL: {workspace_url}")
    print(f"  ✓ GitHub: {GITHUB_ORG}/{GITHUB_REPO}")
    if notebooks:
        print(f"  ✓ Notebook synced from GitHub")
    print(f"  ✓ Lakehouse ready")
    print(f"  ✓ Storage shortcut configured")
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}NEXT: Run the Pipeline")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"  1. In workspace, open: {Fore.GREEN}Load Conference Data{Style.RESET_ALL} notebook")
    print(f"  2. Click {Fore.YELLOW}Run all{Style.RESET_ALL}")
    print(f"  3. Wait ~2-3 minutes for execution")
    print(f"  4. Verify: Last cell shows conference data")
    
    print(f"\n{Fore.CYAN}Then Create Power BI Report:{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}python scripts/create_powerbi_report.py --workspace-id {WORKSPACE_ID}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}GitOps Workflow:{Style.RESET_ALL}")
    print(f"  • Edit code locally → commit → push to GitHub")
    print(f"  • In Fabric: Git icon → {Fore.YELLOW}Update all{Style.RESET_ALL}")
    print(f"  • Or edit in Fabric → Git icon → {Fore.YELLOW}Commit{Style.RESET_ALL} back to GitHub")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
