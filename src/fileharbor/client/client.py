"""
FileHarbor Synchronous Client

High-level synchronous API for FileHarbor client operations.
"""

from pathlib import Path
from typing import Optional, List

from fileharbor.common.config_schema import ClientConfig
from fileharbor.common.protocol import (
    create_response,
    FileInfo,
)
from fileharbor.common.constants import (
    CMD_DELETE,
    CMD_RENAME,
    CMD_LIST,
    CMD_MKDIR,
    CMD_RMDIR,
    CMD_MANIFEST,
    CMD_CHECKSUM,
    CMD_STAT,
    CMD_EXISTS,
    CMD_PING,
)
from fileharbor.common.exceptions import (
    FileHarborException,
    ConnectionError as FHConnectionError,
)

from fileharbor.client.config import load_client_config, validate_client_config
from fileharbor.client.connection import Connection
from fileharbor.client.transfer_manager import TransferManager
from fileharbor.client.progress import ProgressCallback, create_console_progress_callback


class FileHarborClient:
    """
    Synchronous client for FileHarbor server.
    
    Provides high-level API for file operations with automatic
    connection management, resumable transfers, and progress tracking.
    
    Usage:
        with FileHarborClient('client_config.json') as client:
            client.upload('local.txt', 'remote.txt')
            client.download('remote.txt', 'copy.txt')
    """
    
    def __init__(
        self,
        config: str | ClientConfig,
        password: Optional[str] = None,
        auto_connect: bool = False
    ):
        """
        Initialize client.
        
        Args:
            config: Path to config file or ClientConfig object
            password: Password for encrypted config
            auto_connect: Connect immediately
        """
        # Load configuration
        if isinstance(config, str):
            self.config = load_client_config(config, password)
        else:
            self.config = config
        
        validate_client_config(self.config)
        
        # Initialize components
        self.connection: Optional[Connection] = None
        self.transfer_manager: Optional[TransferManager] = None
        self._connected = False
        
        if auto_connect:
            self.connect()
    
    def connect(self) -> None:
        """
        Connect to server.
        
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        if self._connected:
            return
        
        self.connection = Connection(self.config)
        self.connection.connect()
        
        self.transfer_manager = TransferManager(
            self.connection,
            chunk_size=self.config.transfer.chunk_size
        )
        
        self._connected = True
    
    def disconnect(self) -> None:
        """Disconnect from server gracefully."""
        if self.connection:
            self.connection.disconnect()
        
        self.connection = None
        self.transfer_manager = None
        self._connected = False
    
    def is_connected(self) -> bool:
        """
        Check if connected to server.
        
        Returns:
            True if connected
        """
        return self._connected and self.connection is not None
    
    def ping(self) -> bool:
        """
        Ping server to check connection.
        
        Returns:
            True if server responds
        """
        self._ensure_connected()
        return self.connection.ping()
    
    def upload(
        self,
        local_path: str,
        remote_path: str,
        resume: bool = True,
        progress_callback: Optional[ProgressCallback] = None,
        show_progress: bool = False
    ) -> None:
        """
        Upload a file to the server.
        
        Args:
            local_path: Local file path
            remote_path: Remote file path
            resume: Resume if partial upload exists
            progress_callback: Custom progress callback
            show_progress: Show console progress bar
            
        Raises:
            FileNotFoundError: If local file doesn't exist
            FileTransferError: If upload fails
        """
        self._ensure_connected()
        
        # Use console callback if requested
        if show_progress and not progress_callback:
            progress_callback = create_console_progress_callback()
        
        self.transfer_manager.upload_file(
            local_path,
            remote_path,
            resume=resume,
            progress_callback=progress_callback
        )
    
    def download(
        self,
        remote_path: str,
        local_path: str,
        resume: bool = True,
        progress_callback: Optional[ProgressCallback] = None,
        show_progress: bool = False
    ) -> None:
        """
        Download a file from the server.
        
        Args:
            remote_path: Remote file path
            local_path: Local file path
            resume: Resume if partial download exists
            progress_callback: Custom progress callback
            show_progress: Show console progress bar
            
        Raises:
            FileNotFoundError: If remote file doesn't exist
            FileTransferError: If download fails
            ChecksumMismatchError: If checksum verification fails
        """
        self._ensure_connected()
        
        # Use console callback if requested
        if show_progress and not progress_callback:
            progress_callback = create_console_progress_callback()
        
        self.transfer_manager.download_file(
            remote_path,
            local_path,
            resume=resume,
            progress_callback=progress_callback
        )
    
    def upload_with_retry(
        self,
        local_path: str,
        remote_path: str,
        max_retries: int = 3,
        progress_callback: Optional[ProgressCallback] = None,
        show_progress: bool = False
    ) -> None:
        """
        Upload a file with automatic retry on failure.
        
        Args:
            local_path: Local file path
            remote_path: Remote file path
            max_retries: Maximum retry attempts
            progress_callback: Custom progress callback
            show_progress: Show console progress bar
        """
        self._ensure_connected()
        
        if show_progress and not progress_callback:
            progress_callback = create_console_progress_callback()
        
        self.transfer_manager.upload_with_retry(
            local_path,
            remote_path,
            max_retries=max_retries,
            progress_callback=progress_callback
        )
    
    def download_with_retry(
        self,
        remote_path: str,
        local_path: str,
        max_retries: int = 3,
        progress_callback: Optional[ProgressCallback] = None,
        show_progress: bool = False
    ) -> None:
        """
        Download a file with automatic retry on failure.
        
        Args:
            remote_path: Remote file path
            local_path: Local file path
            max_retries: Maximum retry attempts
            progress_callback: Custom progress callback
            show_progress: Show console progress bar
        """
        self._ensure_connected()
        
        if show_progress and not progress_callback:
            progress_callback = create_console_progress_callback()
        
        self.transfer_manager.download_with_retry(
            remote_path,
            local_path,
            max_retries=max_retries,
            progress_callback=progress_callback
        )
    
    def delete(self, remote_path: str) -> None:
        """
        Delete a file on the server.
        
        Args:
            remote_path: Remote file path
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        self._ensure_connected()
        
        msg = create_response(CMD_DELETE, filepath=remote_path)
        self.connection.send_message(msg)
        self.connection.receive_message()
    
    def rename(self, old_path: str, new_path: str) -> None:
        """
        Rename or move a file on the server.
        
        Args:
            old_path: Current file path
            new_path: New file path
            
        Raises:
            FileNotFoundError: If file doesn't exist
            FileExistsError: If destination exists
        """
        self._ensure_connected()
        
        msg = create_response(CMD_RENAME, old_path=old_path, new_path=new_path)
        self.connection.send_message(msg)
        self.connection.receive_message()
    
    def list_directory(
        self,
        remote_path: str = '/',
        recursive: bool = False
    ) -> List[FileInfo]:
        """
        List files in a directory.
        
        Args:
            remote_path: Directory path
            recursive: List recursively
            
        Returns:
            List of FileInfo objects
            
        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        self._ensure_connected()
        
        msg = create_response(
            CMD_LIST,
            dirpath=remote_path,
            recursive=recursive
        )
        self.connection.send_message(msg)
        response = self.connection.receive_message()
        
        files_data = response.content.get('files', [])
        return [
            FileInfo(
                path=f['path'],
                size=f['size'],
                is_directory=f['is_directory'],
                modified_time=f['modified_time'],
                checksum=f.get('checksum', ''),
                created_time=f.get('created_time', 0)
            )
            for f in files_data
        ]
    
    def mkdir(self, remote_path: str) -> None:
        """
        Create a directory on the server.
        
        Args:
            remote_path: Directory path
            
        Raises:
            FileExistsError: If directory already exists
        """
        self._ensure_connected()
        
        msg = create_response(CMD_MKDIR, dirpath=remote_path)
        self.connection.send_message(msg)
        self.connection.receive_message()
    
    def rmdir(self, remote_path: str, recursive: bool = False) -> None:
        """
        Remove a directory on the server.
        
        Args:
            remote_path: Directory path
            recursive: Remove non-empty directories
            
        Raises:
            FileNotFoundError: If directory doesn't exist
            DirectoryNotEmptyError: If not empty and recursive=False
        """
        self._ensure_connected()
        
        msg = create_response(
            CMD_RMDIR,
            dirpath=remote_path,
            recursive=recursive
        )
        self.connection.send_message(msg)
        self.connection.receive_message()
    
    def get_manifest(self, remote_path: str = '/') -> List[FileInfo]:
        """
        Get complete file manifest with checksums.
        
        Args:
            remote_path: Starting directory path
            
        Returns:
            List of FileInfo objects with checksums
        """
        self._ensure_connected()
        
        msg = create_response(CMD_MANIFEST, dirpath=remote_path)
        self.connection.send_message(msg)
        response = self.connection.receive_message()
        
        files_data = response.content.get('files', [])
        return [
            FileInfo(
                path=f['path'],
                size=f['size'],
                checksum=f.get('checksum', ''),
                is_directory=f['is_directory'],
                modified_time=f['modified_time'],
                created_time=f.get('created_time', 0)
            )
            for f in files_data
        ]
    
    def get_checksum(self, remote_path: str) -> str:
        """
        Calculate checksum of a remote file.
        
        Args:
            remote_path: Remote file path
            
        Returns:
            SHA-256 checksum
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        self._ensure_connected()
        
        msg = create_response(CMD_CHECKSUM, filepath=remote_path)
        self.connection.send_message(msg)
        response = self.connection.receive_message()
        
        return response.content.get('checksum', '')
    
    def stat(self, remote_path: str) -> FileInfo:
        """
        Get file statistics.
        
        Args:
            remote_path: Remote file path
            
        Returns:
            FileInfo object
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        self._ensure_connected()
        
        msg = create_response(CMD_STAT, filepath=remote_path)
        self.connection.send_message(msg)
        response = self.connection.receive_message()
        
        return FileInfo(
            path=response.content.get('path', ''),
            size=response.content.get('size', 0),
            checksum=response.content.get('checksum', ''),
            is_directory=response.content.get('is_directory', False),
            modified_time=response.content.get('modified_time', 0),
            created_time=response.content.get('created_time', 0)
        )
    
    def exists(self, remote_path: str) -> bool:
        """
        Check if a file exists on the server.
        
        Args:
            remote_path: Remote file path
            
        Returns:
            True if file exists
        """
        self._ensure_connected()
        
        msg = create_response(CMD_EXISTS, filepath=remote_path)
        self.connection.send_message(msg)
        response = self.connection.receive_message()
        
        return response.content.get('exists', False)
    
    def _ensure_connected(self) -> None:
        """
        Ensure client is connected.
        
        Raises:
            ConnectionError: If not connected
        """
        if not self.is_connected():
            raise FHConnectionError("Not connected to server. Call connect() first.")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
