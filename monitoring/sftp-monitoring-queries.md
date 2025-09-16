# SFTP Operations Monitoring Queries for Application Insights

## SFTP Connection Health Monitoring

### Query: SFTP Connection Success Rate (Last 24 Hours)
```kusto
traces
| where timestamp > ago(24h)
| where message contains "SFTP" and (message contains "connected" or message contains "failed")
| extend ConnectionResult = case(
    message contains "Successfully connected", "Success",
    message contains "Connection failed", "Failed",
    message contains "Authentication failed", "AuthFailed",
    "Other"
)
| summarize 
    Total = count(),
    Successful = countif(ConnectionResult == "Success"),
    Failed = countif(ConnectionResult == "Failed"),
    AuthFailed = countif(ConnectionResult == "AuthFailed")
    by bin(timestamp, 1h)
| extend SuccessRate = round(Successful * 100.0 / Total, 2)
| order by timestamp desc
```

### Query: SFTP Partner Connection Status
```kusto
traces
| where timestamp > ago(4h)
| where message contains "Health check for" 
| extend Partner = extract(@"Health check for (\w+)", 1, message)
| extend Status = extract(@"successful - (\w+)", 1, message)
| where isnotempty(Partner) and isnotempty(Status)
| summarize LatestStatus = arg_max(timestamp, Status) by Partner
| project Partner, Status = LatestStatus, LastCheck = timestamp
```

## File Processing Monitoring

### Query: SFTP File Transfer Volume (Last 24 Hours)
```kusto
traces
| where timestamp > ago(24h)
| where message contains "Successfully" and (message contains "downloaded" or message contains "uploaded")
| extend 
    Operation = case(
        message contains "downloaded", "Download",
        message contains "uploaded", "Upload",
        "Other"
    ),
    Partner = extract(@"for (\w+)", 1, message),
    FileName = extract(@"(\w+\.x12)", 1, message)
| where isnotempty(Operation) and isnotempty(Partner)
| summarize FileCount = count() by bin(timestamp, 1h), Operation, Partner
| order by timestamp desc
```

### Query: SFTP File Processing Errors
```kusto
traces
| where timestamp > ago(24h)
| where severityLevel >= 3  // Warning and above
| where message contains "SFTP" or message contains "trading partner"
| extend 
    Partner = extract(@"partner (\w+)", 1, message),
    ErrorType = case(
        message contains "Connection", "Connection",
        message contains "Authentication", "Authentication", 
        message contains "Permission", "Permission",
        message contains "File", "File",
        "Other"
    )
| project timestamp, severityLevel, message, Partner, ErrorType
| order by timestamp desc
```

## Performance Monitoring

### Query: SFTP Connection Performance
```kusto
traces
| where timestamp > ago(24h)
| where message contains "connection_time_ms"
| extend 
    Partner = extract(@"partner (\w+)", 1, message),
    ConnectionTime = todouble(extract(@"connection_time_ms.*?(\d+\.?\d*)", 1, message))
| where isnotempty(Partner) and isnotempty(ConnectionTime)
| summarize 
    AvgConnectionTime = avg(ConnectionTime),
    MaxConnectionTime = max(ConnectionTime),
    MinConnectionTime = min(ConnectionTime),
    ConnectionCount = count()
    by Partner, bin(timestamp, 1h)
| order by timestamp desc
```

### Query: Large File Detection
```kusto
traces
| where timestamp > ago(24h)
| where message contains "too large"
| extend 
    Partner = extract(@"partner (\w+)", 1, message),
    FileName = extract(@"File (\S+)", 1, message),
    FileSize = extract(@"(\d+) bytes", 1, message)
| project timestamp, Partner, FileName, FileSize = todouble(FileSize) / 1024 / 1024
| order by timestamp desc
```

## Business Intelligence Queries

### Query: Daily SFTP Operations Summary
```kusto
traces
| where timestamp > ago(7d)
| where message contains "SFTP Fetch Summary" or message contains "SFTP Push Summary"
| extend 
    Date = format_datetime(timestamp, "yyyy-MM-dd"),
    Operation = case(
        message contains "Fetch", "Fetch",
        message contains "Push", "Push",
        "Unknown"
    ),
    TotalFiles = toint(extract(@"Total.*?(\d+)", 1, message)),
    SuccessfulFiles = toint(extract(@"Success.*?(\d+)", 1, message)),
    FailedFiles = toint(extract(@"Failed.*?(\d+)", 1, message))
| summarize 
    TotalFiles = sum(TotalFiles),
    SuccessfulFiles = sum(SuccessfulFiles), 
    FailedFiles = sum(FailedFiles)
    by Date, Operation
| extend SuccessRate = round(SuccessfulFiles * 100.0 / TotalFiles, 2)
| order by Date desc
```

### Query: Trading Partner Activity Matrix
```kusto
traces
| where timestamp > ago(30d)
| where message contains "Successfully" and (message contains "processed" or message contains "uploaded")
| extend 
    Partner = extract(@"for (\w+)|to (\w+)", 1, message),
    Week = format_datetime(timestamp, "yyyy-W")
| where isnotempty(Partner)
| summarize FileCount = count() by Week, Partner
| evaluate pivot(Partner, sum(FileCount))
| order by Week desc
```

## Alert Queries

### Alert: High SFTP Failure Rate
```kusto
traces
| where timestamp > ago(1h)
| where message contains "SFTP" and (message contains "failed" or message contains "error")
| summarize FailureCount = count() by bin(timestamp, 15m)
| where FailureCount > 5  // Alert if more than 5 failures in 15 minutes
```

### Alert: SFTP Partner Connectivity Issues
```kusto
traces
| where timestamp > ago(30m)
| where message contains "Connection failed" or message contains "Authentication failed"
| extend Partner = extract(@"for (\w+)|to (\w+)", 1, message)
| summarize FailedAttempts = count() by Partner
| where FailedAttempts >= 3  // Alert if 3+ failures for same partner
```

### Alert: No Files Received from Partners
```kusto
traces
| where timestamp between (ago(4h) .. ago(2h))
| where message contains "Found 0 eligible files"
| extend Partner = extract(@"partner (\w+)", 1, message)
| summarize NoFilePartners = make_set(Partner)
| where array_length(NoFilePartners) > 0
```

## Custom Metrics

### Query: SFTP Throughput Metrics
```kusto
traces
| where timestamp > ago(24h)
| where message contains "Successfully" and message contains "bytes"
| extend 
    Bytes = todouble(extract(@"(\d+) bytes", 1, message)),
    Partner = extract(@"for (\w+)|to (\w+)", 1, message)
| where isnotempty(Bytes) and isnotempty(Partner)
| summarize 
    TotalBytes = sum(Bytes),
    FileCount = count(),
    AvgFileSize = avg(Bytes)
    by bin(timestamp, 1h), Partner
| extend TotalMB = round(TotalBytes / 1024 / 1024, 2)
| order by timestamp desc
```