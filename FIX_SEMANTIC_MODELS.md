# Fix Semantic Model Connections - Complete Guide

## Current Status

✅ **All 3 workspaces deployed successfully:**
- West US Training: `a66b6ce9-4716-48ea-aa58-c93d11626d04`
- East US Training: `c827aea1-0901-4be3-8b70-be074ac9bd6c`
- Central US Training: `28dfcaa8-978b-47c8-92c7-1917f5e6a214`

✅ **Data uploaded to all workspaces**
✅ **Notebooks triggered (West & East US)**

## Problem

The semantic models are pointing to the **old deleted lakehouse** (`2b18478d-fd10-4b63-af4b-5ff1713f542a`) because this connection is hardcoded in the Git repository file:
`ConferenceAttendanceSemanticModel.SemanticModel/definition/expressions.tmdl`

## Solution 1: Manual Fix (Quick - 5 minutes per workspace)

### West US Training
**SQL Endpoint ID:** `e6d537ff-f837-41b5-b05b-2d9aa5ce861b`

1. Open: https://app.fabric.microsoft.com/groups/a66b6ce9-4716-48ea-aa58-c93d11626d04
2. Click on **ConferenceAttendanceSemanticModel**
3. Click **Open data model** (top ribbon)
4. In model designer, right-click the **conference_attendance** table → **Edit query**
5. In Power Query Editor:
   - Find the **Source** step (should show old lakehouse ID)
   - Update the M code to use new SQL Endpoint ID:
     ```m
     = Sql.Database("XP4ZNS2QL4NEHEQ6EJQCCJO6NY-YYVGA7WCYGSE3I6Z4SAWOQFPMI.datawarehouse.fabric.microsoft.com", "e6d537ff-f837-41b5-b05b-2d9aa5ce861b")
     ```
6. Click **Close & Apply**
7. Save the model (Ctrl+S)
8. Refresh the model to load data

### East US Training
**SQL Endpoint ID:** `e929c471-9c9f-452c-8713-874637d29cc2`

1. Open: https://app.fabric.microsoft.com/groups/c827aea1-0901-4be3-8b70-be074ac9bd6c
2. Follow same steps as West US
3. Use SQL Endpoint ID: `e929c471-9c9f-452c-8713-874637d29cc2`

### Central US Training
**SQL Endpoint ID:** `e3b5a3f7-5fb8-4ee7-b28d-637dbe68b435`

1. Open: https://app.fabric.microsoft.com/groups/28dfcaa8-978b-47c8-92c7-1917f5e6a214
2. **First**: Manually run the **Load Conference Data** notebook (Git sync may not have completed)
3. Follow same semantic model update steps
4. Use SQL Endpoint ID: `e3b5a3f7-5fb8-4ee7-b28d-637dbe68b435`

## Solution 2: Fix Git Repository (Long-term - prevents future issues)

Update the semantic model definition to use a **parameter** instead of hardcoded ID:

### Option A: Use Power BI Parameters (Recommended for multi-workspace)

1. Open one workspace's semantic model in Power BI Desktop
2. Go to **Transform Data** → **Manage Parameters**
3. Create a new parameter: `LakehouseId`
4. Update the Source step to use parameter:
   ```m
   = Sql.Database("XP4ZNS2QL4NEHEQ6EJQCCJO6NY-YYVGA7WCYGSE3I6Z4SAWOQFPMI.datawarehouse.fabric.microsoft.com", LakehouseId)
   ```
5. Publish back to Fabric
6. Commit changes to Git (Workspace → Source Control → Commit changes)
7. Pull to local Git repository

### Option B: Update TMDL File Locally (Quick fix for Git)

1. Edit local file: `ConferenceAttendanceSemanticModel.SemanticModel/definition/expressions.tmdl`
2. Change the hardcoded connection to use a comment/placeholder:
   ```tmdl
   expression DatabaseQuery =
       let
           // SQL Endpoint ID - UPDATE THIS IN EACH WORKSPACE AFTER DEPLOYMENT
           // West US: e6d537ff-f837-41b5-b05b-2d9aa5ce861b
           // East US: e929c471-9c9f-452c-8713-874637d29cc2
           // Central US: e3b5a3f7-5fb8-4ee7-b28d-637dbe68b435
           Source = Sql.Database("XP4ZNS2QL4NEHEQ6EJQCCJO6NY-YYVGA7WCYGSE3I6Z4SAWOQFPMI.datawarehouse.fabric.microsoft.com", "REPLACE_WITH_SQL_ENDPOINT_ID")
       in
           Source;
   ```
3. Commit and push to GitHub
4. Update automation scripts to document this manual step

## Verification Checklist

After fixing semantic models:

- [ ] West US Report shows 25 records (West Coast companies: Microsoft, Amazon, Google, etc.)
- [ ] East US Report shows 25 records (Financial firms: JPMorgan, Goldman Sachs, etc.)
- [ ] Central US Report shows 25 records (Industrial companies: United Airlines, Boeing, etc.)
- [ ] Each report shows ONLY its workspace's data (no mixing)
- [ ] Reports load without connection errors

## Next Deployment

For the next clean deployment:

1. If you fixed Git with parameters → Manual step: Set parameter value in each workspace
2. If using hardcoded approach → Manual step: Update SQL Endpoint ID in each semantic model (same as today)
3. Consider creating a post-deployment PowerShell script to automate semantic model updates via Power BI REST API

## Current Workspace IDs Reference

```yaml
workspaces:
  - name: West US Training
    id: a66b6ce9-4716-48ea-aa58-c93d11626d04
    lakehouse_id: 095eca46-ba23-4e49-b344-c718f55e8e59
    sql_endpoint_id: e6d537ff-f837-41b5-b05b-2d9aa5ce861b
    data_file: west_us_attendance.csv
    
  - name: East US Training
    id: c827aea1-0901-4be3-8b70-be074ac9bd6c
    lakehouse_id: 6c2b58fd-c022-4238-ac9b-1a144d7d8c26
    sql_endpoint_id: e929c471-9c9f-452c-8713-874637d29cc2
    data_file: east_us_attendance.csv
    
  - name: Central US Training
    id: 28dfcaa8-978b-47c8-92c7-1917f5e6a214
    lakehouse_id: 12711c88-4f94-422d-a5ff-9339cece16c6
    sql_endpoint_id: e3b5a3f7-5fb8-4ee7-b28d-637dbe68b435
    data_file: central_us_attendance.csv
```

## Documentation Updated

This information is now documented in:
- [x] This file (FIX_SEMANTIC_MODELS.md)
- [ ] WORKSPACE_PARAMETRIZATION_GUIDE.md (needs updating with new IDs)
- [ ] MULTI_WORKSPACE_DEPLOYMENT.md (needs manual step documentation)
