"""
Azure Function for pushing processed files to trading partner SFTP servers.

Triggered by Service Bus queue messages containing information about files ready for delivery.
"""

import os
import json
import logging
import tempfile
from datetime import datetime
from typing import Dict, Any, List

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

# Import our SFTP modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from sftp.manager import TradingPartnerManager
from sftp.exceptions import SFTPConnectionError, SFTPAuthenticationError


# Configuration from environment variables
KEY_VAULT_URI = os.environ.get('KEY_VAULT_URI')
STORAGE_ACCOUNT_NAME = os.environ.get('STORAGE_ACCOUNT_NAME')
SFTP_OUTBOUND_CONTAINER_NAME = os.environ.get('SFTP_OUTBOUND_CONTAINER_NAME', 'sftp-outbound')


def get_configuration() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    
    config = {
        "trading_partners": {
            "enabled": True,
            "sftp": {
                "connection_timeout_seconds": 30,
                "retry_attempts": 3,
                "retry_delay_seconds": 60
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
                        "outbound": os.environ.get('BCBS001_OUTBOUND_DIR', '/outbound/x12')
                    },
                    "file_patterns": {
                        "push": ["*.x12", "*.997", "*.999"]
                    },
                    "transaction_types": {
                        "outbound": ["835", "271", "277", "997"]
                    },
                    "processing": {
                        "auto_push": True,
                        "delete_after_push": False
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
                        "outbound": os.environ.get('AETNA02_OUTBOUND_DIR', '/edi/outgoing')
                    },
                    "file_patterns": {
                        "push": ["*.x12", "*.ack"]
                    },
                    "transaction_types": {
                        "outbound": ["835", "271", "277", "997"]
                    },
                    "processing": {
                        "auto_push": True,
                        "delete_after_push": False
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


def download_blob_to_temp(blob_service_client: BlobServiceClient, container_name: str, blob_name: str, temp_dir: str) -> str:
    """
    Download blob to temporary file.
    
    Args:
        blob_service_client: Azure Blob Service Client
        container_name: Container name
        blob_name: Blob name
        temp_dir: Temporary directory path
        
    Returns:
        Local file path
    """
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    
    local_filename = os.path.basename(blob_name)
    local_file_path = os.path.join(temp_dir, local_filename)
    
    with open(local_file_path, 'wb') as download_file:
        download_file.write(blob_client.download_blob().readall())
    
    return local_file_path


def main(msg: func.ServiceBusMessage) -> None:
    """
    Main function for SFTP push operation.
    
    Args:
        msg: Service Bus message containing file push instructions
    """
    logging.info('SFTP Push function triggered by Service Bus message')
    
    try:
        # Parse message
        message_body = msg.get_body().decode('utf-8')
        message_data = json.loads(message_body)
        
        logging.info(f"Processing message: {message_data}")
        
        # Validate required fields
        required_fields = ['partner_id', 'files']
        for field in required_fields:
            if field not in message_data:
                raise ValueError(f"Missing required field: {field}")
        
        partner_id = message_data['partner_id']
        files_to_push = message_data['files']  # List of blob paths/names
        
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
            
            # Download files from storage to local temp
            local_files = []
            for blob_path in files_to_push:
                try:
                    local_file_path = download_blob_to_temp(
                        manager.blob_service_client,
                        SFTP_OUTBOUND_CONTAINER_NAME,
                        blob_path,
                        temp_dir
                    )
                    local_files.append(local_file_path)
                    logging.info(f"Downloaded {blob_path} to {local_file_path}")
                except Exception as e:
                    logging.error(f"Failed to download {blob_path}: {e}")
                    continue
            
            if not local_files:
                logging.warning("No files successfully downloaded - nothing to push")
                return
            
            # Push files to partner
            results = manager.push_files_to_partner(partner_id, local_files)
            
            # Log results
            successful_uploads = [r for r in results if r['status'] == 'success']
            failed_uploads = [r for r in results if r['status'] == 'failed']
            
            logging.info(f"Push Summary - Partner: {partner_id}, Success: {len(successful_uploads)}, Failed: {len(failed_uploads)}")
            
            # Send notification about results
            notification = {
                "event_type": "sftp_push_completed",
                "partner_id": partner_id,
                "total_files": len(results),
                "successful_files": len(successful_uploads),
                "failed_files": len(failed_uploads),
                "timestamp": datetime.utcnow().isoformat(),
                "files": [
                    {
                        "filename": r['filename'],
                        "status": r['status'],
                        "error": r.get('error')
                    }
                    for r in results
                ]
            }
            
            manager.send_notification(notification)
            
            # Alert on failures
            if failed_uploads:
                alert_notification = {
                    "event_type": "sftp_push_failures",
                    "partner_id": partner_id,
                    "failed_files": len(failed_uploads),
                    "total_files": len(results),
                    "failures": [
                        {
                            "filename": r['filename'],
                            "error": r.get('error')
                        }
                        for r in failed_uploads
                    ],
                    "timestamp": datetime.utcnow().isoformat(),
                    "severity": "warning"
                }
                
                manager.send_notification(alert_notification)
    
    except Exception as e:
        logging.error(f"SFTP Push function failed: {e}")
        
        # Send error notification
        try:
            error_notification = {
                "event_type": "sftp_push_error",
                "error_message": str(e),
                "message_data": message_data if 'message_data' in locals() else None,
                "timestamp": datetime.utcnow().isoformat(),
                "severity": "error"
            }
            
            if 'manager' in locals():
                manager.send_notification(error_notification)
        except:
            pass  # Don't fail on notification errors
        
        raise