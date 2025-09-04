# Operations and Management Guide

## 📋 Table of Contents

1. [Environment Management](#environment-management)
2. [Service Operations](#service-operations)
3. [Data Management](#data-management)
4. [Monitoring and Alerting](#monitoring-and-alerting)
5. [Backup and Recovery](#backup-and-recovery)
6. [Performance Tuning](#performance-tuning)
7. [Troubleshooting](#troubleshooting)
8. [Migration to Azure](#migration-to-azure)

## 🔧 Environment Management

### Starting the Environment

#### Quick Start
```powershell
# Navigate to project directory
cd C:\tmp\ai-fabric-etl

# Start all services
.\setup-local-dev.ps1
```

#### Manual Startup
```powershell
# Navigate to local development directory
cd local-development

# Start services in background
docker-compose up -d

# Start services with logs visible
docker-compose up

# Start specific services
docker-compose up -d minio postgres redis
```

### Stopping the Environment

```powershell
# Stop all services (preserves data)
docker-compose down

# Stop and remove volumes (DESTROYS DATA)
docker-compose down -v

# Stop and remove images
docker-compose down --rmi all

# Force stop all containers
docker-compose kill
```

### Environment Health Checks

```powershell
# Check all service status
docker-compose ps

# Check specific service logs
docker-compose logs airflow-webserver
docker-compose logs -f postgres

# Health check script
.\scripts\health-check.ps1
```

### Configuration Management

#### Environment Variables
Edit `local-development\.env`:
```bash
# Storage Configuration
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123

# Database Configuration
POSTGRES_HOST=data-postgres
POSTGRES_PORT=5432
POSTGRES_DB=x12_data
POSTGRES_USER=x12user
POSTGRES_PASSWORD=x12password

# Processing Configuration
BATCH_SIZE=100
MAX_FILE_SIZE_MB=50
PROCESSING_TIMEOUT_MINUTES=30
```

#### Service Configuration
- **Airflow**: `local-development/airflow/config/`
- **PostgreSQL**: Environment variables in docker-compose.yml
- **MinIO**: Environment variables in docker-compose.yml

## 🎛️ Service Operations

### Airflow Operations

#### DAG Management
```powershell
# List all DAGs
docker exec airflow-webserver airflow dags list

# Enable/disable DAG
docker exec airflow-webserver airflow dags pause x12_processing_pipeline
docker exec airflow-webserver airflow dags unpause x12_processing_pipeline

# Trigger DAG manually
docker exec airflow-webserver airflow dags trigger x12_processing_pipeline

# Check DAG status
docker exec airflow-webserver airflow dags state x12_processing_pipeline 2025-09-04
```

#### Task Management
```powershell
# List tasks for a DAG
docker exec airflow-webserver airflow tasks list x12_processing_pipeline

# Check task instance status
docker exec airflow-webserver airflow tasks state x12_processing_pipeline bronze_processing 2025-09-04

# Clear task instance (rerun)
docker exec airflow-webserver airflow tasks clear x12_processing_pipeline -t bronze_processing
```

#### User Management
```powershell
# Create admin user
docker exec airflow-webserver airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin

# List users
docker exec airflow-webserver airflow users list

# Delete user
docker exec airflow-webserver airflow users delete --username testuser
```

### MinIO Operations

#### Bucket Management
```powershell
# Access MinIO console: http://localhost:9001

# CLI operations using mc (MinIO Client)
docker exec minio mc alias set local http://localhost:9000 minioadmin minioadmin123

# List buckets
docker exec minio mc ls local

# Create bucket
docker exec minio mc mb local/new-bucket

# Copy files
docker exec minio mc cp /data/file.x12 local/bronze-x12-raw/

# Set bucket policy
docker exec minio mc policy set public local/bronze-x12-raw
```

#### Storage Management
```powershell
# Check storage usage
docker exec minio mc admin info local

# Set lifecycle policy
docker exec minio mc ilm add local/archive-x12 \
  --expiry-days 90 \
  --transition-days 30 \
  --storage-class COLD
```

### PostgreSQL Operations

#### Database Management
```powershell
# Connect to database
docker exec -it x12-data-db psql -U x12user -d x12_data

# Backup database
docker exec x12-data-db pg_dump -U x12user x12_data > backup_$(date +%Y%m%d).sql

# Restore database
docker exec -i x12-data-db psql -U x12user x12_data < backup_20250904.sql

# Check database size
docker exec x12-data-db psql -U x12user -d x12_data -c "
SELECT 
  pg_size_pretty(pg_database_size('x12_data')) as database_size,
  pg_size_pretty(pg_total_relation_size('silver_transactions')) as transactions_size;
"
```

#### Table Maintenance
```sql
-- Inside psql session
-- Analyze tables for query optimization
ANALYZE silver_transactions;
ANALYZE gold_transaction_summary;

-- Vacuum tables to reclaim space
VACUUM ANALYZE bronze_x12;

-- Check table sizes
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Jupyter Operations

#### Notebook Management
```powershell
# Get Jupyter access token
docker logs jupyter 2>&1 | findstr "token="

# Access Jupyter Lab: http://localhost:8888

# Install additional packages
docker exec jupyter pip install package-name

# Restart Jupyter service
docker-compose restart jupyter
```

## 💾 Data Management

### File Processing Workflow

#### Input Data Management
```powershell
# Input directory structure
local-development/
└── processed/
    ├── input/          # Drop X12 files here
    ├── bronze/         # Raw file metadata
    ├── silver/         # Parsed transactions
    ├── gold/           # Business analytics
    └── archive/        # Processed files
```

#### Processing Status Check
```sql
-- Check recent processing activity
SELECT 
  filename,
  status,
  processing_timestamp,
  file_size
FROM bronze_x12 
WHERE processing_timestamp >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY processing_timestamp DESC;

-- Check processing quality
SELECT 
  transaction_type,
  COUNT(*) as file_count,
  AVG(quality_score) as avg_quality,
  MIN(quality_score) as min_quality,
  MAX(quality_score) as max_quality
FROM silver_transactions
WHERE parsing_timestamp >= CURRENT_DATE
GROUP BY transaction_type;
```

### Data Retention Management

#### Automated Cleanup
```sql
-- Clean old bronze records (90+ days)
DELETE FROM bronze_x12 
WHERE processing_timestamp < CURRENT_DATE - INTERVAL '90 days';

-- Archive old silver transactions
INSERT INTO silver_transactions_archive 
SELECT * FROM silver_transactions 
WHERE parsing_timestamp < CURRENT_DATE - INTERVAL '1 year';

DELETE FROM silver_transactions 
WHERE parsing_timestamp < CURRENT_DATE - INTERVAL '1 year';
```

#### Manual Data Export
```powershell
# Export data for analysis
docker exec x12-data-db psql -U x12user -d x12_data -c "
COPY (
  SELECT * FROM gold_transaction_summary 
  WHERE processing_date >= '2025-09-01'
) TO STDOUT WITH CSV HEADER;" > transaction_summary.csv
```

## 📊 Monitoring and Alerting

### Service Health Monitoring

#### Automated Health Checks
```powershell
# Create health check script
# File: scripts/health-check.ps1

# Check Airflow
$airflowHealth = Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing
if ($airflowHealth.StatusCode -eq 200) {
    Write-Host "✅ Airflow is healthy"
} else {
    Write-Host "❌ Airflow is down"
}

# Check MinIO
$minioHealth = Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -UseBasicParsing
if ($minioHealth.StatusCode -eq 200) {
    Write-Host "✅ MinIO is healthy"
} else {
    Write-Host "❌ MinIO is down"
}

# Check PostgreSQL
$postgresCheck = docker exec x12-data-db pg_isready -U x12user
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ PostgreSQL is healthy"
} else {
    Write-Host "❌ PostgreSQL is down"
}
```

#### Performance Monitoring
```sql
-- Database performance metrics
SELECT 
  schemaname,
  tablename,
  n_tup_ins as inserts,
  n_tup_upd as updates,
  n_tup_del as deletes,
  n_tup_hot_upd as hot_updates,
  n_live_tup as live_tuples,
  n_dead_tup as dead_tuples
FROM pg_stat_user_tables
ORDER BY n_tup_ins DESC;

-- Query performance
SELECT 
  query,
  calls,
  total_time,
  mean_time,
  rows
FROM pg_stat_statements
WHERE query LIKE '%x12%'
ORDER BY total_time DESC
LIMIT 10;
```

### Processing Monitoring

#### Daily Processing Reports
```sql
-- Daily processing summary
SELECT 
  DATE(processing_timestamp) as processing_date,
  COUNT(*) as files_processed,
  COUNT(CASE WHEN status = 'validated' THEN 1 END) as successful_files,
  COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_files,
  AVG(file_size) as avg_file_size,
  SUM(file_size) as total_data_processed
FROM bronze_x12 
WHERE processing_timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(processing_timestamp)
ORDER BY processing_date DESC;
```

#### Quality Monitoring
```sql
-- Quality trends
SELECT 
  DATE(parsing_timestamp) as parsing_date,
  transaction_type,
  COUNT(*) as transaction_count,
  AVG(quality_score) as avg_quality,
  COUNT(CASE WHEN quality_score < 50 THEN 1 END) as low_quality_count,
  COUNT(CASE WHEN quality_score >= 80 THEN 1 END) as high_quality_count
FROM silver_transactions
WHERE parsing_timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(parsing_timestamp), transaction_type
ORDER BY parsing_date DESC, transaction_type;
```

### Alert Configuration

#### Disk Space Monitoring
```powershell
# Check Docker volume usage
docker system df

# Check host disk space
Get-WmiObject -Class Win32_LogicalDisk | Select-Object DeviceID, @{Name="Size(GB)";Expression={[math]::Round($_.Size/1GB,2)}}, @{Name="FreeSpace(GB)";Expression={[math]::Round($_.FreeSpace/1GB,2)}}
```

#### Processing Failure Alerts
```sql
-- Failed processing alert query
SELECT 
  COUNT(*) as failed_files,
  STRING_AGG(filename, ', ') as failed_file_list
FROM bronze_x12 
WHERE status = 'failed' 
  AND processing_timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour';
```

## 💾 Backup and Recovery

### Data Backup Strategy

#### Database Backup
```powershell
# Daily backup script
# File: scripts/backup-database.ps1

$BackupDate = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = "backups\database"

# Create backup directory
New-Item -ItemType Directory -Path $BackupDir -Force

# Backup PostgreSQL
docker exec x12-data-db pg_dump -U x12user -h localhost x12_data > "$BackupDir\x12_data_$BackupDate.sql"

# Backup Airflow metadata
docker exec airflow-postgres pg_dump -U airflow -h localhost airflow > "$BackupDir\airflow_$BackupDate.sql"

Write-Host "Database backup completed: $BackupDate"
```

#### File Storage Backup
```powershell
# MinIO data backup
# File: scripts/backup-storage.ps1

$BackupDate = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = "backups\storage"

# Sync MinIO buckets to local filesystem
docker exec minio mc mirror local/bronze-x12-raw "$BackupDir\bronze_$BackupDate"
docker exec minio mc mirror local/silver-x12-parsed "$BackupDir\silver_$BackupDate"
docker exec minio mc mirror local/gold-x12-business "$BackupDir\gold_$BackupDate"

Write-Host "Storage backup completed: $BackupDate"
```

### Disaster Recovery

#### Full Environment Recovery
```powershell
# Complete environment restore
# File: scripts/restore-environment.ps1

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupDate
)

# Stop current environment
docker-compose down -v

# Restore database backups
docker-compose up -d postgres data-postgres
Start-Sleep 30

# Restore PostgreSQL data
docker exec -i x12-data-db psql -U x12user x12_data < "backups\database\x12_data_$BackupDate.sql"

# Restore Airflow metadata
docker exec -i airflow-postgres psql -U airflow airflow < "backups\database\airflow_$BackupDate.sql"

# Start remaining services
docker-compose up -d

Write-Host "Environment restored from backup: $BackupDate"
```

#### Data Recovery Verification
```sql
-- Verify data integrity after restore
SELECT 
  'bronze_x12' as table_name,
  COUNT(*) as record_count,
  MAX(processing_timestamp) as latest_record
FROM bronze_x12
UNION ALL
SELECT 
  'silver_transactions',
  COUNT(*),
  MAX(parsing_timestamp)
FROM silver_transactions
UNION ALL
SELECT 
  'gold_transaction_summary',
  COUNT(*),
  MAX(created_at)
FROM gold_transaction_summary;
```

## ⚡ Performance Tuning

### System Resource Optimization

#### Docker Resource Allocation
```yaml
# In docker-compose.yml, add resource limits
services:
  airflow-worker:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
  
  postgres:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
```

#### Database Performance Tuning
```sql
-- PostgreSQL configuration optimization
-- Add to postgresql.conf (requires restart)

-- Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

-- Checkpoint settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB

-- Query optimization
random_page_cost = 1.1
effective_io_concurrency = 200

-- Analyze and optimize queries
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM silver_transactions 
WHERE transaction_type = 'Healthcare Claim'
  AND parsing_timestamp >= CURRENT_DATE - INTERVAL '7 days';
```

### Processing Performance

#### Airflow Optimization
```python
# In DAG configuration
default_args = {
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'max_active_runs': 1,  # Prevent concurrent runs
    'catchup': False,      # Don't backfill
}

# Task parallelization
dag = DAG(
    'x12_processing_pipeline',
    max_active_runs=1,
    max_active_tasks=4,    # Limit concurrent tasks
    concurrency=4,         # Overall concurrency limit
)
```

#### File Processing Optimization
```python
# Batch processing optimization
BATCH_SIZE = 50  # Process files in batches
PARALLEL_TASKS = 4  # Number of parallel workers

# Memory management
def process_large_file(file_path):
    # Stream processing for large files
    with open(file_path, 'r') as f:
        for chunk in iter(lambda: f.read(4096), ''):
            process_chunk(chunk)
```

### Storage Performance

#### MinIO Optimization
```bash
# MinIO performance settings
# Add to MinIO environment variables
MINIO_CACHE_DRIVES="/tmp/cache"
MINIO_CACHE_QUOTA="80%"
MINIO_CACHE_AFTER="3"
MINIO_CACHE_WATERMARK_LOW="70%"
MINIO_CACHE_WATERMARK_HIGH="90%"
```

#### Database Indexing Strategy
```sql
-- Optimize indexes for common queries
CREATE INDEX CONCURRENTLY idx_bronze_x12_processing_timestamp_status 
ON bronze_x12(processing_timestamp, status);

CREATE INDEX CONCURRENTLY idx_silver_transactions_parsing_timestamp_type 
ON silver_transactions(parsing_timestamp, transaction_type);

CREATE INDEX CONCURRENTLY idx_silver_transactions_quality_score 
ON silver_transactions(quality_score) WHERE quality_score < 70;

-- Partial indexes for common filters
CREATE INDEX CONCURRENTLY idx_silver_transactions_recent 
ON silver_transactions(parsing_timestamp) 
WHERE parsing_timestamp >= CURRENT_DATE - INTERVAL '30 days';
```

This comprehensive operations guide provides everything needed to effectively manage and maintain your local X12 EDI processing environment.