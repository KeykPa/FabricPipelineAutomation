#!/usr/bin/env python3
"""List all Fabric workspaces"""

import subprocess
import json

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
    print("Error: requests required")
    exit(1)


def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except:
        return None


def get_fabric_token():
    return run_command(
        "az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv"
    )


token = get_fabric_token()
if not token:
    print(f"{Fore.RED}✗ Failed to get token{Style.RESET_ALL}")
    exit(1)

headers = {"Authorization": f"Bearer {token}"}

print(f"\n{Fore.CYAN}Listing all Fabric workspaces:{Style.RESET_ALL}\n")

try:
    url = "https://api.powerbi.com/v1.0/myorg/groups"
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    workspaces = response.json().get("value", [])
    
    print(f"{Fore.GREEN}Found {len(workspaces)} workspaces:{Style.RESET_ALL}\n")
    
    for ws in workspaces:
        name = ws.get("name")
        ws_id = ws.get("id")
        capacity_id = ws.get("capacityId", "None")
        is_on_dedicated = ws.get("isOnDedicatedCapacity", False)
        
        print(f"{Fore.WHITE}Name: {name}{Style.RESET_ALL}")
        print(f"  ID: {ws_id}")
        print(f"  Capacity: {capacity_id}")
        print(f"  Dedicated: {is_on_dedicated}")
        print()
        
except Exception as e:
    print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")
