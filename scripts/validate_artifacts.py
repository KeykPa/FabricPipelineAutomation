#!/usr/bin/env python3
"""Validate notebook and artifacts before deployment"""

import json
import os
from pathlib import Path

def validate_notebook():
    """Validate notebook has content and all cells."""
    notebook_path = Path("notebooks/load_conference_data.ipynb")
    
    if not notebook_path.exists():
        print("❌ Notebook file not found!")
        return False
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    cells = nb.get('cells', [])
    
    if len(cells) == 0:
        print("❌ Notebook is empty (0 cells)")
        return False
    
    print(f"✓ Notebook has {len(cells)} cells")
    
    # Check for code cells
    code_cells = [c for c in cells if c.get('cell_type') == 'code']
    markdown_cells = [c for c in cells if c.get('cell_type') == 'markdown']
    
    print(f"  - Code cells: {len(code_cells)}")
    print(f"  - Markdown cells: {len(markdown_cells)}")
    
    # Verify cells have content
    empty_cells = 0
    for i, cell in enumerate(cells, 1):
        source = cell.get('source', [])
        if isinstance(source, list):
            content = ''.join(source)
        else:
            content = source
        
        if not content.strip():
            empty_cells += 1
            print(f"  ⚠ Cell {i} is empty")
    
    if empty_cells > 0:
        print(f"  ⚠ Found {empty_cells} empty cells")
    
    # Check expected content
    all_content = json.dumps(nb)
    expected_keywords = [
        'westusattendiesstore',
        'conference-data',
        'abfss://',
        'spark.read',
        'Delta',
        'saveAsTable'
    ]
    
    missing = []
    for keyword in expected_keywords:
        if keyword not in all_content:
            missing.append(keyword)
    
    if missing:
        print(f"  ⚠ Missing expected keywords: {', '.join(missing)}")
        return False
    
    print("  ✓ All expected content found")
    return True


def validate_sample_data():
    """Validate sample data files exist."""
    csv_file = Path("sample-data/conference_attendance.csv")
    json_file = Path("sample-data/conference_attendance.json")
    
    if not csv_file.exists():
        print("❌ CSV sample data not found")
        return False
    
    if not json_file.exists():
        print("❌ JSON sample data not found")
        return False
    
    csv_size = csv_file.stat().st_size
    json_size = json_file.stat().st_size
    
    print(f"✓ Sample data files exist")
    print(f"  - CSV: {csv_size:,} bytes")
    print(f"  - JSON: {json_size:,} bytes")
    
    return True


def validate_powerbi_templates():
    """Check for Power BI templates."""
    template_file = Path("powerbi-templates/attendance-report-template.json")
    
    if template_file.exists():
        size = template_file.stat().st_size
        print(f"✓ Power BI template exists ({size:,} bytes)")
        return True
    else:
        print("⚠ Power BI template not found (will be created during deployment)")
        return True  # Not critical


def validate_scripts():
    """Validate deployment scripts exist."""
    required_scripts = [
        "scripts/setup_azure_resources.py",
        "scripts/fix_and_deploy.py",
        "scripts/deploy_with_gitops.py",
        "scripts/cleanup_all.py",
        "scripts/create_powerbi_report.py"
    ]
    
    all_exist = True
    for script in required_scripts:
        if not Path(script).exists():
            print(f"❌ Missing: {script}")
            all_exist = False
    
    if all_exist:
        print(f"✓ All {len(required_scripts)} deployment scripts present")
    
    return all_exist


def main():
    """Main validation."""
    print("\n" + "="*80)
    print("Artifact Validation for GitHub Deployment")
    print("="*80 + "\n")
    
    results = []
    
    print("1. Validating Notebook...")
    results.append(("Notebook", validate_notebook()))
    print()
    
    print("2. Validating Sample Data...")
    results.append(("Sample Data", validate_sample_data()))
    print()
    
    print("3. Validating Power BI Templates...")
    results.append(("Power BI", validate_powerbi_templates()))
    print()
    
    print("4. Validating Scripts...")
    results.append(("Scripts", validate_scripts()))
    print()
    
    # Summary
    print("="*80)
    print("Validation Summary")
    print("="*80 + "\n")
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status:8} {name}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        print("✓ All validations passed! Ready for deployment.")
        return 0
    else:
        print("❌ Some validations failed. Please fix before deploying.")
        return 1


if __name__ == "__main__":
    exit(main())
