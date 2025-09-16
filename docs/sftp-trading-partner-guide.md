# SFTP Trading Partner Integration Guide

## Overview

This guide provides comprehensive instructions for setting up and managing SFTP connections with trading partners in the X12 EDI processing pipeline. The system supports automated file exchange with healthcare trading partners including claims, eligibility checks, remittance advice, and acknowledgments.

## Architecture

The SFTP integration consists of several key components:

### Core Components
- **SFTP Connector Module** (`src/sftp/`) - Python library for secure SFTP operations
- **Trading Partner Manager** - Orchestrates multi-partner operations and business logic
- **Azure Functions** - Serverless functions for scheduled fetch/push operations
- **Azure Data Factory Pipeline** - Integrated workflow with SFTP operations
- **Monitoring & Alerting** - Comprehensive observability for SFTP operations

### Data Flow
1. **Inbound**: SFTP Fetch → Bronze Storage → Silver Processing → Gold Analytics
2. **Outbound**: Gold Layer → Generate Acknowledgments → SFTP Push to Partners

## Trading Partner Setup

### Prerequisites
- Partner SFTP server details (host, port, directories)
- Authentication credentials (SSH keys or passwords)
- Host key fingerprints for security verification
- Directory structure and file naming conventions
- Supported X12 transaction types

### Configuration Steps

#### 1. Partner Configuration File
Create a configuration file for your trading partners:

```json
{
  "partners": [
    {
      "id": "PARTNER001",
      "name": "Partner Name",
      "connection": {
        "host": "sftp.partner.com",
        "port": 22,
        "username": "username",
        "authentication_method": "key",
        "key_vault_secret_name": "sftp-partner001-private-key",
        "host_key_secret_name": "sftp-partner001-host-key"
      },
      "directories": {
        "inbound": "/inbound/x12",
        "outbound": "/outbound/x12",
        "processed": "/processed",
        "failed": "/failed"
      },
      "file_patterns": {
        "fetch": ["*.x12", "*.edi"],
        "push": ["*.x12", "*.997"]
      },
      "transaction_types": {
        "inbound": ["837", "270", "276"],
        "outbound": ["835", "271", "277", "997"]
      },
      "processing": {
        "auto_fetch": true,
        "auto_push": true,
        "archive_after_fetch": true,
        "max_file_age_hours": 72,
        "max_file_size_mb": 100
      }
    }
  ]
}
```

#### 2. Deploy Infrastructure
```powershell
# Deploy with SFTP support
.\deploy.ps1 -SubscriptionId "your-subscription-id" `
            -ResourceGroupName "rg-x12-pipeline" `
            -Location "East US 2" `
            -ConfigureSFTP `
            -TradingPartnerConfigFile "partners-config.json"
```

#### 3. Configure Secrets in Key Vault
```bash
# Set private key for key-based authentication
az keyvault secret set --vault-name "your-key-vault" \
                      --name "sftp-partner001-private-key" \
                      --file "partner001-private-key.pem"

# Set host key for verification
az keyvault secret set --vault-name "your-key-vault" \
                      --name "sftp-partner001-host-key" \
                      --value "ssh-rsa AAAAB3NzaC1yc2E..."

# Set password for password-based authentication
az keyvault secret set --vault-name "your-key-vault" \
                      --name "sftp-partner001-password" \
                      --value "secure-password"
```

#### 4. Configure Function App Environment
```bash
# Set partner connection details
az functionapp config appsettings set \
  --name "your-sftp-function-app" \
  --resource-group "your-resource-group" \
  --settings "PARTNER001_HOST=sftp.partner.com" \
             "PARTNER001_USERNAME=username" \
             "PARTNER001_INBOUND_DIR=/inbound/x12"
```

## Operations Guide

### Manual Operations

#### Test Partner Connection
```python
from sftp.connector import SFTPConnector

# Create connector
connector = SFTPConnector(
    host="sftp.partner.com",
    username="username",
    private_key="-----BEGIN RSA PRIVATE KEY-----\n...",
    host_key_verification=True
)

# Test connection
try:
    connector.connect()
    files = connector.list_files("/inbound/x12")
    print(f"Found {len(files)} files")
    connector.disconnect()
except Exception as e:
    print(f"Connection failed: {e}")
```

#### Manual File Fetch
```bash
# Trigger SFTP fetch function manually
curl -X POST "https://your-function-app.azurewebsites.net/api/fetch_files" \
     -H "Content-Type: application/json" \
     -d '{"trigger_source": "manual", "batch_id": "manual_001"}'
```

#### Manual File Push
```bash
# Send push notification to Service Bus
az servicebus message send \
  --resource-group "your-resource-group" \
  --namespace-name "your-service-bus" \
  --queue-name "x12-processing-queue" \
  --body '{
    "partner_id": "PARTNER001",
    "files": ["acknowledgments/2025/01/15/PARTNER001_997_20250115_001.x12"]
  }'
```

### Scheduled Operations

#### SFTP Fetch Schedule
- **Frequency**: Every 2 hours (configurable)
- **Function**: `fetch_files`
- **Trigger**: Timer trigger (`0 */2 * * *`)

#### Health Check Schedule
- **Frequency**: Every 6 hours (configurable)
- **Function**: `health_check`
- **Trigger**: Timer trigger (`0 0 */6 * * *`)

#### SFTP Push Operations
- **Trigger**: Service Bus queue messages
- **Function**: `push_files`
- **Source**: Data Factory pipeline completion

## Monitoring and Troubleshooting

### Key Metrics to Monitor

#### Connection Health
- SFTP connection success rate
- Authentication failure rates
- Connection timeout incidents
- Partner availability status

#### File Processing
- Files fetched per hour/day
- File processing success rates
- Large file alerts
- Failed file transfers

#### Performance
- Average connection times
- File transfer speeds
- Queue processing times
- Error recovery times

### Common Issues and Solutions

#### Authentication Failures
**Symptoms**: Connection fails with authentication errors

**Troubleshooting**:
1. Verify credentials in Key Vault
2. Check SSH key format and permissions
3. Confirm username with trading partner
4. Test connection manually

```bash
# Test SSH connection manually
ssh -i private_key.pem username@sftp.partner.com
```

#### Connection Timeouts
**Symptoms**: Connections fail with timeout errors

**Troubleshooting**:
1. Check network connectivity
2. Verify firewall rules
3. Confirm SFTP server status
4. Adjust timeout settings

#### Host Key Verification Failures
**Symptoms**: Host key verification errors

**Troubleshooting**:
1. Update host key in Key Vault
2. Get current host key from partner
3. Verify key format and encoding

```bash
# Get host key
ssh-keyscan -H sftp.partner.com
```

#### File Transfer Failures
**Symptoms**: Files fail to upload/download

**Troubleshooting**:
1. Check file permissions
2. Verify directory paths
3. Confirm file size limits
4. Check disk space

### Monitoring Queries

#### Connection Success Rate
```kusto
traces
| where timestamp > ago(24h)
| where message contains "SFTP" and message contains "connected"
| summarize 
    Total = count(),
    Successful = countif(message contains "Successfully")
    by bin(timestamp, 1h)
| extend SuccessRate = round(Successful * 100.0 / Total, 2)
```

#### Failed File Transfers
```kusto
traces
| where timestamp > ago(24h)
| where severityLevel >= 3
| where message contains "SFTP" and message contains "failed"
| extend Partner = extract(@"partner (\w+)", 1, message)
| summarize FailureCount = count() by Partner, bin(timestamp, 1h)
```

### Alerting Rules

#### Critical Alerts
- **Partner Connection Failures**: 3+ failures in 30 minutes
- **SFTP Function Errors**: Any function execution failures
- **Authentication Issues**: Multiple auth failures for same partner

#### Warning Alerts
- **High Failure Rate**: >20% failures in 1 hour
- **Large Files**: Files exceeding size limits
- **No Files Received**: No files from partners in 4+ hours

## Security Best Practices

### Authentication
- **Prefer SSH Keys**: Use key-based authentication over passwords
- **Key Rotation**: Rotate SSH keys regularly (every 90 days)
- **Strong Passwords**: Use complex passwords if key auth not available
- **Multi-Factor**: Enable MFA where supported by partner

### Network Security
- **Host Key Verification**: Always verify host keys
- **IP Restrictions**: Restrict access by IP when possible
- **VPN/Private Network**: Use VPN or private connectivity
- **Firewall Rules**: Configure restrictive firewall rules

### Data Protection
- **Encryption in Transit**: All SFTP connections use SSH encryption
- **Encryption at Rest**: Azure Storage encryption enabled
- **Access Control**: Use managed identities and RBAC
- **Audit Logging**: Enable comprehensive audit logging

### Secret Management
- **Azure Key Vault**: Store all credentials in Key Vault
- **Managed Identity**: Use managed identity for authentication
- **Least Privilege**: Grant minimum required permissions
- **Secret Rotation**: Implement automated secret rotation

## Performance Optimization

### Connection Pooling
```python
# Configure connection pooling for high-volume operations
sftp_config = {
    "connection_timeout_seconds": 30,
    "retry_attempts": 3,
    "retry_delay_seconds": 60,
    "batch_size": 100
}
```

### Parallel Processing
```python
# Process multiple partners in parallel
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(fetch_files_from_partner, partner_id)
        for partner_id in partner_ids
    ]
```

### File Size Optimization
- **Compression**: Compress large files before transfer
- **Splitting**: Split oversized files into smaller chunks
- **Streaming**: Use streaming for very large files
- **Batching**: Batch small files together

## Disaster Recovery

### Backup Strategies
- **Configuration Backup**: Regular backup of partner configurations
- **Key Backup**: Secure backup of SSH keys and certificates
- **Data Backup**: Regular backup of processed files
- **Documentation**: Keep current partner contact information

### Recovery Procedures
1. **Service Restoration**: Restore SFTP services from backup
2. **Partner Notification**: Notify partners of any outages
3. **File Recovery**: Recover missed files from partners
4. **Processing Replay**: Replay missed processing cycles

### Business Continuity
- **Manual Override**: Manual file transfer capabilities
- **Alternative Channels**: Secondary communication channels
- **Partner Coordination**: Established escalation procedures
- **SLA Management**: Clear service level agreements

## Partner Onboarding Process

### 1. Technical Requirements Gathering
- SFTP server details and connectivity
- Authentication method and credentials
- Directory structure and naming conventions
- File formats and transaction types
- Processing schedules and SLAs

### 2. Security Assessment
- Host key exchange and verification
- IP whitelisting requirements
- Firewall configuration
- Compliance and audit requirements

### 3. Configuration and Testing
- Create partner configuration
- Set up credentials in Key Vault
- Configure Function App settings
- Perform connectivity testing
- Execute end-to-end file transfer tests

### 4. Production Deployment
- Deploy configuration to production
- Monitor initial file transfers
- Verify acknowledgment delivery
- Confirm partner receipt and processing

### 5. Ongoing Management
- Regular health checks
- Performance monitoring
- Credential rotation
- Configuration updates

## API Reference

### SFTP Connector Class
```python
class SFTPConnector:
    def __init__(host, port, username, password=None, private_key=None, ...)
    def connect() -> bool
    def disconnect()
    def list_files(directory, pattern="*") -> List[Dict]
    def download_file(remote_path, local_path) -> bool
    def upload_file(local_path, remote_path) -> bool
    def delete_file(remote_path) -> bool
    def move_file(old_path, new_path) -> bool
    def file_exists(remote_path) -> bool
```

### Trading Partner Manager Class
```python
class TradingPartnerManager:
    def __init__(config, key_vault_uri, storage_account_name, ...)
    def fetch_files_from_partner(partner_id) -> List[Dict]
    def push_files_to_partner(partner_id, files) -> List[Dict]
    def fetch_all_partners() -> Dict[str, List[Dict]]
    def get_partner_stats() -> Dict[str, Any]
    def create_sftp_connector(partner_config) -> SFTPConnector
```

### Azure Functions
- **fetch_files**: Timer-triggered function for file fetching
- **push_files**: Service Bus-triggered function for file pushing
- **health_check**: Timer-triggered function for connection monitoring

## Support and Maintenance

### Regular Maintenance Tasks
- **Weekly**: Review connection health and error logs
- **Monthly**: Analyze file transfer volumes and performance
- **Quarterly**: Review and update partner configurations
- **Annually**: Audit security settings and rotate credentials

### Escalation Procedures
1. **Level 1**: Automated monitoring and alerts
2. **Level 2**: Operations team investigation
3. **Level 3**: Partner communication and coordination
4. **Level 4**: Business stakeholder involvement

### Contact Information
- **Operations Team**: ops@yourcompany.com
- **Technical Support**: support@yourcompany.com
- **Partner Relations**: partners@yourcompany.com
- **Security Team**: security@yourcompany.com