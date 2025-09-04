# Local X12 EDI Processing Environment

## 🚀 Quick Start

### Prerequisites
- Docker Desktop for Windows (latest version)
- At least 8GB RAM available
- 10GB free disk space
- PowerShell 5.1+ (Windows default)

### One-Command Setup

```powershell
# Navigate to project root
cd C:\tmp\ai-fabric-etl

# Run setup script
.\setup-local-dev.ps1
```

**Expected Results:**
- ✅ All services running in Docker
- ✅ Airflow database initialized
- ✅ X12 database schema created
- ✅ Test data ready for processing
- ✅ Web interfaces accessible

## � Access Points

| **Service** | **URL** | **Credentials** | **Purpose** |
|-------------|---------|-----------------|-------------|
| **Airflow UI** | http://localhost:8080 | admin/admin | Pipeline monitoring & management |
| **Jupyter Lab** | http://localhost:8888 | token in logs | Interactive development |
| **MinIO Console** | http://localhost:9001 | minioadmin/minioadmin123 | Storage management |
| **PostgreSQL** | localhost:5432 | x12user/x12password | Database access |

## 📊 Test Data Processing

### Option 1: Automated Processing (Recommended)

```powershell
# Process all test X12 files through the pipeline
docker exec x12-worker python /opt/airflow/processed/process_test_data.py
```

### Option 2: Airflow Pipeline

1. Open Airflow UI: http://localhost:8080
2. Enable the `x12_processing_dag` DAG
3. Trigger the DAG manually
4. Monitor progress in the Airflow UI

### Option 3: Manual File Processing

```powershell
# Copy additional X12 files to processing directory
docker cp your-file.x12 x12-worker:/opt/airflow/processed/input/

# Check processing status
docker exec x12-data-db psql -U x12user -d x12_data -c "
SELECT 
  source_filename, 
  transaction_type, 
  quality_score 
FROM silver_transactions 
ORDER BY quality_score DESC 
LIMIT 10;"
```

## 🏗️ Architecture

### Container Services

```
x12-storage     - MinIO object storage (S3-compatible)
x12-postgres    - Airflow metadata database  
x12-data-db     - X12 data warehouse (medallion architecture)
x12-redis       - Message queue for Airflow workers
x12-airflow     - Airflow webserver
x12-scheduler   - Airflow task scheduler
x12-worker      - Airflow task executor
x12-jupyter     - Jupyter Lab for development
```

### Data Flow

```
Raw X12 Files → Bronze Layer → Silver Layer → Gold Layer
      ↓              ↓             ↓            ↓
  File Storage → Raw Storage → Parsed Data → Analytics
  (input dir)   (bronze_x12)  (silver_tx)  (gold_*)
```
docker-compose ps
```

### 2. Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **Airflow UI** | http://localhost:8080 | admin/admin |
| **Jupyter Lab** | http://localhost:8888 | Check logs for token |
| **MinIO Console** | http://localhost:9001 | minioadmin/minioadmin123 |
| **PostgreSQL** | localhost:5432 | x12user/x12password |

### 3. Initialize Storage Buckets
```powershell
# Create the medallion architecture buckets in MinIO
# Access MinIO Console at http://localhost:9001
# Create buckets: bronze-x12-raw, silver-x12-parsed, gold-x12-business
```

## 📁 **Directory Structure**

```
local-development/
├── docker-compose.yml          # Docker services definition
├── airflow/
│   ├── dags/                  # Airflow DAGs (pipeline definitions)
│   ├── logs/                  # Airflow execution logs
│   ├── config/                # Airflow configuration
│   └── plugins/               # Custom Airflow plugins
├── notebooks-local/           # Modified notebooks for local execution
├── sql/
│   └── init.sql              # Database initialization script
└── README.md                 # This file
```

## 🔄 **Processing Flow**

### Local X12 Processing Pipeline

1. **File Upload**: Upload X12 files to MinIO bronze bucket
2. **Airflow Trigger**: DAG monitors for new files and triggers processing
3. **Bronze Processing**: Jupyter notebook validates and stores raw files
4. **Silver Processing**: Parses X12 segments into structured data
5. **Gold Processing**: Creates business analytics and KPIs
6. **Storage**: Final data stored in PostgreSQL tables

## � Management Commands

### Service Control

```powershell
# Start environment
cd local-development
docker-compose up -d

# Stop environment  
docker-compose down

# Restart specific service
docker-compose restart x12-airflow

# View logs
docker-compose logs -f x12-worker

# Complete cleanup (removes all data)
docker-compose down -v
```

### Health Checks

```powershell
# Check all services
docker ps --format "table {{.Names}}\t{{.Status}}"

# Test database connectivity
docker exec x12-data-db psql -U x12user -d x12_data -c "SELECT version();"

# Test Airflow
Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing

# Test MinIO
Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -UseBasicParsing
```

### Data Inspection

```powershell
# View processed files
docker exec x12-data-db psql -U x12user -d x12_data -c "
SELECT COUNT(*), status FROM bronze_x12 GROUP BY status;"

# View transaction analytics  
docker exec x12-data-db psql -U x12user -d x12_data -c "
SELECT 
  transaction_type,
  COUNT(*) as count,
  ROUND(AVG(quality_score), 1) as avg_quality
FROM silver_transactions 
GROUP BY transaction_type 
ORDER BY transaction_type;"

# View storage usage
docker exec x12-storage mc du local/
```

## 🚨 Troubleshooting

### Common Issues & Solutions

**❌ "Database not initialized" in Airflow UI**
```powershell
docker-compose exec x12-airflow airflow db init
docker-compose exec x12-airflow airflow users create --username admin --firstname Admin --lastname User --role Admin --email admin@example.com --password admin
```

**❌ "Column does not exist" errors**
```powershell
# Reinitialize database schema
docker-compose exec x12-data-db psql -U x12user -d x12_data -f /docker-entrypoint-initdb.d/init.sql
```

**❌ No test files to process**
```powershell
# Copy test data
docker cp testdata\*.x12 x12-worker:/opt/airflow/processed/input/
```

**❌ Services won't start**
```powershell
# Check Docker Desktop is running
docker version

# Check port conflicts
netstat -an | findstr ":8080 :8888 :9000 :9001 :5432"

# View detailed logs
docker-compose logs x12-airflow
```

### Getting Help

1. **Check service logs**: `docker-compose logs [service-name]`
2. **Verify container health**: `docker ps`
3. **Test connectivity**: Use health check commands above
4. **Review documentation**: See `/docs` folder for detailed guides

## 📚 Next Steps

### Development Workflow

1. **Modify X12 processing logic**: Edit files in `local-development/airflow/dags/`
2. **Test changes**: Use Jupyter Lab for interactive development
3. **Deploy to production**: Follow Azure migration guide in `/docs`

### Scaling Considerations

- **Add workers**: Increase `replicas` in docker-compose.yml
- **Optimize database**: Tune PostgreSQL settings for larger datasets  
- **Monitor performance**: Use Airflow metrics and database monitoring

### Production Migration

See `/docs/azure-migration-guide.md` for detailed steps to deploy this pipeline to Azure Fabric.

---

## 📖 Documentation

- [Architecture Guide](../docs/local-development-architecture.md)
- [Operations Management](../docs/operations-management-guide.md)  
- [Troubleshooting](../docs/troubleshooting-guide.md)
- [Performance Tuning](../docs/performance-tuning-guide.md)
- [Azure Migration](../docs/azure-migration-guide.md)

**🎉 You now have a complete local X12 EDI processing environment!**

### 1. Modify Processing Logic
```powershell
# Edit notebooks in Jupyter Lab
# Navigate to http://localhost:8888
# Open notebooks from /work/notebooks-local/
```

### 2. Test with Sample Data
```powershell
# Copy test X12 files to input directory
docker cp ../testdata/test_x12_837_*.x12 x12-jupyter:/home/jovyan/work/data/input/
```

### 3. Monitor Processing
```powershell
# View Airflow DAG execution
# Navigate to http://localhost:8080
# Check DAG status and logs
```

### 4. Query Results
```powershell
# Connect to PostgreSQL to view processed data
docker exec -it x12-data-db psql -U x12user -d x12_data

# Example queries
\dt                           # List tables
SELECT * FROM bronze_x12 LIMIT 5;
SELECT * FROM silver_transactions LIMIT 5;
SELECT * FROM gold_analytics LIMIT 5;
```

## 🔧 **Configuration**

### Environment Variables
Create `.env` file with local configurations:

```env
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
```

## 🧪 **Testing**

### Run Unit Tests
```powershell
# Execute tests inside Jupyter container
docker exec x12-jupyter python -m pytest /home/jovyan/work/tests/
```

### Process Sample Files
```powershell
# Trigger manual DAG run via Airflow UI
# Or use Airflow CLI
docker exec x12-airflow airflow dags trigger x12_processing_dag
```

## 📊 **Monitoring**

### Check Processing Status
```powershell
# View Airflow logs
docker-compose logs airflow-worker

# Check MinIO storage usage
# Access MinIO Console at http://localhost:9001

# Monitor database growth
docker exec x12-data-db psql -U x12user -d x12_data -c "
  SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
  FROM pg_stats 
  WHERE schemaname = 'public';"
```

## 🔄 **Data Migration to Azure**

When ready to move to Azure:

1. **Export Configuration**:
   ```powershell
   # Export Airflow DAGs as Data Factory pipelines
   python scripts/airflow_to_adf_converter.py
   ```

2. **Data Migration**:
   ```powershell
   # Copy processed data to Azure Storage
   azcopy sync ./local-development/processed/ https://yourstorageaccount.blob.core.windows.net/silver-x12-parsed/
   ```

3. **Schema Migration**:
   ```powershell
   # Export PostgreSQL schema for Azure SQL
   pg_dump -s -h localhost -U x12user x12_data > schema_export.sql
   ```

## ⚡ **Performance Optimization**

### Resource Allocation
```yaml
# In docker-compose.yml, adjust resources as needed:
services:
  jupyter:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2'
```

### Processing Optimization
- Adjust `BATCH_SIZE` in environment variables
- Scale Airflow workers: `docker-compose up --scale airflow-worker=3`
- Use SSD storage for Docker volumes in production

## 🛑 **Cleanup**

```powershell
# Stop all services
docker-compose down

# Remove volumes (WARNING: Deletes all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## 🔍 **Troubleshooting**

### Common Issues

1. **Port Conflicts**:
   ```powershell
   # Check what's using ports
   netstat -an | findstr :8080
   # Modify ports in docker-compose.yml if needed
   ```

2. **Memory Issues**:
   ```powershell
   # Increase Docker Desktop memory limit
   # Reduce container resource limits
   ```

3. **Storage Issues**:
   ```powershell
   # Check Docker disk usage
   docker system df
   # Clean up unused containers/images
   docker system prune
   ```

## 📝 **Next Steps**

1. **Customize Processing**: Modify notebooks for your specific X12 requirements
2. **Add Monitoring**: Integrate with local monitoring tools
3. **Scale Testing**: Test with larger data volumes
4. **Azure Migration**: Plan migration strategy to Azure Fabric

This local setup provides a complete development environment that mirrors your Azure Fabric architecture while remaining cost-effective for development and testing.