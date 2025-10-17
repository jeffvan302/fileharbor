"""
FileHarbor Client Connection

TLS socket connection to FileHarbor server.
"""

import socket
import ssl
import tempfile
import os
from typing import Optional

from fileharbor.common.config_schema import ClientConfig
from fileharbor.common.protocol import (
    Message,
    MessageHeader,
    create_handshake_request,
    create_response,
    MESSAGE_HEADER_SIZE,
)
from fileharbor.common.constants import (
    CMD_HANDSHAKE,
    CMD_PING,
    CMD_DISCONNECT,
    STATUS_SUCCESS,
)
from fileharbor.common.exceptions import (
    ConnectionError as FHConnectionError,
    AuthenticationError,
    ProtocolError,
)
from fileharbor.utils.network_utils import send_all, recv_all


class Connection:
    """
    Represents a TLS connection to FileHarbor server.
    
    Handles SSL/TLS setup, handshake, and message exchange.
    """
    
    def __init__(self, config: ClientConfig):
        """
        Initialize connection.
        
        Args:
            config: Client configuration
        """
        self.config = config
        self.socket: Optional[socket.socket] = None
        self.ssl_socket: Optional[ssl.SSLSocket] = None
        self.session_id: Optional[str] = None
        self.connected = False
    
    def connect(self) -> None:
        """
        Connect to server and perform handshake.
        
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        try:
            # Create SSL context
            ssl_context = self._create_ssl_context()
            
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.config.connection.timeout)
            
            # Connect
            self.socket.connect((self.config.server.host, self.config.server.port))
            
            # Wrap with SSL
            self.ssl_socket = ssl_context.wrap_socket(
                self.socket,
                server_hostname=self.config.server.host
            )
            
            # Perform application-level handshake
            self._perform_handshake()
            
            self.connected = True
            
        except socket.timeout:
            raise FHConnectionError(f"Connection timeout to {self.config.server.host}:{self.config.server.port}")
        except socket.error as e:
            raise FHConnectionError(f"Failed to connect: {e}")
        except ssl.SSLError as e:
            raise FHConnectionError(f"SSL/TLS error: {e}")
        except Exception as e:
            self.close()
            raise FHConnectionError(f"Connection failed: {e}")
    
    def disconnect(self) -> None:
        """Disconnect from server gracefully."""
        if not self.connected:
            return
        
        try:
            # Send DISCONNECT command
            disconnect_msg = create_response(CMD_DISCONNECT)
            self.send_message(disconnect_msg)
            
            # Wait for response
            self.receive_message()
        except Exception:
            pass
        finally:
            self.close()
    
    def close(self) -> None:
        """Close the connection without notifying server."""
        self.connected = False
        self.session_id = None
        
        if self.ssl_socket:
            try:
                self.ssl_socket.close()
            except Exception:
                pass
            self.ssl_socket = None
        
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
    
    def send_message(self, message: Message) -> None:
        """
        Send a protocol message.
        
        Args:
            message: Message to send
            
        Raises:
            ConnectionError: If send fails
        """
        if not self.connected or not self.ssl_socket:
            raise FHConnectionError("Not connected")
        
        try:
            data = message.serialize()
            send_all(self.ssl_socket, data)
        except Exception as e:
            raise FHConnectionError(f"Failed to send message: {e}")
    
    def receive_message(self) -> Message:
        """
        Receive a protocol message.
        
        Returns:
            Parsed message
            
        Raises:
            ConnectionError: If receive fails
            ProtocolError: If message is invalid
        """
        if not self.connected or not self.ssl_socket:
            raise FHConnectionError("Not connected")
        
        try:
            # Receive header
            header_data = recv_all(self.ssl_socket, MESSAGE_HEADER_SIZE)
            if not header_data:
                raise FHConnectionError("Connection closed by server")
            
            header = MessageHeader.deserialize(header_data)
            
            # Receive content
            content_data = b''
            if header.content_length > 0:
                content_data = recv_all(self.ssl_socket, header.content_length)
            
            # Parse message
            message = Message.deserialize(header_data, content_data)
            
            # Check for errors
            if message.header.status_code != STATUS_SUCCESS:
                error_msg = message.content.get('error', 'Unknown error')
                raise ProtocolError(f"Server error: {error_msg}")
            
            return message
            
        except FHConnectionError:
            raise
        except ProtocolError:
            raise
        except Exception as e:
            raise FHConnectionError(f"Failed to receive message: {e}")
    
    def ping(self) -> bool:
        """
        Send ping to check connection.
        
        Returns:
            True if server responds
        """
        try:
            ping_msg = create_response(CMD_PING)
            self.send_message(ping_msg)
            response = self.receive_message()
            return response.header.command == CMD_PING
        except Exception:
            return False
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """
        Create SSL context with client certificate.
        
        Returns:
            Configured SSL context
        """
        # Create context for TLS 1.3
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        
        # Load CA certificate for server verification
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as ca_file:
            ca_file.write(self.config.security.ca_certificate)
            ca_path = ca_file.name
        
        try:
            context.load_verify_locations(ca_path)
        finally:
            os.unlink(ca_path)
        
        # Load client certificate and key
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as cert_file:
            cert_file.write(self.config.security.certificate)
            cert_path = cert_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as key_file:
            key_file.write(self.config.security.private_key)
            key_path = key_file.name
        
        try:
            context.load_cert_chain(cert_path, key_path)
        finally:
            os.unlink(cert_path)
            os.unlink(key_path)
        
        # Require server certificate verification
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        
        return context
    
    def _perform_handshake(self) -> None:
        """
        Perform application-level handshake.
        
        Raises:
            AuthenticationError: If handshake fails
        """
        # Create handshake request
        handshake_msg = create_handshake_request(
            library_id=self.config.library_id,
            client_capabilities={
                'resumable_transfers': True,
                'compression': False,
            }
        )
        
        # Send handshake
        self.send_message(handshake_msg)
        
        # Receive response
        response = self.receive_message()
        
        if response.header.command != CMD_HANDSHAKE:
            raise AuthenticationError("Invalid handshake response")
        
        # Extract session ID
        self.session_id = response.content.get('session_id')
        if not self.session_id:
            raise AuthenticationError("No session ID received")
    
    def is_connected(self) -> bool:
        """
        Check if connection is active.
        
        Returns:
            True if connected
        """
        return self.connected and self.ssl_socket is not None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
