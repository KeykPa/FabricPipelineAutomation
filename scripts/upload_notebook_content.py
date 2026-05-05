#!/usr/bin/env python3
"""
Upload Notebook Content to Existing Fabric Notebook

This script uploads the content from a local .ipynb file to an existing Fabric notebook.
Use this to populate an empty notebook that was created via API.
"""

import sys
import os
import subprocess
import json
import base64
import argparse
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


def convert_ipynb_to_py(ipynb_content):
    """Convert Jupyter notebook JSON to Python script format."""
    try:
        notebook_json = json.loads(ipynb_content)
        cells = notebook_json.get('cells', [])
        
        py_content = []
        py_content.append("# Databricks notebook source\n")
        
        for i, cell in enumerate(cells):
            cell_type = cell.get('cell_type', 'code')
            source = cell.get('source', [])
            
            # Convert source to string
            if isinstance(source, list):
                source_text = ''.join(source)
            else:
                source_text = source
            
            if cell_type == 'markdown':
                py_content.append("\n# COMMAND ----------\n")
                py_content.append("# MAGIC %md\n")
                for line in source_text.split('\n'):
                    py_content.append(f"# MAGIC {line}\n")
            else:  # code cell
                py_content.append("\n# COMMAND ----------\n")
                py_content.append(source_text)
                if not source_text.endswith('\n'):
                    py_content.append('\n')
        
        return ''.join(py_content)
        
    except Exception as e:
        print(f"{Fore.RED}✗ Error converting notebook: {e}{Style.RESET_ALL}")
        return None


def upload_notebook_content(workspace_id, notebook_id, notebook_file_path):
    """Upload notebook content to Fabric."""
    print(f"\n{Fore.CYAN}Uploading notebook content...{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  Source file: {notebook_file_path}{Style.RESET_ALL}")
    
    if not os.path.exists(notebook_file_path):
        print(f"{Fore.RED}✗ Notebook file not found: {notebook_file_path}{Style.RESET_ALL}")
        return False
    
    token = get_fabric_token()
    if not token:
        print(f"{Fore.RED}✗ Failed to get authentication token{Style.RESET_ALL}")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Read notebook file
        with open(notebook_file_path, 'r', encoding='utf-8') as f:
            notebook_content = f.read()
        
        # Convert to Python script format
        print(f"{Fore.WHITE}  Converting notebook format...{Style.RESET_ALL}")
        py_content = convert_ipynb_to_py(notebook_content)
        
        if not py_content:
            return False
        
        # Encode to base64
        notebook_base64 = base64.b64encode(py_content.encode('utf-8')).decode('ascii')
        
        # Update notebook definition
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/updateDefinition"
        
        payload = {
            "definition": {
                "parts": [
                    {
                        "path": "notebook-content.py",
                        "payload": notebook_base64,
                        "payloadType": "InlineBase64"
                    }
                ]
            }
        }
        
        print(f"{Fore.WHITE}  Uploading to Fabric...{Style.RESET_ALL}")
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        print(f"{Fore.GREEN}✓ Notebook content uploaded successfully!{Style.RESET_ALL}")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to upload notebook content: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"\n{Fore.RED}Error details:{Style.RESET_ALL}")
                print(json.dumps(error_detail, indent=2))
            except:
                print(e.response.text)
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Upload notebook content to Fabric")
    parser.add_argument("--workspace-id", required=True, help="Fabric workspace ID")
    parser.add_argument("--notebook-id", required=True, help="Fabric notebook ID")
    parser.add_argument("--notebook-file", help="Path to .ipynb file (default: notebooks/load_conference_data.ipynb)")
    
    args = parser.parse_args()
    
    # Determine notebook file path
    if args.notebook_file:
        notebook_file = Path(args.notebook_file)
    else:
        script_dir = Path(__file__).parent
        notebook_file = script_dir.parent / "notebooks" / "load_conference_data.ipynb"
    
    if not notebook_file.exists():
        print(f"{Fore.RED}✗ Notebook file not found: {notebook_file}{Style.RESET_ALL}")
        sys.exit(1)
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Upload Notebook Content to Fabric")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}Workspace ID: {args.workspace_id}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Notebook ID: {args.notebook_id}{Style.RESET_ALL}")
    
    success = upload_notebook_content(args.workspace_id, args.notebook_id, str(notebook_file))
    
    if success:
        print(f"\n{Fore.CYAN}{'=' * 80}")
        print(f"{Fore.CYAN}Success!")
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
        
        print(f"{Fore.GREEN}✓ Notebook content uploaded{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}Next Steps:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}1. Open notebook in Fabric workspace{Style.RESET_ALL}")
        print(f"{Fore.WHITE}   https://app.fabric.microsoft.com/groups/{args.workspace_id}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}2. Verify all cells are present{Style.RESET_ALL}")
        print(f"{Fore.WHITE}3. Create storage shortcut in Lakehouse{Style.RESET_ALL}")
        print(f"{Fore.WHITE}4. Click 'Run all' to execute the notebook{Style.RESET_ALL}")
        print()
    else:
        print(f"\n{Fore.RED}✗ Upload failed{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
