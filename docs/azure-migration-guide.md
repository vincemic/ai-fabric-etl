# Azure Migration Guide

## 📋 Table of Contents

1. [Migration Overview](#migration-overview)
2. [Pre-Migration Planning](#pre-migration-planning)
3. [Infrastructure Mapping](#infrastructure-mapping)
4. [Data Migration Strategy](#data-migration-strategy)
5. [Code Adaptation](#code-adaptation)
6. [Security and Compliance](#security-and-compliance)
7. [Testing Strategy](#testing-strategy)
8. [Deployment Process](#deployment-process)
9. [Post-Migration Validation](#post-migration-validation)
10. [Rollback Planning](#rollback-planning)

## 🚀 Migration Overview

This guide provides a comprehensive roadmap for migrating your local X12 EDI processing environment to Azure, leveraging Azure's native services while maintaining functionality and improving scalability.

### Migration Goals

- **Scalability**: Handle larger volumes of X12 transactions
- **Reliability**: 99.9% uptime with Azure SLA
- **Security**: Enterprise-grade security and compliance
- **Cost Optimization**: Pay-as-you-use pricing model
- **Monitoring**: Advanced analytics and observability

### Migration Timeline

**Estimated Duration**: 4-6 weeks for complete migration

| Phase | Duration | Activities |
|-------|----------|------------|
| Planning & Assessment | 1 week | Infrastructure audit, cost estimation, team training |
| Infrastructure Setup | 1-2 weeks | Azure resources provisioning, networking, security |
| Data Migration | 1 week | Historical data transfer, testing |
| Application Migration | 1-2 weeks | Code adaptation, deployment, testing |
| Go-Live & Optimization | 1 week | Production deployment, monitoring, tuning |

## 📊 Pre-Migration Planning

### Assessment Checklist

**Current Environment Audit**:
```powershell
# Document current resource usage
docker stats --no-stream > migration-baseline.txt

# Catalog data volumes
Get-ChildItem -Recurse local-development\processed | Measure-Object -Property Length -Sum

# Export configuration
docker-compose config > current-config.yml
```

**Business Requirements**:
- [ ] Expected transaction volume (monthly/daily)
- [ ] Performance requirements (processing time SLAs)
- [ ] Compliance requirements (HIPAA, SOX, etc.)
- [ ] High availability needs
- [ ] Disaster recovery requirements
- [ ] Budget constraints

### Cost Estimation

**Use Azure Pricing Calculator** for:
- Azure Data Factory (pipeline runs)
- Azure SQL Database (performance tier)
- Azure Data Lake Storage Gen2 (storage volume)
- Azure Databricks (compute units)
- Azure Monitor (log ingestion)

**Estimated Monthly Costs** (example for 10K transactions/month):
```
Azure Data Factory: $150-300
Azure SQL Database (Standard S2): $75
Azure Data Lake Storage: $20-50
Azure Databricks (Standard): $200-400
Azure Monitor: $30-60
Total: $475-885/month
```

### Team Preparation

**Skills Development**:
- Azure fundamentals training
- Azure Data Factory pipeline development
- Azure SQL Database management
- Infrastructure as Code (Bicep/ARM)
- Azure monitoring and troubleshooting

## 🏗️ Infrastructure Mapping

### Service Mapping Matrix

| Local Component | Azure Service | Purpose | Migration Complexity |
|----------------|---------------|---------|-------------------|
| Docker Compose | Azure Container Instances | Orchestration | Medium |
| MinIO | Azure Data Lake Storage Gen2 | Object Storage | Low |
| PostgreSQL | Azure SQL Database | Relational Data | Medium |
| Apache Airflow | Azure Data Factory | Pipeline Orchestration | High |
| Jupyter Lab | Azure Databricks | Analytics & Development | Medium |
| Redis | Azure Cache for Redis | In-Memory Cache | Low |

### Architecture Comparison

**Local Architecture**:
```
Docker Host
├── MinIO (Object Storage)
├── PostgreSQL (RDBMS)
├── Airflow (Orchestration)
├── Jupyter (Analytics)
└── Redis (Cache)
```

**Azure Architecture**:
```
Azure Resource Group
├── Data Lake Storage Gen2 (Object Storage)
├── Azure SQL Database (RDBMS) 
├── Data Factory (Orchestration)
├── Databricks Workspace (Analytics)
├── Cache for Redis (Cache)
├── Key Vault (Secrets)
├── Application Insights (Monitoring)
└── Log Analytics Workspace (Logs)
```

### Network Architecture

**Azure Networking Setup**:
```
Virtual Network (VNet)
├── Data Subnet (private)
│   ├── SQL Database
│   └── Storage Account
├── Compute Subnet (private)
│   ├── Databricks
│   └── Data Factory IR
└── Management Subnet (public)
    └── Azure Bastion
```

## 💾 Data Migration Strategy

### Data Classification

**Data Categories**:
1. **Historical X12 Files** (Bronze Layer)
   - Source: `local-development/processed/input/`
   - Target: Azure Data Lake Storage Gen2 container `bronze-x12-raw`
   - Method: AzCopy bulk transfer

2. **Processed Transactions** (Silver Layer)
   - Source: PostgreSQL `silver_transactions` table
   - Target: Azure SQL Database
   - Method: Database migration tools

3. **Analytics Data** (Gold Layer)
   - Source: PostgreSQL analytics tables
   - Target: Azure SQL Database + Databricks Delta Tables
   - Method: Hybrid approach

### Migration Methods

#### 1. File Data Migration

**Azure Data Lake Storage Gen2 Setup**:
```powershell
# Create storage account
az storage account create `
  --name x12storage$random `
  --resource-group rg-x12-processing `
  --location eastus2 `
  --sku Standard_LRS `
  --kind StorageV2 `
  --hierarchical-namespace true

# Create containers
az storage container create --name bronze-x12-raw --account-name x12storage$random
az storage container create --name silver-x12-parsed --account-name x12storage$random
az storage container create --name gold-x12-analytics --account-name x12storage$random
```

**Bulk Data Transfer**:
```powershell
# Install AzCopy
winget install Microsoft.AzCopy

# Transfer historical files
azcopy copy "local-development\processed\*" "https://x12storage.blob.core.windows.net/bronze-x12-raw/" --recursive
```

#### 2. Database Migration

**Azure SQL Database Setup**:
```sql
-- Create database
az sql db create `
  --server x12-sql-server `
  --name x12-data `
  --resource-group rg-x12-processing `
  --edition Standard `
  --capacity 20
```

**Schema Migration**:
```powershell
# Export current schema
docker exec x12-data-db pg_dump -U x12user -s x12_data > schema-export.sql

# Convert PostgreSQL to SQL Server syntax (manual process)
# Use Azure Database Migration Service for automated conversion
```

**Data Migration with Azure Database Migration Service**:
```powershell
# Create migration project
az dms project create `
  --service-name x12-migration-service `
  --resource-group rg-x12-processing `
  --name x12-db-migration `
  --source-platform PostgreSQL `
  --target-platform AzureSqlDatabase
```

### Zero-Downtime Migration Strategy

**Phase 1: Setup Parallel Environment**
1. Deploy Azure infrastructure
2. Set up data replication
3. Configure monitoring

**Phase 2: Incremental Sync**
1. Initial bulk data transfer
2. Set up change data capture
3. Continuous replication

**Phase 3: Cutover**
1. Stop local processing
2. Final sync
3. Switch traffic to Azure
4. Validate operations

## 💻 Code Adaptation

### Airflow to Azure Data Factory Migration

**Pipeline Conversion Strategy**:

**Current Airflow DAG**:
```python
@dag(
    'x12_processing_pipeline',
    start_date=pendulum.now(),
    schedule_interval='*/5 * * * *'
)
def x12_processing():
    check_files = PythonOperator(
        task_id='check_for_x12_files',
        python_callable=check_for_x12_files
    )
```

**Azure Data Factory Pipeline**:
```json
{
  "name": "X12ProcessingPipeline",
  "properties": {
    "activities": [
      {
        "name": "CheckForX12Files",
        "type": "GetMetadata",
        "linkedServiceName": {
          "referenceName": "AzureDataLakeStorage",
          "type": "LinkedServiceReference"
        },
        "typeProperties": {
          "dataset": {
            "referenceName": "X12InputFiles",
            "type": "DatasetReference"
          },
          "fieldList": ["childItems", "lastModified"]
        }
      }
    ],
    "triggers": [
      {
        "name": "ScheduledTrigger", 
        "type": "ScheduleTrigger",
        "typeProperties": {
          "recurrence": {
            "frequency": "Minute",
            "interval": 5
          }
        }
      }
    ]
  }
}
```

### Configuration Management

**Azure Key Vault Integration**:
```python
# Replace environment variables with Key Vault references
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://x12-keyvault.vault.azure.net/", credential=credential)

# Instead of os.environ.get('DATABASE_URL')
database_url = client.get_secret("database-connection-string").value
```

### Jupyter to Databricks Migration

**Notebook Conversion**:
```python
# Add to beginning of Databricks notebooks
import pyspark.sql.functions as F
from pyspark.sql.types import *

# Replace pandas with Spark DataFrames
# pandas: df = pd.read_json('file.json')
df = spark.read.json('/mnt/silver-x12-parsed/transactions.json')

# Replace file I/O with Databricks File System
# Local: with open('file.txt', 'r') as f:
dbutils.fs.cp('file://file.txt', '/tmp/file.txt')
with open('/tmp/file.txt', 'r') as f:
    content = f.read()
```

### Application Configurations

**Connection String Updates**:
```python
# Local configuration
LOCAL_CONFIG = {
    'database_url': 'postgresql://x12user:password@localhost:5433/x12_data',
    'storage_url': 'http://localhost:9000',
    'redis_url': 'redis://localhost:6379'
}

# Azure configuration
AZURE_CONFIG = {
    'database_url': 'Server=x12-sql-server.database.windows.net;Database=x12_data;Authentication=Active Directory Managed Identity',
    'storage_url': 'https://x12storage.blob.core.windows.net',
    'redis_url': 'x12cache.redis.cache.windows.net:6380,ssl=True'
}
```

## 🔐 Security and Compliance

### Identity and Access Management

**Azure Active Directory Setup**:
```powershell
# Create service principal for Data Factory
az ad sp create-for-rbac --name "X12DataFactoryPrincipal" --role Contributor

# Assign permissions to storage
az role assignment create `
  --assignee "X12DataFactoryPrincipal" `
  --role "Storage Blob Data Contributor" `
  --scope "/subscriptions/{subscription-id}/resourceGroups/rg-x12-processing"
```

**Managed Identity Configuration**:
```powershell
# Enable managed identity for Data Factory
az datafactory factory identity assign `
  --factory-name x12-data-factory `
  --resource-group rg-x12-processing

# Grant SQL access to managed identity
az sql server ad-admin set `
  --server x12-sql-server `
  --resource-group rg-x12-processing `
  --display-name "X12DataFactory" `
  --object-id {managed-identity-object-id}
```

### Network Security

**Private Endpoints**:
```powershell
# Create private endpoint for SQL Database
az network private-endpoint create `
  --name pe-x12-sql `
  --resource-group rg-x12-processing `
  --vnet-name vnet-x12 `
  --subnet data-subnet `
  --private-connection-resource-id "/subscriptions/{sub}/resourceGroups/rg-x12-processing/providers/Microsoft.Sql/servers/x12-sql-server" `
  --group-id sqlServer `
  --connection-name sql-connection
```

**Network Security Groups**:
```powershell
# Create NSG rules
az network nsg rule create `
  --nsg-name nsg-x12-data `
  --resource-group rg-x12-processing `
  --name AllowSQLFromCompute `
  --priority 100 `
  --source-address-prefixes "10.0.2.0/24" `
  --destination-port-ranges "1433" `
  --access Allow `
  --protocol Tcp
```

### Data Encryption

**Encryption Configuration**:
- **At Rest**: Azure Storage encryption (automatic)
- **In Transit**: TLS 1.2 for all connections
- **Processing**: Transparent Data Encryption (TDE) for SQL Database

**Key Management**:
```powershell
# Create Key Vault
az keyvault create `
  --name x12-keyvault `
  --resource-group rg-x12-processing `
  --location eastus2 `
  --enable-soft-delete true `
  --enable-purge-protection true

# Store sensitive configuration
az keyvault secret set `
  --vault-name x12-keyvault `
  --name "DatabaseConnectionString" `
  --value "Server=x12-sql-server.database.windows.net;Database=x12_data;Authentication=Active Directory Managed Identity"
```

## 🧪 Testing Strategy

### Test Environment Setup

**Staging Environment**:
```powershell
# Deploy staging infrastructure
az deployment group create `
  --resource-group rg-x12-staging `
  --template-file infra/main.bicep `
  --parameters environment=staging
```

### Testing Phases

#### 1. Unit Testing
```python
# Test X12 parsing functions
import pytest
from x12_parser import parse_x12_file

def test_x12_parsing():
    sample_x12 = "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *230101*1200*^*00501*000000001*0*P*:~"
    result = parse_x12_file(sample_x12)
    assert result['interchange_control_number'] == '000000001'
```

#### 2. Integration Testing
```python
# Test end-to-end pipeline
def test_pipeline_integration():
    # Upload test file to Azure storage
    upload_test_file('test_x12_837.x12')
    
    # Trigger Data Factory pipeline
    trigger_pipeline('X12ProcessingPipeline')
    
    # Validate processing results
    results = query_sql_database('SELECT * FROM silver_transactions WHERE source_filename = ?', 'test_x12_837.x12')
    assert len(results) > 0
```

#### 3. Performance Testing
```python
# Load testing with Azure Load Testing
test_config = {
    'virtual_users': 50,
    'duration': '10m',
    'ramp_up': '2m',
    'test_files': ['large_x12_batch.x12']
}
```

#### 4. Disaster Recovery Testing
```powershell
# Test backup restoration
az sql db restore `
  --dest-name x12-data-restored `
  --server x12-sql-server `
  --resource-group rg-x12-processing `
  --source-database x12-data `
  --time "2024-01-15T10:00:00Z"
```

## 🚀 Deployment Process

### Infrastructure Deployment

**Automated Deployment with Bicep**:
```powershell
# Deploy infrastructure
az deployment group create `
  --resource-group rg-x12-processing `
  --template-file infra/main.bicep `
  --parameters @infra/main.parameters.json

# Verify deployment
az deployment group show `
  --resource-group rg-x12-processing `
  --name main `
  --query "properties.provisioningState"
```

### Application Deployment

**Azure Data Factory Deployment**:
```powershell
# Deploy Data Factory pipelines
az datafactory pipeline create `
  --factory-name x12-data-factory `
  --resource-group rg-x12-processing `
  --name X12ProcessingPipeline `
  --pipeline @pipelines/x12-processing-pipeline.json
```

**Databricks Workspace Setup**:
```python
# Deploy notebooks using Databricks CLI
databricks workspace import_dir notebooks/ /Shared/X12Processing/ --language python --overwrite
```

### Configuration Deployment

**Key Vault Secrets**:
```powershell
# Deploy secrets from local configuration
$secrets = @{
    'DatabaseConnectionString' = 'Server=x12-sql-server.database.windows.net;Database=x12_data;Authentication=Active Directory Managed Identity'
    'StorageAccountKey' = (az storage account keys list --account-name x12storage --query '[0].value' --output tsv)
}

foreach ($secret in $secrets.GetEnumerator()) {
    az keyvault secret set --vault-name x12-keyvault --name $secret.Key --value $secret.Value
}
```

## ✅ Post-Migration Validation

### Functional Validation

**Data Integrity Checks**:
```sql
-- Validate record counts
SELECT 
    'bronze_x12' as table_name,
    COUNT(*) as record_count,
    MIN(ingestion_timestamp) as earliest_record,
    MAX(ingestion_timestamp) as latest_record
FROM bronze_x12
UNION ALL
SELECT 
    'silver_transactions',
    COUNT(*),
    MIN(parsing_timestamp),
    MAX(parsing_timestamp)
FROM silver_transactions;

-- Validate data quality
SELECT 
    transaction_type,
    AVG(quality_score) as avg_quality,
    COUNT(*) as transaction_count
FROM silver_transactions
GROUP BY transaction_type;
```

### Performance Validation

**Benchmark Testing**:
```powershell
# Measure processing time for standard batch
$startTime = Get-Date
# Trigger pipeline with test batch
$endTime = Get-Date
$processingTime = $endTime - $startTime
Write-Host "Processing time: $($processingTime.TotalMinutes) minutes"
```

### Monitoring Setup

**Azure Monitor Configuration**:
```powershell
# Create log analytics workspace
az monitor log-analytics workspace create `
  --workspace-name x12-logs `
  --resource-group rg-x12-processing `
  --location eastus2

# Configure diagnostic settings
az monitor diagnostic-settings create `
  --name x12-factory-diagnostics `
  --resource "/subscriptions/{sub}/resourceGroups/rg-x12-processing/providers/Microsoft.DataFactory/factories/x12-data-factory" `
  --workspace "/subscriptions/{sub}/resourceGroups/rg-x12-processing/providers/Microsoft.OperationalInsights/workspaces/x12-logs" `
  --logs '[{"category":"PipelineRuns","enabled":true}]'
```

### Alert Configuration

**Critical Alerts**:
```powershell
# Pipeline failure alert
az monitor metrics alert create `
  --name "X12 Pipeline Failures" `
  --resource-group rg-x12-processing `
  --scopes "/subscriptions/{sub}/resourceGroups/rg-x12-processing/providers/Microsoft.DataFactory/factories/x12-data-factory" `
  --condition "count ActivityFailedRuns > 0" `
  --action-group "/subscriptions/{sub}/resourceGroups/rg-x12-processing/providers/Microsoft.Insights/actionGroups/x12-alerts"
```

## 🔄 Rollback Planning

### Rollback Triggers

**Conditions for Rollback**:
- Data processing failures > 5%
- Performance degradation > 50%
- Critical security incidents
- System unavailability > 30 minutes

### Rollback Procedures

#### 1. Traffic Rollback
```powershell
# Redirect traffic back to local environment
# Update DNS or load balancer configuration
# Disable Azure Data Factory triggers
az datafactory trigger stop --factory-name x12-data-factory --resource-group rg-x12-processing --name ScheduledTrigger
```

#### 2. Data Rollback
```powershell
# Restore local database from backup
docker exec x12-data-db psql -U x12user x12_data < "backups/pre-migration-backup.sql"

# Sync missing data from Azure
azcopy copy "https://x12storage.blob.core.windows.net/bronze-x12-raw/*" "local-development/processed/input/" --recursive
```

#### 3. Application Rollback
```powershell
# Restart local environment
docker-compose up -d

# Verify all services
.\setup-local-dev.ps1 -SkipSetup
```

### Rollback Validation

**Post-Rollback Checks**:
- [ ] All local services running
- [ ] Data integrity verified
- [ ] Processing pipeline functional
- [ ] Performance restored
- [ ] Team notifications sent

This migration guide provides a structured approach to moving your X12 processing environment to Azure while minimizing risk and ensuring business continuity.