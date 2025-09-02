# Databricks notebook source
# MAGIC %md
# MAGIC # Gold Layer - X12 Business Intelligence Aggregations
# MAGIC 
# MAGIC This notebook creates business-ready data marts from the Silver layer X12 data,
# MAGIC performing aggregations and transformations for reporting and analytics.

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
dbutils.widgets.text("silver_container", "silver-x12-parsed", "Silver Container")
dbutils.widgets.text("gold_container", "gold-x12-business", "Gold Container")
dbutils.widgets.text("processing_date", "", "Processing Date (YYYY-MM-DD)")
dbutils.widgets.text("lookback_days", "30", "Lookback Days for Analysis")

# Get parameter values
STORAGE_ACCOUNT_NAME = dbutils.widgets.get("storage_account_name")
SILVER_CONTAINER = dbutils.widgets.get("silver_container")
GOLD_CONTAINER = dbutils.widgets.get("gold_container")
PROCESSING_DATE = dbutils.widgets.get("processing_date") or datetime.now().strftime("%Y-%m-%d")
LOOKBACK_DAYS = int(dbutils.widgets.get("lookback_days"))

# Storage paths
SILVER_PATH = f"abfss://{SILVER_CONTAINER}@{STORAGE_ACCOUNT_NAME}.dfs.core.windows.net/"
GOLD_PATH = f"abfss://{GOLD_CONTAINER}@{STORAGE_ACCOUNT_NAME}.dfs.core.windows.net/"

print(f"Silver Path: {SILVER_PATH}")
print(f"Gold Path: {GOLD_PATH}")
print(f"Processing Date: {PROCESSING_DATE}")
print(f"Lookback Days: {LOOKBACK_DAYS}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Silver Layer Data

# COMMAND ----------

# Calculate date range for analysis
end_date = datetime.strptime(PROCESSING_DATE, "%Y-%m-%d")
start_date = end_date - timedelta(days=LOOKBACK_DAYS)

print(f"Analysis period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

# Load Silver layer transactions
try:
    silver_df = spark.read.table("silver_x12_transactions") \
        .filter(col("processing_date").between(start_date.date(), end_date.date())) \
        .filter(col("is_valid") == True)
    
    total_transactions = silver_df.count()
    print(f"Loaded {total_transactions} valid transactions from Silver layer")
    
    if total_transactions == 0:
        print("No data found for the specified date range")
        dbutils.notebook.exit("No data to process")

except Exception as e:
    print(f"Error loading Silver data: {str(e)}")
    dbutils.notebook.exit(f"Error: {str(e)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Business Logic Functions

# COMMAND ----------

def extract_837_claim_metrics(parsed_data_json):
    """Extract business metrics from 837 (Health Care Claim) data."""
    try:
        data = json.loads(parsed_data_json)
        header = data.get("header", {})
        claim = data.get("claim", {})
        service_lines = data.get("service_lines", [])
        provider = data.get("provider", {})
        subscriber = data.get("subscriber", {})
        
        metrics = {
            "total_service_lines": len(service_lines),
            "total_claim_amount": float(claim.get("monetary_amount", 0) or 0),
            "calculated_total": 0.0,
            "amount_variance": 0.0,
            "unique_service_codes": set(),
            "provider_type": provider.get("entity_identifier_code", ""),
            "filing_indicator": claim.get("claim_filing_indicator_code", "")
        }
        
        calculated_total = 0.0
        for service in service_lines:
            service_amount = float(service.get("monetary_amount", 0) or 0)
            calculated_total += service_amount
            
            service_code = service.get("product_service_id")
            if service_code:
                metrics["unique_service_codes"].add(service_code)
        
        metrics["calculated_total"] = calculated_total
        metrics["amount_variance"] = abs(metrics["total_claim_amount"] - calculated_total)
        metrics["unique_service_count"] = len(metrics["unique_service_codes"])
        
        # Remove set for JSON serialization
        del metrics["unique_service_codes"]
        
        return metrics
    except Exception as e:
        logger.error(f"Error extracting 837 claim metrics: {str(e)}")
        return {}

def extract_835_payment_metrics(parsed_data_json):
    """Extract business metrics from 835 (Health Care Payment/Advice) data."""
    try:
        data = json.loads(parsed_data_json)
        header = data.get("header", {})
        claims = data.get("claims", [])
        payer = data.get("payer", {})
        
        metrics = {
            "total_claims": len(claims),
            "total_payment_amount": float(header.get("monetary_amount", 0) or 0),
            "total_charge_amount": 0.0,
            "total_patient_responsibility": 0.0,
            "payment_variance": 0.0,
            "payer_id": payer.get("identification_code", "")
        }
        
        calculated_charges = 0.0
        calculated_patient_resp = 0.0
        
        for claim in claims:
            claim_charge = float(claim.get("claim_charge_amount", 0) or 0)
            claim_payment = float(claim.get("claim_payment_amount", 0) or 0)
            patient_resp = float(claim.get("patient_responsibility_amount", 0) or 0)
            
            calculated_charges += claim_charge
            calculated_patient_resp += patient_resp
        
        metrics["total_charge_amount"] = calculated_charges
        metrics["total_patient_responsibility"] = calculated_patient_resp
        metrics["payment_variance"] = abs(metrics["total_payment_amount"] - (calculated_charges - calculated_patient_resp))
        
        return metrics
    except Exception as e:
        logger.error(f"Error extracting 835 payment metrics: {str(e)}")
        return {}

def extract_834_enrollment_metrics(parsed_data_json):
    """Extract business metrics from 834 (Benefit Enrollment and Maintenance) data."""
    try:
        data = json.loads(parsed_data_json)
        header = data.get("header", {})
        members = data.get("members", [])
        sponsor = data.get("sponsor", {})
        
        metrics = {
            "total_members": len(members),
            "new_enrollments": 0,
            "terminations": 0,
            "changes": 0,
            "coverage_types": set(),
            "sponsor_id": sponsor.get("identification_code", "")
        }
        
        for member in members:
            maintenance_type = member.get("maintenance_type_code", "")
            if maintenance_type == "021":  # New enrollment
                metrics["new_enrollments"] += 1
            elif maintenance_type == "024":  # Termination
                metrics["terminations"] += 1
            elif maintenance_type == "001":  # Change
                metrics["changes"] += 1
            
            coverages = member.get("coverages", [])
            for coverage in coverages:
                insurance_line = coverage.get("insurance_line_code")
                if insurance_line:
                    metrics["coverage_types"].add(insurance_line)
        
        metrics["unique_coverage_types"] = len(metrics["coverage_types"])
        
        # Remove set for JSON serialization
        del metrics["coverage_types"]
        
        return metrics
    except Exception as e:
        logger.error(f"Error extracting 834 enrollment metrics: {str(e)}")
        return {}

def extract_eligibility_metrics(parsed_data_json):
    """Extract business metrics from 270/271 (Eligibility) data."""
    try:
        data = json.loads(parsed_data_json)
        header = data.get("header", {})
        
        # Handle both 270 (inquiry) and 271 (response) formats
        inquiries = data.get("inquiries", [])
        benefits = data.get("benefits", [])
        
        metrics = {
            "total_inquiries": len(inquiries),
            "total_benefits": len(benefits),
            "service_types": set(),
            "coverage_levels": set()
        }
        
        # Process inquiries (270)
        for inquiry in inquiries:
            service_type = inquiry.get("service_type_code")
            if service_type:
                metrics["service_types"].add(service_type)
        
        # Process benefits (271)
        for benefit in benefits:
            service_type = benefit.get("service_type_code")
            coverage_level = benefit.get("coverage_level_code")
            
            if service_type:
                metrics["service_types"].add(service_type)
            if coverage_level:
                metrics["coverage_levels"].add(coverage_level)
        
        metrics["unique_service_types"] = len(metrics["service_types"])
        metrics["unique_coverage_levels"] = len(metrics["coverage_levels"])
        
        # Remove sets for JSON serialization
        del metrics["service_types"]
        del metrics["coverage_levels"]
        
        return metrics
    except Exception as e:
        logger.error(f"Error extracting eligibility metrics: {str(e)}")
        return {}

def extract_claim_status_metrics(parsed_data_json):
    """Extract business metrics from 276/277 (Claim Status) data."""
    try:
        data = json.loads(parsed_data_json)
        header = data.get("header", {})
        
        # Handle both 276 (request) and 277 (response) formats
        claim_status = data.get("claim_status", [])
        
        metrics = {
            "total_claim_statuses": len(claim_status),
            "status_codes": set(),
            "total_claim_charges": 0.0,
            "total_payments": 0.0
        }
        
        # Process status information (277)
        total_charges = 0.0
        total_payments = 0.0
        
        for status in claim_status:
            status_code = status.get("health_care_claim_status_code")
            claim_charge = float(status.get("total_claim_charge_amount", 0) or 0)
            payment_amount = float(status.get("claim_payment_amount", 0) or 0)
            
            if status_code:
                metrics["status_codes"].add(status_code)
            
            total_charges += claim_charge
            total_payments += payment_amount
        
        metrics["total_claim_charges"] = total_charges
        metrics["total_payments"] = total_payments
        metrics["unique_status_codes"] = len(metrics["status_codes"])
        
        # Remove set for JSON serialization
        del metrics["status_codes"]
        
        return metrics
    except Exception as e:
        logger.error(f"Error extracting claim status metrics: {str(e)}")
        return {}

def extract_preauth_request_metrics(parsed_data_json):
    """Extract business metrics from 278 (Preauthorization Request) data."""
    try:
        data = json.loads(parsed_data_json)
        header = data.get("header", {})
        patient = data.get("patient", {})
        service_provider = data.get("service_provider", {})
        review_information = data.get("review_information", {})
        services = data.get("services", [])
        service_dates = data.get("service_dates", [])
        
        metrics = {
            "total_services": len(services),
            "total_service_amount": 0.0,
            "request_category_code": review_information.get("request_category_code"),
            "certification_type_code": review_information.get("certification_type_code"),
            "service_type_code": review_information.get("service_type_code"),
            "patient_first_name": patient.get("first_name"),
            "patient_last_name": patient.get("last_name_or_org_name"),
            "provider_name": service_provider.get("last_name_or_org_name"),
            "provider_id": service_provider.get("identification_code"),
            "request_date": header.get("date"),
            "reference_id": header.get("reference_identification"),
            "service_unit_counts": 0.0,
            "unique_service_types": 0
        }
        
        # Process services
        total_amount = 0.0
        total_units = 0.0
        service_types = set()
        
        for service in services:
            amount = float(service.get("monetary_amount", 0) or 0)
            units = float(service.get("service_unit_count", 0) or 0)
            service_id = service.get("product_service_id")
            
            total_amount += amount
            total_units += units
            
            if service_id:
                service_types.add(service_id)
        
        metrics["total_service_amount"] = total_amount
        metrics["service_unit_counts"] = total_units
        metrics["unique_service_types"] = len(service_types)
        
        return metrics
    except Exception as e:
        logger.error(f"Error extracting preauth request metrics: {str(e)}")
        return {}

def extract_preauth_response_metrics(parsed_data_json):
    """Extract business metrics from 279 (Preauthorization Response) data."""
    try:
        data = json.loads(parsed_data_json)
        header = data.get("header", {})
        source = data.get("source", {})
        patient = data.get("patient", {})
        review_results = data.get("review_results", [])
        messages = data.get("messages", [])
        authorization_dates = data.get("authorization_dates", [])
        
        metrics = {
            "total_review_results": len(review_results),
            "response_date": header.get("date"),
            "reference_id": header.get("reference_identification"),
            "payer_name": source.get("last_name_or_org_name"),
            "patient_first_name": patient.get("first_name"),
            "patient_last_name": patient.get("last_name_or_org_name"),
            "authorization_status": None,
            "primary_action_code": None,
            "has_messages": len(messages) > 0,
            "total_messages": len(messages),
            "authorization_effective_dates": 0,
            "approved_services": 0,
            "denied_services": 0,
            "pending_services": 0
        }
        
        # Process review results
        approved_count = 0
        denied_count = 0
        pending_count = 0
        
        for result in review_results:
            action_code = result.get("action_code")
            
            if not metrics["primary_action_code"]:
                metrics["primary_action_code"] = action_code
            
            # Categorize action codes
            if action_code in ["A1", "A2", "A3", "A4"]:  # Approved variations
                approved_count += 1
                if not metrics["authorization_status"]:
                    metrics["authorization_status"] = "APPROVED"
            elif action_code in ["A6", "CT", "DJ"]:  # Denied variations
                denied_count += 1
                if not metrics["authorization_status"]:
                    metrics["authorization_status"] = "DENIED"
            elif action_code in ["PA", "PN"]:  # Pending variations
                pending_count += 1
                if not metrics["authorization_status"]:
                    metrics["authorization_status"] = "PENDING"
        
        metrics["approved_services"] = approved_count
        metrics["denied_services"] = denied_count
        metrics["pending_services"] = pending_count
        
        # Count authorization dates
        metrics["authorization_effective_dates"] = len(authorization_dates)
        
        return metrics
    except Exception as e:
        logger.error(f"Error extracting preauth response metrics: {str(e)}")
        return {}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Business Metrics UDFs

# COMMAND ----------

# Register UDFs for business metrics extraction
extract_837_claim_metrics_udf = udf(extract_837_claim_metrics, MapType(StringType(), StringType()))
extract_835_payment_metrics_udf = udf(extract_835_payment_metrics, MapType(StringType(), StringType()))
extract_834_enrollment_metrics_udf = udf(extract_834_enrollment_metrics, MapType(StringType(), StringType()))
extract_eligibility_metrics_udf = udf(extract_eligibility_metrics, MapType(StringType(), StringType()))
extract_claim_status_metrics_udf = udf(extract_claim_status_metrics, MapType(StringType(), StringType()))
extract_preauth_request_metrics_udf = udf(extract_preauth_request_metrics, MapType(StringType(), StringType()))
extract_preauth_response_metrics_udf = udf(extract_preauth_response_metrics, MapType(StringType(), StringType()))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Transaction Summary Data Mart

# COMMAND ----------

# Create transaction summary by type and date
transaction_summary = silver_df.groupBy(
    "processing_date",
    "transaction_type",
    "sender_id",
    "receiver_id"
).agg(
    count("*").alias("transaction_count"),
    avg("quality_score").alias("average_quality_score"),
    min("processing_timestamp").alias("first_processed"),
    max("processing_timestamp").alias("last_processed"),
    countDistinct("interchange_control_number").alias("unique_interchanges"),
    countDistinct("file_name").alias("unique_files")
).withColumn("created_at", current_timestamp())

# Save transaction summary
transaction_summary.write \
    .mode("overwrite") \
    .option("path", f"{GOLD_PATH}transaction_summary/") \
    .saveAsTable("gold_transaction_summary")

print(f"✓ Created transaction summary with {transaction_summary.count()} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Health Care Claim Analytics (837)

# COMMAND ----------

# Extract 837 healthcare claim specific metrics
claim_df = silver_df.filter(col("transaction_type") == "837") \
    .withColumn("business_metrics", extract_837_claim_metrics_udf("parsed_data"))

# Create healthcare claim analytics
claim_analytics = claim_df.select(
    "processing_date",
    "sender_id",
    "receiver_id",
    "interchange_control_number",
    "transaction_set_control_number",
    "quality_score",
    col("business_metrics.total_service_lines").cast("int").alias("total_service_lines"),
    col("business_metrics.total_claim_amount").cast("double").alias("total_claim_amount"),
    col("business_metrics.calculated_total").cast("double").alias("calculated_total"),
    col("business_metrics.amount_variance").cast("double").alias("amount_variance"),
    col("business_metrics.unique_service_count").cast("int").alias("unique_service_count"),
    col("business_metrics.provider_type").alias("provider_type"),
    col("business_metrics.filing_indicator").alias("filing_indicator")
).filter(col("total_claim_amount").isNotNull()) \
 .withColumn("variance_percentage", 
            when(col("total_claim_amount") > 0, 
                 col("amount_variance") / col("total_claim_amount") * 100).otherwise(0)) \
 .withColumn("created_at", current_timestamp())

# Save healthcare claim analytics
claim_analytics.write \
    .mode("overwrite") \
    .partitionBy("processing_date") \
    .option("path", f"{GOLD_PATH}healthcare_claim_analytics/") \
    .saveAsTable("gold_healthcare_claim_analytics")

print(f"✓ Created healthcare claim analytics with {claim_analytics.count()} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Healthcare Payment Analytics (835)

# COMMAND ----------

# Extract 835 healthcare payment specific metrics
payment_df = silver_df.filter(col("transaction_type") == "835") \
    .withColumn("business_metrics", extract_835_payment_metrics_udf("parsed_data"))

# Create healthcare payment analytics
payment_analytics = payment_df.select(
    "processing_date",
    "sender_id",
    "receiver_id",
    "interchange_control_number",
    "transaction_set_control_number",
    "quality_score",
    col("business_metrics.total_claims").cast("int").alias("total_claims"),
    col("business_metrics.total_payment_amount").cast("double").alias("total_payment_amount"),
    col("business_metrics.total_charge_amount").cast("double").alias("total_charge_amount"),
    col("business_metrics.total_patient_responsibility").cast("double").alias("total_patient_responsibility"),
    col("business_metrics.payment_variance").cast("double").alias("payment_variance"),
    col("business_metrics.payer_id").alias("payer_id")
).filter(col("total_payment_amount").isNotNull()) \
 .withColumn("variance_percentage", 
            when(col("total_charge_amount") > 0, 
                 col("payment_variance") / col("total_charge_amount") * 100).otherwise(0)) \
 .withColumn("payment_ratio", 
            when(col("total_charge_amount") > 0, 
                 col("total_payment_amount") / col("total_charge_amount") * 100).otherwise(0)) \
 .withColumn("created_at", current_timestamp())

# Save healthcare payment analytics
payment_analytics.write \
    .mode("overwrite") \
    .partitionBy("processing_date") \
    .option("path", f"{GOLD_PATH}healthcare_payment_analytics/") \
    .saveAsTable("gold_healthcare_payment_analytics")

print(f"✓ Created healthcare payment analytics with {payment_analytics.count()} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Healthcare Enrollment Analytics (834)

# COMMAND ----------

# Extract 834 healthcare enrollment specific metrics
enrollment_df = silver_df.filter(col("transaction_type") == "834") \
    .withColumn("business_metrics", extract_834_enrollment_metrics_udf("parsed_data"))

# Create healthcare enrollment analytics
enrollment_analytics = enrollment_df.select(
    "processing_date",
    "sender_id",
    "receiver_id",
    "interchange_control_number",
    "transaction_set_control_number",
    "quality_score",
    col("business_metrics.total_members").cast("int").alias("total_members"),
    col("business_metrics.new_enrollments").cast("int").alias("new_enrollments"),
    col("business_metrics.terminations").cast("int").alias("terminations"),
    col("business_metrics.changes").cast("int").alias("changes"),
    col("business_metrics.unique_coverage_types").cast("int").alias("unique_coverage_types"),
    col("business_metrics.sponsor_id").alias("sponsor_id")
).filter(col("total_members").isNotNull()) \
 .withColumn("enrollment_ratio", 
            when(col("total_members") > 0, 
                 col("new_enrollments") / col("total_members") * 100).otherwise(0)) \
 .withColumn("termination_ratio", 
            when(col("total_members") > 0, 
                 col("terminations") / col("total_members") * 100).otherwise(0)) \
 .withColumn("created_at", current_timestamp())

# Save healthcare enrollment analytics
enrollment_analytics.write \
    .mode("overwrite") \
    .partitionBy("processing_date") \
    .option("path", f"{GOLD_PATH}healthcare_enrollment_analytics/") \
    .saveAsTable("gold_healthcare_enrollment_analytics")

print(f"✓ Created healthcare enrollment analytics with {enrollment_analytics.count()} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Trading Partner Analytics

# COMMAND ----------

# Create comprehensive trading partner analytics
trading_partner_analytics = silver_df.groupBy(
    "processing_date",
    "sender_id",
    "receiver_id"
).agg(
    count("*").alias("total_transactions"),
    countDistinct("transaction_type").alias("unique_transaction_types"),
    avg("quality_score").alias("average_quality_score"),
    sum(when(col("transaction_type") == "837", 1).otherwise(0)).alias("healthcare_claims"),
    sum(when(col("transaction_type") == "835", 1).otherwise(0)).alias("payment_advices"),
    sum(when(col("transaction_type") == "834", 1).otherwise(0)).alias("enrollments"),
    sum(when(col("transaction_type") == "270", 1).otherwise(0)).alias("eligibility_inquiries"),
    sum(when(col("transaction_type") == "271", 1).otherwise(0)).alias("eligibility_responses"),
    sum(when(col("transaction_type") == "276", 1).otherwise(0)).alias("claim_status_requests"),
    sum(when(col("transaction_type") == "277", 1).otherwise(0)).alias("claim_status_responses"),
    sum(when(col("transaction_type") == "278", 1).otherwise(0)).alias("preauth_requests"),
    sum(when(col("transaction_type") == "279", 1).otherwise(0)).alias("preauth_responses"),
    countDistinct("interchange_control_number").alias("unique_interchanges"),
    min("processing_timestamp").alias("first_transaction"),
    max("processing_timestamp").alias("last_transaction")
).withColumn("trading_partner_id", concat(col("sender_id"), lit("-"), col("receiver_id"))) \
 .withColumn("created_at", current_timestamp())

# Save trading partner analytics
trading_partner_analytics.write \
    .mode("overwrite") \
    .partitionBy("processing_date") \
    .option("path", f"{GOLD_PATH}trading_partner_analytics/") \
    .saveAsTable("gold_trading_partner_analytics")

print(f"✓ Created trading partner analytics with {trading_partner_analytics.count()} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Healthcare Preauthorization Request Analytics

# COMMAND ----------

# Create preauthorization request analytics
preauth_request_df = silver_df.filter(col("transaction_type") == "278") \
    .withColumn("business_metrics", extract_preauth_request_metrics_udf(col("parsed_data")))

if preauth_request_df.count() > 0:
    preauth_request_analytics = preauth_request_df.select(
        "processing_date",
        "transaction_date", 
        "sender_id",
        "receiver_id",
        "file_name",
        col("business_metrics.total_services").cast("int").alias("total_services"),
        col("business_metrics.total_service_amount").cast("double").alias("total_service_amount"),
        col("business_metrics.request_category_code").alias("request_category_code"),
        col("business_metrics.certification_type_code").alias("certification_type_code"),
        col("business_metrics.service_type_code").alias("service_type_code"),
        col("business_metrics.patient_first_name").alias("patient_first_name"),
        col("business_metrics.patient_last_name").alias("patient_last_name"),
        col("business_metrics.provider_name").alias("provider_name"),
        col("business_metrics.provider_id").alias("provider_id"),
        col("business_metrics.request_date").alias("request_date"),
        col("business_metrics.reference_id").alias("reference_id"),
        col("business_metrics.service_unit_counts").cast("double").alias("service_unit_counts"),
        col("business_metrics.unique_service_types").cast("int").alias("unique_service_types")
    ).filter(col("total_services").isNotNull()) \
     .withColumn("created_at", current_timestamp())

    # Save preauthorization request analytics
    preauth_request_analytics.write \
        .mode("overwrite") \
        .partitionBy("processing_date") \
        .option("path", f"{GOLD_PATH}healthcare_preauth_request_analytics/") \
        .saveAsTable("gold_healthcare_preauth_request_analytics")

    print(f"✓ Created preauth request analytics with {preauth_request_analytics.count()} records")
else:
    print("⚠ No preauthorization request (278) transactions found")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Healthcare Preauthorization Response Analytics

# COMMAND ----------

# Create preauthorization response analytics
preauth_response_df = silver_df.filter(col("transaction_type") == "279") \
    .withColumn("business_metrics", extract_preauth_response_metrics_udf(col("parsed_data")))

if preauth_response_df.count() > 0:
    preauth_response_analytics = preauth_response_df.select(
        "processing_date",
        "transaction_date",
        "sender_id", 
        "receiver_id",
        "file_name",
        col("business_metrics.total_review_results").cast("int").alias("total_review_results"),
        col("business_metrics.response_date").alias("response_date"),
        col("business_metrics.reference_id").alias("reference_id"),
        col("business_metrics.payer_name").alias("payer_name"),
        col("business_metrics.patient_first_name").alias("patient_first_name"),
        col("business_metrics.patient_last_name").alias("patient_last_name"),
        col("business_metrics.authorization_status").alias("authorization_status"),
        col("business_metrics.primary_action_code").alias("primary_action_code"),
        col("business_metrics.has_messages").cast("boolean").alias("has_messages"),
        col("business_metrics.total_messages").cast("int").alias("total_messages"),
        col("business_metrics.authorization_effective_dates").cast("int").alias("authorization_effective_dates"),
        col("business_metrics.approved_services").cast("int").alias("approved_services"),
        col("business_metrics.denied_services").cast("int").alias("denied_services"),
        col("business_metrics.pending_services").cast("int").alias("pending_services")
    ).filter(col("total_review_results").isNotNull()) \
     .withColumn("approval_rate", 
                when(col("total_review_results") > 0,
                     col("approved_services") / col("total_review_results") * 100).otherwise(0)) \
     .withColumn("denial_rate",
                when(col("total_review_results") > 0,
                     col("denied_services") / col("total_review_results") * 100).otherwise(0)) \
     .withColumn("created_at", current_timestamp())

    # Save preauthorization response analytics
    preauth_response_analytics.write \
        .mode("overwrite") \
        .partitionBy("processing_date") \
        .option("path", f"{GOLD_PATH}healthcare_preauth_response_analytics/") \
        .saveAsTable("gold_healthcare_preauth_response_analytics")

    print(f"✓ Created preauth response analytics with {preauth_response_analytics.count()} records")
else:
    print("⚠ No preauthorization response (279) transactions found")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Quality Metrics

# COMMAND ----------

# Create data quality metrics
quality_metrics = silver_df.groupBy("processing_date", "transaction_type").agg(
    count("*").alias("total_transactions"),
    avg("quality_score").alias("average_quality_score"),
    min("quality_score").alias("min_quality_score"),
    max("quality_score").alias("max_quality_score"),
    sum(when(col("quality_score") >= 90, 1).otherwise(0)).alias("high_quality_count"),
    sum(when(col("quality_score").between(70, 89), 1).otherwise(0)).alias("medium_quality_count"),
    sum(when(col("quality_score") < 70, 1).otherwise(0)).alias("low_quality_count"),
    countDistinct("file_name").alias("unique_files"),
    countDistinct("sender_id").alias("unique_senders"),
    countDistinct("receiver_id").alias("unique_receivers")
).withColumn("high_quality_percentage", 
            col("high_quality_count") / col("total_transactions") * 100) \
 .withColumn("medium_quality_percentage", 
            col("medium_quality_count") / col("total_transactions") * 100) \
 .withColumn("low_quality_percentage", 
            col("low_quality_count") / col("total_transactions") * 100) \
 .withColumn("created_at", current_timestamp())

# Save data quality metrics
quality_metrics.write \
    .mode("overwrite") \
    .partitionBy("processing_date") \
    .option("path", f"{GOLD_PATH}data_quality_metrics/") \
    .saveAsTable("gold_data_quality_metrics")

print(f"✓ Created data quality metrics with {quality_metrics.count()} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Business KPIs Dashboard Data

# COMMAND ----------

# Create aggregated KPIs for dashboard
business_kpis = silver_df.agg(
    count("*").alias("total_transactions"),
    countDistinct("transaction_type").alias("unique_transaction_types"),
    countDistinct("sender_id").alias("unique_senders"),
    countDistinct("receiver_id").alias("unique_receivers"),
    countDistinct("trading_partner_combination").alias("unique_trading_pairs"),
    avg("quality_score").alias("overall_quality_score"),
    sum(when(col("transaction_type") == "837", 1).otherwise(0)).alias("total_healthcare_claims"),
    sum(when(col("transaction_type") == "835", 1).otherwise(0)).alias("total_payment_advices"),
    sum(when(col("transaction_type") == "834", 1).otherwise(0)).alias("total_enrollments"),
    sum(when(col("transaction_type") == "270", 1).otherwise(0)).alias("total_eligibility_inquiries"),
    sum(when(col("transaction_type") == "271", 1).otherwise(0)).alias("total_eligibility_responses"),
    sum(when(col("transaction_type") == "276", 1).otherwise(0)).alias("total_claim_status_requests"),
    sum(when(col("transaction_type") == "277", 1).otherwise(0)).alias("total_claim_status_responses"),
    max("processing_timestamp").alias("last_processed")
).withColumn("trading_partner_combination", concat(col("sender_id"), lit("-"), col("receiver_id"))) \
 .withColumn("processing_date", lit(PROCESSING_DATE).cast("date")) \
 .withColumn("created_at", current_timestamp())

# Save business KPIs
business_kpis.write \
    .mode("overwrite") \
    .option("path", f"{GOLD_PATH}business_kpis/") \
    .saveAsTable("gold_business_kpis")

print(f"✓ Created business KPIs")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Processing Summary

# COMMAND ----------

# Create processing summary
summary = {
    "processing_date": PROCESSING_DATE,
    "lookback_days": LOOKBACK_DAYS,
    "total_silver_transactions": total_transactions,
    "gold_tables_created": [
        "transaction_summary",
        "healthcare_claim_analytics", 
        "healthcare_payment_analytics",
        "healthcare_enrollment_analytics",
        "healthcare_preauth_request_analytics",
        "healthcare_preauth_response_analytics",
        "trading_partner_analytics",
        "data_quality_metrics",
        "business_kpis"
    ],
    "processing_timestamp": datetime.now().isoformat()
}

# Get record counts for each gold table
try:
    summary["record_counts"] = {
        "transaction_summary": transaction_summary.count(),
        "healthcare_claim_analytics": claim_analytics.count() if 'claim_analytics' in locals() else 0,
        "healthcare_payment_analytics": payment_analytics.count() if 'payment_analytics' in locals() else 0,
        "healthcare_enrollment_analytics": enrollment_analytics.count() if 'enrollment_analytics' in locals() else 0,
        "healthcare_preauth_request_analytics": preauth_request_analytics.count() if 'preauth_request_analytics' in locals() else 0,
        "healthcare_preauth_response_analytics": preauth_response_analytics.count() if 'preauth_response_analytics' in locals() else 0,
        "trading_partner_analytics": trading_partner_analytics.count(),
        "data_quality_metrics": quality_metrics.count(),
        "business_kpis": business_kpis.count()
    }
except Exception as e:
    print(f"Warning: Could not calculate all record counts: {str(e)}")

# Save summary
summary_path = f"{GOLD_PATH}_processing_summaries/{PROCESSING_DATE}_gold_summary.json"
dbutils.fs.put(summary_path, json.dumps(summary, indent=2), overwrite=True)

print("=" * 60)
print("GOLD LAYER PROCESSING SUMMARY")
print("=" * 60)
print(f"Processing Date: {PROCESSING_DATE}")
print(f"Silver Transactions Processed: {total_transactions}")
print(f"Gold Tables Created: {len(summary['gold_tables_created'])}")
for table_name in summary['gold_tables_created']:
    count = summary.get('record_counts', {}).get(table_name, 'Unknown')
    print(f"  - {table_name}: {count} records")

# Return summary for pipeline
dbutils.notebook.exit(json.dumps(summary))

# COMMAND ----------