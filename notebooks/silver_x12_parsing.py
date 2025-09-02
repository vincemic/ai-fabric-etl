# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer - X12 Data Parsing and Cleansing
# MAGIC 
# MAGIC This notebook processes raw X12 files from the Bronze layer, parses them into structured data,
# MAGIC and stores the clean, validated data in the Silver layer.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup and Configuration

# COMMAND ----------

import os
import json
import re
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
dbutils.widgets.text("bronze_container", "bronze-x12-raw", "Bronze Container")
dbutils.widgets.text("silver_container", "silver-x12-parsed", "Silver Container")
dbutils.widgets.text("batch_id", "", "Batch ID")
dbutils.widgets.text("processing_date", "", "Processing Date (YYYY-MM-DD)")

# Get parameter values
STORAGE_ACCOUNT_NAME = dbutils.widgets.get("storage_account_name")
BRONZE_CONTAINER = dbutils.widgets.get("bronze_container")
SILVER_CONTAINER = dbutils.widgets.get("silver_container")
BATCH_ID = dbutils.widgets.get("batch_id")
PROCESSING_DATE = dbutils.widgets.get("processing_date") or datetime.now().strftime("%Y-%m-%d")

# Storage paths
BRONZE_PATH = f"abfss://{BRONZE_CONTAINER}@{STORAGE_ACCOUNT_NAME}.dfs.core.windows.net/processed/"
SILVER_PATH = f"abfss://{SILVER_CONTAINER}@{STORAGE_ACCOUNT_NAME}.dfs.core.windows.net/"

print(f"Bronze Path: {BRONZE_PATH}")
print(f"Silver Path: {SILVER_PATH}")
print(f"Processing Date: {PROCESSING_DATE}")
print(f"Batch ID: {BATCH_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## X12 Parsing Functions

# COMMAND ----------

def parse_x12_segments(file_content, element_separator='*', segment_terminator='~'):
    """
    Parse X12 file content into individual segments.
    
    Args:
        file_content (str): Raw X12 file content
        element_separator (str): Element separator character
        segment_terminator (str): Segment terminator character
        
    Returns:
        list: List of parsed segments
    """
    segments = []
    
    try:
        # Split by segment terminator
        raw_segments = file_content.split(segment_terminator)
        
        for raw_segment in raw_segments:
            if raw_segment.strip():
                # Split by element separator
                elements = raw_segment.strip().split(element_separator)
                if elements and elements[0]:  # Valid segment
                    segment = {
                        "segment_id": elements[0],
                        "elements": elements[1:] if len(elements) > 1 else [],
                        "raw_segment": raw_segment.strip()
                    }
                    segments.append(segment)
    
    except Exception as e:
        logger.error(f"Error parsing X12 segments: {str(e)}")
        raise
    
    return segments

# COMMAND ----------

def parse_isa_segment(elements):
    """Parse ISA (Interchange Control Header) segment."""
    if len(elements) < 16:
        raise ValueError("ISA segment must have at least 16 elements")
    
    return {
        "authorization_info_qualifier": elements[0],
        "authorization_information": elements[1],
        "security_info_qualifier": elements[2],
        "security_information": elements[3],
        "sender_id_qualifier": elements[4],
        "interchange_sender_id": elements[5],
        "receiver_id_qualifier": elements[6],
        "interchange_receiver_id": elements[7],
        "interchange_date": elements[8],
        "interchange_time": elements[9],
        "repetition_separator": elements[10],
        "interchange_control_version": elements[11],
        "interchange_control_number": elements[12],
        "acknowledgment_requested": elements[13],
        "usage_indicator": elements[14],
        "component_element_separator": elements[15]
    }

def parse_gs_segment(elements):
    """Parse GS (Functional Group Header) segment."""
    if len(elements) < 8:
        raise ValueError("GS segment must have at least 8 elements")
    
    return {
        "functional_identifier_code": elements[0],
        "application_senders_code": elements[1],
        "application_receivers_code": elements[2],
        "date": elements[3],
        "time": elements[4],
        "group_control_number": elements[5],
        "responsible_agency_code": elements[6],
        "version_release_industry_id": elements[7]
    }

def parse_st_segment(elements):
    """Parse ST (Transaction Set Header) segment."""
    if len(elements) < 2:
        raise ValueError("ST segment must have at least 2 elements")
    
    return {
        "transaction_set_identifier_code": elements[0],
        "transaction_set_control_number": elements[1],
        "implementation_convention_reference": elements[2] if len(elements) > 2 else None
    }

# COMMAND ----------

def parse_transaction_set(segments, transaction_type):
    """
    Parse specific transaction set based on type.
    
    Args:
        segments (list): List of segments in the transaction set
        transaction_type (str): Transaction set identifier (e.g., '837', '835', '834', '270', '271', '276', '277')
        
    Returns:
        dict: Parsed transaction data
    """
    transaction_data = {
        "transaction_type": transaction_type,
        "segments": segments,
        "parsed_data": {}
    }
    
    try:
        if transaction_type == "837":  # Health Care Claim
            transaction_data["parsed_data"] = parse_837_healthcare_claim(segments)
        elif transaction_type == "835":  # Health Care Claim Payment/Advice
            transaction_data["parsed_data"] = parse_835_payment_advice(segments)
        elif transaction_type == "834":  # Benefit Enrollment and Maintenance
            transaction_data["parsed_data"] = parse_834_enrollment(segments)
        elif transaction_type == "270":  # Health Care Eligibility Benefit Inquiry
            transaction_data["parsed_data"] = parse_270_eligibility_inquiry(segments)
        elif transaction_type == "271":  # Health Care Eligibility Benefit Response
            transaction_data["parsed_data"] = parse_271_eligibility_response(segments)
        elif transaction_type == "276":  # Health Care Claim Status Request
            transaction_data["parsed_data"] = parse_276_claim_status_request(segments)
        elif transaction_type == "277":  # Health Care Claim Status Response
            transaction_data["parsed_data"] = parse_277_claim_status_response(segments)
        elif transaction_type == "278":  # Health Care Services Review Request (Preauthorization Request)
            transaction_data["parsed_data"] = parse_278_preauth_request(segments)
        elif transaction_type == "279":  # Health Care Services Review Response (Preauthorization Response)
            transaction_data["parsed_data"] = parse_279_preauth_response(segments)
        else:
            # Generic parsing for unknown transaction types
            transaction_data["parsed_data"] = parse_generic_transaction(segments)
    
    except Exception as e:
        logger.error(f"Error parsing transaction set {transaction_type}: {str(e)}")
        transaction_data["parsing_error"] = str(e)
    
    return transaction_data

def parse_837_healthcare_claim(segments):
    """Parse 837 (Health Care Claim) transaction."""
    claim_data = {
        "header": {},
        "provider": {},
        "subscriber": {},
        "patient": {},
        "claim": {},
        "service_lines": []
    }
    
    current_service_line = None
    
    for segment in segments:
        segment_id = segment["segment_id"]
        elements = segment["elements"]
        
        if segment_id == "BHT":  # Beginning of Hierarchical Transaction
            claim_data["header"] = {
                "hierarchical_structure_code": elements[0] if elements else None,
                "transaction_set_purpose_code": elements[1] if len(elements) > 1 else None,
                "reference_identification": elements[2] if len(elements) > 2 else None,
                "date": elements[3] if len(elements) > 3 else None,
                "time": elements[4] if len(elements) > 4 else None,
                "transaction_type_code": elements[5] if len(elements) > 5 else None
            }
        elif segment_id == "CLM":  # Claim Information
            claim_data["claim"] = {
                "claim_submitter_identifier": elements[0] if elements else None,
                "monetary_amount": float(elements[1]) if len(elements) > 1 and elements[1] else 0.0,
                "claim_filing_indicator_code": elements[2] if len(elements) > 2 else None,
                "health_care_service_location": elements[4] if len(elements) > 4 else None,
                "provider_signature_indicator": elements[5] if len(elements) > 5 else None,
                "medicare_assignment_code": elements[6] if len(elements) > 6 else None,
                "assignment_acceptance": elements[7] if len(elements) > 7 else None,
                "release_of_information_code": elements[8] if len(elements) > 8 else None
            }
        elif segment_id == "NM1":  # Individual or Organizational Name
            entity_type = elements[0] if elements else None
            name_data = {
                "entity_identifier_code": entity_type,
                "entity_type_qualifier": elements[1] if len(elements) > 1 else None,
                "last_name_or_org_name": elements[2] if len(elements) > 2 else None,
                "first_name": elements[3] if len(elements) > 3 else None,
                "middle_name": elements[4] if len(elements) > 4 else None,
                "identification_code_qualifier": elements[7] if len(elements) > 7 else None,
                "identification_code": elements[8] if len(elements) > 8 else None
            }
            
            if entity_type == "85":  # Billing Provider
                claim_data["provider"] = name_data
            elif entity_type == "IL":  # Insured or Subscriber
                claim_data["subscriber"] = name_data
            elif entity_type == "QC":  # Patient
                claim_data["patient"] = name_data
        
        elif segment_id == "SV1":  # Professional Service
            if current_service_line:
                claim_data["service_lines"].append(current_service_line)
            
            current_service_line = {
                "product_service_id": elements[0] if elements else None,
                "monetary_amount": float(elements[1]) if len(elements) > 1 and elements[1] else 0.0,
                "unit_basis_measurement_code": elements[2] if len(elements) > 2 else None,
                "service_unit_count": float(elements[3]) if len(elements) > 3 and elements[3] else 0.0,
                "place_of_service_code": elements[4] if len(elements) > 4 else None,
                "service_type_code": elements[5] if len(elements) > 5 else None
            }
        
        elif segment_id == "DTP":  # Date or Time or Period
            if current_service_line:
                current_service_line["service_date"] = {
                    "date_time_qualifier": elements[0] if elements else None,
                    "date_time_format_qualifier": elements[1] if len(elements) > 1 else None,
                    "date_time_period": elements[2] if len(elements) > 2 else None
                }
    
    # Add the last service line if it exists
    if current_service_line:
        claim_data["service_lines"].append(current_service_line)
    
    return claim_data

def parse_835_payment_advice(segments):
    """Parse 835 (Health Care Claim Payment/Advice) transaction."""
    payment_data = {
        "header": {},
        "payer": {},
        "payee": {},
        "claims": []
    }
    
    current_claim = None
    current_service = None
    
    for segment in segments:
        segment_id = segment["segment_id"]
        elements = segment["elements"]
        
        if segment_id == "BPR":  # Beginning Segment for Payment
            payment_data["header"] = {
                "transaction_handling_code": elements[0] if elements else None,
                "monetary_amount": float(elements[1]) if len(elements) > 1 and elements[1] else 0.0,
                "credit_debit_flag_code": elements[2] if len(elements) > 2 else None,
                "payment_method_code": elements[3] if len(elements) > 3 else None,
                "payment_format_code": elements[4] if len(elements) > 4 else None,
                "originating_company_identifier": elements[9] if len(elements) > 9 else None,
                "payment_date": elements[15] if len(elements) > 15 else None
            }
        elif segment_id == "TRN":  # Trace
            payment_data["trace"] = {
                "trace_type_code": elements[0] if elements else None,
                "reference_identification": elements[1] if len(elements) > 1 else None,
                "originating_company_identifier": elements[2] if len(elements) > 2 else None
            }
        elif segment_id == "N1":  # Name
            entity_type = elements[0] if elements else None
            name_data = {
                "entity_identifier_code": entity_type,
                "name": elements[1] if len(elements) > 1 else None,
                "identification_code_qualifier": elements[2] if len(elements) > 2 else None,
                "identification_code": elements[3] if len(elements) > 3 else None
            }
            
            if entity_type == "PR":  # Payer
                payment_data["payer"] = name_data
            elif entity_type == "PE":  # Payee
                payment_data["payee"] = name_data
        
        elif segment_id == "CLP":  # Claim Level Payment Information
            if current_claim:
                payment_data["claims"].append(current_claim)
            
            current_claim = {
                "claim_submitter_identifier": elements[0] if elements else None,
                "claim_status_code": elements[1] if len(elements) > 1 else None,
                "claim_charge_amount": float(elements[2]) if len(elements) > 2 and elements[2] else 0.0,
                "claim_payment_amount": float(elements[3]) if len(elements) > 3 and elements[3] else 0.0,
                "patient_responsibility_amount": float(elements[4]) if len(elements) > 4 and elements[4] else 0.0,
                "claim_filing_indicator_code": elements[5] if len(elements) > 5 else None,
                "payer_claim_control_number": elements[6] if len(elements) > 6 else None,
                "facility_code_value": elements[7] if len(elements) > 7 else None,
                "services": []
            }
        
        elif segment_id == "SVC" and current_claim:  # Service Payment Information
            if current_service:
                current_claim["services"].append(current_service)
            
            current_service = {
                "product_service_id": elements[0] if elements else None,
                "charge_amount": float(elements[1]) if len(elements) > 1 and elements[1] else 0.0,
                "payment_amount": float(elements[2]) if len(elements) > 2 and elements[2] else 0.0,
                "revenue_code": elements[3] if len(elements) > 3 else None,
                "quantity": float(elements[4]) if len(elements) > 4 and elements[4] else 0.0
            }
    
    # Add the last service and claim if they exist
    if current_service and current_claim:
        current_claim["services"].append(current_service)
    if current_claim:
        payment_data["claims"].append(current_claim)
    
    return payment_data

def parse_834_enrollment(segments):
    """Parse 834 (Benefit Enrollment and Maintenance) transaction."""
    enrollment_data = {
        "header": {},
        "sponsor": {},
        "members": []
    }
    
    current_member = None
    
    for segment in segments:
        segment_id = segment["segment_id"]
        elements = segment["elements"]
        
        if segment_id == "BGN":  # Beginning Segment
            enrollment_data["header"] = {
                "transaction_set_purpose_code": elements[0] if elements else None,
                "reference_identification": elements[1] if len(elements) > 1 else None,
                "date": elements[2] if len(elements) > 2 else None,
                "time": elements[3] if len(elements) > 3 else None,
                "time_zone_code": elements[4] if len(elements) > 4 else None,
                "transaction_type_code": elements[6] if len(elements) > 6 else None,
                "action_code": elements[7] if len(elements) > 7 else None
            }
        elif segment_id == "N1":  # Name
            entity_type = elements[0] if elements else None
            if entity_type == "P5":  # Plan Sponsor
                enrollment_data["sponsor"] = {
                    "entity_identifier_code": entity_type,
                    "name": elements[1] if len(elements) > 1 else None,
                    "identification_code_qualifier": elements[2] if len(elements) > 2 else None,
                    "identification_code": elements[3] if len(elements) > 3 else None
                }
        elif segment_id == "INS":  # Insured Benefit
            if current_member:
                enrollment_data["members"].append(current_member)
            
            current_member = {
                "subscriber_indicator": elements[0] if elements else None,
                "individual_relationship_code": elements[1] if len(elements) > 1 else None,
                "maintenance_type_code": elements[2] if len(elements) > 2 else None,
                "maintenance_reason_code": elements[3] if len(elements) > 3 else None,
                "benefit_status_code": elements[4] if len(elements) > 4 else None,
                "medicare_plan_code": elements[5] if len(elements) > 5 else None,
                "employment_status_code": elements[7] if len(elements) > 7 else None,
                "student_status_code": elements[8] if len(elements) > 8 else None,
                "coverages": []
            }
        elif segment_id == "NM1" and current_member:  # Individual Name
            current_member["name"] = {
                "entity_identifier_code": elements[0] if elements else None,
                "entity_type_qualifier": elements[1] if len(elements) > 1 else None,
                "last_name": elements[2] if len(elements) > 2 else None,
                "first_name": elements[3] if len(elements) > 3 else None,
                "middle_name": elements[4] if len(elements) > 4 else None,
                "identification_code_qualifier": elements[7] if len(elements) > 7 else None,
                "identification_code": elements[8] if len(elements) > 8 else None
            }
        elif segment_id == "HD" and current_member:  # Health Coverage
            coverage = {
                "maintenance_type_code": elements[0] if elements else None,
                "maintenance_reason_code": elements[1] if len(elements) > 1 else None,
                "insurance_line_code": elements[2] if len(elements) > 2 else None,
                "plan_coverage_description": elements[3] if len(elements) > 3 else None,
                "coverage_level_code": elements[4] if len(elements) > 4 else None
            }
            current_member["coverages"].append(coverage)
    
    # Add the last member if it exists
    if current_member:
        enrollment_data["members"].append(current_member)
    
    return enrollment_data

def parse_270_eligibility_inquiry(segments):
    """Parse 270 (Health Care Eligibility Benefit Inquiry) transaction."""
    inquiry_data = {
        "header": {},
        "provider": {},
        "subscriber": {},
        "patient": {},
        "inquiries": []
    }
    
    for segment in segments:
        segment_id = segment["segment_id"]
        elements = segment["elements"]
        
        if segment_id == "BHT":  # Beginning of Hierarchical Transaction
            inquiry_data["header"] = {
                "hierarchical_structure_code": elements[0] if elements else None,
                "transaction_set_purpose_code": elements[1] if len(elements) > 1 else None,
                "reference_identification": elements[2] if len(elements) > 2 else None,
                "date": elements[3] if len(elements) > 3 else None,
                "time": elements[4] if len(elements) > 4 else None
            }
        elif segment_id == "NM1":  # Individual or Organizational Name
            entity_type = elements[0] if elements else None
            name_data = {
                "entity_identifier_code": entity_type,
                "entity_type_qualifier": elements[1] if len(elements) > 1 else None,
                "last_name_or_org_name": elements[2] if len(elements) > 2 else None,
                "first_name": elements[3] if len(elements) > 3 else None,
                "identification_code_qualifier": elements[7] if len(elements) > 7 else None,
                "identification_code": elements[8] if len(elements) > 8 else None
            }
            
            if entity_type == "1P":  # Provider
                inquiry_data["provider"] = name_data
            elif entity_type == "IL":  # Insured or Subscriber
                inquiry_data["subscriber"] = name_data
            elif entity_type == "QC":  # Patient
                inquiry_data["patient"] = name_data
        
        elif segment_id == "EQ":  # Eligibility or Benefit Inquiry
            inquiry = {
                "service_type_code": elements[0] if elements else None,
                "product_service_id_qualifier": elements[1] if len(elements) > 1 else None,
                "product_service_id": elements[2] if len(elements) > 2 else None,
                "coverage_level_code": elements[3] if len(elements) > 3 else None,
                "insurance_type_code": elements[4] if len(elements) > 4 else None
            }
            inquiry_data["inquiries"].append(inquiry)
    
    return inquiry_data

def parse_271_eligibility_response(segments):
    """Parse 271 (Health Care Eligibility Benefit Response) transaction."""
    response_data = {
        "header": {},
        "source": {},
        "receiver": {},
        "subscriber": {},
        "patient": {},
        "benefits": []
    }
    
    for segment in segments:
        segment_id = segment["segment_id"]
        elements = segment["elements"]
        
        if segment_id == "BHT":  # Beginning of Hierarchical Transaction
            response_data["header"] = {
                "hierarchical_structure_code": elements[0] if elements else None,
                "transaction_set_purpose_code": elements[1] if len(elements) > 1 else None,
                "reference_identification": elements[2] if len(elements) > 2 else None,
                "date": elements[3] if len(elements) > 3 else None,
                "time": elements[4] if len(elements) > 4 else None
            }
        elif segment_id == "NM1":  # Individual or Organizational Name
            entity_type = elements[0] if elements else None
            name_data = {
                "entity_identifier_code": entity_type,
                "entity_type_qualifier": elements[1] if len(elements) > 1 else None,
                "last_name_or_org_name": elements[2] if len(elements) > 2 else None,
                "first_name": elements[3] if len(elements) > 3 else None,
                "identification_code_qualifier": elements[7] if len(elements) > 7 else None,
                "identification_code": elements[8] if len(elements) > 8 else None
            }
            
            if entity_type == "PR":  # Payer
                response_data["source"] = name_data
            elif entity_type == "1P":  # Provider
                response_data["receiver"] = name_data
            elif entity_type == "IL":  # Insured or Subscriber
                response_data["subscriber"] = name_data
            elif entity_type == "QC":  # Patient
                response_data["patient"] = name_data
        
        elif segment_id == "EB":  # Eligibility or Benefit Information
            benefit = {
                "eligibility_benefit_info_code": elements[0] if elements else None,
                "coverage_level_code": elements[1] if len(elements) > 1 else None,
                "service_type_code": elements[2] if len(elements) > 2 else None,
                "insurance_type_code": elements[3] if len(elements) > 3 else None,
                "plan_coverage_description": elements[4] if len(elements) > 4 else None,
                "time_period_qualifier": elements[5] if len(elements) > 5 else None,
                "monetary_amount": float(elements[6]) if len(elements) > 6 and elements[6] else 0.0,
                "percentage": float(elements[7]) if len(elements) > 7 and elements[7] else 0.0
            }
            response_data["benefits"].append(benefit)
    
    return response_data

def parse_276_claim_status_request(segments):
    """Parse 276 (Health Care Claim Status Request) transaction."""
    request_data = {
        "header": {},
        "provider": {},
        "subscriber": {},
        "patient": {},
        "trace": {}
    }
    
    for segment in segments:
        segment_id = segment["segment_id"]
        elements = segment["elements"]
        
        if segment_id == "BHT":  # Beginning of Hierarchical Transaction
            request_data["header"] = {
                "hierarchical_structure_code": elements[0] if elements else None,
                "transaction_set_purpose_code": elements[1] if len(elements) > 1 else None,
                "reference_identification": elements[2] if len(elements) > 2 else None,
                "date": elements[3] if len(elements) > 3 else None,
                "time": elements[4] if len(elements) > 4 else None
            }
        elif segment_id == "TRN":  # Trace
            request_data["trace"] = {
                "trace_type_code": elements[0] if elements else None,
                "reference_identification": elements[1] if len(elements) > 1 else None,
                "originating_company_identifier": elements[2] if len(elements) > 2 else None
            }
        elif segment_id == "NM1":  # Individual or Organizational Name
            entity_type = elements[0] if elements else None
            name_data = {
                "entity_identifier_code": entity_type,
                "entity_type_qualifier": elements[1] if len(elements) > 1 else None,
                "last_name_or_org_name": elements[2] if len(elements) > 2 else None,
                "first_name": elements[3] if len(elements) > 3 else None,
                "identification_code_qualifier": elements[7] if len(elements) > 7 else None,
                "identification_code": elements[8] if len(elements) > 8 else None
            }
            
            if entity_type == "1P":  # Provider
                request_data["provider"] = name_data
            elif entity_type == "IL":  # Insured or Subscriber
                request_data["subscriber"] = name_data
            elif entity_type == "QC":  # Patient
                request_data["patient"] = name_data
    
    return request_data

def parse_277_claim_status_response(segments):
    """Parse 277 (Health Care Claim Status Response) transaction."""
    response_data = {
        "header": {},
        "source": {},
        "receiver": {},
        "claim_status": []
    }
    
    current_status = None
    
    for segment in segments:
        segment_id = segment["segment_id"]
        elements = segment["elements"]
        
        if segment_id == "BHT":  # Beginning of Hierarchical Transaction
            response_data["header"] = {
                "hierarchical_structure_code": elements[0] if elements else None,
                "transaction_set_purpose_code": elements[1] if len(elements) > 1 else None,
                "reference_identification": elements[2] if len(elements) > 2 else None,
                "date": elements[3] if len(elements) > 3 else None,
                "time": elements[4] if len(elements) > 4 else None
            }
        elif segment_id == "NM1":  # Individual or Organizational Name
            entity_type = elements[0] if elements else None
            name_data = {
                "entity_identifier_code": entity_type,
                "entity_type_qualifier": elements[1] if len(elements) > 1 else None,
                "last_name_or_org_name": elements[2] if len(elements) > 2 else None,
                "first_name": elements[3] if len(elements) > 3 else None,
                "identification_code_qualifier": elements[7] if len(elements) > 7 else None,
                "identification_code": elements[8] if len(elements) > 8 else None
            }
            
            if entity_type == "PR":  # Payer
                response_data["source"] = name_data
            elif entity_type == "1P":  # Provider
                response_data["receiver"] = name_data
        
        elif segment_id == "STC":  # Status Information
            if current_status:
                response_data["claim_status"].append(current_status)
            
            current_status = {
                "health_care_claim_status_code": elements[0] if elements else None,
                "status_date": elements[1] if len(elements) > 1 else None,
                "action_code": elements[2] if len(elements) > 2 else None,
                "total_claim_charge_amount": float(elements[3]) if len(elements) > 3 and elements[3] else 0.0,
                "claim_payment_amount": float(elements[4]) if len(elements) > 4 and elements[4] else 0.0,
                "category_of_service": elements[9] if len(elements) > 9 else None,
                "status_effective_date": elements[10] if len(elements) > 10 else None
            }
    
    # Add the last status if it exists
    if current_status:
        response_data["claim_status"].append(current_status)
    
    return response_data

def parse_278_preauth_request(segments):
    """Parse 278 (Health Care Services Review Request - Preauthorization Request) transaction."""
    request_data = {
        "header": {},
        "submitter": {},
        "receiver": {},
        "patient": {},
        "service_provider": {},
        "requesting_provider": {},
        "review_information": {},
        "services": [],
        "service_dates": []
    }
    
    current_service = None
    current_date = None
    
    for segment in segments:
        segment_id = segment["segment_id"]
        elements = segment["elements"]
        
        if segment_id == "BHT":  # Beginning of Hierarchical Transaction
            request_data["header"] = {
                "hierarchical_structure_code": elements[0] if elements else None,
                "transaction_set_purpose_code": elements[1] if len(elements) > 1 else None,
                "reference_identification": elements[2] if len(elements) > 2 else None,
                "date": elements[3] if len(elements) > 3 else None,
                "time": elements[4] if len(elements) > 4 else None
            }
        elif segment_id == "HL":  # Hierarchical Level
            # Store hierarchical level information
            level_code = elements[2] if len(elements) > 2 else None
            if level_code == "20":  # Information Source (Submitter)
                request_data["submitter"]["hierarchical_id"] = elements[0] if elements else None
            elif level_code == "21":  # Information Receiver
                request_data["receiver"]["hierarchical_id"] = elements[0] if elements else None
            elif level_code == "22":  # Patient
                request_data["patient"]["hierarchical_id"] = elements[0] if elements else None
            elif level_code == "23":  # Service Provider
                request_data["service_provider"]["hierarchical_id"] = elements[0] if elements else None
                
        elif segment_id == "NM1":  # Individual or Organizational Name
            entity_type = elements[0] if elements else None
            name_data = {
                "entity_identifier_code": entity_type,
                "entity_type_qualifier": elements[1] if len(elements) > 1 else None,
                "last_name_or_org_name": elements[2] if len(elements) > 2 else None,
                "first_name": elements[3] if len(elements) > 3 else None,
                "middle_name": elements[4] if len(elements) > 4 else None,
                "identification_code_qualifier": elements[7] if len(elements) > 7 else None,
                "identification_code": elements[8] if len(elements) > 8 else None
            }
            
            if entity_type == "X3":  # Dependent
                request_data["patient"].update(name_data)
            elif entity_type == "1P":  # Provider
                request_data["service_provider"].update(name_data)
            elif entity_type == "FA":  # Facility
                request_data["service_provider"].update(name_data)
            elif entity_type == "PR":  # Payer
                request_data["receiver"].update(name_data)
                
        elif segment_id == "UM":  # Health Care Services Review Information
            request_data["review_information"] = {
                "request_category_code": elements[0] if elements else None,
                "certification_type_code": elements[1] if len(elements) > 1 else None,
                "service_type_code": elements[2] if len(elements) > 2 else None,
                "shortage_area_code": elements[3] if len(elements) > 3 else None,
                "review_identification_number": elements[4] if len(elements) > 4 else None
            }
            
        elif segment_id == "SV1":  # Professional Service
            if current_service:
                request_data["services"].append(current_service)
            
            # Parse composite product/service ID
            product_service_info = elements[0].split(":") if elements and elements[0] else ["", ""]
            
            current_service = {
                "product_service_id_qualifier": product_service_info[0] if len(product_service_info) > 0 else None,
                "product_service_id": product_service_info[1] if len(product_service_info) > 1 else None,
                "monetary_amount": float(elements[1]) if len(elements) > 1 and elements[1] else 0.0,
                "unit_basis_measurement_code": elements[2] if len(elements) > 2 else None,
                "service_unit_count": float(elements[3]) if len(elements) > 3 and elements[3] else 0.0,
                "place_of_service_code": elements[4] if len(elements) > 4 else None,
                "diagnosis_code_pointer": elements[6] if len(elements) > 6 else None
            }
            
        elif segment_id == "DTP":  # Date or Time or Period
            if current_date:
                request_data["service_dates"].append(current_date)
            
            current_date = {
                "date_time_qualifier": elements[0] if elements else None,
                "date_time_format_qualifier": elements[1] if len(elements) > 1 else None,
                "date_time_period": elements[2] if len(elements) > 2 else None
            }
    
    # Add the last service and date if they exist
    if current_service:
        request_data["services"].append(current_service)
    if current_date:
        request_data["service_dates"].append(current_date)
    
    return request_data

def parse_279_preauth_response(segments):
    """Parse 279 (Health Care Services Review Response - Preauthorization Response) transaction."""
    response_data = {
        "header": {},
        "source": {},
        "receiver": {},
        "patient": {},
        "service_provider": {},
        "review_results": [],
        "messages": [],
        "authorization_dates": []
    }
    
    current_review = None
    current_message = None
    current_date = None
    
    for segment in segments:
        segment_id = segment["segment_id"]
        elements = segment["elements"]
        
        if segment_id == "BHT":  # Beginning of Hierarchical Transaction
            response_data["header"] = {
                "hierarchical_structure_code": elements[0] if elements else None,
                "transaction_set_purpose_code": elements[1] if len(elements) > 1 else None,
                "reference_identification": elements[2] if len(elements) > 2 else None,
                "date": elements[3] if len(elements) > 3 else None,
                "time": elements[4] if len(elements) > 4 else None
            }
            
        elif segment_id == "HL":  # Hierarchical Level
            # Store hierarchical level information
            level_code = elements[2] if len(elements) > 2 else None
            if level_code == "20":  # Information Source
                response_data["source"]["hierarchical_id"] = elements[0] if elements else None
            elif level_code == "21":  # Information Receiver
                response_data["receiver"]["hierarchical_id"] = elements[0] if elements else None
            elif level_code == "22":  # Patient
                response_data["patient"]["hierarchical_id"] = elements[0] if elements else None
            elif level_code == "23":  # Service Provider
                response_data["service_provider"]["hierarchical_id"] = elements[0] if elements else None
                
        elif segment_id == "NM1":  # Individual or Organizational Name
            entity_type = elements[0] if elements else None
            name_data = {
                "entity_identifier_code": entity_type,
                "entity_type_qualifier": elements[1] if len(elements) > 1 else None,
                "last_name_or_org_name": elements[2] if len(elements) > 2 else None,
                "first_name": elements[3] if len(elements) > 3 else None,
                "middle_name": elements[4] if len(elements) > 4 else None,
                "identification_code_qualifier": elements[7] if len(elements) > 7 else None,
                "identification_code": elements[8] if len(elements) > 8 else None
            }
            
            if entity_type == "X3":  # Dependent (Patient)
                response_data["patient"].update(name_data)
            elif entity_type == "1P":  # Provider
                response_data["service_provider"].update(name_data)
            elif entity_type == "PR":  # Payer
                response_data["source"].update(name_data)
                
        elif segment_id == "HCR":  # Health Care Services Review
            if current_review:
                response_data["review_results"].append(current_review)
            
            current_review = {
                "action_code": elements[0] if elements else None,
                "review_identification_number": elements[1] if len(elements) > 1 else None,
                "review_decision_reason_code": elements[2] if len(elements) > 2 else None,
                "second_review_decision_reason_code": elements[3] if len(elements) > 3 else None
            }
            
        elif segment_id == "MSG":  # Message Text
            if current_message:
                response_data["messages"].append(current_message)
            
            current_message = {
                "free_form_message_text": elements[0] if elements else None
            }
            
        elif segment_id == "PWK":  # Paperwork
            if current_review:
                current_review["paperwork"] = {
                    "report_type_code": elements[0] if elements else None,
                    "report_transmission_code": elements[1] if len(elements) > 1 else None,
                    "report_copies_needed": int(elements[2]) if len(elements) > 2 and elements[2] else None
                }
                
        elif segment_id == "DTP":  # Date or Time or Period
            if current_date:
                response_data["authorization_dates"].append(current_date)
            
            current_date = {
                "date_time_qualifier": elements[0] if elements else None,
                "date_time_format_qualifier": elements[1] if len(elements) > 1 else None,
                "date_time_period": elements[2] if len(elements) > 2 else None
            }
    
    # Add the last items if they exist
    if current_review:
        response_data["review_results"].append(current_review)
    if current_message:
        response_data["messages"].append(current_message)
    if current_date:
        response_data["authorization_dates"].append(current_date)
    
    return response_data

def parse_generic_transaction(segments):
    """Generic parser for unknown transaction types."""
    return {
        "segments_parsed": len(segments),
        "segment_types": list(set([s["segment_id"] for s in segments])),
        "raw_segments": segments
    }
    """Parse 850 (Purchase Order) transaction."""
    po_data = {
        "header": {},
        "line_items": [],
        "summary": {}
    }
    
    current_line_item = None
    
    for segment in segments:
        segment_id = segment["segment_id"]
        elements = segment["elements"]
        
        if segment_id == "BEG":  # Beginning Segment for Purchase Order
            po_data["header"] = {
                "transaction_set_purpose_code": elements[0] if elements else None,
                "purchase_order_type_code": elements[1] if len(elements) > 1 else None,
                "purchase_order_number": elements[2] if len(elements) > 2 else None,
                "release_number": elements[3] if len(elements) > 3 else None,
                "date": elements[4] if len(elements) > 4 else None
            }
        elif segment_id == "PO1":  # Baseline Item Data
            if current_line_item:
                po_data["line_items"].append(current_line_item)
            
            current_line_item = {
                "line_item_id": elements[0] if elements else None,
                "quantity_ordered": elements[1] if len(elements) > 1 else None,
                "unit_of_measure": elements[2] if len(elements) > 2 else None,
                "unit_price": elements[3] if len(elements) > 3 else None,
                "product_id": elements[6] if len(elements) > 6 else None,
                "product_id_qualifier": elements[5] if len(elements) > 5 else None
            }
        elif segment_id == "CTT":  # Transaction Totals
            po_data["summary"] = {
                "number_of_line_items": elements[0] if elements else None,
                "hash_total": elements[1] if len(elements) > 1 else None
            }
    
    # Add the last line item
    if current_line_item:
        po_data["line_items"].append(current_line_item)
    
    return po_data

def parse_810_invoice(segments):
    """Parse 810 (Invoice) transaction."""
    invoice_data = {
        "header": {},
        "line_items": [],
        "summary": {}
    }
    
    current_line_item = None
    
    for segment in segments:
        segment_id = segment["segment_id"]
        elements = segment["elements"]
        
        if segment_id == "BIG":  # Beginning Segment for Invoice
            invoice_data["header"] = {
                "invoice_date": elements[0] if elements else None,
                "invoice_number": elements[1] if len(elements) > 1 else None,
                "purchase_order_date": elements[2] if len(elements) > 2 else None,
                "purchase_order_number": elements[3] if len(elements) > 3 else None
            }
        elif segment_id == "IT1":  # Baseline Item Data (Invoice)
            if current_line_item:
                invoice_data["line_items"].append(current_line_item)
            
            current_line_item = {
                "line_item_id": elements[0] if elements else None,
                "quantity_invoiced": elements[1] if len(elements) > 1 else None,
                "unit_of_measure": elements[2] if len(elements) > 2 else None,
                "unit_price": elements[3] if len(elements) > 3 else None,
                "product_id": elements[6] if len(elements) > 6 else None,
                "product_id_qualifier": elements[5] if len(elements) > 5 else None
            }
        elif segment_id == "TDS":  # Total Monetary Value Summary
            invoice_data["summary"] = {
                "total_invoice_amount": elements[0] if elements else None
            }
    
    # Add the last line item
    if current_line_item:
        invoice_data["line_items"].append(current_line_item)
    
    return invoice_data

def parse_856_ship_notice(segments):
    """Parse 856 (Advance Ship Notice) transaction."""
    asn_data = {
        "header": {},
        "shipment_details": {},
        "line_items": []
    }
    
    current_line_item = None
    
    for segment in segments:
        segment_id = segment["segment_id"]
        elements = segment["elements"]
        
        if segment_id == "BSN":  # Beginning Segment for Ship Notice
            asn_data["header"] = {
                "transaction_set_purpose_code": elements[0] if elements else None,
                "shipment_id": elements[1] if len(elements) > 1 else None,
                "date": elements[2] if len(elements) > 2 else None,
                "time": elements[3] if len(elements) > 3 else None
            }
        elif segment_id == "HL":  # Hierarchical Level
            # Process hierarchical levels for shipment structure
            pass
        elif segment_id == "LIN":  # Item Identification
            if current_line_item:
                asn_data["line_items"].append(current_line_item)
            
            current_line_item = {
                "line_item_id": elements[0] if elements else None,
                "product_id_qualifier": elements[1] if len(elements) > 1 else None,
                "product_id": elements[2] if len(elements) > 2 else None
            }
        elif segment_id == "SN1":  # Item Detail (Shipment)
            if current_line_item:
                current_line_item.update({
                    "quantity_shipped": elements[1] if len(elements) > 1 else None,
                    "unit_of_measure": elements[2] if len(elements) > 2 else None
                })
    
    # Add the last line item
    if current_line_item:
        asn_data["line_items"].append(current_line_item)
    
    return asn_data

def parse_generic_transaction(segments):
    """Generic parser for unknown transaction types."""
    return {
        "segments_parsed": len(segments),
        "segment_types": list(set([s["segment_id"] for s in segments])),
        "raw_segments": segments
    }

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Quality Functions

# COMMAND ----------

def validate_parsed_data(parsed_data, transaction_type):
    """
    Validate parsed transaction data for quality issues.
    
    Args:
        parsed_data (dict): Parsed transaction data
        transaction_type (str): Transaction set identifier
        
    Returns:
        dict: Validation results
    """
    validation_results = {
        "is_valid": True,
        "quality_score": 100,
        "issues": [],
        "warnings": []
    }
    
    try:
        if transaction_type == "837":  # Health Care Claim
            validation_results = validate_837_data(parsed_data, validation_results)
        elif transaction_type == "835":  # Health Care Payment/Advice
            validation_results = validate_835_data(parsed_data, validation_results)
        elif transaction_type == "834":  # Benefit Enrollment and Maintenance
            validation_results = validate_834_data(parsed_data, validation_results)
        elif transaction_type == "270":  # Health Care Eligibility Benefit Inquiry
            validation_results = validate_270_data(parsed_data, validation_results)
        elif transaction_type == "271":  # Health Care Eligibility Benefit Response
            validation_results = validate_271_data(parsed_data, validation_results)
        elif transaction_type == "276":  # Health Care Claim Status Request
            validation_results = validate_276_data(parsed_data, validation_results)
        elif transaction_type == "277":  # Health Care Claim Status Response
            validation_results = validate_277_data(parsed_data, validation_results)
        elif transaction_type == "278":  # Health Care Services Review Request (Preauthorization Request)
            validation_results = validate_278_data(parsed_data, validation_results)
        elif transaction_type == "279":  # Health Care Services Review Response (Preauthorization Response)
            validation_results = validate_279_data(parsed_data, validation_results)
        
        # Calculate final quality score
        issues_count = len(validation_results["issues"])
        warnings_count = len(validation_results["warnings"])
        validation_results["quality_score"] = max(0, 100 - (issues_count * 20) - (warnings_count * 5))
        
        if validation_results["quality_score"] < 50:
            validation_results["is_valid"] = False
    
    except Exception as e:
        validation_results["is_valid"] = False
        validation_results["issues"].append(f"Validation error: {str(e)}")
        validation_results["quality_score"] = 0
    
    return validation_results

def validate_837_data(parsed_data, validation_results):
    """Validate 837 (Health Care Claim) specific data."""
    header = parsed_data.get("header", {})
    claim = parsed_data.get("claim", {})
    provider = parsed_data.get("provider", {})
    subscriber = parsed_data.get("subscriber", {})
    service_lines = parsed_data.get("service_lines", [])
    
    # Required fields validation
    if not header.get("reference_identification"):
        validation_results["issues"].append("Missing claim reference identification")
    
    if not claim.get("claim_submitter_identifier"):
        validation_results["issues"].append("Missing claim submitter identifier")
    
    if not provider.get("last_name_or_org_name"):
        validation_results["issues"].append("Missing provider name")
    
    if not subscriber.get("last_name_or_org_name"):
        validation_results["issues"].append("Missing subscriber name")
    
    if not service_lines:
        validation_results["issues"].append("No service lines found")
    
    # Service line validation
    for i, service in enumerate(service_lines):
        if not service.get("product_service_id"):
            validation_results["warnings"].append(f"Service line {i+1}: Missing product/service ID")
        
        if not service.get("monetary_amount"):
            validation_results["warnings"].append(f"Service line {i+1}: Missing monetary amount")
    
    return validation_results

def validate_835_data(parsed_data, validation_results):
    """Validate 835 (Health Care Payment/Advice) specific data."""
    header = parsed_data.get("header", {})
    payer = parsed_data.get("payer", {})
    payee = parsed_data.get("payee", {})
    claims = parsed_data.get("claims", [])
    
    # Required fields validation
    if not header.get("monetary_amount"):
        validation_results["issues"].append("Missing payment amount")
    
    if not payer.get("name"):
        validation_results["issues"].append("Missing payer name")
    
    if not payee.get("name"):
        validation_results["issues"].append("Missing payee name")
    
    if not claims:
        validation_results["issues"].append("No claims found in payment advice")
    
    # Claim validation
    for i, claim in enumerate(claims):
        if not claim.get("claim_submitter_identifier"):
            validation_results["warnings"].append(f"Claim {i+1}: Missing claim identifier")
        
        if not claim.get("claim_status_code"):
            validation_results["warnings"].append(f"Claim {i+1}: Missing claim status")
    
    return validation_results

def validate_834_data(parsed_data, validation_results):
    """Validate 834 (Benefit Enrollment and Maintenance) specific data."""
    header = parsed_data.get("header", {})
    sponsor = parsed_data.get("sponsor", {})
    members = parsed_data.get("members", [])
    
    # Required fields validation
    if not header.get("reference_identification"):
        validation_results["issues"].append("Missing enrollment reference identification")
    
    if not sponsor.get("name"):
        validation_results["issues"].append("Missing plan sponsor name")
    
    if not members:
        validation_results["issues"].append("No members found in enrollment transaction")
    
    # Member validation
    for i, member in enumerate(members):
        if not member.get("subscriber_indicator"):
            validation_results["warnings"].append(f"Member {i+1}: Missing subscriber indicator")
        
        name = member.get("name", {})
        if not name.get("last_name"):
            validation_results["warnings"].append(f"Member {i+1}: Missing last name")
    
    return validation_results

def validate_270_data(parsed_data, validation_results):
    """Validate 270 (Health Care Eligibility Benefit Inquiry) specific data."""
    header = parsed_data.get("header", {})
    provider = parsed_data.get("provider", {})
    subscriber = parsed_data.get("subscriber", {})
    inquiries = parsed_data.get("inquiries", [])
    
    # Required fields validation
    if not header.get("reference_identification"):
        validation_results["issues"].append("Missing inquiry reference identification")
    
    if not provider.get("last_name_or_org_name"):
        validation_results["issues"].append("Missing provider name")
    
    if not subscriber.get("last_name_or_org_name"):
        validation_results["issues"].append("Missing subscriber name")
    
    if not inquiries:
        validation_results["warnings"].append("No eligibility inquiries found")
    
    return validation_results

def validate_271_data(parsed_data, validation_results):
    """Validate 271 (Health Care Eligibility Benefit Response) specific data."""
    header = parsed_data.get("header", {})
    source = parsed_data.get("source", {})
    subscriber = parsed_data.get("subscriber", {})
    benefits = parsed_data.get("benefits", [])
    
    # Required fields validation
    if not header.get("reference_identification"):
        validation_results["issues"].append("Missing response reference identification")
    
    if not source.get("last_name_or_org_name"):
        validation_results["issues"].append("Missing source/payer name")
    
    if not subscriber.get("last_name_or_org_name"):
        validation_results["issues"].append("Missing subscriber name")
    
    if not benefits:
        validation_results["warnings"].append("No benefit information found")
    
    return validation_results

def validate_276_data(parsed_data, validation_results):
    """Validate 276 (Health Care Claim Status Request) specific data."""
    header = parsed_data.get("header", {})
    provider = parsed_data.get("provider", {})
    trace = parsed_data.get("trace", {})
    
    # Required fields validation
    if not header.get("reference_identification"):
        validation_results["issues"].append("Missing status request reference identification")
    
    if not provider.get("last_name_or_org_name"):
        validation_results["issues"].append("Missing provider name")
    
    if not trace.get("reference_identification"):
        validation_results["issues"].append("Missing trace reference identification")
    
    return validation_results

def validate_277_data(parsed_data, validation_results):
    """Validate 277 (Health Care Claim Status Response) specific data."""
    header = parsed_data.get("header", {})
    source = parsed_data.get("source", {})
    claim_status = parsed_data.get("claim_status", [])
    
    # Required fields validation
    if not header.get("reference_identification"):
        validation_results["issues"].append("Missing status response reference identification")
    
    if not source.get("last_name_or_org_name"):
        validation_results["issues"].append("Missing source/payer name")
    
    if not claim_status:
        validation_results["warnings"].append("No claim status information found")
    
    return validation_results

def validate_278_data(parsed_data, validation_results):
    """Validate 278 (Health Care Services Review Request - Preauthorization Request) specific data."""
    header = parsed_data.get("header", {})
    patient = parsed_data.get("patient", {})
    service_provider = parsed_data.get("service_provider", {})
    review_information = parsed_data.get("review_information", {})
    services = parsed_data.get("services", [])
    
    # Required fields validation
    if not header.get("reference_identification"):
        validation_results["issues"].append("Missing preauthorization request reference identification")
    
    if not header.get("date"):
        validation_results["issues"].append("Missing request date")
    
    if not patient.get("last_name_or_org_name") and not patient.get("first_name"):
        validation_results["issues"].append("Missing patient name information")
    
    if not service_provider.get("last_name_or_org_name"):
        validation_results["issues"].append("Missing service provider name")
    
    if not review_information.get("request_category_code"):
        validation_results["issues"].append("Missing request category code")
    
    if not services:
        validation_results["warnings"].append("No services found in preauthorization request")
    
    # Validate services
    for i, service in enumerate(services):
        if not service.get("product_service_id"):
            validation_results["warnings"].append(f"Service {i+1}: Missing product/service ID")
        
        if service.get("monetary_amount", 0) <= 0:
            validation_results["warnings"].append(f"Service {i+1}: Missing or invalid monetary amount")
    
    return validation_results

def validate_279_data(parsed_data, validation_results):
    """Validate 279 (Health Care Services Review Response - Preauthorization Response) specific data."""
    header = parsed_data.get("header", {})
    source = parsed_data.get("source", {})
    patient = parsed_data.get("patient", {})
    review_results = parsed_data.get("review_results", [])
    
    # Required fields validation
    if not header.get("reference_identification"):
        validation_results["issues"].append("Missing preauthorization response reference identification")
    
    if not header.get("date"):
        validation_results["issues"].append("Missing response date")
    
    if not source.get("last_name_or_org_name"):
        validation_results["issues"].append("Missing source/payer name")
    
    if not patient.get("last_name_or_org_name") and not patient.get("first_name"):
        validation_results["issues"].append("Missing patient name information")
    
    if not review_results:
        validation_results["issues"].append("No review results found in preauthorization response")
    
    # Validate review results
    for i, review in enumerate(review_results):
        if not review.get("action_code"):
            validation_results["issues"].append(f"Review {i+1}: Missing action code")
        
        # Check for common action codes
        action_code = review.get("action_code")
        if action_code not in ["A1", "A2", "A3", "A4", "A6", "CT", "DJ", "PA", "PN"]:
            validation_results["warnings"].append(f"Review {i+1}: Unusual action code '{action_code}'")
    
    return validation_results

# COMMAND ----------

# MAGIC %md
# MAGIC ## Main Processing Logic

# COMMAND ----------

# Define schema for parsed X12 data
parsed_x12_schema = StructType([
    StructField("batch_id", StringType(), True),
    StructField("file_name", StringType(), True),
    StructField("processing_timestamp", TimestampType(), True),
    StructField("interchange_control_number", StringType(), True),
    StructField("functional_group_number", StringType(), True),
    StructField("transaction_set_control_number", StringType(), True),
    StructField("transaction_type", StringType(), True),
    StructField("sender_id", StringType(), True),
    StructField("receiver_id", StringType(), True),
    StructField("transaction_date", StringType(), True),
    StructField("parsed_data", StringType(), True),  # JSON string
    StructField("validation_results", StringType(), True),  # JSON string
    StructField("quality_score", IntegerType(), True),
    StructField("is_valid", BooleanType(), True),
    StructField("processing_date", DateType(), True)
])

# COMMAND ----------

# Get list of Bronze files to process
try:
    if BATCH_ID:
        # Process specific batch
        bronze_files = dbutils.fs.ls(f"{BRONZE_PATH}")
        bronze_files = [f for f in bronze_files if BATCH_ID in f.name and f.name.endswith('.x12')]
    else:
        # Process all unprocessed files
        bronze_files = dbutils.fs.ls(f"{BRONZE_PATH}")
        bronze_files = [f for f in bronze_files if f.name.endswith('.x12')]
    
    print(f"Found {len(bronze_files)} Bronze files to process")
    
    if not bronze_files:
        print("No Bronze files found for processing")
        dbutils.notebook.exit("No files to process")

except Exception as e:
    print(f"Error listing Bronze files: {str(e)}")
    dbutils.notebook.exit(f"Error: {str(e)}")

# COMMAND ----------

# Process each Bronze file
processed_records = []
processing_summary = {
    "batch_id": BATCH_ID,
    "processing_date": PROCESSING_DATE,
    "files_processed": 0,
    "transactions_processed": 0,
    "transactions_valid": 0,
    "transactions_invalid": 0,
    "total_quality_score": 0
}

for file_info in bronze_files:
    try:
        file_path = file_info.path
        file_name = file_info.name
        
        print(f"Processing Bronze file: {file_name}")
        
        # Read file content
        file_content = dbutils.fs.head(file_path, max_bytes=50*1024*1024)  # Read up to 50MB
        
        # Read metadata if available
        metadata_path = f"{file_path}.metadata.json"
        metadata = {}
        try:
            metadata_content = dbutils.fs.head(metadata_path)
            metadata = json.loads(metadata_content)
        except:
            pass
        
        # Parse X12 file
        segments = parse_x12_segments(file_content)
        
        # Group segments by transaction set
        current_transaction = []
        transaction_sets = []
        isa_data = {}
        gs_data = {}
        st_data = {}
        
        for segment in segments:
            segment_id = segment["segment_id"]
            
            if segment_id == "ISA":
                isa_data = parse_isa_segment(segment["elements"])
            elif segment_id == "GS":
                gs_data = parse_gs_segment(segment["elements"])
            elif segment_id == "ST":
                # Start new transaction set
                if current_transaction:
                    transaction_sets.append((st_data, current_transaction))
                st_data = parse_st_segment(segment["elements"])
                current_transaction = [segment]
            elif segment_id == "SE":
                # End current transaction set
                current_transaction.append(segment)
                transaction_sets.append((st_data, current_transaction))
                current_transaction = []
            else:
                current_transaction.append(segment)
        
        # Process each transaction set
        for st_header, transaction_segments in transaction_sets:
            try:
                transaction_type = st_header.get("transaction_set_identifier_code", "")
                
                # Parse transaction
                parsed_transaction = parse_transaction_set(transaction_segments, transaction_type)
                
                # Validate parsed data
                validation_results = validate_parsed_data(
                    parsed_transaction["parsed_data"], 
                    transaction_type
                )
                
                # Create record
                record = {
                    "batch_id": BATCH_ID,
                    "file_name": file_name,
                    "processing_timestamp": datetime.now(),
                    "interchange_control_number": isa_data.get("interchange_control_number", ""),
                    "functional_group_number": gs_data.get("group_control_number", ""),
                    "transaction_set_control_number": st_header.get("transaction_set_control_number", ""),
                    "transaction_type": transaction_type,
                    "sender_id": isa_data.get("interchange_sender_id", ""),
                    "receiver_id": isa_data.get("interchange_receiver_id", ""),
                    "transaction_date": gs_data.get("date", ""),
                    "parsed_data": json.dumps(parsed_transaction["parsed_data"]),
                    "validation_results": json.dumps(validation_results),
                    "quality_score": validation_results["quality_score"],
                    "is_valid": validation_results["is_valid"],
                    "processing_date": datetime.strptime(PROCESSING_DATE, "%Y-%m-%d").date()
                }
                
                processed_records.append(record)
                
                # Update summary
                processing_summary["transactions_processed"] += 1
                if validation_results["is_valid"]:
                    processing_summary["transactions_valid"] += 1
                else:
                    processing_summary["transactions_invalid"] += 1
                processing_summary["total_quality_score"] += validation_results["quality_score"]
                
                print(f"  ✓ Processed transaction {transaction_type} - Quality: {validation_results['quality_score']}")
            
            except Exception as e:
                print(f"  ✗ Error processing transaction: {str(e)}")
                processing_summary["transactions_invalid"] += 1
        
        processing_summary["files_processed"] += 1
        
    except Exception as e:
        print(f"✗ Error processing file {file_name}: {str(e)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save to Silver Layer

# COMMAND ----------

if processed_records:
    # Create DataFrame
    df = spark.createDataFrame(processed_records, schema=parsed_x12_schema)
    
    # Write to Silver layer with partitioning
    silver_output_path = f"{SILVER_PATH}transactions/"
    
    df.write \
        .mode("append") \
        .partitionBy("processing_date", "transaction_type") \
        .option("path", silver_output_path) \
        .saveAsTable("silver_x12_transactions")
    
    print(f"✓ Saved {len(processed_records)} transaction records to Silver layer")
    
    # Calculate and save summary metrics
    processing_summary["average_quality_score"] = (
        processing_summary["total_quality_score"] / processing_summary["transactions_processed"]
        if processing_summary["transactions_processed"] > 0 else 0
    )
    
    # Save processing summary
    summary_path = f"{SILVER_PATH}_processing_summaries/{PROCESSING_DATE}_{BATCH_ID}_summary.json"
    dbutils.fs.put(summary_path, json.dumps(processing_summary, indent=2, default=str), overwrite=True)
else:
    print("No records to save")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Processing Summary

# COMMAND ----------

print("=" * 60)
print("SILVER LAYER PROCESSING SUMMARY")
print("=" * 60)
print(f"Processing Date: {PROCESSING_DATE}")
print(f"Batch ID: {BATCH_ID}")
print(f"Files Processed: {processing_summary['files_processed']}")
print(f"Transactions Processed: {processing_summary['transactions_processed']}")
print(f"Valid Transactions: {processing_summary['transactions_valid']}")
print(f"Invalid Transactions: {processing_summary['transactions_invalid']}")
if processing_summary['transactions_processed'] > 0:
    success_rate = (processing_summary['transactions_valid'] / processing_summary['transactions_processed']) * 100
    avg_quality = processing_summary.get('average_quality_score', 0)
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Average Quality Score: {avg_quality:.1f}")

# Return summary for pipeline
dbutils.notebook.exit(json.dumps(processing_summary, default=str))

# COMMAND ----------