# Azure X12 Pipeline Cost Analysis Script
# This script helps analyze and estimate costs for the Azure Fabric X12 ETL pipeline

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory=$false)]
    [int]$DaysToAnalyze = 30,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = ".\cost-analysis-report.json"
)

# Function to get Azure costs for resource group
function Get-ResourceGroupCosts {
    param(
        [string]$ResourceGroup,
        [string]$Subscription,
        [int]$Days
    )
    
    Write-Host "Analyzing costs for Resource Group: $ResourceGroup" -ForegroundColor Green
    
    $startDate = (Get-Date).AddDays(-$Days).ToString("yyyy-MM-dd")
    $endDate = (Get-Date).ToString("yyyy-MM-dd")
    
    try {
        # Get cost data using Azure CLI
        $costData = az consumption usage list `
            --subscription $Subscription `
            --start-date $startDate `
            --end-date $endDate `
            --query "[?contains(instanceName, '$ResourceGroup')]" | ConvertFrom-Json
        
        return $costData
    }
    catch {
        Write-Error "Failed to retrieve cost data: $_"
        return $null
    }
}

# Function to analyze storage costs
function Get-StorageCostAnalysis {
    param(
        [string]$StorageAccountName,
        [string]$ResourceGroup
    )
    
    Write-Host "Analyzing storage costs for: $StorageAccountName" -ForegroundColor Yellow
    
    try {
        # Get storage metrics
        $metrics = az monitor metrics list `
            --resource "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.Storage/storageAccounts/$StorageAccountName" `
            --metric "UsedCapacity" `
            --aggregation Average `
            --start-time (Get-Date).AddDays(-7).ToString("yyyy-MM-ddTHH:mm:ssZ") `
            --end-time (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ") | ConvertFrom-Json
        
        $latestUsage = $metrics.value[0].timeseries[0].data[-1].average
        $usageGB = [math]::Round($latestUsage / 1GB, 2)
        
        # Estimate monthly costs based on current usage
        $hotTierCost = $usageGB * 0.0208 # Hot tier pricing
        $coolTierCost = $usageGB * 0.0115 # Cool tier pricing
        $archiveTierCost = $usageGB * 0.002 # Archive tier pricing
        
        return @{
            CurrentUsageGB = $usageGB
            EstimatedMonthlyCosts = @{
                HotTier = $hotTierCost
                CoolTier = $coolTierCost
                ArchiveTier = $archiveTierCost
            }
        }
    }
    catch {
        Write-Warning "Could not retrieve storage metrics: $_"
        return $null
    }
}

# Function to analyze Data Factory costs
function Get-DataFactoryCostAnalysis {
    param(
        [string]$DataFactoryName,
        [string]$ResourceGroup
    )
    
    Write-Host "Analyzing Data Factory costs for: $DataFactoryName" -ForegroundColor Yellow
    
    try {
        # Get pipeline run metrics
        $pipelineRuns = az monitor metrics list `
            --resource "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.DataFactory/factories/$DataFactoryName" `
            --metric "PipelineRuns" `
            --aggregation Total `
            --start-time (Get-Date).AddDays(-30).ToString("yyyy-MM-ddTHH:mm:ssZ") `
            --end-time (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ") | ConvertFrom-Json
        
        if ($pipelineRuns.value.Count -gt 0) {
            $totalRuns = ($pipelineRuns.value[0].timeseries[0].data | Measure-Object -Property total -Sum).Sum
            $estimatedMonthlyCost = ($totalRuns / 1000) * 1.00 # $1 per 1000 pipeline activities
            
            return @{
                MonthlyPipelineRuns = $totalRuns
                EstimatedMonthlyCost = $estimatedMonthlyCost
            }
        }
        else {
            Write-Warning "No pipeline run data available"
            return $null
        }
    }
    catch {
        Write-Warning "Could not retrieve Data Factory metrics: $_"
        return $null
    }
}

# Function to estimate costs based on transaction volume
function Get-TransactionVolumeEstimate {
    param(
        [int]$TransactionsPerMonth,
        [int]$AverageFileSizeKB = 75
    )
    
    Write-Host "Estimating costs for $TransactionsPerMonth transactions/month" -ForegroundColor Cyan
    
    $totalDataGB = ($TransactionsPerMonth * $AverageFileSizeKB) / 1024 / 1024
    
    # Storage costs (assuming mixed tier strategy)
    $hotTierData = $totalDataGB * 0.3  # 30% in hot tier
    $coolTierData = $totalDataGB * 0.5  # 50% in cool tier
    $archiveTierData = $totalDataGB * 0.2  # 20% in archive tier
    
    $storageCost = ($hotTierData * 0.0208) + ($coolTierData * 0.0115) + ($archiveTierData * 0.002)
    
    # Data Factory costs (assuming 3 activities per transaction)
    $pipelineActivities = $TransactionsPerMonth * 3
    $dataFactoryCost = ($pipelineActivities / 1000) * 1.00
    
    # Function costs (assuming 2 function calls per transaction, 512MB, 30 seconds each)
    $functionExecutions = $TransactionsPerMonth * 2
    $functionGBSeconds = $functionExecutions * 0.5 * 30 # 512MB * 30 seconds
    $functionCost = ($functionGBSeconds * 0.000016) + (($functionExecutions / 1000000) * 0.20)
    
    # Monitoring costs (assuming 5% of total)
    $monitoringCost = ($storageCost + $dataFactoryCost + $functionCost) * 0.05
    
    $totalEstimatedCost = $storageCost + $dataFactoryCost + $functionCost + $monitoringCost
    
    return @{
        TransactionsPerMonth = $TransactionsPerMonth
        TotalDataGB = [math]::Round($totalDataGB, 2)
        CostBreakdown = @{
            Storage = [math]::Round($storageCost, 2)
            DataFactory = [math]::Round($dataFactoryCost, 2)
            Functions = [math]::Round($functionCost, 2)
            Monitoring = [math]::Round($monitoringCost, 2)
        }
        TotalEstimatedCost = [math]::Round($totalEstimatedCost, 2)
        CostPerTransaction = [math]::Round(($totalEstimatedCost / $TransactionsPerMonth), 6)
    }
}

# Function to generate cost optimization recommendations
function Get-CostOptimizationRecommendations {
    param(
        [hashtable]$CostAnalysis
    )
    
    $recommendations = @()
    
    # Storage optimization recommendations
    if ($CostAnalysis.StorageAnalysis -and $CostAnalysis.StorageAnalysis.CurrentUsageGB -gt 100) {
        $recommendations += @{
            Category = "Storage"
            Priority = "High"
            Recommendation = "Implement lifecycle management to move data to cooler tiers"
            PotentialSavings = "40-60% on storage costs"
        }
    }
    
    # Data Factory optimization recommendations
    if ($CostAnalysis.DataFactoryAnalysis -and $CostAnalysis.DataFactoryAnalysis.MonthlyPipelineRuns -gt 1000) {
        $recommendations += @{
            Category = "Data Factory"
            Priority = "Medium"
            Recommendation = "Optimize pipeline runs by batching activities and using parallel processing"
            PotentialSavings = "25-35% on Data Factory costs"
        }
    }
    
    # General recommendations
    $recommendations += @{
        Category = "Monitoring"
        Priority = "Medium"
        Recommendation = "Configure Log Analytics retention policies and use Basic Log tables for debug data"
        PotentialSavings = "30-50% on monitoring costs"
    }
    
    $recommendations += @{
        Category = "Functions"
        Priority = "Low"
        Recommendation = "Review function memory allocation and optimize execution time"
        PotentialSavings = "20-40% on compute costs"
    }
    
    return $recommendations
}

# Main execution
Write-Host "Starting Azure X12 Pipeline Cost Analysis..." -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green

# Set Azure subscription context
try {
    az account set --subscription $SubscriptionId
    Write-Host "Set subscription context to: $SubscriptionId" -ForegroundColor Green
}
catch {
    Write-Error "Failed to set subscription context: $_"
    exit 1
}

# Initialize results object
$results = @{
    AnalysisDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    ResourceGroup = $ResourceGroupName
    SubscriptionId = $SubscriptionId
    AnalysisPeriodDays = $DaysToAnalyze
}

# Get resource group costs
Write-Host "`nGetting resource group cost data..." -ForegroundColor Yellow
$resourceGroupCosts = Get-ResourceGroupCosts -ResourceGroup $ResourceGroupName -Subscription $SubscriptionId -Days $DaysToAnalyze
$results.ResourceGroupCosts = $resourceGroupCosts

# Find and analyze storage account
Write-Host "`nFinding storage account..." -ForegroundColor Yellow
try {
    $storageAccounts = az storage account list --resource-group $ResourceGroupName --query "[].name" -o tsv
    if ($storageAccounts) {
        $storageAccountName = $storageAccounts.Split("`n")[0].Trim()
        Write-Host "Found storage account: $storageAccountName" -ForegroundColor Green
        $results.StorageAnalysis = Get-StorageCostAnalysis -StorageAccountName $storageAccountName -ResourceGroup $ResourceGroupName
    }
}
catch {
    Write-Warning "Could not find or analyze storage account: $_"
}

# Find and analyze Data Factory
Write-Host "`nFinding Data Factory..." -ForegroundColor Yellow
try {
    $dataFactories = az datafactory list --resource-group $ResourceGroupName --query "[].name" -o tsv
    if ($dataFactories) {
        $dataFactoryName = $dataFactories.Split("`n")[0].Trim()
        Write-Host "Found Data Factory: $dataFactoryName" -ForegroundColor Green
        $results.DataFactoryAnalysis = Get-DataFactoryCostAnalysis -DataFactoryName $dataFactoryName -ResourceGroup $ResourceGroupName
    }
}
catch {
    Write-Warning "Could not find or analyze Data Factory: $_"
}

# Generate cost estimates for different volumes
Write-Host "`nGenerating cost estimates for different transaction volumes..." -ForegroundColor Yellow
$volumeScenarios = @(1000, 10000, 100000, 1000000, 10000000)
$results.CostEstimates = @{}

foreach ($volume in $volumeScenarios) {
    $estimate = Get-TransactionVolumeEstimate -TransactionsPerMonth $volume
    $results.CostEstimates["${volume}_transactions"] = $estimate
}

# Generate optimization recommendations
Write-Host "`nGenerating cost optimization recommendations..." -ForegroundColor Yellow
$results.Recommendations = Get-CostOptimizationRecommendations -CostAnalysis $results

# Output results
Write-Host "`nSaving results to: $OutputPath" -ForegroundColor Green
$results | ConvertTo-Json -Depth 10 | Out-File -FilePath $OutputPath -Encoding UTF8

# Display summary
Write-Host "`n=======================================" -ForegroundColor Green
Write-Host "COST ANALYSIS SUMMARY" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green

if ($results.StorageAnalysis) {
    Write-Host "Current Storage Usage: $($results.StorageAnalysis.CurrentUsageGB) GB" -ForegroundColor Cyan
    Write-Host "Estimated Monthly Storage Cost (Hot): $($results.StorageAnalysis.EstimatedMonthlyCosts.HotTier)" -ForegroundColor Cyan
}

if ($results.DataFactoryAnalysis) {
    Write-Host "Monthly Pipeline Runs: $($results.DataFactoryAnalysis.MonthlyPipelineRuns)" -ForegroundColor Cyan
    Write-Host "Estimated Monthly Data Factory Cost: $($results.DataFactoryAnalysis.EstimatedMonthlyCost)" -ForegroundColor Cyan
}

Write-Host "`nCost Estimates by Transaction Volume:" -ForegroundColor Yellow
foreach ($scenario in $results.CostEstimates.Keys | Sort-Object) {
    $estimate = $results.CostEstimates[$scenario]
    Write-Host "  $($estimate.TransactionsPerMonth) transactions/month: $($estimate.TotalEstimatedCost) USD" -ForegroundColor White
}

Write-Host "`nTop Recommendations:" -ForegroundColor Yellow
$results.Recommendations | Where-Object { $_.Priority -eq "High" } | ForEach-Object {
    Write-Host "  - $($_.Recommendation) (Potential savings: $($_.PotentialSavings))" -ForegroundColor White
}

Write-Host "`nComplete analysis saved to: $OutputPath" -ForegroundColor Green
Write-Host "Review the cost estimation guide for detailed optimization strategies." -ForegroundColor Green