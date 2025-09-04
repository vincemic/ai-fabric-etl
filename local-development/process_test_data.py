#!/usr/bin/env python3
"""
Manual X12 file processing script to test the local environment
"""

import os
import json
import psycopg2
from datetime import datetime
from pathlib import Path

# Database connection
DB_CONFIG = {
    'host': 'x12-data-db',
    'port': 5432,
    'database': 'x12_data',
    'user': 'x12user',
    'password': 'x12password'
}

def connect_db():
    """Create database connection"""
    return psycopg2.connect(**DB_CONFIG)

def parse_x12_file(file_path):
    """Parse X12 file and extract basic information"""
    with open(file_path, 'r') as f:
        content = f.read().strip()
    
    # Basic X12 parsing
    segments = content.split('~')
    segments = [seg.strip() for seg in segments if seg.strip()]
    
    # Extract transaction type from filename
    filename = os.path.basename(file_path)
    transaction_type = filename.split('_')[2]  # e.g., test_x12_837_... -> 837
    
    # Simple quality scoring based on segment count and structure
    quality_score = min(100, len(segments) * 10)  # Basic scoring
    
    # Create parsed data structure
    parsed_data = {
        'source_filename': filename,
        'transaction_type': transaction_type,
        'total_segments': len(segments),
        'quality_score': quality_score,
        'segments': [{'segment_id': seg.split('*')[0], 'data': seg} for seg in segments if '*' in seg],
        'raw_content': content
    }
    
    return parsed_data

def process_bronze_layer(file_path):
    """Process file and insert into bronze layer"""
    filename = os.path.basename(file_path)
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bronze_x12 (source_filename, raw_content, file_size, ingestion_timestamp, status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (filename, content, len(content), datetime.now(), 'processed'))
            
            bronze_id = cur.fetchone()[0]
            conn.commit()
            print(f"✓ Bronze layer: Inserted {filename} with ID {bronze_id}")
            return bronze_id
    finally:
        conn.close()

def process_silver_layer(bronze_id, parsed_data):
    """Process parsed data and insert into silver layer"""
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO silver_transactions (
                    bronze_id, source_filename, transaction_type, 
                    total_segments, quality_score, segments_json,
                    parsing_timestamp, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING transaction_id
            """, (
                bronze_id,
                parsed_data['source_filename'],
                parsed_data['transaction_type'],
                parsed_data['total_segments'],
                parsed_data['quality_score'],
                json.dumps(parsed_data['segments']),
                datetime.now(),
                'valid' if parsed_data['quality_score'] > 50 else 'invalid'
            ))
            
            transaction_id = cur.fetchone()[0]
            conn.commit()
            print(f"✓ Silver layer: Processed transaction {transaction_id} (quality: {parsed_data['quality_score']})")
            return transaction_id
    finally:
        conn.close()

def process_gold_layer(transaction_id, parsed_data):
    """Process business analytics and insert into gold layer"""
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            # Insert into transaction summary
            cur.execute("""
                INSERT INTO gold_transaction_summary (
                    transaction_date, transaction_type, total_count,
                    avg_quality_score, total_volume
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (transaction_date, transaction_type) 
                DO UPDATE SET 
                    total_count = gold_transaction_summary.total_count + 1,
                    avg_quality_score = (gold_transaction_summary.avg_quality_score + EXCLUDED.avg_quality_score) / 2,
                    total_volume = gold_transaction_summary.total_volume + EXCLUDED.total_volume
            """, (
                datetime.now().date(),
                parsed_data['transaction_type'],
                1,
                parsed_data['quality_score'],
                len(parsed_data['raw_content'])
            ))
            
            # Insert into daily analytics
            cur.execute("""
                INSERT INTO gold_daily_analytics (
                    processing_date, files_processed, total_transactions,
                    avg_quality_score, total_data_volume
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (processing_date)
                DO UPDATE SET
                    files_processed = gold_daily_analytics.files_processed + 1,
                    total_transactions = gold_daily_analytics.total_transactions + 1,
                    avg_quality_score = (gold_daily_analytics.avg_quality_score + EXCLUDED.avg_quality_score) / 2,
                    total_data_volume = gold_daily_analytics.total_data_volume + EXCLUDED.total_data_volume
            """, (
                datetime.now().date(),
                1,
                1,
                parsed_data['quality_score'],
                len(parsed_data['raw_content'])
            ))
            
            conn.commit()
            print(f"✓ Gold layer: Updated analytics for {parsed_data['transaction_type']}")
    finally:
        conn.close()

def process_files_in_directory(input_dir):
    """Process all X12 files in the input directory"""
    input_path = Path(input_dir)
    x12_files = list(input_path.glob("*.x12"))
    
    if not x12_files:
        print(f"No X12 files found in {input_dir}")
        return
    
    print(f"Found {len(x12_files)} X12 files to process...")
    
    for file_path in x12_files:
        print(f"\nProcessing {file_path.name}...")
        
        try:
            # Parse the file
            parsed_data = parse_x12_file(file_path)
            
            # Bronze layer
            bronze_id = process_bronze_layer(file_path)
            
            # Silver layer
            transaction_id = process_silver_layer(bronze_id, parsed_data)
            
            # Gold layer
            process_gold_layer(transaction_id, parsed_data)
            
            print(f"✓ Successfully processed {file_path.name}")
            
        except Exception as e:
            print(f"✗ Error processing {file_path.name}: {e}")

def show_processing_results():
    """Display processing results"""
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            # Bronze layer stats
            cur.execute("SELECT COUNT(*), status FROM bronze_x12 GROUP BY status")
            bronze_stats = cur.fetchall()
            
            # Silver layer stats
            cur.execute("SELECT COUNT(*), transaction_type FROM silver_transactions GROUP BY transaction_type")
            silver_stats = cur.fetchall()
            
            # Gold layer stats
            cur.execute("SELECT * FROM gold_daily_analytics ORDER BY processing_date DESC LIMIT 1")
            daily_stats = cur.fetchone()
            
            print("\n" + "="*50)
            print("PROCESSING RESULTS")
            print("="*50)
            
            print("\nBronze Layer (Raw Files):")
            for count, status in bronze_stats:
                print(f"  {status}: {count} files")
            
            print("\nSilver Layer (Parsed Transactions):")
            for count, tx_type in silver_stats:
                print(f"  {tx_type}: {count} transactions")
            
            if daily_stats:
                print(f"\nGold Layer (Daily Analytics):")
                print(f"  Date: {daily_stats[1]}")
                print(f"  Files Processed: {daily_stats[2]}")
                print(f"  Total Transactions: {daily_stats[3]}")
                print(f"  Average Quality Score: {daily_stats[4]:.1f}")
                print(f"  Total Data Volume: {daily_stats[5]:,} bytes")
            
    finally:
        conn.close()

if __name__ == "__main__":
    input_directory = "processed/input"
    
    print("Starting X12 file processing...")
    print(f"Input directory: {input_directory}")
    
    # Process all files
    process_files_in_directory(input_directory)
    
    # Show results
    show_processing_results()
    
    print("\nProcessing complete! 🎉")