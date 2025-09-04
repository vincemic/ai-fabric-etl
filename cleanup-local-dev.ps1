# X12 Local Development Environment Cleanup Script
# This script completely removes the local X12 EDI processing environment
# Run this to free up disk space and reset the environment

Write-Host "X12 Local Development Environment Cleanup" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Confirm cleanup action
$confirmation = Read-Host "This will completely remove all X12 containers, images, and data. Continue? (y/N)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "Cleanup cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Starting cleanup process..." -ForegroundColor Yellow

# Step 1: Navigate to local development directory
Write-Host "1. Navigating to local development directory..." -ForegroundColor Green
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$localDevPath = Join-Path $scriptPath "local-development"

if (Test-Path $localDevPath) {
    Set-Location $localDevPath
    Write-Host "   ✓ Changed to: $localDevPath" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Local development directory not found, continuing from current location" -ForegroundColor Yellow
}

# Step 2: Stop and remove all containers, networks, and volumes
Write-Host ""
Write-Host "2. Stopping and removing Docker containers..." -ForegroundColor Green
try {
    docker-compose down -v 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ All containers, networks, and volumes removed" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  No docker-compose environment found or already stopped" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠️  Error stopping containers: $_" -ForegroundColor Yellow
}

# Step 3: Remove X12 processing Docker images
Write-Host ""
Write-Host "3. Removing X12 processing Docker images..." -ForegroundColor Green

$imagesToRemove = @(
    "postgres:15",
    "minio/minio:latest", 
    "redis:7.2-alpine",
    "apache/airflow:2.7.0-python3.11",
    "jupyter/pyspark-notebook:latest"
)

$imagesRemoved = 0

foreach ($image in $imagesToRemove) {
    try {
        # Check if image exists
        $imageInfo = docker images $image --format "{{.Size}}" 2>$null
        if ($imageInfo) {
            # Remove the image
            docker rmi $image --force 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "   ✓ Removed: $image" -ForegroundColor Green
                $imagesRemoved++
            } else {
                Write-Host "   ⚠️  Could not remove: $image" -ForegroundColor Yellow
            }
        } else {
            Write-Host "   ℹ️  Not found: $image" -ForegroundColor Gray
        }
    } catch {
        Write-Host "   ⚠️  Error removing $image`: $_" -ForegroundColor Yellow
    }
}

Write-Host "   📊 Summary: $imagesRemoved images removed" -ForegroundColor Cyan

# Step 4: Clean up Docker system (dangling images, cache, etc.)
Write-Host ""
Write-Host "4. Cleaning up Docker system..." -ForegroundColor Green
try {
    $pruneOutput = docker system prune -f 2>$null
    Write-Host "   ✓ Docker system cleanup completed" -ForegroundColor Green
    if ($pruneOutput -match "Total reclaimed space: (.+)") {
        Write-Host "   📊 Additional space reclaimed: $($matches[1])" -ForegroundColor Cyan
    }
} catch {
    Write-Host "   ⚠️  Error during system cleanup: $_" -ForegroundColor Yellow
}

# Step 5: Verify cleanup
Write-Host ""
Write-Host "5. Verifying cleanup..." -ForegroundColor Green

# Check containers
$containers = docker ps -a --format "{{.Names}}" 2>$null | Where-Object { $_ -like "x12-*" }
if ($containers) {
    Write-Host "   ⚠️  Some X12 containers still exist:" -ForegroundColor Yellow
    $containers | ForEach-Object { Write-Host "      - $_" -ForegroundColor Yellow }
} else {
    Write-Host "   ✓ No X12 containers remaining" -ForegroundColor Green
}

# Check images  
$x12Images = docker images --format "{{.Repository}}:{{.Tag}}" 2>$null | Where-Object { 
    $_ -match "postgres:15|minio/minio:latest|redis:7.2-alpine|apache/airflow:2.7.0-python3.11|jupyter/pyspark-notebook:latest" 
}
if ($x12Images) {
    Write-Host "   ⚠️  Some X12 images still exist:" -ForegroundColor Yellow
    $x12Images | ForEach-Object { Write-Host "      - $_" -ForegroundColor Yellow }
} else {
    Write-Host "   ✓ No X12 images remaining" -ForegroundColor Green
}

# Check volumes
$x12Volumes = docker volume ls --format "{{.Name}}" 2>$null | Where-Object { $_ -like "*x12*" -or $_ -like "*local-development*" }
if ($x12Volumes) {
    Write-Host "   ⚠️  Some X12 volumes still exist:" -ForegroundColor Yellow
    $x12Volumes | ForEach-Object { Write-Host "      - $_" -ForegroundColor Yellow }
} else {
    Write-Host "   ✓ No X12 volumes remaining" -ForegroundColor Green
}

# Step 6: Cleanup local directories (optional)
Write-Host ""
Write-Host "6. Local directory cleanup (optional)..." -ForegroundColor Green

$directoriesToClean = @(
    "local-development\airflow\logs",
    "local-development\processed\input", 
    "local-development\processed\bronze",
    "local-development\processed\silver",
    "local-development\processed\gold",
    "local-development\processed\archive"
)

$cleanDirs = Read-Host "   Remove local processing directories? This will delete logs and processed files (y/N)"
if ($cleanDirs -eq 'y' -or $cleanDirs -eq 'Y') {
    foreach ($dir in $directoriesToClean) {
        if (Test-Path $dir) {
            try {
                Remove-Item -Path $dir -Recurse -Force
                Write-Host "   ✓ Cleaned: $dir" -ForegroundColor Green
            } catch {
                Write-Host "   ⚠️  Could not clean: $dir - $_" -ForegroundColor Yellow
            }
        }
    }
} else {
    Write-Host "   ℹ️  Local directories preserved" -ForegroundColor Gray
}

# Final summary
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "CLEANUP COMPLETED" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor White
Write-Host "✓ Docker containers removed" -ForegroundColor Green
Write-Host "✓ Docker networks removed" -ForegroundColor Green  
Write-Host "✓ Docker volumes removed" -ForegroundColor Green
Write-Host "✓ Docker images removed ($imagesRemoved images)" -ForegroundColor Green
Write-Host "✓ System cache cleaned" -ForegroundColor Green
Write-Host ""
Write-Host "Next time you run the environment:" -ForegroundColor Yellow
Write-Host "• Run: .\setup-local-dev.ps1" -ForegroundColor White
Write-Host "• Fresh images will be downloaded (~7GB)" -ForegroundColor White  
Write-Host "• Complete environment will be rebuilt" -ForegroundColor White
Write-Host ""
Write-Host "Space freed: Approximately 7+ GB" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎉 X12 local development environment completely removed!" -ForegroundColor Green