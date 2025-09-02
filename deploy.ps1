# Azure Fabric X12 Pipeline Deployment Script
# This script deploys the complete X12 processing pipeline infrastructure

param(
    [Parameter(Mandatory=$true)]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName = "rg-fabric-x12-pipeline",
    
    [Parameter(Mandatory=$true)]
    [string]$Location = "East US 2",
    
    [Parameter(Mandatory=$false)]
    [string]$Environment = "dev",
    
    [Parameter(Mandatory=$false)]
    [string]$ProjectName = "fabricx12"
)

# Set error handling
$ErrorActionPreference = "Stop"

Write-Host "Starting Azure Fabric X12 Pipeline deployment..." -ForegroundColor Green

# Login and set subscription
Write-Host "Setting up Azure context..." -ForegroundColor Yellow
az account set --subscription $SubscriptionId

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to set Azure subscription. Please check your subscription ID and ensure you're logged in."
    exit 1
}

# Create resource group if it doesn't exist
Write-Host "Creating resource group: $ResourceGroupName" -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create resource group."
    exit 1
}

# Update parameters file with dynamic values
Write-Host "Updating deployment parameters..." -ForegroundColor Yellow
$parametersFile = "infra/main.parameters.json"
$parameters = Get-Content $parametersFile | ConvertFrom-Json

$parameters.parameters.environment.value = $Environment
$parameters.parameters.projectName.value = $ProjectName
$parameters.parameters.location.value = $Location

$parameters | ConvertTo-Json -Depth 10 | Set-Content $parametersFile

# Deploy infrastructure
Write-Host "Deploying Azure infrastructure..." -ForegroundColor Yellow
$deploymentName = "fabric-x12-deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

az deployment group create `
    --resource-group $ResourceGroupName `
    --name $deploymentName `
    --template-file "infra/main.bicep" `
    --parameters "@infra/main.parameters.json"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Infrastructure deployment failed."
    exit 1
}

# Get deployment outputs
Write-Host "Retrieving deployment outputs..." -ForegroundColor Yellow
$outputs = az deployment group show `
    --resource-group $ResourceGroupName `
    --name $deploymentName `
    --query properties.outputs `
    --output json | ConvertFrom-Json

$storageAccountName = $outputs.storageAccountName.value
$dataFactoryName = $outputs.dataFactoryName.value
$keyVaultName = $outputs.keyVaultName.value

Write-Host "Deployment completed successfully!" -ForegroundColor Green
Write-Host "Resources created:" -ForegroundColor Cyan
Write-Host "  Storage Account: $storageAccountName" -ForegroundColor White
Write-Host "  Data Factory: $dataFactoryName" -ForegroundColor White
Write-Host "  Key Vault: $keyVaultName" -ForegroundColor White

# Update configuration file with actual resource names
Write-Host "Updating configuration with deployed resource names..." -ForegroundColor Yellow
$configFile = "config/development.json"
$config = Get-Content $configFile | ConvertFrom-Json

$config.azure.subscription_id = $SubscriptionId
$config.azure.resource_group = $ResourceGroupName
$config.azure.location = $Location
$config.azure.storage_account.name = $storageAccountName
$config.azure.data_factory.name = $dataFactoryName
$config.azure.key_vault.name = $keyVaultName

$config | ConvertTo-Json -Depth 10 | Set-Content $configFile

# Create sample X12 file for testing
Write-Host "Creating sample X12 file for testing..." -ForegroundColor Yellow
$sampleX12Content = @"
ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *$(Get-Date -Format 'yyMMdd')*$(Get-Date -Format 'HHmm')*^*00501*000000001*0*T*:~
GS*PO*SENDER*RECEIVER*$(Get-Date -Format 'yyyyMMdd')*$(Get-Date -Format 'HHmm')*1*X*005010~
ST*850*0001~
BEG*00*SA*PO123456**$(Get-Date -Format 'yyyyMMdd')~
REF*CO*CONTRACT123~
PER*BD*John Doe*TE*555-1234~
N1*ST*Ship To Company*92*12345~
N3*123 Main Street~
N4*Anytown*CA*12345*US~
PO1*1*100*EA*10.50*PE*VP*PRODUCT123~
PID*F****Sample Product Description~
PO1*2*50*EA*25.00*PE*VP*PRODUCT456~
PID*F****Another Product Description~
CTT*2*150~
SE*13*0001~
GE*1*1~
IEA*1*000000001~
"@

$sampleFilePath = "sample_x12_file.x12"
$sampleX12Content | Set-Content $sampleFilePath -Encoding ASCII

Write-Host "`nDeployment Summary:" -ForegroundColor Green
Write-Host "===================" -ForegroundColor Green
Write-Host "✓ Resource Group: $ResourceGroupName" -ForegroundColor White
Write-Host "✓ Storage Account: $storageAccountName" -ForegroundColor White
Write-Host "✓ Data Factory: $dataFactoryName" -ForegroundColor White
Write-Host "✓ Key Vault: $keyVaultName" -ForegroundColor White
Write-Host "✓ Configuration updated: $configFile" -ForegroundColor White
Write-Host "✓ Sample X12 file created: $sampleFilePath" -ForegroundColor White

Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "1. Upload the sample X12 file to the bronze container:" -ForegroundColor White
Write-Host "   az storage blob upload --account-name $storageAccountName --container-name bronze-x12-raw --name sample.x12 --file $sampleFilePath --auth-mode login" -ForegroundColor Gray

Write-Host "2. Set up Fabric workspace and import notebooks from /notebooks directory" -ForegroundColor White

Write-Host "3. Import the Data Factory pipeline from /pipelines directory" -ForegroundColor White

Write-Host "4. Configure pipeline parameters and test the processing" -ForegroundColor White

Write-Host "`nMonitoring URLs:" -ForegroundColor Cyan
Write-Host "Data Factory: https://portal.azure.com/#@/resource/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.DataFactory/factories/$dataFactoryName" -ForegroundColor Gray
Write-Host "Storage Account: https://portal.azure.com/#@/resource/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.Storage/storageAccounts/$storageAccountName" -ForegroundColor Gray

Write-Host "`nDeployment completed successfully! 🎉" -ForegroundColor Green