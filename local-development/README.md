# Local Development Environment for X12 EDI Processing

This directory contains the local development setup that mimics the Azure Fabric infrastructure using open-source alternatives.

## 🏗️ **Local Architecture**

| Azure Service | Local Alternative | Purpose |
|---------------|------------------|---------|
| Azure Storage (Data Lake) | MinIO | File storage for Bronze/Silver/Gold layers |
| Azure Data Factory | Apache Airflow | Pipeline orchestration |
| Azure Fabric Notebooks | Jupyter Notebook | Interactive development |
| Azure SQL/Cosmos DB | PostgreSQL | Structured data storage |
| Azure Service Bus | Redis | Message queuing |
| Azure Key Vault | Environment variables | Secrets management |

## 🚀 **Quick Start**

### Prerequisites
- Docker Desktop installed and running
- At least 8GB RAM available for containers
- Ports 8080, 8888, 9000, 9001, 5432 available

### 1. Start the Environment
```powershell
# Navigate to local development directory
cd local-development

# Start all services
docker-compose up -d

# Check service health
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

## 🛠️ **Development Workflow**

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