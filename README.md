# Fabric Pipeline Automation

End-to-end automation that deploys an entire Microsoft Fabric data stack
(Lakehouse → Notebook → DataPipeline → DirectLake Semantic Model → Report)
into multiple workspaces using only the Fabric REST API and Azure CLI tokens.

> See [ARCHITECTURE.md](ARCHITECTURE.md) for the deployment flow diagram and a
> comparison of the approaches that were tested.

---

## What it deploys (per workspace)

| Artifact | Name |
|---|---|
| Lakehouse | `ConferenceDataLakehouse` |
| Notebook | `Load Conference Data` |
| Data Pipeline | `ConferenceAttendanceDataPipeline` |
| Semantic Model (DirectLake) | `ConferenceAttendanceSemanticModel` |
| Report | `AttendanceReport` |
| Delta table | `Tables/conference_attendance` |

The pipeline runs the notebook, which reads
`Files/conference-data/conference_attendance.csv` and writes the Delta table.

---

## Prerequisites

* Python 3.10+
* Azure CLI (`az login` against the Fabric tenant)
* Three pre-existing Fabric workspaces assigned to a Fabric capacity. IDs go
  into `config/workspace-config.yaml`.

```powershell
pip install -r requirements.txt
az login
```

---

## Project layout

```
config/workspace-config.yaml         # Workspace IDs + artifact names
sample-data/conference_attendance.csv# Source CSV (15 columns, 25 rows)
LoadConferenceData.Notebook/
    notebook-content.py              # Source PySpark notebook
scripts/
    deploy_workspace.py              # Main: 8-step end-to-end deploy
    rename_workspaces.py             # PATCH workspace display names
    cleanup_all.py                   # Delete all items in a workspace
    setup_azure_resources.py         # Optional: create Azure storage
    upload_to_blob.py                # Optional: stage CSV in blob
terraform/                           # Optional Azure infra-as-code
ARCHITECTURE.md                      # Diagrams + approach comparison
```

---

## Usage

### Deploy everything (all enabled workspaces)
```powershell
python scripts\deploy_workspace.py
```

### Deploy a single workspace
```powershell
python scripts\deploy_workspace.py --workspace-id <guid>
```

### Apply a different prefix to all workspaces
```powershell
python scripts\rename_workspaces.py --prefix "PROD"
```

### Clean up a workspace
```powershell
python scripts\cleanup_all.py --workspace-id <guid>
```

---

## How it works (high level)

For each enabled workspace, `deploy_workspace.py` runs an idempotent 8-step
flow. See [ARCHITECTURE.md](ARCHITECTURE.md#end-to-end-deployment-flow) for
the full diagram.

1. **Cleanup** — disconnect Git, delete existing items in dependency order
2. **Lakehouse** — create + retry on `ItemDisplayNameNotAvailableYet`
3. **CSV upload** — OneLake DFS API (`PUT/PATCH append/PATCH flush`)
4. **Notebook** — `format=fabricGitSource`; metadata regex-rebound to new lakehouse
5. **Pipeline** — `TridentNotebook` activity wrapping the notebook
6. **Run pipeline** — `POST .../jobs/instances?jobType=Pipeline` then poll
7. **Semantic model** — refresh SQL endpoint metadata, then create `mode: directLake` model
8. **Report** — bound `byConnection` to the semantic model (3 visuals)

After all workspaces deploy, a DAX `EVALUATE ROW(COUNTROWS, DISTINCTCOUNT)` is
issued against each via the Power BI `executeQueries` API for validation.

---

## Authentication

Uses Azure CLI delegated tokens — **no service principals or client secrets.**

```
az account get-access-token --resource https://api.fabric.microsoft.com
az account get-access-token --resource https://storage.azure.com
az account get-access-token --resource https://analysis.windows.net/powerbi/api
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ItemDisplayNameNotAvailableYet` after delete | Already handled with 8× 30s retries |
| Semantic model created but DAX returns `ProcessFull` error | Check `expressionSource: "DatabaseQuery"` and the M expression points to right SQL connection |
| Report shows blank visuals | Confirm Delta table exists (`refreshMetadata` call must run after pipeline finishes) |
| `0-byte notebook` after upload | Verify `format=fabricGitSource` (not `ipynb`) and call `getDefinition` to confirm |

More background in [ARCHITECTURE.md](ARCHITECTURE.md#key-lessons-learned).
