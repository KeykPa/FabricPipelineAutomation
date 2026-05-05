# ENTRA ID AUTHENTICATION - Required Configuration

## 🔐 **CRITICAL: All Services Use Entra ID (Azure AD)**

This project uses **Entra ID (formerly Azure AD) authentication** throughout to ensure secure, enterprise-grade access control without managing keys or secrets.

---

## ✅ **Authentication Architecture**

### **🎯 Identity Types**

#### **For Sample/Development** (This Project):
- **Identity**: Admin account (`admin@MngEnvMCAP882106.onmicrosoft.com`)
- **Purpose**: 
  - Provisions Azure resources and Fabric workspaces
  - Runs notebooks via `mssparkutils` (uses signed-in user credentials)
- **RBAC Required**: `Storage Blob Data Reader` on storage account
- **Benefits**: Simple, single identity for all operations

#### **For Production** (Recommended):
- **Identity**: Fabric Workspace Managed Identity or User-Assigned Managed Identity
- **Purpose**: Dedicated identity for workspace operations
- **RBAC Required**: Same roles, assigned to managed identity
- **Benefits**: Separation of duties, no human credentials in automation
- **Setup**: See "Production Managed Identity Setup" section below

---

### **1. Azure Resources**
- **Azure CLI**: Uses your organizational account
- **Azure Storage**: Entra ID with RBAC (no storage keys in code)
- **Fabric Workspace**: Entra ID SSO
- **Power BI**: Entra ID OAuth

### **2. Fabric Notebooks**
- **Authentication Method**: `mssparkutils` with user credentials
- **No Keys**: All access via Entra ID
- **Automatic**: Users authenticate once when opening workspace

### **3. GitHub Integration**
- **Method**: OAuth Device Flow
- **Interactive**: User authenticates via browser
- **Secure**: No tokens stored in code

---

## 📋 **Required RBAC Roles**

### **For This Sample: Admin Account**

The admin account (`admin@MngEnvMCAP882106.onmicrosoft.com`) needs **Storage Blob Data Reader** because it:
1. **Provisions** Fabric workspaces and resources
2. **Runs** notebooks (via `mssparkutils` with user credentials)

### **Storage Account Permissions**

```bash
# Required role on storage account
"Storage Blob Data Reader"
```

### **Assign Via Azure Portal** (Recommended):

1. **Open Azure Portal**: https://portal.azure.com
2. **Navigate to Storage Account**: `westusattendiesstore`
3. **Access Control (IAM)** → **Add role assignment**
4. **Role**: `Storage Blob Data Reader`
5. **Assign access to**: User, group, or service principal
6. **Select**: `admin@MngEnvMCAP882106.onmicrosoft.com`
   - ℹ️ **Note**: This is the admin account for both provisioning AND notebook execution
7. **Review + assign**
8. **Wait 5 minutes** for RBAC propagation

### **Assign Via Azure CLI**:

```bash
# Get storage account resource ID
STORAGE_ID=$(az storage account show \
  --name westusattendiesstore \
  --resource-group westusattendiesdata \
  --query id -o tsv)

# Assign role (replace with actual user email or object ID)
az role assignment create \
  --assignee user@domain.com \
  --role "Storage Blob Data Reader" \
  --scope $STORAGE_ID
```

### **Verify Role Assignment**:

```bash
az role assignment list \
  --assignee user@domain.com \
  --scope $STORAGE_ID \
  --role "Storage Blob Data Reader"
```

---

## 🚀 **Deployment Authentication Flow**

### **Step 1: Azure CLI Authentication**
```bash
az login
```
- Uses Entra ID organizational account
- Grants access to create Azure resources
- Token valid for resource management

### **Step 2: Fabric Workspace Access**
```bash
python scripts/deploy_workspaces.py
```
- Uses Fabric API with Entra ID token
- Creates workspace and assigns to capacity
- No credentials stored

### **Step 3: GitHub Integration**
- OAuth device flow (interactive)
- User authenticates via browser
- Workspace links to GitHub repo

### **Step 4: Notebook Execution**
- User opens workspace (Entra ID SSO)
- `mssparkutils` uses user's Entra ID credentials
- Accesses storage with RBAC permissions

---

## 🔧 **Troubleshooting Authentication**

### **403 Forbidden Error in Notebook**

**Cause**: User lacks Storage Blob Data Reader role

**Fix**:
1. Assign role via Azure Portal (see above)
2. Wait 5 minutes for RBAC propagation
3. Re-run notebook

### **Azure CLI Token Expired**

**Symptom**: `Continuous access evaluation resulted in challenge`

**Fix**:
```bash
az login --tenant <your-tenant-id>
```

---

## 🏢 **Production Managed Identity Setup**

For production workloads, use managed identities instead of user accounts.

### **Option 1: Workspace Identity** (Recommended for Fabric)

#### **Enable Workspace Identity**:
1. Open workspace in Fabric portal
2. **Workspace settings** → **Azure connections**
3. Enable **Workspace identity**
4. Copy the identity's **Object ID**

#### **Assign RBAC to Workspace Identity**:
```bash
# Get workspace identity object ID from portal
WORKSPACE_IDENTITY_ID="<object-id-from-portal>"

# Assign Storage Blob Data Reader
az role assignment create \
  --assignee-object-id $WORKSPACE_IDENTITY_ID \
  --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Reader" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/westusattendiesdata/providers/Microsoft.Storage/storageAccounts/westusattendiesstore"
```

#### **Update Notebook Code**:
```python
# No changes needed! mssparkutils automatically uses workspace identity
# when configured and user has insufficient permissions
from notebookutils import mssparkutils

storage_path = f"abfss://{container}@{storage_account}.dfs.core.windows.net/{file}"
df = spark.read.format("csv").option("header", "true").load(storage_path)
```

### **Option 2: User-Assigned Managed Identity**

#### **Create Managed Identity**:
```bash
az identity create \
  --name fabricPipelineIdentity \
  --resource-group westusattendiesdata
```

#### **Assign Storage Access**:
```bash
# Get identity principal ID
IDENTITY_ID=$(az identity show \
  --name fabricPipelineIdentity \
  --resource-group westusattendiesdata \
  --query principalId -o tsv)

# Assign role
az role assignment create \
  --assignee $IDENTITY_ID \
  --role "Storage Blob Data Reader" \
  --scope $(az storage account show --name westusattendiesstore --resource-group westusattendiesdata --query id -o tsv)
```

#### **Attach to Workspace**:
Currently, user-assigned managed identities must be configured via workspace settings in the Fabric portal.

### **Benefits of Managed Identity**:
- ✅ No credential management
- ✅ Automatic token rotation
- ✅ Separation of duties (workspace identity ≠ admin identity)
- ✅ Audit trail for workspace operations
- ✅ Works with automation and CI/CD

---

## 🔧 **Troubleshooting**

### **Fabric API 401 Unauthorized**

**Cause**: Token expired or wrong audience

**Fix**:
```bash
# Get fresh token
az account get-access-token --resource https://analysis.windows.net/powerbi/api
```

---

## 📚 **Security Best Practices**

### ✅ **DO:**
- Use Entra ID for all authentication
- Assign least-privilege RBAC roles
- Use managed identities where possible
- Rotate service principal credentials if used
- Enable Conditional Access policies

### ❌ **DON'T:**
- Store storage account keys in code
- Use connection strings in notebooks
- Commit credentials to Git
- Share access tokens
- Use anonymous access

---

## 🎯 **Quick Setup Checklist**

- [ ] Azure CLI installed and authenticated (`az login`)
- [ ] User has **Contributor** role on resource group
- [ ] User has **Storage Blob Data Reader** on storage account
- [ ] User has **Workspace Admin** role in Fabric workspace
- [ ] Capacity assigned to workspace
- [ ] RBAC propagation complete (wait 5 minutes after assignment)

---

## 📖 **Reference Links**

- [Azure RBAC Documentation](https://learn.microsoft.com/azure/role-based-access-control/)
- [Storage Blob Data Reader Role](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles#storage-blob-data-reader)
- [Fabric Security](https://learn.microsoft.com/fabric/security/)
- [mssparkutils Authentication](https://learn.microsoft.com/fabric/data-engineering/microsoft-spark-utilities)

---

## ⚡ **Automated Setup Script**

For automated RBAC assignment:

```bash
python scripts/setup_entra_auth.py
```

This script:
1. Gets current user identity
2. Assigns Storage Blob Data Reader role
3. Verifies permissions
4. Updates notebook configuration
5. Tests end-to-end authentication

---

**Last Updated**: May 5, 2026  
**Authentication Model**: Entra ID (Azure AD) Only - No Keys, No Secrets
