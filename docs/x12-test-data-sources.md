# X12 Test Data Sources and Generation Guide

## Overview

This document provides comprehensive guidance on obtaining and generating test X12 EDI data files for the Azure Fabric X12 ETL Pipeline, with a focus on HIPAA healthcare transaction sets.

## Table of Contents
1. [Official HIPAA Sample Repositories](#official-hipaa-sample-repositories)
2. [Commercial EDI Tools](#commercial-edi-tools)
3. [Open Source Solutions](#open-source-solutions)
4. [Built-in Test Data Generator](#built-in-test-data-generator)
5. [Best Practices for Test Data](#best-practices-for-test-data)
6. [Compliance Considerations](#compliance-considerations)

---

## Official HIPAA Sample Repositories

### 1. CMS (Centers for Medicare & Medicaid Services)

**Primary Resource for HIPAA Test Data**
- **URL**: https://www.cms.gov/Regulations-and-Guidance/Administrative-Simplification/HIPAA-ACA/AdoptedStandardsandOperatingRules
- **Available Formats**: Official HIPAA-compliant X12 5010 format
- **Transaction Types**: 
  - 837P (Professional Claims)
  - 837I (Institutional Claims) 
  - 837D (Dental Claims)
  - 835 (Remittance Advice)
  - 834 (Enrollment/Maintenance)
  - 270/271 (Eligibility Inquiry/Response)
  - 276/277 (Claim Status Request/Response)
  - 278/279 (Prior Authorization Request/Response)

**Access Method**:
```bash
# Download sample files from CMS
curl -O https://www.cms.gov/files/document/hipaa-sample-files.zip
```

### 2. WEDI (Workgroup for Electronic Data Interchange)

**SNIP Testing Resources**
- **URL**: https://www.wedi.org/snip-testing
- **Features**: 
  - SNIP Level 1 & 2 test files
  - Compliance validation samples
  - Error scenario test cases
- **Access**: Membership required for full access

### 3. X12.org Official Standards

**ASC X12 Developer Resources**
- **URL**: https://x12.org/
- **Features**:
  - Official X12 schemas and documentation
  - Implementation guides
  - Sample transaction sets
- **Access**: Developer membership ($200-500/year)

---

## Commercial EDI Tools

### 1. Stedi EDI Platform

**Free and Paid Tiers Available**
- **URL**: https://www.stedi.com/edi
- **Features**:
  - Online EDI Inspector and validator
  - Sample data generation
  - Real-time parsing and validation
- **Free Tier**: Limited sample generation
- **Paid Plans**: Starting at $99/month

```bash
# Example API call to generate sample 837
curl -X POST https://api.stedi.com/edi/generate \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"transaction_type": "837", "count": 10}'
```

### 2. TrueCommerce EDI Tools

**Enterprise EDI Solutions**
- **URL**: https://www.truecommerce.com/
- **Features**: Comprehensive EDI testing suites
- **Access**: Commercial license required

### 3. BizTalk Server Samples (Microsoft)

**Free with BizTalk Server**
- **Location**: `\Program Files (x86)\Microsoft BizTalk Server <VERSION>\SDK\EDI Interface Developer Tutorial\`
- **Sample Files**:
  - `SamplePO.txt` (X12 850 Purchase Order)
  - Various healthcare transaction samples
- **Schemas**: Available in `\XSD_Schema\EDI\` folder

---

## Open Source Solutions

### 1. GitHub Repositories

#### **x12-parser Sample Data**
```bash
git clone https://github.com/MindfulHealth/x12-parser-sample-data
cd x12-parser-sample-data
ls samples/  # Browse available sample files
```

#### **EDI File Examples**
```bash
git clone https://github.com/dipique/x12-file-examples
git clone https://github.com/xlate/x12-examples
```

### 2. Python Libraries for X12 Generation

#### **pyx12 Library**
```bash
pip install pyx12
```

```python
# Example: Generate X12 using pyx12
from pyx12 import x12file
from pyx12 import x12xml

# Create X12 from XML template
x12_data = x12xml.xml_to_x12('sample_837.xml')
print(x12_data)
```

#### **EDI-835-Parser**
```bash
pip install edi-835-parser
```

---

## Built-in Test Data Generator

Our Azure Fabric X12 ETL Pipeline includes a custom test data generator designed specifically for healthcare HIPAA transactions.

### Quick Start

#### **Using PowerShell (Recommended)**
```powershell
# Generate 20 mixed transaction files
.\scripts\Generate-X12TestData.ps1

# Generate 100 files for load testing
.\scripts\Generate-X12TestData.ps1 -FileCount 100

# Generate only claim files (837, 835)
.\scripts\Generate-X12TestData.ps1 -TransactionTypes @("837", "835") -FileCount 50

# Generate in specific directory
.\scripts\Generate-X12TestData.ps1 -OutputPath "C:\temp\x12_test" -FileCount 25
```

#### **Using Python Directly**
```bash
# Navigate to scripts directory
cd scripts

# Generate default test files
python generate_test_x12_data.py

# The script will create a 'test_x12_data' directory with sample files
```

### Generated File Structure

```
test_x12_data/
├── test_x12_837_20250902_143022_001.x12  # Health Care Claim
├── test_x12_835_20250902_143023_002.x12  # Payment Advice
├── test_x12_270_20250902_143024_003.x12  # Eligibility Inquiry
├── test_x12_271_20250902_143025_004.x12  # Eligibility Response
└── ...
```

### Supported Transaction Types

| Code | Description | Use Case |
|------|-------------|----------|
| **837** | Health Care Claim | Claims submission (Professional, Institutional, Dental) |
| **835** | Health Care Claim Payment/Advice | Remittance advice and payment information |
| **834** | Benefit Enrollment and Maintenance | Insurance enrollment and member maintenance |
| **270** | Health Care Eligibility Benefit Inquiry | Check patient eligibility and benefits |
| **271** | Health Care Eligibility Benefit Response | Response to eligibility inquiries |
| **276** | Health Care Claim Status Request | Check status of submitted claims |
| **277** | Health Care Claim Status Response | Response to claim status requests |
| **278** | Health Care Services Review Request | Prior authorization requests |
| **279** | Health Care Services Review Response | Prior authorization responses |

---

## Best Practices for Test Data

### 1. Data Volume Testing

#### **Development/Testing Environment**
- **File Count**: 10-100 files
- **File Size**: 25-50 KB average
- **Frequency**: Daily batch processing
- **Purpose**: Feature development and basic testing

```powershell
# Generate development test set
.\Generate-X12TestData.ps1 -FileCount 50 -OutputPath "dev_test_data"
```

#### **Load Testing Environment**
- **File Count**: 1,000-10,000 files
- **File Size**: 50-100 KB average
- **Frequency**: Hourly processing simulation
- **Purpose**: Performance and scalability testing

```powershell
# Generate load test set
.\Generate-X12TestData.ps1 -FileCount 5000 -OutputPath "load_test_data"
```

#### **Stress Testing Environment**
- **File Count**: 10,000+ files
- **File Size**: 100-200 KB average
- **Frequency**: Continuous processing simulation
- **Purpose**: Maximum capacity testing

### 2. Error Scenario Testing

Create intentionally malformed files to test error handling:

```python
# Example: Generate files with missing segments
def generate_error_scenarios():
    scenarios = [
        "missing_isa_header",
        "invalid_control_numbers", 
        "missing_st_trailer",
        "invalid_element_separators",
        "truncated_file"
    ]
    # Implementation would generate specific error cases
```

### 3. Transaction Mix Testing

Simulate realistic transaction volume distributions:

```json
{
  "transaction_mix": {
    "837": 60,   // 60% claims
    "835": 20,   // 20% payments  
    "270": 10,   // 10% eligibility inquiries
    "271": 5,    // 5% eligibility responses
    "276": 3,    // 3% status requests
    "277": 2     // 2% status responses
  }
}
```

---

## Compliance Considerations

### 1. PHI (Protected Health Information) Handling

**⚠️ IMPORTANT: Never use real patient data for testing**

- Use synthetic/fake data only
- Ensure all patient identifiers are fictitious
- Follow HIPAA compliance guidelines for test environments

### 2. Test Data Sanitization

Our generator creates compliant test data:
- Fake NPI numbers (using valid format but non-existent providers)
- Synthetic patient names and demographics
- Fictitious claim numbers and amounts
- Test-only identifiers

### 3. Environment Isolation

- Keep test data separate from production systems
- Use dedicated Azure storage containers for test files
- Apply appropriate access controls and monitoring

---

## Integration with Azure Fabric Pipeline

### 1. Upload Test Files to Azure Storage

```bash
# Using Azure CLI
az storage blob upload-batch \
  --destination bronze-healthcare-x12-raw \
  --source test_x12_data \
  --account-name yourstorageaccount \
  --auth-mode login

# Using PowerShell with Az module
$files = Get-ChildItem -Path "test_x12_data" -Filter "*.x12"
foreach ($file in $files) {
    Set-AzStorageBlobContent `
        -File $file.FullName `
        -Container "bronze-healthcare-x12-raw" `
        -Blob $file.Name `
        -Context $storageContext
}
```

### 2. Monitor Pipeline Processing

```bash
# Check pipeline runs
az datafactory pipeline-run list \
  --resource-group rg-fabric-x12-pipeline \
  --factory-name your-data-factory \
  --last-updated-after "2025-09-01" \
  --last-updated-before "2025-09-03"
```

### 3. Validate Processed Data

Check Silver and Gold layer tables after processing:

```sql
-- Query Silver layer for processing results
SELECT 
    transaction_type,
    processing_status,
    COUNT(*) as file_count,
    AVG(quality_score) as avg_quality_score
FROM silver_x12_transactions 
WHERE processing_date >= '2025-09-01'
GROUP BY transaction_type, processing_status;

-- Query Gold layer for business metrics
SELECT 
    transaction_date,
    transaction_type,
    total_transactions,
    total_amount,
    avg_processing_time_minutes
FROM gold_transaction_summary 
WHERE transaction_date >= '2025-09-01'
ORDER BY transaction_date DESC;
```

---

## Cost Estimation for Test Data

Based on the cost analysis in our pipeline documentation:

| Test Scenario | File Count | Est. Monthly Cost | Use Case |
|---------------|------------|------------------|----------|
| **Development** | 1,000 files | $45-70 | Feature development |
| **Integration** | 10,000 files | $150-250 | Integration testing |
| **Load Testing** | 100,000 files | $450-850 | Performance validation |
| **Stress Testing** | 1,000,000+ files | $1,500+ | Capacity planning |

*Costs include storage, processing, and monitoring for test environments*

---

## Support and Resources

### Documentation Links
- [Azure Fabric X12 ETL Pipeline README](../README.md)
- [Cost Estimation Guide](cost-estimation-guide.md)
- [HIPAA Compliance Guide](managed-identity-rbac-enhancements.md)

### External Resources
- [CMS HIPAA Standards](https://www.cms.gov/Regulations-and-Guidance/Administrative-Simplification/HIPAA-ACA)
- [X12.org Standards](https://x12.org/)
- [WEDI Resources](https://www.wedi.org/)

### Getting Help
- Review troubleshooting guides in main documentation
- Check Azure Data Factory monitoring for processing issues
- Contact development team for custom test scenarios

---

*Last Updated: September 2, 2025*
*Version: 1.0*