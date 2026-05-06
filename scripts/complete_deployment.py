"""
Complete Multi-Workspace Deployment
Uploads data, updates semantic models, and runs notebooks for all workspaces.
"""
import subprocess
import json
import time
import logging
import requests
import yaml
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DeploymentCompleter:
    def __init__(self):
        self.workspace_ids = {
            'West US Training': '3c687de4-6eb2-45ec-80ab-ff7dcb71bd0c',
            'East US Training': 'a1f1aed8-2357-4a12-be22-3956e2104953',
            'Central US Training': '91f25483-a8ca-4652-9e70-f060c0566b48'
        }
        self.data_files = {
            'West US Training': 'sample-data/west_us_attendance.csv',
            'East US Training': 'sample-data/east_us_attendance.csv',
            'Central US Training': 'sample-data/central_us_attendance.csv'
        }
        self.token = None
        
    def get_fabric_token(self):
        """Get Fabric API token via Azure CLI"""
        if self.token:
            return self.token
            
        logging.info("Getting Fabric API token via Azure CLI")
        try:
            result = subprocess.run(
                ['az', 'account', 'get-access-token', '--resource', 'https://api.fabric.microsoft.com'],
                capture_output=True,
                text=True,
                shell=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Azure CLI error: {result.stderr}")
            
            token_data = json.loads(result.stdout)
            self.token = token_data['accessToken']
            logging.info("✓ Fabric API token obtained")
            return self.token
            
        except Exception as e:
            logging.error(f"Failed to get token: {e}")
            raise
    
    def get_workspace_items(self, workspace_id):
        """Get all items in workspace"""
        token = self.get_fabric_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        url = f'https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items'
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json().get('value', [])
    
    def get_lakehouse_info(self, workspace_id, lakehouse_name='ConferenceDataLakehouse'):
        """Get lakehouse ID and SQL Endpoint ID"""
        items = self.get_workspace_items(workspace_id)
        
        # Find the lakehouse
        lakehouse = next((item for item in items if item['type'] == 'Lakehouse' and item['displayName'] == lakehouse_name), None)
        if not lakehouse:
            raise Exception(f"Lakehouse '{lakehouse_name}' not found in workspace")
        
        lakehouse_id = lakehouse['id']
        
        # Find the SQL Endpoint (same ID as lakehouse but different type)
        sql_endpoint = next((item for item in items if item['type'] == 'SQLEndpoint' and item['displayName'] == lakehouse_name), None)
        sql_endpoint_id = sql_endpoint['id'] if sql_endpoint else lakehouse_id
        
        return lakehouse_id, sql_endpoint_id
    
    def get_storage_token(self):
        """Get storage token for OneLake operations"""
        logging.info("Getting storage token for OneLake...")
        try:
            result = subprocess.run(
                ['az', 'account', 'get-access-token', '--resource', 'https://storage.azure.com'],
                capture_output=True,
                text=True,
                shell=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Azure CLI error: {result.stderr}")
            
            token_data = json.loads(result.stdout)
            logging.info("✓ Storage token obtained")
            return token_data['accessToken']
            
        except Exception as e:
            logging.error(f"Failed to get storage token: {e}")
            raise
    
    def upload_data_to_onelake(self, workspace_id, lakehouse_id, csv_file):
        """Upload CSV data to OneLake using proper 3-step process"""
        storage_token = self.get_storage_token()
        
        # Read CSV file
        csv_path = Path(csv_file)
        if not csv_path.exists():
            raise Exception(f"CSV file not found: {csv_file}")
        
        csv_data = csv_path.read_bytes()
        file_size = len(csv_data)
        
        logging.info(f"Uploading {csv_file} ({file_size} bytes) to OneLake...")
        
        # OneLake paths (filesystem=workspace_id, path=lakehouse_id/Files/...)
        onelake_host = 'onelake.dfs.fabric.microsoft.com'
        filesystem = workspace_id
        directory_path = f'{lakehouse_id}/Files/conference-data'
        file_path = f'{directory_path}/conference_attendance.csv'
        
        headers = {
            'Authorization': f'Bearer {storage_token}',
            'x-ms-version': '2023-11-03'
        }
        
        # Step 1: Create directory
        logging.info("Creating directory...")
        dir_url = f'https://{onelake_host}/{filesystem}/{directory_path}?resource=directory'
        response = requests.put(dir_url, headers=headers)
        if response.status_code not in [200, 201, 409]:  # 409 = already exists
            logging.warning(f"Directory creation returned {response.status_code}: {response.text}")
        
        # Step 2: Create file (PUT with resource=file)
        logging.info("Creating file...")
        file_url = f'https://{onelake_host}/{filesystem}/{file_path}?resource=file'
        response = requests.put(file_url, headers=headers)
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to create file: {response.status_code} - {response.text}")
        
        # Step 3: Upload content (PATCH with action=append)
        logging.info("Uploading content...")
        upload_url = f'https://{onelake_host}/{filesystem}/{file_path}?action=append&position=0'
        upload_headers = {
            'Authorization': f'Bearer {storage_token}',
            'Content-Length': str(file_size),
            'x-ms-version': '2023-11-03'
        }
        response = requests.patch(
            upload_url,
            headers=upload_headers,
            data=csv_data
        )
        if response.status_code not in [200, 202]:
            raise Exception(f"Failed to upload content: {response.status_code} - {response.text}")
        
        # Step 4: Flush (PATCH with action=flush)
        logging.info("Flushing data...")
        flush_url = f'https://{onelake_host}/{filesystem}/{file_path}?action=flush&position={file_size}'
        flush_headers = {
            'Authorization': f'Bearer {storage_token}',
            'x-ms-version': '2023-11-03'
        }
        response = requests.patch(
            flush_url,
            headers=flush_headers
        )
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to flush: {response.status_code} - {response.text}")
        
        logging.info(f"✓ Data uploaded successfully ({file_size} bytes)")
    
    def update_semantic_model_connection(self, workspace_id, workspace_name, sql_endpoint_id):
        """Print manual steps to update semantic model connection"""
        logging.info(f"\n{'='*60}")
        logging.info(f"MANUAL STEP REQUIRED: Update Semantic Model Connection")
        logging.info(f"Workspace: {workspace_name}")
        logging.info(f"{'='*60}")
        logging.info(f"SQL Endpoint ID: {sql_endpoint_id}")
        logging.info("")
        logging.info("Steps:")
        logging.info(f"1. Open: https://app.fabric.microsoft.com/groups/{workspace_id}")
        logging.info("2. Click on 'ConferenceAttendanceSemanticModel'")
        logging.info("3. Click 'Open data model' (top ribbon)")
        logging.info("4. In model designer, right-click the table → 'Edit query'")
        logging.info("5. In Power Query Editor:")
        logging.info("   - Find the Source step")
        logging.info(f"   - Update the database parameter to: {sql_endpoint_id}")
        logging.info("6. Click 'Close & Apply'")
        logging.info("7. Save the model")
        logging.info(f"{'='*60}\n")
    
    def run_notebook(self, workspace_id, notebook_name='Load Conference Data'):
        """Trigger notebook execution via API"""
        token = self.get_fabric_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Get notebook ID
        items = self.get_workspace_items(workspace_id)
        notebook = next((item for item in items if item['type'] == 'Notebook' and item['displayName'] == notebook_name), None)
        if not notebook:
            raise Exception(f"Notebook '{notebook_name}' not found")
        
        notebook_id = notebook['id']
        
        # Trigger notebook run
        url = f'https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/jobs/instances?jobType=RunNotebook'
        response = requests.post(url, headers=headers)
        
        if response.status_code == 202:
            logging.info(f"✓ Notebook '{notebook_name}' execution triggered")
        else:
            logging.warning(f"Notebook execution returned {response.status_code}: {response.text}")
    
    def process_workspace(self, workspace_name):
        """Complete deployment for a single workspace"""
        workspace_id = self.workspace_ids[workspace_name]
        data_file = self.data_files[workspace_name]
        
        logging.info(f"\n{'='*60}")
        logging.info(f"Processing: {workspace_name}")
        logging.info(f"Workspace ID: {workspace_id}")
        logging.info(f"{'='*60}")
        
        try:
            # 1. Get Lakehouse and SQL Endpoint IDs
            logging.info("Getting lakehouse and SQL Endpoint IDs...")
            lakehouse_id, sql_endpoint_id = self.get_lakehouse_info(workspace_id)
            logging.info(f"✓ Lakehouse ID: {lakehouse_id}")
            logging.info(f"✓ SQL Endpoint ID: {sql_endpoint_id}")
            
            # 2. Upload data
            self.upload_data_to_onelake(workspace_id, lakehouse_id, data_file)
            
            # 3. Run notebook to load data
            logging.info("Triggering notebook execution...")
            self.run_notebook(workspace_id)
            
            # 4. Print manual steps for semantic model
            self.update_semantic_model_connection(workspace_id, workspace_name, sql_endpoint_id)
            
            return {
                'workspace_name': workspace_name,
                'workspace_id': workspace_id,
                'sql_endpoint_id': sql_endpoint_id,
                'status': 'success'
            }
            
        except Exception as e:
            logging.error(f"✗ Failed to process {workspace_name}: {e}")
            return {
                'workspace_name': workspace_name,
                'workspace_id': workspace_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def complete_all_deployments(self):
        """Process all workspaces"""
        logging.info("\n" + "="*60)
        logging.info("COMPLETING MULTI-WORKSPACE DEPLOYMENT")
        logging.info("="*60)
        
        results = []
        for workspace_name in self.workspace_ids.keys():
            result = self.process_workspace(workspace_name)
            results.append(result)
            
            # Wait between workspaces
            if workspace_name != list(self.workspace_ids.keys())[-1]:
                logging.info("\nWaiting 5 seconds before next workspace...")
                time.sleep(5)
        
        # Summary
        logging.info("\n" + "="*60)
        logging.info("DEPLOYMENT SUMMARY")
        logging.info("="*60)
        
        successful = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] == 'failed']
        
        logging.info(f"Total: {len(results)}")
        logging.info(f"Successful: {len(successful)}")
        logging.info(f"Failed: {len(failed)}")
        
        if successful:
            logging.info("\n✓ Successful deployments:")
            for r in successful:
                logging.info(f"  - {r['workspace_name']}")
                logging.info(f"    Workspace ID: {r['workspace_id']}")
                logging.info(f"    SQL Endpoint ID: {r['sql_endpoint_id']}")
        
        if failed:
            logging.warning("\n✗ Failed deployments:")
            for r in failed:
                logging.warning(f"  - {r['workspace_name']}: {r.get('error', 'Unknown error')}")
        
        logging.info("\n" + "="*60)
        logging.info("NEXT STEPS")
        logging.info("="*60)
        logging.info("1. Update semantic model connections using the SQL Endpoint IDs above")
        logging.info("2. Wait for notebook executions to complete (~30 seconds each)")
        logging.info("3. Refresh semantic models in each workspace")
        logging.info("4. Open reports to verify data")
        logging.info("="*60)

if __name__ == '__main__':
    completer = DeploymentCompleter()
    completer.complete_all_deployments()
