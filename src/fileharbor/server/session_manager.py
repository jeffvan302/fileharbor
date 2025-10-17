"""
FileHarbor Session Manager

Manages client sessions, file locks, and resumable transfer state.
"""

import time
import threading
import pickle
from pathlib import Path
from typing import Dict, Optional, Set, Tuple
from dataclasses import dataclass, field

from fileharbor.common.constants import (
    SESSION_CLEANUP_INTERVAL,
    DEFAULT_IDLE_TIMEOUT,
    RESUME_STATE_EXTENSION,
)


@dataclass
class TransferState:
    """State for a resumable file transfer."""
    filepath: str
    file_size: int
    checksum: str
    bytes_transferred: int
    chunk_size: int
    last_activity: float = field(default_factory=time.time)
    
    def update_progress(self, bytes_count: int) -> None:
        """Update transfer progress."""
        self.bytes_transferred += bytes_count
        self.last_activity = time.time()
    
    def is_complete(self) -> bool:
        """Check if transfer is complete."""
        return self.bytes_transferred >= self.file_size


@dataclass
class ClientSession:
    """Represents an active client session."""
    session_id: str
    client_id: str
    library_id: str
    connected_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    active_transfers: Dict[str, TransferState] = field(default_factory=dict)
    locked_files: Set[str] = field(default_factory=set)
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()
    
    def is_idle(self, timeout: int) -> bool:
        """Check if session has been idle too long."""
        return (time.time() - self.last_activity) > timeout


class SessionManager:
    """
    Manages client sessions and transfer state.
    
    Handles:
    - Active session tracking
    - File locking
    - Resumable transfer state
    - Session timeout
    """
    
    def __init__(self, state_file: Optional[str] = None):
        """
        Initialize session manager.
        
        Args:
            state_file: Optional file to persist session state
        """
        self.sessions: Dict[str, ClientSession] = {}
        self.library_locks: Dict[str, str] = {}  # library_id -> client_id
        self.file_locks: Dict[str, str] = {}  # file_path -> session_id
        self.state_file = state_file
        self.lock = threading.RLock()
        self.cleanup_thread = None
        self.running = False
        
        # Load persisted state if available
        if state_file:
            self._load_state()
    
    def start(self) -> None:
        """Start the session manager and cleanup thread."""
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
    
    def stop(self) -> None:
        """Stop the session manager."""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5.0)
        
        # Save state before stopping
        if self.state_file:
            self._save_state()
    
    def create_session(
        self,
        session_id: str,
        client_id: str,
        library_id: str
    ) -> ClientSession:
        """
        Create a new client session.
        
        Args:
            session_id: Unique session identifier
            client_id: Client UUID
            library_id: Library UUID
            
        Returns:
            ClientSession object
            
        Raises:
            ValueError: If library is already locked by another client
        """
        with self.lock:
            # Check if library is available
            if library_id in self.library_locks:
                locked_by = self.library_locks[library_id]
                if locked_by != client_id:
                    raise ValueError(
                        f"Library {library_id} is currently in use by another client"
                    )
            
            # Create session
            session = ClientSession(
                session_id=session_id,
                client_id=client_id,
                library_id=library_id
            )
            
            self.sessions[session_id] = session
            self.library_locks[library_id] = client_id
            
            return session
    
    def get_session(self, session_id: str) -> Optional[ClientSession]:
        """
        Get session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ClientSession or None
        """
        with self.lock:
            return self.sessions.get(session_id)
    
    def update_session_activity(self, session_id: str) -> None:
        """
        Update session activity timestamp.
        
        Args:
            session_id: Session identifier
        """
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id].update_activity()
    
    def close_session(self, session_id: str) -> None:
        """
        Close a session and release all locks.
        
        Args:
            session_id: Session identifier
        """
        with self.lock:
            if session_id not in self.sessions:
                return
            
            session = self.sessions[session_id]
            
            # Release library lock
            if session.library_id in self.library_locks:
                if self.library_locks[session.library_id] == session.client_id:
                    del self.library_locks[session.library_id]
            
            # Release file locks
            for filepath in list(session.locked_files):
                self.unlock_file(session_id, filepath)
            
            # Remove session
            del self.sessions[session_id]
    
    def lock_file(self, session_id: str, filepath: str) -> bool:
        """
        Acquire lock on a file.
        
        Args:
            session_id: Session identifier
            filepath: File path to lock
            
        Returns:
            True if lock acquired, False if already locked
        """
        with self.lock:
            if filepath in self.file_locks:
                # Check if it's locked by this session
                return self.file_locks[filepath] == session_id
            
            # Acquire lock
            self.file_locks[filepath] = session_id
            if session_id in self.sessions:
                self.sessions[session_id].locked_files.add(filepath)
            
            return True
    
    def unlock_file(self, session_id: str, filepath: str) -> None:
        """
        Release lock on a file.
        
        Args:
            session_id: Session identifier
            filepath: File path to unlock
        """
        with self.lock:
            if filepath in self.file_locks:
                if self.file_locks[filepath] == session_id:
                    del self.file_locks[filepath]
            
            if session_id in self.sessions:
                self.sessions[session_id].locked_files.discard(filepath)
    
    def is_file_locked(self, filepath: str) -> bool:
        """
        Check if a file is locked.
        
        Args:
            filepath: File path to check
            
        Returns:
            True if file is locked
        """
        with self.lock:
            return filepath in self.file_locks
    
    def start_transfer(
        self,
        session_id: str,
        filepath: str,
        file_size: int,
        checksum: str,
        chunk_size: int,
        resume_offset: int = 0
    ) -> TransferState:
        """
        Start or resume a file transfer.
        
        Args:
            session_id: Session identifier
            filepath: File path being transferred
            file_size: Total file size
            checksum: Expected file checksum
            chunk_size: Transfer chunk size
            resume_offset: Bytes already transferred (for resume)
            
        Returns:
            TransferState object
        """
        with self.lock:
            if session_id not in self.sessions:
                raise ValueError(f"Session not found: {session_id}")
            
            session = self.sessions[session_id]
            
            # Create transfer state
            transfer = TransferState(
                filepath=filepath,
                file_size=file_size,
                checksum=checksum,
                bytes_transferred=resume_offset,
                chunk_size=chunk_size
            )
            
            session.active_transfers[filepath] = transfer
            
            return transfer
    
    def update_transfer_progress(
        self,
        session_id: str,
        filepath: str,
        bytes_count: int
    ) -> None:
        """
        Update transfer progress.
        
        Args:
            session_id: Session identifier
            filepath: File path being transferred
            bytes_count: Number of bytes transferred in this chunk
        """
        with self.lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                if filepath in session.active_transfers:
                    session.active_transfers[filepath].update_progress(bytes_count)
                    session.update_activity()
    
    def complete_transfer(self, session_id: str, filepath: str) -> None:
        """
        Mark transfer as complete and remove from active transfers.
        
        Args:
            session_id: Session identifier
            filepath: File path that completed
        """
        with self.lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                if filepath in session.active_transfers:
                    del session.active_transfers[filepath]
    
    def get_transfer_state(
        self,
        session_id: str,
        filepath: str
    ) -> Optional[TransferState]:
        """
        Get transfer state for a file.
        
        Args:
            session_id: Session identifier
            filepath: File path
            
        Returns:
            TransferState or None
        """
        with self.lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                return session.active_transfers.get(filepath)
            return None
    
    def cleanup_idle_sessions(self, timeout: int = DEFAULT_IDLE_TIMEOUT) -> int:
        """
        Clean up idle sessions.
        
        Args:
            timeout: Idle timeout in seconds
            
        Returns:
            Number of sessions cleaned up
        """
        with self.lock:
            idle_sessions = [
                session_id
                for session_id, session in self.sessions.items()
                if session.is_idle(timeout)
            ]
            
            for session_id in idle_sessions:
                self.close_session(session_id)
            
            return len(idle_sessions)
    
    def get_active_session_count(self) -> int:
        """Get number of active sessions."""
        with self.lock:
            return len(self.sessions)
    
    def _cleanup_loop(self) -> None:
        """Background thread for cleaning up idle sessions."""
        while self.running:
            time.sleep(SESSION_CLEANUP_INTERVAL)
            try:
                cleaned = self.cleanup_idle_sessions()
                if cleaned > 0:
                    print(f"🧹 Cleaned up {cleaned} idle session(s)")
            except Exception as e:
                print(f"❌ Error in session cleanup: {e}")
    
    def _save_state(self) -> None:
        """Save session state to disk."""
        if not self.state_file:
            return
        
        try:
            with self.lock:
                with open(self.state_file, 'wb') as f:
                    pickle.dump({
                        'sessions': self.sessions,
                        'library_locks': self.library_locks,
                        'file_locks': self.file_locks,
                    }, f)
        except Exception as e:
            print(f"⚠️  Failed to save session state: {e}")
    
    def _load_state(self) -> None:
        """Load session state from disk."""
        if not self.state_file or not Path(self.state_file).exists():
            return
        
        try:
            with self.lock:
                with open(self.state_file, 'rb') as f:
                    state = pickle.load(f)
                    self.sessions = state.get('sessions', {})
                    self.library_locks = state.get('library_locks', {})
                    self.file_locks = state.get('file_locks', {})
            print(f"✅ Loaded session state from {self.state_file}")
        except Exception as e:
            print(f"⚠️  Failed to load session state: {e}")
