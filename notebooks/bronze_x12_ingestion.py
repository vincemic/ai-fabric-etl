# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Layer - X12 File Ingestion
# MAGIC 
# MAGIC This notebook handles the ingestion of raw X12 files from Azure Storage into the Bronze layer.
# MAGIC It performs basic validation and metadata extraction without transforming the data.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup and Configuration

# COMMAND ----------

import os
import json
from datetime import datetime
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

# Configuration - these should be passed as parameters or retrieved from Key Vault
dbutils.widgets.text("storage_account_name", "", "Storage Account Name")
dbutils.widgets.text("source_container", "bronze-x12-raw", "Source Container")
dbutils.widgets.text("target_container", "bronze-x12-raw", "Target Container") 
dbutils.widgets.text("file_pattern", "*.x12", "File Pattern")
dbutils.widgets.text("batch_id", "", "Batch ID")

# Get parameter values
STORAGE_ACCOUNT_NAME = dbutils.widgets.get("storage_account_name")
SOURCE_CONTAINER = dbutils.widgets.get("source_container")
TARGET_CONTAINER = dbutils.widgets.get("target_container")
FILE_PATTERN = dbutils.widgets.get("file_pattern")
BATCH_ID = dbutils.widgets.get("batch_id") or datetime.now().strftime("%Y%m%d_%H%M%S")

# Storage paths
SOURCE_PATH = f"abfss://{SOURCE_CONTAINER}@{STORAGE_ACCOUNT_NAME}.dfs.core.windows.net/"
TARGET_PATH = f"abfss://{TARGET_CONTAINER}@{STORAGE_ACCOUNT_NAME}.dfs.core.windows.net/processed/"

print(f"Source Path: {SOURCE_PATH}")
print(f"Target Path: {TARGET_PATH}")
print(f"Batch ID: {BATCH_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## X12 File Processing Functions

# COMMAND ----------

def extract_x12_metadata(file_content):
    """
    Extract metadata from X12 file content.
    
    Args:
        file_content (str): Raw X12 file content
        
    Returns:
        dict: Extracted metadata
    """
    metadata = {
        "file_size": len(file_content),
        "line_count": file_content.count('\n'),
        "interchange_control_header": None,
        "functional_group_header": None,
        "transaction_set_header": None,
        "segment_count": 0,
        "element_separator": None,
        "segment_terminator": None
    }
    
    try:
        # X12 files typically start with ISA (Interchange Control Header)
        if file_content.startswith('ISA'):
            # Extract element separator (position 3)
            metadata["element_separator"] = file_content[3] if len(file_content) > 3 else None
            
            # Extract segment terminator (usually at end of ISA segment)
            isa_end = file_content.find('\n')
            if isa_end > 0:
                metadata["segment_terminator"] = file_content[isa_end-1] if file_content[isa_end-1] not in ['\r', '\n'] else None
            
            # Count segments (rough estimate)
            if metadata["segment_terminator"]:
                metadata["segment_count"] = file_content.count(metadata["segment_terminator"])
            
            # Extract ISA header info
            if metadata["element_separator"]:
                isa_elements = file_content.split('\n')[0].split(metadata["element_separator"])
                if len(isa_elements) >= 16:
                    metadata["interchange_control_header"] = {
                        "authorization_info": isa_elements[1],
                        "sender_id": isa_elements[6],
                        "receiver_id": isa_elements[8],
                        "interchange_date": isa_elements[9],
                        "interchange_time": isa_elements[10],
                        "control_number": isa_elements[13]
                    }
        
        # Look for GS (Functional Group Header)
        gs_start = file_content.find('GS' + (metadata["element_separator"] or '*'))
        if gs_start >= 0:
            gs_line_end = file_content.find(metadata["segment_terminator"] or '~', gs_start)
            if gs_line_end > gs_start:
                gs_segment = file_content[gs_start:gs_line_end]
                gs_elements = gs_segment.split(metadata["element_separator"] or '*')
                if len(gs_elements) >= 8:
                    metadata["functional_group_header"] = {
                        "functional_id_code": gs_elements[1],
                        "application_sender": gs_elements[2],
                        "application_receiver": gs_elements[3],
                        "date": gs_elements[4],
                        "time": gs_elements[5],
                        "group_control_number": gs_elements[6]
                    }
        
        # Look for ST (Transaction Set Header)
        st_start = file_content.find('ST' + (metadata["element_separator"] or '*'))
        if st_start >= 0:
            st_line_end = file_content.find(metadata["segment_terminator"] or '~', st_start)
            if st_line_end > st_start:
                st_segment = file_content[st_start:st_line_end]
                st_elements = st_segment.split(metadata["element_separator"] or '*')
                if len(st_elements) >= 3:
                    metadata["transaction_set_header"] = {
                        "transaction_set_id": st_elements[1],
                        "control_number": st_elements[2]
                    }
    
    except Exception as e:
        logger.error(f"Error extracting X12 metadata: {str(e)}")
        metadata["extraction_error"] = str(e)
    
    return metadata

# COMMAND ----------

def validate_x12_file(file_content):
    """
    Perform basic validation on X12 file.
    
    Args:
        file_content (str): Raw X12 file content
        
    Returns:
        dict: Validation results
    """
    validation_results = {
        "is_valid": True,
        "errors": [],
        "warnings": []
    }
    
    try:
        # Check if file starts with ISA
        if not file_content.startswith('ISA'):
            validation_results["is_valid"] = False
            validation_results["errors"].append("File does not start with ISA segment")
        
        # Check minimum file size
        if len(file_content) < 100:
            validation_results["is_valid"] = False
            validation_results["errors"].append("File too small to be valid X12")
        
        # Check for required segments
        required_segments = ['ISA', 'GS', 'ST']
        for segment in required_segments:
            if segment not in file_content:
                validation_results["errors"].append(f"Missing required segment: {segment}")
                validation_results["is_valid"] = False
        
        # Check for proper segment termination
        if file_content.count('~') < 3:  # ISA, GS, ST minimum
            validation_results["warnings"].append("Unusual number of segment terminators")
        
        # Check file encoding
        try:
            file_content.encode('ascii')
        except UnicodeEncodeError:
            validation_results["warnings"].append("File contains non-ASCII characters")
    
    except Exception as e:
        validation_results["is_valid"] = False
        validation_results["errors"].append(f"Validation error: {str(e)}")
    
    return validation_results

# COMMAND ----------

# MAGIC %md
# MAGIC ## Main Processing Logic

# COMMAND ----------

# Get list of X12 files to process
try:
    file_list = dbutils.fs.ls(SOURCE_PATH)
    x12_files = [f for f in file_list if f.name.endswith('.x12') or f.name.endswith('.edi') or f.name.endswith('.txt')]
    
    print(f"Found {len(x12_files)} X12 files to process")
    
    if not x12_files:
        print("No X12 files found for processing")
        dbutils.notebook.exit("No files to process")
    
except Exception as e:
    print(f"Error listing files: {str(e)}")
    dbutils.notebook.exit(f"Error: {str(e)}")

# COMMAND ----------

# Process each file
processed_files = []
failed_files = []

for file_info in x12_files:
    try:
        file_path = file_info.path
        file_name = file_info.name
        
        print(f"Processing file: {file_name}")
        
        # Read file content
        file_content = dbutils.fs.head(file_path, max_bytes=10*1024*1024)  # Read up to 10MB
        
        # Validate file
        validation_results = validate_x12_file(file_content)
        
        # Extract metadata
        metadata = extract_x12_metadata(file_content)
        
        # Create processing record
        processing_record = {
            "batch_id": BATCH_ID,
            "file_name": file_name,
            "file_path": file_path,
            "file_size": file_info.size,
            "processing_timestamp": datetime.now().isoformat(),
            "validation_results": validation_results,
            "metadata": metadata,
            "status": "processed" if validation_results["is_valid"] else "failed"
        }
        
        # Store the file in Bronze layer with metadata
        if validation_results["is_valid"]:
            # Create target path with partitioning
            target_file_path = f"{TARGET_PATH}year={datetime.now().year}/month={datetime.now().month:02d}/day={datetime.now().day:02d}/{BATCH_ID}_{file_name}"
            
            # Copy file to target location
            dbutils.fs.cp(file_path, target_file_path)
            
            # Store metadata as JSON
            metadata_path = f"{target_file_path}.metadata.json"
            dbutils.fs.put(metadata_path, json.dumps(processing_record, indent=2), overwrite=True)
            
            processed_files.append(processing_record)
            print(f"✓ Successfully processed: {file_name}")
        else:
            failed_files.append(processing_record)
            print(f"✗ Failed to process: {file_name} - {validation_results['errors']}")
    
    except Exception as e:
        error_record = {
            "batch_id": BATCH_ID,
            "file_name": file_name,
            "file_path": file_path,
            "processing_timestamp": datetime.now().isoformat(),
            "status": "error",
            "error_message": str(e)
        }
        failed_files.append(error_record)
        print(f"✗ Error processing {file_name}: {str(e)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Processing Summary

# COMMAND ----------

# Create summary
summary = {
    "batch_id": BATCH_ID,
    "processing_timestamp": datetime.now().isoformat(),
    "total_files": len(x12_files),
    "processed_files": len(processed_files),
    "failed_files": len(failed_files),
    "success_rate": len(processed_files) / len(x12_files) * 100 if x12_files else 0
}

# Store summary
summary_path = f"{TARGET_PATH}_batch_summaries/{BATCH_ID}_summary.json"
dbutils.fs.put(summary_path, json.dumps(summary, indent=2), overwrite=True)

# Display summary
print("=" * 50)
print("PROCESSING SUMMARY")
print("=" * 50)
print(f"Batch ID: {BATCH_ID}")
print(f"Total files: {summary['total_files']}")
print(f"Successfully processed: {summary['processed_files']}")
print(f"Failed: {summary['failed_files']}")
print(f"Success rate: {summary['success_rate']:.1f}%")

# Return summary for pipeline
dbutils.notebook.exit(json.dumps(summary))

# COMMAND ----------