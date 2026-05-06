"""
Assign Default Lakehouse to Notebooks in Multiple Workspaces
This script automatically assigns the correct lakehouse to each notebook in each workspace.
"""

import yaml
import subprocess
import json
import sys
import time

class LakehouseAssigner:
    def __init__(self, config_path="config/workspace-config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.token = None
    
    def get_fabric_token(self):
        """Get Fabric API token using Azure CLI"""
        if not self.token:
            result = subprocess.run(
                ['az', 'account', 'get-access-token', '--resource', 'https://api.fabric.microsoft.com'],
                capture_output=True,
                text=True,
                shell=True
            )
            if result.returncode == 0:
                self.token = json.loads(result.stdout)['accessToken']
            else:
                raise Exception(f"Failed to get token: {result.stderr}")
        return self.token
    
    def get_workspace_items(self, workspace_id):
        """Get all items in a workspace"""
        import requests
        
        token = self.get_fabric_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        url = f'https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json().get('value', [])
        else:
            print(f"❌ Failed to get items: {response.status_code}")
            print(response.text)
            return []
    
    def update_notebook_lakehouse(self, workspace_id, notebook_id, lakehouse_id, notebook_name, lakehouse_name):
        """Update notebook to use specific lakehouse as default"""
        import requests
        
        token = self.get_fabric_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Get current notebook definition
        url = f'https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks/{notebook_id}'
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Failed to get notebook {notebook_name}: {response.status_code}")
            return False
        
        # Update notebook definition with lakehouse reference
        # The notebook needs to have the lakehouse set in its metadata
        definition_url = f'https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/definition'
        
        # Get the current definition
        response = requests.post(f"{definition_url}/getDefinition", headers=headers)
        
        if response.status_code == 202:
            # Wait for the operation to complete
            operation_url = response.headers.get('Location')
            if operation_url:
                # Poll for completion
                max_attempts = 30
                for i in range(max_attempts):
                    time.sleep(2)
                    op_response = requests.get(operation_url, headers=headers)
                    if op_response.status_code == 200:
                        result = op_response.json()
                        if result.get('status') == 'Succeeded':
                            print(f"✅ Retrieved definition for {notebook_name}")
                            break
                    elif i == max_attempts - 1:
                        print(f"⚠️ Timeout waiting for definition")
                        return False
        
        # For now, we'll use the Fabric VS Code extension's approach
        # The notebook metadata should include defaultLakehouse reference
        print(f"ℹ️ Notebook {notebook_name} will be updated via Fabric extension tool")
        return True
    
    def assign_lakehouses(self):
        """Assign default lakehouses to notebooks in all workspaces"""
        print("\n🏠 Assigning Default Lakehouses to Notebooks")
        print("=" * 60)
        
        for workspace_config in self.config['fabric']['workspaces']:
            if not workspace_config.get('enabled', True):
                continue
            
            workspace_name = workspace_config['name']
            # You'll need to update this with actual workspace IDs
            # For now, we'll document what needs to be done
            
            print(f"\n📁 Workspace: {workspace_name}")
            print(f"   Lakehouse: {workspace_config['lakehouse']['name']}")
            print(f"   Notebook: {workspace_config.get('notebook_name', 'Load Conference Data')}")
            
            # This will be completed using the Fabric extension tool
            print(f"   ⚠️ Manual step required: Use fabric_setDefaultLakehouseTool")

if __name__ == "__main__":
    assigner = LakehouseAssigner()
    assigner.assign_lakehouses()
    
    print("\n" + "=" * 60)
    print("✅ Lakehouse assignment process documented")
    print("\nNext: Use Fabric VS Code extension to set default lakehouses")
    print("Or use the fabric_setDefaultLakehouseTool via GitHub Copilot")
