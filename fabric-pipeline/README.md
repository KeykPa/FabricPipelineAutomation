# Fabric Pipeline Configuration

This folder contains the Microsoft Fabric pipeline definitions and related configurations.

## Files

### pipeline-definition.json
Main pipeline definition that orchestrates the data flow from Azure Blob Storage to Lakehouse.

**Key Activities:**
1. **CopyBlobToLakehouse**: Copies data from blob storage to lakehouse table
2. **ValidateDataLoad**: Validates the data load was successful

**Parameters:**
- `SourceFileName`: Name of the file in blob storage (default: conference_attendance.csv)
- `TargetTableName`: Name of the target table in Lakehouse (default: conference_attendance)

### dataset-blob-source.json
Dataset definition for the Azure Blob Storage source containing the CSV files.

**Configuration:**
- Container: `conference-data`
- Format: Delimited Text (CSV)
- First row as header: Yes

### dataset-lakehouse-destination.json
Dataset definition for the Fabric Lakehouse destination table.

**Schema:**
- 15 columns matching the conference attendance data structure
- Includes data type mappings for proper conversion

## Deployment

### Prerequisites
1. Azure Blob Storage account with connection string
2. Fabric workspace with Lakehouse created
3. Appropriate permissions to create and run pipelines

### Manual Deployment

1. **Create Linked Services:**
   - Azure Blob Storage linked service named `AzureBlobStorageLinkedService`
   - Fabric Lakehouse linked service named `FabricLakehouseLinkedService`

2. **Import Pipeline:**
   - Navigate to your Fabric workspace
   - Go to Data Factory > Pipelines
   - Click "New" > "Import from pipeline definition"
   - Upload `pipeline-definition.json`

3. **Create Datasets:**
   - Import `dataset-blob-source.json` as a new dataset
   - Import `dataset-lakehouse-destination.json` as a new dataset

4. **Configure Connections:**
   - Update linked service references to match your environment
   - Set appropriate authentication methods

### Automated Deployment

Use the provided PowerShell script:

```powershell
.\scripts\deploy-pipeline.ps1 `
    -WorkspaceId "<your-workspace-id>" `
    -PipelinePath ".\fabric-pipeline\pipeline-definition.json"
```

## Pipeline Triggers

### Scheduled Trigger
Run the pipeline on a schedule (e.g., daily):

```json
{
  "name": "DailySchedule",
  "properties": {
    "type": "ScheduleTrigger",
    "typeProperties": {
      "recurrence": {
        "frequency": "Day",
        "interval": 1,
        "startTime": "2026-05-01T06:00:00Z",
        "timeZone": "UTC"
      }
    },
    "pipelines": [
      {
        "pipelineReference": {
          "referenceName": "ConferenceAttendanceDataPipeline",
          "type": "PipelineReference"
        },
        "parameters": {}
      }
    ]
  }
}
```

### Event-based Trigger
Trigger when a new file is uploaded to blob storage:

```json
{
  "name": "BlobEventTrigger",
  "properties": {
    "type": "BlobEventsTrigger",
    "typeProperties": {
      "blobPathBeginsWith": "/conference-data/blobs/",
      "blobPathEndsWith": ".csv",
      "ignoreEmptyBlobs": true,
      "events": [
        "Microsoft.Storage.BlobCreated"
      ]
    },
    "pipelines": [
      {
        "pipelineReference": {
          "referenceName": "ConferenceAttendanceDataPipeline",
          "type": "PipelineReference"
        },
        "parameters": {}
      }
    ]
  }
}
```

## Monitoring

### Activity Runs
Monitor pipeline execution in Fabric:
1. Navigate to your pipeline
2. Click "Monitor" tab
3. View activity runs and their status

### Logs
Pipeline logs include:
- Copy activity details (rows read, rows written)
- Validation query results
- Error messages if any activity fails

### Alerts
Set up alerts for:
- Pipeline failures
- Long-running executions
- Data validation errors

## Troubleshooting

### Common Issues

**Issue: Copy activity fails with authentication error**
- Solution: Verify blob storage connection string and permissions

**Issue: Data not appearing in Lakehouse**
- Solution: Check table name matches parameter, verify lakehouse permissions

**Issue: Schema mismatch errors**
- Solution: Ensure CSV columns match expected schema, check data types

## Extending the Pipeline

### Add Data Transformation
Insert a Data Flow activity between copy and validation:

```json
{
  "name": "TransformData",
  "type": "DataFlow",
  "dependsOn": [
    {
      "activity": "CopyBlobToLakehouse",
      "dependencyConditions": ["Succeeded"]
    }
  ],
  "typeProperties": {
    "dataFlow": {
      "referenceName": "ConferenceDataTransform",
      "type": "DataFlowReference"
    }
  }
}
```

### Add Data Quality Checks
Add script activities to validate data quality:
- Check for null values in required fields
- Validate email formats
- Verify date ranges
- Detect duplicate registrations

### Handle Multiple File Formats
Use ForEach activity to process both CSV and JSON files:

```json
{
  "name": "ForEachFile",
  "type": "ForEach",
  "typeProperties": {
    "items": {
      "value": "@pipeline().parameters.FileList",
      "type": "Expression"
    },
    "activities": [
      // Copy activity here
    ]
  }
}
```
