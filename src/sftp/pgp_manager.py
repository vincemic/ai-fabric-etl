"""
PGP Manager for handling encryption and decryption of SFTP files.

Provides secure file encryption/decryption capabilities for trading partner
file exchanges using PGP (Pretty Good Privacy) encryption.
"""

import os
import io
import json
import logging
import tempfile
from typing import Dict, List, Optional, Tuple, Union, Any
from pathlib import Path
from datetime import datetime

import pgpy
from pgpy import PGPKey, PGPMessage, PGPSignature
from pgpy.constants import PubKeyAlgorithm, KeyFlags, HashAlgorithm, SymmetricKeyAlgorithm, CompressionAlgorithm

from .exceptions import (
    SFTPFileError,
    SFTPConfigurationError
)


class PGPManager:
    """
    Manager for PGP encryption and decryption operations.
    
    Features:
    - File encryption and decryption
    - Key management and validation
    - Signature creation and verification
    - Azure Key Vault integration for key storage
    - Multi-partner key support
    """
    
    def __init__(
        self,
        config: Dict[str, Any] = None,
        key_vault_client=None,
        logger: logging.Logger = None
    ):
        """
        Initialize PGP Manager.
        
        Args:
            config: PGP configuration dictionary
            key_vault_client: Azure Key Vault client for key retrieval
            logger: Custom logger instance
        """
        self.config = config or {}
        self.key_vault_client = key_vault_client
        self.logger = logger or logging.getLogger(__name__)
        
        # Key caches
        self._public_keys: Dict[str, PGPKey] = {}
        self._private_keys: Dict[str, PGPKey] = {}
        
        # Default PGP settings
        self.default_cipher = SymmetricKeyAlgorithm.AES256
        self.default_hash = HashAlgorithm.SHA256
        self.default_compression = CompressionAlgorithm.ZLIB
        
        self.logger.info("PGP Manager initialized")
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Retrieve secret from Azure Key Vault.
        
        Args:
            secret_name: Name of the secret
            
        Returns:
            Secret value or None if not found
        """
        if not self.key_vault_client:
            self.logger.warning("Key Vault client not available")
            return None
        
        try:
            secret = self.key_vault_client.get_secret(secret_name)
            self.logger.debug(f"Retrieved PGP secret: {secret_name}")
            return secret.value
        except Exception as e:
            self.logger.error(f"Failed to retrieve PGP secret {secret_name}: {e}")
            return None
    
    def load_public_key(self, partner_id: str, key_source: Union[str, Dict[str, Any]]) -> Optional[PGPKey]:
        """
        Load public key for a trading partner.
        
        Args:
            partner_id: Trading partner ID
            key_source: Key source (file path, Key Vault secret name, or key content)
            
        Returns:
            PGPKey instance or None if loading failed
        """
        try:
            # Check cache first
            if partner_id in self._public_keys:
                self.logger.debug(f"Using cached public key for {partner_id}")
                return self._public_keys[partner_id]
            
            key_content = None
            
            if isinstance(key_source, dict):
                # Key source configuration
                if key_source.get('type') == 'key_vault':
                    key_content = self.get_secret(key_source.get('secret_name'))
                elif key_source.get('type') == 'file':
                    key_file_path = key_source.get('path')
                    if os.path.exists(key_file_path):
                        with open(key_file_path, 'r') as f:
                            key_content = f.read()
                elif key_source.get('type') == 'inline':
                    key_content = key_source.get('content')
            elif isinstance(key_source, str):
                # Direct key content or file path
                if os.path.exists(key_source):
                    with open(key_source, 'r') as f:
                        key_content = f.read()
                else:
                    # Assume it's key content
                    key_content = key_source
            
            if not key_content:
                self.logger.error(f"Could not load public key content for {partner_id}")
                return None
            
            # Parse PGP key
            try:
                key, _ = pgpy.PGPKey.from_blob(key_content)
                
                # Validate key
                if not key.is_public:
                    self.logger.error(f"Key for {partner_id} is not a public key")
                    return None
                
                # Cache the key
                self._public_keys[partner_id] = key
                
                self.logger.info(f"Successfully loaded public key for {partner_id} (Key ID: {key.fingerprint.keyid})")
                return key
                
            except Exception as e:
                self.logger.error(f"Failed to parse public key for {partner_id}: {e}")
                return None
        
        except Exception as e:
            self.logger.error(f"Error loading public key for {partner_id}: {e}")
            return None
    
    def load_private_key(self, partner_id: str, key_source: Union[str, Dict[str, Any]], passphrase: str = None) -> Optional[PGPKey]:
        """
        Load private key for a trading partner.
        
        Args:
            partner_id: Trading partner ID
            key_source: Key source (file path, Key Vault secret name, or key content)
            passphrase: Key passphrase if required
            
        Returns:
            PGPKey instance or None if loading failed
        """
        try:
            # Check cache first
            if partner_id in self._private_keys:
                self.logger.debug(f"Using cached private key for {partner_id}")
                return self._private_keys[partner_id]
            
            key_content = None
            
            if isinstance(key_source, dict):
                # Key source configuration
                if key_source.get('type') == 'key_vault':
                    key_content = self.get_secret(key_source.get('secret_name'))
                elif key_source.get('type') == 'file':
                    key_file_path = key_source.get('path')
                    if os.path.exists(key_file_path):
                        with open(key_file_path, 'r') as f:
                            key_content = f.read()
                elif key_source.get('type') == 'inline':
                    key_content = key_source.get('content')
            elif isinstance(key_source, str):
                # Direct key content or file path
                if os.path.exists(key_source):
                    with open(key_source, 'r') as f:
                        key_content = f.read()
                else:
                    # Assume it's key content
                    key_content = key_source
            
            if not key_content:
                self.logger.error(f"Could not load private key content for {partner_id}")
                return None
            
            # Parse PGP key
            try:
                key, _ = pgpy.PGPKey.from_blob(key_content)
                
                # Validate key
                if not key.is_private:
                    self.logger.error(f"Key for {partner_id} is not a private key")
                    return None
                
                # Unlock key if passphrase provided
                if passphrase and key.is_protected:
                    try:
                        with key.unlock(passphrase):
                            # Key unlocked successfully
                            pass
                    except Exception as e:
                        self.logger.error(f"Failed to unlock private key for {partner_id}: {e}")
                        return None
                
                # Cache the key
                self._private_keys[partner_id] = key
                
                self.logger.info(f"Successfully loaded private key for {partner_id} (Key ID: {key.fingerprint.keyid})")
                return key
                
            except Exception as e:
                self.logger.error(f"Failed to parse private key for {partner_id}: {e}")
                return None
        
        except Exception as e:
            self.logger.error(f"Error loading private key for {partner_id}: {e}")
            return None
    
    def encrypt_file(
        self,
        input_file_path: str,
        output_file_path: str,
        recipient_partner_id: str,
        sign: bool = False,
        signer_partner_id: str = None
    ) -> bool:
        """
        Encrypt a file using PGP.
        
        Args:
            input_file_path: Path to input file
            output_file_path: Path to output encrypted file
            recipient_partner_id: Partner ID for encryption (public key)
            sign: Whether to sign the file
            signer_partner_id: Partner ID for signing (private key)
            
        Returns:
            bool: True if encryption successful
        """
        try:
            self.logger.info(f"Encrypting file {input_file_path} for {recipient_partner_id}")
            
            # Load recipient's public key
            recipient_config = self._get_partner_pgp_config(recipient_partner_id)
            if not recipient_config:
                raise SFTPConfigurationError(f"No PGP configuration found for partner {recipient_partner_id}")
            
            public_key = self.load_public_key(recipient_partner_id, recipient_config.get('public_key'))
            if not public_key:
                raise SFTPFileError(f"Could not load public key for {recipient_partner_id}", input_file_path, "encrypt")
            
            # Load signer's private key if signing
            private_key = None
            if sign:
                signer_id = signer_partner_id or 'our_organization'
                signer_config = self._get_partner_pgp_config(signer_id)
                if signer_config:
                    passphrase = self._get_key_passphrase(signer_id)
                    private_key = self.load_private_key(signer_id, signer_config.get('private_key'), passphrase)
            
            # Read input file
            with open(input_file_path, 'rb') as f:
                file_content = f.read()
            
            # Create PGP message
            message = pgpy.PGPMessage.new(file_content, file=True)
            
            # Sign if requested
            if sign and private_key:
                try:
                    if private_key.is_protected:
                        passphrase = self._get_key_passphrase(signer_partner_id or 'our_organization')
                        with private_key.unlock(passphrase):
                            message |= private_key.sign(message)
                    else:
                        message |= private_key.sign(message)
                    self.logger.debug(f"File signed with key {private_key.fingerprint.keyid}")
                except Exception as e:
                    self.logger.warning(f"Failed to sign file: {e}")
            
            # Encrypt message
            encrypted_message = public_key.encrypt(
                message,
                cipher=self.default_cipher,
                compression=self.default_compression
            )
            
            # Write encrypted file
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
            with open(output_file_path, 'w') as f:
                f.write(str(encrypted_message))
            
            self.logger.info(f"Successfully encrypted file to {output_file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt file {input_file_path}: {e}")
            return False
    
    def decrypt_file(
        self,
        input_file_path: str,
        output_file_path: str,
        recipient_partner_id: str,
        verify_signature: bool = False,
        expected_signer_partner_id: str = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Decrypt a PGP encrypted file.
        
        Args:
            input_file_path: Path to encrypted input file
            output_file_path: Path to decrypted output file
            recipient_partner_id: Partner ID for decryption (private key)
            verify_signature: Whether to verify signature
            expected_signer_partner_id: Expected signer's partner ID (public key)
            
        Returns:
            Tuple of (success, signature_info)
        """
        try:
            self.logger.info(f"Decrypting file {input_file_path} for {recipient_partner_id}")
            
            # Load recipient's private key
            recipient_config = self._get_partner_pgp_config(recipient_partner_id)
            if not recipient_config:
                raise SFTPConfigurationError(f"No PGP configuration found for partner {recipient_partner_id}")
            
            passphrase = self._get_key_passphrase(recipient_partner_id)
            private_key = self.load_private_key(recipient_partner_id, recipient_config.get('private_key'), passphrase)
            if not private_key:
                raise SFTPFileError(f"Could not load private key for {recipient_partner_id}", input_file_path, "decrypt")
            
            # Read encrypted file
            with open(input_file_path, 'r') as f:
                encrypted_content = f.read()
            
            # Parse encrypted message
            try:
                encrypted_message = pgpy.PGPMessage.from_blob(encrypted_content)
            except Exception as e:
                raise SFTPFileError(f"Invalid PGP message format: {e}", input_file_path, "decrypt")
            
            # Decrypt message
            if private_key.is_protected:
                with private_key.unlock(passphrase):
                    decrypted_message = private_key.decrypt(encrypted_message)
            else:
                decrypted_message = private_key.decrypt(encrypted_message)
            
            signature_info = None
            
            # Verify signature if requested
            if verify_signature and expected_signer_partner_id:
                try:
                    signer_config = self._get_partner_pgp_config(expected_signer_partner_id)
                    if signer_config:
                        signer_public_key = self.load_public_key(expected_signer_partner_id, signer_config.get('public_key'))
                        if signer_public_key:
                            # Check for signatures
                            signature_valid = False
                            signatures = []
                            
                            # Get signatures from message
                            for signature in decrypted_message.signatures:
                                sig_verification = signer_public_key.verify(decrypted_message, signature)
                                signatures.append({
                                    'signer_key_id': signature.signer,
                                    'creation_time': signature.signature.creation_time,
                                    'valid': sig_verification,
                                    'hash_algorithm': str(signature.signature.hash_algorithm)
                                })
                                if sig_verification:
                                    signature_valid = True
                            
                            signature_info = {
                                'verified': signature_valid,
                                'expected_signer': expected_signer_partner_id,
                                'signatures': signatures
                            }
                            
                            if signature_valid:
                                self.logger.info(f"Signature verified for {expected_signer_partner_id}")
                            else:
                                self.logger.warning(f"Signature verification failed for {expected_signer_partner_id}")
                        else:
                            self.logger.warning(f"Could not load signer public key for {expected_signer_partner_id}")
                    else:
                        self.logger.warning(f"No PGP configuration found for signer {expected_signer_partner_id}")
                except Exception as e:
                    self.logger.warning(f"Signature verification failed: {e}")
                    signature_info = {
                        'verified': False,
                        'error': str(e),
                        'expected_signer': expected_signer_partner_id
                    }
            
            # Write decrypted file
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
            with open(output_file_path, 'wb') as f:
                f.write(decrypted_message.message)
            
            self.logger.info(f"Successfully decrypted file to {output_file_path}")
            return True, signature_info
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt file {input_file_path}: {e}")
            return False, None
    
    def _get_partner_pgp_config(self, partner_id: str) -> Optional[Dict[str, Any]]:
        """
        Get PGP configuration for a trading partner.
        
        Args:
            partner_id: Trading partner ID
            
        Returns:
            PGP configuration dictionary or None
        """
        # Look for partner-specific PGP configuration
        pgp_config = self.config.get('pgp', {})
        
        # Check partner-specific config first
        partner_configs = pgp_config.get('partners', {})
        if partner_id in partner_configs:
            return partner_configs[partner_id]
        
        # Check for default configuration
        if partner_id == 'our_organization':
            return pgp_config.get('our_organization', {})
        
        return None
    
    def _get_key_passphrase(self, partner_id: str) -> Optional[str]:
        """
        Get passphrase for a partner's private key.
        
        Args:
            partner_id: Trading partner ID
            
        Returns:
            Passphrase string or None
        """
        partner_config = self._get_partner_pgp_config(partner_id)
        if not partner_config:
            return None
        
        passphrase_config = partner_config.get('private_key_passphrase')
        if not passphrase_config:
            return None
        
        if isinstance(passphrase_config, dict):
            if passphrase_config.get('type') == 'key_vault':
                return self.get_secret(passphrase_config.get('secret_name'))
            elif passphrase_config.get('type') == 'environment':
                return os.environ.get(passphrase_config.get('variable_name'))
            elif passphrase_config.get('type') == 'inline':
                return passphrase_config.get('value')
        else:
            # Direct passphrase value
            return passphrase_config
        
        return None
    
    def generate_key_pair(
        self,
        name: str,
        email: str,
        passphrase: str = None,
        key_size: int = 4096
    ) -> Tuple[PGPKey, PGPKey]:
        """
        Generate a new PGP key pair.
        
        Args:
            name: Key holder name
            email: Key holder email
            passphrase: Private key passphrase (optional)
            key_size: Key size in bits (default: 4096)
            
        Returns:
            Tuple of (private_key, public_key)
        """
        try:
            self.logger.info(f"Generating PGP key pair for {name} <{email}>")
            
            # Create user ID
            uid = pgpy.PGPUID.new(name, email=email)
            
            # Generate key
            key = pgpy.PGPKey.new(PubKeyAlgorithm.RSAEncryptOrSign, key_size)
            
            # Add user ID
            key.add_uid(
                uid,
                usage={KeyFlags.Sign, KeyFlags.EncryptCommunications, KeyFlags.EncryptStorage},
                hashes=[HashAlgorithm.SHA256, HashAlgorithm.SHA384, HashAlgorithm.SHA512],
                ciphers=[SymmetricKeyAlgorithm.AES256, SymmetricKeyAlgorithm.AES192, SymmetricKeyAlgorithm.AES128],
                compression=[CompressionAlgorithm.ZLIB, CompressionAlgorithm.BZ2, CompressionAlgorithm.ZIP]
            )
            
            # Protect private key with passphrase if provided
            if passphrase:
                key.protect(passphrase, SymmetricKeyAlgorithm.AES256, HashAlgorithm.SHA256)
            
            # Extract public key
            public_key = key.pubkey
            
            self.logger.info(f"Generated key pair (Key ID: {key.fingerprint.keyid})")
            return key, public_key
            
        except Exception as e:
            self.logger.error(f"Failed to generate key pair: {e}")
            raise
    
    def validate_key_configuration(self, partner_id: str) -> Dict[str, Any]:
        """
        Validate PGP key configuration for a partner.
        
        Args:
            partner_id: Trading partner ID
            
        Returns:
            Validation results dictionary
        """
        results = {
            'partner_id': partner_id,
            'valid': True,
            'errors': [],
            'warnings': [],
            'public_key': None,
            'private_key': None
        }
        
        try:
            partner_config = self._get_partner_pgp_config(partner_id)
            if not partner_config:
                results['valid'] = False
                results['errors'].append(f"No PGP configuration found for partner {partner_id}")
                return results
            
            # Validate public key
            if 'public_key' in partner_config:
                try:
                    public_key = self.load_public_key(partner_id, partner_config['public_key'])
                    if public_key:
                        results['public_key'] = {
                            'loaded': True,
                            'key_id': public_key.fingerprint.keyid,
                            'algorithm': str(public_key.key_algorithm),
                            'creation_time': public_key.created,
                            'user_ids': [str(uid) for uid in public_key.userids]
                        }
                    else:
                        results['valid'] = False
                        results['errors'].append("Failed to load public key")
                except Exception as e:
                    results['valid'] = False
                    results['errors'].append(f"Public key error: {e}")
            else:
                results['warnings'].append("No public key configuration found")
            
            # Validate private key
            if 'private_key' in partner_config:
                try:
                    passphrase = self._get_key_passphrase(partner_id)
                    private_key = self.load_private_key(partner_id, partner_config['private_key'], passphrase)
                    if private_key:
                        results['private_key'] = {
                            'loaded': True,
                            'key_id': private_key.fingerprint.keyid,
                            'algorithm': str(private_key.key_algorithm),
                            'creation_time': private_key.created,
                            'is_protected': private_key.is_protected,
                            'user_ids': [str(uid) for uid in private_key.userids]
                        }
                    else:
                        results['valid'] = False
                        results['errors'].append("Failed to load private key")
                except Exception as e:
                    results['valid'] = False
                    results['errors'].append(f"Private key error: {e}")
            else:
                results['warnings'].append("No private key configuration found")
            
        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"Configuration validation error: {e}")
        
        return results
    
    def clear_key_cache(self, partner_id: str = None):
        """
        Clear cached keys.
        
        Args:
            partner_id: Specific partner ID to clear, or None for all
        """
        if partner_id:
            self._public_keys.pop(partner_id, None)
            self._private_keys.pop(partner_id, None)
            self.logger.debug(f"Cleared cached keys for {partner_id}")
        else:
            self._public_keys.clear()
            self._private_keys.clear()
            self.logger.debug("Cleared all cached keys")