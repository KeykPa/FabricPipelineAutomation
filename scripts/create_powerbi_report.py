#!/usr/bin/env python3
"""
Create Power BI Report from Lakehouse (Simplified)

This script creates a Power BI report using the Lakehouse's built-in semantic model.
Much simpler approach that works with Fabric's automatic semantic model creation.
"""

import sys
import subprocess
import json
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
    except subprocess.CalledProcessError:
        return None


def get_fabric_token():
    """Get Fabric API token."""
    return run_command(
        "az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv"
    )


def list_workspace_items(workspace_id):
    """List all items in workspace."""
    print(f"\n{Fore.CYAN}Listing workspace items...{Style.RESET_ALL}")
    
    token = get_fabric_token()
    if not token:
        return []
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        items = response.json().get("value", [])
        
        print(f"{Fore.GREEN}✓ Found {len(items)} items{Style.RESET_ALL}")
        
        for item in items:
            item_type = item.get("type")
            name = item.get("displayName")
            item_id = item.get("id")
            print(f"  {item_type:20s} {name:40s} {item_id}")
        
        return items
        
    except Exception as e:
        print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
        return []


def find_lakehouse_semantic_model(workspace_id, lakehouse_name):
    """Find the default semantic model created by Lakehouse."""
    print(f"\n{Fore.CYAN}Finding semantic model for lakehouse...{Style.RESET_ALL}")
    
    items = list_workspace_items(workspace_id)
    
    # Lakehouse creates a default semantic model with the same name
    for item in items:
        if item.get("type") == "SemanticModel":
            display_name = item.get("displayName")
            if lakehouse_name in display_name or display_name.endswith("(default)"):
                model_id = item.get("id")
                print(f"{Fore.GREEN}✓ Found semantic model: {display_name}{Style.RESET_ALL}")
                print(f"  ID: {model_id}")
                return model_id, display_name
    
    print(f"{Fore.YELLOW}⚠ No default semantic model found{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  Tip: Load data into Lakehouse table first to auto-create semantic model{Style.RESET_ALL}")
    return None, None


def create_report_in_workspace(workspace_id, model_id, report_name):
    """Create blank Power BI report bound to semantic model."""
    print(f"\n{Fore.CYAN}Creating report: {report_name}{Style.RESET_ALL}")
    
    token = get_fabric_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Use Power BI REST API to create report
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
        print(f"  ID: {report_id}")
        print(f"  URL: {web_url}")
        
        return report_id, web_url
        
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to create report: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error = e.response.json()
                print(f"  Error: {error.get('error', {}).get('message', 'Unknown error')}")
            except:
                print(f"  Status: {e.response.status_code}")
        return None, None


def print_report_instructions(workspace_id, report_id):
    """Print instructions for configuring the report."""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Report Configuration Instructions")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.YELLOW}The report has been created but is currently blank.{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Follow these steps to add visuals:{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}Option 1: Edit in Power BI Service (Web){Style.RESET_ALL}")
    print(f"{Fore.WHITE}1. Open report: https://app.powerbi.com/groups/{workspace_id}/reports/{report_id}/ReportSection{Style.RESET_ALL}")
    print(f"{Fore.WHITE}2. Click 'Edit' button{Style.RESET_ALL}")
    print(f"{Fore.WHITE}3. Add visuals from the Visualizations pane{Style.RESET_ALL}")
    print(f"{Fore.WHITE}4. Drag fields from conference_attendance table{Style.RESET_ALL}")
    print(f"{Fore.WHITE}5. Save changes{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}Option 2: Download and Edit in Power BI Desktop{Style.RESET_ALL}")
    print(f"{Fore.WHITE}1. In Power BI Service, click '...' → 'Download this file' → '.pbix'{Style.RESET_ALL}")
    print(f"{Fore.WHITE}2. Open .pbix in Power BI Desktop{Style.RESET_ALL}")
    print(f"{Fore.WHITE}3. Add visuals (see template: powerbi-templates/README.md){Style.RESET_ALL}")
    print(f"{Fore.WHITE}4. Publish back to workspace{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}Recommended Visuals (from template):{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}Page 1 - Overview:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Card: COUNT(RegistrationID) - Total Registrations{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Card: COUNT(RegistrationID) WHERE AttendanceStatus='Attended'{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Card: Attendance Rate (DAX: DIVIDE([Attended], [Total], 0)){Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Donut Chart: AttendanceStatus by COUNT(RegistrationID){Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Bar Chart: SessionName by COUNT(RegistrationID){Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}Page 2 - Attendee List:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Table: FirstName, LastName, Email, Company, JobTitle, SessionName, AttendanceStatus, SessionRating{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}Page 3 - Session Analytics:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Matrix: SessionName with Registrations, Attended, Attendance%, AvgRating{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  • Treemap: Company by COUNT(RegistrationID){Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}Full template reference: powerbi-templates/README.md{Style.RESET_ALL}\n")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Create Power BI report from Lakehouse")
    parser.add_argument("--workspace-id", required=True, help="Fabric workspace ID")
    parser.add_argument("--lakehouse-name", default="ConferenceDataLakehouse", help="Lakehouse name")
    parser.add_argument("--report-name", default="Conference Attendance Report", help="Report name")
    
    args = parser.parse_args()
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Power BI Report Creation")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    # Step 1: Find semantic model
    model_id, model_name = find_lakehouse_semantic_model(args.workspace_id, args.lakehouse_name)
    
    if not model_id:
        print(f"\n{Fore.RED}✗ Cannot create report without semantic model{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Solution:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}1. Ensure data is loaded into Lakehouse tables{Style.RESET_ALL}")
        print(f"{Fore.WHITE}2. Lakehouse automatically creates a semantic model{Style.RESET_ALL}")
        print(f"{Fore.WHITE}3. Re-run this script{Style.RESET_ALL}")
        sys.exit(1)
    
    # Step 2: Create report
    report_id, web_url = create_report_in_workspace(args.workspace_id, model_id, args.report_name)
    
    if not report_id:
        print(f"\n{Fore.RED}✗ Report creation failed{Style.RESET_ALL}")
        sys.exit(1)
    
    # Step 3: Show configuration instructions
    print_report_instructions(args.workspace_id, report_id)
    
    # Summary
    print(f"{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Deployment Complete")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.GREEN}✓ Report created successfully!{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  Report ID: {report_id}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  Workspace: https://app.powerbi.com/groups/{args.workspace_id}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  Direct Link: {web_url}{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}Next: Add visuals using the web editor or Power BI Desktop{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()
