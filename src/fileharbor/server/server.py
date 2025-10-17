"""
FileHarbor Server

Main server implementation with TLS socket and multi-threading.
"""

import socket
import ssl
import threading
import logging
import signal
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fileharbor.common.config_schema import ServerConfig
from fileharbor.common.exceptions import ServerError, ServerStartupError

from fileharbor.server.config import load_server_config, validate_server_config
from fileharbor.server.auth import ServerAuthenticator
from fileharbor.server.library_manager import LibraryManager
from fileharbor.server.session_manager import SessionManager
from fileharbor.server.connection_handler import ConnectionHandler


class FileHarborServer:
    """
    FileHarbor Server
    
    Multi-threaded TLS server for secure file transfers.
    """
    
    def __init__(self, config: ServerConfig):
        """
        Initialize server.
        
        Args:
            config: Server configuration
        """
        self.config = config
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self.ssl_context: Optional[ssl.SSLContext] = None
        self.thread_pool: Optional[ThreadPoolExecutor] = None
        
        # Initialize components
        self.authenticator = ServerAuthenticator(config)
        self.library_manager = LibraryManager(config)
        self.session_manager = SessionManager()
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def start(self) -> None:
        """
        Start the server.
        
        Raises:
            ServerStartupError: If server fails to start
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("🚀 FileHarbor Server Starting")
            self.logger.info("=" * 60)
            
            # Validate configuration
            validate_server_config(self.config)
            
            # Create SSL context
            self.ssl_context = self.authenticator.create_ssl_context()
            self.logger.info("🔐 SSL/TLS context initialized")
            
            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind and listen
            host = self.config.server.host
            port = self.config.server.port
            self.server_socket.bind((host, port))
            self.server_socket.listen(self.config.server.max_connections)
            
            self.logger.info(f"📡 Listening on {host}:{port}")
            self.logger.info(f"👥 Max connections: {self.config.server.max_connections}")
            self.logger.info(f"🧵 Worker threads: {self.config.server.worker_threads}")
            
            # Create thread pool
            self.thread_pool = ThreadPoolExecutor(
                max_workers=self.config.server.worker_threads,
                thread_name_prefix="FileHarbor-Worker"
            )
            
            # Start session manager
            self.session_manager.start()
            
            # Log library information
            self.logger.info(f"📚 Libraries configured: {len(self.config.libraries)}")
            for lib_id, library in self.config.libraries.items():
                client_count = len(library.authorized_clients)
                self.logger.info(
                    f"   - {library.name}: {library.path} "
                    f"({client_count} client(s))"
                )
            
            self.running = True
            self.logger.info("✅ Server started successfully")
            self.logger.info("=" * 60)
            
            # Accept connections
            self._accept_connections()
            
        except OSError as e:
            raise ServerStartupError(f"Failed to bind to {host}:{port}: {e}")
        except Exception as e:
            raise ServerStartupError(f"Server startup failed: {e}")
    
    def stop(self) -> None:
        """Stop the server gracefully."""
        if not self.running:
            return
        
        self.logger.info("=" * 60)
        self.logger.info("🛑 Shutting down FileHarbor Server")
        self.logger.info("=" * 60)
        
        self.running = False
        
        # Stop accepting new connections
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        
        # Stop session manager
        self.session_manager.stop()
        
        # Shutdown thread pool
        if self.thread_pool:
            self.logger.info("⏳ Waiting for active connections to complete...")
            self.thread_pool.shutdown(wait=True, cancel_futures=False)
        
        self.logger.info("✅ Server stopped")
        self.logger.info("=" * 60)
    
    def _accept_connections(self) -> None:
        """Accept and handle incoming connections."""
        while self.running:
            try:
                # Accept connection
                client_socket, client_address = self.server_socket.accept()
                
                # Wrap with SSL
                try:
                    ssl_socket = self.ssl_context.wrap_socket(
                        client_socket,
                        server_side=True
                    )
                except ssl.SSLError as e:
                    self.logger.warning(f"❌ SSL handshake failed from {client_address}: {e}")
                    client_socket.close()
                    continue
                
                # Handle connection in thread pool
                self.thread_pool.submit(
                    self._handle_client,
                    ssl_socket,
                    client_address
                )
                
            except OSError:
                if self.running:
                    # Only log if we're still supposed to be running
                    self.logger.error("❌ Error accepting connection")
                break
            except Exception as e:
                if self.running:
                    self.logger.error(f"❌ Unexpected error: {e}", exc_info=True)
    
    def _handle_client(self, client_socket: socket.socket, client_address: tuple) -> None:
        """
        Handle a client connection.
        
        Args:
            client_socket: Client SSL socket
            client_address: Client address tuple
        """
        handler = ConnectionHandler(
            client_socket,
            client_address,
            self.authenticator,
            self.library_manager,
            self.session_manager,
            self.logger
        )
        
        try:
            handler.handle()
        except Exception as e:
            self.logger.error(
                f"❌ Error handling client {client_address}: {e}",
                exc_info=True
            )
    
    def _setup_logging(self) -> logging.Logger:
        """
        Setup logging configuration.
        
        Returns:
            Logger instance
        """
        logger = logging.getLogger('FileHarbor')
        
        # Set log level
        log_level = getattr(logging, self.config.logging.level.upper(), logging.INFO)
        logger.setLevel(log_level)
        
        # Remove existing handlers
        logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler (if configured)
        if self.config.logging.file:
            try:
                from logging.handlers import RotatingFileHandler
                
                file_handler = RotatingFileHandler(
                    self.config.logging.file,
                    maxBytes=self.config.logging.max_size,
                    backupCount=self.config.logging.backup_count
                )
                file_handler.setLevel(log_level)
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - '
                    '%(filename)s:%(lineno)d - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
                
                logger.info(f"📝 Logging to file: {self.config.logging.file}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to setup file logging: {e}")
        
        return logger
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        self.logger.info(f"⚠️  Received signal: {signal_name}")
        self.stop()
        sys.exit(0)
    
    def get_status(self) -> dict:
        """
        Get server status information.
        
        Returns:
            Dictionary with status info
        """
        return {
            'running': self.running,
            'host': self.config.server.host,
            'port': self.config.server.port,
            'active_sessions': self.session_manager.get_active_session_count(),
            'libraries': len(self.config.libraries),
            'worker_threads': self.config.server.worker_threads,
        }
