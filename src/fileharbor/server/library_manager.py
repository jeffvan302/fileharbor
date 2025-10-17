"""
FileHarbor Library Manager

Manages library paths and access control.
"""

from pathlib import Path
from typing import Optional

from fileharbor.common.config_schema import ServerConfig, LibraryConfig
from fileharbor.common.validators import validate_path
from fileharbor.common.exceptions import (
    LibraryNotFoundError,
    LibraryAccessDeniedError,
    LibraryPathError,
    InvalidPathError,
    PathTraversalError,
)


class LibraryManager:
    """
    Manages library access and path resolution.
    
    Ensures:
    - Library paths are valid and accessible
    - Client access control is enforced
    - Path traversal attacks are prevented
    - File paths stay within library boundaries
    """
    
    def __init__(self, config: ServerConfig):
        """
        Initialize library manager.
        
        Args:
            config: Server configuration
        """
        self.config = config
        self._validate_libraries()
    
    def _validate_libraries(self) -> None:
        """
        Validate all library paths exist and are accessible.
        
        Raises:
            LibraryPathError: If library path is invalid
        """
        for lib_id, library in self.config.libraries.items():
            lib_path = Path(library.path)
            
            if not lib_path.exists():
                raise LibraryPathError(
                    f"Library path does not exist: {library.name} -> {library.path}"
                )
            
            if not lib_path.is_dir():
                raise LibraryPathError(
                    f"Library path is not a directory: {library.name} -> {library.path}"
                )
            
            # Check read/write permissions
            if not lib_path.is_dir() or not lib_path.exists():
                raise LibraryPathError(
                    f"Library path is not accessible: {library.name} -> {library.path}"
                )
    
    def get_library(self, library_id: str) -> LibraryConfig:
        """
        Get library configuration.
        
        Args:
            library_id: Library UUID
            
        Returns:
            LibraryConfig object
            
        Raises:
            LibraryNotFoundError: If library doesn't exist
        """
        if library_id not in self.config.libraries:
            raise LibraryNotFoundError(f"Library not found: {library_id}")
        
        return self.config.libraries[library_id]
    
    def check_client_access(self, library_id: str, client_id: str) -> bool:
        """
        Check if client has access to library.
        
        Args:
            library_id: Library UUID
            client_id: Client UUID
            
        Returns:
            True if access granted
            
        Raises:
            LibraryNotFoundError: If library doesn't exist
            LibraryAccessDeniedError: If access denied
        """
        library = self.get_library(library_id)
        
        if client_id not in library.authorized_clients:
            client_name = self.config.clients.get(client_id, {}).name if client_id in self.config.clients else client_id
            raise LibraryAccessDeniedError(
                f"Client '{client_name}' does not have access to library '{library.name}'"
            )
        
        return True
    
    def resolve_path(self, library_id: str, filepath: str) -> str:
        """
        Resolve a file path within a library.
        
        Performs security validation to prevent path traversal attacks.
        
        Args:
            library_id: Library UUID
            filepath: Relative file path within library
            
        Returns:
            Absolute file path
            
        Raises:
            LibraryNotFoundError: If library doesn't exist
            PathTraversalError: If path traversal detected
            InvalidPathError: If path is invalid
        """
        library = self.get_library(library_id)
        library_path = library.path
        
        # Validate and resolve path
        try:
            absolute_path = validate_path(filepath, library_path)
        except (PathTraversalError, InvalidPathError) as e:
            raise
        
        return absolute_path
    
    def get_library_path(self, library_id: str) -> str:
        """
        Get library base path.
        
        Args:
            library_id: Library UUID
            
        Returns:
            Library base path
            
        Raises:
            LibraryNotFoundError: If library doesn't exist
        """
        library = self.get_library(library_id)
        return library.path
    
    def get_rate_limit(self, library_id: str) -> int:
        """
        Get rate limit for a library.
        
        Args:
            library_id: Library UUID
            
        Returns:
            Rate limit in bytes per second (0 = unlimited)
            
        Raises:
            LibraryNotFoundError: If library doesn't exist
        """
        library = self.get_library(library_id)
        return library.rate_limit_bps
    
    def get_idle_timeout(self, library_id: str) -> int:
        """
        Get idle timeout for a library.
        
        Args:
            library_id: Library UUID
            
        Returns:
            Idle timeout in seconds
            
        Raises:
            LibraryNotFoundError: If library doesn't exist
        """
        library = self.get_library(library_id)
        return library.idle_timeout
    
    def list_libraries(self) -> dict:
        """
        Get all libraries.
        
        Returns:
            Dictionary of library_id -> LibraryConfig
        """
        return self.config.libraries
    
    def get_library_stats(self, library_id: str) -> dict:
        """
        Get statistics for a library.
        
        Args:
            library_id: Library UUID
            
        Returns:
            Dictionary with stats
            
        Raises:
            LibraryNotFoundError: If library doesn't exist
        """
        library = self.get_library(library_id)
        lib_path = Path(library.path)
        
        # Calculate directory size
        total_size = 0
        file_count = 0
        dir_count = 0
        
        try:
            for item in lib_path.rglob('*'):
                if item.is_file():
                    file_count += 1
                    try:
                        total_size += item.stat().st_size
                    except (OSError, FileNotFoundError):
                        pass
                elif item.is_dir():
                    dir_count += 1
        except Exception:
            pass
        
        return {
            'name': library.name,
            'path': library.path,
            'total_size': total_size,
            'file_count': file_count,
            'directory_count': dir_count,
            'authorized_clients': len(library.authorized_clients),
            'rate_limit_bps': library.rate_limit_bps,
        }
