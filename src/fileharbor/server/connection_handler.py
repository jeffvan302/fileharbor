"""
FileHarbor Connection Handler

Handles individual client connections and processes protocol messages.
"""

import socket
import logging
from typing import Optional
import secrets

from fileharbor.common.protocol import (
    Message,
    MessageHeader,
    MessageType,
    create_response,
    create_error_response,
    create_data_message,
    parse_handshake_request,
    parse_put_start_request,
    parse_get_start_request,
    is_request,
)
from fileharbor.common.constants import (
    CMD_HANDSHAKE,
    CMD_PUT_START,
    CMD_PUT_CHUNK,
    CMD_PUT_COMPLETE,
    CMD_GET_START,
    CMD_GET_CHUNK,
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
    CMD_DISCONNECT,
    STATUS_SUCCESS,
    STATUS_BAD_REQUEST,
    STATUS_UNAUTHORIZED,
    STATUS_NOT_FOUND,
    STATUS_INTERNAL_ERROR,
    STATUS_LOCKED,
    MESSAGE_HEADER_SIZE,
    DEFAULT_CHUNK_SIZE,
)
from fileharbor.common.exceptions import (
    FileHarborException,
    AuthenticationError,
    LibraryAccessDeniedError,
    PathTraversalError,
)
from fileharbor.utils.network_utils import send_all, recv_all

from fileharbor.server.auth import ServerAuthenticator, extract_client_cert_from_ssl
from fileharbor.server.library_manager import LibraryManager
from fileharbor.server.file_operations import FileOperationHandler
from fileharbor.server.session_manager import SessionManager
from fileharbor.server.rate_limiter import RateLimiter


class ConnectionHandler:
    """
    Handles a single client connection.
    
    Processes protocol messages and executes file operations.
    """
    
    def __init__(
        self,
        client_socket: socket.socket,
        client_address: tuple,
        authenticator: ServerAuthenticator,
        library_manager: LibraryManager,
        session_manager: SessionManager,
        logger: logging.Logger
    ):
        """
        Initialize connection handler.
        
        Args:
            client_socket: Client socket
            client_address: Client address tuple
            authenticator: Server authenticator
            library_manager: Library manager
            session_manager: Session manager
            logger: Logger instance
        """
        self.socket = client_socket
        self.address = client_address
        self.authenticator = authenticator
        self.library_manager = library_manager
        self.session_manager = session_manager
        self.logger = logger
        
        # Connection state
        self.authenticated = False
        self.client_id: Optional[str] = None
        self.library_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.file_handler: Optional[FileOperationHandler] = None
        self.rate_limiter: Optional[RateLimiter] = None
        
        self.running = True
    
    def handle(self) -> None:
        """
        Main connection handling loop.
        
        Processes messages from the client until disconnection.
        """
        try:
            self.logger.info(f"📥 New connection from {self.address[0]}:{self.address[1]}")
            
            # Main message loop
            while self.running:
                try:
                    # Receive message header
                    header_data = recv_all(self.socket, MESSAGE_HEADER_SIZE)
                    if not header_data:
                        # Client disconnected
                        break
                    
                    header = MessageHeader.deserialize(header_data)
                    
                    # Receive message content
                    content_data = b''
                    if header.content_length > 0:
                        content_data = recv_all(self.socket, header.content_length)
                    
                    # Parse message
                    message = Message.deserialize(header_data, content_data)
                    
                    # Update session activity
                    if self.session_id:
                        self.session_manager.update_session_activity(self.session_id)
                    
                    # Process message
                    self._process_message(message)
                    
                except FileHarborException as e:
                    self.logger.warning(f"⚠️  Client error: {e}")
                    self._send_error(CMD_DISCONNECT, str(e), STATUS_BAD_REQUEST)
                except Exception as e:
                    self.logger.error(f"❌ Unexpected error: {e}", exc_info=True)
                    self._send_error(CMD_DISCONNECT, "Internal server error", STATUS_INTERNAL_ERROR)
                    break
        
        finally:
            self._cleanup()
    
    def _process_message(self, message: Message) -> None:
        """
        Process a protocol message.
        
        Args:
            message: Parsed message
        """
        command = message.header.command
        
        self.logger.debug(f"📨 Received: {command}")
        
        # Handshake must be first
        if not self.authenticated and command != CMD_HANDSHAKE:
            self._send_error(command, "Authentication required", STATUS_UNAUTHORIZED)
            return
        
        # Route to appropriate handler
        if command == CMD_HANDSHAKE:
            self._handle_handshake(message)
        elif command == CMD_PUT_START:
            self._handle_put_start(message)
        elif command == CMD_PUT_CHUNK:
            self._handle_put_chunk(message)
        elif command == CMD_PUT_COMPLETE:
            self._handle_put_complete(message)
        elif command == CMD_GET_START:
            self._handle_get_start(message)
        elif command == CMD_GET_CHUNK:
            self._handle_get_chunk(message)
        elif command == CMD_DELETE:
            self._handle_delete(message)
        elif command == CMD_RENAME:
            self._handle_rename(message)
        elif command == CMD_LIST:
            self._handle_list(message)
        elif command == CMD_MKDIR:
            self._handle_mkdir(message)
        elif command == CMD_RMDIR:
            self._handle_rmdir(message)
        elif command == CMD_MANIFEST:
            self._handle_manifest(message)
        elif command == CMD_CHECKSUM:
            self._handle_checksum(message)
        elif command == CMD_STAT:
            self._handle_stat(message)
        elif command == CMD_EXISTS:
            self._handle_exists(message)
        elif command == CMD_PING:
            self._handle_ping(message)
        elif command == CMD_DISCONNECT:
            self._handle_disconnect(message)
        else:
            self._send_error(command, f"Unknown command: {command}", STATUS_BAD_REQUEST)
    
    def _handle_handshake(self, message: Message) -> None:
        """Handle HANDSHAKE command."""
        try:
            # Extract client certificate from SSL socket
            cert_pem = extract_client_cert_from_ssl(self.socket)
            if not cert_pem:
                raise AuthenticationError("No client certificate provided")
            
            # Validate certificate and extract client ID
            self.client_id = self.authenticator.validate_client_certificate(cert_pem)
            
            # Parse handshake request
            handshake = parse_handshake_request(message)
            self.library_id = handshake.library_id
            
            # Check library access
            self.authenticator.check_library_access(self.client_id, self.library_id)
            
            # Create session
            self.session_id = secrets.token_hex(16)
            self.session_manager.create_session(
                self.session_id,
                self.client_id,
                self.library_id
            )
            
            # Setup file handler
            library_path = self.library_manager.get_library_path(self.library_id)
            self.file_handler = FileOperationHandler(library_path)
            
            # Setup rate limiter
            rate_limit = self.library_manager.get_rate_limit(self.library_id)
            self.rate_limiter = RateLimiter(rate_limit)
            
            self.authenticated = True
            
            client_name = self.authenticator.get_client_name(self.client_id)
            library_config = self.library_manager.get_library(self.library_id)
            
            self.logger.info(
                f"✅ Authenticated: {client_name} -> {library_config.name} "
                f"(session: {self.session_id})"
            )
            
            # Send response
            response = create_response(
                CMD_HANDSHAKE,
                session_id=self.session_id,
                server_capabilities={
                    'resumable_transfers': True,
                    'compression': False,
                    'chunk_size': library_config.idle_timeout,
                }
            )
            self._send_message(response)
            
        except (AuthenticationError, LibraryAccessDeniedError) as e:
            self.logger.warning(f"❌ Authentication failed: {e}")
            self._send_error(CMD_HANDSHAKE, str(e), STATUS_UNAUTHORIZED)
            self.running = False
        except Exception as e:
            self.logger.error(f"❌ Handshake error: {e}")
            self._send_error(CMD_HANDSHAKE, "Handshake failed", STATUS_INTERNAL_ERROR)
            self.running = False
    
    def _handle_put_start(self, message: Message) -> None:
        """Handle PUT_START command."""
        try:
            req = parse_put_start_request(message)
            
            # Resolve path
            abs_path = self.library_manager.resolve_path(self.library_id, req.filepath)
            
            # Check if file is locked
            if self.session_manager.is_file_locked(abs_path):
                self._send_error(CMD_PUT_START, "File is locked", STATUS_LOCKED)
                return
            
            # Lock file
            self.session_manager.lock_file(self.session_id, abs_path)
            
            # Start upload
            temp_path, resume_offset = self.file_handler.start_upload(
                abs_path,
                req.file_size,
                req.checksum,
                resume=req.resume
            )
            
            # Track transfer
            self.session_manager.start_transfer(
                self.session_id,
                abs_path,
                req.file_size,
                req.checksum,
                req.chunk_size,
                resume_offset=resume_offset
            )
            
            self.logger.info(f"📤 Upload started: {req.filepath} ({req.file_size} bytes)")
            
            # Send response
            response = create_response(
                CMD_PUT_START,
                temp_filepath=temp_path,
                resume_offset=resume_offset
            )
            self._send_message(response)
            
        except PathTraversalError as e:
            self.logger.warning(f"🚨 Path traversal attempt: {e}")
            self._send_error(CMD_PUT_START, str(e), STATUS_BAD_REQUEST)
        except Exception as e:
            self.logger.error(f"❌ PUT_START error: {e}")
            self._send_error(CMD_PUT_START, str(e), STATUS_INTERNAL_ERROR)
    
    def _handle_put_chunk(self, message: Message) -> None:
        """Handle PUT_CHUNK command - receive file data."""
        try:
            filepath = message.content.get('filepath')
            offset = message.content.get('offset')
            chunk_size = message.content.get('chunk_size')
            
            # Resolve path
            abs_path = self.library_manager.resolve_path(self.library_id, filepath)
            
            # Get transfer state
            transfer = self.session_manager.get_transfer_state(self.session_id, abs_path)
            if not transfer:
                self._send_error(CMD_PUT_CHUNK, "No active transfer", STATUS_BAD_REQUEST)
                return
            
            # Receive chunk data (after the JSON message)
            chunk_data = recv_all(self.socket, chunk_size)
            
            # Apply rate limiting
            if self.rate_limiter:
                self.rate_limiter.acquire(len(chunk_data))
            
            # Write chunk
            temp_filepath = message.content.get('temp_filepath')
            bytes_written = self.file_handler.write_chunk(temp_filepath, offset, chunk_data)
            
            # Update progress
            self.session_manager.update_transfer_progress(
                self.session_id,
                abs_path,
                bytes_written
            )
            
            # Send response
            response = create_response(
                CMD_PUT_CHUNK,
                bytes_written=bytes_written
            )
            self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"❌ PUT_CHUNK error: {e}")
            self._send_error(CMD_PUT_CHUNK, str(e), STATUS_INTERNAL_ERROR)
    
    def _handle_put_complete(self, message: Message) -> None:
        """Handle PUT_COMPLETE command."""
        try:
            filepath = message.content.get('filepath')
            temp_filepath = message.content.get('temp_filepath')
            expected_checksum = message.content.get('checksum')
            modified_time = message.content.get('modified_time')
            created_time = message.content.get('created_time')
            
            # Resolve path
            abs_path = self.library_manager.resolve_path(self.library_id, filepath)
            
            # Complete upload
            self.file_handler.complete_upload(
                temp_filepath,
                abs_path,
                expected_checksum,
                modified_time=modified_time,
                created_time=created_time
            )
            
            # Clean up
            self.session_manager.complete_transfer(self.session_id, abs_path)
            self.session_manager.unlock_file(self.session_id, abs_path)
            
            self.logger.info(f"✅ Upload complete: {filepath}")
            
            # Send response
            response = create_response(CMD_PUT_COMPLETE)
            self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"❌ PUT_COMPLETE error: {e}")
            self._send_error(CMD_PUT_COMPLETE, str(e), STATUS_INTERNAL_ERROR)
    
    def _handle_get_start(self, message: Message) -> None:
        """Handle GET_START command."""
        try:
            req = parse_get_start_request(message)
            
            # Resolve path
            abs_path = self.library_manager.resolve_path(self.library_id, req.filepath)
            
            # Start download
            file_size, checksum = self.file_handler.start_download(abs_path, req.offset)
            
            self.logger.info(f"📥 Download started: {req.filepath} ({file_size} bytes)")
            
            # Determine chunk size (use client's preference or default)
            chunk_size = req.chunk_size if req.chunk_size else DEFAULT_CHUNK_SIZE
            
            # Send response
            response = create_response(
                CMD_GET_START,
                file_size=file_size,
                checksum=checksum,
                chunk_size=chunk_size
            )
            self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"❌ GET_START error: {e}")
            self._send_error(CMD_GET_START, str(e), STATUS_INTERNAL_ERROR)
    
    def _handle_get_chunk(self, message: Message) -> None:
        """Handle GET_CHUNK command - send file data."""
        try:
            filepath = message.content.get('filepath')
            offset = message.content.get('offset')
            chunk_size = message.content.get('chunk_size')
            
            # Resolve path
            abs_path = self.library_manager.resolve_path(self.library_id, filepath)
            
            # Read chunk
            chunk_data = self.file_handler.read_chunk(abs_path, offset, chunk_size)
            
            # Apply rate limiting
            if self.rate_limiter:
                self.rate_limiter.acquire(len(chunk_data))
            
            # Send response with data
            response = create_response(
                CMD_GET_CHUNK,
                chunk_size=len(chunk_data)
            )
            self._send_message(response)
            
            # Send chunk data
            send_all(self.socket, chunk_data)
            
        except Exception as e:
            self.logger.error(f"❌ GET_CHUNK error: {e}")
            self._send_error(CMD_GET_CHUNK, str(e), STATUS_INTERNAL_ERROR)
    
    def _handle_delete(self, message: Message) -> None:
        """Handle DELETE command."""
        try:
            filepath = message.content.get('filepath')
            
            # Resolve path
            abs_path = self.library_manager.resolve_path(self.library_id, filepath)
            
            # Delete file
            self.file_handler.delete_file(abs_path)
            
            self.logger.info(f"🗑️  Deleted: {filepath}")
            
            # Send response
            response = create_response(CMD_DELETE)
            self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"❌ DELETE error: {e}")
            self._send_error(CMD_DELETE, str(e), STATUS_INTERNAL_ERROR)
    
    def _handle_rename(self, message: Message) -> None:
        """Handle RENAME command."""
        try:
            old_path = message.content.get('old_path')
            new_path = message.content.get('new_path')
            
            # Resolve paths
            abs_old_path = self.library_manager.resolve_path(self.library_id, old_path)
            abs_new_path = self.library_manager.resolve_path(self.library_id, new_path)
            
            # Rename file
            self.file_handler.rename_file(abs_old_path, abs_new_path)
            
            self.logger.info(f"📝 Renamed: {old_path} -> {new_path}")
            
            # Send response
            response = create_response(CMD_RENAME)
            self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"❌ RENAME error: {e}")
            self._send_error(CMD_RENAME, str(e), STATUS_INTERNAL_ERROR)
    
    def _handle_list(self, message: Message) -> None:
        """Handle LIST command."""
        try:
            dirpath = message.content.get('dirpath', '/')
            recursive = message.content.get('recursive', False)
            
            # Resolve path
            abs_path = self.library_manager.resolve_path(self.library_id, dirpath)
            
            # List directory
            files = self.file_handler.list_directory(abs_path, recursive)
            
            # Convert to dict
            files_data = [
                {
                    'path': f.path,
                    'size': f.size,
                    'is_directory': f.is_directory,
                    'modified_time': f.modified_time,
                }
                for f in files
            ]
            
            self.logger.debug(f"📂 Listed: {dirpath} ({len(files)} items)")
            
            # Send response
            response = create_response(
                CMD_LIST,
                files=files_data
            )
            self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"❌ LIST error: {e}")
            self._send_error(CMD_LIST, str(e), STATUS_INTERNAL_ERROR)
    
    def _handle_mkdir(self, message: Message) -> None:
        """Handle MKDIR command."""
        try:
            dirpath = message.content.get('dirpath')
            
            # Resolve path
            abs_path = self.library_manager.resolve_path(self.library_id, dirpath)
            
            # Create directory
            self.file_handler.create_directory(abs_path)
            
            self.logger.info(f"📁 Created directory: {dirpath}")
            
            # Send response
            response = create_response(CMD_MKDIR)
            self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"❌ MKDIR error: {e}")
            self._send_error(CMD_MKDIR, str(e), STATUS_INTERNAL_ERROR)
    
    def _handle_rmdir(self, message: Message) -> None:
        """Handle RMDIR command."""
        try:
            dirpath = message.content.get('dirpath')
            recursive = message.content.get('recursive', False)
            
            # Resolve path
            abs_path = self.library_manager.resolve_path(self.library_id, dirpath)
            
            # Remove directory
            self.file_handler.remove_directory(abs_path, recursive)
            
            self.logger.info(f"🗑️  Removed directory: {dirpath}")
            
            # Send response
            response = create_response(CMD_RMDIR)
            self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"❌ RMDIR error: {e}")
            self._send_error(CMD_RMDIR, str(e), STATUS_INTERNAL_ERROR)
    
    def _handle_manifest(self, message: Message) -> None:
        """Handle MANIFEST command."""
        try:
            dirpath = message.content.get('dirpath', '/')
            
            # Get manifest
            files = self.file_handler.get_manifest(dirpath)
            
            # Convert to dict
            files_data = [
                {
                    'path': f.path,
                    'size': f.size,
                    'checksum': f.checksum,
                    'is_directory': f.is_directory,
                    'modified_time': f.modified_time,
                    'created_time': f.created_time,
                }
                for f in files
            ]
            
            self.logger.info(f"📋 Manifest generated: {len(files)} items")
            
            # Send response
            response = create_response(
                CMD_MANIFEST,
                files=files_data,
                total_count=len(files)
            )
            self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"❌ MANIFEST error: {e}")
            self._send_error(CMD_MANIFEST, str(e), STATUS_INTERNAL_ERROR)
    
    def _handle_checksum(self, message: Message) -> None:
        """Handle CHECKSUM command."""
        try:
            filepath = message.content.get('filepath')
            
            # Resolve path
            abs_path = self.library_manager.resolve_path(self.library_id, filepath)
            
            # Calculate checksum
            checksum = self.file_handler.get_checksum(abs_path)
            
            # Send response
            response = create_response(
                CMD_CHECKSUM,
                checksum=checksum
            )
            self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"❌ CHECKSUM error: {e}")
            self._send_error(CMD_CHECKSUM, str(e), STATUS_INTERNAL_ERROR)
    
    def _handle_stat(self, message: Message) -> None:
        """Handle STAT command."""
        try:
            filepath = message.content.get('filepath')
            
            # Resolve path
            abs_path = self.library_manager.resolve_path(self.library_id, filepath)
            
            # Get file info
            file_info = self.file_handler.get_file_info(abs_path)
            
            # Send response
            response = create_response(
                CMD_STAT,
                path=file_info.path,
                size=file_info.size,
                checksum=file_info.checksum,
                is_directory=file_info.is_directory,
                modified_time=file_info.modified_time,
                created_time=file_info.created_time
            )
            self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"❌ STAT error: {e}")
            self._send_error(CMD_STAT, str(e), STATUS_INTERNAL_ERROR)
    
    def _handle_exists(self, message: Message) -> None:
        """Handle EXISTS command."""
        try:
            filepath = message.content.get('filepath')
            
            # Resolve path
            abs_path = self.library_manager.resolve_path(self.library_id, filepath)
            
            # Check existence
            exists = self.file_handler.file_exists(abs_path)
            
            # Send response
            response = create_response(
                CMD_EXISTS,
                exists=exists
            )
            self._send_message(response)
            
        except Exception as e:
            self.logger.error(f"❌ EXISTS error: {e}")
            self._send_error(CMD_EXISTS, str(e), STATUS_INTERNAL_ERROR)
    
    def _handle_ping(self, message: Message) -> None:
        """Handle PING command."""
        response = create_response(CMD_PING)
        self._send_message(response)
    
    def _handle_disconnect(self, message: Message) -> None:
        """Handle DISCONNECT command."""
        self.logger.info(f"👋 Client disconnecting")
        response = create_response(CMD_DISCONNECT)
        self._send_message(response)
        self.running = False
    
    def _send_message(self, message: Message) -> None:
        """
        Send a protocol message.
        
        Args:
            message: Message to send
        """
        data = message.serialize()
        send_all(self.socket, data)
    
    def _send_error(self, command: str, error_message: str, status_code: int) -> None:
        """
        Send an error response.
        
        Args:
            command: Command that caused the error
            error_message: Error description
            status_code: HTTP-style status code
        """
        response = create_error_response(command, error_message, status_code)
        self._send_message(response)
    
    def _cleanup(self) -> None:
        """Clean up connection resources."""
        if self.session_id:
            self.session_manager.close_session(self.session_id)
        
        try:
            self.socket.close()
        except Exception:
            pass
        
        self.logger.info(f"🔌 Connection closed: {self.address[0]}:{self.address[1]}")
