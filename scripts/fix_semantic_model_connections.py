"""
Fix Semantic Model Connections in All Workspaces
Updates the hardcoded SQL Endpoint connection to workspace-specific endpoints
"""

import subprocess
import json
import requests
import time

class SemanticModelFixer:
    def __init__(self):
        self.token = None
        
        # Workspace configurations
        self.workspaces = {
            "West US Training": {
                "workspace_id": "fc615d62-70ff-4e43-9974-643027144ee2",
                "sql_endpoint_id": "26edfea8-3e0d-4eab-a1cb-e1b54d9f94ee",
                "lakehouse_id": "a0e3109e-3197-4bf0-a30f-2611e777ef4b"
            },
            "East US Training": {
                "workspace_id": "50990989-81b4-4128-95d0-2eee8eff809a",
                "sql_endpoint_id": "e04e3078-7592-457f-913c-ef742f862576",
                "lakehouse_id": "f8f18265-eeb9-4be4-8ab3-ec55b3896504"
            },
            "Central US Training": {
                "workspace_id": "d2e05386-ef7d-40c2-a06e-bc89eadeb810",
                "sql_endpoint_id": "b7cf2b1b-685f-4e37-9afb-abec1aef4d9a",
                "lakehouse_id": "1db21ffc-fc6c-4c2d-af30-5d01ad814a00"
            }
        }
    
    def get_fabric_token(self):
        """Get Fabric API token"""
        if not self.token:
            result = subprocess.run(
                ['az', 'account', 'get-access-token', '--resource', 'https://api.fabric.microsoft.com'],
                capture_output=True,
                text=True,
                shell=True
            )
            if result.returncode == 0:
                self.token = json.loads(result.stdout)['accessToken']
        return self.token
    
    def get_powerbi_token(self):
        """Get Power BI API token"""
        result = subprocess.run(
            ['az', 'account', 'get-access-token', '--resource', 'https://analysis.windows.net/powerbi/api'],
            capture_output=True,
            text=True,
            shell=True
        )
        if result.returncode == 0:
            return json.loads(result.stdout)['accessToken']
        return None
    
    def get_semantic_model_id(self, workspace_id):
        """Get semantic model ID from workspace"""
        token = self.get_fabric_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        url = f'https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            items = response.json().get('value', [])
            for item in items:
                if item['type'] == 'SemanticModel' and 'ConferenceAttendance' in item['displayName']:
                    return item['id']
        return None
    
    def get_sql_endpoint_details(self, workspace_id, sql_endpoint_id):
        """Get SQL Endpoint server and database details"""
        token = self.get_fabric_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        url = f'https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{sql_endpoint_id}'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            item = response.json()
            # The SQL Endpoint properties contain connection details
            properties = item.get('properties', {})
            
            # Get connection string from properties
            # Format: <something>.datawarehouse.fabric.microsoft.com
            # For now, we'll construct it based on the pattern
            return {
                'database': sql_endpoint_id,
                'server_pattern': 'datawarehouse.fabric.microsoft.com'
            }
        
        return None
    
    def update_semantic_model_connection(self, workspace_id, model_id, sql_endpoint_id, workspace_name):
        """Update semantic model to use correct SQL Endpoint"""
        print(f"\n{'='*60}")
        print(f"Updating: {workspace_name}")
        print(f"{'='*60}")
        print(f"Workspace ID: {workspace_id}")
        print(f"Model ID: {model_id}")
        print(f"SQL Endpoint ID: {sql_endpoint_id}")
        
        # Get Power BI token
        pbi_token = self.get_powerbi_token()
        if not pbi_token:
            print("❌ Failed to get Power BI token")
            return False
        
        headers = {
            'Authorization': f'Bearer {pbi_token}',
            'Content-Type': 'application/json'
        }
        
        # Step 1: Get current data sources
        url = f'https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{model_id}/datasources'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            datasources = response.json().get('value', [])
            print(f"\n📊 Current data sources: {len(datasources)}")
            for ds in datasources:
                print(f"   - {ds.get('datasourceType')}: {ds.get('connectionDetails', {}).get('database', 'N/A')}")
        else:
            print(f"⚠️  Could not get datasources: {response.status_code}")
        
        # Step 2: Try to update parameters (if model uses parameters)
        url = f'https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{model_id}/Default.UpdateParameters'
        
        # Try updating with SQL Endpoint ID
        update_params = {
            "updateDetails": [
                {
                    "name": "DatabaseId",
                    "newValue": sql_endpoint_id
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=update_params)
        
        if response.status_code == 200:
            print("✅ Parameters updated successfully")
            return True
        else:
            print(f"⚠️  Parameter update status: {response.status_code}")
            if response.status_code == 400:
                print("   Note: Model may not use parameters")
        
        # Step 3: Try to rebind (if needed)
        print("\n📌 Manual step required:")
        print(f"   1. Open: https://app.fabric.microsoft.com/groups/{workspace_id}")
        print(f"   2. Open semantic model: ConferenceAttendanceSemanticModel")
        print(f"   3. Settings → Data source credentials")
        print(f"   4. Update database to: {sql_endpoint_id}")
        print(f"   5. Click Apply and Refresh")
        
        return False
    
    def refresh_semantic_model(self, workspace_id, model_id):
        """Trigger semantic model refresh"""
        pbi_token = self.get_powerbi_token()
        if not pbi_token:
            return False
        
        headers = {
            'Authorization': f'Bearer {pbi_token}',
            'Content-Type': 'application/json'
        }
        
        url = f'https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{model_id}/refreshes'
        response = requests.post(url, headers=headers, json={"notifyOption": "NoNotification"})
        
        if response.status_code == 202:
            print("✅ Refresh triggered")
            return True
        else:
            print(f"⚠️  Refresh status: {response.status_code}")
            return False
    
    def fix_all_workspaces(self):
        """Fix semantic models in all workspaces"""
        print("\n" + "="*60)
        print("SEMANTIC MODEL CONNECTION FIX")
        print("="*60)
        
        for workspace_name, config in self.workspaces.items():
            try:
                workspace_id = config['workspace_id']
                sql_endpoint_id = config['sql_endpoint_id']
                
                # Get semantic model ID
                model_id = self.get_semantic_model_id(workspace_id)
                
                if not model_id:
                    print(f"\n❌ {workspace_name}: Semantic model not found")
                    continue
                
                # Update connection
                self.update_semantic_model_connection(
                    workspace_id,
                    model_id,
                    sql_endpoint_id,
                    workspace_name
                )
                
            except Exception as e:
                print(f"\n❌ Error in {workspace_name}: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print("\n⚠️  Manual Steps Required:")
        print("\nFor each workspace:")
        print("1. Open the workspace in Fabric")
        print("2. Open ConferenceAttendanceSemanticModel")
        print("3. Click Settings (gear icon)")
        print("4. Go to 'Data source credentials' or 'Parameters'")
        print("5. Update the connection to use the correct SQL Endpoint:")
        print("\n   Workspace SQL Endpoint IDs:")
        for name, config in self.workspaces.items():
            print(f"   - {name}: {config['sql_endpoint_id']}")
        print("\n6. Click 'Apply' and 'Refresh dataset'")
        print("7. Open the report to verify data displays")

if __name__ == "__main__":
    fixer = SemanticModelFixer()
    fixer.fix_all_workspaces()
