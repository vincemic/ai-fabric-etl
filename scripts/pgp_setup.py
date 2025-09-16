#!/usr/bin/env python3
"""
PGP Setup and Management Script for SFTP Trading Partners

This script helps with:
- Generating PGP key pairs
- Importing partner public keys
- Exporting public keys for sharing
- Validating key configurations
- Testing PGP operations
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add src directory to path
script_dir = Path(__file__).parent
src_dir = script_dir / 'src'
sys.path.insert(0, str(src_dir))

try:
    from sftp.pgp_manager import PGPManager
    from sftp.manager import TradingPartnerManager
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def load_config(config_file: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {e}")


def generate_organization_keys(
    pgp_manager: PGPManager,
    name: str,
    email: str,
    passphrase: Optional[str] = None,
    key_size: int = 4096,
    output_dir: str = "keys"
) -> Dict[str, str]:
    """Generate PGP key pair for the organization."""
    
    print(f"Generating PGP key pair for {name} <{email}>...")
    
    # Generate key pair
    private_key, public_key = pgp_manager.generate_key_pair(
        name=name,
        email=email,
        passphrase=passphrase,
        key_size=key_size
    )
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Export keys to files
    private_key_file = os.path.join(output_dir, "organization-private-key.asc")
    public_key_file = os.path.join(output_dir, "organization-public-key.asc")
    
    with open(private_key_file, 'w') as f:
        f.write(str(private_key))
    
    with open(public_key_file, 'w') as f:
        f.write(str(public_key))
    
    # Set appropriate permissions
    os.chmod(private_key_file, 0o600)  # Read/write for owner only
    os.chmod(public_key_file, 0o644)  # Read for all, write for owner
    
    result = {
        'key_id': private_key.fingerprint.keyid,
        'fingerprint': str(private_key.fingerprint),
        'private_key_file': private_key_file,
        'public_key_file': public_key_file,
        'private_key_content': str(private_key),
        'public_key_content': str(public_key)
    }
    
    print(f"Key pair generated successfully!")
    print(f"Key ID: {result['key_id']}")
    print(f"Fingerprint: {result['fingerprint']}")
    print(f"Private key: {private_key_file}")
    print(f"Public key: {public_key_file}")
    
    return result


def import_partner_key(
    pgp_manager: PGPManager,
    partner_id: str,
    key_file: str,
    output_dir: str = "keys"
) -> Dict[str, str]:
    """Import a trading partner's public key."""
    
    print(f"Importing public key for partner {partner_id} from {key_file}...")
    
    if not os.path.exists(key_file):
        raise FileNotFoundError(f"Key file not found: {key_file}")
    
    # Load the key
    public_key = pgp_manager.load_public_key(partner_id, key_file)
    
    if not public_key:
        raise ValueError(f"Failed to load public key from {key_file}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Copy key to partner-specific file
    partner_key_file = os.path.join(output_dir, f"{partner_id}-public-key.asc")
    
    with open(key_file, 'r') as src, open(partner_key_file, 'w') as dst:
        dst.write(src.read())
    
    os.chmod(partner_key_file, 0o644)
    
    result = {
        'partner_id': partner_id,
        'key_id': public_key.fingerprint.keyid,
        'fingerprint': str(public_key.fingerprint),
        'key_file': partner_key_file,
        'user_ids': [str(uid) for uid in public_key.userids],
        'creation_time': public_key.created.isoformat() if public_key.created else None
    }
    
    print(f"Partner key imported successfully!")
    print(f"Partner: {partner_id}")
    print(f"Key ID: {result['key_id']}")
    print(f"Fingerprint: {result['fingerprint']}")
    print(f"User IDs: {', '.join(result['user_ids'])}")
    print(f"Saved to: {partner_key_file}")
    
    return result


def validate_configuration(config: Dict[str, Any], logger: logging.Logger) -> bool:
    """Validate PGP configuration."""
    
    print("Validating PGP configuration...")
    
    # Create temporary PGP manager for validation
    pgp_manager = PGPManager(config=config, logger=logger)
    
    overall_valid = True
    
    # Validate organization keys
    print("\nValidating organization keys...")
    org_validation = pgp_manager.validate_key_configuration('our_organization')
    
    if org_validation['valid']:
        print("✓ Organization PGP configuration is valid")
        if org_validation.get('private_key'):
            print(f"  Private key: {org_validation['private_key']['key_id']}")
        if org_validation.get('public_key'):
            print(f"  Public key: {org_validation['public_key']['key_id']}")
    else:
        print("✗ Organization PGP configuration has issues:")
        for error in org_validation.get('errors', []):
            print(f"  - {error}")
        overall_valid = False
    
    # Validate partner keys
    partners = config.get('trading_partners', {}).get('partners', [])
    pgp_enabled_partners = [p for p in partners if p.get('pgp', {}).get('enabled', False)]
    
    if pgp_enabled_partners:
        print(f"\nValidating {len(pgp_enabled_partners)} PGP-enabled partners...")
        
        for partner in pgp_enabled_partners:
            partner_id = partner['id']
            print(f"\nValidating partner {partner_id}...")
            
            partner_validation = pgp_manager.validate_key_configuration(partner_id)
            
            if partner_validation['valid']:
                print(f"✓ Partner {partner_id} PGP configuration is valid")
                if partner_validation.get('public_key'):
                    print(f"  Public key: {partner_validation['public_key']['key_id']}")
            else:
                print(f"✗ Partner {partner_id} PGP configuration has issues:")
                for error in partner_validation.get('errors', []):
                    print(f"  - {error}")
                overall_valid = False
    
    print(f"\nOverall validation: {'✓ PASSED' if overall_valid else '✗ FAILED'}")
    return overall_valid


def test_pgp_operations(config: Dict[str, Any], partner_id: str, logger: logging.Logger) -> bool:
    """Test PGP operations for a specific partner."""
    
    print(f"Testing PGP operations for partner {partner_id}...")
    
    # Create temporary trading partner manager
    manager = TradingPartnerManager(
        config=config,
        logger=logger
    )
    
    # Run PGP tests
    test_results = manager.test_pgp_operations(partner_id)
    
    print(f"\nPGP Test Results for {partner_id}:")
    print(f"Timestamp: {test_results['timestamp']}")
    
    # Encryption test
    encrypt_test = test_results.get('encrypt_test', {})
    if encrypt_test.get('success'):
        print("✓ Encryption test: PASSED")
    else:
        print(f"✗ Encryption test: FAILED - {encrypt_test.get('error', 'Unknown error')}")
    
    # Decryption test
    decrypt_test = test_results.get('decrypt_test', {})
    if decrypt_test.get('success'):
        print("✓ Decryption test: PASSED")
        signature_info = decrypt_test.get('signature_info')
        if signature_info:
            if signature_info.get('verified'):
                print("✓ Signature verification: PASSED")
            else:
                print("✗ Signature verification: FAILED")
    else:
        print(f"✗ Decryption test: FAILED - {decrypt_test.get('error', 'Unknown error')}")
    
    # Round-trip test
    round_trip_test = test_results.get('round_trip_test', {})
    if round_trip_test.get('success'):
        print("✓ Round-trip test: PASSED")
    else:
        print("✗ Round-trip test: FAILED")
        if round_trip_test.get('content_matches') is False:
            print("  Content does not match after encrypt/decrypt cycle")
    
    overall_success = all([
        encrypt_test.get('success', False),
        decrypt_test.get('success', False),
        round_trip_test.get('success', False)
    ])
    
    print(f"\nOverall test result: {'✓ PASSED' if overall_success else '✗ FAILED'}")
    return overall_success


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="PGP Setup and Management for SFTP Trading Partners")
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('-c', '--config', default='trading-partners-config.json', help='Configuration file path')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate keys command
    gen_parser = subparsers.add_parser('generate-keys', help='Generate organization PGP key pair')
    gen_parser.add_argument('--name', required=True, help='Organization name')
    gen_parser.add_argument('--email', required=True, help='Organization email')
    gen_parser.add_argument('--passphrase', help='Private key passphrase (optional)')
    gen_parser.add_argument('--key-size', type=int, default=4096, help='Key size in bits (default: 4096)')
    gen_parser.add_argument('--output-dir', default='keys', help='Output directory for keys')
    
    # Import key command
    import_parser = subparsers.add_parser('import-key', help='Import trading partner public key')
    import_parser.add_argument('--partner-id', required=True, help='Trading partner ID')
    import_parser.add_argument('--key-file', required=True, help='Path to partner public key file')
    import_parser.add_argument('--output-dir', default='keys', help='Output directory for keys')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate PGP configuration')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test PGP operations')
    test_parser.add_argument('--partner-id', required=True, help='Trading partner ID to test')
    
    # List keys command
    list_parser = subparsers.add_parser('list-keys', help='List all configured keys')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    try:
        if args.command == 'generate-keys':
            pgp_manager = PGPManager(logger=logger)
            result = generate_organization_keys(
                pgp_manager=pgp_manager,
                name=args.name,
                email=args.email,
                passphrase=args.passphrase,
                key_size=args.key_size,
                output_dir=args.output_dir
            )
            
            print("\nNext steps:")
            print("1. Store the private key securely in Azure Key Vault")
            print("2. Share the public key with trading partners")
            print("3. Update your configuration to reference the Key Vault secrets")
            
        elif args.command == 'import-key':
            pgp_manager = PGPManager(logger=logger)
            result = import_partner_key(
                pgp_manager=pgp_manager,
                partner_id=args.partner_id,
                key_file=args.key_file,
                output_dir=args.output_dir
            )
            
            print("\nNext steps:")
            print("1. Store the partner's public key in Azure Key Vault")
            print("2. Update your configuration to reference the Key Vault secret")
            print("3. Test PGP operations with the partner")
            
        elif args.command == 'validate':
            config = load_config(args.config)
            success = validate_configuration(config, logger)
            sys.exit(0 if success else 1)
            
        elif args.command == 'test':
            config = load_config(args.config)
            success = test_pgp_operations(config, args.partner_id, logger)
            sys.exit(0 if success else 1)
            
        elif args.command == 'list-keys':
            config = load_config(args.config)
            pgp_manager = PGPManager(config=config, logger=logger)
            
            print("Configured PGP Keys:")
            print("=" * 50)
            
            # Organization keys
            print("\nOrganization:")
            org_validation = pgp_manager.validate_key_configuration('our_organization')
            if org_validation['valid']:
                if org_validation.get('private_key'):
                    print(f"  Private key: {org_validation['private_key']['key_id']}")
                if org_validation.get('public_key'):
                    print(f"  Public key: {org_validation['public_key']['key_id']}")
            else:
                print("  No valid keys configured")
            
            # Partner keys
            partners = config.get('trading_partners', {}).get('partners', [])
            pgp_enabled_partners = [p for p in partners if p.get('pgp', {}).get('enabled', False)]
            
            if pgp_enabled_partners:
                print("\nPartners:")
                for partner in pgp_enabled_partners:
                    partner_id = partner['id']
                    partner_name = partner['name']
                    print(f"\n  {partner_id} ({partner_name}):")
                    
                    partner_validation = pgp_manager.validate_key_configuration(partner_id)
                    if partner_validation['valid']:
                        if partner_validation.get('public_key'):
                            print(f"    Public key: {partner_validation['public_key']['key_id']}")
                    else:
                        print("    No valid keys configured")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()