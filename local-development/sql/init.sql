-- Initialize database schema for local X12 processing
-- This script creates tables that mirror the Azure Fabric lakehouse structure

-- Bronze layer table - stores raw file metadata
CREATE TABLE IF NOT EXISTS bronze_x12 (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT,
    file_size BIGINT,
    processing_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',
    raw_content_sample TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Silver layer table - stores parsed transaction data
CREATE TABLE IF NOT EXISTS silver_transactions (
    id SERIAL PRIMARY KEY,
    source_filename VARCHAR(255) NOT NULL,
    transaction_type VARCHAR(100),
    transaction_code VARCHAR(10),
    total_segments INTEGER,
    quality_score INTEGER,
    parsing_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    segments_json JSONB,
    status VARCHAR(50) DEFAULT 'parsed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Gold layer analytics tables
CREATE TABLE IF NOT EXISTS gold_transaction_summary (
    id SERIAL PRIMARY KEY,
    processing_date DATE DEFAULT CURRENT_DATE,
    transaction_type VARCHAR(100),
    transaction_count INTEGER DEFAULT 0,
    average_quality_score DECIMAL(5,2),
    total_segments INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gold_daily_analytics (
    id SERIAL PRIMARY KEY,
    analytics_date DATE DEFAULT CURRENT_DATE,
    total_files_processed INTEGER DEFAULT 0,
    high_quality_files INTEGER DEFAULT 0,
    medium_quality_files INTEGER DEFAULT 0,
    low_quality_files INTEGER DEFAULT 0,
    transaction_types_json JSONB,
    segment_analysis_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Healthcare-specific analytics tables
CREATE TABLE IF NOT EXISTS gold_claim_analytics (
    id SERIAL PRIMARY KEY,
    processing_date DATE DEFAULT CURRENT_DATE,
    claim_type VARCHAR(50), -- Professional, Institutional, Dental
    total_claims INTEGER DEFAULT 0,
    total_claim_amount DECIMAL(15,2) DEFAULT 0,
    average_claim_amount DECIMAL(10,2) DEFAULT 0,
    provider_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gold_payment_analytics (
    id SERIAL PRIMARY KEY,
    processing_date DATE DEFAULT CURRENT_DATE,
    payer_name VARCHAR(255),
    total_payments INTEGER DEFAULT 0,
    total_payment_amount DECIMAL(15,2) DEFAULT 0,
    average_payment_amount DECIMAL(10,2) DEFAULT 0,
    adjustment_amount DECIMAL(15,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gold_eligibility_analytics (
    id SERIAL PRIMARY KEY,
    processing_date DATE DEFAULT CURRENT_DATE,
    inquiry_count INTEGER DEFAULT 0,
    response_count INTEGER DEFAULT 0,
    active_coverage_count INTEGER DEFAULT 0,
    inactive_coverage_count INTEGER DEFAULT 0,
    average_response_time_minutes DECIMAL(8,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Data quality monitoring tables
CREATE TABLE IF NOT EXISTS gold_data_quality_metrics (
    id SERIAL PRIMARY KEY,
    processing_date DATE DEFAULT CURRENT_DATE,
    total_files INTEGER DEFAULT 0,
    validation_errors INTEGER DEFAULT 0,
    parsing_errors INTEGER DEFAULT 0,
    business_rule_violations INTEGER DEFAULT 0,
    overall_quality_score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Processing audit trail
CREATE TABLE IF NOT EXISTS processing_audit (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(100),
    stage VARCHAR(20), -- bronze, silver, gold
    filename VARCHAR(255),
    status VARCHAR(50), -- success, failed, processing
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    records_processed INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_bronze_x12_filename ON bronze_x12(filename);
CREATE INDEX IF NOT EXISTS idx_bronze_x12_status ON bronze_x12(status);
CREATE INDEX IF NOT EXISTS idx_bronze_x12_processing_timestamp ON bronze_x12(processing_timestamp);

CREATE INDEX IF NOT EXISTS idx_silver_transactions_source_filename ON silver_transactions(source_filename);
CREATE INDEX IF NOT EXISTS idx_silver_transactions_transaction_type ON silver_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_silver_transactions_quality_score ON silver_transactions(quality_score);
CREATE INDEX IF NOT EXISTS idx_silver_transactions_parsing_timestamp ON silver_transactions(parsing_timestamp);

CREATE INDEX IF NOT EXISTS idx_gold_transaction_summary_date ON gold_transaction_summary(processing_date);
CREATE INDEX IF NOT EXISTS idx_gold_transaction_summary_type ON gold_transaction_summary(transaction_type);

CREATE INDEX IF NOT EXISTS idx_gold_daily_analytics_date ON gold_daily_analytics(analytics_date);

CREATE INDEX IF NOT EXISTS idx_processing_audit_batch_id ON processing_audit(batch_id);
CREATE INDEX IF NOT EXISTS idx_processing_audit_stage ON processing_audit(stage);
CREATE INDEX IF NOT EXISTS idx_processing_audit_status ON processing_audit(status);

-- Insert sample data for testing
INSERT INTO bronze_x12 (filename, file_path, file_size, status, raw_content_sample) VALUES
('sample_837_claim.x12', '/input/sample_837_claim.x12', 2048, 'validated', 'ISA*00*          *00*          *ZZ*SUBMITTER_ID   *ZZ*RECEIVER_ID    *230904*1234*^*00501*000000001*0*P*>~'),
('sample_835_payment.x12', '/input/sample_835_payment.x12', 1536, 'validated', 'ISA*00*          *00*          *ZZ*PAYER_ID       *ZZ*PROVIDER_ID    *230904*1235*^*00501*000000002*0*P*>~');

INSERT INTO silver_transactions (source_filename, transaction_type, transaction_code, total_segments, quality_score, segments_json) VALUES
('sample_837_claim.x12', 'Healthcare Claim', '837', 45, 92, '{"segments": [{"segment_id": "ISA", "elements": ["00", "", "00", "", "ZZ", "SUBMITTER_ID", "ZZ", "RECEIVER_ID"]}]}'),
('sample_835_payment.x12', 'Payment/Remittance', '835', 32, 88, '{"segments": [{"segment_id": "ISA", "elements": ["00", "", "00", "", "ZZ", "PAYER_ID", "ZZ", "PROVIDER_ID"]}]}');

INSERT INTO gold_transaction_summary (transaction_type, transaction_count, average_quality_score, total_segments) VALUES
('Healthcare Claim', 1, 92.00, 45),
('Payment/Remittance', 1, 88.00, 32);

INSERT INTO gold_daily_analytics (total_files_processed, high_quality_files, medium_quality_files, low_quality_files, transaction_types_json, segment_analysis_json) VALUES
(2, 2, 0, 0, '{"Healthcare Claim": 1, "Payment/Remittance": 1}', '{"ISA": 2, "GS": 2, "ST": 2, "BHT": 2}');

-- Create views for common queries
CREATE OR REPLACE VIEW v_daily_processing_summary AS
SELECT 
    processing_date,
    COUNT(*) as total_files,
    AVG(quality_score) as avg_quality_score,
    COUNT(CASE WHEN quality_score > 80 THEN 1 END) as high_quality_files,
    COUNT(CASE WHEN quality_score BETWEEN 50 AND 80 THEN 1 END) as medium_quality_files,
    COUNT(CASE WHEN quality_score < 50 THEN 1 END) as low_quality_files
FROM silver_transactions 
WHERE parsing_timestamp::date = CURRENT_DATE
GROUP BY processing_date;

CREATE OR REPLACE VIEW v_transaction_type_breakdown AS
SELECT 
    transaction_type,
    COUNT(*) as file_count,
    AVG(quality_score) as avg_quality_score,
    SUM(total_segments) as total_segments,
    MIN(parsing_timestamp) as first_processed,
    MAX(parsing_timestamp) as last_processed
FROM silver_transactions
GROUP BY transaction_type
ORDER BY file_count DESC;

CREATE OR REPLACE VIEW v_recent_processing_activity AS
SELECT 
    b.filename,
    b.file_size,
    b.processing_timestamp as bronze_timestamp,
    s.transaction_type,
    s.quality_score,
    s.parsing_timestamp as silver_timestamp,
    EXTRACT(EPOCH FROM (s.parsing_timestamp - b.processing_timestamp)) as processing_duration_seconds
FROM bronze_x12 b
LEFT JOIN silver_transactions s ON b.filename = s.source_filename
WHERE b.processing_timestamp >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY b.processing_timestamp DESC;

-- Grant permissions (adjust as needed for your setup)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO x12user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO x12user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO x12user;