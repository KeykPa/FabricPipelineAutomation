# Semantic Model Parameterization with XMLA/REST

## ✅ **Solution Implemented**

We've implemented **Power Query parameters + REST API updates** to eliminate hardcoded SQL Endpoint connections.

---

## 🎯 **How It Works**

### **1. Git-synced semantic model uses parameters**

**File**: `ConferenceAttendanceSemanticModel.SemanticModel/definition/expressions.tmdl`

```tmdl
/// Parameter for SQL Server endpoint
expression SqlServer = "XP4ZNS2QL4NEHEQ6EJQCCJO6NY-YYVGA7WCYGSE3I6Z4SAWOQFPMI.datawarehouse.fabric.microsoft.com" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

/// Parameter for SQL Database (Lakehouse SQL Endpoint ID)
expression SqlDatabase = "PLACEHOLDER-SQL-ENDPOINT-ID" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

expression DatabaseQuery =
    let
        database = Sql.Database(SqlServer, SqlDatabase)
    in
        database
```

**Benefits**:
- ✅ Visual design stays in Git
- ✅ Connections are workspace-specific
- ✅ No manual fixes required
- ✅ Fully automated deployment

---

### **2. Automation updates parameters per workspace**

**Script**: `scripts/update_semantic_model_parameters.py`

**Process**:
1. Get Power BI API token
2. Find semantic model by name
3. Update parameters via REST API:
   ```json
   {
     "updateDetails": [
       { "name": "SqlServer", "newValue": "..." },
       { "name": "SqlDatabase", "newValue": "{SQL_ENDPOINT_ID}" }
     ]
   }
   ```
4. Trigger dataset refresh
5. Data loaded from correct lakehouse

---

## 📋 **Deployment Workflow**

### **Step 1: Git sync** (brings parameterized model)
```bash
python scripts/deploy_multi_workspace.py
```
- Creates workspaces
- Assigns to capacity
- Configures Git integration (manual OAuth)
- Git sync brings semantic model with parameters

### **Step 2: Upload data & run notebook**
```bash
python scripts/complete_deployment.py
```
- Uploads CSV data to OneLake
- Triggers notebook execution
- Data loaded to Delta tables

### **Step 3: Update semantic model parameters**
```bash
python scripts/update_semantic_model_parameters.py
```
- Updates `SqlDatabase` parameter per workspace
- Triggers refresh
- Reports now show correct data

---

## 🔧 **REST API Endpoint Used**

```http
POST https://api.powerbi.com/v1.0/myorg/groups/{workspaceId}/datasets/{datasetId}/Default.UpdateParameters
Authorization: Bearer {token}
Content-Type: application/json

{
  "updateDetails": [
    { "name": "SqlDatabase", "newValue": "25c7be8f-cccb-43bb-b7b6-dce0f7bed5fe" }
  ]
}
```

**Token**: `az account get-access-token --resource https://analysis.windows.net/powerbi/api`

---

## ✅ **Workspace-Specific Parameters**

| Workspace           | SQL Endpoint ID                      |
|---------------------|--------------------------------------|
| West US Training    | `25c7be8f-cccb-43bb-b7b6-dce0f7bed5fe` |
| East US Training    | `02740c90-5a07-4cc3-855b-4559eb435a20` |
| Central US Training | `a799af4d-47f4-4383-b443-f250695ba1a1` |

---

## 🎯 **Alternative: XMLA (TMSL)**

For more advanced scenarios (multi-tenant, CI/CD), use XMLA:

```powershell
$xmlaEndpoint = "powerbi://api.powerbi.com/v1.0/myorg/WestUSTraining"
$command = @"
{
  "update": {
    "object": { "database": "ConferenceAttendanceSemanticModel" },
    "parameters": [
      { "name": "SqlDatabase", "value": "25c7be8f-cccb-43bb-b7b6-dce0f7bed5fe" }
    ]
  }
}
"@

Invoke-ASCmd -Server $xmlaEndpoint -Database "ConferenceAttendanceSemanticModel" -Query $command
```

**Requires**:
- XMLA endpoint = Read/Write (Fabric capacity)
- `SqlServer` module (PowerShell)

---

## 📚 **References**

- [Power BI REST API - Update Parameters](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/update-parameters)
- [XMLA endpoint in Fabric](https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-developer)
- [Power Query parameters](https://learn.microsoft.com/en-us/power-query/power-query-query-parameters)

---

## ✅ **Summary**

**Before**: Hardcoded connections → Manual fixes required  
**After**: Parameterized model → Fully automated deployment

**Benefits**:
- ✅ No manual Power Query editing
- ✅ Visual design version-controlled in Git
- ✅ Workspace-specific data isolation
- ✅ CI/CD ready
