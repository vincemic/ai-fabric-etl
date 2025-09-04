# X12 Local Development Environment Management

Quick reference for managing the local X12 EDI processing environment.

## 🚀 **Setup Commands**

### Initial Setup (Fresh Installation)
```powershell
# Clone repository (if needed)
git clone https://github.com/vincemic/ai-fabric-etl.git
cd ai-fabric-etl

# One-command setup - downloads ~7GB of Docker images
.\setup-local-dev.ps1
```

### Quick Start (Environment Already Built)
```powershell
# Navigate to local development directory
cd local-development

# Start all services
docker-compose up -d

# Check service health
docker-compose ps
```

## 🔧 **Management Commands**

### Service Control
```powershell
# Start environment
docker-compose up -d

# Stop environment (preserves data)
docker-compose down

# Restart specific service
docker-compose restart x12-airflow

# View logs
docker-compose logs -f x12-worker

# View all services status
docker-compose ps
```

### Health Checks
```powershell
# Test all services
docker ps --format "table {{.Names}}\t{{.Status}}"

# Test database
docker exec x12-data-db psql -U x12user -d x12_data -c "SELECT version();"

# Test Airflow
Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing

# Test MinIO
Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -UseBasicParsing
```

## 📊 **Data Processing**

### Process Test Data
```powershell
# Automated processing (recommended)
docker exec x12-worker python /opt/airflow/processed/process_test_data.py

# Copy additional files for processing
docker cp your-file.x12 x12-worker:/opt/airflow/processed/input/
```

### Monitor Processing
```powershell
# View processed files summary
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
```

## 🌐 **Access URLs**

| **Service** | **URL** | **Credentials** |
|-------------|---------|-----------------|
| **Airflow UI** | http://localhost:8080 | admin/admin |
| **Jupyter Lab** | http://localhost:8888 | token in logs |
| **MinIO Console** | http://localhost:9001 | minioadmin/minioadmin123 |
| **PostgreSQL** | localhost:5432 | x12user/x12password |

### Get Jupyter Token
```powershell
docker-compose logs x12-jupyter | findstr token
```

## 🧹 **Cleanup Commands**

### Partial Cleanup (Preserves Images)
```powershell
# Stop and remove containers, keep images for faster restart
docker-compose down -v
```

### Complete Cleanup (Removes Everything)
```powershell
# Automated complete cleanup - frees ~7GB
.\cleanup-local-dev.ps1
```

### Manual Cleanup Steps
```powershell
# 1. Stop containers and remove volumes
docker-compose down -v

# 2. Remove specific images
docker rmi postgres:15 minio/minio:latest redis:7.2-alpine apache/airflow:2.7.0-python3.11 jupyter/pyspark-notebook:latest

# 3. Clean system
docker system prune -f
```

## 🚨 **Troubleshooting**

### Common Issues

**Environment won't start:**
```powershell
# Check Docker Desktop is running
docker version

# Check port conflicts
netstat -an | findstr ":8080 :8888 :9000 :9001 :5432"
```

**Database not initialized:**
```powershell
docker-compose exec x12-airflow airflow db init
docker-compose exec x12-airflow airflow users create --username admin --firstname Admin --lastname User --role Admin --email admin@example.com --password admin
```

**Schema errors:**
```powershell
docker-compose exec x12-data-db psql -U x12user -d x12_data -f /docker-entrypoint-initdb.d/init.sql
```

**No test files:**
```powershell
docker cp testdata\*.x12 x12-worker:/opt/airflow/processed/input/
```

### Get Help
```powershell
# View service logs
docker-compose logs [service-name]

# Check container health
docker ps

# View detailed logs for specific service
docker-compose logs -f x12-airflow
```

## 📝 **Development Workflow**

1. **Start Environment**: `.\setup-local-dev.ps1` (first time) or `docker-compose up -d`
2. **Process Data**: Use Airflow UI or automated script
3. **Develop**: Use Jupyter Lab for interactive development
4. **Monitor**: Check Airflow UI and database queries
5. **Stop**: `docker-compose down` (preserves data) or `.\cleanup-local-dev.ps1` (removes everything)

## 📚 **Documentation Links**

- [Architecture Guide](docs/local-development-architecture.md)
- [Operations Management](docs/operations-management-guide.md)
- [Troubleshooting Guide](docs/troubleshooting-guide.md)
- [Performance Tuning](docs/performance-tuning-guide.md)
- [Azure Migration](docs/azure-migration-guide.md)

---

**💡 Tip**: Bookmark this file for quick reference during development!