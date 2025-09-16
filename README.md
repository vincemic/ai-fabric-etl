# Azure Fabric X12 EDI Processing Pipeline - Healthcare

This project implements a comprehensive data pipeline for processing healthcare X12 EDI files using Azure Fabric and a medallion data architecture (Bronze, Silver, Gold layers) with secure SFTP file exchange and PGP encryption capabilities.

## Architecture Overview

The solution follows a medallion data architecture pattern:

- **Bronze Layer**: Raw X12 file ingestion and basic validation
- **Silver Layer**: Parsed and cleaned X12 data with quality checks  
- **Gold Layer**: Business-ready aggregated data for analytics and reporting

### SFTP Integration with PGP Encryption

- **Secure File Exchange**: Automated SFTP operations for trading partner file exchange
- **PGP Encryption**: End-to-end encryption for sensitive healthcare data
- **Digital Signatures**: File authenticity verification using PGP signatures
- **Multi-Partner Support**: Individual encryption settings per trading partner

## Components

### Infrastructure (`/infra`)
- `main.bicep` - Azure infrastructure deployment template
- `main.parameters.json` - Infrastructure parameters

### SFTP Functions (`/functions/sftp-operations`)
- `fetch_files/` - Automated file retrieval from trading partners with PGP decryption
- `push_files/` - Secure file delivery to trading partners with PGP encryption
- `health_check/` - Connection monitoring and PGP validation

### Notebooks (`/notebooks`)
- `bronze_x12_ingestion.py` - Bronze layer processing
- `silver_x12_parsing.py` - Silver layer data parsing and validation
- `gold_x12_analytics.py` - Gold layer business analytics

### Pipelines (`/pipelines`)
- `x12-processing-pipeline.json` - Data Factory pipeline definition

### Configuration (`/config`)
- `development.json` - Environment-specific configuration
- `trading-partners-config.sample.json` - Sample trading partner configuration
- `pgp-trading-partners-config.example.json` - Complete PGP configuration example

### Schemas (`/schemas`)
- `x12_transaction_schemas.json` - X12 transaction type definitions

### SFTP Source Code (`/src/sftp`)
- `manager.py` - Trading partner management with PGP operations
- `connector.py` - SFTP connection handling
- `pgp_manager.py` - PGP encryption, decryption, and signing
- `exceptions.py` - Custom exception classes

### Documentation (`/docs`)
- `pgp-encryption-guide.md` - Comprehensive PGP setup and usage guide
- `sftp-trading-partner-guide.md` - Trading partner setup instructions
- `cost-estimation-guide.md` - Comprehensive cost analysis and optimization guide
- `managed-identity-rbac-enhancements.md` - Security and RBAC documentation

### Scripts (`/scripts`)
- `pgp_setup.py` - PGP key generation and management utility
- `cost_calculator.py` - Interactive cost estimation tool
- `cost_scenarios.json` - Pre-defined cost scenarios for batch analysis
- `Analyze-PipelineCosts.ps1` - PowerShell cost monitoring and analysis

## Quick Start with PGP Encryption

### 1. Generate Organization PGP Keys

```bash
# Generate new key pair for your organization
python scripts/pgp_setup.py generate-keys \
  --name "Your Organization" \
  --email "edi@yourorg.com" \
  --passphrase "your-secure-passphrase"
```

### 2. Import Trading Partner Keys

```bash
# Import a partner's public key
python scripts/pgp_setup.py import-key \
  --partner-id PARTNER001 \
  --key-file /path/to/partner-public-key.asc
```

### 3. Configure Trading Partners

Update `trading-partners-config.json` with PGP settings:

```json
{
  "id": "PARTNER001",
  "pgp": {
    "enabled": true,
    "encrypt_outbound": true,
    "decrypt_inbound": true,
    "sign_outbound": true,
    "verify_inbound": true
  }
}
```

### 4. Validate Configuration

```bash
# Validate all PGP configurations
python scripts/pgp_setup.py validate --config trading-partners-config.json

# Test PGP operations with a specific partner
python scripts/pgp_setup.py test --partner-id PARTNER001
```

For detailed setup instructions, see the [PGP Encryption Guide](docs/pgp-encryption-guide.md).

## Cost Analysis and Planning

This solution includes comprehensive cost analysis tools to help you estimate and optimize operational costs:

### Cost Estimation Guide (`docs/cost-estimation-guide.md`)

A detailed analysis covering:

- **Monthly cost ranges**: $45 (1K transactions) to $8,500+ (10M+ transactions)
- **Component breakdown**: Storage, Data Factory, Functions, Monitoring
- **5 scenario models**: From small clinics to enterprise healthcare systems
- **20+ optimization strategies**: Actionable cost reduction techniques
- **Monitoring setup**: Budget alerts and cost tracking queries

### Interactive Cost Calculator (`scripts/cost_calculator.py`)

```powershell
# Interactive mode - guided prompts
python scripts/cost_calculator.py

# Batch mode - process multiple scenarios
python scripts/cost_calculator.py scripts/cost_scenarios.json
```

Features:

- Real-time cost calculations based on transaction volume
- Customizable parameters (file size, processing frequency)
- Export results to JSON for analysis
- Built-in optimization recommendations

### Cost Monitoring Script (`scripts/Analyze-PipelineCosts.ps1`)

```powershell
# Run cost analysis on current Azure resources
.\scripts\Analyze-PipelineCosts.ps1
```

Capabilities:

- Query actual Azure costs for your resources
- Generate automated optimization suggestions
- Track spending against predefined budgets
- Resource-specific cost breakdowns

## Supported X12 Transaction Types

- **837** - Health Care Claim (Professional, Institutional, and Dental)
- **835** - Health Care Claim Payment/Advice (Remittance Advice)
- **834** - Benefit Enrollment and Maintenance (Insurance Enrollment)
- **270** - Health Care Eligibility Benefit Inquiry
- **271** - Health Care Eligibility Benefit Response
- **276** - Health Care Claim Status Request
- **277** - Health Care Claim Status Response
- **278** - Health Care Services Review Request (Preauthorization Request)
- **279** - Health Care Services Review Response (Preauthorization Response)

## Prerequisites

- Azure subscription with appropriate permissions
- Azure CLI installed and configured
- Azure Developer CLI (azd) installed
- Databricks workspace (for notebook execution)
- Azure Data Factory (for pipeline orchestration)

## Deployment

### 1. Infrastructure Deployment

```powershell
# Login to Azure
az login

# Set subscription
az account set --subscription "your-subscription-id"

# Deploy infrastructure
az deployment group create `
  --resource-group "rg-fabric-x12-pipeline" `
  --template-file "infra/main.bicep" `
  --parameters "@infra/main.parameters.json"
```

### 2. Alternative: Using Azure Developer CLI

```powershell
# Initialize and deploy
azd init
azd up
```

### 3. Configure Fabric Workspace

1. Create a new Fabric workspace
2. Create a lakehouse named `healthcare_x12_lakehouse`
3. Import the notebooks from the `/notebooks` directory
4. Configure the notebook parameters with your storage account details

### 4. Configure Data Factory Pipeline

1. Import the pipeline from `/pipelines/x12-processing-pipeline.json`
2. Configure linked services for:
   - Azure Storage (Bronze, Silver, Gold containers)
   - Databricks workspace
   - Key Vault (for secrets)
3. Set up pipeline parameters

## Usage

### Processing X12 Files

1. **Upload healthcare X12 files** to the Bronze container (`bronze-healthcare-x12-raw`)
2. **Trigger the pipeline** manually or set up a schedule/event trigger
3. **Monitor progress** through Azure Data Factory monitoring

### Pipeline Flow

1. **Bronze Ingestion**:
   - Validates X12 file format
   - Extracts metadata
   - Stores raw files with processing information

2. **Silver Parsing**:
   - Parses X12 segments and elements
   - Validates data quality
   - Stores structured data

3. **Gold Analytics**:
   - Creates business-ready data marts
   - Generates KPIs and metrics
   - Provides aggregated views for reporting

### Data Access

Once processed, data is available in the following tables:

- `silver_x12_transactions` - Parsed transaction data
- `gold_transaction_summary` - Transaction summaries by type and date
- `gold_claim_analytics` - Healthcare claim metrics and analytics
- `gold_payment_analytics` - Healthcare payment and remittance advice analytics
- `gold_enrollment_analytics` - Insurance enrollment and maintenance metrics
- `gold_eligibility_analytics` - Healthcare eligibility inquiry and response analytics
- `gold_claim_status_analytics` - Claim status tracking and monitoring
- `gold_provider_analytics` - Healthcare provider performance metrics
- `gold_payer_analytics` - Insurance payer analytics and KPIs
- `gold_data_quality_metrics` - Data quality monitoring
- `gold_business_kpis` - Overall healthcare business KPIs

## Configuration

### Environment Variables

Update `/config/development.json` with your environment-specific values:

```json
{
  "azure": {
    "subscription_id": "your-subscription-id",
    "resource_group": "your-resource-group",
    "storage_account": {
      "name": "your-storage-account"
    },
    "data_factory": {
      "name": "your-data-factory"
    }
  }
}
```

### Security

The solution implements Azure security best practices:

- **Managed Identity** authentication for all Azure services
- **Key Vault** for storing secrets and connection strings
- **RBAC** for fine-grained access control
- **Storage Account** key access disabled
- **Network security** with private endpoints (optional)

## Monitoring and Alerting

### Data Quality Monitoring

The pipeline includes comprehensive data quality checks:

- File format validation
- Segment structure validation
- Business rule validation
- Quality score calculation (0-100)

### Monitoring Dashboards

Create Power BI dashboards using the Gold layer tables:

- Healthcare claim volume and processing trends
- Healthcare preauthorization request and response analytics
- Preauthorization approval/denial rates and turnaround times
- Data quality metrics for healthcare transactions
- Provider and payer performance analytics
- Claims processing SLA compliance
- Healthcare enrollment and eligibility metrics

### Alerts

Set up alerts for:

- Pipeline failures
- Data quality below threshold (< 70% quality score)
- Processing time SLA breaches
- Storage capacity warnings

## Troubleshooting

### Common Issues

1. **File Format Errors**
   - Check X12 file starts with ISA segment
   - Verify segment terminators and element separators
   - Validate file encoding (ASCII expected)

2. **Permission Errors**
   - Verify Managed Identity has Storage Blob Data Contributor role
   - Check Key Vault access policies
   - Ensure Data Factory has correct permissions

3. **Processing Timeouts**
   - Increase notebook timeout settings
   - Optimize file batch sizes
   - Scale up Databricks cluster

### Debugging

1. **Check processing logs** in Application Insights
2. **Review Data Factory activity logs**
3. **Examine notebook execution logs**
4. **Monitor storage account metrics**

## Performance Optimization

### File Processing

- **Batch Size**: Process 100 files per batch (configurable)
- **File Size Limit**: 50MB per file (configurable)
- **Parallel Processing**: Multiple notebooks can run concurrently

### Databricks Optimization

- Use appropriate cluster size based on data volume
- Enable auto-scaling for variable workloads
- Consider using Photon runtime for better performance

### Storage Optimization

- Use hot tier for active processing
- Move to cool/archive tiers for long-term storage
- Implement lifecycle management policies

## Cost Optimization

1. **Use consumption-based pricing** where possible
2. **Schedule pipeline runs** during off-peak hours
3. **Implement data retention policies**
4. **Monitor storage and compute costs** regularly

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

1. Check the troubleshooting guide above
2. Review Azure Fabric documentation
3. Open an issue in this repository
4. Contact the development team

## Version History

- **v1.0.0** - Initial release with Bronze, Silver, Gold processing
- **v1.1.0** - Added data quality monitoring and alerts
- **v1.2.0** - Enhanced business analytics and KPIs
- **v1.3.0** - Added comprehensive cost analysis tools and documentation