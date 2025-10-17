"""
FileHarbor Checksum Utilities

SHA-256 checksum calculation for file integrity verification.
"""

import hashlib
from pathlib import Path
from typing import Union, BinaryIO

from fileharbor.common.constants import CHECKSUM_BUFFER_SIZE, CHECKSUM_ALGORITHM


def calculate_file_checksum(filepath: Union[str, Path]) -> str:
    """
    Calculate SHA-256 checksum of a file.
    
    Uses streaming to handle large files without loading into memory.
    
    Args:
        filepath: Path to file
        
    Returns:
        Hex-encoded SHA-256 checksum
        
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    sha256_hash = hashlib.sha256()
    
    with open(filepath, 'rb') as f:
        # Read file in chunks to avoid loading entire file into memory
        while True:
            chunk = f.read(CHECKSUM_BUFFER_SIZE)
            if not chunk:
                break
            sha256_hash.update(chunk)
    
    return sha256_hash.hexdigest()


def calculate_stream_checksum(stream: BinaryIO, size: int = None) -> str:
    """
    Calculate SHA-256 checksum of a binary stream.
    
    Args:
        stream: Binary stream to read
        size: Optional expected size (for validation)
        
    Returns:
        Hex-encoded SHA-256 checksum
        
    Raises:
        IOError: If stream cannot be read
    """
    sha256_hash = hashlib.sha256()
    bytes_read = 0
    
    while True:
        chunk = stream.read(CHECKSUM_BUFFER_SIZE)
        if not chunk:
            break
        sha256_hash.update(chunk)
        bytes_read += len(chunk)
        
        # Check if we've read the expected amount
        if size is not None and bytes_read > size:
            raise IOError(f"Stream size exceeds expected size: {size}")
    
    # Verify we read the expected amount
    if size is not None and bytes_read != size:
        raise IOError(f"Stream size mismatch: expected {size}, got {bytes_read}")
    
    return sha256_hash.hexdigest()


def calculate_bytes_checksum(data: bytes) -> str:
    """
    Calculate SHA-256 checksum of byte data.
    
    Args:
        data: Byte data
        
    Returns:
        Hex-encoded SHA-256 checksum
    """
    return hashlib.sha256(data).hexdigest()


def verify_file_checksum(filepath: Union[str, Path], expected_checksum: str) -> bool:
    """
    Verify file checksum matches expected value.
    
    Args:
        filepath: Path to file
        expected_checksum: Expected SHA-256 checksum (hex-encoded)
        
    Returns:
        True if checksum matches, False otherwise
    """
    actual_checksum = calculate_file_checksum(filepath)
    return actual_checksum.lower() == expected_checksum.lower()


class ChecksumCalculator:
    """
    Incremental checksum calculator for streaming operations.
    
    Allows calculating checksum while processing data in chunks.
    """
    
    def __init__(self):
        """Initialize checksum calculator."""
        self._hash = hashlib.sha256()
        self._bytes_processed = 0
    
    def update(self, data: bytes) -> None:
        """
        Update checksum with new data.
        
        Args:
            data: Byte data to add to checksum
        """
        self._hash.update(data)
        self._bytes_processed += len(data)
    
    def digest(self) -> str:
        """
        Get current checksum value.
        
        Returns:
            Hex-encoded SHA-256 checksum
        """
        return self._hash.hexdigest()
    
    def bytes_processed(self) -> int:
        """
        Get total bytes processed.
        
        Returns:
            Number of bytes processed
        """
        return self._bytes_processed
    
    def reset(self) -> None:
        """Reset calculator to initial state."""
        self._hash = hashlib.sha256()
        self._bytes_processed = 0


def checksum_matches(checksum1: str, checksum2: str) -> bool:
    """
    Compare two checksums (case-insensitive).
    
    Args:
        checksum1: First checksum
        checksum2: Second checksum
        
    Returns:
        True if checksums match
    """
    return checksum1.lower() == checksum2.lower()
