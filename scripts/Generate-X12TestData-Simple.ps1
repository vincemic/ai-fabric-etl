# Generate-X12TestData.ps1
# PowerShell script to generate X12 test data files for the Azure Fabric ETL pipeline

param(
    [string]$OutputPath = "test_x12_data",
    [int]$FileCount = 20,
    [string[]]$TransactionTypes = @("837", "835", "270", "271", "276", "277"),
    [switch]$Help
)

if ($Help) {
    Write-Host "Generate-X12TestData.ps1 - Generate test X12 files for Azure Fabric ETL Pipeline" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "SYNTAX:"
    Write-Host "    .\Generate-X12TestData.ps1 [-OutputPath <path>] [-FileCount <number>] [-TransactionTypes <array>] [-Help]"
    Write-Host ""
    Write-Host "PARAMETERS:"
    Write-Host "    -OutputPath        Directory to store generated test files (default: test_x12_data)"
    Write-Host "    -FileCount         Number of test files to generate (default: 20)"
    Write-Host "    -TransactionTypes  Array of transaction types to generate"
    Write-Host "    -Help              Show this help message"
    Write-Host ""
    Write-Host "EXAMPLES:"
    Write-Host "    .\Generate-X12TestData.ps1"
    Write-Host "    .\Generate-X12TestData.ps1 -FileCount 100"
    Write-Host "    .\Generate-X12TestData.ps1 -TransactionTypes @('837', '835') -FileCount 50"
    return
}

Write-Host "Azure Fabric X12 ETL Pipeline - Test Data Generator" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python detected: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.7+ to continue."
    return
}

# Create output directory if it doesn't exist
if (-not (Test-Path $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
    Write-Host "✓ Created output directory: $OutputPath" -ForegroundColor Green
}

# Check if the generator script exists
$generatorScript = Join-Path $PSScriptRoot "generate_test_x12_data.py"
if (-not (Test-Path $generatorScript)) {
    Write-Error "Test data generator script not found: $generatorScript"
    return
}

Write-Host ""
Write-Host "Generating X12 test data files..." -ForegroundColor Yellow
Write-Host "  Output Path: $OutputPath"
Write-Host "  File Count: $FileCount"
Write-Host "  Transaction Types: $($TransactionTypes -join ', ')"

try {
    # Run the Python generator
    python $generatorScript
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ Test data generation completed successfully!" -ForegroundColor Green
        
        # Display file statistics
        $generatedFiles = Get-ChildItem -Path $OutputPath -Filter "*.x12" -File -ErrorAction SilentlyContinue
        if ($generatedFiles) {
            $totalSize = ($generatedFiles | Measure-Object -Property Length -Sum).Sum
            $avgSize = $totalSize / $generatedFiles.Count
            
            Write-Host ""
            Write-Host "Generated File Statistics:" -ForegroundColor Cyan
            Write-Host "  Total Files: $($generatedFiles.Count)"
            Write-Host "  Total Size: $([math]::Round($totalSize / 1KB, 2)) KB"
            Write-Host "  Average Size: $([math]::Round($avgSize / 1024, 2)) KB per file"
        }
        
        Write-Host ""
        Write-Host "Next Steps:" -ForegroundColor Yellow
        Write-Host "1. Upload test files to your Bronze container (bronze-healthcare-x12-raw)"
        Write-Host "2. Trigger the Azure Data Factory pipeline manually"
        Write-Host "3. Monitor pipeline execution through Azure Data Factory"
        Write-Host "4. Verify processed data in Silver and Gold layers"
    }
    else {
        Write-Error "Test data generation failed with exit code: $LASTEXITCODE"
    }
}
catch {
    Write-Error "Error running test data generator: $($_.Exception.Message)"
}

Write-Host ""