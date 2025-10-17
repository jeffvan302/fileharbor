"""
FileHarbor File Utilities

File metadata extraction and manipulation utilities.
"""

import os
import shutil
from pathlib import Path
from typing import Union, Tuple, Optional
from datetime import datetime

from fileharbor.common.constants import (
    METADATA_DATE_FORMAT,
    TEMP_FILE_PREFIX,
)


# ============================================================================
# File Metadata
# ============================================================================

def get_file_size(filepath: Union[str, Path]) -> int:
    """
    Get file size in bytes.
    
    Args:
        filepath: Path to file
        
    Returns:
        File size in bytes
    """
    return os.path.getsize(filepath)


def get_file_mtime(filepath: Union[str, Path]) -> float:
    """
    Get file modification time as Unix timestamp.
    
    Args:
        filepath: Path to file
        
    Returns:
        Modification time as Unix timestamp
    """
    return os.path.getmtime(filepath)


def get_file_ctime(filepath: Union[str, Path]) -> float:
    """
    Get file creation time as Unix timestamp.
    
    On Unix systems, this is the last metadata change time.
    
    Args:
        filepath: Path to file
        
    Returns:
        Creation time as Unix timestamp
    """
    return os.path.getctime(filepath)


def set_file_times(
    filepath: Union[str, Path],
    modified_time: Optional[float] = None,
    access_time: Optional[float] = None
) -> None:
    """
    Set file access and modification times.
    
    Args:
        filepath: Path to file
        modified_time: Modification time as Unix timestamp (None = current time)
        access_time: Access time as Unix timestamp (None = current time)
    """
    if access_time is None:
        access_time = modified_time if modified_time else None
    
    if access_time is not None and modified_time is not None:
        os.utime(filepath, (access_time, modified_time))
    elif modified_time is not None:
        os.utime(filepath, (modified_time, modified_time))


def format_timestamp(timestamp: float) -> str:
    """
    Format Unix timestamp as ISO 8601 string.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        ISO 8601 formatted string
    """
    dt = datetime.utcfromtimestamp(timestamp)
    return dt.strftime(METADATA_DATE_FORMAT)


def parse_timestamp(timestamp_str: str) -> float:
    """
    Parse ISO 8601 timestamp string to Unix timestamp.
    
    Args:
        timestamp_str: ISO 8601 formatted string
        
    Returns:
        Unix timestamp
    """
    dt = datetime.strptime(timestamp_str, METADATA_DATE_FORMAT)
    return dt.timestamp()


# ============================================================================
# File Operations
# ============================================================================

def ensure_directory_exists(dirpath: Union[str, Path]) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        dirpath: Path to directory
    """
    os.makedirs(dirpath, exist_ok=True)


def is_file_locked(filepath: Union[str, Path]) -> bool:
    """
    Check if a file is locked (being written to).
    
    This is a simple check and may not be perfect across all platforms.
    
    Args:
        filepath: Path to file
        
    Returns:
        True if file appears to be locked
    """
    if not os.path.exists(filepath):
        return False
    
    # Try to open file for writing
    try:
        with open(filepath, 'a'):
            pass
        return False
    except (IOError, PermissionError):
        return True


def safe_delete(filepath: Union[str, Path]) -> bool:
    """
    Safely delete a file, ignoring errors if file doesn't exist.
    
    Args:
        filepath: Path to file
        
    Returns:
        True if file was deleted, False if it didn't exist
    """
    try:
        os.remove(filepath)
        return True
    except FileNotFoundError:
        return False


def safe_rename(old_path: Union[str, Path], new_path: Union[str, Path]) -> None:
    """
    Safely rename a file, handling cross-device moves.
    
    Args:
        old_path: Current file path
        new_path: New file path
    """
    try:
        os.rename(old_path, new_path)
    except OSError:
        # If rename fails (e.g., cross-device), use copy + delete
        shutil.copy2(old_path, new_path)
        os.remove(old_path)


def create_temp_filename(base_path: Union[str, Path], original_name: str) -> Path:
    """
    Create a temporary filename for a file being transferred.
    
    Args:
        base_path: Directory for temporary file
        original_name: Original filename
        
    Returns:
        Path to temporary file
    """
    base_path = Path(base_path)
    return base_path / f"{TEMP_FILE_PREFIX}{original_name}"


# ============================================================================
# Size Formatting
# ============================================================================

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def parse_file_size(size_str: str) -> int:
    """
    Parse human-readable file size to bytes.
    
    Args:
        size_str: Size string (e.g., "1.5 MB", "100KB")
        
    Returns:
        Size in bytes
        
    Raises:
        ValueError: If format is invalid
    """
    size_str = size_str.strip().upper()
    
    # Extract number and unit
    import re
    match = re.match(r'^([\d.]+)\s*([KMGT]?B?)$', size_str)
    if not match:
        raise ValueError(f"Invalid size format: {size_str}")
    
    number = float(match.group(1))
    unit = match.group(2) or 'B'
    
    # Convert to bytes
    multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
    }
    
    if unit not in multipliers:
        raise ValueError(f"Unknown unit: {unit}")
    
    return int(number * multipliers[unit])


# ============================================================================
# Directory Operations
# ============================================================================

def list_directory(
    dirpath: Union[str, Path],
    recursive: bool = False
) -> list[Tuple[str, bool, int]]:
    """
    List files in a directory.
    
    Args:
        dirpath: Path to directory
        recursive: If True, list recursively
        
    Returns:
        List of tuples (path, is_directory, size)
    """
    dirpath = Path(dirpath)
    results = []
    
    if recursive:
        for root, dirs, files in os.walk(dirpath):
            root_path = Path(root)
            
            # Add directories
            for dirname in dirs:
                dir_full_path = root_path / dirname
                relative_path = dir_full_path.relative_to(dirpath)
                results.append((str(relative_path), True, 0))
            
            # Add files
            for filename in files:
                file_full_path = root_path / filename
                relative_path = file_full_path.relative_to(dirpath)
                size = get_file_size(file_full_path)
                results.append((str(relative_path), False, size))
    else:
        for item in dirpath.iterdir():
            is_dir = item.is_dir()
            size = 0 if is_dir else get_file_size(item)
            results.append((item.name, is_dir, size))
    
    return sorted(results, key=lambda x: (not x[1], x[0]))  # Dirs first, then alphabetical


def get_directory_size(dirpath: Union[str, Path]) -> int:
    """
    Calculate total size of all files in directory (recursive).
    
    Args:
        dirpath: Path to directory
        
    Returns:
        Total size in bytes
    """
    total_size = 0
    for root, dirs, files in os.walk(dirpath):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                total_size += get_file_size(filepath)
            except (OSError, FileNotFoundError):
                pass  # Skip files that can't be accessed
    return total_size


def is_directory_empty(dirpath: Union[str, Path]) -> bool:
    """
    Check if a directory is empty.
    
    Args:
        dirpath: Path to directory
        
    Returns:
        True if directory is empty
    """
    return not any(Path(dirpath).iterdir())


# ============================================================================
# Path Utilities
# ============================================================================

def split_path(filepath: str) -> Tuple[str, str]:
    """
    Split a path into directory and filename.
    
    Args:
        filepath: File path
        
    Returns:
        Tuple of (directory, filename)
    """
    return os.path.split(filepath)


def join_path(*parts: str) -> str:
    """
    Join path components.
    
    Args:
        *parts: Path components
        
    Returns:
        Joined path
    """
    return os.path.join(*parts)


def get_file_extension(filepath: Union[str, Path]) -> str:
    """
    Get file extension (including the dot).
    
    Args:
        filepath: File path
        
    Returns:
        Extension (e.g., ".txt")
    """
    return Path(filepath).suffix


def get_filename_without_extension(filepath: Union[str, Path]) -> str:
    """
    Get filename without extension.
    
    Args:
        filepath: File path
        
    Returns:
        Filename without extension
    """
    return Path(filepath).stem
