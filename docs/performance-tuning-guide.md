# Performance Tuning Guide

## 📋 Table of Contents

1. [Performance Overview](#performance-overview)
2. [System Requirements](#system-requirements)
3. [Docker Optimization](#docker-optimization)
4. [Database Performance](#database-performance)
5. [Storage Optimization](#storage-optimization)
6. [Pipeline Efficiency](#pipeline-efficiency)
7. [Monitoring and Metrics](#monitoring-and-metrics)
8. [Troubleshooting Performance Issues](#troubleshooting-performance-issues)

## 🎯 Performance Overview

This guide provides comprehensive strategies for optimizing the performance of your local X12 EDI processing environment. Proper tuning can improve processing speeds by 50-80% and reduce resource consumption significantly.

### Performance Targets

| Metric | Target | Current Baseline | Optimized Target |
|--------|--------|------------------|------------------|
| File Processing Rate | transactions/hour | 1,000 | 5,000+ |
| Database Query Response | milliseconds | 500ms | 100ms |
| Memory Usage | GB | 8GB | 4GB |
| Startup Time | minutes | 5min | 2min |
| Storage Efficiency | compression ratio | 1:1 | 3:1 |

### Key Performance Factors

1. **Hardware Resources**: CPU, Memory, Disk I/O
2. **Container Configuration**: Resource limits, networking
3. **Database Tuning**: Indexes, queries, connection pooling
4. **Storage Strategy**: Compression, partitioning, caching
5. **Pipeline Optimization**: Batch sizes, parallelization

## 💻 System Requirements

### Minimum Requirements

**Development Environment**:
- CPU: 4 cores, 2.5GHz
- RAM: 8GB
- Storage: 50GB SSD
- Network: 100 Mbps

**Production-Ready Environment**:
- CPU: 8 cores, 3.0GHz
- RAM: 16GB
- Storage: 100GB NVMe SSD
- Network: 1 Gbps

### Recommended Hardware Configuration

```powershell
# Check current system specifications
Get-ComputerInfo | Select-Object TotalPhysicalMemory, CsProcessors, CsSystemType

# Check disk performance
Get-PhysicalDisk | Select-Object DeviceId, MediaType, SpindleSpeed
```

### Docker Desktop Configuration

**Optimal Settings**:
```powershell
# Configure Docker Desktop resources
# Settings → Resources → Advanced
# - CPUs: 6-8 cores
# - Memory: 12-16 GB  
# - Swap: 2 GB
# - Disk Image Size: 64 GB
```

## 🐳 Docker Optimization

### Container Resource Limits

**Optimized docker-compose.yml**:
```yaml
version: '3.8'
services:
  minio:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    
  postgres:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '1.0'
    command: >
      postgres 
      -c shared_buffers=512MB
      -c effective_cache_size=1536MB
      -c maintenance_work_mem=128MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=16MB
      -c default_statistics_target=100
    
  airflow-webserver:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.5'
        reservations:
          memory: 1G
          cpus: '0.5'
    
  airflow-scheduler:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '1.0'
    
  airflow-worker:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '3.0'
        reservations:
          memory: 2G
          cpus: '1.5'
    
  jupyter:
    deploy:
      resources:
        limits:
          memory: 3G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

### Network Optimization

**Custom Network Configuration**:
```yaml
networks:
  x12-network:
    driver: bridge
    driver_opts:
      com.docker.network.driver.mtu: 1500
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Volume Performance

**High-Performance Volume Configuration**:
```yaml
volumes:
  postgres-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: C:\tmp\ai-fabric-etl\volumes\postgres-data
  
  minio-data:
    driver: local
    driver_opts:
      type: none
      o: bind  
      device: C:\tmp\ai-fabric-etl\volumes\minio-data
```

## 🗄️ Database Performance

### PostgreSQL Configuration Optimization

**postgresql.conf Settings**:
```sql
-- Memory settings
shared_buffers = 512MB                 -- 25% of available RAM
effective_cache_size = 1536MB          -- 75% of available RAM  
work_mem = 64MB                        -- For sorting/hashing operations
maintenance_work_mem = 256MB           -- For VACUUM, CREATE INDEX

-- Checkpoint settings
checkpoint_completion_target = 0.9     -- Spread checkpoints over time
wal_buffers = 16MB                     -- WAL buffer size
checkpoint_timeout = 15min             -- Maximum time between checkpoints

-- Query planner settings
default_statistics_target = 100        -- Statistics sampling
random_page_cost = 1.1                 -- SSD optimization
effective_io_concurrency = 200         -- SSD concurrent I/O

-- Connection settings
max_connections = 200                  -- Concurrent connections
shared_preload_libraries = 'pg_stat_statements'
```

### Index Optimization

**Critical Indexes for X12 Processing**:
```sql
-- Performance monitoring
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Bronze layer indexes
CREATE INDEX CONCURRENTLY idx_bronze_x12_filename_status 
ON bronze_x12(source_filename, status);

CREATE INDEX CONCURRENTLY idx_bronze_x12_ingestion_time 
ON bronze_x12(ingestion_timestamp) 
WHERE status = 'processed';

-- Silver layer indexes  
CREATE INDEX CONCURRENTLY idx_silver_transactions_type_date
ON silver_transactions(transaction_type, parsing_timestamp);

CREATE INDEX CONCURRENTLY idx_silver_transactions_quality
ON silver_transactions(quality_score) 
WHERE quality_score >= 80;

CREATE INDEX CONCURRENTLY idx_silver_segments_gin
ON silver_transactions USING gin(segments_json);

-- Gold layer indexes
CREATE INDEX CONCURRENTLY idx_gold_claims_provider_date
ON gold_claims_analytics(provider_id, claim_date);

CREATE INDEX CONCURRENTLY idx_gold_payments_amount
ON gold_payments_analytics(payment_amount) 
WHERE payment_amount > 100;

-- Composite indexes for common queries
CREATE INDEX CONCURRENTLY idx_silver_complex_query
ON silver_transactions(transaction_type, parsing_timestamp, quality_score)
WHERE status = 'valid';
```

### Query Optimization

**Optimized Queries**:
```sql
-- Before: Sequential scan
SELECT * FROM silver_transactions 
WHERE transaction_type = '837' 
  AND parsing_timestamp >= CURRENT_DATE - INTERVAL '7 days';

-- After: Index scan with LIMIT
SELECT transaction_id, transaction_type, quality_score, parsing_timestamp
FROM silver_transactions 
WHERE transaction_type = '837' 
  AND parsing_timestamp >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY parsing_timestamp DESC
LIMIT 1000;

-- Use EXISTS instead of IN for better performance
SELECT COUNT(*) 
FROM bronze_x12 b
WHERE EXISTS (
  SELECT 1 FROM silver_transactions s 
  WHERE s.source_filename = b.source_filename
);

-- Batch processing with CTEs
WITH recent_transactions AS (
  SELECT * FROM silver_transactions 
  WHERE parsing_timestamp >= CURRENT_DATE - INTERVAL '1 day'
),
processed_claims AS (
  SELECT 
    transaction_id,
    jsonb_extract_path_text(segments_json, 'claim_amount') as amount
  FROM recent_transactions 
  WHERE transaction_type = '837'
)
SELECT AVG(amount::numeric) FROM processed_claims;
```

### Connection Pooling

**PgBouncer Configuration** (optional enhancement):
```ini
[databases]
x12_data = host=localhost port=5433 dbname=x12_data

[pgbouncer]
pool_mode = transaction
listen_port = 6432
listen_addr = *
auth_type = trust
auth_file = userlist.txt
logfile = pgbouncer.log
pidfile = pgbouncer.pid
admin_users = postgres
stats_users = postgres
max_client_conn = 200
default_pool_size = 25
server_round_robin = 1
```

## 💾 Storage Optimization

### MinIO Performance Tuning

**MinIO Configuration**:
```yaml
minio:
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin123
    # Performance optimizations
    MINIO_CACHE_DRIVES: "C:\\tmp\\minio-cache"
    MINIO_CACHE_EXCLUDE: "*.tmp"
    MINIO_CACHE_QUOTA: 80
    MINIO_CACHE_AFTER: 2
    MINIO_CACHE_WATERMARK_LOW: 70
    MINIO_CACHE_WATERMARK_HIGH: 90
  command: >
    server /data
    --console-address ":9001"
    --cache-drives="C:\\tmp\\minio-cache"
    --cache-quota=80
```

### File Compression

**Compression Strategy**:
```python
import gzip
import json
from pathlib import Path

def compress_x12_files():
    """Compress processed X12 files to save storage"""
    input_dir = Path("local-development/processed/input")
    archive_dir = Path("local-development/processed/archive")
    
    for x12_file in input_dir.glob("*.x12"):
        if x12_file.stat().st_mtime < (time.time() - 7*24*3600):  # 7 days old
            with open(x12_file, 'rb') as f_in:
                with gzip.open(archive_dir / f"{x12_file.name}.gz", 'wb') as f_out:
                    f_out.write(f_in.read())
            x12_file.unlink()  # Remove original

def compress_json_output():
    """Compress JSON output files"""
    for json_file in Path("local-development/processed/silver").glob("*.json"):
        with open(json_file, 'r') as f_in:
            data = json.load(f_in)
        
        compressed_path = json_file.with_suffix('.json.gz')
        with gzip.open(compressed_path, 'wt') as f_out:
            json.dump(data, f_out, separators=(',', ':'))  # Compact JSON
        
        if compressed_path.stat().st_size < json_file.stat().st_size * 0.7:
            json_file.unlink()  # Remove if >30% compression
```

### Disk I/O Optimization

**Windows Disk Performance**:
```powershell
# Check disk performance
Get-PhysicalDisk | Get-StorageReliabilityCounter

# Optimize volume for performance
Optimize-Volume -DriveLetter C -ReTrim

# Set file system cache
fsutil behavior set DisableDeleteNotify NTFS 0
fsutil behavior set DisableDeleteNotify ReFS 0
```

### Data Partitioning Strategy

**Table Partitioning**:
```sql
-- Partition silver_transactions by month
CREATE TABLE silver_transactions_y2024m01 PARTITION OF silver_transactions
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE silver_transactions_y2024m02 PARTITION OF silver_transactions  
FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Automatic partition creation function
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date)
RETURNS void AS $$
DECLARE
    partition_name text;
    end_date date;
BEGIN
    partition_name := table_name || '_y' || EXTRACT(year FROM start_date) || 'm' || LPAD(EXTRACT(month FROM start_date)::text, 2, '0');
    end_date := start_date + INTERVAL '1 month';
    
    EXECUTE format('CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;
```

## ⚡ Pipeline Efficiency

### Airflow Configuration Tuning

**Optimized Airflow Settings**:
```python
# airflow.cfg optimizations
[core]
executor = CeleryExecutor
sql_alchemy_pool_size = 10
sql_alchemy_max_overflow = 20
sql_alchemy_pool_recycle = 3600
parallelism = 32                    # Increase task parallelism
dag_concurrency = 16               # Concurrent tasks per DAG
max_active_runs_per_dag = 16       # Active DAG runs

[celery]
worker_concurrency = 8             # Worker processes
task_soft_time_limit = 600         # Task timeout
task_time_limit = 1200             # Hard timeout
result_backend_session_cache_size = 10000

[scheduler]
job_heartbeat_sec = 5              # Faster heartbeat
scheduler_heartbeat_sec = 5        # Scheduler frequency
num_runs = -1                      # Unlimited runs
```

### Task Optimization

**Efficient X12 Processing DAG**:
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from concurrent.futures import ThreadPoolExecutor, as_completed
import pendulum

# Optimized configuration
default_args = {
    'owner': 'x12-team',
    'depends_on_past': False,
    'start_date': pendulum.now(),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': pendulum.duration(minutes=5),
    'pool': 'x12_processing_pool',  # Dedicated resource pool
}

@dag(
    'x12_processing_optimized',
    default_args=default_args,
    description='Optimized X12 processing pipeline',
    schedule_interval=pendulum.duration(minutes=5),
    catchup=False,
    max_active_runs=3,
    concurrency=8,
    tags=['x12', 'optimized']
)
def optimized_x12_processing():
    
    def parallel_file_processing(**context):
        """Process multiple files in parallel"""
        files = get_pending_files()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(process_single_file, file): file 
                for file in files
            }
            
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=300)  # 5 minute timeout
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to process {futures[future]}: {e}")
            
            return results
    
    def batch_database_insert(**context):
        """Batch insert for better database performance"""
        processed_data = context['task_instance'].xcom_pull(task_ids='parallel_bronze_processing')
        
        if not processed_data:
            return
        
        # Use COPY for bulk insert instead of individual INSERTs
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Prepare data for COPY
                data_tuples = [
                    (item['filename'], item['content'], item['timestamp'])
                    for item in processed_data
                ]
                
                # Bulk insert using COPY
                psycopg2.extras.execute_values(
                    cur,
                    "INSERT INTO bronze_x12 (source_filename, raw_content, ingestion_timestamp) VALUES %s",
                    data_tuples,
                    template=None,
                    page_size=1000
                )
                conn.commit()
    
    # Define tasks with optimizations
    parallel_bronze = PythonOperator(
        task_id='parallel_bronze_processing',
        python_callable=parallel_file_processing,
        pool='x12_processing_pool',
        retries=3
    )
    
    batch_insert = PythonOperator(
        task_id='batch_database_insert',
        python_callable=batch_database_insert,
        pool='database_pool',
        depends_on_past=False
    )
    
    parallel_bronze >> batch_insert

dag = optimized_x12_processing()
```

### Memory-Efficient Processing

**Streaming Processing for Large Files**:
```python
def stream_process_large_x12(file_path, batch_size=1000):
    """Process large X12 files without loading entire file into memory"""
    
    def x12_segment_generator(file_handle):
        """Generator that yields X12 segments one at a time"""
        buffer = ""
        while True:
            chunk = file_handle.read(8192)  # Read in chunks
            if not chunk:
                if buffer:
                    yield buffer
                break
                
            buffer += chunk
            while '~' in buffer:
                segment, buffer = buffer.split('~', 1)
                yield segment + '~'
    
    processed_count = 0
    batch_data = []
    
    with open(file_path, 'r') as f:
        for segment in x12_segment_generator(f):
            processed_segment = parse_x12_segment(segment)
            batch_data.append(processed_segment)
            
            if len(batch_data) >= batch_size:
                # Process batch
                insert_batch_to_database(batch_data)
                batch_data = []
                processed_count += batch_size
                
                # Memory cleanup
                if processed_count % (batch_size * 10) == 0:
                    import gc
                    gc.collect()
    
    # Process remaining data
    if batch_data:
        insert_batch_to_database(batch_data)
```

## 📊 Monitoring and Metrics

### Performance Metrics Collection

**System Monitoring Setup**:
```python
import psutil
import time
from datetime import datetime

class PerformanceMonitor:
    def __init__(self):
        self.metrics = []
    
    def collect_system_metrics(self):
        """Collect comprehensive system metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        metrics = {
            'timestamp': datetime.now(),
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_gb': memory.available / (1024**3),
            'disk_percent': disk.percent,
            'disk_free_gb': disk.free / (1024**3)
        }
        
        self.metrics.append(metrics)
        return metrics
    
    def collect_docker_metrics(self):
        """Collect Docker container metrics"""
        import docker
        client = docker.from_env()
        
        container_metrics = {}
        for container in client.containers.list():
            stats = container.stats(stream=False)
            
            # Calculate CPU percentage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            cpu_percent = (cpu_delta / system_delta) * 100.0
            
            # Calculate memory usage
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            memory_percent = (memory_usage / memory_limit) * 100.0
            
            container_metrics[container.name] = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'memory_mb': memory_usage / (1024**2)
            }
        
        return container_metrics
```

### Database Performance Monitoring

**PostgreSQL Performance Queries**:
```sql
-- Monitor query performance
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    stddev_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 20;

-- Monitor table performance
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    n_tup_ins,
    n_tup_upd,
    n_tup_del
FROM pg_stat_user_tables 
ORDER BY seq_tup_read DESC;

-- Monitor index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
ORDER BY idx_scan DESC;

-- Monitor database connections
SELECT 
    count(*) as connection_count,
    state,
    application_name
FROM pg_stat_activity 
GROUP BY state, application_name;
```

### Custom Metrics Dashboard

**Jupyter Notebook for Monitoring**:
```python
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from datetime import datetime, timedelta

def create_performance_dashboard():
    """Create performance monitoring dashboard"""
    
    # Fetch metrics from database
    query = """
    SELECT 
        measurement_time,
        cpu_usage,
        memory_usage,
        processing_rate,
        queue_depth
    FROM system_metrics 
    WHERE measurement_time >= NOW() - INTERVAL '24 hours'
    ORDER BY measurement_time
    """
    
    df = pd.read_sql(query, connection)
    
    # Create dashboard
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # CPU Usage
    axes[0,0].plot(df['measurement_time'], df['cpu_usage'])
    axes[0,0].set_title('CPU Usage Over Time')
    axes[0,0].set_ylabel('CPU %')
    axes[0,0].axhline(y=80, color='r', linestyle='--', label='Warning Threshold')
    
    # Memory Usage
    axes[0,1].plot(df['measurement_time'], df['memory_usage'], color='orange')
    axes[0,1].set_title('Memory Usage Over Time')
    axes[0,1].set_ylabel('Memory %')
    axes[0,1].axhline(y=85, color='r', linestyle='--', label='Warning Threshold')
    
    # Processing Rate
    axes[1,0].bar(df['measurement_time'], df['processing_rate'], width=0.02)
    axes[1,0].set_title('Processing Rate (Transactions/Hour)')
    axes[1,0].set_ylabel('Transactions')
    
    # Queue Depth
    axes[1,1].plot(df['measurement_time'], df['queue_depth'], color='green')
    axes[1,1].set_title('Queue Depth')
    axes[1,1].set_ylabel('Pending Files')
    
    plt.tight_layout()
    plt.savefig('performance_dashboard.png', dpi=300, bbox_inches='tight')
    plt.show()
```

### Alerting Configuration

**Performance Alert System**:
```python
def check_performance_thresholds():
    """Monitor system and alert on performance issues"""
    
    thresholds = {
        'cpu_percent': 85,
        'memory_percent': 90,
        'disk_percent': 85,
        'queue_depth': 100,
        'processing_rate_min': 500  # transactions per hour
    }
    
    current_metrics = collect_system_metrics()
    alerts = []
    
    for metric, threshold in thresholds.items():
        if metric.endswith('_min'):
            actual_metric = metric.replace('_min', '')
            if current_metrics.get(actual_metric, float('inf')) < threshold:
                alerts.append(f"LOW {actual_metric}: {current_metrics[actual_metric]} < {threshold}")
        else:
            if current_metrics.get(metric, 0) > threshold:
                alerts.append(f"HIGH {metric}: {current_metrics[metric]} > {threshold}")
    
    if alerts:
        send_alerts(alerts)
        return False
    return True

def send_alerts(alerts):
    """Send performance alerts"""
    message = f"Performance Alert at {datetime.now()}\n\n" + "\n".join(alerts)
    
    # Log to file
    with open('performance_alerts.log', 'a') as f:
        f.write(f"{datetime.now()} - {message}\n")
    
    # Could integrate with email, Slack, Teams, etc.
    print(f"ALERT: {message}")
```

## 🔧 Troubleshooting Performance Issues

### Common Performance Problems

#### Slow Database Queries
```sql
-- Identify slow queries
SELECT 
    query,
    calls,
    total_time / calls as avg_time_ms,
    rows / calls as avg_rows
FROM pg_stat_statements 
WHERE calls > 10 
ORDER BY avg_time_ms DESC 
LIMIT 10;

-- Fix with proper indexing
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM silver_transactions 
WHERE transaction_type = '837' 
  AND parsing_timestamp >= CURRENT_DATE - INTERVAL '7 days';
```

#### High Memory Usage
```powershell
# Check container memory usage
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Investigate memory leaks
docker exec airflow-worker python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory info: {process.memory_info()}')
print(f'Memory percent: {process.memory_percent():.2f}%')
"
```

#### Container Startup Issues
```powershell
# Check container dependencies
docker-compose ps

# Examine startup logs
docker-compose logs --tail=50 postgres
docker-compose logs --tail=50 airflow-scheduler

# Test service connectivity
docker exec airflow-webserver ping postgres -c 3
```

### Performance Profiling

**Python Code Profiling**:
```python
import cProfile
import pstats
from pstats import SortKey

def profile_x12_processing():
    """Profile X12 processing performance"""
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run X12 processing
    process_x12_batch('test_files/')
    
    profiler.disable()
    
    # Analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats(SortKey.TIME)
    stats.print_stats(20)  # Top 20 functions by time
    
    # Save profile data
    stats.dump_stats('x12_processing_profile.prof')

# Memory profiling with memory_profiler
from memory_profiler import profile

@profile
def memory_intensive_function():
    """Function to profile memory usage"""
    large_data = []
    for i in range(10000):
        large_data.append(f"Data item {i}" * 100)
    return large_data
```

This performance tuning guide provides comprehensive strategies to optimize your X12 processing environment for maximum efficiency and throughput.