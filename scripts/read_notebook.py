#!/usr/bin/env python3
"""
Read Notebook Content from Fabric

This script downloads and displays the content of a Fabric notebook to verify what's actually stored.
"""

import sys
import subprocess
import json
import base64

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


def get_notebook_definition(workspace_id, notebook_id):
    """Read notebook definition from Fabric."""
    print(f"\n{Fore.CYAN}Reading notebook from Fabric...{Style.RESET_ALL}")
    
    token = get_fabric_token()
    if not token:
        return None
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Get notebook definition
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{workspace_id}/notebooks/{notebook_id}/getDefinition"
        
        response = requests.post(url, headers=headers, json={}, timeout=30)
        response.raise_for_status()
        
        definition = response.json()
        
        print(f"{Fore.GREEN}✓ Definition retrieved{Style.RESET_ALL}")
        print(f"\n{Fore.WHITE}Full response:{Style.RESET_ALL}")
        print(json.dumps(definition, indent=2))
        
        # Extract parts
        parts = definition.get("definition", {}).get("parts", []) if definition else []
        
        if not parts:
            print(f"{Fore.YELLOW}⚠ Notebook has no content parts{Style.RESET_ALL}")
            return None
        
        print(f"\n{Fore.CYAN}Notebook Parts:{Style.RESET_ALL}")
        for part in parts:
            path = part.get("path", "unknown")
            payload_type = part.get("payloadType", "unknown")
            print(f"  • {path} ({payload_type})")
            
            if payload_type == "InlineBase64":
                payload = part.get("payload", "")
                if payload:
                    try:
                        content = base64.b64decode(payload).decode('utf-8')
                        lines = content.split('\n')
                        print(f"\n{Fore.WHITE}Content Preview (first 30 lines):{Style.RESET_ALL}")
                        print("=" * 80)
                        for i, line in enumerate(lines[:30], 1):
                            print(f"{i:3d} | {line}")
                        if len(lines) > 30:
                            print(f"... ({len(lines) - 30} more lines)")
                        print("=" * 80)
                        
                        return content
                    except Exception as e:
                        print(f"{Fore.RED}✗ Error decoding content: {e}{Style.RESET_ALL}")
        
        return None
        
    except Exception as e:
        print(f"{Fore.RED}✗ Failed to read notebook: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(json.dumps(e.response.json(), indent=2))
            except:
                print(e.response.text)
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Read notebook content from Fabric")
    parser.add_argument("--workspace-id", required=True, help="Workspace ID")
    parser.add_argument("--notebook-id", required=True, help="Notebook ID")
    
    args = parser.parse_args()
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Read Notebook from Fabric")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    
    print(f"\n{Fore.WHITE}Workspace: {args.workspace_id}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Notebook: {args.notebook_id}{Style.RESET_ALL}")
    
    content = get_notebook_definition(args.workspace_id, args.notebook_id)
    
    if content:
        print(f"\n{Fore.GREEN}✓ Notebook has content!{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.YELLOW}⚠ Notebook appears to be empty{Style.RESET_ALL}")
