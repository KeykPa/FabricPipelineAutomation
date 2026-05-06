#!/usr/bin/env python3
"""
Multi-Workspace Deployment Script for Microsoft Fabric

This script automates the deployment of multiple Fabric workspaces with individual data,
Git integration, and Power BI reports.

Features:
- Creates multiple workspaces from config file
- Uploads workspace-specific CSV files to OneLake
- Configures Git integration (requires manual OAuth)
- Verifies notebooks, semantic models, and reports sync from Git
- Each workspace gets its own isolated data

Usage:
    python scripts/deploy_multi_workspace.py
    python scripts/deploy_multi_workspace.py --workspace "West US Training"
    python scripts/deploy_multi_workspace.py --dry-run
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional

import requests
import yaml
from azure.identity import DefaultAzureCredential

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FabricMultiWorkspaceDeployer:
    """Deploys multiple Fabric workspaces with individual data and Git integration."""
    
    def __init__(self, config_path: str = "config/workspace-config.yaml"):
        """Initialize the deployer with configuration."""
        self.config_path = config_path
        self.config = self._load_config()
        self.credential = DefaultAzureCredential()
        self.fabric_token = None
        self.capacity_id = None
        
    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        logger.info(f"Loading configuration from {self.config_path}")
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded {len(config.get('workspaces', []))} workspace definitions")
        return config
    
    def get_fabric_token(self) -> str:
        """Get Azure AD token for Fabric API."""
        if self.fabric_token:
            return self.fabric_token
            
        try:
            logger.info("Getting Fabric API token via Azure CLI")
            result = subprocess.run(
                "az account get-access-token --resource https://api.fabric.microsoft.com",
                capture_output=True,
                text=True,
                check=True,
                shell=True
            )
            token_data = json.loads(result.stdout)
            self.fabric_token = token_data["accessToken"]
            logger.info("✓ Fabric API token obtained")
            return self.fabric_token
        except Exception as e:
            logger.error(f"Failed to get Fabric API token: {e}")
            raise
    
    def get_capacity_id(self) -> str:
        """Get or discover Fabric capacity ID."""
        if self.capacity_id:
            return self.capacity_id
            
        # Check if capacity_id is in config
        if self.config.get('fabric', {}).get('capacity_id'):
            self.capacity_id = self.config['fabric']['capacity_id']
            logger.info(f"✓ Using capacity ID from config: {self.capacity_id}")
            return self.capacity_id
        
        # Discover capacity by name
        capacity_name = self.config.get('fabric', {}).get('capacity_name')
        if not capacity_name:
            raise ValueError("No capacity_name or capacity_id in configuration")
        
        logger.info(f"Discovering capacity ID for '{capacity_name}'")
        token = self.get_fabric_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            "https://api.fabric.microsoft.com/v1/capacities",
            headers=headers
        )
        response.raise_for_status()
        
        capacities = response.json().get('value', [])
        for capacity in capacities:
            if capacity.get('displayName') == capacity_name:
                self.capacity_id = capacity['id']
                logger.info(f"✓ Found capacity ID: {self.capacity_id}")
                return self.capacity_id
        
        raise ValueError(f"Capacity '{capacity_name}' not found")
    
    def create_workspace(self, workspace_config: dict) -> Optional[dict]:
        """Create a Fabric workspace."""
        workspace_name = workspace_config['name']
        logger.info(f"\n{'='*60}")
        logger.info(f"Creating workspace: {workspace_name}")
        logger.info(f"{'='*60}")
        
        token = self.get_fabric_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Check if workspace exists
        response = requests.get(
            "https://api.fabric.microsoft.com/v1/workspaces",
            headers=headers
        )
        response.raise_for_status()
        
        workspaces = response.json().get('value', [])
        for ws in workspaces:
            if ws.get('displayName') == workspace_name:
                if self.config.get('deployment', {}).get('skip_existing_workspaces', True):
                    logger.info(f"✓ Workspace '{workspace_name}' already exists (ID: {ws['id']})")
                    return ws
                else:
                    raise ValueError(f"Workspace '{workspace_name}' already exists")
        
        # Create new workspace
        logger.info(f"Creating new workspace '{workspace_name}'")
        payload = {
            "displayName": workspace_name,
            "description": workspace_config.get('description', '')
        }
        
        response = requests.post(
            "https://api.fabric.microsoft.com/v1/workspaces",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        workspace = response.json()
        logger.info(f"✓ Workspace created: {workspace['id']}")
        
        # Wait for workspace to be ready
        wait_time = self.config.get('deployment', {}).get('workspace_creation_wait', 5)
        logger.info(f"Waiting {wait_time} seconds for workspace to be ready...")
        time.sleep(wait_time)
        
        return workspace
    
    def assign_to_capacity(self, workspace_id: str) -> None:
        """Assign workspace to Fabric capacity."""
        capacity_id = self.get_capacity_id()
        logger.info(f"Assigning workspace to capacity {capacity_id}")
        
        token = self.get_fabric_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {"capacityId": capacity_id}
        
        response = requests.post(
            f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/assignToCapacity",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        logger.info("✓ Workspace assigned to capacity")
    
    def configure_git_integration(self, workspace_id: str, workspace_config: dict) -> None:
        """Configure Git integration for workspace (requires manual OAuth)."""
        logger.info("\n--- Git Integration Configuration ---")
        
        git_config = workspace_config.get('git', {})
        organization = git_config.get('organization')
        repository = git_config.get('repository')
        branch = git_config.get('branch', 'main')
        directory = git_config.get('directory', '/')
        
        logger.info(f"Repository: {organization}/{repository}")
        logger.info(f"Branch: {branch}")
        logger.info(f"Directory: {directory}")
        
        # Open browser for manual Git connection
        if self.config.get('deployment', {}).get('auto_open_browser', True):
            git_url = f"https://app.fabric.microsoft.com/groups/{workspace_id}/settings/git-integration"
            logger.info(f"\n{'!'*60}")
            logger.info("MANUAL STEP REQUIRED: Git OAuth Connection")
            logger.info(f"{'!'*60}")
            logger.info(f"Opening browser: {git_url}")
            logger.info("")
            logger.info("Steps:")
            logger.info(f"  1. Click 'Connect' or 'Git integration'")
            logger.info(f"  2. Select provider: {git_config.get('provider', 'GitHub')}")
            logger.info(f"  3. Authorize Fabric to access your repository")
            logger.info(f"  4. Select: {organization}/{repository}")
            logger.info(f"  5. Branch: {branch}")
            logger.info(f"  6. Directory: {directory}")
            logger.info(f"  7. Click 'Connect and sync'")
            logger.info("")
            
            webbrowser.open(git_url)
            
            input("Press Enter after completing Git setup in the browser...")
        
        # Wait for Git sync
        wait_time = self.config.get('deployment', {}).get('git_sync_wait', 45)
        logger.info(f"Waiting {wait_time} seconds for Git sync to complete...")
        time.sleep(wait_time)
        
        logger.info("✓ Git integration configured")
    
    def create_lakehouse(self, workspace_id: str, workspace_config: dict) -> Optional[dict]:
        """Create a lakehouse in the workspace."""
        lakehouse_name = workspace_config.get('lakehouse', {}).get('name', 'ConferenceDataLakehouse')
        logger.info(f"\n--- Creating Lakehouse: {lakehouse_name} ---")
        
        token = self.get_fabric_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Check if lakehouse already exists
        response = requests.get(
            f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items",
            headers=headers
        )
        response.raise_for_status()
        
        items = response.json().get('value', [])
        for item in items:
            if item.get('type') == 'Lakehouse' and item.get('displayName') == lakehouse_name:
                logger.info(f"✓ Lakehouse '{lakehouse_name}' already exists (ID: {item['id']})")
                return item
        
        # Create lakehouse
        payload = {
            "displayName": lakehouse_name,
            "type": "Lakehouse"
        }
        
        response = requests.post(
            f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        lakehouse = response.json()
        logger.info(f"✓ Lakehouse created: {lakehouse['id']}")
        return lakehouse
    
    def upload_data_to_onelake(self, workspace_id: str, lakehouse_id: str, workspace_config: dict) -> None:
        """Upload workspace-specific CSV file to OneLake."""
        data_file = workspace_config.get('data_file')
        if not data_file:
            logger.warning("No data_file specified in workspace config, skipping upload")
            return
        
        logger.info(f"\n--- Uploading Data: {data_file} ---")
        
        # Get OneLake token
        result = subprocess.run(
            "az account get-access-token --resource https://storage.azure.com",
            capture_output=True,
            text=True,
            check=True,
            shell=True
        )
        token_data = json.loads(result.stdout)
        onelake_token = token_data["accessToken"]
        
        # Read CSV file
        csv_path = f"sample-data/{data_file}"
        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found: {csv_path}")
            return
        
        with open(csv_path, 'rb') as f:
            file_data = f.read()
        
        # OneLake path
        lakehouse_name = workspace_config.get('lakehouse', {}).get('name', 'ConferenceDataLakehouse')
        onelake_path = f"{workspace_id}/{lakehouse_name}.Lakehouse/Files/conference-data/conference_attendance.csv"
        
        headers = {
            "Authorization": f"Bearer {onelake_token}",
            "x-ms-version": "2023-11-03"
        }
        
        # Step 1: Create file (PUT with resource=file)
        url = f"https://onelake.dfs.fabric.microsoft.com/{onelake_path}?resource=file"
        logger.info(f"Creating file in OneLake...")
        response = requests.put(url, headers=headers)
        response.raise_for_status()
        
        # Step 2: Upload data (PATCH with action=append)
        url = f"https://onelake.dfs.fabric.microsoft.com/{onelake_path}?action=append&position=0"
        headers["Content-Type"] = "application/octet-stream"
        logger.info(f"Uploading {len(file_data)} bytes...")
        response = requests.patch(url, headers=headers, data=file_data)
        response.raise_for_status()
        
        # Step 3: Flush (PATCH with action=flush)
        url = f"https://onelake.dfs.fabric.microsoft.com/{onelake_path}?action=flush&position={len(file_data)}"
        logger.info(f"Finalizing upload...")
        response = requests.patch(url, headers=headers)
        response.raise_for_status()
        
        logger.info(f"✓ Uploaded {data_file} to OneLake (Files/conference-data/)")
    
    def verify_artifacts(self, workspace_id: str, workspace_config: dict) -> Dict[str, bool]:
        """Verify expected artifacts synced from Git."""
        logger.info("\n--- Verifying Artifacts ---")
        
        token = self.get_fabric_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items",
            headers=headers
        )
        response.raise_for_status()
        
        items = response.json().get('value', [])
        expected_artifacts = workspace_config.get('expected_artifacts', [])
        
        verification_results = {}
        
        for expected in expected_artifacts:
            artifact_type = expected['type']
            artifact_name = expected['name']
            
            found = any(
                item.get('type') == artifact_type and item.get('displayName') == artifact_name
                for item in items
            )
            
            verification_results[f"{artifact_type}:{artifact_name}"] = found
            
            if found:
                logger.info(f"✓ {artifact_type} '{artifact_name}' found")
            else:
                logger.warning(f"✗ {artifact_type} '{artifact_name}' NOT found")
        
        return verification_results
    
    def deploy_workspace(self, workspace_config: dict, dry_run: bool = False) -> Dict:
        """Deploy a single workspace with all components."""
        workspace_name = workspace_config['name']
        
        if not workspace_config.get('enabled', False):
            logger.info(f"Skipping disabled workspace: {workspace_name}")
            return {'skipped': True}
        
        if dry_run:
            logger.info(f"[DRY RUN] Would deploy workspace: {workspace_name}")
            return {'dry_run': True}
        
        results = {
            'workspace_name': workspace_name,
            'success': False,
            'steps': {}
        }
        
        try:
            # Step 1: Create workspace
            workspace = self.create_workspace(workspace_config)
            results['workspace_id'] = workspace['id']
            results['steps']['create_workspace'] = True
            
            # Step 2: Assign to capacity
            self.assign_to_capacity(workspace['id'])
            results['steps']['assign_capacity'] = True
            
            # Step 3: Configure Git (manual OAuth required)
            self.configure_git_integration(workspace['id'], workspace_config)
            results['steps']['git_integration'] = True
            
            # Step 4: Create lakehouse
            if self.config.get('deployment', {}).get('auto_create_lakehouse', True):
                lakehouse = self.create_lakehouse(workspace['id'], workspace_config)
                results['lakehouse_id'] = lakehouse['id'] if lakehouse else None
                results['steps']['create_lakehouse'] = True
            
            # Step 5: Upload data
            if self.config.get('deployment', {}).get('auto_upload_data', True) and results.get('lakehouse_id'):
                self.upload_data_to_onelake(workspace['id'], results['lakehouse_id'], workspace_config)
                results['steps']['upload_data'] = True
            
            # Step 6: Verify artifacts
            verification = self.verify_artifacts(workspace['id'], workspace_config)
            results['verification'] = verification
            results['steps']['verify_artifacts'] = True
            
            results['success'] = True
            logger.info(f"\n{'='*60}")
            logger.info(f"✓ Workspace '{workspace_name}' deployed successfully!")
            logger.info(f"{'='*60}")
            logger.info(f"Workspace URL: https://app.fabric.microsoft.com/groups/{workspace['id']}")
            
        except Exception as e:
            logger.error(f"✗ Failed to deploy workspace '{workspace_name}': {e}")
            results['error'] = str(e)
        
        return results
    
    def deploy_all_workspaces(self, specific_workspace: Optional[str] = None, dry_run: bool = False) -> List[Dict]:
        """Deploy all enabled workspaces."""
        workspaces = self.config.get('workspaces', [])
        
        if specific_workspace:
            workspaces = [ws for ws in workspaces if ws['name'] == specific_workspace]
            if not workspaces:
                logger.error(f"Workspace '{specific_workspace}' not found in configuration")
                return []
        
        enabled_workspaces = [ws for ws in workspaces if ws.get('enabled', False)]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Multi-Workspace Deployment")
        logger.info(f"{'='*60}")
        logger.info(f"Total workspaces in config: {len(workspaces)}")
        logger.info(f"Enabled workspaces: {len(enabled_workspaces)}")
        logger.info(f"{'='*60}\n")
        
        results = []
        for ws_config in enabled_workspaces:
            result = self.deploy_workspace(ws_config, dry_run)
            results.append(result)
        
        # Summary
        self.print_summary(results)
        
        return results
    
    def print_summary(self, results: List[Dict]) -> None:
        """Print deployment summary."""
        logger.info(f"\n{'='*60}")
        logger.info("DEPLOYMENT SUMMARY")
        logger.info(f"{'='*60}")
        
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success') and not r.get('skipped')]
        
        logger.info(f"Total: {len(results)}")
        logger.info(f"Successful: {len(successful)}")
        logger.info(f"Failed: {len(failed)}")
        
        if successful:
            logger.info(f"\n✓ Successfully deployed:")
            for r in successful:
                logger.info(f"  - {r['workspace_name']} (ID: {r.get('workspace_id')})")
        
        if failed:
            logger.warning(f"\n✗ Failed deployments:")
            for r in failed:
                logger.warning(f"  - {r['workspace_name']}: {r.get('error')}")
        
        logger.info(f"\n{'='*60}")
        logger.info("NEXT STEPS")
        logger.info(f"{'='*60}")
        logger.info("1. Open each workspace and run the notebook 'Load Conference Data'")
        logger.info("2. Verify Delta tables created: conference_attendance")
        logger.info("3. Open reports to verify data shows correctly")
        logger.info("4. Each report should show ONLY that workspace's data")
        logger.info(f"{'='*60}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Deploy multiple Fabric workspaces with individual data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy all enabled workspaces
  python scripts/deploy_multi_workspace.py
  
  # Deploy specific workspace
  python scripts/deploy_multi_workspace.py --workspace "West US Training"
  
  # Dry run (show what would be deployed)
  python scripts/deploy_multi_workspace.py --dry-run
  
  # Custom config file
  python scripts/deploy_multi_workspace.py --config my-config.yaml
"""
    )
    
    parser.add_argument(
        '--config',
        default='config/workspace-config.yaml',
        help='Path to configuration file (default: config/workspace-config.yaml)'
    )
    parser.add_argument(
        '--workspace',
        help='Deploy specific workspace only'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deployed without making changes'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List configured workspaces and exit'
    )
    
    args = parser.parse_args()
    
    try:
        deployer = FabricMultiWorkspaceDeployer(args.config)
        
        if args.list:
            print(f"\nConfigured Workspaces:")
            print(f"{'='*60}")
            for ws in deployer.config.get('workspaces', []):
                status = "✓ ENABLED" if ws.get('enabled') else "✗ DISABLED"
                data_file = ws.get('data_file', 'N/A')
                print(f"{ws['name']:30} {status:12} Data: {data_file}")
            print(f"{'='*60}\n")
            return 0
        
        results = deployer.deploy_all_workspaces(
            specific_workspace=args.workspace,
            dry_run=args.dry_run
        )
        
        # Exit with error code if any deployments failed
        failed = [r for r in results if not r.get('success') and not r.get('skipped')]
        return 1 if failed else 0
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
