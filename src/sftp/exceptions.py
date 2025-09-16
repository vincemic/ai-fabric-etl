"""
Custom exceptions for SFTP operations.
"""


class SFTPError(Exception):
    """Base exception for SFTP operations."""
    pass


class SFTPConnectionError(SFTPError):
    """Raised when SFTP connection fails."""
    
    def __init__(self, message: str, host: str = None, port: int = None):
        super().__init__(message)
        self.host = host
        self.port = port
        

class SFTPAuthenticationError(SFTPError):
    """Raised when SFTP authentication fails."""
    
    def __init__(self, message: str, username: str = None):
        super().__init__(message)
        self.username = username


class SFTPFileError(SFTPError):
    """Raised when SFTP file operations fail."""
    
    def __init__(self, message: str, filename: str = None, operation: str = None):
        super().__init__(message)
        self.filename = filename
        self.operation = operation


class SFTPDirectoryError(SFTPError):
    """Raised when SFTP directory operations fail."""
    
    def __init__(self, message: str, directory: str = None):
        super().__init__(message)
        self.directory = directory


class SFTPPermissionError(SFTPError):
    """Raised when SFTP permission errors occur."""
    
    def __init__(self, message: str, path: str = None, required_permission: str = None):
        super().__init__(message)
        self.path = path
        self.required_permission = required_permission


"""
Custom exceptions for SFTP operations.
"""


class SFTPError(Exception):
    """Base exception for SFTP operations."""
    pass


class SFTPConnectionError(SFTPError):
    """Raised when SFTP connection fails."""
    
    def __init__(self, message: str, host: str = None, port: int = None):
        super().__init__(message)
        self.host = host
        self.port = port
        

class SFTPAuthenticationError(SFTPError):
    """Raised when SFTP authentication fails."""
    
    def __init__(self, message: str, username: str = None):
        super().__init__(message)
        self.username = username


class SFTPFileError(SFTPError):
    """Raised when SFTP file operations fail."""
    
    def __init__(self, message: str, filename: str = None, operation: str = None):
        super().__init__(message)
        self.filename = filename
        self.operation = operation


class SFTPDirectoryError(SFTPError):
    """Raised when SFTP directory operations fail."""
    
    def __init__(self, message: str, directory: str = None):
        super().__init__(message)
        self.directory = directory


class SFTPPermissionError(SFTPError):
    """Raised when SFTP permission errors occur."""
    
    def __init__(self, message: str, path: str = None, required_permission: str = None):
        super().__init__(message)
        self.path = path
        self.required_permission = required_permission


class SFTPTimeoutError(SFTPError):
    """Raised when SFTP operations timeout."""
    
    def __init__(self, message: str, timeout_seconds: int = None):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


class SFTPConfigurationError(SFTPError):
    """Raised when SFTP configuration is invalid."""
    
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message)
        self.config_key = config_key


class PGPError(SFTPError):
    """Base exception for PGP operations."""
    pass


class PGPKeyError(PGPError):
    """Raised when PGP key operations fail."""
    
    def __init__(self, message: str, key_id: str = None, operation: str = None):
        super().__init__(message)
        self.key_id = key_id
        self.operation = operation


class PGPEncryptionError(PGPError):
    """Raised when PGP encryption fails."""
    
    def __init__(self, message: str, recipient: str = None):
        super().__init__(message)
        self.recipient = recipient


class PGPDecryptionError(PGPError):
    """Raised when PGP decryption fails."""
    
    def __init__(self, message: str, key_id: str = None):
        super().__init__(message)
        self.key_id = key_id


class PGPSignatureError(PGPError):
    """Raised when PGP signature operations fail."""
    
    def __init__(self, message: str, signer: str = None, verification_status: bool = None):
        super().__init__(message)
        self.signer = signer
        self.verification_status = verification_status