# Troubleshooting Guide

## 📋 Table of Contents

1. [Common Issues](#common-issues)
2. [Service-Specific Problems](#service-specific-problems)
3. [Performance Issues](#performance-issues)
4. [Data Processing Problems](#data-processing-problems)
5. [Network and Connectivity](#network-and-connectivity)
6. [Debugging Tools and Techniques](#debugging-tools-and-techniques)
7. [Log Analysis](#log-analysis)
8. [Recovery Procedures](#recovery-procedures)

## ⚠️ Common Issues

### Environment Won't Start

**Symptom**: Docker containers fail to start or exit immediately

**Possible Causes & Solutions**:

1. **Docker Desktop Not Running**
   ```powershell
   # Check Docker status
   docker version
   
   # If error, start Docker Desktop and wait for it to fully initialize
   ```

2. **Port Conflicts**
   ```powershell
   # Check what's using required ports
   netstat -an | findstr ":8080 :8888 :9000 :9001 :5432"
   
   # Solution: Stop conflicting services or modify ports in docker-compose.yml
   ```

3. **Insufficient Resources**
   ```powershell
   # Check available memory
   Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object TotalPhysicalMemory
   
   # Solution: Close other applications or reduce container resource limits
   ```

4. **Volume Mount Issues**
   ```powershell
   # Check if directories exist
   Test-Path "local-development\airflow\dags"
   
   # Solution: Create missing directories
   mkdir "local-development\airflow\dags" -Force
   ```

### Services Start But Don't Work

**Symptom**: Containers running but services inaccessible or malfunctioning

**Diagnostic Steps**:

1. **Check Service Health**
   ```powershell
   # Overall status
   docker-compose ps
   
   # Specific service logs
   docker-compose logs airflow-webserver
   docker-compose logs postgres
   ```

2. **Network Connectivity**
   ```powershell
   # Test internal network
   docker exec airflow-webserver ping postgres
   docker exec airflow-webserver ping minio
   ```

3. **Service Dependencies**
   ```powershell
   # Check if dependent services are ready
   docker exec postgres pg_isready -U airflow
   docker exec redis redis-cli ping
   ```

### Data Processing Failures

**Symptom**: Files uploaded but not processed, or processing fails

**Troubleshooting**:

1. **Check Airflow DAG Status**
   - Access http://localhost:8080
   - Verify DAG is enabled (toggle switch)
   - Check for failed task instances

2. **File Format Issues**
   ```powershell
   # Validate X12 file format
   Get-Content "testdata\test_x12_837_*.x12" | Select-Object -First 1
   # Should start with "ISA"
   ```

3. **Permission Issues**
   ```powershell
   # Check file permissions in mounted volumes
   docker exec airflow-worker ls -la /opt/airflow/data/input/
   ```

## 🔧 Service-Specific Problems

### Airflow Issues

#### Webserver Won't Start
```powershell
# Check Airflow initialization
docker-compose logs airflow-webserver

# Common solutions:
# 1. Reset Airflow database
docker-compose down
docker volume rm local-development_postgres-db-volume
docker-compose up -d postgres
Start-Sleep 30
docker-compose up -d airflow-webserver

# 2. Check Airflow configuration
docker exec airflow-webserver airflow config list
```

#### DAG Import Failures
```powershell
# Check DAG syntax
docker exec airflow-webserver python -m py_compile /opt/airflow/dags/x12_processing_dag.py

# Check DAG import errors
docker exec airflow-webserver airflow dags list-import-errors

# Restart scheduler after fixing DAGs
docker-compose restart airflow-scheduler
```

#### Task Execution Failures
```sql
-- Check task instances in Airflow database
docker exec airflow-postgres psql -U airflow -c "
SELECT 
  dag_id, 
  task_id, 
  state, 
  start_date, 
  end_date,
  log_url
FROM task_instance 
WHERE dag_id = 'x12_processing_pipeline'
ORDER BY start_date DESC 
LIMIT 10;"
```

### PostgreSQL Issues

#### Connection Problems
```powershell
# Test database connectivity
docker exec x12-data-db pg_isready -U x12user

# Check PostgreSQL logs
docker-compose logs data-postgres

# Reset PostgreSQL if corrupted
docker-compose down
docker volume rm local-development_data-postgres-volume
docker-compose up -d data-postgres
```

#### Performance Issues
```sql
-- Check slow queries
SELECT 
  query,
  calls,
  total_time,
  mean_time,
  rows
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;

-- Check blocking queries
SELECT 
  blocked_locks.pid AS blocked_pid,
  blocked_activity.usename AS blocked_user,
  blocking_locks.pid AS blocking_pid,
  blocking_activity.usename AS blocking_user,
  blocked_activity.query AS blocked_statement,
  blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

#### Data Corruption
```sql
-- Check database integrity
REINDEX DATABASE x12_data;

-- Check table corruption
SELECT 
  schemaname, 
  tablename, 
  attname, 
  n_distinct, 
  correlation 
FROM pg_stats 
WHERE schemaname = 'public';

-- Repair corrupted tables
VACUUM FULL bronze_x12;
ANALYZE bronze_x12;
```

### MinIO Issues

#### Storage Access Problems
```powershell
# Test MinIO connectivity
Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live"

# Check MinIO logs
docker-compose logs minio

# Test bucket access
docker exec minio mc ls local/bronze-x12-raw
```

#### Storage Full
```powershell
# Check storage usage
docker exec minio mc admin info local

# Clean up old files
docker exec minio mc rm --recursive --force local/archive-x12/old/

# Set lifecycle policies
docker exec minio mc ilm add local/bronze-x12-raw --expiry-days 30
```

### Jupyter Issues

#### Notebook Server Won't Start
```powershell
# Check Jupyter logs
docker-compose logs jupyter

# Reset Jupyter environment
docker-compose restart jupyter

# Get access token
docker logs jupyter 2>&1 | findstr "token="
```

#### Kernel Issues
```powershell
# Restart kernel inside Jupyter
# Or restart the entire service
docker-compose restart jupyter

# Check available kernels
docker exec jupyter jupyter kernelspec list
```

## 🐌 Performance Issues

### Slow Processing

**Diagnosis**:
```powershell
# Check system resources
docker stats

# Check disk I/O
Get-Counter "\PhysicalDisk(*)\Disk Transfers/sec"

# Check database performance
docker exec x12-data-db psql -U x12user -d x12_data -c "
SELECT 
  schemaname,
  tablename,
  seq_scan,
  seq_tup_read,
  idx_scan,
  idx_tup_fetch
FROM pg_stat_user_tables
ORDER BY seq_scan DESC;"
```

**Solutions**:

1. **Increase Resource Limits**
   ```yaml
   # In docker-compose.yml
   services:
     airflow-worker:
       deploy:
         resources:
           limits:
             memory: 4G
             cpus: '2.0'
   ```

2. **Optimize Database**
   ```sql
   -- Add missing indexes
   CREATE INDEX CONCURRENTLY idx_silver_transactions_type_date 
   ON silver_transactions(transaction_type, parsing_timestamp);
   
   -- Update statistics
   ANALYZE;
   ```

3. **Tune Airflow**
   ```python
   # In DAG configuration
   default_args = {
       'pool': 'default_pool',
       'max_active_runs': 2,
   }
   ```

### Memory Issues

**Symptoms**: Containers getting killed, out of memory errors

**Solutions**:
```powershell
# Check memory usage
docker stats --no-stream

# Increase Docker Desktop memory limit
# Settings → Resources → Memory

# Reduce batch sizes in processing
# Edit airflow/dags/x12_processing_dag.py
# Reduce BATCH_SIZE from 100 to 50
```

### Disk Space Issues

**Monitoring**:
```powershell
# Check Docker disk usage
docker system df

# Check host disk space
Get-WmiObject -Class Win32_LogicalDisk

# Clean up Docker resources
docker system prune -f
docker volume prune -f
```

## 📊 Data Processing Problems

### Files Not Being Processed

**Troubleshooting Steps**:

1. **Check File Location**
   ```powershell
   # Verify files are in correct directory
   ls local-development\processed\input\
   
   # Check file permissions
   Get-Acl local-development\processed\input\*.x12
   ```

2. **Validate File Format**
   ```powershell
   # Check X12 file starts with ISA
   Get-Content "local-development\processed\input\*.x12" | Select-Object -First 1
   ```

3. **Check Processing Logs**
   ```sql
   -- Check processing audit trail
   SELECT * FROM processing_audit 
   WHERE start_time >= CURRENT_DATE 
   ORDER BY start_time DESC;
   ```

### Data Quality Issues

**Low Quality Scores**:
```sql
-- Identify low quality files
SELECT 
  source_filename,
  transaction_type,
  quality_score,
  total_segments,
  parsing_timestamp
FROM silver_transactions 
WHERE quality_score < 70
ORDER BY quality_score ASC;

-- Analyze segment distribution
SELECT 
  segment_id,
  COUNT(*) as segment_count
FROM (
  SELECT jsonb_array_elements(segments_json->'segments')->>'segment_id' as segment_id
  FROM silver_transactions
  WHERE quality_score < 70
) segments
GROUP BY segment_id
ORDER BY segment_count DESC;
```

### Transaction Parsing Failures

**Debug Parsing Issues**:
```python
# Manual debugging in Jupyter
import json

# Load failed transaction
with open('/home/jovyan/work/data/processed/silver/failed_file.json', 'r') as f:
    failed_data = json.load(f)

# Examine raw content
print(failed_data['raw_content'][:500])

# Check segment structure
segments = failed_data['raw_content'].split('~')
for i, segment in enumerate(segments[:5]):
    print(f"Segment {i}: {segment}")
```

## 🌐 Network and Connectivity

### Service Communication Issues

**Inter-Service Connectivity**:
```powershell
# Test network connectivity between services
docker exec airflow-webserver ping postgres
docker exec airflow-webserver ping minio
docker exec airflow-webserver ping redis

# Check DNS resolution
docker exec airflow-webserver nslookup postgres
```

### External Access Issues

**Web UI Access Problems**:
```powershell
# Check port bindings
docker port x12-airflow 8080
docker port x12-jupyter 8888
docker port x12-minio 9001

# Test local access
Invoke-WebRequest -Uri "http://localhost:8080" -UseBasicParsing
```

### Network Configuration

**Custom Network Issues**:
```powershell
# Inspect Docker network
docker network ls
docker network inspect local-development_default

# Recreate network if needed
docker-compose down
docker network prune
docker-compose up -d
```

## 🔍 Debugging Tools and Techniques

### Container Debugging

**Access Container Shell**:
```powershell
# Access Airflow worker
docker exec -it x12-airflow bash

# Access PostgreSQL
docker exec -it x12-data-db psql -U x12user -d x12_data

# Access MinIO
docker exec -it x12-storage sh
```

### Process Monitoring

**Real-time Monitoring**:
```powershell
# Monitor container resources
docker stats

# Monitor specific container
docker stats x12-airflow --no-stream

# Monitor logs in real-time
docker-compose logs -f airflow-worker
```

### Database Debugging

**Query Analysis**:
```sql
-- Enable query logging (requires restart)
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_duration = on;
SELECT pg_reload_conf();

-- View active queries
SELECT 
  pid,
  now() - pg_stat_activity.query_start AS duration,
  query,
  state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
```

## 📝 Log Analysis

### Centralized Logging

**Access All Logs**:
```powershell
# View all service logs
docker-compose logs

# Filter logs by service
docker-compose logs airflow-webserver | findstr "ERROR"

# View logs with timestamps
docker-compose logs -t --since="1h" airflow-worker
```

### Log Patterns

**Common Error Patterns**:
```powershell
# Database connection errors
docker-compose logs | findstr "connection.*failed"

# Memory issues
docker-compose logs | findstr "OutOfMemory\|MemoryError"

# File processing errors
docker-compose logs | findstr "X12\|parsing.*failed"
```

### Structured Log Analysis

**Airflow Task Logs**:
- Access via Web UI: http://localhost:8080 → DAGs → x12_processing_pipeline → Graph View → Click Task → Logs
- Or directly: `local-development/airflow/logs/x12_processing_pipeline/`

## 🔧 Recovery Procedures

### Quick Recovery

**Service Recovery**:
```powershell
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart airflow-webserver

# Force recreate containers
docker-compose up -d --force-recreate
```

### Data Recovery

**Database Recovery**:
```powershell
# Restore from backup
docker exec -i x12-data-db psql -U x12user x12_data < "backups\database\x12_data_backup.sql"

# Reset processing state
docker exec x12-data-db psql -U x12user -d x12_data -c "
UPDATE bronze_x12 SET status = 'pending' 
WHERE status = 'processing' 
  AND processing_timestamp < CURRENT_TIMESTAMP - INTERVAL '1 hour';"
```

### Complete Environment Reset

**Nuclear Option** (destroys all data):
```powershell
# Stop and remove everything
docker-compose down -v --rmi all

# Remove all Docker resources
docker system prune -a -f

# Restart fresh environment
.\setup-local-dev.ps1
```

### Selective Recovery

**Recover Specific Component**:
```powershell
# Reset only Airflow
docker-compose stop airflow-webserver airflow-scheduler airflow-worker
docker volume rm local-development_postgres-db-volume
docker-compose up -d postgres
Start-Sleep 30
docker-compose up -d airflow-webserver airflow-scheduler airflow-worker

# Reset only MinIO
docker-compose stop minio
docker volume rm local-development_minio-data
docker-compose up -d minio
```

This troubleshooting guide covers the most common issues you'll encounter and provides systematic approaches to diagnose and resolve them.