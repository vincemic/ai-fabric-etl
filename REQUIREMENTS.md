# Azure Fabric X12 ETL Pipeline Requirements

## Azure Services Required
- Azure Storage Account (Gen2)
- Azure Data Factory
- Azure Key Vault  
- Azure Fabric Workspace
- Azure Databricks (for notebook execution)
- Azure Application Insights (for monitoring)
- Azure Log Analytics Workspace

## Azure CLI Tools
- Azure CLI (latest version)
- Azure Developer CLI (azd)

## PowerShell Modules
- Az PowerShell Module
- Azure PowerShell

## Permissions Required
- Contributor role on target Resource Group
- Storage Blob Data Contributor on Storage Account
- Key Vault Secrets User on Key Vault
- Data Factory Contributor on Data Factory

## Optional Components
- Power BI (for dashboards)
- Azure Monitor (for alerting)
- Azure Private Endpoints (for network security)