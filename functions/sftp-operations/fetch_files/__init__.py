"""
Azure Function for fetching files from trading partner SFTP servers.

Triggered by timer schedule to periodically check for new X12 files.
"""

import os
import json
import logging
import tempfile
from datetime import datetime
from typing import Dict, Any

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient
from azure.servicebus import ServiceBusClient, ServiceBusMessage

# Import our SFTP modules (assumes they're packaged with the function)
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from sftp.manager import TradingPartnerManager
from sftp.exceptions import SFTPConnectionError, SFTPAuthenticationError


# Configuration from environment variables
KEY_VAULT_URI = os.environ.get('KEY_VAULT_URI')
STORAGE_ACCOUNT_NAME = os.environ.get('STORAGE_ACCOUNT_NAME')
BRONZE_CONTAINER_NAME = os.environ.get('BRONZE_CONTAINER_NAME', 'bronze-x12-raw')
SFTP_INBOUND_CONTAINER_NAME = os.environ.get('SFTP_INBOUND_CONTAINER_NAME', 'sftp-inbound')
SERVICE_BUS_NAMESPACE = os.environ.get('SERVICE_BUS_NAMESPACE')
SERVICE_BUS_QUEUE_NAME = os.environ.get('SERVICE_BUS_QUEUE_NAME', 'x12-processing-queue')


def get_configuration() -> Dict[str, Any]:
    """Load configuration from environment and Key Vault."""
    
    # Base configuration structure
    config = {
        "trading_partners": {
            "enabled": True,
            "sftp": {
                "connection_timeout_seconds": 30,
                "retry_attempts": 3,
                "retry_delay_seconds": 60,
                "batch_size": 100
            },
            "partners": [
                {
                    "id": "BCBS001",
                    "name": "Blue Cross Blue Shield",
                    "enabled": True,
                    "connection": {
                        "host": os.environ.get('BCBS001_HOST'),
                        "port": int(os.environ.get('BCBS001_PORT', '22')),
                        "username": os.environ.get('BCBS001_USERNAME'),
                        "authentication_method": "key",
                        "key_vault_secret_name": "sftp-bcbs001-private-key",
                        "host_key_secret_name": "sftp-bcbs001-host-key",
                        "host_key_verification": True
                    },
                    "directories": {
                        "inbound": os.environ.get('BCBS001_INBOUND_DIR', '/inbound/x12'),
                        "processed": os.environ.get('BCBS001_PROCESSED_DIR', '/processed')
                    },
                    "file_patterns": {
                        "fetch": ["*.x12", "*.edi", "*.txt"]
                    },
                    "transaction_types": {
                        "inbound": ["837", "270", "276", "834"]
                    },
                    "processing": {
                        "auto_fetch": True,
                        "archive_after_fetch": True,
                        "max_file_age_hours": 72,
                        "max_file_size_mb": 100
                    }
                },
                {
                    "id": "AETNA02",
                    "name": "Aetna Health Plans",
                    "enabled": True,
                    "connection": {
                        "host": os.environ.get('AETNA02_HOST'),
                        "port": int(os.environ.get('AETNA02_PORT', '22')),
                        "username": os.environ.get('AETNA02_USERNAME'),
                        "authentication_method": "password",
                        "password_secret_name": "sftp-aetna02-password",
                        "host_key_secret_name": "sftp-aetna02-host-key",
                        "host_key_verification": True
                    },
                    "directories": {
                        "inbound": os.environ.get('AETNA02_INBOUND_DIR', '/edi/incoming'),
                        "processed": os.environ.get('AETNA02_PROCESSED_DIR', '/edi/archive')
                    },
                    "file_patterns": {
                        "fetch": ["*.x12", "*.edi"]
                    },
                    "transaction_types": {
                        "inbound": ["837", "270", "276"]
                    },
                    "processing": {
                        "auto_fetch": True,
                        "archive_after_fetch": True,
                        "max_file_age_hours": 48,
                        "max_file_size_mb": 50
                    }
                }
            ]
        }
    }
    
    # Filter out partners with missing host configuration
    enabled_partners = []
    for partner in config["trading_partners"]["partners"]:
        if partner["connection"]["host"]:
            enabled_partners.append(partner)
        else:
            logging.warning(f"Skipping partner {partner['id']} - no host configured")
    
    config["trading_partners"]["partners"] = enabled_partners
    
    return config


def main(mytimer: func.TimerRequest) -> None:
    """
    Main function for SFTP fetch operation.
    
    Args:
        mytimer: Timer trigger request
    """
    utc_timestamp = datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
    
    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info(f'SFTP Fetch function executed at {utc_timestamp}')
    
    try:
        # Load configuration
        config = get_configuration()
        
        # Initialize Trading Partner Manager
        manager = TradingPartnerManager(
            config=config,
            key_vault_uri=KEY_VAULT_URI,
            storage_account_name=STORAGE_ACCOUNT_NAME
        )
        
        # Create temporary directory for downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            logging.info(f"Using temporary directory: {temp_dir}")
            
            # Fetch files from all partners
            all_results = manager.fetch_all_partners()
            
            total_files = 0
            successful_files = 0
            failed_files = 0
            
            # Process results and upload to Bronze container
            for partner_id, results in all_results.items():
                logging.info(f"Processing {len(results)} files from partner {partner_id}")
                
                for result in results:
                    total_files += 1
                    
                    if result['status'] == 'success':
                        successful_files += 1
                        
                        # Move file from SFTP staging to Bronze container for processing
                        if result.get('blob_path') and manager.blob_service_client:
                            try:
                                # Copy from sftp-inbound to bronze-x12-raw
                                source_blob_client = manager.blob_service_client.get_blob_client(
                                    container=SFTP_INBOUND_CONTAINER_NAME,
                                    blob=result['blob_path'].split('/')[-1]  # Get blob name from path
                                )
                                
                                bronze_blob_name = f"trading_partners/{partner_id}/{result['filename']}"
                                dest_blob_client = manager.blob_service_client.get_blob_client(
                                    container=BRONZE_CONTAINER_NAME,
                                    blob=bronze_blob_name
                                )
                                
                                # Copy blob
                                dest_blob_client.start_copy_from_url(source_blob_client.url)
                                
                                logging.info(f"Copied {result['filename']} to Bronze container")
                                
                                # Send processing notification
                                notification = {
                                    "event_type": "file_received",
                                    "partner_id": partner_id,
                                    "filename": result['filename'],
                                    "blob_path": bronze_blob_name,
                                    "size": result['size'],
                                    "timestamp": utc_timestamp,
                                    "source": "sftp_fetch"
                                }
                                
                                manager.send_notification(notification)
                                
                            except Exception as e:
                                logging.error(f"Failed to move {result['filename']} to Bronze container: {e}")
                                failed_files += 1
                    else:
                        failed_files += 1
                        logging.error(f"Failed to fetch {result.get('filename', 'unknown')}: {result.get('error')}")
            
            # Log summary
            logging.info(f"SFTP Fetch Summary - Total: {total_files}, Success: {successful_files}, Failed: {failed_files}")
            
            # Send overall status notification
            summary_notification = {
                "event_type": "sftp_fetch_completed",
                "total_files": total_files,
                "successful_files": successful_files,
                "failed_files": failed_files,
                "partners_processed": len(all_results),
                "timestamp": utc_timestamp,
                "execution_id": func.TraceContext.trace_context.trace_id if hasattr(func, 'TraceContext') else 'unknown'
            }
            
            manager.send_notification(summary_notification)
            
            # Alert on high failure rate
            if total_files > 0 and (failed_files / total_files) > 0.2:  # More than 20% failures
                alert_notification = {
                    "event_type": "sftp_fetch_high_failure_rate",
                    "failure_rate": failed_files / total_files,
                    "total_files": total_files,
                    "failed_files": failed_files,
                    "timestamp": utc_timestamp,
                    "severity": "warning"
                }
                
                manager.send_notification(alert_notification)
    
    except Exception as e:
        logging.error(f"SFTP Fetch function failed: {e}")
        
        # Send error notification
        try:
            error_notification = {
                "event_type": "sftp_fetch_error",
                "error_message": str(e),
                "timestamp": utc_timestamp,
                "severity": "error"
            }
            
            # Try to send notification if manager is initialized
            if 'manager' in locals():
                manager.send_notification(error_notification)
        except:
            pass  # Don't fail on notification errors
        
        raise