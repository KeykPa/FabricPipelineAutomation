#!/usr/bin/env python3
"""
Complete Automated Deployment with Semantic Model Parameterization

This script performs end-to-end deployment:
1. Cleanup existing workspaces (optional)
2. Create workspaces and assign to capacity
3. Configure Git integration (brings parameterized semantic models)
4. Upload data to OneLake
5. Execute notebooks (load data to Delta tables)
6. Update semantic model parameters (workspace-specific SQL endpoints)
7. Refresh datasets

Fully automated except Git OAuth (3 manual browser steps)
"""

import os
import sys
import json
import time
import yaml
import logging
import subprocess
import requests
import webbrowser
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CompleteFabricDeployer:
    def __init__(self, config_file='config/workspace-config.yaml', cleanup_first=False):
        self.config_file = config_file
        self.cleanup_first = cleanup_first
        self.config = None
        self.fabric_token = None
        self.storage_token = None
        self.powerbi_token = None
        
        # Load configuration
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
            
        self.enabled_workspaces = [w for w in self.config['workspaces'] if w.get('enabled', True)]
        
    def get_fabric_token(self):
        """Get Fabric API token"""
        if not self.fabric_token:
            result = subprocess.run(
                ['az', 'account', 'get-access-token', '--resource', 'https://api.fabric.microsoft.com'],
                capture_output=True,
                text=True,
                shell=True
            )
            if result.returncode != 0:
                raise Exception(f"Failed to get Fabric token: {result.stderr}")
            
            token_data = json.loads(result.stdout)
            self.fabric_token = token_data['accessToken']
        return self.fabric_token
        
    def get_storage_token(self):
        """Get Storage API token"""
        if not self.storage_token:
            result = subprocess.run(
                ['az', 'account', 'get-access-token', '--resource', 'https://storage.azure.com'],
                capture_output=True,
                text=True,
                shell=True
            )
            if result.returncode != 0:
                raise Exception(f"Failed to get Storage token: {result.stderr}")
            
            token_data = json.loads(result.stdout)
            self.storage_token = token_data['accessToken']
        return self.storage_token
        
    def get_powerbi_token(self):
        """Get Power BI API token"""
        if not self.powerbi_token:
            result = subprocess.run(
                ['az', 'account', 'get-access-token', '--resource', 'https://analysis.windows.net/powerbi/api'],
                capture_output=True,
                text=True,
                shell=True
            )
            if result.returncode != 0:
                raise Exception(f"Failed to get Power BI token: {result.stderr}")
            
            token_data = json.loads(result.stdout)
            self.powerbi_token = token_data['accessToken']
        return self.powerbi_token
        
    def cleanup_workspaces(self):
        """Delete existing workspaces"""
        logger.info("\n" + "="*60)
        logger.info("CLEANUP: Deleting existing workspaces")
        logger.info("="*60)
        
        token = self.get_fabric_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Get all workspaces to find by name
        list_url = "https://api.fabric.microsoft.com/v1/workspaces"
        list_response = requests.get(list_url, headers=headers)
        
        if list_response.status_code != 200:
            logger.error(f"Failed to list workspaces: {list_response.status_code}")
            return
            
        all_workspaces = list_response.json().get('value', [])
        workspace_map = {ws['displayName']: ws['id'] for ws in all_workspaces}
        
        for workspace in self.enabled_workspaces:
            workspace_name = workspace['name']
            
            # Try to get ID from config or lookup
            workspace_id = workspace.get('id') or workspace_map.get(workspace_name)
            
            if workspace_id:
                logger.info(f"\nDeleting workspace: {workspace_name} ({workspace_id})")
                
                url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}"
                response = requests.delete(url, headers=headers)
                
                if response.status_code in [200, 204]:
                    logger.info(f"✓ Deleted {workspace_name}")
                    # Clear ID from config
                    workspace['id'] = None
                elif response.status_code == 404:
                    logger.info(f"⊘ Workspace {workspace_name} already deleted")
                else:
                    logger.warning(f"Failed to delete {workspace_name}: {response.status_code}")
            else:
                logger.info(f"⊘ Workspace {workspace_name} not found (already deleted)")
                    
            time.sleep(2)
                
        logger.info("\n✓ Cleanup complete\n")
        
    def create_workspace(self, workspace_name, capacity_id):
        """Create a Fabric workspace (or get existing)"""
        logger.info(f"Creating workspace: {workspace_name}")
        
        token = self.get_fabric_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "displayName": workspace_name,
            "description": f"Automated training workspace for {workspace_name}",
            "capacityId": capacity_id
        }
        
        url = "https://api.fabric.microsoft.com/v1/workspaces"
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            workspace_data = response.json()
            workspace_id = workspace_data['id']
            logger.info(f"✓ Workspace created: {workspace_id}")
            return workspace_id
        elif response.status_code == 409:
            # Workspace already exists - look it up
            logger.info("Workspace already exists - looking up ID...")
            
            list_response = requests.get(url, headers=headers)
            if list_response.status_code == 200:
                all_workspaces = list_response.json().get('value', [])
                workspace = next((ws for ws in all_workspaces if ws['displayName'] == workspace_name), None)
                
                if workspace:
                    workspace_id = workspace['id']
                    logger.info(f"✓ Found existing workspace: {workspace_id}")
                    return workspace_id
                    
            raise Exception(f"Workspace exists but could not be found")
        else:
            raise Exception(f"Failed to create workspace: {response.status_code} - {response.text}")
            
    def configure_git_integration(self, workspace_id, workspace_name, git_config):
        """Configure Git integration for workspace"""
        logger.info(f"\nConfiguring Git integration for: {workspace_name}")
        
        token = self.get_fabric_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "gitProviderDetails": {
                "ownerName": git_config['organization'],
                "organizationName": git_config['organization'],
                "projectName": git_config['repository'],
                "gitProviderType": "GitHub",
                "repositoryName": git_config['repository'],
                "branchName": git_config['branch'],
                "directoryName": git_config.get('directory', '/')
            }
        }
        
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/git/connect"
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            logger.info("✓ Git connection initiated")
            
            # Open browser for OAuth
            logger.info("\n" + "!"*60)
            logger.info("MANUAL ACTION REQUIRED")
            logger.info("!"*60)
            logger.info("A browser window will open for Git authentication.")
            logger.info("Please complete the OAuth flow and return here.")
            logger.info("!"*60 + "\n")
            
            input("Press ENTER when ready to open browser...")
            
            # Open Fabric workspace in browser
            workspace_url = f"https://app.fabric.microsoft.com/groups/{workspace_id}/list"
            webbrowser.open(workspace_url)
            
            input("\nAfter completing OAuth in browser, press ENTER to continue...")
            
            # Wait for Git sync to complete
            logger.info("Waiting 30 seconds for Git sync to complete...")
            time.sleep(30)
            
            # Trigger initial sync
            logger.info("Triggering Git sync...")
            sync_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/git/updateFromGit"
            sync_response = requests.post(sync_url, headers=headers, json={})
            
            if sync_response.status_code in [200, 202]:
                logger.info("✓ Git sync triggered")
                logger.info("Waiting 60 seconds for sync to complete...")
                time.sleep(60)
            else:
                logger.warning(f"Git sync returned: {sync_response.status_code}")
                
            logger.info("✓ Git integration configured")
            
        else:
            logger.error(f"Failed to connect Git: {response.status_code}")
            logger.error(f"Response: {response.text}")
            raise Exception(f"Git connection failed: {response.text}")
            
    def create_lakehouse(self, workspace_id, lakehouse_name):
        """Create lakehouse in workspace"""
        logger.info(f"Creating lakehouse: {lakehouse_name}")
        
        token = self.get_fabric_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "displayName": lakehouse_name,
            "description": "Automated lakehouse for conference data"
        }
        
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses"
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201, 202]:
            lakehouse_data = response.json()
            lakehouse_id = lakehouse_data['id']
            logger.info(f"✓ Lakehouse created: {lakehouse_id}")
            
            # Wait for lakehouse to be ready
            logger.info("Waiting 20 seconds for lakehouse initialization...")
            time.sleep(20)
            
            return lakehouse_id
        else:
            raise Exception(f"Failed to create lakehouse: {response.status_code} - {response.text}")
            
    def get_lakehouse_info(self, workspace_id, lakehouse_name):
        """Get lakehouse ID and SQL endpoint ID"""
        logger.info("Getting lakehouse information...")
        
        token = self.get_fabric_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Get lakehouse ID
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/lakehouses"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        lakehouses = response.json().get('value', [])
        lakehouse = next((lh for lh in lakehouses if lh['displayName'] == lakehouse_name), None)
        
        if not lakehouse:
            raise Exception(f"Lakehouse {lakehouse_name} not found")
            
        lakehouse_id = lakehouse['id']
        
        # Get SQL endpoint ID
        sql_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/sqlEndpoints"
        sql_response = requests.get(sql_url, headers=headers)
        sql_response.raise_for_status()
        
        sql_endpoints = sql_response.json().get('value', [])
        sql_endpoint = next((ep for ep in sql_endpoints if lakehouse_name in ep['displayName']), None)
        
        sql_endpoint_id = sql_endpoint['id'] if sql_endpoint else None
        
        logger.info(f"✓ Lakehouse ID: {lakehouse_id}")
        logger.info(f"✓ SQL Endpoint ID: {sql_endpoint_id}")
        
        return lakehouse_id, sql_endpoint_id
        
    def upload_data_to_onelake(self, workspace_id, lakehouse_id, data_file):
        """Upload CSV data to OneLake using DFS API"""
        logger.info(f"Uploading data: {data_file}")
        
        token = self.get_storage_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'x-ms-version': '2023-01-03'
        }
        
        # Read file content
        file_path = Path(data_file)
        with open(file_path, 'rb') as f:
            content = f.read()
            
        file_name = file_path.name
        onelake_path = f"{lakehouse_id}/Files/conference-data/{file_name}"
        
        # Step 1: Create directory
        dir_url = f"https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{lakehouse_id}/Files/conference-data"
        dir_response = requests.put(f"{dir_url}?resource=directory", headers=headers)
        
        if dir_response.status_code in [201, 409]:  # 409 = already exists
            logger.info("✓ Directory ready")
        else:
            logger.warning(f"Directory creation: {dir_response.status_code}")
            
        # Step 2: Create file
        file_url = f"https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{onelake_path}"
        create_response = requests.put(f"{file_url}?resource=file", headers=headers)
        
        if create_response.status_code not in [201, 409]:
            raise Exception(f"Failed to create file: {create_response.status_code}")
            
        logger.info("✓ File created")
        
        # Step 3: Append data
        append_headers = headers.copy()
        append_headers['Content-Type'] = 'application/octet-stream'
        append_headers['Content-Length'] = str(len(content))
        
        append_response = requests.patch(
            f"{file_url}?action=append&position=0",
            headers=append_headers,
            data=content
        )
        
        if append_response.status_code not in [200, 202]:
            raise Exception(f"Failed to append data: {append_response.status_code}")
            
        logger.info(f"✓ Data appended ({len(content)} bytes)")
        
        # Step 4: Flush
        flush_headers = headers.copy()
        flush_headers['Content-Length'] = '0'
        
        flush_response = requests.patch(
            f"{file_url}?action=flush&position={len(content)}",
            headers=flush_headers
        )
        
        if flush_response.status_code not in [200, 201]:
            raise Exception(f"Failed to flush: {flush_response.status_code}")
            
        logger.info("✓ Data upload complete")
        
    def run_notebook(self, workspace_id, notebook_name):
        """Trigger notebook execution"""
        logger.info(f"Executing notebook: {notebook_name}")
        
        token = self.get_fabric_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Get notebook ID
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        notebooks = response.json().get('value', [])
        notebook = next((nb for nb in notebooks if nb['displayName'] == notebook_name), None)
        
        if not notebook:
            raise Exception(f"Notebook {notebook_name} not found")
            
        notebook_id = notebook['id']
        
        # Trigger execution
        run_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/jobs/instances?jobType=RunNotebook"
        run_response = requests.post(run_url, headers=headers, json={})
        
        if run_response.status_code in [200, 202]:
            logger.info("✓ Notebook execution triggered")
            logger.info("Waiting 45 seconds for execution to complete...")
            time.sleep(45)
        else:
            logger.warning(f"Notebook execution: {run_response.status_code}")
            
    def update_semantic_model_parameters(self, workspace_id, sql_endpoint_id):
        """Update semantic model parameters"""
        logger.info("Updating semantic model parameters...")
        
        token = self.get_powerbi_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Get dataset ID
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        datasets = response.json().get('value', [])
        dataset = next((d for d in datasets if d['name'] == 'ConferenceAttendanceSemanticModel'), None)
        
        if not dataset:
            logger.warning("Semantic model not found - may not be synced yet")
            return False
            
        dataset_id = dataset['id']
        logger.info(f"✓ Semantic Model ID: {dataset_id}")
        
        # Update parameters
        update_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{dataset_id}/Default.UpdateParameters"
        
        payload = {
            "updateDetails": [
                {
                    "name": "SqlServer",
                    "newValue": "XP4ZNS2QL4NEHEQ6EJQCCJO6NY-YYVGA7WCYGSE3I6Z4SAWOQFPMI.datawarehouse.fabric.microsoft.com"
                },
                {
                    "name": "SqlDatabase",
                    "newValue": sql_endpoint_id
                }
            ]
        }
        
        update_response = requests.post(update_url, headers=headers, json=payload)
        
        if update_response.status_code in [200, 204]:
            logger.info("✓ Parameters updated successfully")
        else:
            logger.error(f"Failed to update parameters: {update_response.status_code}")
            logger.error(f"Response: {update_response.text}")
            return False
            
        # Refresh dataset
        refresh_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{dataset_id}/refreshes"
        refresh_response = requests.post(refresh_url, headers=headers, json={"notifyOption": "NoNotification"})
        
        if refresh_response.status_code in [200, 202]:
            logger.info("✓ Dataset refresh triggered")
            logger.info("Waiting 30 seconds for refresh to complete...")
            time.sleep(30)
        else:
            logger.warning(f"Dataset refresh: {refresh_response.status_code}")
            
        return True
        
    def deploy_workspace(self, workspace_config):
        """Deploy a single workspace end-to-end"""
        workspace_name = workspace_config['name']
        
        logger.info("\n" + "="*60)
        logger.info(f"DEPLOYING WORKSPACE: {workspace_name}")
        logger.info("="*60 + "\n")
        
        try:
            # Step 1: Create workspace
            capacity_id = self.config['fabric']['capacity_id']
            workspace_id = self.create_workspace(workspace_name, capacity_id)
            workspace_config['id'] = workspace_id
            
            # Step 2: Configure Git integration
            git_config = workspace_config.get('git', {})
            if git_config.get('enabled', True):
                self.configure_git_integration(workspace_id, workspace_name, git_config)
            
            # Step 3: Create lakehouse
            lakehouse_name = workspace_config.get('lakehouse', {}).get('name', 'ConferenceDataLakehouse')
            lakehouse_id = self.create_lakehouse(workspace_id, lakehouse_name)
            
            # Step 4: Get lakehouse info
            lakehouse_id, sql_endpoint_id = self.get_lakehouse_info(workspace_id, lakehouse_name)
            workspace_config['sql_endpoint_id'] = sql_endpoint_id
            
            # Step 5: Upload data
            data_file = workspace_config.get('data_file', 'conference_attendance.csv')
            # Ensure full path to sample-data folder
            if not data_file.startswith('sample-data'):
                data_file = f"sample-data/{data_file}"
            self.upload_data_to_onelake(workspace_id, lakehouse_id, data_file)
            
            # Step 6: Run notebook
            notebook_name = workspace_config.get('notebook_name', 'LoadConferenceData')
            self.run_notebook(workspace_id, notebook_name)
            
            # Step 7: Update semantic model parameters
            if sql_endpoint_id:
                logger.info("\nWaiting 10 seconds before parameter update...")
                time.sleep(10)
                
                self.update_semantic_model_parameters(workspace_id, sql_endpoint_id)
            
            logger.info("\n" + "="*60)
            logger.info(f"✓ DEPLOYMENT SUCCESSFUL: {workspace_name}")
            logger.info("="*60 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"\n✗ DEPLOYMENT FAILED: {workspace_name}")
            logger.error(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
    def deploy_all(self):
        """Deploy all enabled workspaces"""
        logger.info("\n" + "="*60)
        logger.info("COMPLETE AUTOMATED DEPLOYMENT")
        logger.info("="*60)
        logger.info(f"Total workspaces: {len(self.enabled_workspaces)}")
        logger.info(f"Cleanup first: {self.cleanup_first}")
        logger.info("="*60 + "\n")
        
        # Cleanup if requested
        if self.cleanup_first:
            self.cleanup_workspaces()
            logger.info("Waiting 30 seconds after cleanup...")
            time.sleep(30)
            
        # Deploy each workspace
        successful = []
        failed = []
        
        for workspace_config in self.enabled_workspaces:
            if self.deploy_workspace(workspace_config):
                successful.append(workspace_config['name'])
            else:
                failed.append(workspace_config['name'])
                
        # Summary
        logger.info("\n" + "="*60)
        logger.info("DEPLOYMENT SUMMARY")
        logger.info("="*60)
        logger.info(f"Total: {len(self.enabled_workspaces)}")
        logger.info(f"Successful: {len(successful)}")
        logger.info(f"Failed: {len(failed)}")
        
        if successful:
            logger.info(f"\n✓ Successful:")
            for name in successful:
                logger.info(f"  - {name}")
                
        if failed:
            logger.info(f"\n✗ Failed:")
            for name in failed:
                logger.info(f"  - {name}")
                
        # Save updated config
        with open(self.config_file, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
            
        logger.info(f"\n✓ Configuration saved to {self.config_file}")
        logger.info("="*60 + "\n")
        
        return 0 if not failed else 1


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Complete Fabric deployment with parameterization')
    parser.add_argument('--cleanup', action='store_true', help='Delete existing workspaces first')
    parser.add_argument('--config', default='config/workspace-config.yaml', help='Config file path')
    
    args = parser.parse_args()
    
    deployer = CompleteFabricDeployer(
        config_file=args.config,
        cleanup_first=args.cleanup
    )
    
    return deployer.deploy_all()


if __name__ == '__main__':
    sys.exit(main())
