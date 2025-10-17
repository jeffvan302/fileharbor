"""
FileHarbor Async Client

High-level asynchronous API for FileHarbor client operations.
"""

import asyncio
from pathlib import Path
from typing import Optional, List

from fileharbor.common.config_schema import ClientConfig
from fileharbor.common.protocol import FileInfo
from fileharbor.common.exceptions import (
    FileHarborException,
    ConnectionError as FHConnectionError,
)

from fileharbor.client.config import load_client_config, validate_client_config
from fileharbor.client.connection import Connection
from fileharbor.client.transfer_manager import TransferManager
from fileharbor.client.progress import ProgressCallback, create_console_progress_callback


class AsyncFileHarborClient:
    """
    Asynchronous client for FileHarbor server.
    
    Provides high-level async API for file operations with automatic
    connection management, resumable transfers, and progress tracking.
    
    Usage:
        async with AsyncFileHarborClient('client_config.json') as client:
            await client.upload_async('local.txt', 'remote.txt')
            await client.download_async('remote.txt', 'copy.txt')
    """
    
    def __init__(
        self,
        config: str | ClientConfig,
        password: Optional[str] = None,
        auto_connect: bool = False
    ):
        """
        Initialize async client.
        
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
        self._lock = asyncio.Lock()
        
        if auto_connect:
            # Note: Can't actually connect in __init__ for async
            # User should call connect_async() or use context manager
            pass
    
    async def connect_async(self) -> None:
        """
        Connect to server asynchronously.
        
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        async with self._lock:
            if self._connected:
                return
            
            # Run sync connect in executor
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._sync_connect
            )
    
    def _sync_connect(self) -> None:
        """Synchronous connect (run in executor)."""
        self.connection = Connection(self.config)
        self.connection.connect()
        
        self.transfer_manager = TransferManager(
            self.connection,
            chunk_size=self.config.transfer.chunk_size
        )
        
        self._connected = True
    
    async def disconnect_async(self) -> None:
        """Disconnect from server gracefully."""
        async with self._lock:
            if self.connection:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.connection.disconnect
                )
            
            self.connection = None
            self.transfer_manager = None
            self._connected = False
    
    async def upload_async(
        self,
        local_path: str,
        remote_path: str,
        resume: bool = True,
        progress_callback: Optional[ProgressCallback] = None,
        show_progress: bool = False
    ) -> None:
        """
        Upload a file asynchronously.
        
        Args:
            local_path: Local file path
            remote_path: Remote file path
            resume: Resume if partial upload exists
            progress_callback: Custom progress callback
            show_progress: Show console progress bar
        """
        await self._ensure_connected_async()
        
        if show_progress and not progress_callback:
            progress_callback = create_console_progress_callback()
        
        # Run upload in executor to avoid blocking
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.transfer_manager.upload_file,
            local_path,
            remote_path,
            resume,
            progress_callback
        )
    
    async def download_async(
        self,
        remote_path: str,
        local_path: str,
        resume: bool = True,
        progress_callback: Optional[ProgressCallback] = None,
        show_progress: bool = False
    ) -> None:
        """
        Download a file asynchronously.
        
        Args:
            remote_path: Remote file path
            local_path: Local file path
            resume: Resume if partial download exists
            progress_callback: Custom progress callback
            show_progress: Show console progress bar
        """
        await self._ensure_connected_async()
        
        if show_progress and not progress_callback:
            progress_callback = create_console_progress_callback()
        
        # Run download in executor
        await asyncio.get_event_loop().run_in_executor(
            None,
            self.transfer_manager.download_file,
            remote_path,
            local_path,
            resume,
            progress_callback
        )
    
    async def delete_async(self, remote_path: str) -> None:
        """
        Delete a file asynchronously.
        
        Args:
            remote_path: Remote file path
        """
        await self._ensure_connected_async()
        
        from fileharbor.common.protocol import create_response
        from fileharbor.common.constants import CMD_DELETE
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            self._sync_delete,
            remote_path
        )
    
    def _sync_delete(self, remote_path: str) -> None:
        """Synchronous delete (run in executor)."""
        from fileharbor.common.protocol import create_response
        from fileharbor.common.constants import CMD_DELETE
        
        msg = create_response(CMD_DELETE, filepath=remote_path)
        self.connection.send_message(msg)
        self.connection.receive_message()
    
    async def list_directory_async(
        self,
        remote_path: str = '/',
        recursive: bool = False
    ) -> List[FileInfo]:
        """
        List files in a directory asynchronously.
        
        Args:
            remote_path: Directory path
            recursive: List recursively
            
        Returns:
            List of FileInfo objects
        """
        await self._ensure_connected_async()
        
        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._sync_list_directory,
            remote_path,
            recursive
        )
    
    def _sync_list_directory(self, remote_path: str, recursive: bool) -> List[FileInfo]:
        """Synchronous list (run in executor)."""
        from fileharbor.common.protocol import create_response
        from fileharbor.common.constants import CMD_LIST
        
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
    
    async def mkdir_async(self, remote_path: str) -> None:
        """
        Create a directory asynchronously.
        
        Args:
            remote_path: Directory path
        """
        await self._ensure_connected_async()
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            self._sync_mkdir,
            remote_path
        )
    
    def _sync_mkdir(self, remote_path: str) -> None:
        """Synchronous mkdir (run in executor)."""
        from fileharbor.common.protocol import create_response
        from fileharbor.common.constants import CMD_MKDIR
        
        msg = create_response(CMD_MKDIR, dirpath=remote_path)
        self.connection.send_message(msg)
        self.connection.receive_message()
    
    async def exists_async(self, remote_path: str) -> bool:
        """
        Check if file exists asynchronously.
        
        Args:
            remote_path: Remote file path
            
        Returns:
            True if file exists
        """
        await self._ensure_connected_async()
        
        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._sync_exists,
            remote_path
        )
    
    def _sync_exists(self, remote_path: str) -> bool:
        """Synchronous exists check (run in executor)."""
        from fileharbor.common.protocol import create_response
        from fileharbor.common.constants import CMD_EXISTS
        
        msg = create_response(CMD_EXISTS, filepath=remote_path)
        self.connection.send_message(msg)
        response = self.connection.receive_message()
        
        return response.content.get('exists', False)
    
    async def get_manifest_async(self, remote_path: str = '/') -> List[FileInfo]:
        """
        Get file manifest asynchronously.
        
        Args:
            remote_path: Starting directory path
            
        Returns:
            List of FileInfo objects
        """
        await self._ensure_connected_async()
        
        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._sync_get_manifest,
            remote_path
        )
    
    def _sync_get_manifest(self, remote_path: str) -> List[FileInfo]:
        """Synchronous manifest (run in executor)."""
        from fileharbor.common.protocol import create_response
        from fileharbor.common.constants import CMD_MANIFEST
        
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
    
    async def ping_async(self) -> bool:
        """
        Ping server asynchronously.
        
        Returns:
            True if server responds
        """
        await self._ensure_connected_async()
        
        return await asyncio.get_event_loop().run_in_executor(
            None,
            self.connection.ping
        )
    
    async def _ensure_connected_async(self) -> None:
        """
        Ensure client is connected.
        
        Raises:
            ConnectionError: If not connected
        """
        if not self._connected:
            raise FHConnectionError("Not connected to server. Call connect_async() first.")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect_async()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect_async()
        return False
