#!/usr/bin/env python3
"""
Complete End-to-End Power BI Report Deployment

This script orchestrates:
1. Run Notebook to load data into Lakehouse
2. Wait for semantic model to be auto-created
3. Create Power BI report bound to semantic model
4. Provide instructions for adding visuals

Full automation!
"""

import sys
import subprocess
import time
import argparse

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        CYAN = GREEN = YELLOW = WHITE = RED = ""
    class Style:
        RESET_ALL = ""

try:
    import requests
except ImportError:
    print("Error: 'requests' required. Run: pip install requests")
    sys.exit(1)


def run_command(cmd):
    """Execute command."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return None


def get_fabric_token():
    """Get Fabric API token."""
    return run_command(
        "az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv"
    )


def run_notebook(workspace_id, notebook_id):
    """Trigger notebook execution."""
    print(f"\n{Fore.CYAN}Running notebook to load data...{Style.RESET_ALL}")
    
    token = get_fabric_token()
    if not token:
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Trigger notebook run via Fabric API
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{notebook_id}/jobs/instances?jobType=RunNotebook"
        
        response = requests.post(url, headers=headers, json={}, timeout=30)
        response.raise_for_status()
        
        job_id = response.json().get("id")
        print(f"{Fore.GREEN}✓ Notebook job started: {job_id}{Style.RESET_ALL}")
        
        # Wait for completion
        print(f"{Fore.WHITE}  Waiting for notebook to complete...{Style.RESET_ALL}")
        
        status_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{notebook_id}/jobs/instances/{job_id}"
        
        for i in range(30):  # Max 5 minutes (30 * 10 seconds)
            time.sleep(10)
            
            status_response = requests.get(status_url, headers=headers, timeout=10)
            status_response.raise_for_status()
            
            status = status_response.json().get("status")
            print(f"{Fore.WHITE}  Status: {status}{Style.RESET_ALL}")
            
            if status == "Completed":
                print(f"{Fore.GREEN}✓ Notebook completed successfully!{Style.RESET_ALL}")
                return True
            elif status in ["Failed", "Cancelled"]:
                print(f"{Fore.RED}✗ Notebook execution failed{Style.RESET_ALL}")
                return False
        
        print(f"{Fore.YELLOW}⚠ Notebook still running (timeout)...{Style.RESET_ALL}")
        return True  # Assume success
        
    except Exception as e:
        print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(e.response.json())
            except:
                print(e.response.text)
        
        print(f"\n{Fore.YELLOW}Note: You can manually run the notebook in Fabric workspace{Style.RESET_ALL}")
        return False


def wait_for_semantic_model(workspace_id, lakehouse_name, max_wait=60):
    """Wait for semantic model to be created."""
    print(f"\n{Fore.CYAN}Waiting for semantic model creation...{Style.RESET_ALL}")
    
    token = get_fabric_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    for i in range(max_wait):
        try:
            url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            items = response.json().get("value", [])
            
            for item in items:
                if item.get("type") == "SemanticModel":
                    display_name = item.get("displayName")
                    if lakehouse_name in display_name:
                        model_id = item.get("id")
                        print(f"{Fore.GREEN}✓ Semantic model found: {display_name}{Style.RESET_ALL}")
                        return model_id, display_name
            
            print(f"{Fore.WHITE}  Waiting... ({i+1}s){Style.RESET_ALL}", end="\r")
            time.sleep(1)
            
        except Exception as e:
            print(f"{Fore.RED}✗ Error checking: {e}{Style.RESET_ALL}")
            time.sleep(1)
    
    print(f"\n{Fore.YELLOW}⚠ Semantic model not found yet{Style.RESET_ALL}")
    return None, None


def create_report(workspace_id, model_id, report_name):
    """Create Power BI report."""
    print(f"\n{Fore.CYAN}Creating Power BI report...{Style.RESET_ALL}")
    
    token = get_fabric_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports"
        
        payload = {
            "name": report_name,
            "datasetId": model_id
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        report_id = response.json().get("id")
        web_url = response.json().get("webUrl")
        
        print(f"{Fore.GREEN}✓ Report created!{Style.RESET_ALL}")
        print(f"  URL: {web_url}")
        
        return report_id, web_url
        
    except Exception as e:
        print(f"{Fore.RED}✗ Failed: {e}{Style.RESET_ALL}")
        return None, None


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Complete Power BI deployment")
    parser.add_argument("--workspace-id", required=True, help="Fabric workspace ID")
    parser.add_argument("--notebook-id", help="Notebook ID to run (optional)")
    parser.add_argument("--lakehouse-name", default="ConferenceDataLakehouse", help="Lakehouse name")
    parser.add_argument("--report-name", default="Conference Attendance Report", help="Report name")
    parser.add_argument("--skip-notebook", action="store_true", help="Skip notebook execution")
    
    args = parser.parse_args()
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Complete Power BI Report Deployment")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    # Step 1: Run notebook (optional)
    if not args.skip_notebook and args.notebook_id:
        success = run_notebook(args.workspace_id, args.notebook_id)
        if success:
            # Give time for semantic model to be created
            time.sleep(15)
    
    # Step 2: Wait for semantic model
    model_id, model_name = wait_for_semantic_model(args.workspace_id, args.lakehouse_name, max_wait=30)
    
    if not model_id:
        print(f"\n{Fore.YELLOW}{'=' * 80}")
        print(f"{Fore.YELLOW}Manual Steps Required")
        print(f"{Fore.YELLOW}{'=' * 80}{Style.RESET_ALL}\n")
        
        print(f"{Fore.WHITE}1. Load data into Lakehouse:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}   • Open workspace: https://app.fabric.microsoft.com/groups/{args.workspace_id}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}   • Run notebook: 'Load Conference Data'{Style.RESET_ALL}")
        print(f"{Fore.WHITE}   • Wait for completion{Style.RESET_ALL}\n")
        
        print(f"{Fore.WHITE}2. Verify semantic model created:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}   • Refresh workspace{Style.RESET_ALL}")
        print(f"{Fore.WHITE}   • Look for '{args.lakehouse_name}' semantic model{Style.RESET_ALL}\n")
        
        print(f"{Fore.WHITE}3. Re-run this script:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}   python scripts/create_powerbi_report.py --workspace-id {args.workspace_id}{Style.RESET_ALL}\n")
        
        sys.exit(1)
    
    # Step 3: Create report
    report_id, web_url = create_report(args.workspace_id, model_id, args.report_name)
    
    if not report_id:
        print(f"\n{Fore.RED}✗ Report creation failed{Style.RESET_ALL}")
        sys.exit(1)
    
    # Summary
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Deployment Complete!")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.GREEN}✓ Semantic Model: {model_name}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✓ Report: {args.report_name}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  URL: {web_url}{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}Next Steps:{Style.RESET_ALL}\n")
    print(f"{Fore.WHITE}1. Open report and click 'Edit'{Style.RESET_ALL}")
    print(f"{Fore.WHITE}2. Add visuals from template (see powerbi-templates/README.md){Style.RESET_ALL}")
    print(f"{Fore.WHITE}3. Save and publish{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}Or use Power BI Desktop:{Style.RESET_ALL}\n")
    print(f"{Fore.WHITE}1. Download .pbix from workspace{Style.RESET_ALL}")
    print(f"{Fore.WHITE}2. Add visuals in Desktop{Style.RESET_ALL}")
    print(f"{Fore.WHITE}3. Publish back to workspace{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()
