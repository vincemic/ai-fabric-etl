# SFTP Trading Partner Quick Setup Guide

## Overview
This guide provides step-by-step instructions to quickly set up SFTP trading partner connectivity for the X12 EDI processing pipeline.

## Prerequisites
- Azure subscription with appropriate permissions
- Trading partner SFTP server details
- SSH keys or passwords for authentication
- Azure CLI installed and authenticated

## Step 1: Deploy Infrastructure

### Basic Deployment
```powershell
# Clone repository and navigate to project directory
git clone <repository-url>
cd ai-fabric-etl

# Deploy basic infrastructure
.\deploy.ps1 -SubscriptionId "your-subscription-id" `
            -ResourceGroupName "rg-x12-pipeline" `
            -Location "East US 2"
```

### SFTP-Enabled Deployment
```powershell
# Deploy with SFTP support enabled
.\deploy.ps1 -SubscriptionId "your-subscription-id" `
            -ResourceGroupName "rg-x12-pipeline" `
            -Location "East US 2" `
            -ConfigureSFTP
```

## Step 2: Configure Trading Partners

### 2.1 Create Partner Configuration
Copy the sample configuration and update with your partner details:

```powershell
# Copy sample configuration
Copy-Item "trading-partners-config.sample.json" "trading-partners-config.json"

# Edit the configuration file with your partner details
notepad trading-partners-config.json
```

### 2.2 Update Partner Details
Edit `trading-partners-config.json` to include:
- Partner SFTP host and port
- Username and authentication method
- Directory paths
- File patterns and transaction types

## Step 3: Configure Security

### 3.1 Store SSH Keys in Key Vault
```bash
# Store private key for key-based authentication
az keyvault secret set --vault-name "your-key-vault-name" \
                      --name "sftp-partner001-private-key" \
                      --file "path/to/private-key.pem"

# Store host key for server verification
az keyvault secret set --vault-name "your-key-vault-name" \
                      --name "sftp-partner001-host-key" \
                      --value "ssh-rsa AAAAB3NzaC1yc2E..."
```

### 3.2 Configure Function App Settings
```bash
# Set partner connection details
az functionapp config appsettings set \
  --name "your-sftp-function-app" \
  --resource-group "your-resource-group" \
  --settings "PARTNER001_HOST=sftp.partner.com" \
             "PARTNER001_USERNAME=username" \
             "PARTNER001_INBOUND_DIR=/inbound"
```

## Step 4: Deploy SFTP Functions

### 4.1 Install Azure Functions Core Tools
```powershell
# Install via npm (if not already installed)
npm install -g azure-functions-core-tools@4 --unsafe-perm true
```

### 4.2 Deploy Functions
```powershell
# Navigate to functions directory
cd functions/sftp-operations

# Deploy functions
func azure functionapp publish your-sftp-function-app-name --python
```

## Step 5: Test Connectivity

### 5.1 Test Local Development Environment
```powershell
# Start local development environment
cd local-development
docker-compose up -d

# Test SFTP connections
docker exec -it x12-sftp-test-client python tests/test_sftp_connections.py
```

### 5.2 Test Production Connectivity
```bash
# Trigger health check function manually
curl -X POST "https://your-function-app.azurewebsites.net/api/health_check"

# Check Application Insights for results
```

## Step 6: Configure Monitoring

### 6.1 Set Up Alerts
Import the provided alert configuration:

```bash
# Import alerts (requires Azure CLI extension)
az monitor scheduled-query create --name "SFTP-High-Failure-Rate" \
                                 --resource-group "your-resource-group" \
                                 --query-file "monitoring/sftp-alerts-config.json"
```

### 6.2 Create Dashboard
1. Open Azure Portal
2. Navigate to Application Insights
3. Create new dashboard
4. Import queries from `monitoring/sftp-monitoring-queries.md`

## Step 7: Verify End-to-End Operation

### 7.1 Place Test Files
Place test X12 files in partner SFTP inbound directories

### 7.2 Monitor Processing
1. Check SFTP fetch function logs
2. Verify files appear in Bronze storage container
3. Monitor Data Factory pipeline execution
4. Confirm acknowledgments are generated and sent

## Common Issues and Quick Fixes

### Authentication Failures
```bash
# Verify Key Vault secrets
az keyvault secret show --vault-name "your-key-vault" --name "sftp-partner001-private-key"

# Test SSH connection manually
ssh -i private_key.pem username@sftp.partner.com
```

### Function App Errors
```bash
# Check function app logs
az functionapp log tail --name "your-function-app" --resource-group "your-resource-group"

# Restart function app
az functionapp restart --name "your-function-app" --resource-group "your-resource-group"
```

### Network Connectivity
```bash
# Test network connectivity from Function App
az functionapp show --name "your-function-app" --resource-group "your-resource-group"

# Check outbound IP addresses and firewall rules
```

## Next Steps

1. **Production Readiness**: Review security settings and enable all monitoring
2. **Partner Onboarding**: Add additional trading partners using the same process
3. **Performance Tuning**: Optimize fetch/push schedules based on volume
4. **Backup and Recovery**: Implement backup procedures for configurations and keys

## Support Resources

- **Documentation**: See `docs/sftp-trading-partner-guide.md` for comprehensive guide
- **Troubleshooting**: Check Application Insights logs and monitoring dashboards
- **Local Testing**: Use local development environment for testing changes
- **Configuration**: Refer to sample files and configuration schemas

## Success Criteria

✅ Infrastructure deployed successfully  
✅ SFTP connections tested and working  
✅ Functions deployed and running  
✅ Files can be fetched from partners  
✅ Acknowledgments can be sent to partners  
✅ Monitoring and alerting configured  
✅ End-to-end pipeline processing verified