# Azure Fabric X12 Pipeline Deployment Script with SFTP Support
# This script deploys the complete X12 processing pipeline infrastructure including SFTP trading partner connectivity

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
    [string]$ProjectName = "fabricx12",
    
    [Parameter(Mandatory=$false)]
    [string]$AdminPrincipalId = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$ConfigureSFTP,
    
    [Parameter(Mandatory=$false)]
    [string]$TradingPartnerConfigFile = ""
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
Write-Host "✓ SFTP Function App: $sftpFunctionAppName" -ForegroundColor White
Write-Host "✓ Configuration updated: $configFile" -ForegroundColor White
Write-Host "✓ Sample X12 file created: $sampleFilePath" -ForegroundColor White

# Configure SFTP if requested
if ($ConfigureSFTP) {
    Write-Host "`n🔧 Configuring SFTP Trading Partner Integration..." -ForegroundColor Cyan
    
    # Get Key Vault URI
    $keyVaultUri = az keyvault show --name $keyVaultName --resource-group $ResourceGroupName --query "properties.vaultUri" --output tsv
    
    # Set trading partner secrets if config file provided
    if ($TradingPartnerConfigFile) {
        Set-TradingPartnerSecrets -KeyVaultName $keyVaultName -PartnerConfigFile $TradingPartnerConfigFile
    }
    
    # Configure SFTP Function environment variables
    Configure-SFTPEnvironmentVariables -FunctionAppName $sftpFunctionAppName -ResourceGroupName $ResourceGroupName -KeyVaultUri $keyVaultUri -StorageAccountName $storageAccountName
    
    # Deploy SFTP Functions
    Deploy-SFTPFunctions -FunctionAppName $sftpFunctionAppName -ResourceGroupName $ResourceGroupName
    
    Write-Host "✓ SFTP Configuration completed" -ForegroundColor Green
}

Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "1. Upload the sample X12 file to the bronze container:" -ForegroundColor White
Write-Host "   az storage blob upload --account-name $storageAccountName --container-name bronze-x12-raw --name sample.x12 --file $sampleFilePath --auth-mode login" -ForegroundColor Gray

Write-Host "2. Set up Fabric workspace and import notebooks from /notebooks directory" -ForegroundColor White

Write-Host "3. Import the Data Factory pipeline from /pipelines directory" -ForegroundColor White

Write-Host "4. Configure pipeline parameters and test the processing" -ForegroundColor White

if ($ConfigureSFTP) {
    Write-Host "5. Configure trading partner SFTP connection details:" -ForegroundColor White
    Write-Host "   - Update Function App environment variables with partner hosts and usernames" -ForegroundColor Gray
    Write-Host "   - Upload private keys and host keys to Key Vault" -ForegroundColor Gray
    Write-Host "   - Test SFTP connections using the health check function" -ForegroundColor Gray
    
    Write-Host "6. Set up monitoring alerts in Application Insights:" -ForegroundColor White
    Write-Host "   - Import alert configurations from /monitoring/sftp-alerts-config.json" -ForegroundColor Gray
    Write-Host "   - Configure notification webhooks and email recipients" -ForegroundColor Gray
}

Write-Host "`nMonitoring URLs:" -ForegroundColor Cyan
Write-Host "Data Factory: https://portal.azure.com/#@/resource/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.DataFactory/factories/$dataFactoryName" -ForegroundColor Gray
Write-Host "Storage Account: https://portal.azure.com/#@/resource/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.Storage/storageAccounts/$storageAccountName" -ForegroundColor Gray
if ($ConfigureSFTP) {
    Write-Host "SFTP Function App: https://portal.azure.com/#@/resource/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.Web/sites/$sftpFunctionAppName" -ForegroundColor Gray
    Write-Host "Key Vault: https://portal.azure.com/#@/resource/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.KeyVault/vaults/$keyVaultName" -ForegroundColor Gray
}

Write-Host "`nSFTP Functions Deployment:" -ForegroundColor Cyan
if ($ConfigureSFTP) {
    Write-Host "To manually deploy SFTP functions:" -ForegroundColor White
    Write-Host "  cd functions/sftp-operations" -ForegroundColor Gray
    Write-Host "  func azure functionapp publish $sftpFunctionAppName --python" -ForegroundColor Gray
} else {
    Write-Host "To enable SFTP functionality, re-run with -ConfigureSFTP flag:" -ForegroundColor White
    Write-Host "  .\deploy.ps1 -SubscriptionId $SubscriptionId -ResourceGroupName $ResourceGroupName -Location '$Location' -ConfigureSFTP" -ForegroundColor Gray
}

Write-Host "`nDeployment completed successfully! 🎉" -ForegroundColor Green

# Functions for SFTP Configuration
function Set-TradingPartnerSecrets {
    param(
        [string]$KeyVaultName,
        [string]$PartnerConfigFile
    )
    
    if (-not $PartnerConfigFile -or -not (Test-Path $PartnerConfigFile)) {
        Write-Host "⚠️  No trading partner config file provided or file not found" -ForegroundColor Yellow
        Write-Host "   Please manually configure Key Vault secrets for trading partners:" -ForegroundColor Gray
        Write-Host "   - sftp-bcbs001-private-key" -ForegroundColor Gray
        Write-Host "   - sftp-bcbs001-host-key" -ForegroundColor Gray
        Write-Host "   - sftp-aetna02-password" -ForegroundColor Gray
        Write-Host "   - sftp-aetna02-host-key" -ForegroundColor Gray
        return
    }
    
    Write-Host "📁 Configuring trading partner secrets..." -ForegroundColor Yellow
    
    try {
        $partnerConfig = Get-Content $PartnerConfigFile | ConvertFrom-Json
        
        foreach ($partner in $partnerConfig.partners) {
            $partnerId = $partner.id
            
            if ($partner.connection.authentication_method -eq "key") {
                $keySecretName = $partner.connection.key_vault_secret_name
                if ($partner.private_key_file -and (Test-Path $partner.private_key_file)) {
                    $privateKey = Get-Content $partner.private_key_file -Raw
                    az keyvault secret set --vault-name $KeyVaultName --name $keySecretName --value $privateKey
                    Write-Host "   ✓ Set private key for $partnerId" -ForegroundColor Green
                }
            }
            
            if ($partner.connection.authentication_method -eq "password") {
                $passwordSecretName = $partner.connection.password_secret_name
                if ($partner.password) {
                    az keyvault secret set --vault-name $KeyVaultName --name $passwordSecretName --value $partner.password
                    Write-Host "   ✓ Set password for $partnerId" -ForegroundColor Green
                }
            }
            
            # Set host key if provided
            $hostKeySecretName = $partner.connection.host_key_secret_name
            if ($partner.host_key_file -and (Test-Path $partner.host_key_file)) {
                $hostKey = Get-Content $partner.host_key_file -Raw
                az keyvault secret set --vault-name $KeyVaultName --name $hostKeySecretName --value $hostKey
                Write-Host "   ✓ Set host key for $partnerId" -ForegroundColor Green
            }
        }
        
        Write-Host "✓ Trading partner secrets configured successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Failed to configure trading partner secrets: $_" -ForegroundColor Red
    }
}

function Deploy-SFTPFunctions {
    param(
        [string]$FunctionAppName,
        [string]$ResourceGroupName
    )
    
    Write-Host "🔧 Deploying SFTP Functions..." -ForegroundColor Yellow
    
    $functionsPath = "functions/sftp-operations"
    
    if (-not (Test-Path $functionsPath)) {
        Write-Host "❌ SFTP Functions directory not found: $functionsPath" -ForegroundColor Red
        return $false
    }
    
    try {
        # Copy source modules to functions directory
        if (Test-Path "src/sftp") {
            Copy-Item -Path "src/sftp" -Destination "$functionsPath/" -Recurse -Force
            Write-Host "   ✓ Copied SFTP modules to functions directory" -ForegroundColor Green
        }
        
        Write-Host "   📦 Functions directory prepared" -ForegroundColor Gray
        Write-Host "   Use Azure Functions Core Tools to deploy:" -ForegroundColor Gray
        Write-Host "     cd $functionsPath" -ForegroundColor Gray
        Write-Host "     func azure functionapp publish $FunctionAppName --python" -ForegroundColor Gray
        
        return $true
    }
    catch {
        Write-Host "❌ Failed to prepare SFTP Functions: $_" -ForegroundColor Red
        return $false
    }
}

function Configure-SFTPEnvironmentVariables {
    param(
        [string]$FunctionAppName,
        [string]$ResourceGroupName,
        [string]$KeyVaultUri,
        [string]$StorageAccountName
    )
    
    Write-Host "⚙️  Configuring SFTP Function environment variables..." -ForegroundColor Yellow
    
    # Set environment variables for trading partner connections
    $envVars = @{
        "BCBS001_HOST" = ""  # To be set manually or from config
        "BCBS001_PORT" = "22"
        "BCBS001_USERNAME" = ""  # To be set manually or from config
        "BCBS001_INBOUND_DIR" = "/inbound/x12"
        "BCBS001_OUTBOUND_DIR" = "/outbound/x12"
        "BCBS001_PROCESSED_DIR" = "/processed"
        
        "AETNA02_HOST" = ""  # To be set manually or from config
        "AETNA02_PORT" = "22"
        "AETNA02_USERNAME" = ""  # To be set manually or from config
        "AETNA02_INBOUND_DIR" = "/edi/incoming"
        "AETNA02_OUTBOUND_DIR" = "/edi/outgoing"
        "AETNA02_PROCESSED_DIR" = "/edi/archive"
    }
    
    foreach ($key in $envVars.Keys) {
        if ($envVars[$key] -ne "") {
            az functionapp config appsettings set --name $FunctionAppName --resource-group $ResourceGroupName --settings "$key=$($envVars[$key])" | Out-Null
        }
    }
    
    Write-Host "✓ Base environment variables configured" -ForegroundColor Green
    Write-Host "⚠️  Please manually set trading partner host and username values:" -ForegroundColor Yellow
    Write-Host "   az functionapp config appsettings set --name $FunctionAppName --resource-group $ResourceGroupName --settings 'BCBS001_HOST=your-bcbs-host'" -ForegroundColor Gray
    Write-Host "   az functionapp config appsettings set --name $FunctionAppName --resource-group $ResourceGroupName --settings 'BCBS001_USERNAME=your-bcbs-username'" -ForegroundColor Gray
    Write-Host "   az functionapp config appsettings set --name $FunctionAppName --resource-group $ResourceGroupName --settings 'AETNA02_HOST=your-aetna-host'" -ForegroundColor Gray
    Write-Host "   az functionapp config appsettings set --name $FunctionAppName --resource-group $ResourceGroupName --settings 'AETNA02_USERNAME=your-aetna-username'" -ForegroundColor Gray
}