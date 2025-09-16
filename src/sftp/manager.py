"""
Trading Partner Manager for coordinating SFTP operations across multiple partners.

Handles:
- Configuration management
- Multi-partner operations
- File processing workflows
- Error handling and retry logic
- Monitoring and logging
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient
from azure.servicebus import ServiceBusClient, ServiceBusMessage

from .connector import SFTPConnector
from .pgp_manager import PGPManager
from .exceptions import SFTPConnectionError, SFTPAuthenticationError, SFTPFileError


class TradingPartnerManager:
    """
    Manager for coordinating SFTP operations across multiple trading partners.
    
    Features:
    - Multi-partner configuration management
    - Parallel file operations
    - Azure integration (Key Vault, Storage, Service Bus)
    - Retry logic and error handling
    - Comprehensive logging and monitoring
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        key_vault_uri: str = None,
        storage_account_name: str = None,
        logger: logging.Logger = None
    ):
        """
        Initialize Trading Partner Manager.
        
        Args:
            config: Configuration dictionary with trading partner settings
            key_vault_uri: Azure Key Vault URI for secrets
            storage_account_name: Azure Storage account name
            logger: Custom logger instance
        """
        self.config = config
        self.key_vault_uri = key_vault_uri
        self.storage_account_name = storage_account_name
        self.logger = logger or logging.getLogger(__name__)
        
        # Azure clients
        self.credential = DefaultAzureCredential()
        self.key_vault_client = None
        self.blob_service_client = None
        self.servicebus_client = None
        
        # Initialize Azure clients if URIs provided
        if self.key_vault_uri:
            self.key_vault_client = SecretClient(
                vault_url=self.key_vault_uri,
                credential=self.credential
            )
        
        if self.storage_account_name:
            account_url = f"https://{self.storage_account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=self.credential
            )
        
        # Configuration
        self.sftp_config = config.get('trading_partners', {}).get('sftp', {})
        self.partners = config.get('trading_partners', {}).get('partners', [])
        self.enabled_partners = [p for p in self.partners if p.get('enabled', True)]
        
        # Initialize PGP Manager
        self.pgp_manager = PGPManager(
            config=config,
            key_vault_client=self.key_vault_client,
            logger=self.logger
        )
        
        self.logger.info(f"Initialized manager with {len(self.enabled_partners)} enabled partners")
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Retrieve secret from Azure Key Vault.
        
        Args:
            secret_name: Name of the secret
            
        Returns:
            Secret value or None if not found
        """
        if not self.key_vault_client:
            self.logger.warning("Key Vault client not initialized")
            return None
        
        try:
            secret = self.key_vault_client.get_secret(secret_name)
            self.logger.debug(f"Retrieved secret: {secret_name}")
            return secret.value
        except Exception as e:
            self.logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            return None
    
    def create_sftp_connector(self, partner_config: Dict[str, Any]) -> SFTPConnector:
        """
        Create SFTP connector for a trading partner.
        
        Args:
            partner_config: Partner configuration dictionary
            
        Returns:
            Configured SFTPConnector instance
        """
        connection_config = partner_config.get('connection', {})
        
        # Get authentication credentials
        username = connection_config.get('username')
        password = None
        private_key = None
        host_key = None
        
        # Retrieve secrets from Key Vault
        if connection_config.get('password_secret_name'):
            password = self.get_secret(connection_config['password_secret_name'])
        
        if connection_config.get('key_vault_secret_name'):
            private_key = self.get_secret(connection_config['key_vault_secret_name'])
        
        if connection_config.get('host_key_secret_name'):
            host_key = self.get_secret(connection_config['host_key_secret_name'])
        
        # Create connector
        connector = SFTPConnector(
            host=connection_config.get('host'),
            port=connection_config.get('port', 22),
            username=username,
            password=password,
            private_key=private_key,
            host_key=host_key,
            host_key_verification=connection_config.get('host_key_verification', True),
            connection_timeout=self.sftp_config.get('connection_timeout_seconds', 30),
            logger=self.logger
        )
        
        return connector
    
    def fetch_files_from_partner(
        self,
        partner_id: str,
        local_download_path: str = "/tmp/sftp_downloads"
    ) -> List[Dict[str, Any]]:
        """
        Fetch files from a specific trading partner.
        
        Args:
            partner_id: Trading partner ID
            local_download_path: Local path for downloaded files
            
        Returns:
            List of processed file information
        """
        # Find partner configuration
        partner_config = None
        for partner in self.enabled_partners:
            if partner.get('id') == partner_id:
                partner_config = partner
                break
        
        if not partner_config:
            raise ValueError(f"Partner {partner_id} not found or not enabled")
        
        if not partner_config.get('processing', {}).get('auto_fetch', True):
            self.logger.info(f"Auto-fetch disabled for partner {partner_id}")
            return []
        
        results = []
        connector = None
        
        try:
            self.logger.info(f"Starting file fetch for partner {partner_id}")
            
            # Create and connect to SFTP
            connector = self.create_sftp_connector(partner_config)
            connector.connect()
            
            # Get inbound directory and file patterns
            directories = partner_config.get('directories', {})
            inbound_dir = directories.get('inbound', '/inbound')
            file_patterns = partner_config.get('file_patterns', {}).get('fetch', ['*.x12'])
            processing_config = partner_config.get('processing', {})
            
            # List files for each pattern
            all_files = []
            for pattern in file_patterns:
                try:
                    files = connector.list_files(inbound_dir, pattern)
                    all_files.extend(files)
                except Exception as e:
                    self.logger.warning(f"Failed to list files with pattern {pattern}: {e}")
            
            # Filter files by age and size
            max_age_hours = processing_config.get('max_file_age_hours', 72)
            max_size_mb = processing_config.get('max_file_size_mb', 100)
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            eligible_files = []
            for file_info in all_files:
                if file_info['mtime'] >= cutoff_time:
                    if file_info['size'] <= max_size_mb * 1024 * 1024:  # Convert MB to bytes
                        eligible_files.append(file_info)
                    else:
                        self.logger.warning(f"File {file_info['filename']} too large: {file_info['size']} bytes")
                else:
                    self.logger.debug(f"File {file_info['filename']} too old: {file_info['mtime']}")
            
            self.logger.info(f"Found {len(eligible_files)} eligible files for partner {partner_id}")
            
            # Download files
            for file_info in eligible_files:
                try:
                    # Create local file path
                    local_file_path = os.path.join(
                        local_download_path,
                        partner_id,
                        datetime.now().strftime('%Y/%m/%d'),
                        file_info['filename']
                    )
                    
                    # Download file
                    success = connector.download_file(file_info['remote_path'], local_file_path)
                    
                    if success:
                        # Handle PGP decryption if enabled
                        final_file_path = local_file_path
                        decryption_info = None
                        
                        pgp_config = partner_config.get('pgp', {})
                        if pgp_config.get('enabled', False) and pgp_config.get('decrypt_inbound', False):
                            try:
                                decrypted_file_path = local_file_path + '.decrypted'
                                
                                decrypt_success, signature_info = self.pgp_manager.decrypt_file(
                                    input_file_path=local_file_path,
                                    output_file_path=decrypted_file_path,
                                    recipient_partner_id='our_organization',
                                    verify_signature=pgp_config.get('verify_inbound', False),
                                    expected_signer_partner_id=partner_id
                                )
                                
                                if decrypt_success:
                                    final_file_path = decrypted_file_path
                                    decryption_info = {
                                        'decrypted': True,
                                        'signature_info': signature_info
                                    }
                                    self.logger.info(f"Successfully decrypted {file_info['filename']}")
                                    
                                    # Remove encrypted file
                                    try:
                                        os.remove(local_file_path)
                                    except Exception as e:
                                        self.logger.warning(f"Could not remove encrypted file {local_file_path}: {e}")
                                else:
                                    self.logger.warning(f"Failed to decrypt {file_info['filename']}, using original file")
                                    decryption_info = {
                                        'decrypted': False,
                                        'error': 'Decryption failed'
                                    }
                            
                            except Exception as e:
                                self.logger.warning(f"PGP decryption failed for {file_info['filename']}: {e}")
                                decryption_info = {
                                    'decrypted': False,
                                    'error': str(e)
                                }
                        
                        # Upload to Azure Storage if configured
                        blob_path = None
                        if self.blob_service_client:
                            blob_path = self.upload_to_storage(
                                final_file_path,
                                container_name='sftp-inbound',
                                blob_name=f"{partner_id}/{datetime.now().strftime('%Y/%m/%d')}/{file_info['filename']}"
                            )
                        
                        # Archive or delete original file
                        if processing_config.get('archive_after_fetch', True):
                            archive_dir = directories.get('processed', '/processed')
                            archive_path = f"{archive_dir}/{datetime.now().strftime('%Y%m%d')}_{file_info['filename']}"
                            try:
                                connector.move_file(file_info['remote_path'], archive_path)
                                self.logger.info(f"Archived {file_info['filename']} to {archive_path}")
                            except Exception as e:
                                self.logger.warning(f"Failed to archive {file_info['filename']}: {e}")
                        
                        # Record successful processing
                        result = {
                            'partner_id': partner_id,
                            'filename': file_info['filename'],
                            'remote_path': file_info['remote_path'],
                            'local_path': final_file_path,
                            'blob_path': blob_path,
                            'size': file_info['size'],
                            'download_time': datetime.now(),
                            'status': 'success',
                            'pgp_info': decryption_info
                        }
                        results.append(result)
                        
                        self.logger.info(f"Successfully processed {file_info['filename']} for {partner_id}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to process {file_info['filename']}: {e}")
                    
                    # Record failed processing
                    result = {
                        'partner_id': partner_id,
                        'filename': file_info['filename'],
                        'remote_path': file_info['remote_path'],
                        'error': str(e),
                        'download_time': datetime.now(),
                        'status': 'failed'
                    }
                    results.append(result)
            
        except Exception as e:
            self.logger.error(f"Error fetching files for partner {partner_id}: {e}")
            raise
        
        finally:
            if connector:
                connector.disconnect()
        
        return results
    
    def push_files_to_partner(
        self,
        partner_id: str,
        files: List[str],
        file_type: str = 'outbound'
    ) -> List[Dict[str, Any]]:
        """
        Push files to a specific trading partner.
        
        Args:
            partner_id: Trading partner ID
            files: List of local file paths to upload
            file_type: Type of files ('outbound', 'acknowledgment', etc.)
            
        Returns:
            List of upload results
        """
        # Find partner configuration
        partner_config = None
        for partner in self.enabled_partners:
            if partner.get('id') == partner_id:
                partner_config = partner
                break
        
        if not partner_config:
            raise ValueError(f"Partner {partner_id} not found or not enabled")
        
        if not partner_config.get('processing', {}).get('auto_push', True):
            self.logger.info(f"Auto-push disabled for partner {partner_id}")
            return []
        
        results = []
        connector = None
        
        try:
            self.logger.info(f"Starting file push for partner {partner_id} ({len(files)} files)")
            
            # Create and connect to SFTP
            connector = self.create_sftp_connector(partner_config)
            connector.connect()
            
            # Get outbound directory
            directories = partner_config.get('directories', {})
            outbound_dir = directories.get('outbound', '/outbound')
            processing_config = partner_config.get('processing', {})
            
            # Upload each file
            for local_file_path in files:
                try:
                    filename = os.path.basename(local_file_path)
                    
                    # Handle PGP encryption if enabled
                    final_file_path = local_file_path
                    encryption_info = None
                    
                    pgp_config = partner_config.get('pgp', {})
                    if pgp_config.get('enabled', False) and pgp_config.get('encrypt_outbound', False):
                        try:
                            encrypted_file_path = local_file_path + '.pgp'
                            
                            encrypt_success = self.pgp_manager.encrypt_file(
                                input_file_path=local_file_path,
                                output_file_path=encrypted_file_path,
                                recipient_partner_id=partner_id,
                                sign=pgp_config.get('sign_outbound', False),
                                signer_partner_id='our_organization'
                            )
                            
                            if encrypt_success:
                                final_file_path = encrypted_file_path
                                filename = filename + '.pgp'  # Update filename for upload
                                encryption_info = {
                                    'encrypted': True,
                                    'signed': pgp_config.get('sign_outbound', False)
                                }
                                self.logger.info(f"Successfully encrypted {os.path.basename(local_file_path)}")
                            else:
                                self.logger.warning(f"Failed to encrypt {os.path.basename(local_file_path)}, using original file")
                                encryption_info = {
                                    'encrypted': False,
                                    'error': 'Encryption failed'
                                }
                        
                        except Exception as e:
                            self.logger.warning(f"PGP encryption failed for {os.path.basename(local_file_path)}: {e}")
                            encryption_info = {
                                'encrypted': False,
                                'error': str(e)
                            }
                    
                    remote_file_path = f"{outbound_dir}/{filename}"
                    
                    # Upload file
                    success = connector.upload_file(final_file_path, remote_file_path)
                    
                    if success:
                        # Clean up encrypted file if it was created
                        if final_file_path != local_file_path:
                            try:
                                os.remove(final_file_path)
                            except Exception as e:
                                self.logger.warning(f"Could not remove encrypted file {final_file_path}: {e}")
                        
                        # Record successful upload
                        result = {
                            'partner_id': partner_id,
                            'filename': os.path.basename(local_file_path),
                            'local_path': local_file_path,
                            'remote_path': remote_file_path,
                            'upload_time': datetime.now(),
                            'status': 'success',
                            'pgp_info': encryption_info
                        }
                        results.append(result)
                        
                        self.logger.info(f"Successfully uploaded {filename} to {partner_id}")
                        
                        # Delete local file if configured
                        if processing_config.get('delete_after_push', False):
                            try:
                                os.remove(local_file_path)
                                self.logger.debug(f"Deleted local file {local_file_path}")
                            except Exception as e:
                                self.logger.warning(f"Failed to delete local file {local_file_path}: {e}")
                    
                    else:
                        # Clean up encrypted file if it was created but upload failed
                        if final_file_path != local_file_path:
                            try:
                                os.remove(final_file_path)
                            except Exception as e:
                                self.logger.warning(f"Could not remove encrypted file {final_file_path}: {e}")
                
                except Exception as e:
                    # Clean up encrypted file if it was created but process failed
                    if 'final_file_path' in locals() and final_file_path != local_file_path:
                        try:
                            os.remove(final_file_path)
                        except Exception:
                            pass
                    
                    self.logger.error(f"Failed to upload {local_file_path}: {e}")
                    
                    # Record failed upload
                    result = {
                        'partner_id': partner_id,
                        'filename': os.path.basename(local_file_path),
                        'local_path': local_file_path,
                        'error': str(e),
                        'upload_time': datetime.now(),
                        'status': 'failed'
                    }
                    results.append(result)
        
        except Exception as e:
            self.logger.error(f"Error pushing files to partner {partner_id}: {e}")
            raise
        
        finally:
            if connector:
                connector.disconnect()
        
        return results
    
    def fetch_all_partners(self, max_workers: int = 3) -> Dict[str, List[Dict]]:
        """
        Fetch files from all enabled trading partners in parallel.
        
        Args:
            max_workers: Maximum number of parallel worker threads
            
        Returns:
            Dictionary mapping partner_id to list of results
        """
        all_results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit fetch tasks for each partner
            future_to_partner = {
                executor.submit(self.fetch_files_from_partner, partner['id']): partner['id']
                for partner in self.enabled_partners
                if partner.get('processing', {}).get('auto_fetch', True)
            }
            
            # Collect results
            for future in as_completed(future_to_partner):
                partner_id = future_to_partner[future]
                try:
                    results = future.result()
                    all_results[partner_id] = results
                    self.logger.info(f"Completed fetch for partner {partner_id}: {len(results)} files")
                except Exception as e:
                    self.logger.error(f"Failed to fetch from partner {partner_id}: {e}")
                    all_results[partner_id] = []
        
        return all_results
    
    def upload_to_storage(
        self,
        local_file_path: str,
        container_name: str,
        blob_name: str
    ) -> Optional[str]:
        """
        Upload file to Azure Blob Storage.
        
        Args:
            local_file_path: Local file path
            container_name: Storage container name
            blob_name: Blob name/path
            
        Returns:
            Blob URL if successful, None otherwise
        """
        if not self.blob_service_client:
            self.logger.warning("Blob service client not initialized")
            return None
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            with open(local_file_path, 'rb') as data:
                blob_client.upload_blob(data, overwrite=True)
            
            blob_url = blob_client.url
            self.logger.debug(f"Uploaded {local_file_path} to {blob_url}")
            return blob_url
            
        except Exception as e:
            self.logger.error(f"Failed to upload {local_file_path} to storage: {e}")
            return None
    
    def send_notification(
        self,
        message: Dict[str, Any],
        queue_name: str = 'x12-processing-queue'
    ):
        """
        Send notification message to Service Bus queue.
        
        Args:
            message: Message data dictionary
            queue_name: Service Bus queue name
        """
        if not self.servicebus_client:
            self.logger.warning("Service Bus client not initialized")
            return
        
        try:
            with self.servicebus_client:
                sender = self.servicebus_client.get_queue_sender(queue_name=queue_name)
                with sender:
                    service_bus_message = ServiceBusMessage(json.dumps(message))
                    sender.send_messages(service_bus_message)
            
            self.logger.debug(f"Sent notification to queue {queue_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
    
    def get_partner_stats(self) -> Dict[str, Any]:
        """
        Get statistics about trading partners and their configurations.
        
        Returns:
            Dictionary with partner statistics
        """
        stats = {
            'total_partners': len(self.partners),
            'enabled_partners': len(self.enabled_partners),
            'auto_fetch_enabled': len([p for p in self.enabled_partners 
                                     if p.get('processing', {}).get('auto_fetch', True)]),
            'auto_push_enabled': len([p for p in self.enabled_partners 
                                    if p.get('processing', {}).get('auto_push', True)]),
            'partners': []
        }
        
        for partner in self.enabled_partners:
            partner_stats = {
                'id': partner.get('id'),
                'name': partner.get('name'),
                'host': partner.get('connection', {}).get('host'),
                'auto_fetch': partner.get('processing', {}).get('auto_fetch', True),
                'auto_push': partner.get('processing', {}).get('auto_push', True),
                'supported_transactions': {
                    'inbound': partner.get('transaction_types', {}).get('inbound', []),
                    'outbound': partner.get('transaction_types', {}).get('outbound', [])
                }
            }
            stats['partners'].append(partner_stats)
        
        return stats
    
    def validate_pgp_configuration(self, partner_id: str = None) -> Dict[str, Any]:
        """
        Validate PGP configuration for partners.
        
        Args:
            partner_id: Specific partner ID to validate, or None for all
            
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'timestamp': datetime.now(),
            'overall_valid': True,
            'partners': {}
        }
        
        partners_to_check = [partner_id] if partner_id else [p['id'] for p in self.enabled_partners]
        
        for pid in partners_to_check:
            try:
                # Check if partner has PGP configuration
                partner_config = None
                for partner in self.enabled_partners:
                    if partner.get('id') == pid:
                        partner_config = partner
                        break
                
                if not partner_config:
                    validation_results['partners'][pid] = {
                        'valid': False,
                        'error': 'Partner configuration not found'
                    }
                    validation_results['overall_valid'] = False
                    continue
                
                pgp_config = partner_config.get('pgp', {})
                
                if not pgp_config.get('enabled', False):
                    validation_results['partners'][pid] = {
                        'valid': True,
                        'pgp_enabled': False,
                        'message': 'PGP not enabled for this partner'
                    }
                    continue
                
                # Validate PGP configuration
                pgp_validation = self.pgp_manager.validate_key_configuration(pid)
                validation_results['partners'][pid] = pgp_validation
                
                if not pgp_validation['valid']:
                    validation_results['overall_valid'] = False
                
            except Exception as e:
                validation_results['partners'][pid] = {
                    'valid': False,
                    'error': f'Validation failed: {e}'
                }
                validation_results['overall_valid'] = False
                self.logger.error(f"PGP validation failed for {pid}: {e}")
        
        # Also validate our organization's keys
        try:
            org_validation = self.pgp_manager.validate_key_configuration('our_organization')
            validation_results['our_organization'] = org_validation
            
            if not org_validation['valid']:
                validation_results['overall_valid'] = False
        
        except Exception as e:
            validation_results['our_organization'] = {
                'valid': False,
                'error': f'Organization key validation failed: {e}'
            }
            validation_results['overall_valid'] = False
            self.logger.error(f"Organization PGP validation failed: {e}")
        
        return validation_results
    
    def test_pgp_operations(self, partner_id: str, test_content: str = "PGP Test Message") -> Dict[str, Any]:
        """
        Test PGP encrypt/decrypt operations for a partner.
        
        Args:
            partner_id: Trading partner ID
            test_content: Test message content
            
        Returns:
            Dictionary with test results
        """
        test_results = {
            'partner_id': partner_id,
            'timestamp': datetime.now(),
            'encrypt_test': {'success': False},
            'decrypt_test': {'success': False},
            'round_trip_test': {'success': False}
        }
        
        try:
            # Find partner configuration
            partner_config = None
            for partner in self.enabled_partners:
                if partner.get('id') == partner_id:
                    partner_config = partner
                    break
            
            if not partner_config:
                test_results['error'] = 'Partner configuration not found'
                return test_results
            
            pgp_config = partner_config.get('pgp', {})
            if not pgp_config.get('enabled', False):
                test_results['error'] = 'PGP not enabled for partner'
                return test_results
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create test file
                test_file = os.path.join(temp_dir, 'test_message.txt')
                with open(test_file, 'w') as f:
                    f.write(test_content)
                
                # Test encryption
                try:
                    encrypted_file = os.path.join(temp_dir, 'test_message.pgp')
                    encrypt_success = self.pgp_manager.encrypt_file(
                        input_file_path=test_file,
                        output_file_path=encrypted_file,
                        recipient_partner_id=partner_id,
                        sign=True,
                        signer_partner_id='our_organization'
                    )
                    
                    test_results['encrypt_test'] = {
                        'success': encrypt_success,
                        'encrypted_file_exists': os.path.exists(encrypted_file),
                        'encrypted_file_size': os.path.getsize(encrypted_file) if os.path.exists(encrypted_file) else 0
                    }
                    
                    if encrypt_success:
                        # Test decryption
                        try:
                            decrypted_file = os.path.join(temp_dir, 'test_message_decrypted.txt')
                            decrypt_success, signature_info = self.pgp_manager.decrypt_file(
                                input_file_path=encrypted_file,
                                output_file_path=decrypted_file,
                                recipient_partner_id='our_organization',
                                verify_signature=True,
                                expected_signer_partner_id='our_organization'
                            )
                            
                            test_results['decrypt_test'] = {
                                'success': decrypt_success,
                                'signature_info': signature_info,
                                'decrypted_file_exists': os.path.exists(decrypted_file)
                            }
                            
                            if decrypt_success and os.path.exists(decrypted_file):
                                # Verify content matches
                                with open(decrypted_file, 'r') as f:
                                    decrypted_content = f.read()
                                
                                content_matches = decrypted_content == test_content
                                test_results['round_trip_test'] = {
                                    'success': content_matches,
                                    'original_content': test_content,
                                    'decrypted_content': decrypted_content,
                                    'content_matches': content_matches
                                }
                        
                        except Exception as e:
                            test_results['decrypt_test'] = {
                                'success': False,
                                'error': str(e)
                            }
                
                except Exception as e:
                    test_results['encrypt_test'] = {
                        'success': False,
                        'error': str(e)
                    }
        
        except Exception as e:
            test_results['error'] = f'Test setup failed: {e}'
            self.logger.error(f"PGP test failed for {partner_id}: {e}")
        
        return test_results