# Power BI Report Management

## Why No PBIX File?

We use **API-based report creation** instead of storing PBIX files in GitHub because:

1. **PBIX files are binary** - not version-control friendly
2. **JSON templates are better for GitOps** - readable, diffable, mergeable
3. **Automated deployment** - script creates report from semantic model
4. **No manual downloads** - everything via API

## What We Have

- **JSON Template**: `attendance-report-template.json`
  - Report structure and page layouts
  - Can be version controlled
  - Used by `create_powerbi_report.py`

- **Creation Script**: `scripts/create_powerbi_report.py`
  - Finds Lakehouse semantic model
  - Creates blank report
  - Applies template (if provided)

## How It Works

### 1. Notebook Creates Semantic Model
When you run the `Load Conference Data` notebook:
- Delta table `conference_attendance` is created
- Fabric automatically creates a semantic model (Direct Lake mode)
- Model name: `ConferenceDataLakehouse` (same as Lakehouse)

### 2. Script Creates Report
```bash
python scripts/create_powerbi_report.py --workspace-id <workspace-id>
```

This:
- Finds the semantic model
- Creates a new report
- Links to the model
- Returns the report URL

### 3. Manual Customization
In Power BI Service:
- Add visuals (charts, tables, cards)
- Create pages
- Apply filters
- Publish

## Why This Approach?

✅ **GitOps Friendly**: All code in version control  
✅ **Automated**: No manual PBIX uploads  
✅ **Consistent**: Same process every time  
✅ **Team Friendly**: No binary file conflicts  

## Alternative: Manual PBIX Creation

If you prefer Power BI Desktop:

1. Open Power BI Desktop
2. Get Data → Power BI datasets
3. Select `ConferenceDataLakehouse`
4. Create visuals
5. Save as `.pbix`
6. Publish to workspace

**Note**: PBIX files are not recommended for version control.

## Future: Report Definition API

Microsoft is developing APIs for full report definitions. When available, we can:
- Export complete report layouts as JSON
- Version control everything
- Fully automated report deployment

For now, we use:
- Automated report creation (script)
- Manual visual customization (UI)
- Template reference (JSON guide)
