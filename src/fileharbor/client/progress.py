"""
FileHarbor Progress Tracking

Progress callbacks and monitoring for file transfers.
"""

import time
from typing import Optional, Callable
from dataclasses import dataclass


@dataclass
class TransferProgress:
    """
    Progress information for a file transfer.
    """
    filepath: str
    bytes_transferred: int
    total_bytes: int
    start_time: float
    operation: str  # 'upload' or 'download'
    
    def __post_init__(self):
        """Initialize computed properties."""
        if self.start_time == 0:
            self.start_time = time.time()
    
    @property
    def percentage(self) -> float:
        """Get percentage complete (0-100)."""
        if self.total_bytes == 0:
            return 0.0
        return (self.bytes_transferred / self.total_bytes) * 100
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time
    
    @property
    def transfer_rate(self) -> float:
        """Get current transfer rate in bytes/second."""
        elapsed = self.elapsed_time
        if elapsed == 0:
            return 0.0
        return self.bytes_transferred / elapsed
    
    @property
    def transfer_rate_mbps(self) -> float:
        """Get transfer rate in megabits per second."""
        return (self.transfer_rate * 8) / 1_000_000
    
    @property
    def eta_seconds(self) -> Optional[float]:
        """Get estimated time to completion in seconds."""
        if self.bytes_transferred == 0:
            return None
        
        bytes_remaining = self.total_bytes - self.bytes_transferred
        rate = self.transfer_rate
        
        if rate == 0:
            return None
        
        return bytes_remaining / rate
    
    @property
    def is_complete(self) -> bool:
        """Check if transfer is complete."""
        return self.bytes_transferred >= self.total_bytes
    
    def format_summary(self) -> str:
        """
        Format a human-readable summary.
        
        Returns:
            Formatted string
        """
        percentage = self.percentage
        rate_mbps = self.transfer_rate_mbps
        
        size_mb = self.total_bytes / (1024 * 1024)
        transferred_mb = self.bytes_transferred / (1024 * 1024)
        
        summary = f"{self.operation.title()}: {self.filepath}\n"
        summary += f"  Progress: {transferred_mb:.2f}/{size_mb:.2f} MB ({percentage:.1f}%)\n"
        summary += f"  Rate: {rate_mbps:.2f} Mbps"
        
        if self.eta_seconds is not None:
            eta_min = int(self.eta_seconds / 60)
            eta_sec = int(self.eta_seconds % 60)
            summary += f"\n  ETA: {eta_min}m {eta_sec}s"
        
        return summary


# Type alias for progress callbacks
ProgressCallback = Callable[[TransferProgress], None]


class ProgressTracker:
    """
    Tracks progress for file transfers and invokes callbacks.
    """
    
    def __init__(
        self,
        filepath: str,
        total_bytes: int,
        operation: str,
        callback: Optional[ProgressCallback] = None,
        update_interval: float = 0.5
    ):
        """
        Initialize progress tracker.
        
        Args:
            filepath: File being transferred
            total_bytes: Total file size
            operation: 'upload' or 'download'
            callback: Optional callback function
            update_interval: Minimum seconds between callbacks
        """
        self.filepath = filepath
        self.total_bytes = total_bytes
        self.operation = operation
        self.callback = callback
        self.update_interval = update_interval
        
        self.bytes_transferred = 0
        self.start_time = time.time()
        self.last_callback_time = 0.0
    
    def update(self, bytes_count: int) -> None:
        """
        Update progress by adding transferred bytes.
        
        Args:
            bytes_count: Number of bytes transferred in this update
        """
        self.bytes_transferred += bytes_count
        
        # Invoke callback if enough time has passed
        now = time.time()
        if self.callback and (now - self.last_callback_time) >= self.update_interval:
            progress = TransferProgress(
                filepath=self.filepath,
                bytes_transferred=self.bytes_transferred,
                total_bytes=self.total_bytes,
                start_time=self.start_time,
                operation=self.operation
            )
            
            try:
                self.callback(progress)
            except Exception:
                # Don't let callback errors stop the transfer
                pass
            
            self.last_callback_time = now
    
    def complete(self) -> None:
        """Mark transfer as complete and do final callback."""
        self.bytes_transferred = self.total_bytes
        
        if self.callback:
            progress = TransferProgress(
                filepath=self.filepath,
                bytes_transferred=self.bytes_transferred,
                total_bytes=self.total_bytes,
                start_time=self.start_time,
                operation=self.operation
            )
            
            try:
                self.callback(progress)
            except Exception:
                pass
    
    def get_progress(self) -> TransferProgress:
        """
        Get current progress.
        
        Returns:
            TransferProgress object
        """
        return TransferProgress(
            filepath=self.filepath,
            bytes_transferred=self.bytes_transferred,
            total_bytes=self.total_bytes,
            start_time=self.start_time,
            operation=self.operation
        )


def create_console_progress_callback() -> ProgressCallback:
    """
    Create a simple console progress callback.
    
    Returns:
        Progress callback function
    """
    def callback(progress: TransferProgress):
        """Print progress to console."""
        percentage = progress.percentage
        rate_mbps = progress.transfer_rate_mbps
        
        # Create progress bar
        bar_width = 40
        filled = int(bar_width * percentage / 100)
        bar = '█' * filled + '░' * (bar_width - filled)
        
        print(
            f"\r{progress.operation.title()}: [{bar}] "
            f"{percentage:.1f}% @ {rate_mbps:.2f} Mbps",
            end='',
            flush=True
        )
        
        if progress.is_complete:
            print()  # New line when complete
    
    return callback
