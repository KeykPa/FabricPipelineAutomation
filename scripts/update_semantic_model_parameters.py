#!/usr/bin/env python3
"""
Update Semantic Model Parameters using Power BI REST API
Sets SqlDatabase parameter to workspace-specific SQL Endpoint ID
"""

import os
import sys
import json
import time
import logging
import subprocess
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SemanticModelParameterUpdater:
    def __init__(self, workspace_id, workspace_name, sql_endpoint_id):
        self.workspace_id = workspace_id
        self.workspace_name = workspace_name
        self.sql_endpoint_id = sql_endpoint_id
        self.powerbi_token = None
        self.dataset_id = None
        
    def get_powerbi_token(self):
        """Get Power BI API token"""
        logger.info("Getting Power BI API token...")
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
        logger.info("✓ Power BI API token obtained")
        
    def get_dataset_id(self):
        """Get semantic model ID by name"""
        logger.info("Getting semantic model ID...")
        
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id}/datasets"
        headers = {
            'Authorization': f'Bearer {self.powerbi_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        datasets = response.json().get('value', [])
        dataset = next((d for d in datasets if d['name'] == 'ConferenceAttendanceSemanticModel'), None)
        
        if not dataset:
            raise Exception("Semantic model 'ConferenceAttendanceSemanticModel' not found")
            
        self.dataset_id = dataset['id']
        logger.info(f"✓ Semantic Model ID: {self.dataset_id}")
        
    def update_parameters(self):
        """Update dataset parameters via Power BI REST API"""
        logger.info(f"Updating parameters for {self.workspace_name}...")
        logger.info(f"  SqlServer: XP4ZNS2QL4NEHEQ6EJQCCJO6NY-YYVGA7WCYGSE3I6Z4SAWOQFPMI.datawarehouse.fabric.microsoft.com")
        logger.info(f"  SqlDatabase: {self.sql_endpoint_id}")
        
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id}/datasets/{self.dataset_id}/Default.UpdateParameters"
        headers = {
            'Authorization': f'Bearer {self.powerbi_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "updateDetails": [
                {
                    "name": "SqlServer",
                    "newValue": "XP4ZNS2QL4NEHEQ6EJQCCJO6NY-YYVGA7WCYGSE3I6Z4SAWOQFPMI.datawarehouse.fabric.microsoft.com"
                },
                {
                    "name": "SqlDatabase",
                    "newValue": self.sql_endpoint_id
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 204]:
            logger.info("✓ Parameters updated successfully")
        else:
            logger.error(f"Failed to update parameters: {response.status_code}")
            logger.error(f"Response: {response.text}")
            raise Exception(f"Parameter update failed: {response.text}")
            
    def refresh_dataset(self):
        """Trigger dataset refresh"""
        logger.info("Triggering dataset refresh...")
        
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id}/datasets/{self.dataset_id}/refreshes"
        headers = {
            'Authorization': f'Bearer {self.powerbi_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "notifyOption": "NoNotification"
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 202]:
            logger.info("✓ Dataset refresh triggered")
            logger.info("Waiting 30 seconds for refresh to complete...")
            time.sleep(30)
        else:
            logger.warning(f"Dataset refresh returned {response.status_code}: {response.text}")
            
    def execute(self):
        """Execute parameter update workflow"""
        logger.info(f"\n{'='*60}")
        logger.info(f"UPDATING PARAMETERS: {self.workspace_name}")
        logger.info(f"Workspace ID: {self.workspace_id}")
        logger.info(f"SQL Endpoint ID: {self.sql_endpoint_id}")
        logger.info(f"{'='*60}\n")
        
        try:
            # Step 1: Get Power BI token
            self.get_powerbi_token()
            
            # Step 2: Get dataset ID
            self.get_dataset_id()
            
            # Step 3: Update parameters
            self.update_parameters()
            
            # Step 4: Refresh dataset
            self.refresh_dataset()
            
            logger.info(f"\n{'='*60}")
            logger.info(f"✓ PARAMETER UPDATE SUCCESSFUL: {self.workspace_name}")
            logger.info(f"{'='*60}\n")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ PARAMETER UPDATE FAILED: {self.workspace_name}")
            logger.error(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Update parameters for all workspaces"""
    
    workspaces = [
        {
            'id': '3c687de4-6eb2-45ec-80ab-ff7dcb71bd0c',
            'name': 'West US Training',
            'sql_endpoint_id': '25c7be8f-cccb-43bb-b7b6-dce0f7bed5fe'
        },
        {
            'id': 'a1f1aed8-2357-4a12-be22-3956e2104953',
            'name': 'East US Training',
            'sql_endpoint_id': '02740c90-5a07-4cc3-855b-4559eb435a20'
        },
        {
            'id': '91f25483-a8ca-4652-9e70-f060c0566b48',
            'name': 'Central US Training',
            'sql_endpoint_id': 'a799af4d-47f4-4383-b443-f250695ba1a1'
        }
    ]
    
    logger.info(f"\n{'='*60}")
    logger.info("SEMANTIC MODEL PARAMETER UPDATE")
    logger.info(f"{'='*60}")
    logger.info(f"Total workspaces: {len(workspaces)}")
    logger.info(f"{'='*60}\n")
    
    successful = []
    failed = []
    
    for workspace in workspaces:
        updater = SemanticModelParameterUpdater(
            workspace['id'],
            workspace['name'],
            workspace['sql_endpoint_id']
        )
        
        if updater.execute():
            successful.append(workspace['name'])
        else:
            failed.append(workspace['name'])
            
        # Wait between workspaces
        if workspace != workspaces[-1]:
            logger.info("Waiting 5 seconds before next workspace...\n")
            time.sleep(5)
            
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("UPDATE SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total: {len(workspaces)}")
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
            
    logger.info(f"{'='*60}\n")
    
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
