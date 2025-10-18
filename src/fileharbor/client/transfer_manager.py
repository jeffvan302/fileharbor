"""
FileHarbor Transfer Manager

Handles resumable file uploads and downloads with chunking and progress tracking.
"""

from pathlib import Path
from typing import Optional

from fileharbor.common.protocol import (
    create_put_start_request,
    create_get_start_request,
    create_response,
    parse_put_start_response,
    parse_get_start_response,
)
from fileharbor.common.constants import (
    CMD_PUT_START,
    CMD_PUT_CHUNK,
    CMD_PUT_COMPLETE,
    CMD_GET_START,
    CMD_GET_CHUNK,
    DEFAULT_CHUNK_SIZE,
)
from fileharbor.common.exceptions import (
    FileTransferError,
    ChecksumMismatchError,
)
from fileharbor.utils.checksum import calculate_file_checksum
from fileharbor.utils.file_utils import get_file_size, get_file_mtime, get_file_ctime
from fileharbor.utils.network_utils import send_all, recv_all

from fileharbor.client.connection import Connection
from fileharbor.client.progress import ProgressTracker, ProgressCallback


class TransferManager:
    """
    Manages file transfers with resume support and progress tracking.
    """
    
    def __init__(self, connection: Connection, chunk_size: int = DEFAULT_CHUNK_SIZE):
        """
        Initialize transfer manager.
        
        Args:
            connection: Active connection to server
            chunk_size: Size of transfer chunks in bytes
        """
        self.connection = connection
        self.chunk_size = chunk_size
    
    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        resume: bool = True,
        progress_callback: Optional[ProgressCallback] = None
    ) -> None:
        """
        Upload a file to the server.
        
        Args:
            local_path: Local file path
            remote_path: Remote file path
            resume: Whether to resume if partial upload exists
            progress_callback: Optional progress callback
            
        Raises:
            FileNotFoundError: If local file doesn't exist
            FileTransferError: If upload fails
        """
        local_file = Path(local_path)
        
        if not local_file.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        # Get file info
        file_size = get_file_size(local_file)
        modified_time = get_file_mtime(local_file)
        created_time = get_file_ctime(local_file)
        
        # Create progress tracker BEFORE checksum calculation
        # Total operation = checksum calculation + upload
        tracker = ProgressTracker(
            filepath=remote_path,
            total_bytes=file_size * 2,  # Count file twice: once for checksum, once for upload
            operation='upload',
            callback=progress_callback
        )
        
        # Calculate checksum with progress tracking
        checksum = self._calculate_checksum_with_progress(local_file, file_size, tracker)
        
        # Start upload
        put_start_msg = create_put_start_request(
            filepath=remote_path,
            file_size=file_size,
            checksum=checksum,
            chunk_size=self.chunk_size,
            resume=resume
        )
        
        self.connection.send_message(put_start_msg)
        response = self.connection.receive_message()
        
        put_start_resp = parse_put_start_response(response)
        temp_filepath = put_start_resp.temp_filepath
        resume_offset = put_start_resp.resume_offset
        
        # Update tracker if resuming (add to existing checksum progress)
        if resume_offset > 0:
            tracker.update(resume_offset)
        
        # Upload chunks
        with open(local_file, 'rb') as f:
            # Seek to resume position
            f.seek(resume_offset)
            offset = resume_offset
            
            while offset < file_size:
                # Read chunk
                chunk_data = f.read(self.chunk_size)
                if not chunk_data:
                    break
                
                # Send PUT_CHUNK message
                chunk_msg = create_response(
                    CMD_PUT_CHUNK,
                    filepath=remote_path,
                    temp_filepath=temp_filepath,
                    offset=offset,
                    chunk_size=len(chunk_data)
                )
                self.connection.send_message(chunk_msg)
                
                # Send chunk data
                send_all(self.connection.ssl_socket, chunk_data)
                
                # Receive response
                chunk_response = self.connection.receive_message()
                
                # Update progress
                bytes_written = chunk_response.content.get('bytes_written', len(chunk_data))
                offset += bytes_written
                tracker.update(bytes_written)
        
        # Complete upload
        complete_msg = create_response(
            CMD_PUT_COMPLETE,
            filepath=remote_path,
            temp_filepath=temp_filepath,
            checksum=checksum,
            modified_time=modified_time,
            created_time=created_time
        )
        
        self.connection.send_message(complete_msg)
        complete_response = self.connection.receive_message()
        
        # Mark complete
        tracker.complete()
    
    def download_file(
        self,
        remote_path: str,
        local_path: str,
        resume: bool = True,
        progress_callback: Optional[ProgressCallback] = None
    ) -> None:
        """
        Download a file from the server.
        
        Args:
            remote_path: Remote file path
            local_path: Local file path
            resume: Whether to resume if partial download exists
            progress_callback: Optional progress callback
            
        Raises:
            FileTransferError: If download fails
            ChecksumMismatchError: If checksum verification fails
        """
        local_file = Path(local_path)
        
        # Check for resume
        resume_offset = 0
        if resume and local_file.exists():
            resume_offset = get_file_size(local_file)
        
        # Start download
        get_start_msg = create_get_start_request(
            filepath=remote_path,
            offset=resume_offset
        )
        
        self.connection.send_message(get_start_msg)
        response = self.connection.receive_message()
        
        get_start_resp = parse_get_start_response(response)
        file_size = get_start_resp.file_size
        expected_checksum = get_start_resp.checksum
        
        # Create progress tracker
        tracker = ProgressTracker(
            filepath=remote_path,
            total_bytes=file_size,
            operation='download',
            callback=progress_callback
        )
        
        # Update tracker if resuming
        if resume_offset > 0:
            tracker.bytes_transferred = resume_offset
        
        # Ensure parent directory exists
        local_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Download chunks
        mode = 'ab' if resume else 'wb'
        with open(local_file, mode) as f:
            offset = resume_offset
            
            while offset < file_size:
                # Request chunk
                bytes_to_read = min(self.chunk_size, file_size - offset)
                
                chunk_msg = create_response(
                    CMD_GET_CHUNK,
                    filepath=remote_path,
                    offset=offset,
                    chunk_size=bytes_to_read
                )
                
                self.connection.send_message(chunk_msg)
                
                # Receive response
                chunk_response = self.connection.receive_message()
                chunk_size = chunk_response.content.get('chunk_size', 0)
                
                # Receive chunk data
                chunk_data = recv_all(self.connection.ssl_socket, chunk_size)
                
                # Write chunk
                f.write(chunk_data)
                f.flush()
                
                # Update progress
                offset += len(chunk_data)
                tracker.update(len(chunk_data))
        
        # Verify checksum
        actual_checksum = calculate_file_checksum(local_file)
        if actual_checksum.lower() != expected_checksum.lower():
            # Delete corrupted file
            local_file.unlink()
            raise ChecksumMismatchError(
                expected_checksum,
                actual_checksum,
                str(local_file)
            )
        
        # Mark complete
        tracker.complete()
    
    def upload_with_retry(
        self,
        local_path: str,
        remote_path: str,
        max_retries: int = 3,
        progress_callback: Optional[ProgressCallback] = None
    ) -> None:
        """
        Upload a file with automatic retry on failure.
        
        Args:
            local_path: Local file path
            remote_path: Remote file path
            max_retries: Maximum number of retry attempts
            progress_callback: Optional progress callback
            
        Raises:
            FileTransferError: If all retries fail
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                self.upload_file(
                    local_path,
                    remote_path,
                    resume=True,
                    progress_callback=progress_callback
                )
                return  # Success
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Retry with resume enabled
                    continue
        
        # All retries failed
        raise FileTransferError(f"Upload failed after {max_retries} attempts: {last_error}")
    
    def download_with_retry(
        self,
        remote_path: str,
        local_path: str,
        max_retries: int = 3,
        progress_callback: Optional[ProgressCallback] = None
    ) -> None:
        """
        Download a file with automatic retry on failure.
        
        Args:
            remote_path: Remote file path
            local_path: Local file path
            max_retries: Maximum number of retry attempts
            progress_callback: Optional progress callback
            
        Raises:
            FileTransferError: If all retries fail
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                self.download_file(
                    remote_path,
                    local_path,
                    resume=True,
                    progress_callback=progress_callback
                )
                return  # Success
            except ChecksumMismatchError:
                # Don't retry checksum mismatches - file is corrupted on server
                raise
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Retry with resume enabled
                    continue
        
        # All retries failed
        raise FileTransferError(f"Download failed after {max_retries} attempts: {last_error}")
    
    def _calculate_checksum_with_progress(
        self,
        filepath: Path,
        file_size: int,
        tracker: ProgressTracker
    ) -> str:
        """
        Calculate file checksum with progress updates.
        
        Args:
            filepath: Path to file
            file_size: Size of file
            tracker: Progress tracker to update
            
        Returns:
            SHA-256 checksum hex string
        """
        import hashlib
        from fileharbor.common.constants import CHECKSUM_BUFFER_SIZE
        
        sha256_hash = hashlib.sha256()
        
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(CHECKSUM_BUFFER_SIZE)
                if not chunk:
                    break
                sha256_hash.update(chunk)
                tracker.update(len(chunk))
        
        return sha256_hash.hexdigest()
