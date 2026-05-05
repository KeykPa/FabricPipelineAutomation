#!/usr/bin/env python3
"""
Multi-Workspace Git Integration Deployment

Reads workspace-config.yaml and deploys multiple Fabric workspaces with Git integration.
Supports single or multi-workspace deployment based on configuration.
"""

import sys
import subprocess
import os
import time
import webbrowser
from pathlib import Path

# Install dependencies
try:
    import yaml
except ImportError:
    print("Installing pyyaml...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyyaml"], check=True)
    import yaml

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
    print("Installing colorama...")
    subprocess.run([sys.executable, "-m", "pip", "install", "colorama"], check=True)
    from colorama import init, Fore, Style
    init(autoreset=True)

# Import from existing scripts
sys.path.insert(0, os.path.dirname(__file__))
from fix_and_deploy import (
    get_fabric_token,
    create_workspace,
    get_capacity_id,
    assign_workspace_to_capacity
)


class WorkspaceDeployer:
    """Handles multi-workspace deployment with Git integration."""
    
    def __init__(self, config_path="config/workspace-config.yaml"):
        """Initialize deployer with configuration."""
        self.config_path = config_path
        self.config = self.load_config()
        self.deployment_results = []
    
    def load_config(self):
        """Load YAML configuration file."""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            print(f"{Fore.RED}✗ Configuration file not found: {self.config_path}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  Please create config/workspace-config.yaml{Style.RESET_ALL}")
            sys.exit(1)
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def get_enabled_workspaces(self):
        """Get list of enabled workspaces from config."""
        workspaces = self.config.get('workspaces', [])
        enabled = [ws for ws in workspaces if ws.get('enabled', True)]
        
        print(f"\n{Fore.CYAN}Configuration Summary:{Style.RESET_ALL}")
        print(f"  Total workspaces defined: {len(workspaces)}")
        print(f"  Enabled for deployment: {len(enabled)}")
        print()
        
        return enabled
    
    def wait_for_user(self, message, workspace_name=""):
        """Wait for user to complete manual action."""
        prefix = f"[{workspace_name}] " if workspace_name else ""
        print(f"\n{Fore.YELLOW}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{prefix}{message}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'='*80}{Style.RESET_ALL}\n")
        input(f"{Fore.CYAN}Press ENTER when done...{Style.RESET_ALL}")
    
    def check_workspace_exists(self, workspace_name):
        """Check if workspace already exists."""
        token = get_fabric_token()
        if not token:
            return None
        
        headers = {"Authorization": f"Bearer {token}"}
        url = "https://api.powerbi.com/v1.0/myorg/groups"
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            workspaces = response.json().get("value", [])
            
            for ws in workspaces:
                if ws.get("name") == workspace_name:
                    return ws.get("id")
            
            return None
        except Exception as e:
            print(f"{Fore.RED}✗ Error checking workspace: {e}{Style.RESET_ALL}")
            return None
    
    def verify_git_sync(self, workspace_id, expected_artifacts):
        """Verify that artifacts synced from Git."""
        token = get_fabric_token()
        if not token:
            return False
        
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            items = response.json().get("value", [])
            
            found_artifacts = []
            for expected in expected_artifacts:
                expected_type = expected.get('type')
                expected_name = expected.get('name')
                
                for item in items:
                    if item.get('type') == expected_type:
                        item_name = item.get('displayName', '')
                        if expected_name.lower() in item_name.lower() or item_name.lower() in expected_name.lower():
                            found_artifacts.append(item_name)
                            break
            
            return found_artifacts
        except Exception as e:
            print(f"{Fore.YELLOW}! Could not verify artifacts: {e}{Style.RESET_ALL}")
            return []
    
    def deploy_workspace(self, ws_config):
        """Deploy a single workspace with Git integration."""
        ws_name = ws_config.get('name')
        ws_desc = ws_config.get('description', '')
        
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}Deploying Workspace: {ws_name}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        if ws_desc:
            print(f"{Fore.WHITE}{ws_desc}{Style.RESET_ALL}\n")
        
        result = {
            'workspace_name': ws_name,
            'status': 'pending',
            'workspace_id': None,
            'git_connected': False,
            'artifacts_synced': [],
            'lakehouse_created': False,
            'shortcut_created': False
        }
        
        # Step 1: Check if workspace exists
        print(f"{Fore.CYAN}Step 1: Checking if workspace exists...{Style.RESET_ALL}")
        workspace_id = self.check_workspace_exists(ws_name)
        
        if workspace_id:
            skip_existing = self.config.get('deployment', {}).get('skip_existing_workspaces', True)
            
            if skip_existing:
                print(f"{Fore.GREEN}✓ Workspace already exists: {workspace_id}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}  Using existing workspace{Style.RESET_ALL}")
                result['workspace_id'] = workspace_id
                result['status'] = 'existing'
            else:
                print(f"{Fore.RED}✗ Workspace already exists and skip_existing_workspaces=false{Style.RESET_ALL}")
                result['status'] = 'failed'
                result['error'] = 'Workspace already exists'
                return result
        else:
            # Create new workspace
            print(f"{Fore.CYAN}Creating workspace: {ws_name}{Style.RESET_ALL}")
            workspace_id = create_workspace(ws_name)
            
            if not workspace_id:
                print(f"{Fore.RED}✗ Failed to create workspace{Style.RESET_ALL}")
                result['status'] = 'failed'
                result['error'] = 'Workspace creation failed'
                return result
            
            result['workspace_id'] = workspace_id
            result['status'] = 'created'
            
            # Wait after creation
            wait_time = self.config.get('deployment', {}).get('workspace_creation_wait', 5)
            if wait_time > 0:
                print(f"{Fore.WHITE}Waiting {wait_time} seconds...{Style.RESET_ALL}")
                time.sleep(wait_time)
        
        # Step 2: Assign to capacity
        print(f"\n{Fore.CYAN}Step 2: Assigning to Capacity{Style.RESET_ALL}")
        capacity_name = self.config.get('fabric', {}).get('capacity_name')
        
        if capacity_name:
            capacity_id = get_capacity_id(capacity_name)
            if capacity_id:
                if assign_workspace_to_capacity(workspace_id, capacity_id):
                    print(f"{Fore.GREEN}✓ Workspace assigned to capacity{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}! Failed to assign capacity (may already be assigned){Style.RESET_ALL}")
        
        # Step 3: Git Integration (Interactive)
        print(f"\n{Fore.CYAN}Step 3: Git Integration{Style.RESET_ALL}")
        
        git_config = ws_config.get('git', {})
        git_provider = git_config.get('provider', 'GitHub')
        git_org = git_config.get('organization')
        git_repo = git_config.get('repository')
        git_branch = git_config.get('branch', 'main')
        git_dir = git_config.get('directory', '/')
        
        workspace_url = f"https://app.fabric.microsoft.com/groups/{workspace_id}"
        
        auto_open = self.config.get('deployment', {}).get('auto_open_browser', True)
        if auto_open:
            print(f"{Fore.WHITE}Opening workspace in browser...{Style.RESET_ALL}")
            webbrowser.open(workspace_url)
            time.sleep(2)
        else:
            print(f"{Fore.CYAN}Workspace URL: {workspace_url}{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}Git Configuration:{Style.RESET_ALL}")
        print(f"  Provider: {Fore.GREEN}{git_provider}{Style.RESET_ALL}")
        print(f"  Organization: {Fore.GREEN}{git_org}{Style.RESET_ALL}")
        print(f"  Repository: {Fore.GREEN}{git_repo}{Style.RESET_ALL}")
        print(f"  Branch: {Fore.GREEN}{git_branch}{Style.RESET_ALL}")
        print(f"  Directory: {Fore.GREEN}{git_dir}{Style.RESET_ALL}")
        print()
        
        print(f"{Fore.WHITE}In the Fabric workspace:{Style.RESET_ALL}")
        print(f"  1. Click {Fore.YELLOW}Settings (⚙️){Style.RESET_ALL}")
        print(f"  2. Go to {Fore.YELLOW}Git integration{Style.RESET_ALL} tab")
        print(f"  3. Click {Fore.YELLOW}Connect{Style.RESET_ALL}")
        print(f"  4. Select {Fore.YELLOW}{git_provider}{Style.RESET_ALL}")
        print(f"  5. Authorize (if prompted)")
        print(f"  6. Select:")
        print(f"     - Organization: {Fore.GREEN}{git_org}{Style.RESET_ALL}")
        print(f"     - Repository: {Fore.GREEN}{git_repo}{Style.RESET_ALL}")
        print(f"     - Branch: {Fore.GREEN}{git_branch}{Style.RESET_ALL}")
        print(f"     - Folder: {Fore.GREEN}{git_dir}{Style.RESET_ALL}")
        print(f"  7. Click {Fore.YELLOW}Connect and sync{Style.RESET_ALL}")
        print(f"  8. Wait for sync to complete")
        print()
        
        self.wait_for_user("Complete Git connection", ws_name)
        result['git_connected'] = True
        
        # Step 4: Verify sync
        print(f"\n{Fore.CYAN}Step 4: Verifying Artifact Sync{Style.RESET_ALL}")
        
        expected_artifacts = ws_config.get('expected_artifacts', [])
        sync_wait = self.config.get('deployment', {}).get('git_sync_wait', 30)
        
        print(f"{Fore.WHITE}Waiting {sync_wait} seconds for sync...{Style.RESET_ALL}")
        time.sleep(sync_wait)
        
        found_artifacts = self.verify_git_sync(workspace_id, expected_artifacts)
        
        if found_artifacts:
            print(f"{Fore.GREEN}✓ Found {len(found_artifacts)} artifact(s):{Style.RESET_ALL}")
            for artifact in found_artifacts:
                print(f"  - {artifact}")
            result['artifacts_synced'] = found_artifacts
        else:
            print(f"{Fore.YELLOW}! No artifacts found yet{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  Check the workspace - sync may still be in progress{Style.RESET_ALL}")
        
        # Step 5: Lakehouse and Shortcut (Manual for now)
        lakehouse_config = ws_config.get('lakehouse', {})
        if lakehouse_config:
            print(f"\n{Fore.CYAN}Step 5: Lakehouse and Storage Shortcut{Style.RESET_ALL}")
            
            lh_name = lakehouse_config.get('name', 'Lakehouse')
            shortcut_config = lakehouse_config.get('storage_shortcut', {})
            
            print(f"\n{Fore.WHITE}Create Lakehouse:{Style.RESET_ALL}")
            print(f"  1. Click {Fore.YELLOW}New{Style.RESET_ALL} → {Fore.YELLOW}Lakehouse{Style.RESET_ALL}")
            print(f"  2. Name: {Fore.GREEN}{lh_name}{Style.RESET_ALL}")
            print(f"  3. Click {Fore.YELLOW}Create{Style.RESET_ALL}")
            print()
            
            if shortcut_config:
                sc_name = shortcut_config.get('name', 'data')
                sc_url = shortcut_config.get('url')
                sc_container = shortcut_config.get('container')
                
                print(f"{Fore.WHITE}Create Storage Shortcut:{Style.RESET_ALL}")
                print(f"  1. Open {Fore.GREEN}{lh_name}{Style.RESET_ALL}")
                print(f"  2. Click {Fore.YELLOW}Files{Style.RESET_ALL} → {Fore.YELLOW}New shortcut{Style.RESET_ALL}")
                print(f"  3. Select {Fore.YELLOW}Azure Data Lake Storage Gen2{Style.RESET_ALL}")
                print(f"  4. URL: {Fore.GREEN}{sc_url}{Style.RESET_ALL}")
                print(f"  5. Auth: {Fore.GREEN}Microsoft Entra ID{Style.RESET_ALL}")
                print(f"  6. Container: {Fore.GREEN}{sc_container}{Style.RESET_ALL}")
                print(f"  7. Name: {Fore.GREEN}{sc_name}{Style.RESET_ALL}")
                print(f"  8. Click {Fore.YELLOW}Create{Style.RESET_ALL}")
                print()
            
            self.wait_for_user("Create Lakehouse and shortcut", ws_name)
            result['lakehouse_created'] = True
            result['shortcut_created'] = True
        
        result['status'] = 'success'
        return result
    
    def deploy_all(self):
        """Deploy all enabled workspaces."""
        enabled_workspaces = self.get_enabled_workspaces()
        
        if not enabled_workspaces:
            print(f"{Fore.YELLOW}No workspaces enabled for deployment{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Edit config/workspace-config.yaml and set enabled: true{Style.RESET_ALL}")
            return
        
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}Multi-Workspace Git Integration Deployment")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        for idx, ws_config in enumerate(enabled_workspaces, 1):
            ws_name = ws_config.get('name')
            print(f"\n{Fore.CYAN}[{idx}/{len(enabled_workspaces)}] Starting: {ws_name}{Style.RESET_ALL}")
            
            result = self.deploy_workspace(ws_config)
            self.deployment_results.append(result)
            
            print(f"\n{Fore.GREEN}✓ Workspace {idx}/{len(enabled_workspaces)} completed{Style.RESET_ALL}")
            
            if idx < len(enabled_workspaces):
                print(f"\n{Fore.CYAN}Moving to next workspace...{Style.RESET_ALL}")
                time.sleep(2)
        
        # Final Summary
        self.print_summary()
    
    def print_summary(self):
        """Print deployment summary."""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}Deployment Summary")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        for result in self.deployment_results:
            ws_name = result['workspace_name']
            status = result['status']
            
            if status == 'success':
                status_icon = f"{Fore.GREEN}✓{Style.RESET_ALL}"
            elif status in ['created', 'existing']:
                status_icon = f"{Fore.GREEN}✓{Style.RESET_ALL}"
            else:
                status_icon = f"{Fore.RED}✗{Style.RESET_ALL}"
            
            print(f"{status_icon} {Fore.WHITE}{ws_name}{Style.RESET_ALL}")
            print(f"  ID: {result.get('workspace_id', 'N/A')}")
            print(f"  Status: {status}")
            
            if result.get('git_connected'):
                print(f"  Git: {Fore.GREEN}Connected{Style.RESET_ALL}")
            
            if result.get('artifacts_synced'):
                print(f"  Artifacts: {', '.join(result['artifacts_synced'])}")
            
            if result.get('lakehouse_created'):
                print(f"  Lakehouse: {Fore.GREEN}Created{Style.RESET_ALL}")
            
            print()
        
        # Next steps
        print(f"{Fore.CYAN}Next Steps:{Style.RESET_ALL}")
        print(f"  1. Run notebooks in each workspace")
        print(f"  2. Create Power BI reports using:")
        print(f"     {Fore.GREEN}python scripts/create_powerbi_report.py --workspace-id <id>{Style.RESET_ALL}")
        print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Deploy Fabric workspaces with Git integration from config file"
    )
    parser.add_argument(
        "--config",
        default="config/workspace-config.yaml",
        help="Path to workspace configuration file (default: config/workspace-config.yaml)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List configured workspaces and exit"
    )
    
    args = parser.parse_args()
    
    deployer = WorkspaceDeployer(args.config)
    
    if args.list:
        workspaces = deployer.get_enabled_workspaces()
        print(f"\n{Fore.CYAN}Enabled Workspaces:{Style.RESET_ALL}\n")
        for ws in workspaces:
            print(f"  • {ws.get('name')}")
            print(f"    Repo: {ws.get('git', {}).get('organization')}/{ws.get('git', {}).get('repository')}")
            print()
        return 0
    
    deployer.deploy_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
