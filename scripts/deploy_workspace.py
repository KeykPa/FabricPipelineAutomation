#!/usr/bin/env python3
"""
End-to-end Fabric workspace deployment.

For each enabled workspace in config/workspace-config.yaml:
  1. Cleanup (Git disconnect + delete items)
  2. Create Lakehouse
  3. Upload CSV to lakehouse Files
  4. Create Notebook (rebound to new lakehouse)
  5. Create DataPipeline (TridentNotebook activity)
  6. Run pipeline → Delta table created
  7. Refresh SQL endpoint + create DirectLake SemanticModel
  8. Create Report bound to SemanticModel

Then validates each workspace via DAX query.

Usage:
    python scripts/deploy_workspace.py
    python scripts/deploy_workspace.py --workspace-id <id>   # single workspace
"""

import argparse
import base64
import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

import requests
import yaml

try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    class _NoColor:
        def __getattr__(self, _): return ""
    Fore = Style = _NoColor()

# ---------- Constants ----------
API = "https://api.fabric.microsoft.com/v1"
ONELAKE = "https://onelake.dfs.fabric.microsoft.com"
PBI_API = "https://api.powerbi.com/v1.0/myorg"

ROOT = Path(__file__).parent.parent
CONFIG_FILE = ROOT / "config" / "workspace-config.yaml"
SOURCE_NOTEBOOK_PY = ROOT / "LoadConferenceData.Notebook" / "notebook-content.py"
SOURCE_CSV = ROOT / "sample-data" / "conference_attendance.csv"

LAKEHOUSE_NAME = "ConferenceDataLakehouse"
NOTEBOOK_NAME = "Load Conference Data"
PIPELINE_NAME = "ConferenceAttendanceDataPipeline"
SEMANTIC_MODEL_NAME = "ConferenceAttendanceSemanticModel"
REPORT_NAME = "AttendanceReport"
TABLE_NAME = "conference_attendance"

# Columns matching sample-data/conference_attendance.csv
TABLE_COLUMNS = [
    ("RegistrationID", "string"), ("FirstName", "string"), ("LastName", "string"),
    ("Email", "string"), ("Company", "string"), ("JobTitle", "string"),
    ("RegistrationDate", "string"), ("SessionName", "string"), ("SessionDate", "string"),
    ("SessionTime", "string"), ("AttendanceStatus", "string"), ("CheckInTime", "string"),
    ("CheckOutTime", "string"), ("SessionRating", "int64"), ("FeedbackComments", "string"),
]


# ---------- Auth ----------
def get_token(resource: str) -> str:
    r = subprocess.run(
        ['az', 'account', 'get-access-token', '--resource', resource],
        capture_output=True, text=True, shell=True
    )
    if r.returncode != 0:
        raise RuntimeError(f"az get-access-token failed: {r.stderr}")
    return json.loads(r.stdout)['accessToken']


def fab_headers():
    return {
        'Authorization': f'Bearer {get_token("https://api.fabric.microsoft.com")}',
        'Content-Type': 'application/json'
    }


def storage_headers():
    return {
        'Authorization': f'Bearer {get_token("https://storage.azure.com")}',
        'x-ms-version': '2023-01-03'
    }


def pbi_headers():
    return {
        'Authorization': f'Bearer {get_token("https://analysis.windows.net/powerbi/api")}',
        'Content-Type': 'application/json'
    }


# ---------- Helpers ----------
def b64(s: str) -> str:
    return base64.b64encode(s.encode('utf-8')).decode('utf-8')


def poll_lro(headers, location, label, timeout_steps=60):
    for i in range(timeout_steps):
        time.sleep(3)
        op = requests.get(location, headers=headers)
        if op.status_code != 200:
            continue
        data = op.json()
        status = data.get('status')
        print(f"  [{i*3}s] {label}: {status}")
        if status == 'Succeeded':
            result_url = op.headers.get('Location')
            if result_url:
                res = requests.get(result_url, headers=headers)
                if res.status_code == 200:
                    return res.json()
            return data
        if status in ('Failed', 'Cancelled'):
            print(f"{Fore.RED}    Failed: {op.text}{Style.RESET_ALL}")
            return None
    return None


def post_item_with_retry(ws_id, payload, label):
    """POST /items with retry for ItemDisplayNameNotAvailableYet."""
    h = fab_headers()
    url = f"{API}/workspaces/{ws_id}/items"
    for attempt in range(8):
        r = requests.post(url, headers=h, json=payload)
        if r.status_code == 201:
            return r.json()
        if r.status_code == 202:
            return poll_lro(h, r.headers.get('Location'), label)
        if 'ItemDisplayNameNotAvailableYet' in r.text or r.status_code == 409:
            print(f"  [{attempt+1}/8] {label} name not available yet, waiting 30s...")
            time.sleep(30)
            continue
        print(f"{Fore.RED}{label} create failed [{r.status_code}]: {r.text}{Style.RESET_ALL}")
        return None
    print(f"{Fore.RED}{label} create timed out{Style.RESET_ALL}")
    return None


# ---------- Step 1: Cleanup ----------
def disconnect_git(ws_id):
    h = fab_headers()
    r = requests.post(f"{API}/workspaces/{ws_id}/git/disconnect", headers=h)
    if r.status_code in (200, 204):
        print(f"  {Fore.GREEN}✓ Git disconnected{Style.RESET_ALL}")
    elif 'NotConnected' in r.text or r.status_code == 400:
        print(f"  Git: not connected")
    else:
        print(f"  Git disconnect status: {r.status_code}")


def delete_all_items(ws_id):
    h = fab_headers()
    items = requests.get(f"{API}/workspaces/{ws_id}/items", headers=h).json().get('value', [])
    order = {'Report': 0, 'SemanticModel': 1, 'DataPipeline': 2, 'Notebook': 3,
             'SQLEndpoint': 4, 'Lakehouse': 5}
    items.sort(key=lambda x: order.get(x['type'], 99))
    for it in items:
        if it['type'] == 'SQLEndpoint':
            continue  # auto-deleted with lakehouse
        r = requests.delete(f"{API}/workspaces/{ws_id}/items/{it['id']}", headers=h)
        c = Fore.GREEN if r.status_code in (200, 204) else Fore.RED
        print(f"  {c}[{r.status_code}] Deleted {it['type']}: {it['displayName']}{Style.RESET_ALL}")


# ---------- Step 2: Lakehouse ----------
def create_lakehouse(ws_id):
    h = fab_headers()
    payload = {"displayName": LAKEHOUSE_NAME, "description": "Conference data lakehouse"}
    for attempt in range(8):
        r = requests.post(f"{API}/workspaces/{ws_id}/lakehouses", headers=h, json=payload)
        if r.status_code == 201:
            return r.json()
        if r.status_code == 202:
            return poll_lro(h, r.headers.get('Location'), 'Lakehouse')
        if 'ItemDisplayNameNotAvailableYet' in r.text:
            print(f"  [{attempt+1}/8] Name not available, waiting 30s...")
            time.sleep(30)
            continue
        print(f"{Fore.RED}Lakehouse create failed: {r.text}{Style.RESET_ALL}")
        return None
    return None


# ---------- Step 3: Upload CSV ----------
def upload_csv_to_lakehouse(ws_id, lh_id):
    h = storage_headers()
    csv_data = SOURCE_CSV.read_bytes()
    file_path = "Files/conference-data/conference_attendance.csv"
    base = f"{ONELAKE}/{ws_id}/{lh_id}/{file_path}"

    r = requests.put(f"{base}?resource=file", headers=h)
    if r.status_code not in (200, 201):
        print(f"  {Fore.RED}Create file failed: {r.status_code} {r.text}{Style.RESET_ALL}")
        return False

    append_h = {**h, 'Content-Type': 'application/octet-stream'}
    r = requests.patch(f"{base}?action=append&position=0", headers=append_h, data=csv_data)
    if r.status_code not in (200, 202):
        print(f"  {Fore.RED}Append failed: {r.status_code} {r.text}{Style.RESET_ALL}")
        return False

    r = requests.patch(f"{base}?action=flush&position={len(csv_data)}", headers=h)
    if r.status_code not in (200, 202):
        print(f"  {Fore.RED}Flush failed: {r.status_code} {r.text}{Style.RESET_ALL}")
        return False

    print(f"  {Fore.GREEN}✓ Uploaded {len(csv_data):,} bytes{Style.RESET_ALL}")
    return True


# ---------- Step 4: Notebook ----------
def create_notebook(ws_id, lh_id):
    content = SOURCE_NOTEBOOK_PY.read_text(encoding='utf-8')
    content = re.sub(r'"default_lakehouse":\s*"[^"]+"',
                     f'"default_lakehouse": "{lh_id}"', content)
    content = re.sub(r'"default_lakehouse_name":\s*"[^"]+"',
                     f'"default_lakehouse_name": "{LAKEHOUSE_NAME}"', content)
    content = re.sub(r'"default_lakehouse_workspace_id":\s*"[^"]+"',
                     f'"default_lakehouse_workspace_id": "{ws_id}"', content)

    platform = json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Notebook", "displayName": NOTEBOOK_NAME},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid4())}
    })

    payload = {
        "displayName": NOTEBOOK_NAME, "type": "Notebook",
        "definition": {
            "format": "fabricGitSource",
            "parts": [
                {"path": "notebook-content.py", "payload": b64(content), "payloadType": "InlineBase64"},
                {"path": ".platform", "payload": b64(platform), "payloadType": "InlineBase64"},
            ]
        }
    }
    return post_item_with_retry(ws_id, payload, 'Notebook')


# ---------- Step 5: Pipeline ----------
def create_pipeline(ws_id, notebook_id):
    pipeline_def = {
        "properties": {
            "activities": [{
                "name": "RunLoadConferenceData",
                "type": "TridentNotebook",
                "typeProperties": {
                    "notebookId": notebook_id,
                    "workspaceId": ws_id,
                    "parameters": {}
                }
            }]
        }
    }
    platform = json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "DataPipeline", "displayName": PIPELINE_NAME},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid4())}
    })
    payload = {
        "displayName": PIPELINE_NAME, "type": "DataPipeline",
        "definition": {
            "parts": [
                {"path": "pipeline-content.json", "payload": b64(json.dumps(pipeline_def)), "payloadType": "InlineBase64"},
                {"path": ".platform", "payload": b64(platform), "payloadType": "InlineBase64"},
            ]
        }
    }
    return post_item_with_retry(ws_id, payload, 'Pipeline')


# ---------- Step 6: Run pipeline ----------
def run_pipeline(ws_id, pipeline_id):
    h = fab_headers()
    url = f"{API}/workspaces/{ws_id}/items/{pipeline_id}/jobs/instances?jobType=Pipeline"
    r = requests.post(url, headers=h, data="{}")
    if r.status_code != 202:
        print(f"  {Fore.RED}Run failed: {r.status_code} {r.text}{Style.RESET_ALL}")
        return False
    job_id = r.headers.get('Location').rstrip('/').split('/')[-1]
    print(f"  Job ID: {job_id}")
    status_url = f"{API}/workspaces/{ws_id}/items/{pipeline_id}/jobs/instances/{job_id}"
    for i in range(60):
        time.sleep(10)
        st = requests.get(status_url, headers=h).json()
        status = st.get('status')
        print(f"  [{(i+1)*10}s] {status}")
        if status == 'Completed':
            return True
        if status in ('Failed', 'Cancelled', 'Deduped'):
            print(f"  {Fore.RED}Pipeline {status}: {st.get('failureReason')}{Style.RESET_ALL}")
            return False
    return False


# ---------- Step 7: Semantic model ----------
def get_lakehouse(ws_id, lh_id):
    h = fab_headers()
    return requests.get(f"{API}/workspaces/{ws_id}/lakehouses/{lh_id}", headers=h).json()


def refresh_sql_endpoint(ws_id, lh_id):
    h = fab_headers()
    lh = get_lakehouse(ws_id, lh_id)
    sql_ep_id = lh['properties']['sqlEndpointProperties']['id']
    url = f"{API}/workspaces/{ws_id}/sqlEndpoints/{sql_ep_id}/refreshMetadata?preview=true"
    r = requests.post(url, headers=h, data="{}")
    if r.status_code in (200, 202):
        print(f"  {Fore.GREEN}✓ SQL endpoint metadata refreshed{Style.RESET_ALL}")
    return lh['properties']['sqlEndpointProperties']['connectionString']


def create_semantic_model(ws_id, sql_connection):
    bim_cols = []
    for name, dt in TABLE_COLUMNS:
        provider = "int" if dt == "int64" else "varchar(8000)"
        summarize = "sum" if dt == "int64" else "none"
        bim_cols.append({
            "name": name, "dataType": dt, "sourceColumn": name,
            "sourceProviderType": provider, "summarizeBy": summarize,
            "sourceLineageTag": name
        })

    model = {
        "name": SEMANTIC_MODEL_NAME, "compatibilityLevel": 1604,
        "model": {
            "culture": "en-US",
            "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "sourceQueryCulture": "en-US",
            "tables": [{
                "name": TABLE_NAME, "sourceLineageTag": f"[dbo].[{TABLE_NAME}]",
                "columns": bim_cols,
                "partitions": [{
                    "name": TABLE_NAME, "mode": "directLake",
                    "source": {"type": "entity", "entityName": TABLE_NAME,
                               "expressionSource": "DatabaseQuery", "schemaName": "dbo"}
                }]
            }],
            "expressions": [{
                "name": "DatabaseQuery", "kind": "m",
                "expression": ["let",
                               f'    database = Sql.Database("{sql_connection}", "{LAKEHOUSE_NAME}")',
                               "in", "    database"]
            }],
            "annotations": [{"name": "PBI_QueryOrder", "value": '["DatabaseQuery"]'}]
        }
    }
    pbism = {"version": "4.0", "settings": {}}
    platform = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": SEMANTIC_MODEL_NAME},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid4())}
    }
    payload = {
        "displayName": SEMANTIC_MODEL_NAME, "type": "SemanticModel",
        "definition": {
            "parts": [
                {"path": "model.bim", "payload": b64(json.dumps(model, indent=2)), "payloadType": "InlineBase64"},
                {"path": "definition.pbism", "payload": b64(json.dumps(pbism)), "payloadType": "InlineBase64"},
                {"path": ".platform", "payload": b64(json.dumps(platform)), "payloadType": "InlineBase64"},
            ]
        }
    }
    return post_item_with_retry(ws_id, payload, 'SemanticModel')


# ---------- Step 8: Report ----------
def create_report(ws_id, sm_id):
    layout = {
        "config": json.dumps({"version": "5.43", "themeCollection": {"baseTheme": {"name": "CY24SU10"}},
                              "activeSectionIndex": 0, "defaultDrillFilterOtherVisuals": True,
                              "linguisticSchemaSyncVersion": 0}),
        "layoutOptimization": 0, "publicCustomVisuals": [],
        "resourcePackages": [{"resourcePackage": {"disabled": False,
            "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": 202}],
            "name": "SharedResources", "type": 2}}],
        "sections": [{
            "name": "ReportSection", "displayName": "Overview", "displayOption": 1,
            "filters": "[]", "height": 720, "width": 1280, "config": "{}", "ordinal": 0,
            "visualContainers": [
                {"x": 20, "y": 20, "z": 0, "width": 1240, "height": 80,
                 "config": json.dumps({"name": "title",
                    "layouts": [{"id": 0, "position": {"x": 20, "y": 20, "z": 0, "width": 1240, "height": 80}}],
                    "singleVisual": {"visualType": "textbox", "drillFilterOtherVisuals": True,
                        "objects": {"general": [{"properties": {"paragraphs": [{
                            "textRuns": [{"value": "Conference Attendance Dashboard",
                                "textStyle": {"fontSize": "28pt", "fontWeight": "bold", "color": "#2C3E50"}}],
                            "horizontalTextAlignment": "center"}]}}]}}})},
                {"x": 20, "y": 120, "z": 1, "width": 280, "height": 140,
                 "config": json.dumps({"name": "card_total",
                    "layouts": [{"id": 0, "position": {"x": 20, "y": 120, "z": 1, "width": 280, "height": 140}}],
                    "singleVisual": {"visualType": "card",
                        "projections": {"Values": [{"queryRef": "Count of RegistrationID", "active": True}]},
                        "prototypeQuery": {"Version": 2,
                            "From": [{"Name": "c", "Entity": TABLE_NAME, "Type": 0}],
                            "Select": [{"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": "RegistrationID"}}, "Function": 2}, "Name": "Count of RegistrationID"}]},
                        "drillFilterOtherVisuals": True}})},
                {"x": 20, "y": 280, "z": 2, "width": 620, "height": 420,
                 "config": json.dumps({"name": "bar_company",
                    "layouts": [{"id": 0, "position": {"x": 20, "y": 280, "z": 2, "width": 620, "height": 420}}],
                    "singleVisual": {"visualType": "barChart",
                        "projections": {"Category": [{"queryRef": "Company", "active": True}],
                                        "Y": [{"queryRef": "Count of RegistrationID"}]},
                        "prototypeQuery": {"Version": 2,
                            "From": [{"Name": "c", "Entity": TABLE_NAME, "Type": 0}],
                            "Select": [
                                {"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": "Company"}, "Name": "Company"},
                                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": "RegistrationID"}}, "Function": 2}, "Name": "Count of RegistrationID"}],
                            "OrderBy": [{"Direction": 2, "Expression": {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": "RegistrationID"}}, "Function": 2}}}]},
                        "drillFilterOtherVisuals": True}})},
                {"x": 660, "y": 280, "z": 3, "width": 600, "height": 420,
                 "config": json.dumps({"name": "pie_status",
                    "layouts": [{"id": 0, "position": {"x": 660, "y": 280, "z": 3, "width": 600, "height": 420}}],
                    "singleVisual": {"visualType": "pieChart",
                        "projections": {"Category": [{"queryRef": "AttendanceStatus", "active": True}],
                                        "Y": [{"queryRef": "Count of RegistrationID"}]},
                        "prototypeQuery": {"Version": 2,
                            "From": [{"Name": "c", "Entity": TABLE_NAME, "Type": 0}],
                            "Select": [
                                {"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": "AttendanceStatus"}, "Name": "AttendanceStatus"},
                                {"Aggregation": {"Expression": {"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": "RegistrationID"}}, "Function": 2}, "Name": "Count of RegistrationID"}]},
                        "drillFilterOtherVisuals": True}})},
            ]
        }]
    }
    pbir = {
        "version": "4.0",
        "datasetReference": {"byPath": None,
            "byConnection": {"connectionString": None, "pbiServiceModelId": None,
                "pbiModelVirtualServerName": "sobe_wowvirtualserver",
                "pbiModelDatabaseName": sm_id, "name": "EntityDataSource",
                "connectionType": "pbiServiceXmlaStyleLive"}}
    }
    platform = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": REPORT_NAME},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid4())}
    }
    payload = {
        "displayName": REPORT_NAME, "type": "Report",
        "definition": {
            "parts": [
                {"path": "report.json", "payload": b64(json.dumps(layout)), "payloadType": "InlineBase64"},
                {"path": "definition.pbir", "payload": b64(json.dumps(pbir, indent=2)), "payloadType": "InlineBase64"},
                {"path": ".platform", "payload": b64(json.dumps(platform)), "payloadType": "InlineBase64"},
            ]
        }
    }
    return post_item_with_retry(ws_id, payload, 'Report')


# ---------- Validation ----------
def validate_workspace(ws_id, sm_id, ws_name):
    body = {"queries": [{"query": (
        "EVALUATE ROW("
        f"\"TotalRows\", COUNTROWS('{TABLE_NAME}'),"
        f"\"DistinctCompanies\", DISTINCTCOUNT('{TABLE_NAME}'[Company])"
        ")"
    )}], "serializerSettings": {"includeNulls": True}}
    try:
        r = requests.post(f"{PBI_API}/groups/{ws_id}/datasets/{sm_id}/executeQueries",
                          headers=pbi_headers(), json=body)
        if r.status_code == 200:
            row = r.json()['results'][0]['tables'][0]['rows'][0]
            print(f"  {Fore.GREEN}✓ {ws_name}: {row['[TotalRows]']} rows, "
                  f"{row['[DistinctCompanies]']} companies{Style.RESET_ALL}")
            return True
        print(f"  {Fore.RED}✗ {ws_name}: HTTP {r.status_code} {r.text}{Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"  {Fore.RED}✗ {ws_name}: {e}{Style.RESET_ALL}")
        return False


# ---------- Orchestration ----------
def deploy_workspace(ws):
    name, ws_id = ws['name'], ws['id']
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"WORKSPACE: {name}  [{ws_id}]")
    print(f"{'='*70}{Style.RESET_ALL}\n")

    print(f"{Fore.YELLOW}[1/8] Cleanup{Style.RESET_ALL}")
    disconnect_git(ws_id)
    delete_all_items(ws_id)
    print(f"  Waiting 15s for propagation...")
    time.sleep(15)

    print(f"\n{Fore.YELLOW}[2/8] Create Lakehouse{Style.RESET_ALL}")
    lh = create_lakehouse(ws_id)
    if not lh: return None
    lh_id = lh['id']
    print(f"  {Fore.GREEN}✓ {lh_id}{Style.RESET_ALL}")
    time.sleep(10)

    print(f"\n{Fore.YELLOW}[3/8] Upload CSV{Style.RESET_ALL}")
    if not upload_csv_to_lakehouse(ws_id, lh_id): return None

    print(f"\n{Fore.YELLOW}[4/8] Create Notebook{Style.RESET_ALL}")
    nb = create_notebook(ws_id, lh_id)
    if not nb: return None
    print(f"  {Fore.GREEN}✓ {nb['id']}{Style.RESET_ALL}")

    print(f"\n{Fore.YELLOW}[5/8] Create Pipeline{Style.RESET_ALL}")
    pl = create_pipeline(ws_id, nb['id'])
    if not pl: return None
    print(f"  {Fore.GREEN}✓ {pl['id']}{Style.RESET_ALL}")
    time.sleep(15)

    print(f"\n{Fore.YELLOW}[6/8] Run Pipeline{Style.RESET_ALL}")
    if not run_pipeline(ws_id, pl['id']): return None

    print(f"\n{Fore.YELLOW}[7/8] Refresh SQL endpoint + create SemanticModel{Style.RESET_ALL}")
    sql_conn = refresh_sql_endpoint(ws_id, lh_id)
    time.sleep(10)
    sm = create_semantic_model(ws_id, sql_conn)
    if not sm: return None
    print(f"  {Fore.GREEN}✓ {sm['id']}{Style.RESET_ALL}")
    time.sleep(15)

    print(f"\n{Fore.YELLOW}[8/8] Create Report{Style.RESET_ALL}")
    rpt = create_report(ws_id, sm['id'])
    if not rpt: return None
    print(f"  {Fore.GREEN}✓ {rpt['id']}{Style.RESET_ALL}")

    print(f"\n{Fore.GREEN}✓ {name} deployed{Style.RESET_ALL}")
    print(f"  https://app.powerbi.com/groups/{ws_id}")
    return {'lakehouse_id': lh_id, 'notebook_id': nb['id'], 'pipeline_id': pl['id'],
            'semantic_model_id': sm['id'], 'report_id': rpt['id']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace-id', help='Deploy single workspace')
    args = parser.parse_args()

    config = yaml.safe_load(CONFIG_FILE.read_text())
    workspaces = [w for w in config['workspaces'] if w.get('enabled', False)]
    if args.workspace_id:
        workspaces = [w for w in workspaces if w['id'] == args.workspace_id]

    if not workspaces:
        print(f"{Fore.RED}No enabled workspaces found in config{Style.RESET_ALL}")
        sys.exit(1)

    print(f"{Fore.CYAN}{'='*70}")
    print(f"DEPLOYING {len(workspaces)} workspace(s)")
    print(f"{'='*70}{Style.RESET_ALL}")

    results = {}
    for ws in workspaces:
        info = deploy_workspace(ws)
        results[ws['name']] = info

    print(f"\n{Fore.CYAN}{'='*70}")
    print("VALIDATION (DAX queries)")
    print(f"{'='*70}{Style.RESET_ALL}")
    for ws in workspaces:
        info = results.get(ws['name'])
        if info:
            validate_workspace(ws['id'], info['semantic_model_id'], ws['name'])

    print(f"\n{Fore.CYAN}{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}{Style.RESET_ALL}")
    for name, info in results.items():
        icon = f"{Fore.GREEN}✓" if info else f"{Fore.RED}✗"
        print(f"  {icon} {name}{Style.RESET_ALL}")


if __name__ == '__main__':
    main()
