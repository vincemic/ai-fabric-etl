# PGP Encryption Guide for SFTP Operations

This guide explains how to set up and use PGP (Pretty Good Privacy) encryption with the SFTP function application for secure file exchange with trading partners.

## Overview

The SFTP function application now supports PGP encryption for:
- **Encrypting outbound files** before sending to trading partners
- **Decrypting inbound files** received from trading partners
- **Signing outbound files** for authenticity verification
- **Verifying signatures** on inbound files

## Prerequisites

### Required Dependencies

The following Python packages are required and included in `requirements.txt`:
- `pgpy` - Pure Python PGP implementation
- `cryptography` - Cryptographic primitives
- `python-gnupg` - Alternative GPG interface (backup)

### Azure Key Vault Setup

PGP keys should be stored securely in Azure Key Vault with appropriate access policies:

1. **Function App Managed Identity** must have `Get` and `List` permissions on Key Vault secrets
2. **Key naming convention**:
   - `pgp-{partner-id}-public-key` - Partner's public key
   - `pgp-our-organization-private-key` - Our private key
   - `pgp-our-organization-public-key` - Our public key
   - `pgp-our-organization-passphrase` - Our private key passphrase (if used)

## Configuration

### Partner Configuration

Each trading partner can have individual PGP settings in the configuration:

```json
{
  "id": "PARTNER001",
  "name": "Trading Partner 1",
  "connection": {
    // ... SFTP connection settings
  },
  "pgp": {
    "enabled": true,
    "encrypt_outbound": true,
    "decrypt_inbound": true,
    "sign_outbound": true,
    "verify_inbound": true,
    "public_key": {
      "type": "key_vault",
      "secret_name": "pgp-partner001-public-key"
    }
  }
}
```

### Global PGP Configuration

Organization-wide PGP settings:

```json
{
  "pgp": {
    "our_organization": {
      "private_key": {
        "type": "key_vault",
        "secret_name": "pgp-our-organization-private-key"
      },
      "public_key": {
        "type": "key_vault",
        "secret_name": "pgp-our-organization-public-key"
      },
      "private_key_passphrase": {
        "type": "key_vault",
        "secret_name": "pgp-our-organization-passphrase"
      }
    },
    "partners": {
      "PARTNER001": {
        "public_key": {
          "type": "key_vault",
          "secret_name": "pgp-partner001-public-key"
        }
      }
    }
  }
}
```

### Key Source Types

PGP keys can be sourced from multiple locations:

#### Key Vault (Recommended)
```json
{
  "type": "key_vault",
  "secret_name": "pgp-partner-public-key"
}
```

#### File Path
```json
{
  "type": "file",
  "path": "/path/to/key.asc"
}
```

#### Inline Content
```json
{
  "type": "inline",
  "content": "-----BEGIN PGP PUBLIC KEY BLOCK-----\n..."
}
```

## Key Management

### Generating Key Pairs

Use the PGP Manager to generate new key pairs:

```python
from sftp.pgp_manager import PGPManager

pgp_manager = PGPManager()

# Generate new key pair
private_key, public_key = pgp_manager.generate_key_pair(
    name="Organization Name",
    email="contact@organization.com",
    passphrase="secure_passphrase",
    key_size=4096
)

# Export keys
private_key_content = str(private_key)
public_key_content = str(public_key)
```

### Importing Existing Keys

Keys can be imported from various formats:
- ASCII-armored (.asc files)
- Binary PGP format
- GPG keyring exports

### Key Exchange Process

1. **Generate your organization's key pair**
2. **Export and securely share your public key** with trading partners
3. **Receive and import trading partner public keys**
4. **Store all keys in Azure Key Vault**
5. **Test encryption/decryption** before production use

## Operations

### Inbound File Processing (Fetch)

When fetching files from trading partners:

1. **Download encrypted file** from SFTP server
2. **Decrypt file** using our private key
3. **Verify signature** (if enabled) using partner's public key
4. **Store decrypted file** in Azure Storage
5. **Archive original encrypted file** on SFTP server

#### Configuration Example
```json
{
  "pgp": {
    "enabled": true,
    "decrypt_inbound": true,
    "verify_inbound": true
  }
}
```

### Outbound File Processing (Push)

When sending files to trading partners:

1. **Read unencrypted file** from local storage
2. **Sign file** (if enabled) using our private key
3. **Encrypt file** using partner's public key
4. **Upload encrypted file** to SFTP server
5. **Clean up temporary files**

#### Configuration Example
```json
{
  "pgp": {
    "enabled": true,
    "encrypt_outbound": true,
    "sign_outbound": true
  }
}
```

## Security Considerations

### Key Storage
- **Never store private keys in configuration files**
- **Use Azure Key Vault** for all key storage
- **Protect private keys with strong passphrases**
- **Implement proper access controls** on Key Vault

### Key Rotation
- **Regularly rotate encryption keys** (recommended: annually)
- **Coordinate key updates** with trading partners
- **Maintain backward compatibility** during transition periods
- **Test new keys** before deploying to production

### Monitoring
- **Monitor PGP operations** for failures
- **Alert on signature verification failures**
- **Track key usage and expiration dates**
- **Log all PGP operations** for audit purposes

## Testing and Validation

### Health Check Integration

The health check function now includes PGP validation:

```bash
# Health check includes:
# 1. Key loading validation
# 2. Encryption/decryption round-trip test
# 3. Signature creation and verification
# 4. Configuration validation
```

### Manual Testing

Use the PGP manager for manual testing:

```python
# Test PGP operations for a partner
test_results = manager.test_pgp_operations("PARTNER001")

# Validate configuration
validation_results = manager.validate_pgp_configuration("PARTNER001")
```

## Troubleshooting

### Common Issues

#### Key Loading Failures
- **Check Key Vault permissions** for Function App managed identity
- **Verify secret names** match configuration
- **Validate key format** (ASCII-armored vs binary)
- **Check key expiration dates**

#### Encryption/Decryption Failures
- **Verify key compatibility** between partners
- **Check passphrase requirements** for private keys
- **Validate key algorithms** and cipher suites
- **Review file size limitations**

#### Signature Verification Failures
- **Confirm signer identity** matches expected partner
- **Check signature creation time** for validity windows
- **Verify hash algorithms** are supported
- **Review key trust relationships**

### Logging and Diagnostics

PGP operations are logged with details:
- Key loading success/failure
- Encryption/decryption operations
- Signature creation/verification
- Configuration validation results

Log levels:
- `INFO`: Successful operations
- `WARNING`: Non-critical issues (e.g., signature verification failures)
- `ERROR`: Critical failures requiring attention

### Performance Considerations

#### File Size Limits
- **Large files** may require streaming encryption
- **Memory usage** increases with file size
- **Timeout settings** may need adjustment

#### Optimization Tips
- **Cache loaded keys** to avoid repeated Key Vault calls
- **Use compression** with encryption for better performance
- **Implement parallel processing** for multiple files
- **Monitor Function App memory usage**

## Environment Variables

Required environment variables for PGP operations:

```bash
# Azure Key Vault
KEY_VAULT_URI=https://your-keyvault.vault.azure.net/

# Trading Partner Configuration (if using environment-based config)
PARTNER001_PGP_ENABLED=true
PARTNER001_PGP_ENCRYPT_OUTBOUND=true
PARTNER001_PGP_DECRYPT_INBOUND=true
```

## Example Scenarios

### Scenario 1: Receive Encrypted Claims File

1. **Partner encrypts** 837 claims file with our public key
2. **SFTP fetch function** downloads encrypted file
3. **PGP manager decrypts** file using our private key
4. **Signature verification** confirms file authenticity
5. **Decrypted file** stored in Bronze container for processing

### Scenario 2: Send Encrypted Response File

1. **Processing generates** 835 payment file
2. **PGP manager signs** file with our private key
3. **PGP manager encrypts** file with partner's public key
4. **SFTP push function** uploads encrypted file
5. **Partner decrypts** and processes file

## Support and Maintenance

### Regular Tasks
- **Monitor key expiration dates**
- **Update trading partner keys** as needed
- **Review and rotate organization keys** annually
- **Test PGP operations** during maintenance windows

### Backup and Recovery
- **Backup private keys** securely
- **Document key recovery procedures**
- **Maintain key escrow** for business continuity
- **Test restore procedures** regularly

For additional support, consult the main project documentation or contact the development team.