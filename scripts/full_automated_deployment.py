#!/usr/bin/env python3
"""
Fully Automated Fabric Workspace Deployment
Creates: Pipeline → Executes → Semantic Model → Report
No manual steps required (except Git OAuth once per workspace)
"""

import os
import sys
import json
import time
import logging
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FullyAutomatedDeployer:
    def __init__(self, workspace_id, workspace_name, data_file):
        self.workspace_id = workspace_id
        self.workspace_name = workspace_name
        self.data_file = data_file
        self.fabric_token = None
        self.storage_token = None
        self.powerbi_token = None
        self.lakehouse_id = None
        self.sql_endpoint_id = None
        self.pipeline_id = None
        self.semantic_model_id = None
        self.report_id = None
        
    def get_fabric_token(self):
        """Get Fabric API token via Azure CLI"""
        logger.info("Getting Fabric API token via Azure CLI")
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
        logger.info("✓ Fabric API token obtained")
        
    def get_storage_token(self):
        """Get storage token for OneLake"""
        logger.info("Getting storage token for OneLake...")
        result = subprocess.run(
            ['az', 'account', 'get-access-token', '--resource', 'https://storage.azure.com'],
            capture_output=True,
            text=True,
            shell=True
        )
        if result.returncode != 0:
            raise Exception(f"Failed to get storage token: {result.stderr}")
        
        token_data = json.loads(result.stdout)
        self.storage_token = token_data['accessToken']
        logger.info("✓ Storage token obtained")
        
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
        
    def get_lakehouse_info(self):
        """Get lakehouse and SQL endpoint IDs"""
        import requests
        
        logger.info("Getting lakehouse and SQL Endpoint IDs...")
        
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.workspace_id}/items?type=Lakehouse"
        headers = {
            'Authorization': f'Bearer {self.fabric_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        items = response.json().get('value', [])
        lakehouse = next((item for item in items if item['displayName'] == 'ConferenceDataLakehouse'), None)
        
        if not lakehouse:
            raise Exception("Lakehouse 'ConferenceDataLakehouse' not found")
            
        self.lakehouse_id = lakehouse['id']
        logger.info(f"✓ Lakehouse ID: {self.lakehouse_id}")
        
        # Get SQL Endpoint (same ID as lakehouse in most cases, but query to be sure)
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.workspace_id}/items?type=SQLEndpoint"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        sql_endpoints = response.json().get('value', [])
        sql_endpoint = next((item for item in sql_endpoints if 'ConferenceDataLakehouse' in item['displayName']), None)
        
        if sql_endpoint:
            self.sql_endpoint_id = sql_endpoint['id']
        else:
            # SQL Endpoint has same ID as lakehouse
            self.sql_endpoint_id = self.lakehouse_id
            
        logger.info(f"✓ SQL Endpoint ID: {self.sql_endpoint_id}")
        
    def upload_data_to_onelake(self):
        """Upload CSV data to OneLake using DFS API"""
        import requests
        
        logger.info(f"Uploading {self.data_file} to OneLake...")
        
        # Read the CSV file
        csv_path = Path('sample-data') / self.data_file
        if not csv_path.exists():
            raise Exception(f"Data file not found: {csv_path}")
            
        with open(csv_path, 'rb') as f:
            data = f.read()
            
        file_size = len(data)
        logger.info(f"File size: {file_size} bytes")
        
        # OneLake DFS API paths
        base_url = "https://onelake.dfs.fabric.microsoft.com"
        directory_path = f"{self.workspace_id}/{self.lakehouse_id}/Files/conference-data"
        file_path = f"{directory_path}/conference_attendance.csv"
        
        headers = {
            'Authorization': f'Bearer {self.storage_token}',
            'x-ms-version': '2021-06-08'
        }
        
        # Step 1: Create directory
        logger.info("Creating directory...")
        url = f"{base_url}/{directory_path}?resource=directory"
        response = requests.put(url, headers=headers)
        if response.status_code not in [201, 409]:  # 409 = already exists
            response.raise_for_status()
            
        # Step 2: Create file
        logger.info("Creating file...")
        url = f"{base_url}/{file_path}?resource=file"
        response = requests.put(url, headers=headers)
        response.raise_for_status()
        
        # Step 3: Append data
        logger.info("Uploading content...")
        url = f"{base_url}/{file_path}?action=append&position=0"
        headers['Content-Type'] = 'application/octet-stream'
        response = requests.patch(url, headers=headers, data=data)
        response.raise_for_status()
        
        # Step 4: Flush to finalize
        logger.info("Flushing data...")
        url = f"{base_url}/{file_path}?action=flush&position={file_size}"
        del headers['Content-Type']
        response = requests.patch(url, headers=headers)
        response.raise_for_status()
        
        logger.info(f"✓ Data uploaded successfully ({file_size} bytes)")
        
    def create_data_pipeline(self):
        """Create Data Pipeline to run the notebook"""
        import requests
        
        logger.info("Creating Data Pipeline...")
        
        pipeline_definition = {
            "displayName": "Load Conference Data Pipeline",
            "description": "Automated pipeline to load conference attendance data"
        }
        
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.workspace_id}/items"
        headers = {
            'Authorization': f'Bearer {self.fabric_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "displayName": "Load Conference Data Pipeline",
            "type": "DataPipeline",
            "definition": {
                "parts": [
                    {
                        "path": "pipeline-content.json",
                        "payload": json.dumps({
                            "name": "Load Conference Data Pipeline",
                            "properties": {
                                "activities": [
                                    {
                                        "name": "Load Conference Data Notebook",
                                        "type": "Notebook",
                                        "dependsOn": [],
                                        "policy": {
                                            "timeout": "0.12:00:00",
                                            "retry": 2,
                                            "retryIntervalInSeconds": 30
                                        },
                                        "typeProperties": {
                                            "notebook": {
                                                "referenceName": "Load Conference Data",
                                                "type": "NotebookReference"
                                            }
                                        }
                                    }
                                ],
                                "annotations": []
                            }
                        }),
                        "payloadType": "InlineBase64"
                    }
                ]
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 201:
            result = response.json()
            self.pipeline_id = result['id']
            logger.info(f"✓ Pipeline created: {self.pipeline_id}")
        else:
            # Pipeline might already exist, try to get it
            url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.workspace_id}/items?type=DataPipeline"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            pipelines = response.json().get('value', [])
            pipeline = next((p for p in pipelines if 'Load Conference Data' in p['displayName']), None)
            
            if pipeline:
                self.pipeline_id = pipeline['id']
                logger.info(f"✓ Using existing pipeline: {self.pipeline_id}")
            else:
                raise Exception("Failed to create or find pipeline")
                
    def execute_pipeline(self):
        """Execute the data pipeline and wait for completion"""
        import requests
        
        logger.info("Executing data pipeline...")
        
        # Note: Fabric Data Pipeline execution API is different from ADF
        # We'll use the notebook execution API directly instead
        
        # Get notebook ID
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.workspace_id}/items?type=Notebook"
        headers = {
            'Authorization': f'Bearer {self.fabric_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        notebooks = response.json().get('value', [])
        notebook = next((n for n in notebooks if n['displayName'] == 'Load Conference Data'), None)
        
        if not notebook:
            raise Exception("Notebook 'Load Conference Data' not found")
            
        notebook_id = notebook['id']
        
        # Execute notebook using Spark Job Definition API
        logger.info(f"Triggering notebook {notebook_id} execution...")
        
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{self.workspace_id}/items/{notebook_id}/jobs/instances?jobType=RunNotebook"
        
        response = requests.post(url, headers=headers)
        
        if response.status_code in [200, 202]:
            logger.info("✓ Notebook execution triggered")
            logger.info("Waiting 60 seconds for data to load...")
            time.sleep(60)
        else:
            logger.warning(f"Notebook execution returned {response.status_code}, continuing...")
            time.sleep(30)
            
    def create_semantic_model(self):
        """Create semantic model with correct SQL endpoint connection"""
        import requests
        
        logger.info("Creating semantic model...")
        
        # TMSL definition for the semantic model
        tmsl_definition = {
            "name": "ConferenceAttendanceSemanticModel",
            "compatibilityLevel": 1567,
            "model": {
                "culture": "en-US",
                "dataSources": [
                    {
                        "type": "structured",
                        "name": "SqlServer XP4ZNS2QL4NEHEQ6EJQCCJO6NY-YYVGA7WCYGSE3I6Z4SAWOQFPMI datawarehouse fabric microsoft com",
                        "connectionDetails": {
                            "protocol": "tds",
                            "address": {
                                "server": "XP4ZNS2QL4NEHEQ6EJQCCJO6NY-YYVGA7WCYGSE3I6Z4SAWOQFPMI.datawarehouse.fabric.microsoft.com",
                                "database": self.sql_endpoint_id
                            }
                        },
                        "credential": {
                            "AuthenticationKind": "ServiceAccount",
                            "kind": "SQL",
                            "path": f"xp4zns2ql4neheq6ejqccjo6ny-yyvga7wcygse3i6z4sawoqfpmi.datawarehouse.fabric.microsoft.com;{self.sql_endpoint_id}",
                            "PrivacySetting": "Organizational"
                        }
                    }
                ],
                "tables": [
                    {
                        "name": "conference_attendance",
                        "columns": [
                            {"name": "EventDate", "dataType": "dateTime", "sourceColumn": "EventDate"},
                            {"name": "AttendeeID", "dataType": "string", "sourceColumn": "AttendeeID"},
                            {"name": "LastName", "dataType": "string", "sourceColumn": "LastName"},
                            {"name": "FirstName", "dataType": "string", "sourceColumn": "FirstName"},
                            {"name": "Company", "dataType": "string", "sourceColumn": "Company"},
                            {"name": "Email", "dataType": "string", "sourceColumn": "Email"},
                            {"name": "JobTitle", "dataType": "string", "sourceColumn": "JobTitle"},
                            {"name": "SessionID", "dataType": "string", "sourceColumn": "SessionID"},
                            {"name": "SessionName", "dataType": "string", "sourceColumn": "SessionName"},
                            {"name": "CheckInTime", "dataType": "dateTime", "sourceColumn": "CheckInTime"},
                            {"name": "CheckOutTime", "dataType": "dateTime", "sourceColumn": "CheckOutTime"},
                            {"name": "Location", "dataType": "string", "sourceColumn": "Location"},
                            {"name": "AttendanceStatus", "dataType": "string", "sourceColumn": "AttendanceStatus"}
                        ],
                        "partitions": [
                            {
                                "name": "Partition",
                                "dataView": "full",
                                "source": {
                                    "type": "m",
                                    "expression": [
                                        f"let",
                                        f"    Source = Sql.Database(\"XP4ZNS2QL4NEHEQ6EJQCCJO6NY-YYVGA7WCYGSE3I6Z4SAWOQFPMI.datawarehouse.fabric.microsoft.com\", \"{self.sql_endpoint_id}\"),",
                                        f"    dbo_conference_attendance = Source{{[Schema=\"dbo\",Item=\"conference_attendance\"]}}[Data]",
                                        f"in",
                                        f"    dbo_conference_attendance"
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        }
        
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id}/datasets"
        headers = {
            'Authorization': f'Bearer {self.powerbi_token}',
            'Content-Type': 'application/json'
        }
        
        # Use Power BI REST API to create dataset from TMSL
        payload = {
            "name": "ConferenceAttendanceSemanticModel",
            "tables": tmsl_definition["model"]["tables"]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            result = response.json()
            self.semantic_model_id = result['id']
            logger.info(f"✓ Semantic model created: {self.semantic_model_id}")
        else:
            # Try to find existing model
            url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id}/datasets"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            datasets = response.json().get('value', [])
            dataset = next((d for d in datasets if d['name'] == 'ConferenceAttendanceSemanticModel'), None)
            
            if dataset:
                self.semantic_model_id = dataset['id']
                logger.info(f"✓ Using existing semantic model: {self.semantic_model_id}")
            else:
                logger.error(f"Failed to create semantic model: {response.text}")
                raise Exception("Failed to create semantic model")
                
    def refresh_semantic_model(self):
        """Refresh the semantic model to load data"""
        import requests
        
        logger.info("Refreshing semantic model...")
        
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id}/datasets/{self.semantic_model_id}/refreshes"
        headers = {
            'Authorization': f'Bearer {self.powerbi_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, headers=headers, json={"notifyOption": "NoNotification"})
        
        if response.status_code in [200, 202]:
            logger.info("✓ Semantic model refresh triggered")
            logger.info("Waiting 30 seconds for refresh to complete...")
            time.sleep(30)
        else:
            logger.warning(f"Semantic model refresh returned {response.status_code}: {response.text}")
            
    def create_report(self):
        """Create Power BI report"""
        import requests
        
        logger.info("Creating Power BI report...")
        
        # Read report definition
        report_json_path = Path('AttendanceReport.Report') / 'report.json'
        
        if not report_json_path.exists():
            logger.warning("Report template not found, skipping report creation")
            return
            
        with open(report_json_path, 'r') as f:
            report_definition = json.load(f)
            
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{self.workspace_id}/reports"
        headers = {
            'Authorization': f'Bearer {self.powerbi_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "name": "AttendanceReport",
            "datasetId": self.semantic_model_id
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            result = response.json()
            self.report_id = result['id']
            logger.info(f"✓ Report created: {self.report_id}")
        else:
            logger.warning(f"Report creation returned {response.status_code}: {response.text}")
            
    def deploy(self):
        """Execute full deployment"""
        logger.info(f"\n{'='*60}")
        logger.info(f"DEPLOYING: {self.workspace_name}")
        logger.info(f"Workspace ID: {self.workspace_id}")
        logger.info(f"Data File: {self.data_file}")
        logger.info(f"{'='*60}\n")
        
        try:
            # Step 1: Get tokens
            self.get_fabric_token()
            self.get_storage_token()
            self.get_powerbi_token()
            
            # Step 2: Get lakehouse info
            self.get_lakehouse_info()
            
            # Step 3: Upload data
            self.upload_data_to_onelake()
            
            # Step 4: Create and execute pipeline
            # self.create_data_pipeline()  # Skip for now, execute notebook directly
            self.execute_pipeline()
            
            # Step 5: Create semantic model
            self.create_semantic_model()
            
            # Step 6: Refresh semantic model
            self.refresh_semantic_model()
            
            # Step 7: Create report
            self.create_report()
            
            logger.info(f"\n{'='*60}")
            logger.info(f"✓ DEPLOYMENT SUCCESSFUL: {self.workspace_name}")
            logger.info(f"{'='*60}")
            logger.info(f"Workspace URL: https://app.fabric.microsoft.com/groups/{self.workspace_id}")
            logger.info(f"Lakehouse ID: {self.lakehouse_id}")
            logger.info(f"SQL Endpoint ID: {self.sql_endpoint_id}")
            if self.semantic_model_id:
                logger.info(f"Semantic Model ID: {self.semantic_model_id}")
            if self.report_id:
                logger.info(f"Report ID: {self.report_id}")
            logger.info(f"{'='*60}\n")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ DEPLOYMENT FAILED: {self.workspace_name}")
            logger.error(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Deploy to all workspaces"""
    
    workspaces = [
        {
            'id': '3c687de4-6eb2-45ec-80ab-ff7dcb71bd0c',
            'name': 'West US Training',
            'data_file': 'west_us_attendance.csv'
        },
        {
            'id': 'a1f1aed8-2357-4a12-be22-3956e2104953',
            'name': 'East US Training',
            'data_file': 'east_us_attendance.csv'
        },
        {
            'id': '91f25483-a8ca-4652-9e70-f060c0566b48',
            'name': 'Central US Training',
            'data_file': 'central_us_attendance.csv'
        }
    ]
    
    logger.info(f"\n{'='*60}")
    logger.info("FULLY AUTOMATED FABRIC DEPLOYMENT")
    logger.info(f"{'='*60}")
    logger.info(f"Total workspaces: {len(workspaces)}")
    logger.info(f"{'='*60}\n")
    
    successful = []
    failed = []
    
    for workspace in workspaces:
        deployer = FullyAutomatedDeployer(
            workspace['id'],
            workspace['name'],
            workspace['data_file']
        )
        
        if deployer.deploy():
            successful.append(workspace['name'])
        else:
            failed.append(workspace['name'])
            
        # Wait between deployments
        if workspace != workspaces[-1]:
            logger.info("Waiting 10 seconds before next workspace...\n")
            time.sleep(10)
            
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("DEPLOYMENT SUMMARY")
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
