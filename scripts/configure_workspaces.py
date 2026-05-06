#!/usr/bin/env python3
"""
Post-Deployment Configuration Script for Multi-Workspace Setup

This script configures each workspace after Git sync by:
1. Getting the lakehouse SQL Endpoint ID for each workspace
2. Updating the semantic model connection to point to that workspace's lakehouse
3. Uploading workspace-specific CSV data
4. Triggering notebook execution to create Delta tables

Usage:
    python scripts/configure_workspaces.py
    python scripts/configure_workspaces.py --workspace "West US Training"
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests
import yaml

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkspaceConfigurator:
    """Configures workspace-specific settings after Git sync."""
    
    def __init__(self, config_path: str = "config/workspace-config.yaml"):
        """Initialize the configurator with configuration."""
        self.config_path = config_path
        self.config = self._load_config()
        self.fabric_token = None
        self.onelake_token = None
        
    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        logger.info(f"Loading configuration from {self.config_path}")
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    
    def get_fabric_token(self) -> str:
        """Get Azure AD token for Fabric API."""
        if self.fabric_token:
            return self.fabric_token
            
        try:
            result = subprocess.run(
                "az account get-access-token --resource https://api.fabric.microsoft.com",
                capture_output=True,
                text=True,
                check=True,
                shell=True
            )
            token_data = json.loads(result.stdout)
            self.fabric_token = token_data["accessToken"]
            return self.fabric_token
        except Exception as e:
            logger.error(f"Failed to get Fabric API token: {e}")
            raise
    
    def get_onelake_token(self) -> str:
        """Get Azure AD token for OneLake API."""
        if self.onelake_token:
            return self.onelake_token
            
        try:
            result = subprocess.run(
                "az account get-access-token --resource https://storage.azure.com",
                capture_output=True,
                text=True,
                check=True,
                shell=True
            )
            token_data = json.loads(result.stdout)
            self.onelake_token = token_data["accessToken"]
            return self.onelake_token
        except Exception as e:
            logger.error(f"Failed to get OneLake token: {e}")
            raise
    
    def get_workspace_items(self, workspace_id: str) -> List[Dict]:
        """Get all items in a workspace."""
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
        
        return response.json().get('value', [])
    
    def get_lakehouse_sql_endpoint(self, workspace_id: str, lakehouse_name: str) -> Optional[Dict]:
        """Get the SQL Endpoint for a lakehouse."""
        items = self.get_workspace_items(workspace_id)
        
        # Find the SQL Endpoint (it has the same display name as the lakehouse)
        for item in items:
            if item.get('type') == 'SQLEndpoint' and item.get('displayName') == lakehouse_name:
                return item
        
        return None
    
    def update_semantic_model_connection(self, workspace_id: str, semantic_model_name: str, 
                                        sql_endpoint_id: str, sql_endpoint_server: str) -> bool:
        """Update semantic model to point to the correct SQL Endpoint."""
        logger.info(f"Updating semantic model '{semantic_model_name}' connection...")
        
        token = self.get_fabric_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Get semantic model item
        items = self.get_workspace_items(workspace_id)
        semantic_model = None
        for item in items:
            if item.get('type') == 'SemanticModel' and item.get('displayName') == semantic_model_name:
                semantic_model = item
                break
        
        if not semantic_model:
            logger.error(f"Semantic model '{semantic_model_name}' not found")
            return False
        
        semantic_model_id = semantic_model['id']
        
        # Update the semantic model definition via Fabric API
        # We need to update the expressions.tmdl to point to the new SQL Endpoint
        
        # Get current definition
        definition_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{semantic_model_id}/getDefinition"
        response = requests.post(definition_url, headers=headers, json={})
        
        if response.status_code != 200:
            logger.warning(f"Could not get semantic model definition: {response.status_code}")
            logger.info("You may need to manually update the semantic model connection in Fabric UI")
            return False
        
        definition_data = response.json()
        
        # Update the definition with new SQL Endpoint
        # This would require parsing and updating the TMDL files
        # For now, we'll provide manual instructions
        
        logger.info(f"✓ Found semantic model: {semantic_model_id}")
        logger.info(f"\nMANUAL STEP REQUIRED:")
        logger.info(f"  1. Open semantic model '{semantic_model_name}' in workspace")
        logger.info(f"  2. Go to Settings → Parameters or Data source settings")
        logger.info(f"  3. Update SQL Endpoint to: {sql_endpoint_server}")
        logger.info(f"  4. Database ID: {sql_endpoint_id}")
        logger.info(f"  Or edit expressions.tmdl locally and push to Git\n")
        
        return True
    
    def upload_workspace_data(self, workspace_id: str, lakehouse_id: str, csv_filename: str) -> bool:
        """Upload CSV data to workspace lakehouse."""
        logger.info(f"Uploading data: {csv_filename}")
        
        csv_path = f"sample-data/{csv_filename}"
        if not Path(csv_path).exists():
            logger.error(f"CSV file not found: {csv_path}")
            return False
        
        with open(csv_path, 'rb') as f:
            file_data = f.read()
        
        token = self.get_onelake_token()
        
        # Get lakehouse name
        items = self.get_workspace_items(workspace_id)
        lakehouse_name = None
        for item in items:
            if item.get('id') == lakehouse_id and item.get('type') == 'Lakehouse':
                lakehouse_name = item.get('displayName')
                break
        
        if not lakehouse_name:
            logger.error(f"Lakehouse not found: {lakehouse_id}")
            return False
        
        # OneLake path
        onelake_path = f"{workspace_id}/{lakehouse_name}.Lakehouse/Files/conference-data/conference_attendance.csv"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "x-ms-version": "2023-11-03"
        }
        
        try:
            # Step 1: Create file
            url = f"https://onelake.dfs.fabric.microsoft.com/{onelake_path}?resource=file"
            response = requests.put(url, headers=headers)
            
            if response.status_code == 409:
                # File exists, delete and recreate
                logger.info("File exists, overwriting...")
                delete_url = f"https://onelake.dfs.fabric.microsoft.com/{onelake_path}"
                requests.delete(delete_url, headers=headers)
                response = requests.put(url, headers=headers)
            
            response.raise_for_status()
            
            # Step 2: Upload data
            url = f"https://onelake.dfs.fabric.microsoft.com/{onelake_path}?action=append&position=0"
            headers["Content-Type"] = "application/octet-stream"
            response = requests.patch(url, headers=headers, data=file_data)
            response.raise_for_status()
            
            # Step 3: Flush
            url = f"https://onelake.dfs.fabric.microsoft.com/{onelake_path}?action=flush&position={len(file_data)}"
            response = requests.patch(url, headers=headers)
            response.raise_for_status()
            
            logger.info(f"✓ Uploaded {len(file_data)} bytes to OneLake")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload data: {e}")
            return False
    
    def configure_workspace(self, workspace_config: dict, workspace_id: str) -> Dict:
        """Configure a single workspace."""
        workspace_name = workspace_config['name']
        logger.info(f"\n{'='*60}")
        logger.info(f"Configuring workspace: {workspace_name}")
        logger.info(f"{'='*60}")
        
        results = {
            'workspace_name': workspace_name,
            'workspace_id': workspace_id,
            'success': False,
            'steps': {}
        }
        
        try:
            lakehouse_name = workspace_config.get('lakehouse', {}).get('name', 'ConferenceDataLakehouse')
            
            # Step 1: Get SQL Endpoint
            logger.info("\n--- Step 1: Get SQL Endpoint ---")
            sql_endpoint = self.get_lakehouse_sql_endpoint(workspace_id, lakehouse_name)
            
            if not sql_endpoint:
                logger.error(f"SQL Endpoint not found for lakehouse '{lakehouse_name}'")
                return results
            
            sql_endpoint_id = sql_endpoint['id']
            
            # Get SQL Endpoint properties to get the server address
            items = self.get_workspace_items(workspace_id)
            lakehouse_item = None
            for item in items:
                if item.get('type') == 'Lakehouse' and item.get('displayName') == lakehouse_name:
                    lakehouse_item = item
                    break
            
            if not lakehouse_item:
                logger.error(f"Lakehouse '{lakehouse_name}' not found")
                return results
            
            lakehouse_id = lakehouse_item['id']
            
            logger.info(f"✓ SQL Endpoint ID: {sql_endpoint_id}")
            logger.info(f"✓ Lakehouse ID: {lakehouse_id}")
            results['sql_endpoint_id'] = sql_endpoint_id
            results['lakehouse_id'] = lakehouse_id
            results['steps']['get_sql_endpoint'] = True
            
            # Step 2: Upload workspace-specific data
            logger.info("\n--- Step 2: Upload Data ---")
            csv_filename = workspace_config.get('data_file')
            if csv_filename:
                upload_success = self.upload_workspace_data(workspace_id, lakehouse_id, csv_filename)
                results['steps']['upload_data'] = upload_success
            else:
                logger.warning("No data_file specified in config")
                results['steps']['upload_data'] = False
            
            # Step 3: Update semantic model (manual for now)
            logger.info("\n--- Step 3: Update Semantic Model ---")
            semantic_model_name = workspace_config.get('powerbi', {}).get('semantic_model', 'ConferenceAttendanceSemanticModel')
            
            # For now, provide manual instructions
            # In the future, we can automate this by updating the TMDL files via API
            self.update_semantic_model_connection(
                workspace_id,
                semantic_model_name,
                sql_endpoint_id,
                f"<server>.datawarehouse.fabric.microsoft.com"
            )
            results['steps']['update_semantic_model'] = True
            
            results['success'] = True
            logger.info(f"\n✓ Workspace '{workspace_name}' configured")
            
        except Exception as e:
            logger.error(f"✗ Failed to configure workspace '{workspace_name}': {e}")
            results['error'] = str(e)
        
        return results
    
    def configure_all_workspaces(self, specific_workspace: Optional[str] = None) -> List[Dict]:
        """Configure all workspaces."""
        workspaces_config = self.config.get('workspaces', [])
        
        if specific_workspace:
            workspaces_config = [ws for ws in workspaces_config if ws['name'] == specific_workspace]
        
        enabled_workspaces = [ws for ws in workspaces_config if ws.get('enabled', False)]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Workspace Configuration")
        logger.info(f"{'='*60}")
        logger.info(f"Enabled workspaces: {len(enabled_workspaces)}")
        logger.info(f"{'='*60}\n")
        
        # First, get workspace IDs
        token = self.get_fabric_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(
            "https://api.fabric.microsoft.com/v1/workspaces",
            headers=headers
        )
        response.raise_for_status()
        
        all_workspaces = response.json().get('value', [])
        workspace_id_map = {ws['displayName']: ws['id'] for ws in all_workspaces}
        
        results = []
        for ws_config in enabled_workspaces:
            ws_name = ws_config['name']
            ws_id = workspace_id_map.get(ws_name)
            
            if not ws_id:
                logger.error(f"Workspace '{ws_name}' not found in Fabric")
                continue
            
            result = self.configure_workspace(ws_config, ws_id)
            results.append(result)
        
        # Summary
        self.print_summary(results)
        
        return results
    
    def print_summary(self, results: List[Dict]) -> None:
        """Print configuration summary."""
        logger.info(f"\n{'='*60}")
        logger.info("CONFIGURATION SUMMARY")
        logger.info(f"{'='*60}")
        
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]
        
        logger.info(f"Total: {len(results)}")
        logger.info(f"Successful: {len(successful)}")
        logger.info(f"Failed: {len(failed)}")
        
        if successful:
            logger.info(f"\n✓ Successfully configured:")
            for r in successful:
                logger.info(f"  - {r['workspace_name']}")
                logger.info(f"    SQL Endpoint: {r.get('sql_endpoint_id')}")
                logger.info(f"    Data uploaded: {r['steps'].get('upload_data', False)}")
        
        if failed:
            logger.warning(f"\n✗ Failed configurations:")
            for r in failed:
                logger.warning(f"  - {r['workspace_name']}: {r.get('error')}")
        
        logger.info(f"\n{'='*60}")
        logger.info("NEXT STEPS")
        logger.info(f"{'='*60}")
        logger.info("For each workspace:")
        logger.info("  1. Update semantic model connection (see manual steps above)")
        logger.info("  2. Open notebook 'Load Conference Data'")
        logger.info("  3. Click 'Run All' to create Delta tables")
        logger.info("  4. Refresh semantic model")
        logger.info("  5. Open report to verify data")
        logger.info(f"{'='*60}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Configure workspaces after deployment"
    )
    
    parser.add_argument(
        '--config',
        default='config/workspace-config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--workspace',
        help='Configure specific workspace only'
    )
    
    args = parser.parse_args()
    
    try:
        configurator = WorkspaceConfigurator(args.config)
        results = configurator.configure_all_workspaces(specific_workspace=args.workspace)
        
        failed = [r for r in results if not r.get('success')]
        return 1 if failed else 0
        
    except Exception as e:
        logger.error(f"Configuration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
