# ENTRA ID AUTHENTICATION - Required Configuration

## 🔐 **CRITICAL: All Services Use Entra ID (Azure AD)**

This project uses **Entra ID (formerly Azure AD) authentication** throughout to ensure secure, enterprise-grade access control without managing keys or secrets.

---

## ✅ **Authentication Architecture**

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

### **Storage Account Permissions**

Every user who will run the Fabric notebook needs:

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
6. **Select**: Your user or group
7. **Review + assign**

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
