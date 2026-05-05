# Terraform configuration for Fabric Lakehouse automation
# This uses the Azure Fabric provider to create resources via ARM APIs

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~> 1.0"
    }
  }
}

provider "azurerm" {
  features {}
}

provider "azapi" {
}

variable "workspace_id" {
  description = "Fabric Workspace ID"
  type        = string
  default     = "00bcfcd2-97d8-48b0-8ae4-67e7395ac373"
}

variable "lakehouse_name" {
  description = "Name of the Lakehouse"
  type        = string
  default     = "ConferenceDataLakehouse"
}

variable "storage_account_name" {
  description = "Storage account for data"
  type        = string
  default     = "westusattendiesstore"
}

# Attempt to create Lakehouse via Azure API
# Note: This may also fail if the tenant doesn't support Fabric Data Engineering
resource "azapi_resource" "lakehouse" {
  type      = "Microsoft.Fabric/workspaces/lakehouses@2023-11-01"
  name      = var.lakehouse_name
  parent_id = "/providers/Microsoft.Fabric/workspaces/${var.workspace_id}"

  body = jsonencode({
    properties = {
      displayName = var.lakehouse_name
      description = "Lakehouse for conference attendance data - Created via Terraform"
    }
  })

  lifecycle {
    ignore_changes = [
      body
    ]
  }
}

output "lakehouse_id" {
  value       = azapi_resource.lakehouse.id
  description = "The ID of the created Lakehouse"
}

output "instructions" {
  value = <<-EOT
    
    Lakehouse created: ${var.lakehouse_name}
    
    Next steps:
    1. Create storage shortcut in Fabric UI
    2. Create notebook
    3. Run data load pipeline
    
  EOT
}
