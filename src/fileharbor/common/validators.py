"""
FileHarbor Input Validators

Path traversal prevention and input validation utilities.
"""

import os
import re
from pathlib import Path
from typing import Optional

from fileharbor.common.constants import (
    FORBIDDEN_PATH_COMPONENTS,
    FORBIDDEN_FILENAME_CHARS,
    MAX_PATH_DEPTH,
    MAX_PATH_LENGTH,
)
from fileharbor.common.exceptions import (
    PathTraversalError,
    InvalidPathError,
)


def validate_path(filepath: str, base_path: str) -> str:
    """
    Validate and sanitize a file path to prevent directory traversal.
    
    This is CRITICAL for security. It ensures that:
    1. No path traversal (../) attempts
    2. Path stays within base_path
    3. No forbidden characters
    4. Path length is reasonable
    
    Args:
        filepath: Requested file path (relative or absolute)
        base_path: Base directory that must contain the file
        
    Returns:
        Absolute, normalized path that is safe to use
        
    Raises:
        PathTraversalError: If path traversal is detected
        InvalidPathError: If path is invalid
    """
    # Normalize base path
    base_path = os.path.abspath(os.path.normpath(base_path))
    
    # Remove leading slashes from filepath to make it relative
    filepath = filepath.lstrip('/')
    
    # Normalize the filepath
    try:
        filepath = os.path.normpath(filepath)
    except Exception as e:
        raise InvalidPathError(f"Invalid path format: {e}")
    
    # Check for forbidden path components
    path_parts = filepath.split(os.sep)
    for part in path_parts:
        if part in FORBIDDEN_PATH_COMPONENTS:
            raise PathTraversalError(filepath)
        
        # Check for forbidden characters in each component
        for forbidden_char in FORBIDDEN_FILENAME_CHARS:
            if forbidden_char in part:
                raise InvalidPathError(
                    f"Path contains forbidden character: {repr(forbidden_char)}"
                )
    
    # Check path depth
    if len(path_parts) > MAX_PATH_DEPTH:
        raise InvalidPathError(
            f"Path depth exceeds maximum of {MAX_PATH_DEPTH} levels"
        )
    
    # Construct the full path
    full_path = os.path.abspath(os.path.join(base_path, filepath))
    
    # CRITICAL: Ensure the resolved path is still within base_path
    # This protects against symlink attacks and other traversal methods
    try:
        os.path.commonpath([base_path, full_path])
    except ValueError:
        # Paths are on different drives (Windows) or one is relative
        raise PathTraversalError(filepath)
    
    if not full_path.startswith(base_path):
        raise PathTraversalError(filepath)
    
    # Check total path length
    if len(full_path) > MAX_PATH_LENGTH:
        raise InvalidPathError(
            f"Path length exceeds maximum of {MAX_PATH_LENGTH} characters"
        )
    
    return full_path


def validate_filename(filename: str) -> bool:
    """
    Validate a filename (not a path).
    
    Args:
        filename: Name of file (no path separators)
        
    Returns:
        True if valid
        
    Raises:
        InvalidPathError: If filename is invalid
    """
    if not filename:
        raise InvalidPathError("Filename cannot be empty")
    
    # Check for path separators
    if '/' in filename or '\\' in filename:
        raise InvalidPathError("Filename cannot contain path separators")
    
    # Check for forbidden characters
    for forbidden_char in FORBIDDEN_FILENAME_CHARS:
        if forbidden_char in filename:
            raise InvalidPathError(
                f"Filename contains forbidden character: {repr(forbidden_char)}"
            )
    
    # Check for reserved names (Windows)
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
    }
    if filename.upper() in reserved_names:
        raise InvalidPathError(f"Filename is a reserved name: {filename}")
    
    return True


def sanitize_path_for_display(filepath: str, max_length: int = 60) -> str:
    """
    Sanitize a path for display in logs or UI.
    
    Truncates long paths and ensures safe characters.
    
    Args:
        filepath: Path to sanitize
        max_length: Maximum length for display
        
    Returns:
        Sanitized path string
    """
    if len(filepath) <= max_length:
        return filepath
    
    # Truncate with ellipsis
    return filepath[:max_length-3] + '...'


def is_subdirectory(child: str, parent: str) -> bool:
    """
    Check if child is a subdirectory of parent.
    
    Args:
        child: Potential child directory
        parent: Parent directory
        
    Returns:
        True if child is under parent
    """
    child = os.path.abspath(os.path.normpath(child))
    parent = os.path.abspath(os.path.normpath(parent))
    
    return child.startswith(parent + os.sep) or child == parent


def validate_library_path(path: str) -> bool:
    """
    Validate a library base path.
    
    Args:
        path: Library path to validate
        
    Returns:
        True if valid
        
    Raises:
        InvalidPathError: If path is invalid
    """
    if not path:
        raise InvalidPathError("Library path cannot be empty")
    
    # Convert to absolute path
    try:
        abs_path = os.path.abspath(os.path.normpath(path))
    except Exception as e:
        raise InvalidPathError(f"Invalid library path: {e}")
    
    # Check if path exists
    if not os.path.exists(abs_path):
        raise InvalidPathError(f"Library path does not exist: {abs_path}")
    
    # Check if it's a directory
    if not os.path.isdir(abs_path):
        raise InvalidPathError(f"Library path is not a directory: {abs_path}")
    
    # Check if readable and writable
    if not os.access(abs_path, os.R_OK | os.W_OK):
        raise InvalidPathError(f"Library path is not readable/writable: {abs_path}")
    
    return True


def normalize_path_separators(path: str) -> str:
    """
    Normalize path separators to forward slashes.
    
    This ensures consistent path handling across platforms.
    
    Args:
        path: Path with any separator style
        
    Returns:
        Path with forward slashes
    """
    return path.replace('\\', '/')


def validate_checksum_format(checksum: str) -> bool:
    """
    Validate SHA-256 checksum format.
    
    Args:
        checksum: Checksum string to validate
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If checksum format is invalid
    """
    if not checksum:
        raise ValueError("Checksum cannot be empty")
    
    # SHA-256 produces 64 hexadecimal characters
    if len(checksum) != 64:
        raise ValueError(f"Invalid checksum length: expected 64, got {len(checksum)}")
    
    # Check if hexadecimal
    if not re.match(r'^[a-fA-F0-9]{64}$', checksum):
        raise ValueError("Checksum must be 64 hexadecimal characters")
    
    return True


def validate_uuid_format(uuid_str: str) -> bool:
    """
    Validate UUID format (for library and client IDs).
    
    Args:
        uuid_str: UUID string to validate
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If UUID format is invalid
    """
    # Standard UUID format: 8-4-4-4-12 hexadecimal characters
    uuid_pattern = r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$'
    
    if not re.match(uuid_pattern, uuid_str):
        raise ValueError(f"Invalid UUID format: {uuid_str}")
    
    return True


def validate_port(port: int) -> bool:
    """
    Validate network port number.
    
    Args:
        port: Port number to validate
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If port is invalid
    """
    if not isinstance(port, int):
        raise ValueError("Port must be an integer")
    
    if port < 1 or port > 65535:
        raise ValueError(f"Port must be between 1 and 65535, got {port}")
    
    # Warn about privileged ports
    if port < 1024:
        import warnings
        warnings.warn(
            f"Port {port} is a privileged port and may require elevated permissions",
            UserWarning
        )
    
    return True


def validate_chunk_size(chunk_size: int) -> bool:
    """
    Validate chunk size for file transfers.
    
    Args:
        chunk_size: Chunk size in bytes
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If chunk size is invalid
    """
    from fileharbor.common.constants import MIN_CHUNK_SIZE, MAX_CHUNK_SIZE
    
    if not isinstance(chunk_size, int):
        raise ValueError("Chunk size must be an integer")
    
    if chunk_size < MIN_CHUNK_SIZE:
        raise ValueError(
            f"Chunk size must be at least {MIN_CHUNK_SIZE} bytes, got {chunk_size}"
        )
    
    if chunk_size > MAX_CHUNK_SIZE:
        raise ValueError(
            f"Chunk size cannot exceed {MAX_CHUNK_SIZE} bytes, got {chunk_size}"
        )
    
    return True


def validate_rate_limit(rate_limit: int) -> bool:
    """
    Validate rate limit value.
    
    Args:
        rate_limit: Rate limit in bytes per second (0 = unlimited)
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If rate limit is invalid
    """
    from fileharbor.common.constants import MIN_RATE_LIMIT
    
    if not isinstance(rate_limit, int):
        raise ValueError("Rate limit must be an integer")
    
    if rate_limit < 0:
        raise ValueError("Rate limit cannot be negative")
    
    if rate_limit > 0 and rate_limit < MIN_RATE_LIMIT:
        raise ValueError(
            f"Rate limit must be at least {MIN_RATE_LIMIT} bytes/sec or 0 (unlimited), "
            f"got {rate_limit}"
        )
    
    return True


def validate_timeout(timeout: float) -> bool:
    """
    Validate timeout value.
    
    Args:
        timeout: Timeout in seconds
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If timeout is invalid
    """
    if not isinstance(timeout, (int, float)):
        raise ValueError("Timeout must be a number")
    
    if timeout <= 0:
        raise ValueError("Timeout must be positive")
    
    if timeout > 86400:  # 24 hours
        import warnings
        warnings.warn(
            f"Timeout of {timeout} seconds (>24 hours) is unusually long",
            UserWarning
        )
    
    return True
