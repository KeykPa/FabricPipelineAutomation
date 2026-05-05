#!/usr/bin/env python3
"""
Update Fabric Notebook Content - Correct Format

Uses the proper Fabric Items API format for updating notebook definitions.
"""

import sys
import subprocess
import json
import base64
from pathlib import Path

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
    print("Error: 'requests' required")
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


def convert_ipynb_to_fabric_format(ipynb_path):
    """Convert .ipynb to Fabric notebook JSON format."""
    with open(ipynb_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    cells = notebook.get('cells', [])
    
    # Convert to simple text format with cell markers
    output_lines = []
    
    for i, cell in enumerate(cells):
        cell_type = cell.get('cell_type', 'code')
        source = cell.get('source', [])
        
        # Join source lines
        if isinstance(source, list):
            content = ''.join(source)
        else:
            content = source
        
        # Add cell marker
        output_lines.append(f"# CELL {i+1} - {cell_type.upper()}\n")
        
        if cell_type == 'markdown':
            # Add markdown as comments
            for line in content.split('\n'):
                output_lines.append(f"# {line}\n")
        else:
            # Add code directly
            output_lines.append(content)
            if not content.endswith('\n'):
                output_lines.append('\n')
        
        output_lines.append('\n')
    
    return ''.join(output_lines)


def update_notebook_via_items_api(workspace_id, notebook_id, content):
    """Update notebook using Items API."""
    print(f"\n{Fore.CYAN}Updating notebook via Items API...{Style.RESET_ALL}")
    
    token = get_fabric_token()
    if not token:
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Encode content
        content_base64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
        
        # Use updateDefinition endpoint with correct format
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/items/{notebook_id}/updateDefinition"
        
        payload = {
            "definition": {
                "parts": [
                    {
                        "path": ".platform",
                        "payload": base64.b64encode(json.dumps({
                            "metadata": {
                                "type": "Notebook"
                            }
                        }).encode('utf-8')).decode('ascii'),
                        "payloadType": "InlineBase64"
                    },
                    {
                        "path": "notebook-content.py",
                        "payload": content_base64,
                        "payloadType": "InlineBase64"
                    }
                ]
            }
        }
        
        print(f"{Fore.WHITE}  Sending update request...{Style.RESET_ALL}")
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        print(f"{Fore.GREEN}✓ Notebook updated!{Style.RESET_ALL}")
        return True
        
    except Exception as e:
        print(f"{Fore.RED}✗ Update failed: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(json.dumps(e.response.json(), indent=2))
            except:
                print(e.response.text)
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Update Fabric notebook content")
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--notebook-id", required=True)
    parser.add_argument("--notebook-file", help="Path to .ipynb file")
    
    args = parser.parse_args()
    
    # Determine file path
    if args.notebook_file:
        notebook_file = Path(args.notebook_file)
    else:
        script_dir = Path(__file__).parent
        notebook_file = script_dir.parent / "notebooks" / "load_conference_data.ipynb"
    
    if not notebook_file.exists():
        print(f"{Fore.RED}✗ File not found: {notebook_file}{Style.RESET_ALL}")
        sys.exit(1)
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Update Fabric Notebook")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}Source: {notebook_file}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Workspace: {args.workspace_id}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Notebook: {args.notebook_id}{Style.RESET_ALL}")
    
    # Convert notebook
    print(f"\n{Fore.CYAN}Converting notebook format...{Style.RESET_ALL}")
    content = convert_ipynb_to_fabric_format(str(notebook_file))
    
    print(f"{Fore.WHITE}  Content length: {len(content)} characters{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  Preview (first 500 chars):{Style.RESET_ALL}")
    print("-" * 80)
    print(content[:500])
    print("-" * 80)
    
    # Update notebook
    success = update_notebook_via_items_api(args.workspace_id, args.notebook_id, content)
    
    if success:
        print(f"\n{Fore.GREEN}✓ Success! Refresh your browser to see the changes.{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}✗ Failed to update notebook{Style.RESET_ALL}")
        sys.exit(1)
