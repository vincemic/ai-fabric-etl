# Azure Fabric X12 ETL Pipeline - Cost Estimation Guide

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Cost Components](#cost-components)
4. [Pricing Models and Scenarios](#pricing-models-and-scenarios)
5. [Cost Calculations by Volume](#cost-calculations-by-volume)
6. [Cost Optimization Recommendations](#cost-optimization-recommendations)
7. [Monitoring and Budgeting](#monitoring-and-budgeting)
8. [Appendix: Pricing References](#appendix-pricing-references)

---

## Executive Summary

This document provides cost estimates for operating the Azure Fabric X12 EDI processing pipeline across various transaction volumes and processing frequencies. The pipeline implements a medallion data architecture (Bronze, Silver, Gold) using Azure Data Factory, Azure Storage, Azure Functions, and comprehensive monitoring.

### Cost Range Summary
| Monthly Volume | Low Volume (1K transactions) | Medium Volume (100K transactions) | High Volume (10M transactions) |
|----------------|------------------------------|-----------------------------------|--------------------------------|
| **Estimated Monthly Cost** | $45 - $85 | $450 - $850 | $4,500 - $8,500 |
| **Per Transaction Cost** | $0.045 - $0.085 | $0.0045 - $0.0085 | $0.00045 - $0.00085 |

---

## Architecture Overview

The pipeline consists of the following key components:

```
Input X12 Files → Bronze Layer (Raw) → Silver Layer (Parsed) → Gold Layer (Analytics)
                     ↓                    ↓                       ↓
                Storage (Hot)        Storage (Cool)          Storage (Hot)
                     ↓                    ↓                       ↓
                Data Factory        Data Factory            Data Factory
                     ↓                    ↓                       ↓
                Monitoring          Monitoring              Monitoring
```

### Key Infrastructure Components:
- **Storage Account**: 4 containers (Bronze, Silver, Gold, Archive)
- **Data Factory**: Pipeline orchestration and data movement
- **Azure Functions**: Lightweight processing and event handling
- **Key Vault**: Secrets and connection string management
- **Service Bus**: Message queuing for reliable processing
- **Log Analytics & Application Insights**: Monitoring and diagnostics

---

## Cost Components

### 1. Azure Storage Costs

#### Storage Capacity Costs (per month)
| Access Tier | Price per GB | Use Case | Recommended For |
|-------------|--------------|----------|----------------|
| **Hot** | $0.0208 | Active processing, Gold layer | Current month data |
| **Cool** | $0.0115 | Infrequent access, Silver layer | 30-90 day old data |
| **Archive** | $0.002 | Long-term retention | Compliance/historical data |

#### Transaction Costs (per 10,000 operations)
| Operation Type | Hot | Cool | Archive |
|----------------|-----|------|---------|
| **Write Operations** | $0.143 | $0.260 | $0.273 |
| **Read Operations** | $0.0057 | $0.013 | $7.15* |
| **Data Retrieval** | Free | $0.01/GB | $0.022/GB |

*Archive read operations require rehydration (takes 1-15 hours)

### 2. Azure Data Factory Costs

#### Pipeline Activity Costs
| Activity Type | Price per 1,000 Runs | Notes |
|---------------|---------------------|-------|
| **Pipeline Activities** | $1.00 | Orchestration, triggers |
| **Copy Activities** | $0.25 | Data movement between tiers |
| **Data Flow Activities** | $0.274/hour | Complex transformations |

#### Data Integration Runtime
- **Managed Virtual Network**: $0.274/hour when active
- **Self-hosted Runtime**: No additional charge (uses your compute)

### 3. Azure Functions Costs

#### Consumption Plan (Recommended for X12 processing)
- **Execution Time**: $0.000016/GB-second
- **Executions**: $0.20 per million executions
- **Free Grants**: 400,000 GB-seconds + 1 million executions/month

#### Premium Plan (For consistent workloads)
- **EP1**: $148.92/month (1 vCore, 3.5 GB RAM)
- **EP2**: $297.84/month (2 vCore, 7 GB RAM)
- **EP3**: $595.68/month (4 vCore, 14 GB RAM)

### 4. Monitoring and Logging Costs

#### Log Analytics Workspace
- **Data Ingestion**: $2.30/GB (first 5 GB free per month)
- **Data Retention**: $0.10/GB/month (beyond 31 days)
- **Data Export**: $0.10/GB

#### Application Insights
- Billed through Log Analytics workspace
- Web tests: $5.00 per test per month

### 5. Supporting Services

#### Azure Key Vault
- **Key/Secret Operations**: $0.03 per 10,000 operations
- **Storage**: $1.00 per 10,000 keys/secrets per month

#### Service Bus (Standard Tier)
- **Base Cost**: $10.00/month per namespace
- **Messaging Operations**: $0.05 per million operations

---

## Pricing Models and Scenarios

### Scenario 1: Development/Testing Environment

**Monthly Volume**: 1,000 X12 transactions
**File Size**: 50 KB average per transaction
**Processing Frequency**: Daily batch processing

#### Cost Breakdown:
| Component | Monthly Cost | Details |
|-----------|--------------|---------|
| **Storage** | $5-10 | 50 MB data, mixed tiers |
| **Data Factory** | $15-25 | 30 pipeline runs/month |
| **Functions** | $0 | Within free tier |
| **Monitoring** | $10-15 | Basic logging |
| **Support Services** | $15-20 | Key Vault, Service Bus |
| **Total** | $45-70 | |

### Scenario 2: Production Environment - Medium Scale

**Monthly Volume**: 100,000 X12 transactions
**File Size**: 75 KB average per transaction
**Processing Frequency**: Hourly processing (24x/day)

#### Cost Breakdown:
| Component | Monthly Cost | Details |
|-----------|--------------|---------|
| **Storage** | $50-80 | 7.5 GB data across tiers |
| **Data Factory** | $200-300 | 720 pipeline runs/month |
| **Functions** | $25-40 | Processing time and executions |
| **Monitoring** | $75-125 | Enhanced monitoring |
| **Support Services** | $25-35 | Key Vault, Service Bus |
| **Total** | $375-580 | |

### Scenario 3: Enterprise Production - High Scale

**Monthly Volume**: 10,000,000 X12 transactions
**File Size**: 100 KB average per transaction
**Processing Frequency**: Real-time processing (continuous)

#### Cost Breakdown:
| Component | Monthly Cost | Details |
|-----------|--------------|---------|
| **Storage** | $800-1,200 | 1 TB data with lifecycle management |
| **Data Factory** | $2,000-3,000 | High-frequency processing |
| **Functions Premium** | $600-900 | EP2 plan for consistent performance |
| **Monitoring** | $500-800 | Comprehensive telemetry |
| **Support Services** | $100-150 | Enterprise features |
| **Total** | $4,000-6,050 | |

---

## Cost Calculations by Volume

### File Size Impact Analysis

| File Size | 1K files/month | 100K files/month | 10M files/month |
|-----------|----------------|------------------|-----------------|
| **25 KB** | $30-55 | $280-520 | $2,800-5,200 |
| **50 KB** | $45-75 | $420-750 | $4,200-7,500 |
| **100 KB** | $65-105 | $650-1,050 | $6,500-10,500 |
| **200 KB** | $95-155 | $950-1,550 | $9,500-15,500 |

### Processing Frequency Impact

| Frequency | Description | Cost Multiplier | Use Case |
|-----------|-------------|-----------------|----------|
| **Daily Batch** | Once per day | 1.0x | Development, small volume |
| **Hourly** | 24 times per day | 1.8x | Standard production |
| **Every 15 min** | 96 times per day | 2.5x | Near real-time |
| **Continuous** | Event-driven | 3.0x | High-volume enterprise |

### Data Retention Strategy Costs

| Retention Strategy | Storage Cost Impact | Retrieval Cost | Recommended For |
|-------------------|-------------------|----------------|-----------------|
| **30 days Hot** | Baseline | No additional cost | Active processing |
| **90 days Cool** | -45% storage cost | $0.01/GB retrieval | Recent history |
| **1 year Archive** | -90% storage cost | $0.022/GB + time | Compliance |
| **7 years Archive** | -90% storage cost | $0.022/GB + time | Legal requirements |

---

## Cost Optimization Recommendations

### 1. Storage Optimization

#### Implement Lifecycle Management
```json
{
  "rules": [
    {
      "name": "MoveToCool",
      "type": "Lifecycle",
      "definition": {
        "filters": {
          "blobTypes": ["blockBlob"],
          "prefixMatch": ["silver-x12-parsed/"]
        },
        "actions": {
          "baseBlob": {
            "tierToCool": { "daysAfterModificationGreaterThan": 30 }
          }
        }
      }
    },
    {
      "name": "MoveToArchive", 
      "type": "Lifecycle",
      "definition": {
        "filters": {
          "blobTypes": ["blockBlob"],
          "prefixMatch": ["archive-x12/"]
        },
        "actions": {
          "baseBlob": {
            "tierToArchive": { "daysAfterModificationGreaterThan": 180 }
          }
        }
      }
    }
  ]
}
```

**Expected Savings**: 40-60% on storage costs

#### Data Compression
- Implement compression for Silver and Gold layers
- Expected file size reduction: 60-80%
- **Estimated Savings**: $200-400/month for high-volume scenarios

### 2. Data Factory Optimization

#### Batch Processing Strategy
- Process files in batches of 100-500 files
- Use parallel processing where possible
- Schedule during off-peak hours for lower costs

#### Pipeline Efficiency
- Combine multiple small activities into single notebook executions
- Use dynamic parameters to reduce duplicate pipeline runs
- **Estimated Savings**: 25-35% on Data Factory costs

### 3. Function App Optimization

#### Right-sizing Strategy
| Scenario | Recommended Plan | Monthly Cost | Use Case |
|----------|------------------|--------------|----------|
| **Low Volume** | Consumption | $0-50 | < 50K transactions |
| **Medium Volume** | Consumption | $50-200 | 50K-500K transactions |
| **High Volume** | Premium EP1 | $150-300 | > 500K transactions |

#### Performance Optimization
- Optimize function memory allocation (128MB increments)
- Reduce function execution time through efficient code
- **Estimated Savings**: 20-40% on compute costs

### 4. Monitoring Optimization

#### Log Analytics Configuration
- Set appropriate retention periods (default: 31 days)
- Use Basic Log tables for debugging data
- Configure data export for long-term storage

#### Cost-Effective Monitoring
| Data Type | Retention | Cost per GB/month |
|-----------|-----------|-------------------|
| **Error Logs** | 90 days | $0.10 |
| **Performance Metrics** | 30 days | $0.10 |
| **Debug Information** | 7 days | $0.05 (Basic Logs) |

**Estimated Savings**: 30-50% on monitoring costs

---

## Monitoring and Budgeting

### 1. Cost Monitoring Setup

#### Azure Cost Management
```bash
# Create budget alert
az consumption budget create \
  --resource-group "rg-fabric-x12-pipeline" \
  --budget-name "X12-Pipeline-Budget" \
  --amount 500 \
  --time-grain Monthly \
  --time-period start="2025-01-01" \
  --category Cost
```

#### Budget Thresholds
| Volume Tier | Budget Alert Thresholds |
|-------------|------------------------|
| **Development** | 80% of $100/month |
| **Production Medium** | 80% of $750/month |
| **Production High** | 80% of $6,000/month |

### 2. Cost Tracking Queries

#### Data Factory Cost Analysis
```kusto
AzureMetrics
| where ResourceProvider == "MICROSOFT.DATAFACTORY"
| where MetricName in ("PipelineRuns", "ActivityRuns", "TriggerRuns")
| summarize Total = sum(Average) by MetricName, bin(TimeGenerated, 1d)
| order by TimeGenerated desc
```

#### Storage Cost Analysis
```kusto
Usage
| where DataType == "StorageAccount"
| where ResourceName contains "fabricx12"
| summarize TotalGB = sum(Quantity) by bin(TimeGenerated, 1d)
| order by TimeGenerated desc
```

### 3. Performance vs. Cost Optimization

#### Key Performance Indicators (KPIs)
| Metric | Target | Cost Impact |
|--------|---------|-------------|
| **Processing Time** | < 30 min/batch | Higher compute costs for faster processing |
| **Error Rate** | < 0.1% | Additional costs for retry processing |
| **Storage Efficiency** | > 80% compression | Reduced storage costs |
| **Pipeline Success Rate** | > 99.9% | Monitoring and alert costs |

---

## Appendix: Pricing References

### Current Azure Pricing (as of Sept 2025)
All prices are based on East US 2 region and are subject to change. For the most current pricing:

- [Azure Storage Pricing](https://azure.microsoft.com/pricing/details/storage/blobs/)
- [Azure Data Factory Pricing](https://azure.microsoft.com/pricing/details/data-factory/)
- [Azure Functions Pricing](https://azure.microsoft.com/pricing/details/functions/)
- [Azure Monitor Pricing](https://azure.microsoft.com/pricing/details/monitor/)

### Regional Pricing Variations
Costs may vary by Azure region. Consider these factors:
- East US 2: Baseline pricing (used in this document)
- West Europe: ~5-10% higher
- Asia Pacific: ~10-15% higher
- Government regions: ~15-20% higher

### Cost Calculator Resources
Use the [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/) to get personalized estimates based on your specific:
- Transaction volumes
- File sizes
- Processing frequency
- Retention requirements
- Regional preferences

---

## Conclusion

The Azure Fabric X12 ETL pipeline provides a scalable, cost-effective solution for healthcare EDI processing. Key cost factors include:

1. **Transaction Volume**: Primary cost driver (linear scaling)
2. **File Size**: Affects storage and processing costs
3. **Processing Frequency**: Impacts Data Factory and compute costs
4. **Retention Strategy**: Long-term storage cost optimization
5. **Monitoring Depth**: Balance between visibility and cost

**Recommended Starting Configuration**:
- Begin with Consumption plan for Functions
- Implement lifecycle management for storage
- Use Basic Log Analytics configuration
- Monitor costs weekly and optimize based on actual usage patterns

For questions or detailed cost analysis assistance, contact the development team or Azure support.