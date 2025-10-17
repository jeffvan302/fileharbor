"""
FileHarbor Exception Hierarchy

All custom exceptions for the FileHarbor library.
"""


class FileHarborException(Exception):
    """Base exception for all FileHarbor errors."""
    
    def __init__(self, message: str, details: dict = None):
        """
        Initialize FileHarbor exception.
        
        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            details_str = ', '.join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


# ============================================================================
# Connection Errors
# ============================================================================

class ConnectionError(FileHarborException):
    """Base class for connection-related errors."""
    pass


class AuthenticationError(ConnectionError):
    """Raised when client authentication fails."""
    pass


class CertificateError(ConnectionError):
    """Raised when certificate validation fails."""
    pass


class NetworkError(ConnectionError):
    """Raised when network communication fails."""
    pass


class TimeoutError(ConnectionError):
    """Raised when an operation times out."""
    pass


class ServerUnavailableError(ConnectionError):
    """Raised when the server is not reachable."""
    pass


# ============================================================================
# Transfer Errors
# ============================================================================

class TransferError(FileHarborException):
    """Base class for file transfer errors."""
    pass


class ChecksumMismatchError(TransferError):
    """Raised when file checksum validation fails."""
    
    def __init__(self, expected: str, actual: str, filepath: str = None):
        details = {
            'expected': expected,
            'actual': actual,
        }
        if filepath:
            details['filepath'] = filepath
        super().__init__(
            f"Checksum mismatch: expected {expected[:16]}..., got {actual[:16]}...",
            details
        )


class FileLockedError(TransferError):
    """Raised when attempting to access a locked file."""
    pass


class DiskFullError(TransferError):
    """Raised when server disk is full."""
    pass


class TransferInterruptedError(TransferError):
    """Raised when a transfer is interrupted unexpectedly."""
    pass


class PartialTransferError(TransferError):
    """Raised when a partial transfer cannot be resumed."""
    pass


# ============================================================================
# Configuration Errors
# ============================================================================

class ConfigurationError(FileHarborException):
    """Base class for configuration-related errors."""
    pass


class InvalidConfigError(ConfigurationError):
    """Raised when configuration validation fails."""
    pass


class ConfigVersionError(ConfigurationError):
    """Raised when config version is incompatible."""
    
    def __init__(self, found_version: str, required_version: str):
        super().__init__(
            f"Config version {found_version} is incompatible. "
            f"Requires version {required_version} or higher.",
            {'found_version': found_version, 'required_version': required_version}
        )


class DecryptionError(ConfigurationError):
    """Raised when config file decryption fails."""
    pass


class EncryptionError(ConfigurationError):
    """Raised when config file encryption fails."""
    pass


class MissingConfigError(ConfigurationError):
    """Raised when required configuration is missing."""
    pass


# ============================================================================
# Operation Errors
# ============================================================================

class OperationError(FileHarborException):
    """Base class for file operation errors."""
    pass


class FileNotFoundError(OperationError):
    """Raised when a requested file doesn't exist."""
    pass


class FileExistsError(OperationError):
    """Raised when a file already exists and shouldn't be overwritten."""
    pass


class PermissionDeniedError(OperationError):
    """Raised when client lacks permission for an operation."""
    pass


class PathTraversalError(OperationError):
    """Raised when a path traversal attack is detected."""
    
    def __init__(self, attempted_path: str):
        super().__init__(
            f"Path traversal attempt detected: {attempted_path}",
            {'attempted_path': attempted_path}
        )


class InvalidPathError(OperationError):
    """Raised when a file path is invalid."""
    pass


class DirectoryNotEmptyError(OperationError):
    """Raised when attempting to remove a non-empty directory."""
    pass


# ============================================================================
# Library Management Errors
# ============================================================================

class LibraryError(FileHarborException):
    """Base class for library management errors."""
    pass


class LibraryNotFoundError(LibraryError):
    """Raised when a requested library doesn't exist."""
    pass


class LibraryAccessDeniedError(LibraryError):
    """Raised when client lacks access to a library."""
    pass


class LibraryInUseError(LibraryError):
    """Raised when a library is already in use by another client."""
    pass


class LibraryPathError(LibraryError):
    """Raised when a library path is invalid or inaccessible."""
    pass


# ============================================================================
# Rate Limiting Errors
# ============================================================================

class RateLimitError(FileHarborException):
    """Base class for rate limiting errors."""
    pass


class RateLimitExceededError(RateLimitError):
    """Raised when rate limit is exceeded."""
    pass


# ============================================================================
# Protocol Errors
# ============================================================================

class ProtocolError(FileHarborException):
    """Base class for protocol-related errors."""
    pass


class InvalidMessageError(ProtocolError):
    """Raised when a protocol message is malformed."""
    pass


class UnsupportedOperationError(ProtocolError):
    """Raised when an operation is not supported."""
    pass


class ProtocolVersionError(ProtocolError):
    """Raised when protocol versions are incompatible."""
    pass


# ============================================================================
# Cryptography Errors
# ============================================================================

class CryptoError(FileHarborException):
    """Base class for cryptography errors."""
    pass


class CertificateGenerationError(CryptoError):
    """Raised when certificate generation fails."""
    pass


class CertificateValidationError(CryptoError):
    """Raised when certificate validation fails."""
    pass


class CertificateRevokedError(CryptoError):
    """Raised when a certificate has been revoked."""
    
    def __init__(self, certificate_id: str):
        super().__init__(
            f"Certificate has been revoked: {certificate_id}",
            {'certificate_id': certificate_id}
        )


class KeyGenerationError(CryptoError):
    """Raised when key generation fails."""
    pass


# ============================================================================
# Server Errors
# ============================================================================

class ServerError(FileHarborException):
    """Base class for server-side errors."""
    pass


class ServerConfigError(ServerError):
    """Raised when server configuration is invalid."""
    pass


class ServerStartupError(ServerError):
    """Raised when server fails to start."""
    pass


class ServerShutdownError(ServerError):
    """Raised when server shutdown encounters an error."""
    pass


# ============================================================================
# Client Errors
# ============================================================================

class ClientError(FileHarborException):
    """Base class for client-side errors."""
    pass


class ClientConfigError(ClientError):
    """Raised when client configuration is invalid."""
    pass


class ConnectionPoolError(ClientError):
    """Raised when connection pool encounters an error."""
    pass
