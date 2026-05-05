#!/usr/bin/env python3
"""
Setup Entra ID (Azure AD) authentication for Fabric deployment.
Assigns required RBAC roles and verifies permissions.
"""

import sys
import subprocess
import time

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "colorama"], check=True)
    from colorama import init, Fore, Style
    init(autoreset=True)


def run_command(cmd, description):
    """Run Azure CLI command."""
    print(f"\n{Fore.CYAN}{description}...{Style.RESET_ALL}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                print(f"{Fore.GREEN}✓ Success{Style.RESET_ALL}")
                return output
            else:
                print(f"{Fore.YELLOW}! Command succeeded but returned no output{Style.RESET_ALL}")
                return ""
        else:
            print(f"{Fore.RED}✗ Failed{Style.RESET_ALL}")
            print(f"{Fore.RED}{result.stderr}{Style.RESET_ALL}")
            return None
    except Exception as e:
        print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        return None


def get_account_info():
    """Get current Azure account information."""
    result = subprocess.run(
        'az account show --query "{subscription:id, user:user.name}" -o json',
        shell=True,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        import json
        return json.loads(result.stdout)
    return None


def assign_role_via_rest_api(storage_id, user_email, subscription_id):
    """Assign role using Azure REST API (bypasses Graph API token issues)."""
    import uuid
    import json
    
    # Generate a unique GUID for this role assignment
    role_assignment_name = str(uuid.uuid4())
    
    # Storage Blob Data Reader role definition ID (this is a well-known GUID)
    role_definition_id = f"/subscriptions/{subscription_id}/providers/Microsoft.Authorization/roleDefinitions/2a2b9908-6ea1-4ae2-8e65-a410df84e7d1"
    
    print(f"\n{Fore.CYAN}Attempting role assignment via REST API...{Style.RESET_ALL}")
    
    # Try method 1: Get signed-in user object ID (doesn't require Graph API)
    print(f"{Fore.CYAN}Getting signed-in user object ID...{Style.RESET_ALL}")
    result = subprocess.run(
        'az ad signed-in-user show --query id -o tsv',
        shell=True,
        capture_output=True,
        text=True
    )
    
    principal_id = None
    if result.returncode == 0 and result.stdout.strip():
        principal_id = result.stdout.strip()
        print(f"{Fore.GREEN}✓ Found object ID: {principal_id}{Style.RESET_ALL}")
    else:
        # Try method 2: Parse from access token
        print(f"{Fore.YELLOW}Trying to extract from access token...{Style.RESET_ALL}")
        token_result = subprocess.run(
            'az account get-access-token --query accessToken -o tsv',
            shell=True,
            capture_output=True,
            text=True
        )
        
        if token_result.returncode == 0 and token_result.stdout.strip():
            # Decode JWT token to get oid claim
            import base64
            try:
                token = token_result.stdout.strip()
                # JWT tokens have 3 parts separated by dots
                parts = token.split('.')
                if len(parts) >= 2:
                    # Add padding if needed
                    payload = parts[1]
                    payload += '=' * (4 - len(payload) % 4)
                    decoded = base64.b64decode(payload)
                    token_data = json.loads(decoded)
                    if 'oid' in token_data:
                        principal_id = token_data['oid']
                        print(f"{Fore.GREEN}✓ Extracted object ID from token: {principal_id}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}Could not parse token: {e}{Style.RESET_ALL}")
    
    if not principal_id:
        print(f"{Fore.RED}✗ Could not get user object ID{Style.RESET_ALL}")
        return False
    
    # Create role assignment using Azure Resource Manager REST API
    url = f"{storage_id}/providers/Microsoft.Authorization/roleAssignments/{role_assignment_name}?api-version=2022-04-01"
    
    body = {
        "properties": {
            "roleDefinitionId": role_definition_id,
            "principalId": principal_id,
            "principalType": "User"
        }
    }
    
    # Write JSON to temp file to avoid PowerShell escaping issues
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(body, f)
        temp_file = f.name
    
    try:
        print(f"{Fore.CYAN}Creating role assignment...{Style.RESET_ALL}")
        result = subprocess.run(
            f'az rest --method PUT --url "{url}" --body @{temp_file}',
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"{Fore.GREEN}✓ Role assignment successful!{Style.RESET_ALL}")
            return True
        else:
            # Check if already exists
            if "RoleAssignmentExists" in result.stderr or "already exists" in result.stderr.lower():
                print(f"{Fore.GREEN}✓ Role already assigned!{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.YELLOW}Assignment failed: {result.stderr.strip()}{Style.RESET_ALL}")
    finally:
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    return False


def main():
    RESOURCE_GROUP = "westusattendiesdata"
    STORAGE_ACCOUNT = "westusattendiesstore"
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}Setup Entra ID Authentication for Fabric")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}This script assigns Storage Blob Data Reader to the admin account that:{Style.RESET_ALL}")
    print(f"  1. Provisions Azure resources and Fabric workspaces")
    print(f"  2. Runs notebooks (via mssparkutils with user credentials)")
    print(f"  3. All authentication via Entra ID (no keys!)")
    print(f"\n{Fore.YELLOW}For production: Use workspace managed identity (see ENTRA_AUTH_GUIDE.md){Style.RESET_ALL}\n")
    
    # Step 1: Get current account info
    print(f"{Fore.CYAN}Getting Azure account information...{Style.RESET_ALL}")
    account_info = get_account_info()
    
    if not account_info:
        print(f"{Fore.RED}✗ Could not get account information. Please run: az login{Style.RESET_ALL}")
        return 1
    
    subscription_id = account_info['subscription']
    user_email = account_info['user']
    
    print(f"{Fore.GREEN}✓ Subscription: {subscription_id}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✓ User: {user_email}{Style.RESET_ALL}")
    
    # Step 2: Get storage account resource ID
    storage_id = run_command(
        f'az storage account show --name {STORAGE_ACCOUNT} --resource-group {RESOURCE_GROUP} --query id -o tsv',
        "Getting storage account resource ID"
    )
    
    if not storage_id:
        print(f"\n{Fore.RED}✗ Could not get storage account ID{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Manual steps required:{Style.RESET_ALL}")
        print(f"  1. Open: https://portal.azure.com")
        print(f"  2. Go to: {RESOURCE_GROUP} → {STORAGE_ACCOUNT} → Access Control (IAM)")
        print(f"  3. Add role assignment: 'Storage Blob Data Reader'")
        print(f"  4. Assign to: {user_email}")
        return 1
    
    print(f"{Fore.WHITE}  Storage ID: {storage_id}{Style.RESET_ALL}")
    
    # Step 3: Assign role using REST API (bypasses Graph API token issues)
    success = assign_role_via_rest_api(storage_id, user_email, subscription_id)
    
    if not success:
        print(f"\n{Fore.YELLOW}{'='*80}")
        print(f"{Fore.YELLOW}AUTOMATED ASSIGNMENT FAILED - MANUAL STEPS REQUIRED{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'='*80}{Style.RESET_ALL}\n")
        
        print(f"{Fore.WHITE}Azure Portal Method:{Style.RESET_ALL}\n")
        print(f"1. Open: https://portal.azure.com")
        print(f"2. Navigate to: Resource Groups → {RESOURCE_GROUP} → {STORAGE_ACCOUNT}")
        print(f"3. Click: Access Control (IAM)")
        print(f"4. Click: + Add → Add role assignment")
        print(f"5. Select role: {Fore.CYAN}Storage Blob Data Reader{Style.RESET_ALL}")
        print(f"6. Click: Next")
        print(f"7. Select: {Fore.CYAN}{user_email}{Style.RESET_ALL}")
        print(f"8. Click: Review + assign")
        print(f"9. Wait 5 minutes for RBAC propagation\n")
        return 1
    
    # Step 4: Wait for propagation
    print(f"\n{Fore.YELLOW}Waiting 10 seconds for RBAC propagation...{Style.RESET_ALL}")
    time.sleep(10)
    
    # Success
    print(f"\n{Fore.GREEN}{'='*80}")
    print(f"{Fore.GREEN}✓ Entra ID Authentication Configured{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}What's configured:{Style.RESET_ALL}")
    print(f"  ✓ User: {user_email}")
    print(f"  ✓ Role: Storage Blob Data Reader")
    print(f"  ✓ Scope: {STORAGE_ACCOUNT}")
    print(f"  ✓ Authentication: Entra ID (Azure AD)")
    print(f"  ✓ No keys or secrets in code")
    
    print(f"\n{Fore.CYAN}Next steps:{Style.RESET_ALL}")
    print(f"  1. Wait 5 minutes for complete RBAC propagation")
    print(f"  2. Open Fabric workspace: https://app.fabric.microsoft.com")
    print(f"  3. Run notebook 'Load Conference Data'")
    print(f"  4. Notebook will use your Entra ID credentials automatically via mssparkutils")
    
    print(f"\n{Fore.WHITE}For more info, see: docs/ENTRA_AUTH_GUIDE.md{Style.RESET_ALL}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
