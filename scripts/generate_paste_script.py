#!/usr/bin/env python3
"""Generate a simple Python script from the notebook that can be manually pasted"""

import json
import sys
from pathlib import Path

# Set UTF-8 encoding for stdout
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Read the notebook
notebook_path = Path(__file__).parent.parent / "notebooks" / "load_conference_data.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

print("=" * 80)
print("PASTE THIS INTO YOUR FABRIC NOTEBOOK")
print("=" * 80)
print()
print("Instructions:")
print("1. Open: https://app.fabric.microsoft.com/groups/07fafa98-29b0-49a0-9464-a80f2f6af2e2")
print("2. Click 'Load Conference Data' notebook")
print("3. Delete the empty cell if present")
print("4. Copy ALL the code below (Ctrl+A, Ctrl+C)")
print("5. In Fabric: Click '+ Code' button")
print("6. Paste (Ctrl+V)")
print("7. Click 'Run all'")
print()
print("=" * 80)
print()

# Generate single Python script
for i, cell in enumerate(nb.get('cells', []), 1):
    cell_type = cell.get('cell_type')
    source = cell.get('source', [])
    
    # Convert source to text
    if isinstance(source, list):
        content = ''.join(source)
    else:
        content = source
    
    if cell_type == 'markdown':
        # Convert markdown to commented Python
        print(f"# {'=' * 76}")
        for line in content.split('\n'):
            if line.strip():
                print(f"# {line}")
        print(f"# {'=' * 76}")
        print()
    
    elif cell_type == 'code':
        # Add code with separator comment
        print(f"# CELL {i} - CODE")
        print(content.rstrip())
        print()
        print()

print("# END OF NOTEBOOK")
print("# Run all cells above")
