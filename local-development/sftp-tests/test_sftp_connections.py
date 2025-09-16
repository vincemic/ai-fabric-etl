#!/usr/bin/env python3
"""
Test script for SFTP trading partner connections in local development environment.

This script tests the SFTP functionality using the local test SFTP server.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Add the src directory to the path
sys.path.append('/app/src')

from sftp.connector import SFTPConnector
from sftp.manager import TradingPartnerManager
from sftp.exceptions import SFTPConnectionError, SFTPAuthenticationError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Local development configuration
LOCAL_CONFIG = {
    "trading_partners": {
        "enabled": True,
        "sftp": {
            "connection_timeout_seconds": 10,
            "retry_attempts": 2,
            "retry_delay_seconds": 5,
            "batch_size": 10
        },
        "partners": [
            {
                "id": "BCBS001",
                "name": "Blue Cross Blue Shield (Test)",
                "enabled": True,
                "connection": {
                    "host": "x12-sftp-server",  # Docker service name
                    "port": 22,
                    "username": "bcbs001",
                    "authentication_method": "password",
                    "password": "password123",
                    "host_key_verification": False  # Disable for testing
                },
                "directories": {
                    "inbound": "/home/bcbs001/inbound/x12",
                    "outbound": "/home/bcbs001/outbound/x12",
                    "processed": "/home/bcbs001/processed",
                    "failed": "/home/bcbs001/failed"
                },
                "file_patterns": {
                    "fetch": ["*.x12", "*.edi", "*.txt"],
                    "push": ["*.x12", "*.997", "*.999"]
                },
                "transaction_types": {
                    "inbound": ["837", "270", "276", "834"],
                    "outbound": ["835", "271", "277", "997"]
                },
                "processing": {
                    "auto_fetch": True,
                    "auto_push": True,
                    "archive_after_fetch": True,
                    "delete_after_push": False,
                    "max_file_age_hours": 72,
                    "max_file_size_mb": 100
                }
            },
            {
                "id": "AETNA02",
                "name": "Aetna Health Plans (Test)",
                "enabled": True,
                "connection": {
                    "host": "x12-sftp-server",  # Docker service name
                    "port": 22,
                    "username": "aetna02",
                    "authentication_method": "password",
                    "password": "password456",
                    "host_key_verification": False  # Disable for testing
                },
                "directories": {
                    "inbound": "/home/aetna02/edi/incoming",
                    "outbound": "/home/aetna02/edi/outgoing",
                    "processed": "/home/aetna02/edi/archive",
                    "failed": "/home/aetna02/edi/errors"
                },
                "file_patterns": {
                    "fetch": ["*.x12", "*.edi"],
                    "push": ["*.x12", "*.ack"]
                },
                "transaction_types": {
                    "inbound": ["837", "270", "276"],
                    "outbound": ["835", "271", "277", "997"]
                },
                "processing": {
                    "auto_fetch": True,
                    "auto_push": True,
                    "archive_after_fetch": True,
                    "delete_after_push": False,
                    "max_file_age_hours": 48,
                    "max_file_size_mb": 50
                }
            }
        ]
    }
}


def test_basic_connection(partner_config):
    """Test basic SFTP connection to a trading partner."""
    logger.info(f"Testing connection to {partner_config['name']}...")
    
    connection_config = partner_config['connection']
    
    try:
        connector = SFTPConnector(
            host=connection_config['host'],
            port=connection_config['port'],
            username=connection_config['username'],
            password=connection_config.get('password'),
            host_key_verification=connection_config.get('host_key_verification', False),
            connection_timeout=10,
            logger=logger
        )
        
        # Test connection
        success = connector.connect()
        if success:
            logger.info(f"✓ Successfully connected to {partner_config['name']}")
            
            # Test directory access
            directories = partner_config.get('directories', {})
            for dir_type, dir_path in directories.items():
                try:
                    files = connector.list_files(dir_path)
                    logger.info(f"  ✓ Access to {dir_type} directory successful ({len(files)} files)")
                except Exception as e:
                    logger.warning(f"  ⚠️  Access to {dir_type} directory failed: {e}")
            
            connector.disconnect()
            return True
        else:
            logger.error(f"❌ Failed to connect to {partner_config['name']}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Connection test failed for {partner_config['name']}: {e}")
        return False


def test_file_operations(partner_config):
    """Test file upload and download operations."""
    logger.info(f"Testing file operations for {partner_config['name']}...")
    
    connection_config = partner_config['connection']
    directories = partner_config.get('directories', {})
    
    try:
        connector = SFTPConnector(
            host=connection_config['host'],
            port=connection_config['port'],
            username=connection_config['username'],
            password=connection_config.get('password'),
            host_key_verification=connection_config.get('host_key_verification', False),
            connection_timeout=10,
            logger=logger
        )
        
        connector.connect()
        
        # Create a test file
        test_filename = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.x12"
        test_content = f"""ISA*00*          *00*          *ZZ*TESTSEN        *ZZ*TESTREC        *{datetime.now().strftime('%y%m%d')}*{datetime.now().strftime('%H%M')}*^*00501*000000001*0*T*:~
GS*HC*TESTSEN*TESTREC*{datetime.now().strftime('%Y%m%d')}*{datetime.now().strftime('%H%M')}*1*X*005010~
ST*837*0001~
BHT*0019*00*TEST001*{datetime.now().strftime('%Y%m%d')}*{datetime.now().strftime('%H%M')}~
SE*4*0001~
GE*1*1~
IEA*1*000000001~"""
        
        local_test_file = f"/tmp/{test_filename}"
        with open(local_test_file, 'w') as f:
            f.write(test_content)
        
        # Test upload to outbound directory
        outbound_dir = directories.get('outbound', '/outbound')
        remote_test_path = f"{outbound_dir}/{test_filename}"
        
        upload_success = connector.upload_file(local_test_file, remote_test_path)
        if upload_success:
            logger.info(f"  ✓ File upload successful: {test_filename}")
            
            # Test file existence
            if connector.file_exists(remote_test_path):
                logger.info(f"  ✓ File existence check successful")
                
                # Test download
                download_path = f"/tmp/downloaded_{test_filename}"
                download_success = connector.download_file(remote_test_path, download_path)
                if download_success:
                    logger.info(f"  ✓ File download successful")
                    
                    # Verify content
                    with open(download_path, 'r') as f:
                        downloaded_content = f.read()
                    
                    if downloaded_content == test_content:
                        logger.info(f"  ✓ File content verification successful")
                    else:
                        logger.warning(f"  ⚠️  File content mismatch")
                    
                    # Clean up
                    os.remove(download_path)
                else:
                    logger.error(f"  ❌ File download failed")
                
                # Test file move to processed directory
                processed_dir = directories.get('processed', '/processed')
                processed_path = f"{processed_dir}/processed_{test_filename}"
                
                move_success = connector.move_file(remote_test_path, processed_path)
                if move_success:
                    logger.info(f"  ✓ File move successful")
                    
                    # Clean up - delete the processed file
                    connector.delete_file(processed_path)
                    logger.info(f"  ✓ File cleanup successful")
                else:
                    logger.warning(f"  ⚠️  File move failed")
                    # Try to clean up original file
                    connector.delete_file(remote_test_path)
            else:
                logger.error(f"  ❌ File existence check failed")
        else:
            logger.error(f"  ❌ File upload failed")
        
        # Clean up local file
        os.remove(local_test_file)
        
        connector.disconnect()
        return upload_success
        
    except Exception as e:
        logger.error(f"❌ File operations test failed for {partner_config['name']}: {e}")
        return False


def test_trading_partner_manager():
    """Test the Trading Partner Manager functionality."""
    logger.info("Testing Trading Partner Manager...")
    
    try:
        # Create manager (without Azure services for local testing)
        manager = TradingPartnerManager(
            config=LOCAL_CONFIG,
            key_vault_uri=None,  # No Key Vault in local environment
            storage_account_name=None,  # No Azure Storage in local environment
            logger=logger
        )
        
        # Test partner stats
        stats = manager.get_partner_stats()
        logger.info(f"Partner stats: {stats['total_partners']} total, {stats['enabled_partners']} enabled")
        
        # Test individual partner connections
        for partner in LOCAL_CONFIG['trading_partners']['partners']:
            try:
                connector = manager.create_sftp_connector(partner)
                connector.connect()
                logger.info(f"✓ Manager successfully created connector for {partner['id']}")
                connector.disconnect()
            except Exception as e:
                logger.error(f"❌ Manager failed to create connector for {partner['id']}: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Trading Partner Manager test failed: {e}")
        return False


def setup_test_files():
    """Set up test files in SFTP server directories."""
    logger.info("Setting up test files in SFTP directories...")
    
    # Sample X12 files for testing
    sample_files = [
        {
            "name": "sample_837_claim.x12",
            "content": f"""ISA*00*          *00*          *ZZ*PROVIDER       *ZZ*PAYER          *{datetime.now().strftime('%y%m%d')}*{datetime.now().strftime('%H%M')}*^*00501*000000001*0*T*:~
GS*HC*PROVIDER*PAYER*{datetime.now().strftime('%Y%m%d')}*{datetime.now().strftime('%H%M')}*1*X*005010~
ST*837*0001~
BHT*0019*00*CLAIM001*{datetime.now().strftime('%Y%m%d')}*{datetime.now().strftime('%H%M')}~
NM1*41*2*PROVIDER CLINIC*****46*123456789~
SE*5*0001~
GE*1*1~
IEA*1*000000001~"""
        },
        {
            "name": "sample_270_eligibility.x12",
            "content": f"""ISA*00*          *00*          *ZZ*PROVIDER       *ZZ*PAYER          *{datetime.now().strftime('%y%m%d')}*{datetime.now().strftime('%H%M')}*^*00501*000000002*0*T*:~
GS*HS*PROVIDER*PAYER*{datetime.now().strftime('%Y%m%d')}*{datetime.now().strftime('%H%M')}*1*X*005010~
ST*270*0001~
BHT*0022*13*ELIG001*{datetime.now().strftime('%Y%m%d')}*{datetime.now().strftime('%H%M')}~
HL*1**20*1~
NM1*PR*2*PAYER NAME*****PI*PAYERID~
SE*6*0001~
GE*1*1~
IEA*1*000000002~"""
        }
    ]
    
    # Upload sample files to each partner's inbound directory
    for partner in LOCAL_CONFIG['trading_partners']['partners']:
        logger.info(f"Setting up test files for {partner['name']}...")
        
        connection_config = partner['connection']
        inbound_dir = partner['directories']['inbound']
        
        try:
            connector = SFTPConnector(
                host=connection_config['host'],
                port=connection_config['port'],
                username=connection_config['username'],
                password=connection_config.get('password'),
                host_key_verification=False,
                connection_timeout=10,
                logger=logger
            )
            
            connector.connect()
            
            for sample_file in sample_files:
                # Create local temp file
                local_path = f"/tmp/{sample_file['name']}"
                with open(local_path, 'w') as f:
                    f.write(sample_file['content'])
                
                # Upload to partner's inbound directory
                remote_path = f"{inbound_dir}/{sample_file['name']}"
                
                if connector.upload_file(local_path, remote_path):
                    logger.info(f"  ✓ Uploaded {sample_file['name']} to {partner['id']}")
                else:
                    logger.warning(f"  ⚠️  Failed to upload {sample_file['name']} to {partner['id']}")
                
                # Clean up local file
                os.remove(local_path)
            
            connector.disconnect()
            
        except Exception as e:
            logger.error(f"❌ Failed to setup test files for {partner['name']}: {e}")


def main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("SFTP Trading Partner Connection Tests")
    logger.info("=" * 60)
    
    # Test results
    results = {
        'connection_tests': [],
        'file_operation_tests': [],
        'manager_test': False,
        'setup_test': False
    }
    
    # Set up test files first
    try:
        setup_test_files()
        results['setup_test'] = True
        logger.info("✓ Test file setup completed")
    except Exception as e:
        logger.error(f"❌ Test file setup failed: {e}")
    
    # Test basic connections
    logger.info("\n" + "-" * 40)
    logger.info("Testing Basic Connections")
    logger.info("-" * 40)
    
    for partner in LOCAL_CONFIG['trading_partners']['partners']:
        success = test_basic_connection(partner)
        results['connection_tests'].append({
            'partner': partner['id'],
            'success': success
        })
    
    # Test file operations
    logger.info("\n" + "-" * 40)
    logger.info("Testing File Operations")
    logger.info("-" * 40)
    
    for partner in LOCAL_CONFIG['trading_partners']['partners']:
        success = test_file_operations(partner)
        results['file_operation_tests'].append({
            'partner': partner['id'],
            'success': success
        })
    
    # Test Trading Partner Manager
    logger.info("\n" + "-" * 40)
    logger.info("Testing Trading Partner Manager")
    logger.info("-" * 40)
    
    results['manager_test'] = test_trading_partner_manager()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    connection_successes = sum(1 for r in results['connection_tests'] if r['success'])
    file_op_successes = sum(1 for r in results['file_operation_tests'] if r['success'])
    
    logger.info(f"Setup Test: {'✓ PASS' if results['setup_test'] else '❌ FAIL'}")
    logger.info(f"Connection Tests: {connection_successes}/{len(results['connection_tests'])} passed")
    logger.info(f"File Operation Tests: {file_op_successes}/{len(results['file_operation_tests'])} passed")
    logger.info(f"Manager Test: {'✓ PASS' if results['manager_test'] else '❌ FAIL'}")
    
    # Detailed results
    for result in results['connection_tests']:
        status = "✓ PASS" if result['success'] else "❌ FAIL"
        logger.info(f"  {result['partner']} Connection: {status}")
    
    for result in results['file_operation_tests']:
        status = "✓ PASS" if result['success'] else "❌ FAIL"
        logger.info(f"  {result['partner']} File Ops: {status}")
    
    # Overall result
    total_tests = len(results['connection_tests']) + len(results['file_operation_tests']) + 2
    total_passed = connection_successes + file_op_successes + (1 if results['manager_test'] else 0) + (1 if results['setup_test'] else 0)
    
    logger.info(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        logger.info("🎉 All tests passed! SFTP functionality is working correctly.")
        return 0
    else:
        logger.error("⚠️  Some tests failed. Check the logs above for details.")
        return 1


if __name__ == "__main__":
    exit(main())