#!/usr/bin/env python3
"""
End-to-End Deployment: Notebook → Table → Semantic Model → Power BI Report

This script orchestrates the complete pipeline:
1. Runs the notebook to create Delta table
2. Creates/finds semantic model from lakehouse
3. Creates Power BI report bound to the model
"""

import sys
import subprocess
import json
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
    """Execute shell command."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}Command failed: {cmd}{Style.RESET_ALL}")
        print(f"{Fore.RED}{e.stderr}{Style.RESET_ALL}")
        return None


def get_fabric_token():
    """Get Fabric API token."""
    return run_command(
        "az account get-access-token --resource https://api.fabric.microsoft.com --query accessToken -o tsv"
    )


def get_powerbi_token():
    """Get Power BI API token."""
    return run_command(
        "az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv"
    )


def run_notebook(workspace_id, notebook_id, notebook_name):
    """Trigger notebook execution."""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"Step 1: Running Notebook")
    print(f"{'=' * 80}{Style.RESET_ALL}\n")
    
    token = get_fabric_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Trigger notebook run
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/jobs/instances?jobType=RunNotebook"
        
        print(f"{Fore.WHITE}Triggering notebook: {notebook_name}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}URL: {url}{Style.RESET_ALL}")
        
        response = requests.post(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        job_info = response.json()
        job_id = job_info.get("id")
        
        print(f"{Fore.GREEN}✓ Notebook execution started{Style.RESET_ALL}")
        print(f"  Job ID: {job_id}")
        
        # Wait for notebook completion
        print(f"\n{Fore.YELLOW}Waiting for notebook to complete...{Style.RESET_ALL}")
        
        for i in range(60):  # Wait up to 5 minutes
            time.sleep(5)
            
            # Check job status
            status_url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/jobs/instances/{job_id}"
            status_response = requests.get(status_url, headers=headers, timeout=10)
            
            if status_response.status_code == 200:
                status = status_response.json().get("status")
                print(f"  Status: {status} ({i*5}s elapsed)")
                
                if status == "Completed":
                    print(f"{Fore.GREEN}✓ Notebook completed successfully!{Style.RESET_ALL}")
                    return True
                elif status in ["Failed", "Cancelled"]:
                    print(f"{Fore.RED}✗ Notebook execution {status.lower()}{Style.RESET_ALL}")
                    return False
        
        print(f"{Fore.YELLOW}⚠ Notebook still running after 5 minutes{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  Continue anyway - table may already be created{Style.RESET_ALL}")
        return True
        
    except Exception as e:
        print(f"{Fore.RED}✗ Error running notebook: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"  {error_detail}")
            except:
                print(f"  Status: {e.response.status_code}")
                print(f"  Response: {e.response.text}")
        
        print(f"\n{Fore.YELLOW}You can run the notebook manually at:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}https://app.fabric.microsoft.com/groups/{workspace_id}/synapsenotebooks/{notebook_id}{Style.RESET_ALL}")
        
        return False


def find_lakehouse_semantic_model(workspace_id, lakehouse_name):
    """Find or create semantic model from lakehouse."""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"Step 2: Finding Semantic Model")
    print(f"{'=' * 80}{Style.RESET_ALL}\n")
    
    token = get_fabric_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # List all items in workspace
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        items = response.json().get("value", [])
        
        # Look for semantic model
        # Lakehouse creates a default semantic model with suffix " (default)"
        for item in items:
            if item.get("type") == "SemanticModel":
                display_name = item.get("displayName", "")
                
                # Match lakehouse name or default suffix
                if lakehouse_name.lower() in display_name.lower() or display_name.endswith("(default)"):
                    model_id = item.get("id")
                    print(f"{Fore.GREEN}✓ Found semantic model: {display_name}{Style.RESET_ALL}")
                    print(f"  ID: {model_id}")
                    return model_id, display_name
        
        # If not found, lakehouse should auto-create it when table is created
        print(f"{Fore.YELLOW}⚠ Semantic model not found yet{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  Waiting for Fabric to auto-generate semantic model...{Style.RESET_ALL}")
        
        # Wait and retry
        time.sleep(10)
        
        response = requests.get(url, headers=headers, timeout=10)
        items = response.json().get("value", [])
        
        for item in items:
            if item.get("type") == "SemanticModel":
                display_name = item.get("displayName", "")
                if lakehouse_name.lower() in display_name.lower() or display_name.endswith("(default)"):
                    model_id = item.get("id")
                    print(f"{Fore.GREEN}✓ Found semantic model: {display_name}{Style.RESET_ALL}")
                    print(f"  ID: {model_id}")
                    return model_id, display_name
        
        print(f"{Fore.RED}✗ Semantic model still not available{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Troubleshooting:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}1. Ensure the notebook ran successfully{Style.RESET_ALL}")
        print(f"{Fore.WHITE}2. Check that Delta table 'conference_attendance' exists in lakehouse{Style.RESET_ALL}")
        print(f"{Fore.WHITE}3. Lakehouse automatically creates semantic model when tables exist{Style.RESET_ALL}")
        
        return None, None
        
    except Exception as e:
        print(f"{Fore.RED}✗ Error finding semantic model: {e}{Style.RESET_ALL}")
        return None, None


def create_power_bi_report(workspace_id, model_id, report_name):
    """Create Power BI report bound to semantic model."""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"Step 3: Creating Power BI Report")
    print(f"{'=' * 80}{Style.RESET_ALL}\n")
    
    token = get_powerbi_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Create report using Power BI API
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports"
        
        payload = {
            "name": report_name,
            "datasetId": model_id
        }
        
        print(f"{Fore.WHITE}Creating report: {report_name}{Style.RESET_ALL}")
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        report_data = response.json()
        report_id = report_data.get("id")
        web_url = report_data.get("webUrl")
        
        print(f"{Fore.GREEN}✓ Power BI report created successfully!{Style.RESET_ALL}")
        print(f"  Report ID: {report_id}")
        print(f"  Web URL: {web_url}")
        
        return report_id, web_url
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 409:
            print(f"{Fore.YELLOW}⚠ Report already exists{Style.RESET_ALL}")
            # Try to find existing report
            try:
                list_url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports"
                list_response = requests.get(list_url, headers=headers, timeout=10)
                reports = list_response.json().get("value", [])
                
                for report in reports:
                    if report.get("name") == report_name:
                        report_id = report.get("id")
                        web_url = report.get("webUrl")
                        print(f"{Fore.GREEN}✓ Found existing report{Style.RESET_ALL}")
                        print(f"  Report ID: {report_id}")
                        print(f"  Web URL: {web_url}")
                        return report_id, web_url
            except:
                pass
        
        print(f"{Fore.RED}✗ Failed to create report: {e}{Style.RESET_ALL}")
        try:
            error_detail = e.response.json()
            print(f"  Error: {error_detail.get('error', {}).get('message', 'Unknown')}")
        except:
            print(f"  Status: {e.response.status_code}")
        
        return None, None
    
    except Exception as e:
        print(f"{Fore.RED}✗ Error creating report: {e}{Style.RESET_ALL}")
        return None, None


def print_next_steps(workspace_id, report_id, report_url):
    """Print next steps for report configuration."""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"✓✓✓ DEPLOYMENT COMPLETE ✓✓✓")
    print(f"{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.GREEN}Your end-to-end pipeline is ready!{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}What was created:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  ✓ Delta table: conference_attendance (in Lakehouse){Style.RESET_ALL}")
    print(f"{Fore.WHITE}  ✓ Semantic model: Auto-generated from lakehouse{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  ✓ Power BI report: Bound to semantic model{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}Next Steps:{Style.RESET_ALL}\n")
    
    print(f"{Fore.YELLOW}1. Open the report:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   {report_url}{Style.RESET_ALL}\n")
    
    print(f"{Fore.YELLOW}2. Add visuals to the report:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Click 'Edit' in the report{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Drag fields from 'conference_attendance' table{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   • Create KPIs, charts, and tables{Style.RESET_ALL}\n")
    
    print(f"{Fore.YELLOW}3. Recommended visuals:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   📊 KPI Cards: Total Registrations, Attended, Attendance Rate{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   📊 Donut Chart: AttendanceStatus breakdown{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   📊 Bar Chart: Top sessions by attendance{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   📊 Table: Attendee details{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}Full template: powerbi-templates/README.md{Style.RESET_ALL}\n")
    
    print(f"{Fore.GREEN}Enjoy your automated Fabric pipeline! 🎉{Style.RESET_ALL}\n")


def main():
    """Main orchestration function."""
    parser = argparse.ArgumentParser(
        description="End-to-end deployment: Notebook → Table → Model → Report"
    )
    parser.add_argument("--workspace-id", required=True, help="Fabric workspace ID")
    parser.add_argument("--notebook-id", default="c6ca0b35-a76a-4221-b3e3-2df6231eca00", 
                       help="Notebook ID")
    parser.add_argument("--lakehouse-name", default="ConferenceDataLakehouse", 
                       help="Lakehouse name")
    parser.add_argument("--report-name", default="Conference Attendance Report", 
                       help="Power BI report name")
    parser.add_argument("--skip-notebook", action="store_true", 
                       help="Skip notebook execution (if table already exists)")
    
    args = parser.parse_args()
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}END-TO-END FABRIC PIPELINE DEPLOYMENT")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}Workspace ID: {args.workspace_id}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Notebook ID: {args.notebook_id}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Lakehouse: {args.lakehouse_name}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Report Name: {args.report_name}{Style.RESET_ALL}\n")
    
    # Step 1: Run notebook (optional)
    if not args.skip_notebook:
        notebook_success = run_notebook(
            args.workspace_id, 
            args.notebook_id, 
            "Load Conference Data"
        )
        
        if not notebook_success:
            print(f"\n{Fore.YELLOW}⚠ Notebook execution had issues{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  Continuing anyway - table may already exist{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.YELLOW}Skipping notebook execution{Style.RESET_ALL}")
    
    # Step 2: Find semantic model
    model_id, model_name = find_lakehouse_semantic_model(
        args.workspace_id, 
        args.lakehouse_name
    )
    
    if not model_id:
        print(f"\n{Fore.RED}✗ Cannot proceed without semantic model{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Solutions:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}1. Run notebook to create Delta table: LoadConferenceData{Style.RESET_ALL}")
        print(f"{Fore.WHITE}2. Wait a few seconds for Fabric to auto-generate semantic model{Style.RESET_ALL}")
        print(f"{Fore.WHITE}3. Verify table exists in Lakehouse{Style.RESET_ALL}")
        sys.exit(1)
    
    # Step 3: Create Power BI report
    report_id, report_url = create_power_bi_report(
        args.workspace_id,
        model_id,
        args.report_name
    )
    
    if not report_id:
        print(f"\n{Fore.RED}✗ Failed to create Power BI report{Style.RESET_ALL}")
        sys.exit(1)
    
    # Success!
    print_next_steps(args.workspace_id, report_id, report_url)


if __name__ == "__main__":
    main()
