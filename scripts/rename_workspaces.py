#!/usr/bin/env python3
"""
Rename Fabric workspaces by adding/replacing a prefix.
Updates workspace-config.yaml in place with the new names.

Usage:
    python scripts/rename_workspaces.py --prefix "GIZ"
"""

import argparse
import json
import subprocess
from pathlib import Path

import requests
import yaml

API = "https://api.fabric.microsoft.com/v1"
ROOT = Path(__file__).parent.parent
CONFIG_FILE = ROOT / "config" / "workspace-config.yaml"


def get_token():
    r = subprocess.run(
        ['az', 'account', 'get-access-token', '--resource', 'https://api.fabric.microsoft.com'],
        capture_output=True, text=True, shell=True
    )
    return json.loads(r.stdout)['accessToken']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', required=True, help='Prefix to apply (e.g. "GIZ")')
    args = parser.parse_args()

    headers = {'Authorization': f'Bearer {get_token()}', 'Content-Type': 'application/json'}
    config = yaml.safe_load(CONFIG_FILE.read_text())

    for ws in config['workspaces']:
        ws_id = ws.get('id')
        if not ws_id:
            print(f"  Skip (no id): {ws['name']}")
            continue

        # Strip any existing single-word prefix
        parts = ws['name'].split(' ', 1)
        base = parts[1] if len(parts) > 1 and len(parts[0]) <= 5 and parts[0].isupper() else ws['name']
        new_name = f"{args.prefix} {base}"

        print(f"  {ws['name']} → {new_name}")
        r = requests.patch(f"{API}/workspaces/{ws_id}", headers=headers,
                           json={"displayName": new_name})
        if r.status_code in (200, 204):
            ws['name'] = new_name
            print(f"    ✓ Renamed")
        else:
            print(f"    ✗ HTTP {r.status_code}: {r.text}")

    CONFIG_FILE.write_text(yaml.safe_dump(config, sort_keys=False))
    print(f"\n✓ Config updated: {CONFIG_FILE}")


if __name__ == '__main__':
    main()
