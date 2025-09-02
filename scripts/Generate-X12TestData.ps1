# Generate-X12TestData.ps1
# PowerShell script to generate X12 test data files for the Azure Fabric ETL pipeline

param(
    [Parameter()]
    [string]$OutputPath = "test_x12_data",
    
    [Parameter()]
    [int]$FileCount = 20,
    
    [Parameter()]
    [string[]]$TransactionTypes = @("837", "835", "270", "271", "276", "277"),
    
    [Parameter()]
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Generate-X12TestData.ps1 - Generate test X12 files for Azure Fabric ETL Pipeline

SYNTAX:
    .\Generate-X12TestData.ps1 [-OutputPath <path>] [-FileCount <number>] [-TransactionTypes <array>] [-Help]

PARAMETERS:
    -OutputPath        Directory to store generated test files (default: test_x12_data)
    -FileCount         Number of test files to generate (default: 20)
    -TransactionTypes  Array of transaction types to generate (default: 837,835,270,271,276,277)
    -Help              Show this help message

EXAMPLES:
    # Generate 20 test files (default)
    .\Generate-X12TestData.ps1
    
    # Generate 100 test files for load testing
    .\Generate-X12TestData.ps1 -FileCount 100
    
    # Generate only claim files (837, 835)
    .\Generate-X12TestData.ps1 -TransactionTypes @("837", "835") -FileCount 50
    
    # Generate files in specific directory
    .\Generate-X12TestData.ps1 -OutputPath "C:\temp\x12_test_data" -FileCount 10

SUPPORTED TRANSACTION TYPES:
    837 - Health Care Claim (Professional, Institutional, Dental)
    835 - Health Care Claim Payment/Advice (Remittance Advice)
    834 - Benefit Enrollment and Maintenance (Insurance Enrollment)
    270 - Health Care Eligibility Benefit Inquiry
    271 - Health Care Eligibility Benefit Response
    276 - Health Care Claim Status Request
    277 - Health Care Claim Status Response
    278 - Health Care Services Review Request (Preauthorization)
    279 - Health Care Services Review Response (Preauthorization)
"@
    return
}

Write-Host "Azure Fabric X12 ETL Pipeline - Test Data Generator" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan

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

Write-Host "`nGenerating X12 test data files..." -ForegroundColor Yellow
Write-Host "  Output Path: $OutputPath"
Write-Host "  File Count: $FileCount"
Write-Host "  Transaction Types: $($TransactionTypes -join ', ')"

try {
    # Run the Python generator
    $env:X12_OUTPUT_PATH = $OutputPath
    $env:X12_FILE_COUNT = $FileCount
    $env:X12_TRANSACTION_TYPES = $TransactionTypes -join ","
    
    python $generatorScript
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✓ Test data generation completed successfully!" -ForegroundColor Green
        
        # Display file statistics
        $generatedFiles = Get-ChildItem -Path $OutputPath -Filter "*.x12" -File
        $totalSize = ($generatedFiles | Measure-Object -Property Length -Sum).Sum
        $avgSize = if ($generatedFiles.Count -gt 0) { $totalSize / $generatedFiles.Count } else { 0 }
        
        Write-Host "`nGenerated File Statistics:" -ForegroundColor Cyan
        Write-Host "  Total Files: $($generatedFiles.Count)"
        Write-Host "  Total Size: $([math]::Round($totalSize / 1KB, 2)) KB"
        Write-Host "  Average Size: $([math]::Round($avgSize / 1024, 2)) KB per file"
        
        # Group by transaction type
        $typeGroups = $generatedFiles | Group-Object { ($_.Name -split '_')[2] }
        Write-Host "`nFiles by Transaction Type:"
        foreach ($group in $typeGroups) {
            $transactionType = $group.Name
            $count = $group.Count
            $description = switch ($transactionType) {
                "837" { "Health Care Claim" }
                "835" { "Health Care Payment/Advice" }
                "834" { "Benefit Enrollment" }
                "270" { "Eligibility Inquiry" }
                "271" { "Eligibility Response" }
                "276" { "Claim Status Request" }
                "277" { "Claim Status Response" }
                "278" { "Services Review Request" }
                "279" { "Services Review Response" }
                default { "Unknown" }
            }
            Write-Host "  $transactionType ($description): $count files"
        }
        
        Write-Host "`nNext Steps:" -ForegroundColor Yellow
        Write-Host "1. Upload test files to your Bronze container (bronze-healthcare-x12-raw)"
        Write-Host "2. Trigger the Azure Data Factory pipeline manually or wait for scheduled trigger"
        Write-Host "3. Monitor pipeline execution through Azure Data Factory monitoring"
        Write-Host "4. Verify processed data in Silver and Gold layers"
        
        Write-Host "`nAzure Storage Upload Example:" -ForegroundColor Cyan
        Write-Host "  az storage blob upload-batch ``"
        Write-Host "    --destination bronze-healthcare-x12-raw ``"
        Write-Host "    --source $OutputPath ``"
        Write-Host "    --account-name YOUR_STORAGE_ACCOUNT"
        
    }
    else {
        Write-Error "Test data generation failed with exit code: $LASTEXITCODE"
    }
}
catch {
    Write-Error "Error running test data generator: $($_.Exception.Message)"
}

Write-Host ""