"""
FileHarbor File Operations

Handlers for file operations (PUT, GET, DELETE, LIST, MANIFEST, etc.)
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, BinaryIO

from fileharbor.common.protocol import FileInfo
from fileharbor.common.constants import (
    TEMP_FILE_PREFIX,
    PARTIAL_FILE_EXTENSION,
)
from fileharbor.common.exceptions import (
    FileNotFoundError as FHFileNotFoundError,
    FileExistsError,
    DirectoryNotEmptyError,
    InvalidPathError,
    DiskFullError,
)
from fileharbor.utils.checksum import calculate_file_checksum, ChecksumCalculator
from fileharbor.utils.file_utils import (
    get_file_size,
    get_file_mtime,
    get_file_ctime,
    set_file_times,
    ensure_directory_exists,
    safe_delete,
    safe_rename,
)


class FileOperationHandler:
    """
    Handles all file system operations for the server.
    
    Provides methods for:
    - File upload (with resume support)
    - File download (with resume support)
    - File deletion
    - File/directory rename
    - Directory operations
    - File listing
    - Manifest generation
    """
    
    def __init__(self, library_base_path: str):
        """
        Initialize file operation handler.
        
        Args:
            library_base_path: Base path for the library
        """
        self.library_base_path = Path(library_base_path)
    
    def start_upload(
        self,
        filepath: str,
        file_size: int,
        expected_checksum: str,
        resume: bool = False
    ) -> tuple[str, int]:
        """
        Start a file upload.
        
        Args:
            filepath: Absolute file path
            file_size: Expected file size
            expected_checksum: Expected SHA-256 checksum
            resume: Whether to resume an existing upload
            
        Returns:
            Tuple of (temp_filepath, resume_offset)
            
        Raises:
            FileExistsError: If file exists and resume=False
        """
        file_path = Path(filepath)
        temp_path = file_path.parent / f"{TEMP_FILE_PREFIX}{file_path.name}"
        
        # Check if resuming
        resume_offset = 0
        if resume and temp_path.exists():
            # Resume from existing temp file
            resume_offset = get_file_size(temp_path)
            if resume_offset >= file_size:
                # Already complete
                resume_offset = 0
        else:
            # Starting new upload
            if file_path.exists() and not resume:
                raise FileExistsError(f"File already exists: {filepath}")
            
            # Ensure parent directory exists
            ensure_directory_exists(file_path.parent)
            
            # Create/truncate temp file
            temp_path.touch()
        
        return str(temp_path), resume_offset
    
    def write_chunk(
        self,
        temp_filepath: str,
        offset: int,
        data: bytes
    ) -> int:
        """
        Write a chunk of data to a file.
        
        Args:
            temp_filepath: Path to temporary file
            offset: Byte offset to write at
            data: Data to write
            
        Returns:
            Number of bytes written
            
        Raises:
            DiskFullError: If disk is full
        """
        try:
            with open(temp_filepath, 'r+b') as f:
                f.seek(offset)
                bytes_written = f.write(data)
                f.flush()
                os.fsync(f.fileno())
                return bytes_written
        except OSError as e:
            if e.errno == 28:  # ENOSPC - No space left on device
                raise DiskFullError("Server disk is full")
            raise
    
    def complete_upload(
        self,
        temp_filepath: str,
        final_filepath: str,
        expected_checksum: str,
        modified_time: Optional[float] = None,
        created_time: Optional[float] = None
    ) -> None:
        """
        Complete a file upload by verifying checksum and moving to final location.
        
        Args:
            temp_filepath: Path to temporary file
            final_filepath: Final file path
            expected_checksum: Expected SHA-256 checksum
            modified_time: File modification time to set
            created_time: File creation time to set
            
        Raises:
            ChecksumMismatchError: If checksum doesn't match
        """
        temp_path = Path(temp_filepath)
        final_path = Path(final_filepath)
        
        # Verify checksum
        actual_checksum = calculate_file_checksum(temp_path)
        if actual_checksum.lower() != expected_checksum.lower():
            from fileharbor.common.exceptions import ChecksumMismatchError
            raise ChecksumMismatchError(expected_checksum, actual_checksum, final_filepath)
        
        # Move to final location
        safe_rename(temp_path, final_path)
        
        # Set file times if provided
        if modified_time is not None:
            set_file_times(final_path, modified_time=modified_time)
    
    def start_download(
        self,
        filepath: str,
        offset: int = 0
    ) -> tuple[int, str]:
        """
        Start a file download.
        
        Args:
            filepath: Absolute file path
            offset: Byte offset to start from (for resume)
            
        Returns:
            Tuple of (file_size, checksum)
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = Path(filepath)
        
        if not file_path.exists():
            raise FHFileNotFoundError(f"File not found: {filepath}")
        
        if not file_path.is_file():
            raise InvalidPathError(f"Not a file: {filepath}")
        
        file_size = get_file_size(file_path)
        checksum = calculate_file_checksum(file_path)
        
        return file_size, checksum
    
    def read_chunk(
        self,
        filepath: str,
        offset: int,
        chunk_size: int
    ) -> bytes:
        """
        Read a chunk of data from a file.
        
        Args:
            filepath: Absolute file path
            offset: Byte offset to read from
            chunk_size: Number of bytes to read
            
        Returns:
            Chunk data
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        with open(filepath, 'rb') as f:
            f.seek(offset)
            data = f.read(chunk_size)
            return data
    
    def delete_file(self, filepath: str) -> None:
        """
        Delete a file.
        
        Args:
            filepath: Absolute file path
            
        Raises:
            FileNotFoundError: If file doesn't exist
            InvalidPathError: If path is a directory
        """
        file_path = Path(filepath)
        
        if not file_path.exists():
            raise FHFileNotFoundError(f"File not found: {filepath}")
        
        if file_path.is_dir():
            raise InvalidPathError(f"Cannot delete directory with delete_file: {filepath}")
        
        safe_delete(file_path)
    
    def rename_file(self, old_path: str, new_path: str) -> None:
        """
        Rename or move a file.
        
        Args:
            old_path: Current file path
            new_path: New file path
            
        Raises:
            FileNotFoundError: If source doesn't exist
            FileExistsError: If destination exists
        """
        old_file = Path(old_path)
        new_file = Path(new_path)
        
        if not old_file.exists():
            raise FHFileNotFoundError(f"File not found: {old_path}")
        
        if new_file.exists():
            raise FileExistsError(f"Destination already exists: {new_path}")
        
        # Ensure destination directory exists
        ensure_directory_exists(new_file.parent)
        
        safe_rename(old_file, new_file)
    
    def create_directory(self, dirpath: str) -> None:
        """
        Create a directory.
        
        Args:
            dirpath: Directory path to create
            
        Raises:
            FileExistsError: If directory already exists
        """
        dir_path = Path(dirpath)
        
        if dir_path.exists():
            if dir_path.is_dir():
                raise FileExistsError(f"Directory already exists: {dirpath}")
            else:
                raise FileExistsError(f"File exists at path: {dirpath}")
        
        ensure_directory_exists(dir_path)
    
    def remove_directory(self, dirpath: str, recursive: bool = False) -> None:
        """
        Remove a directory.
        
        Args:
            dirpath: Directory path to remove
            recursive: If True, remove non-empty directories
            
        Raises:
            FileNotFoundError: If directory doesn't exist
            DirectoryNotEmptyError: If directory not empty and recursive=False
        """
        dir_path = Path(dirpath)
        
        if not dir_path.exists():
            raise FHFileNotFoundError(f"Directory not found: {dirpath}")
        
        if not dir_path.is_dir():
            raise InvalidPathError(f"Not a directory: {dirpath}")
        
        # Check if empty
        if any(dir_path.iterdir()):
            if not recursive:
                raise DirectoryNotEmptyError(f"Directory not empty: {dirpath}")
            shutil.rmtree(dir_path)
        else:
            dir_path.rmdir()
    
    def list_directory(
        self,
        dirpath: str,
        recursive: bool = False
    ) -> List[FileInfo]:
        """
        List files in a directory.
        
        Args:
            dirpath: Directory path to list
            recursive: If True, list recursively
            
        Returns:
            List of FileInfo objects
            
        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        dir_path = Path(dirpath)
        
        if not dir_path.exists():
            raise FHFileNotFoundError(f"Directory not found: {dirpath}")
        
        if not dir_path.is_dir():
            raise InvalidPathError(f"Not a directory: {dirpath}")
        
        files = []
        
        if recursive:
            for item in dir_path.rglob('*'):
                files.append(self._get_file_info(item, dir_path))
        else:
            for item in dir_path.iterdir():
                files.append(self._get_file_info(item, dir_path))
        
        return sorted(files, key=lambda x: (not x.is_directory, x.path))
    
    def get_file_info(self, filepath: str) -> FileInfo:
        """
        Get information about a file.
        
        Args:
            filepath: File path
            
        Returns:
            FileInfo object
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = Path(filepath)
        
        if not file_path.exists():
            raise FHFileNotFoundError(f"File not found: {filepath}")
        
        return self._get_file_info(file_path, self.library_base_path)
    
    def get_manifest(self, dirpath: str = "/") -> List[FileInfo]:
        """
        Get complete manifest of all files in library.
        
        Args:
            dirpath: Directory path (default: root)
            
        Returns:
            List of FileInfo objects with checksums
        """
        resolved_path = self.library_base_path / dirpath.lstrip('/')
        return self.list_directory(str(resolved_path), recursive=True)
    
    def file_exists(self, filepath: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            filepath: File path to check
            
        Returns:
            True if file exists
        """
        return Path(filepath).exists()
    
    def get_checksum(self, filepath: str) -> str:
        """
        Calculate checksum of a file.
        
        Args:
            filepath: File path
            
        Returns:
            SHA-256 checksum
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = Path(filepath)
        
        if not file_path.exists():
            raise FHFileNotFoundError(f"File not found: {filepath}")
        
        return calculate_file_checksum(file_path)
    
    def _get_file_info(self, file_path: Path, base_path: Path) -> FileInfo:
        """
        Get FileInfo for a path.
        
        Args:
            file_path: Path object
            base_path: Base library path
            
        Returns:
            FileInfo object
        """
        try:
            relative_path = file_path.relative_to(base_path)
        except ValueError:
            relative_path = file_path
        
        is_directory = file_path.is_dir()
        size = 0
        checksum = ""
        
        if not is_directory:
            try:
                size = get_file_size(file_path)
                # Calculate checksum for all files (manifest requirement)
                checksum = calculate_file_checksum(file_path)
            except (OSError, FileNotFoundError):
                pass
        
        try:
            modified_time = get_file_mtime(file_path)
            created_time = get_file_ctime(file_path)
        except (OSError, FileNotFoundError):
            import time
            modified_time = time.time()
            created_time = time.time()
        
        return FileInfo(
            path=str(relative_path),
            size=size,
            checksum=checksum,
            created_time=created_time,
            modified_time=modified_time,
            is_directory=is_directory
        )
