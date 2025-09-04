# Test Data Directory

This directory contains generated X12 test data files for the Azure Fabric ETL pipeline testing.

## Generated Files

### Direct Test Files
- **20 basic X12 files** (`test_x12_*.x12`) - Generated using the original test data generator
- Contains various transaction types: 837, 835, 270, 271, 276, 277

### Scenario-Based Test Files
- **53 scenario-specific files** organized in subdirectories under `scenarios/`
- More realistic data with proper provider/payer relationships

## Scenarios

### 1. Development (15 files)
- **Purpose**: Basic development testing
- **Transaction Types**: 837 (Claims), 835 (Payments), 270 (Eligibility Inquiry), 271 (Eligibility Response)
- **Location**: `scenarios/development/`

### 2. Claims Processing (20 files)
- **Purpose**: Claims and payments focus
- **Transaction Types**: 837 (Claims), 835 (Payments)
- **Location**: `scenarios/claims_processing/`

### 3. Eligibility Verification (10 files)
- **Purpose**: Eligibility inquiries and responses
- **Transaction Types**: 270 (Eligibility Inquiry), 271 (Eligibility Response)
- **Location**: `scenarios/eligibility_verification/`

### 4. Status Requests (8 files)
- **Purpose**: Claim status requests and responses
- **Transaction Types**: 276 (Status Request), 277 (Status Response)
- **Location**: `scenarios/status_requests/`

## Transaction Types Explained

| Code | Description | Purpose |
|------|-------------|---------|
| 837 | Health Care Claim | Professional/Institutional/Dental claims |
| 835 | Health Care Claim Payment/Advice | Remittance advice and payment information |
| 834 | Benefit Enrollment and Maintenance | Insurance enrollment and changes |
| 270 | Health Care Eligibility Benefit Inquiry | Check patient eligibility |
| 271 | Health Care Eligibility Benefit Response | Response to eligibility inquiry |
| 276 | Health Care Claim Status Request | Request status of submitted claim |
| 277 | Health Care Claim Status Response | Response to claim status request |
| 278 | Health Care Services Review Request | Preauthorization requests |
| 279 | Health Care Services Review Response | Preauthorization responses |

## Test Providers

| Provider ID | Name | NPI |
|-------------|------|-----|
| MSC001 | MAIN STREET CLINIC | 1234567890 |
| DTH002 | DOWNTOWN HOSPITAL | 2345678901 |
| FCC003 | FAMILY CARE CENTER | 3456789012 |
| SPC004 | SPECIALTY PHYSICIANS | 4567890123 |
| UCP005 | URGENT CARE PLUS | 5678901234 |

## Test Payers

| Payer ID | Name |
|----------|------|
| BCBS001 | BLUE CROSS BLUE SHIELD |
| AETNA02 | AETNA HEALTH PLANS |
| UHC0003 | UNITED HEALTHCARE |
| CIGNA04 | CIGNA HEALTHCARE |
| HUMANA5 | HUMANA MEDICAL |

## File Naming Convention

### Original Files
```
test_x12_{transaction_type}_{timestamp}_{sequence}.x12
```

### Scenario Files
```
{scenario}_{transaction_type}_{provider_id}_{payer_id}_{timestamp}_{sequence}.x12
```

## Usage

### 1. Azure Storage Upload
Upload files to your Bronze container for ETL pipeline processing:

```bash
# Azure CLI
az storage blob upload-batch \
  --destination bronze-healthcare-x12-raw \
  --source testdata \
  --account-name YOUR_STORAGE_ACCOUNT

# Upload specific scenario
az storage blob upload-batch \
  --destination bronze-healthcare-x12-raw \
  --source testdata/scenarios/development \
  --account-name YOUR_STORAGE_ACCOUNT
```

### 2. PowerShell Upload
```powershell
# Upload all files
$files = Get-ChildItem -Path "testdata" -Filter "*.x12" -Recurse
foreach ($file in $files) {
    az storage blob upload --file $file.FullName --name $file.Name --container-name bronze-healthcare-x12-raw --account-name YOUR_STORAGE_ACCOUNT
}
```

### 3. Manual Testing
- Copy individual files to test specific scenarios
- Use different transaction types to test various pipeline branches
- Monitor processing through Azure Data Factory

## Generating Additional Test Data

### Using the Original Generator
```bash
cd scripts
python generate_test_x12_data.py
```

### Using the Enhanced Generator
```bash
cd testdata
python generate_additional_testdata.py
```

### Using PowerShell Script
```powershell
cd scripts
.\Generate-X12TestData.ps1 -OutputPath "../testdata" -FileCount 50 -TransactionTypes @("837", "835")
```

## File Structure

```
testdata/
├── README.md                          # This file
├── generate_additional_testdata.py    # Enhanced test data generator
├── test_data_summary.json            # Generation summary
├── test_x12_*.x12                    # Original test files (20 files)
└── scenarios/
    ├── development/                   # Development scenario (15 files)
    ├── claims_processing/             # Claims processing scenario (20 files)
    ├── eligibility_verification/      # Eligibility scenario (10 files)
    └── status_requests/               # Status requests scenario (8 files)
```

## Data Characteristics

- **Format**: X12 EDI standard compliant
- **Encoding**: ASCII
- **Segment Terminator**: ~ (tilde)
- **Element Separator**: * (asterisk)
- **Component Separator**: : (colon)
- **Test Environment**: All files marked as Test data (ISA15 = T)

## Troubleshooting

### Common Issues
1. **File Format Errors**: Ensure files are ASCII encoded
2. **Upload Failures**: Check Azure storage account permissions
3. **Pipeline Errors**: Verify X12 format compliance in logs

### Validation
- Check file content with text editor (should see X12 segments)
- Verify file sizes are reasonable (1-10KB typical)
- Ensure proper X12 structure (ISA...GS...ST...SE...GE...IEA)

## Next Steps

1. Upload test files to Azure Blob Storage (Bronze layer)
2. Trigger the Azure Data Factory pipeline
3. Monitor pipeline execution and logs
4. Verify processed data appears in Silver and Gold layers
5. Validate data transformations and analytics

## Support

For issues with test data generation or pipeline processing:
1. Check Azure Data Factory monitoring logs
2. Verify X12 format compliance
3. Review pipeline configuration
4. Check storage account connectivity and permissions