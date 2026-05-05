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


def main():
    RESOURCE_GROUP = "westusattendiesdata"
    STORAGE_ACCOUNT = "westusattendiesstore"
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}Setup Entra ID Authentication for Fabric")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}This script will:{Style.RESET_ALL}")
    print(f"  1. Get current user identity")
    print(f"  2. Assign 'Storage Blob Data Reader' role")
    print(f"  3. Verify permissions")
    print(f"  4. All authentication via Entra ID (no keys!)\n")
    
    # Step 1: Get storage account resource ID
    storage_id = run_command(
        f'az storage account show --name {STORAGE_ACCOUNT} --resource-group {RESOURCE_GROUP} --query id -o tsv',
        "Getting storage account resource ID"
    )
    
    if not storage_id:
        print(f"\n{Fore.RED}✗ Could not get storage account ID{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Manual steps required:{Style.RESET_ALL}")
        print(f"  1. Open: https://portal.azure.com/#resource/subscriptions/<sub>/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.Storage/storageAccounts/{STORAGE_ACCOUNT}")
        print(f"  2. Go to: Access Control (IAM)")
        print(f"  3. Add role assignment: 'Storage Blob Data Reader'")
        print(f"  4. Assign to your user account")
        return 1
    
    print(f"{Fore.WHITE}  Storage ID: {storage_id}{Style.RESET_ALL}")
    
    # Step 2: Get current user
    print(f"\n{Fore.CYAN}Getting current user identity...{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}  If this fails, use Azure Portal to assign role manually{Style.RESET_ALL}")
    
    user_id = run_command(
        'az ad signed-in-user show --query id -o tsv',
        "Retrieving user object ID"
    )
    
    if not user_id:
        # Alternative: try getting from account
        print(f"{Fore.YELLOW}  Trying alternative method...{Style.RESET_ALL}")
        user_email = run_command(
            'az account show --query user.name -o tsv',
            "Getting user email"
        )
        
        if user_email:
            print(f"{Fore.WHITE}  User: {user_email}{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}{'='*80}")
            print(f"{Fore.YELLOW}MANUAL ROLE ASSIGNMENT REQUIRED{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
            
            print(f"{Fore.WHITE}Azure Portal Method (Recommended):{Style.RESET_ALL}\n")
            print(f"1. Open: https://portal.azure.com")
            print(f"2. Navigate to: Resource Groups → {RESOURCE_GROUP} → {STORAGE_ACCOUNT}")
            print(f"3. Click: Access Control (IAM)")
            print(f"4. Click: + Add → Add role assignment")
            print(f"5. Select role: {Fore.CYAN}Storage Blob Data Reader{Style.RESET_ALL}")
            print(f"6. Click: Next")
            print(f"7. Select: {Fore.CYAN}{user_email}{Style.RESET_ALL}")
            print(f"8. Click: Review + assign")
            print(f"9. Wait 5 minutes for RBAC propagation")
            
            print(f"\n{Fore.WHITE}Or use Azure CLI:{Style.RESET_ALL}\n")
            print(f"az role assignment create \\")
            print(f"  --assignee {user_email} \\")
            print(f"  --role 'Storage Blob Data Reader' \\")
            print(f"  --scope {storage_id}")
            
            return 0
        else:
            print(f"\n{Fore.RED}✗ Could not retrieve user identity{Style.RESET_ALL}")
            return 1
    
    print(f"{Fore.WHITE}  User ID: {user_id}{Style.RESET_ALL}")
    
    # Step 3: Check if role already assigned
    existing = run_command(
        f'az role assignment list --assignee {user_id} --scope {storage_id} --role "Storage Blob Data Reader" --query "[].id" -o tsv',
        "Checking existing role assignments"
    )
    
    if existing:
        print(f"\n{Fore.GREEN}✓ Role already assigned!{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  User already has 'Storage Blob Data Reader' access{Style.RESET_ALL}")
    else:
        # Step 4: Assign role
        assignment = run_command(
            f'az role assignment create --assignee {user_id} --role "Storage Blob Data Reader" --scope {storage_id}',
            "Assigning 'Storage Blob Data Reader' role"
        )
        
        if assignment:
            print(f"\n{Fore.GREEN}✓ Role assigned successfully!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  Waiting 30 seconds for RBAC propagation...{Style.RESET_ALL}")
            time.sleep(30)
        else:
            print(f"\n{Fore.RED}✗ Role assignment failed{Style.RESET_ALL}")
            return 1
    
    # Step 5: Verify
    print(f"\n{Fore.CYAN}Verifying permissions...{Style.RESET_ALL}")
    verify = run_command(
        f'az role assignment list --assignee {user_id} --scope {storage_id} --query "[].{{Role:roleDefinitionName,Scope:scope}}" -o table',
        "Listing role assignments"
    )
    
    if verify:
        print(f"\n{verify}")
    
    # Success
    print(f"\n{Fore.GREEN}{'='*80}")
    print(f"{Fore.GREEN}✓ Entra ID Authentication Configured{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}What's configured:{Style.RESET_ALL}")
    print(f"  ✓ RBAC: Storage Blob Data Reader role assigned")
    print(f"  ✓ Authentication: Entra ID (Azure AD)")
    print(f"  ✓ No keys or secrets in code")
    print(f"  ✓ Secure, enterprise-grade access control")
    
    print(f"\n{Fore.CYAN}Next steps:{Style.RESET_ALL}")
    print(f"  1. Wait 5 minutes for RBAC propagation (if just assigned)")
    print(f"  2. Open Fabric workspace")
    print(f"  3. Run notebook 'Load Conference Data'")
    print(f"  4. Notebook will use your Entra ID credentials automatically")
    
    print(f"\n{Fore.WHITE}For more info, see: docs/ENTRA_AUTH_GUIDE.md{Style.RESET_ALL}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
