"""
SFTP module for X12 EDI trading partner file exchange.

This module provides functionality to:
- Connect to trading partner SFTP servers
- Fetch inbound X12 files
- Push outbound processed files and acknowledgments
- Handle authentication and security
- Manage file lifecycle and error handling
"""

from .connector import SFTPConnector
from .manager import TradingPartnerManager
from .exceptions import SFTPConnectionError, SFTPAuthenticationError, SFTPFileError

__version__ = "1.0.0"
__all__ = [
    "SFTPConnector",
    "TradingPartnerManager", 
    "SFTPConnectionError",
    "SFTPAuthenticationError",
    "SFTPFileError"
]