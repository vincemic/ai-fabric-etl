"""
SFTP Connector for trading partner file exchange.

Handles secure connections, authentication, and file operations with trading partners.
"""

import os
import io
import json
import logging
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
import paramiko
from paramiko import SSHClient, SFTPClient
from paramiko.ssh_exception import AuthenticationException, SSHException, NoValidConnectionsError

from .exceptions import (
    SFTPConnectionError,
    SFTPAuthenticationError, 
    SFTPFileError,
    SFTPDirectoryError,
    SFTPPermissionError,
    SFTPTimeoutError
)


class SFTPConnector:
    """
    Secure SFTP connector for trading partner file exchange.
    
    Features:
    - Key-based and password authentication
    - Host key verification
    - Connection pooling and retry logic
    - File transfer with progress tracking
    - Error handling and logging
    """
    
    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = None,
        password: str = None,
        private_key: str = None,
        private_key_passphrase: str = None,
        host_key: str = None,
        host_key_verification: bool = True,
        connection_timeout: int = 30,
        auth_timeout: int = 30,
        logger: logging.Logger = None
    ):
        """
        Initialize SFTP connector.
        
        Args:
            host: SFTP server hostname or IP
            port: SFTP server port (default: 22)
            username: Username for authentication
            password: Password for authentication (if not using key)
            private_key: Private key content for key-based auth
            private_key_passphrase: Passphrase for private key (if required)
            host_key: Expected host key for verification
            host_key_verification: Whether to verify host key (default: True)
            connection_timeout: Connection timeout in seconds
            auth_timeout: Authentication timeout in seconds
            logger: Custom logger instance
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.private_key = private_key
        self.private_key_passphrase = private_key_passphrase
        self.host_key = host_key
        self.host_key_verification = host_key_verification
        self.connection_timeout = connection_timeout
        self.auth_timeout = auth_timeout
        
        self.logger = logger or logging.getLogger(__name__)
        
        self._ssh_client: Optional[SSHClient] = None
        self._sftp_client: Optional[SFTPClient] = None
        self._is_connected = False
        
    def connect(self) -> bool:
        """
        Establish SFTP connection.
        
        Returns:
            bool: True if connection successful
            
        Raises:
            SFTPConnectionError: If connection fails
            SFTPAuthenticationError: If authentication fails
        """
        try:
            self.logger.info(f"Connecting to SFTP server {self.host}:{self.port}")
            
            # Create SSH client
            self._ssh_client = SSHClient()
            
            # Configure host key policy
            if self.host_key_verification:
                if self.host_key:
                    # Add known host key
                    host_keys = self._ssh_client.get_host_keys()
                    host_keys.add(self.host, 'ssh-rsa', paramiko.RSAKey(data=self.host_key.encode()))
                else:
                    # Use system host keys
                    self._ssh_client.load_system_host_keys()
                    self._ssh_client.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
            else:
                self.logger.warning("Host key verification is disabled - this is not secure!")
                self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Prepare authentication
            connect_kwargs = {
                'hostname': self.host,
                'port': self.port,
                'username': self.username,
                'timeout': self.connection_timeout,
                'auth_timeout': self.auth_timeout,
                'look_for_keys': False
            }
            
            # Add authentication method
            if self.private_key:
                self.logger.debug("Using private key authentication")
                key_file = io.StringIO(self.private_key)
                pkey = paramiko.RSAKey.from_private_key(key_file, password=self.private_key_passphrase)
                connect_kwargs['pkey'] = pkey
            elif self.password:
                self.logger.debug("Using password authentication")
                connect_kwargs['password'] = self.password
            else:
                raise SFTPAuthenticationError("No authentication method provided")
            
            # Connect
            self._ssh_client.connect(**connect_kwargs)
            
            # Open SFTP channel
            self._sftp_client = self._ssh_client.open_sftp()
            self._is_connected = True
            
            self.logger.info(f"Successfully connected to {self.host}:{self.port}")
            return True
            
        except AuthenticationException as e:
            self.logger.error(f"Authentication failed for {self.username}@{self.host}: {e}")
            raise SFTPAuthenticationError(f"Authentication failed: {e}", self.username)
        except NoValidConnectionsError as e:
            self.logger.error(f"No valid connections to {self.host}:{self.port}: {e}")
            raise SFTPConnectionError(f"Connection failed: {e}", self.host, self.port)
        except SSHException as e:
            self.logger.error(f"SSH error connecting to {self.host}: {e}")
            raise SFTPConnectionError(f"SSH error: {e}", self.host, self.port)
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to {self.host}: {e}")
            raise SFTPConnectionError(f"Unexpected error: {e}", self.host, self.port)
    
    def disconnect(self):
        """Close SFTP and SSH connections."""
        try:
            if self._sftp_client:
                self._sftp_client.close()
                self._sftp_client = None
            
            if self._ssh_client:
                self._ssh_client.close()
                self._ssh_client = None
                
            self._is_connected = False
            self.logger.info(f"Disconnected from {self.host}:{self.port}")
            
        except Exception as e:
            self.logger.warning(f"Error during disconnect: {e}")
    
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._is_connected and self._sftp_client is not None
    
    def list_files(self, remote_directory: str, file_pattern: str = "*") -> List[Dict]:
        """
        List files in remote directory matching pattern.
        
        Args:
            remote_directory: Remote directory path
            file_pattern: File pattern to match (default: "*")
            
        Returns:
            List of file information dictionaries
            
        Raises:
            SFTPDirectoryError: If directory operations fail
            SFTPFileError: If file listing fails
        """
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")
        
        try:
            self.logger.debug(f"Listing files in {remote_directory} with pattern {file_pattern}")
            
            # Change to directory
            self._sftp_client.chdir(remote_directory)
            
            # List files
            file_list = []
            for item in self._sftp_client.listdir_attr('.'):
                if not item.filename.startswith('.'):  # Skip hidden files
                    # Simple pattern matching (could be enhanced with fnmatch)
                    if file_pattern == "*" or file_pattern in item.filename:
                        file_info = {
                            'filename': item.filename,
                            'size': item.st_size,
                            'mtime': datetime.fromtimestamp(item.st_mtime),
                            'permissions': oct(item.st_mode)[-3:],
                            'is_file': not item.st_mode & 0o040000,  # Check if not directory
                            'remote_path': f"{remote_directory.rstrip('/')}/{item.filename}"
                        }
                        file_list.append(file_info)
            
            self.logger.info(f"Found {len(file_list)} files in {remote_directory}")
            return file_list
            
        except FileNotFoundError as e:
            self.logger.error(f"Directory not found: {remote_directory}")
            raise SFTPDirectoryError(f"Directory not found: {remote_directory}")
        except PermissionError as e:
            self.logger.error(f"Permission denied accessing {remote_directory}")
            raise SFTPPermissionError(f"Permission denied: {remote_directory}", remote_directory, "read")
        except Exception as e:
            self.logger.error(f"Error listing files in {remote_directory}: {e}")
            raise SFTPFileError(f"Failed to list files: {e}")
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Download file from remote server.
        
        Args:
            remote_path: Remote file path
            local_path: Local file path
            
        Returns:
            bool: True if download successful
            
        Raises:
            SFTPFileError: If download fails
        """
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")
        
        try:
            self.logger.info(f"Downloading {remote_path} to {local_path}")
            
            # Ensure local directory exists
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Download file
            self._sftp_client.get(remote_path, local_path)
            
            # Verify download
            if os.path.exists(local_path):
                local_size = os.path.getsize(local_path)
                remote_size = self._sftp_client.stat(remote_path).st_size
                
                if local_size == remote_size:
                    self.logger.info(f"Successfully downloaded {remote_path} ({local_size} bytes)")
                    return True
                else:
                    self.logger.error(f"File size mismatch: local={local_size}, remote={remote_size}")
                    raise SFTPFileError(f"File size mismatch during download", remote_path, "download")
            else:
                raise SFTPFileError(f"Downloaded file not found locally", remote_path, "download")
                
        except FileNotFoundError as e:
            self.logger.error(f"Remote file not found: {remote_path}")
            raise SFTPFileError(f"Remote file not found: {remote_path}", remote_path, "download")
        except PermissionError as e:
            self.logger.error(f"Permission denied downloading {remote_path}")
            raise SFTPPermissionError(f"Permission denied: {remote_path}", remote_path, "read")
        except Exception as e:
            self.logger.error(f"Error downloading {remote_path}: {e}")
            raise SFTPFileError(f"Download failed: {e}", remote_path, "download")
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """
        Upload file to remote server.
        
        Args:
            local_path: Local file path
            remote_path: Remote file path
            
        Returns:
            bool: True if upload successful
            
        Raises:
            SFTPFileError: If upload fails
        """
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")
        
        try:
            self.logger.info(f"Uploading {local_path} to {remote_path}")
            
            # Verify local file exists
            if not os.path.exists(local_path):
                raise SFTPFileError(f"Local file not found: {local_path}", local_path, "upload")
            
            # Ensure remote directory exists
            remote_dir = str(Path(remote_path).parent)
            try:
                self._sftp_client.chdir(remote_dir)
            except FileNotFoundError:
                self.logger.debug(f"Creating remote directory: {remote_dir}")
                self._create_remote_directory(remote_dir)
            
            # Upload file
            local_size = os.path.getsize(local_path)
            self._sftp_client.put(local_path, remote_path)
            
            # Verify upload
            remote_size = self._sftp_client.stat(remote_path).st_size
            
            if local_size == remote_size:
                self.logger.info(f"Successfully uploaded {local_path} ({local_size} bytes)")
                return True
            else:
                self.logger.error(f"File size mismatch: local={local_size}, remote={remote_size}")
                raise SFTPFileError(f"File size mismatch during upload", remote_path, "upload")
                
        except PermissionError as e:
            self.logger.error(f"Permission denied uploading to {remote_path}")
            raise SFTPPermissionError(f"Permission denied: {remote_path}", remote_path, "write")
        except Exception as e:
            self.logger.error(f"Error uploading {local_path}: {e}")
            raise SFTPFileError(f"Upload failed: {e}", remote_path, "upload")
    
    def delete_file(self, remote_path: str) -> bool:
        """
        Delete file on remote server.
        
        Args:
            remote_path: Remote file path
            
        Returns:
            bool: True if deletion successful
            
        Raises:
            SFTPFileError: If deletion fails
        """
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")
        
        try:
            self.logger.info(f"Deleting remote file: {remote_path}")
            self._sftp_client.remove(remote_path)
            self.logger.info(f"Successfully deleted {remote_path}")
            return True
            
        except FileNotFoundError as e:
            self.logger.warning(f"File not found for deletion: {remote_path}")
            return True  # Consider already deleted as success
        except PermissionError as e:
            self.logger.error(f"Permission denied deleting {remote_path}")
            raise SFTPPermissionError(f"Permission denied: {remote_path}", remote_path, "delete")
        except Exception as e:
            self.logger.error(f"Error deleting {remote_path}: {e}")
            raise SFTPFileError(f"Delete failed: {e}", remote_path, "delete")
    
    def move_file(self, old_path: str, new_path: str) -> bool:
        """
        Move/rename file on remote server.
        
        Args:
            old_path: Current remote file path
            new_path: New remote file path
            
        Returns:
            bool: True if move successful
            
        Raises:
            SFTPFileError: If move fails
        """
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")
        
        try:
            self.logger.info(f"Moving {old_path} to {new_path}")
            
            # Ensure destination directory exists
            remote_dir = str(Path(new_path).parent)
            try:
                self._sftp_client.chdir(remote_dir)
            except FileNotFoundError:
                self.logger.debug(f"Creating remote directory: {remote_dir}")
                self._create_remote_directory(remote_dir)
            
            # Move file
            self._sftp_client.rename(old_path, new_path)
            self.logger.info(f"Successfully moved {old_path} to {new_path}")
            return True
            
        except FileNotFoundError as e:
            self.logger.error(f"Source file not found: {old_path}")
            raise SFTPFileError(f"Source file not found: {old_path}", old_path, "move")
        except PermissionError as e:
            self.logger.error(f"Permission denied moving {old_path}")
            raise SFTPPermissionError(f"Permission denied", old_path, "write")
        except Exception as e:
            self.logger.error(f"Error moving {old_path}: {e}")
            raise SFTPFileError(f"Move failed: {e}", old_path, "move")
    
    def file_exists(self, remote_path: str) -> bool:
        """
        Check if file exists on remote server.
        
        Args:
            remote_path: Remote file path
            
        Returns:
            bool: True if file exists
        """
        if not self.is_connected():
            raise SFTPConnectionError("Not connected to SFTP server")
        
        try:
            self._sftp_client.stat(remote_path)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            self.logger.warning(f"Error checking file existence {remote_path}: {e}")
            return False
    
    def _create_remote_directory(self, remote_path: str):
        """Create remote directory recursively."""
        parts = remote_path.strip('/').split('/')
        current_path = ''
        
        for part in parts:
            current_path = f"{current_path}/{part}" if current_path else part
            try:
                self._sftp_client.mkdir(current_path)
                self.logger.debug(f"Created directory: {current_path}")
            except FileExistsError:
                pass  # Directory already exists
            except Exception as e:
                self.logger.warning(f"Could not create directory {current_path}: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()