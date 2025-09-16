# Databricks notebook source
# MAGIC %md
# MAGIC # Generate X12 Acknowledgments for Trading Partners
# MAGIC 
# MAGIC This notebook generates X12 997 Functional Acknowledgments for processed trading partner files.
# MAGIC These acknowledgments are then pushed back to trading partners via SFTP.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup and Configuration

# COMMAND ----------

import os
import json
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration Parameters

# COMMAND ----------

# Configuration parameters
dbutils.widgets.text("storage_account_name", "", "Storage Account Name")
dbutils.widgets.text("batch_id", "", "Batch ID")
dbutils.widgets.text("processing_date", "", "Processing Date (YYYY-MM-DD)")

# Get parameter values
STORAGE_ACCOUNT_NAME = dbutils.widgets.get("storage_account_name")
BATCH_ID = dbutils.widgets.get("batch_id")
PROCESSING_DATE = dbutils.widgets.get("processing_date") or datetime.now().strftime("%Y-%m-%d")

# Storage paths
SILVER_PATH = f"abfss://silver-x12-parsed@{STORAGE_ACCOUNT_NAME}.dfs.core.windows.net/"
SFTP_OUTBOUND_PATH = f"abfss://sftp-outbound@{STORAGE_ACCOUNT_NAME}.dfs.core.windows.net/"

print(f"Silver Path: {SILVER_PATH}")
print(f"SFTP Outbound Path: {SFTP_OUTBOUND_PATH}")
print(f"Processing Date: {PROCESSING_DATE}")
print(f"Batch ID: {BATCH_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Processed Files Data

# COMMAND ----------

# Read silver layer data for the processing date
silver_df = spark.read.format("delta").load(SILVER_PATH) \
    .filter(col("processing_date") == PROCESSING_DATE) \
    .filter(col("source_system") == "trading_partners")

print(f"Loaded {silver_df.count()} processed files from silver layer")

# COMMAND ----------

# MAGIC %md
# MAGIC ## X12 997 Acknowledgment Generation Functions

# COMMAND ----------

def generate_997_acknowledgment(
    sender_id: str,
    receiver_id: str,
    functional_group_control_number: str,
    transaction_set_control_numbers: list,
    ack_code: str = "A",  # A=Accept, E=Error, R=Reject
    error_codes: list = None
) -> str:
    """
    Generate X12 997 Functional Acknowledgment.
    
    Args:
        sender_id: Original sender ID (becomes receiver in ack)
        receiver_id: Original receiver ID (becomes sender in ack)
        functional_group_control_number: GS06 from original transmission
        transaction_set_control_numbers: List of ST02 values from original
        ack_code: Acknowledgment code (A/E/R)
        error_codes: List of error codes if any
        
    Returns:
        Complete X12 997 transaction as string
    """
    
    current_date = datetime.now()
    current_time = current_date.strftime("%H%M")
    current_date_str = current_date.strftime("%y%m%d")
    
    # Generate control numbers
    interchange_control_number = current_date.strftime("%y%m%d%H%M")
    group_control_number = current_date.strftime("%H%M%S")
    transaction_control_number = "0001"
    
    # ISA Header
    isa = f"ISA*00*          *00*          *ZZ*{receiver_id:<15}*ZZ*{sender_id:<15}*{current_date_str}*{current_time}*^*00501*{interchange_control_number}*0*T*:~"
    
    # GS Header
    gs = f"GS*FA*{receiver_id}*{sender_id}*{current_date.strftime('%Y%m%d')}*{current_time}*{group_control_number}*X*005010~"
    
    # ST Header - 997 Transaction Set
    st = f"ST*997*{transaction_control_number}~"
    
    # AK1 - Functional Group Response Header
    ak1 = f"AK1*{functional_group_control_number[:2]}*{functional_group_control_number}~"
    
    # AK2/AK5 pairs for each transaction set
    ak_segments = []
    for ts_control in transaction_set_control_numbers:
        ak2 = f"AK2*{ts_control[:3]}*{ts_control}~"
        ak5 = f"AK5*{ack_code}~"
        ak_segments.extend([ak2, ak5])
    
    # AK9 - Functional Group Response Trailer
    accepted_count = len([ts for ts in transaction_set_control_numbers]) if ack_code == "A" else 0
    ak9 = f"AK9*{ack_code}*{len(transaction_set_control_numbers)}*{len(transaction_set_control_numbers)}*{accepted_count}~"
    
    # SE Trailer
    segment_count = 4 + len(ak_segments) + 1  # ST + AK1 + AK2/AK5 pairs + AK9 + SE
    se = f"SE*{segment_count}*{transaction_control_number}~"
    
    # GE Trailer
    ge = f"GE*1*{group_control_number}~"
    
    # IEA Trailer
    iea = f"IEA*1*{interchange_control_number}~"
    
    # Combine all segments
    segments = [isa, gs, st, ak1] + ak_segments + [ak9, se, ge, iea]
    
    return "\n".join(segments)

# Register UDF for generating acknowledgments
generate_997_udf = udf(generate_997_acknowledgment, StringType())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Group Files by Trading Partner and Generate Acknowledgments

# COMMAND ----------

# Group processed files by trading partner and extract control numbers
partner_summary = silver_df.groupBy("sender_id", "receiver_id") \
    .agg(
        collect_list("interchange_control_number").alias("interchange_numbers"),
        collect_list("group_control_number").alias("group_numbers"),
        collect_list("transaction_control_number").alias("transaction_numbers"),
        count("*").alias("file_count"),
        max("processing_timestamp").alias("last_processed"),
        collect_list("file_name").alias("processed_files")
    )

print(f"Processing acknowledgments for {partner_summary.count()} trading partners")

# COMMAND ----------

# Generate acknowledgments for each partner
acknowledgments_df = partner_summary.withColumn(
    "acknowledgment_content",
    generate_997_udf(
        col("sender_id"),
        col("receiver_id"), 
        col("group_numbers").getItem(0),  # Use first group number as reference
        col("transaction_numbers"),
        lit("A")  # Accept all for now - could be enhanced with error detection
    )
).withColumn(
    "ack_filename",
    concat(
        col("sender_id"), 
        lit("_997_"), 
        lit(BATCH_ID),
        lit(".x12")
    )
).withColumn(
    "generation_timestamp",
    current_timestamp()
).withColumn(
    "partner_directory",
    concat(
        lit("acknowledgments/"),
        date_format(current_timestamp(), "yyyy/MM/dd"),
        lit("/"),
        col("sender_id")
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save Acknowledgments to SFTP Outbound Container

# COMMAND ----------

# Save acknowledgment metadata
acknowledgments_df.select(
    "sender_id",
    "receiver_id", 
    "ack_filename",
    "file_count",
    "generation_timestamp",
    "partner_directory",
    "processed_files"
).write \
.mode("overwrite") \
.option("path", f"{SFTP_OUTBOUND_PATH}metadata/acknowledgments_{PROCESSING_DATE}/") \
.saveAsTable("acknowledgment_metadata")

print("✓ Saved acknowledgment metadata")

# COMMAND ----------

# Save acknowledgment files to storage
acknowledgment_files = acknowledgments_df.collect()

for ack_row in acknowledgment_files:
    partner_id = ack_row["sender_id"]
    filename = ack_row["ack_filename"] 
    content = ack_row["acknowledgment_content"]
    directory = ack_row["partner_directory"]
    
    # Create full path
    blob_path = f"{directory}/{filename}"
    
    # Write file content to blob storage
    # Note: In a real implementation, you would use Azure SDK to write the blob
    # For this example, we'll save it as a single-row DataFrame
    ack_content_df = spark.createDataFrame([(content,)], ["content"])
    
    # Save to blob storage
    ack_content_df.coalesce(1) \
        .write \
        .mode("overwrite") \
        .text(f"{SFTP_OUTBOUND_PATH}{blob_path}")
    
    logger.info(f"Generated acknowledgment for partner {partner_id}: {blob_path}")

print(f"✓ Generated {len(acknowledgment_files)} acknowledgment files")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary and Notification

# COMMAND ----------

# Create summary report
summary_report = {
    "processing_date": PROCESSING_DATE,
    "batch_id": BATCH_ID,
    "total_partners": len(acknowledgment_files),
    "total_files_acknowledged": sum([row["file_count"] for row in acknowledgment_files]),
    "acknowledgments_generated": len(acknowledgment_files),
    "generation_timestamp": datetime.now().isoformat(),
    "partners": [
        {
            "partner_id": row["sender_id"],
            "files_acknowledged": row["file_count"],
            "acknowledgment_filename": row["ack_filename"],
            "blob_path": f"{row['partner_directory']}/{row['ack_filename']}"
        }
        for row in acknowledgment_files
    ]
}

print("Acknowledgment Generation Summary:")
print(f"  - Partners: {summary_report['total_partners']}")
print(f"  - Files Acknowledged: {summary_report['total_files_acknowledged']}")
print(f"  - Acknowledgments Generated: {summary_report['acknowledgments_generated']}")

# Save summary report
summary_df = spark.createDataFrame([json.dumps(summary_report)], StringType()).toDF("summary_json")
summary_df.write \
    .mode("overwrite") \
    .text(f"{SFTP_OUTBOUND_PATH}reports/acknowledgment_summary_{PROCESSING_DATE}_{BATCH_ID}.json")

print("✓ Acknowledgment generation completed successfully")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Optional: Validate Generated Acknowledgments

# COMMAND ----------

def validate_x12_997(content: str) -> bool:
    """Basic validation of X12 997 structure."""
    lines = content.strip().split('\n')
    
    # Check required segments
    required_segments = ['ISA', 'GS', 'ST*997', 'AK1', 'AK9', 'SE', 'GE', 'IEA']
    
    content_str = '\n'.join(lines)
    for segment in required_segments:
        if segment not in content_str:
            return False
    
    # Check segment order
    if not lines[0].startswith('ISA'):
        return False
    if not lines[-1].startswith('IEA'):
        return False
    
    return True

# Validate generated acknowledgments
validation_results = []
for ack_row in acknowledgment_files:
    is_valid = validate_x12_997(ack_row["acknowledgment_content"])
    validation_results.append({
        "partner_id": ack_row["sender_id"],
        "filename": ack_row["ack_filename"],
        "is_valid": is_valid
    })

valid_count = sum(1 for r in validation_results if r["is_valid"])
print(f"Validation Results: {valid_count}/{len(validation_results)} acknowledgments are valid")

if valid_count < len(validation_results):
    print("⚠️  Some acknowledgments failed validation:")
    for result in validation_results:
        if not result["is_valid"]:
            print(f"  - {result['partner_id']}: {result['filename']}")
else:
    print("✓ All acknowledgments passed validation")