# Script to set up local development environment
# Run this to quickly start the X12 processing environment

Write-Host "Setting up local X12 EDI processing environment..." -ForegroundColor Green

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check if Docker is running
try {
    docker version | Out-Null
    Write-Host "Docker is running" -ForegroundColor Green
} catch {
    Write-Host "Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Check available memory
$totalMemory = (Get-CimInstance -ClassName Win32_ComputerSystem).TotalPhysicalMemory / 1GB
if ($totalMemory -lt 8) {
    Write-Host "Warning: Less than 8GB RAM detected. Performance may be impacted." -ForegroundColor Yellow
} else {
    Write-Host "Sufficient memory available ($([math]::Round($totalMemory, 1))GB)" -ForegroundColor Green
}

# Create necessary directories
Write-Host "Creating directory structure..." -ForegroundColor Yellow

$directories = @(
    "local-development\airflow\logs",
    "local-development\airflow\config", 
    "local-development\airflow\plugins",
    "local-development\notebooks-local",
    "local-development\processed\bronze",
    "local-development\processed\silver", 
    "local-development\processed\gold",
    "local-development\processed\archive"
)

foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "Created $dir" -ForegroundColor Green
    }
}

# Copy test data to input directory
Write-Host "Copying test data..." -ForegroundColor Yellow
$inputDir = "local-development\processed\input"
if (!(Test-Path $inputDir)) {
    New-Item -ItemType Directory -Path $inputDir -Force | Out-Null
}

# Copy a few sample files for testing
if (Test-Path "testdata\*.x12") {
    Copy-Item "testdata\test_x12_837_*.x12" $inputDir -Force
    Copy-Item "testdata\test_x12_835_*.x12" $inputDir -Force
    Write-Host "Copied sample X12 files to input directory" -ForegroundColor Green
}

# Set up environment file
Write-Host "Creating environment configuration..." -ForegroundColor Yellow

$envContent = @"
# Local Development Environment Configuration
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123

# Database Configuration  
POSTGRES_HOST=x12-data-db
POSTGRES_PORT=5432
POSTGRES_DB=x12_data
POSTGRES_USER=x12user
POSTGRES_PASSWORD=x12password

# Processing Configuration
BATCH_SIZE=100
MAX_FILE_SIZE_MB=50
PROCESSING_TIMEOUT_MINUTES=30

# Airflow Configuration
AIRFLOW_UID=50000
_AIRFLOW_WWW_USER_USERNAME=admin
_AIRFLOW_WWW_USER_PASSWORD=admin
"@

$envContent | Out-File -FilePath "local-development\.env" -Encoding UTF8
Write-Host "Created .env configuration file" -ForegroundColor Green

# Start services
Write-Host "Starting Docker containers..." -ForegroundColor Yellow
Set-Location "local-development"

try {
    # Build and start services
    docker-compose up -d --build
    
    Write-Host "Waiting for services to start..." -ForegroundColor Yellow
    Start-Sleep 30
    
    # Check service health
    Write-Host "Checking service health..." -ForegroundColor Yellow
    
    $services = @{
        "MinIO Storage" = "http://localhost:9000/minio/health/live"
        "PostgreSQL" = "localhost:5432"
        "Airflow" = "http://localhost:8080/health"
        "Jupyter" = "http://localhost:8888"
    }
    
    foreach ($service in $services.GetEnumerator()) {
        try {
            if ($service.Value -like "http*") {
                $response = Invoke-WebRequest -Uri $service.Value -TimeoutSec 5
                if ($response.StatusCode -eq 200) {
                    Write-Host "$($service.Key) is healthy" -ForegroundColor Green
                }
            } else {
                # For PostgreSQL, check if port is open
                $tcpClient = New-Object System.Net.Sockets.TcpClient
                $tcpClient.ConnectAsync("localhost", 5432).Wait(5000)
                if ($tcpClient.Connected) {
                    Write-Host "$($service.Key) is healthy" -ForegroundColor Green
                    $tcpClient.Close()
                }
            }
        } catch {
            Write-Host "$($service.Key) is still starting up..." -ForegroundColor Yellow
        }
    }
    
    # Initialize Airflow database (critical first step)
    Write-Host "Initializing Airflow database..." -ForegroundColor Yellow
    docker-compose exec x12-airflow airflow db init
    
    # Create Airflow admin user (one-time setup)
    Write-Host "Creating Airflow admin user..." -ForegroundColor Yellow
    docker-compose exec x12-airflow airflow users create --username admin --firstname Admin --lastname User --role Admin --email admin@example.com --password admin
    
    # Initialize database schema (critical for X12 processing)
    Write-Host "Initializing X12 database schema..." -ForegroundColor Yellow
    docker-compose exec x12-data-db psql -U x12user -d x12_data -f /docker-entrypoint-initdb.d/init.sql
    
    # Create MinIO buckets
    Write-Host "Creating storage buckets..." -ForegroundColor Yellow
    docker-compose exec x12-storage mc alias set local http://localhost:9000 minioadmin minioadmin123
    docker-compose exec x12-storage mc mb local/bronze-x12-raw 2>$null
    docker-compose exec x12-storage mc mb local/silver-x12-parsed 2>$null  
    docker-compose exec x12-storage mc mb local/gold-x12-business 2>$null
    
    Write-Host ""
    Write-Host "Local X12 processing environment is ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Access Information:" -ForegroundColor Cyan
    Write-Host "Airflow UI:      http://localhost:8080 (admin/admin)" -ForegroundColor White
    Write-Host "Jupyter Lab:     http://localhost:8888 (check logs for token)" -ForegroundColor White
    Write-Host "MinIO Console:   http://localhost:9001 (minioadmin/minioadmin123)" -ForegroundColor White
    Write-Host "PostgreSQL:      localhost:5432 (x12user/x12password)" -ForegroundColor White
    
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "1. Open Airflow UI and enable the 'x12_processing_dag' DAG"
    Write-Host "2. Upload X12 files to the input directory: local-development\processed\input"
    Write-Host "3. Monitor processing in Airflow UI"  
    Write-Host "4. View results in PostgreSQL or processed data directories"
    Write-Host "5. To process test data now, run: docker exec x12-worker python /opt/airflow/processed/process_test_data.py"
    
    Write-Host ""
    Write-Host "Quick Commands:" -ForegroundColor Magenta
    Write-Host "Stop environment:    docker-compose down"
    Write-Host "View logs:          docker-compose logs -f [service-name]"
    Write-Host "Restart services:   docker-compose restart"
    Write-Host "Full cleanup:       docker-compose down -v"
    
    # Get Jupyter token
    Write-Host ""
    Write-Host "Getting Jupyter access token..." -ForegroundColor Yellow
    Start-Sleep 5
    $jupyterLogs = docker-compose logs x12-jupyter 2>$null | Select-String "token="
    if ($jupyterLogs) {
        Write-Host "Jupyter token found in logs above" -ForegroundColor Green
    } else {
        Write-Host "To get Jupyter token, run: docker-compose logs x12-jupyter | findstr token" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "Error starting services: $_" -ForegroundColor Red
    Write-Host "Try running: docker-compose logs" -ForegroundColor Yellow
} finally {
    Set-Location ".."
}

Write-Host ""
Write-Host "For detailed documentation, see: local-development\README.md" -ForegroundColor Cyan