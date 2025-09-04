# Local X12 Processing DAG for Airflow
# This DAG replaces Azure Data Factory for local development

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.filesystem import FileSensor
import os
import json

# Default arguments for the DAG
default_args = {
    'owner': 'x12-processing-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 9, 4),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'x12_processing_pipeline',
    default_args=default_args,
    description='Local X12 EDI file processing pipeline',
    schedule_interval=timedelta(minutes=15),  # Check for new files every 15 minutes
    catchup=False,
    max_active_runs=1,
)

# Configuration
INPUT_PATH = '/opt/airflow/data/input'
PROCESSED_PATH = '/opt/airflow/data/processed'
BRONZE_PATH = f'{PROCESSED_PATH}/bronze'
SILVER_PATH = f'{PROCESSED_PATH}/silver'
GOLD_PATH = f'{PROCESSED_PATH}/gold'

def check_for_x12_files(**context):
    """Check for new X12 files in the input directory"""
    import glob
    
    x12_files = glob.glob(f'{INPUT_PATH}/*.x12')
    if x12_files:
        print(f"Found {len(x12_files)} X12 files to process")
        return x12_files
    else:
        print("No X12 files found")
        return []

def bronze_processing(**context):
    """Bronze layer processing - validate and store raw files"""
    x12_files = context['task_instance'].xcom_pull(task_ids='check_files')
    
    if not x12_files:
        print("No files to process in bronze layer")
        return
    
    processed_files = []
    
    for file_path in x12_files:
        try:
            # Basic X12 validation
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Check if file starts with ISA segment
            if not content.startswith('ISA'):
                print(f"Invalid X12 file: {file_path} - Missing ISA segment")
                continue
                
            # Extract metadata
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Create bronze record
            bronze_record = {
                'filename': filename,
                'file_path': file_path,
                'file_size': file_size,
                'processing_timestamp': datetime.now().isoformat(),
                'status': 'validated',
                'raw_content': content[:1000]  # Store first 1000 chars for debugging
            }
            
            # Save to bronze layer
            os.makedirs(BRONZE_PATH, exist_ok=True)
            bronze_file = f"{BRONZE_PATH}/{filename}.json"
            
            with open(bronze_file, 'w') as f:
                json.dump(bronze_record, f, indent=2)
                
            processed_files.append(bronze_file)
            print(f"Processed {filename} in bronze layer")
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
    
    return processed_files

def silver_processing(**context):
    """Silver layer processing - parse X12 segments"""
    bronze_files = context['task_instance'].xcom_pull(task_ids='bronze_processing')
    
    if not bronze_files:
        print("No bronze files to process")
        return
    
    processed_files = []
    
    for bronze_file in bronze_files:
        try:
            # Load bronze record
            with open(bronze_file, 'r') as f:
                bronze_record = json.load(f)
            
            # Read original X12 file
            x12_content = ""
            with open(bronze_record['file_path'], 'r') as f:
                x12_content = f.read()
            
            # Basic X12 parsing (simplified)
            segments = x12_content.split('~')
            parsed_segments = []
            
            for segment in segments:
                if segment.strip():
                    elements = segment.split('*')
                    if elements:
                        parsed_segments.append({
                            'segment_id': elements[0] if elements else '',
                            'elements': elements[1:] if len(elements) > 1 else [],
                            'element_count': len(elements) - 1
                        })
            
            # Create silver record
            silver_record = {
                'source_file': bronze_record['filename'],
                'bronze_file': bronze_file,
                'parsing_timestamp': datetime.now().isoformat(),
                'total_segments': len(parsed_segments),
                'segments': parsed_segments,
                'transaction_type': 'unknown',  # Could be enhanced to detect 837, 835, etc.
                'quality_score': min(100, len(parsed_segments) * 5),  # Simple quality metric
                'status': 'parsed'
            }
            
            # Detect transaction type from segments
            for segment in parsed_segments:
                if segment['segment_id'] == 'ST' and len(segment['elements']) > 0:
                    transaction_code = segment['elements'][0]
                    transaction_types = {
                        '837': 'Healthcare Claim',
                        '835': 'Payment/Remittance',
                        '834': 'Enrollment',
                        '270': 'Eligibility Inquiry',
                        '271': 'Eligibility Response',
                        '276': 'Status Request',
                        '277': 'Status Response'
                    }
                    silver_record['transaction_type'] = transaction_types.get(transaction_code, f'Unknown ({transaction_code})')
                    break
            
            # Save to silver layer
            os.makedirs(SILVER_PATH, exist_ok=True)
            silver_file = f"{SILVER_PATH}/{bronze_record['filename']}_parsed.json"
            
            with open(silver_file, 'w') as f:
                json.dump(silver_record, f, indent=2)
                
            processed_files.append(silver_file)
            print(f"Parsed {bronze_record['filename']} in silver layer - {silver_record['transaction_type']}")
            
        except Exception as e:
            print(f"Error processing {bronze_file}: {str(e)}")
    
    return processed_files

def gold_processing(**context):
    """Gold layer processing - create business analytics"""
    silver_files = context['task_instance'].xcom_pull(task_ids='silver_processing')
    
    if not silver_files:
        print("No silver files to process")
        return
    
    # Aggregate analytics across all processed files
    analytics = {
        'processing_date': datetime.now().isoformat(),
        'total_files_processed': len(silver_files),
        'transaction_type_summary': {},
        'quality_summary': {
            'high_quality': 0,  # > 80
            'medium_quality': 0,  # 50-80
            'low_quality': 0     # < 50
        },
        'segment_analysis': {},
        'files_detail': []
    }
    
    for silver_file in silver_files:
        try:
            # Load silver record
            with open(silver_file, 'r') as f:
                silver_record = json.load(f)
            
            # Update transaction type summary
            tx_type = silver_record['transaction_type']
            analytics['transaction_type_summary'][tx_type] = analytics['transaction_type_summary'].get(tx_type, 0) + 1
            
            # Update quality summary
            quality_score = silver_record['quality_score']
            if quality_score > 80:
                analytics['quality_summary']['high_quality'] += 1
            elif quality_score > 50:
                analytics['quality_summary']['medium_quality'] += 1
            else:
                analytics['quality_summary']['low_quality'] += 1
            
            # Analyze segments
            for segment in silver_record['segments']:
                seg_id = segment['segment_id']
                analytics['segment_analysis'][seg_id] = analytics['segment_analysis'].get(seg_id, 0) + 1
            
            # Add file detail
            analytics['files_detail'].append({
                'filename': silver_record['source_file'],
                'transaction_type': tx_type,
                'quality_score': quality_score,
                'segment_count': silver_record['total_segments']
            })
            
        except Exception as e:
            print(f"Error processing {silver_file}: {str(e)}")
    
    # Save analytics to gold layer
    os.makedirs(GOLD_PATH, exist_ok=True)
    gold_file = f"{GOLD_PATH}/analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(gold_file, 'w') as f:
        json.dump(analytics, f, indent=2)
    
    print(f"Created gold analytics: {analytics['total_files_processed']} files processed")
    print(f"Transaction types: {analytics['transaction_type_summary']}")
    print(f"Quality distribution: {analytics['quality_summary']}")
    
    return gold_file

def cleanup_processed_files(**context):
    """Move processed files to archive"""
    x12_files = context['task_instance'].xcom_pull(task_ids='check_files')
    
    if not x12_files:
        return
    
    archive_path = f'{PROCESSED_PATH}/archive'
    os.makedirs(archive_path, exist_ok=True)
    
    for file_path in x12_files:
        try:
            filename = os.path.basename(file_path)
            archive_file = f"{archive_path}/{filename}"
            
            # Move file to archive
            os.rename(file_path, archive_file)
            print(f"Archived {filename}")
            
        except Exception as e:
            print(f"Error archiving {file_path}: {str(e)}")

# Define tasks
check_files_task = PythonOperator(
    task_id='check_files',
    python_callable=check_for_x12_files,
    dag=dag,
)

bronze_processing_task = PythonOperator(
    task_id='bronze_processing',
    python_callable=bronze_processing,
    dag=dag,
)

silver_processing_task = PythonOperator(
    task_id='silver_processing',
    python_callable=silver_processing,
    dag=dag,
)

gold_processing_task = PythonOperator(
    task_id='gold_processing',
    python_callable=gold_processing,
    dag=dag,
)

cleanup_task = PythonOperator(
    task_id='cleanup_processed_files',
    python_callable=cleanup_processed_files,
    dag=dag,
)

# Create directory structure
create_dirs_task = BashOperator(
    task_id='create_directories',
    bash_command=f'mkdir -p {BRONZE_PATH} {SILVER_PATH} {GOLD_PATH} {PROCESSED_PATH}/archive',
    dag=dag,
)

# Set task dependencies
create_dirs_task >> check_files_task >> bronze_processing_task >> silver_processing_task >> gold_processing_task >> cleanup_task