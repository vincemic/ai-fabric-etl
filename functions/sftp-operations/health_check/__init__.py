"""
Azure Function for health checking SFTP connections to trading partners.

Triggered by timer schedule to periodically verify connectivity and alert on issues.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

import azure.functions as func

# Import our SFTP modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from sftp.manager import TradingPartnerManager
from sftp.exceptions import SFTPConnectionError, SFTPAuthenticationError


# Configuration from environment variables
KEY_VAULT_URI = os.environ.get('KEY_VAULT_URI')
STORAGE_ACCOUNT_NAME = os.environ.get('STORAGE_ACCOUNT_NAME')


def get_configuration() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    
    config = {
        "trading_partners": {
            "enabled": True,
            "sftp": {
                "connection_timeout_seconds": 10,  # Shorter timeout for health checks
                "retry_attempts": 1,
                "retry_delay_seconds": 5
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
                        "inbound": os.environ.get('BCBS001_INBOUND_DIR', '/inbound/x12')
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
                        "inbound": os.environ.get('AETNA02_INBOUND_DIR', '/edi/incoming')
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


def test_partner_connection(manager: TradingPartnerManager, partner_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test connection to a single trading partner.
    
    Args:
        manager: Trading Partner Manager instance
        partner_config: Partner configuration
        
    Returns:
        Dictionary with test results
    """
    partner_id = partner_config.get('id')
    partner_name = partner_config.get('name')
    
    test_result = {
        'partner_id': partner_id,
        'partner_name': partner_name,
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'unknown',
        'connection_time_ms': None,
        'error_message': None,
        'directories_accessible': [],
        'directories_failed': []
    }
    
    connector = None
    
    try:
        start_time = datetime.utcnow()
        
        # Create and test connection
        connector = manager.create_sftp_connector(partner_config)
        connector.connect()
        
        end_time = datetime.utcnow()
        connection_time = (end_time - start_time).total_seconds() * 1000
        
        test_result['connection_time_ms'] = round(connection_time, 2)
        test_result['status'] = 'connected'
        
        # Test directory access
        directories = partner_config.get('directories', {})
        for dir_type, dir_path in directories.items():
            try:
                # Try to list directory (just to test access)
                files = connector.list_files(dir_path)
                test_result['directories_accessible'].append({
                    'type': dir_type,
                    'path': dir_path,
                    'file_count': len(files)
                })
                logging.info(f"Partner {partner_id}: Access to {dir_type} directory successful ({len(files)} files)")
            except Exception as e:
                test_result['directories_failed'].append({
                    'type': dir_type,
                    'path': dir_path,
                    'error': str(e)
                })
                logging.warning(f"Partner {partner_id}: Access to {dir_type} directory failed: {e}")
        
        # Overall status based on directory access
        if test_result['directories_failed']:
            test_result['status'] = 'connected_with_issues'
        else:
            test_result['status'] = 'healthy'
            
        logging.info(f"Health check for {partner_id} successful - {test_result['status']}")
        
    except SFTPConnectionError as e:
        test_result['status'] = 'connection_failed'
        test_result['error_message'] = f"Connection error: {str(e)}"
        logging.error(f"Connection failed for {partner_id}: {e}")
        
    except SFTPAuthenticationError as e:
        test_result['status'] = 'authentication_failed'
        test_result['error_message'] = f"Authentication error: {str(e)}"
        logging.error(f"Authentication failed for {partner_id}: {e}")
        
    except Exception as e:
        test_result['status'] = 'error'
        test_result['error_message'] = str(e)
        logging.error(f"Unexpected error testing {partner_id}: {e}")
        
    finally:
        if connector:
            try:
                connector.disconnect()
            except:
                pass
    
    return test_result


def main(mytimer: func.TimerRequest) -> None:
    """
    Main function for SFTP health check operation.
    
    Args:
        mytimer: Timer trigger request
    """
    utc_timestamp = datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
    
    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info(f'SFTP Health Check function executed at {utc_timestamp}')
    
    try:
        # Load configuration
        config = get_configuration()
        
        # Initialize Trading Partner Manager
        manager = TradingPartnerManager(
            config=config,
            key_vault_uri=KEY_VAULT_URI,
            storage_account_name=STORAGE_ACCOUNT_NAME
        )
        
        # Test each partner
        health_results = []
        pgp_results = []
        
        for partner_config in config["trading_partners"]["partners"]:
            if partner_config.get('enabled', True):
                result = test_partner_connection(manager, partner_config)
                health_results.append(result)
                
                # Test PGP configuration if enabled
                partner_id = partner_config.get('id')
                pgp_config = partner_config.get('pgp', {})
                if pgp_config.get('enabled', False):
                    try:
                        pgp_validation = manager.validate_pgp_configuration(partner_id)
                        pgp_test = manager.test_pgp_operations(partner_id)
                        
                        pgp_result = {
                            'partner_id': partner_id,
                            'validation': pgp_validation,
                            'operations_test': pgp_test,
                            'overall_pgp_status': 'healthy' if pgp_validation.get('valid', False) and pgp_test.get('round_trip_test', {}).get('success', False) else 'failed'
                        }
                        pgp_results.append(pgp_result)
                        
                    except Exception as e:
                        pgp_results.append({
                            'partner_id': partner_id,
                            'error': str(e),
                            'overall_pgp_status': 'error'
                        })
                        logging.warning(f"PGP health check failed for {partner_id}: {e}")
        
        # Validate our organization's PGP configuration
        org_pgp_validation = None
        try:
            org_pgp_validation = manager.validate_pgp_configuration('our_organization')
        except Exception as e:
            logging.warning(f"Organization PGP validation failed: {e}")
            org_pgp_validation = {'valid': False, 'error': str(e)}
        
        # Analyze overall health
        total_partners = len(health_results)
        healthy_partners = len([r for r in health_results if r['status'] == 'healthy'])
        failed_partners = len([r for r in health_results if r['status'] in ['connection_failed', 'authentication_failed', 'error']])
        partners_with_issues = len([r for r in health_results if r['status'] == 'connected_with_issues'])
        
        # Analyze PGP health
        pgp_enabled_partners = len(pgp_results)
        healthy_pgp_partners = len([r for r in pgp_results if r['overall_pgp_status'] == 'healthy'])
        failed_pgp_partners = len([r for r in pgp_results if r['overall_pgp_status'] in ['failed', 'error']])
        
        overall_status = 'healthy'
        if failed_partners > 0:
            overall_status = 'critical' if failed_partners == total_partners else 'degraded'
        elif partners_with_issues > 0 or failed_pgp_partners > 0:
            overall_status = 'warning'
        
        # Log summary
        logging.info(f"Health Check Summary - Total: {total_partners}, Healthy: {healthy_partners}, Issues: {partners_with_issues}, Failed: {failed_partners}")
        logging.info(f"PGP Health Summary - PGP Enabled: {pgp_enabled_partners}, Healthy: {healthy_pgp_partners}, Failed: {failed_pgp_partners}")
        
        # Send health report notification
        health_report = {
            "event_type": "sftp_health_check",
            "overall_status": overall_status,
            "total_partners": total_partners,
            "healthy_partners": healthy_partners,
            "partners_with_issues": partners_with_issues,
            "failed_partners": failed_partners,
            "pgp_enabled_partners": pgp_enabled_partners,
            "healthy_pgp_partners": healthy_pgp_partners,
            "failed_pgp_partners": failed_pgp_partners,
            "organization_pgp_status": org_pgp_validation,
            "timestamp": utc_timestamp,
            "partner_results": health_results,
            "pgp_results": pgp_results
        }
        
        manager.send_notification(health_report)
        
        # Send alert if there are critical issues
        if overall_status in ['critical', 'degraded']:
            failed_results = [r for r in health_results if r['status'] in ['connection_failed', 'authentication_failed', 'error']]
            
            alert_notification = {
                "event_type": "sftp_health_alert",
                "severity": "critical" if overall_status == 'critical' else "warning",
                "overall_status": overall_status,
                "failed_partners": failed_partners,
                "total_partners": total_partners,
                "failures": [
                    {
                        "partner_id": r['partner_id'],
                        "partner_name": r['partner_name'],
                        "status": r['status'],
                        "error_message": r['error_message']
                    }
                    for r in failed_results
                ],
                "timestamp": utc_timestamp
            }
            
            manager.send_notification(alert_notification)
            
        logging.info(f"Health check completed - Overall status: {overall_status}")
    
    except Exception as e:
        logging.error(f"SFTP Health Check function failed: {e}")
        
        # Send error notification
        try:
            error_notification = {
                "event_type": "sftp_health_check_error",
                "error_message": str(e),
                "timestamp": utc_timestamp,
                "severity": "error"
            }
            
            if 'manager' in locals():
                manager.send_notification(error_notification)
        except:
            pass  # Don't fail on notification errors
        
        raise