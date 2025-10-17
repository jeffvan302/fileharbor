"""
FileHarbor Network Protocol

Defines the message structure and serialization for client-server communication.
"""

import json
import struct
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum

from fileharbor.common.constants import (
    MESSAGE_HEADER_SIZE,
    MESSAGE_ENCODING,
    PROTOCOL_VERSION,
    STATUS_SUCCESS,
    STATUS_INTERNAL_ERROR,
    CMD_HANDSHAKE,
    CMD_PUT_START,
    CMD_GET_START,
)
from fileharbor.common.exceptions import ProtocolError, InvalidMessageError


class MessageType(Enum):
    """Message type enumeration."""
    REQUEST = 'REQUEST'
    RESPONSE = 'RESPONSE'
    DATA = 'DATA'


@dataclass
class MessageHeader:
    """
    Fixed-size message header.
    
    Structure (1024 bytes):
    - Version: 16 bytes (string)
    - Message Type: 16 bytes (REQUEST/RESPONSE/DATA)
    - Command: 64 bytes (command name)
    - Content Length: 8 bytes (uint64)
    - Status Code: 4 bytes (int32)
    - Flags: 4 bytes (reserved for future use)
    - Checksum: 32 bytes (SHA-256 of content)
    - Reserved: 880 bytes (padding for future extensions)
    """
    version: str = PROTOCOL_VERSION
    message_type: str = MessageType.REQUEST.value
    command: str = ''
    content_length: int = 0
    status_code: int = STATUS_SUCCESS
    flags: int = 0
    checksum: str = ''
    
    def serialize(self) -> bytes:
        """
        Serialize header to fixed-size bytes.
        
        Returns:
            1024 bytes of header data
        """
        # Pack structured data
        header = struct.pack(
            '16s16s64sQII32s880s',
            self.version.encode(MESSAGE_ENCODING)[:16],
            self.message_type.encode(MESSAGE_ENCODING)[:16],
            self.command.encode(MESSAGE_ENCODING)[:64],
            self.content_length,
            self.status_code,
            self.flags,
            self.checksum.encode(MESSAGE_ENCODING)[:32],
            b'',  # Reserved space
        )
        
        return header
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'MessageHeader':
        """
        Deserialize header from bytes.
        
        Args:
            data: 1024 bytes of header data
            
        Returns:
            MessageHeader instance
            
        Raises:
            InvalidMessageError: If data is invalid
        """
        if len(data) != MESSAGE_HEADER_SIZE:
            raise InvalidMessageError(
                f"Invalid header size: expected {MESSAGE_HEADER_SIZE}, got {len(data)}"
            )
        
        try:
            unpacked = struct.unpack('16s16s64sQII32s880s', data)
            
            return cls(
                version=unpacked[0].decode(MESSAGE_ENCODING).rstrip('\x00'),
                message_type=unpacked[1].decode(MESSAGE_ENCODING).rstrip('\x00'),
                command=unpacked[2].decode(MESSAGE_ENCODING).rstrip('\x00'),
                content_length=unpacked[3],
                status_code=unpacked[4],
                flags=unpacked[5],
                checksum=unpacked[6].decode(MESSAGE_ENCODING).rstrip('\x00'),
            )
        except Exception as e:
            raise InvalidMessageError(f"Failed to deserialize header: {e}")


@dataclass
class Message:
    """
    Complete protocol message.
    
    A message consists of a fixed header followed by variable-length JSON content.
    """
    header: MessageHeader
    content: Dict[str, Any] = field(default_factory=dict)
    
    def serialize(self) -> bytes:
        """
        Serialize complete message to bytes.
        
        Returns:
            Header + JSON content as bytes
        """
        # Serialize content to JSON
        content_bytes = json.dumps(self.content).encode(MESSAGE_ENCODING)
        
        # Update header with content information
        self.header.content_length = len(content_bytes)
        
        # Calculate checksum if content exists
        if content_bytes:
            import hashlib
            self.header.checksum = hashlib.sha256(content_bytes).hexdigest()
        
        # Serialize header
        header_bytes = self.header.serialize()
        
        return header_bytes + content_bytes
    
    @classmethod
    def deserialize(cls, header_data: bytes, content_data: bytes) -> 'Message':
        """
        Deserialize message from header and content bytes.
        
        Args:
            header_data: 1024 bytes of header
            content_data: Variable-length content
            
        Returns:
            Message instance
            
        Raises:
            InvalidMessageError: If message is invalid
        """
        header = MessageHeader.deserialize(header_data)
        
        # Verify content length
        if len(content_data) != header.content_length:
            raise InvalidMessageError(
                f"Content length mismatch: expected {header.content_length}, "
                f"got {len(content_data)}"
            )
        
        # Verify checksum if present
        if header.checksum and content_data:
            import hashlib
            actual_checksum = hashlib.sha256(content_data).hexdigest()
            if actual_checksum != header.checksum:
                raise InvalidMessageError(
                    f"Checksum mismatch: expected {header.checksum}, got {actual_checksum}"
                )
        
        # Parse JSON content
        try:
            content = json.loads(content_data.decode(MESSAGE_ENCODING)) if content_data else {}
        except json.JSONDecodeError as e:
            raise InvalidMessageError(f"Failed to parse JSON content: {e}")
        
        return cls(header=header, content=content)


# ============================================================================
# Message Builders
# ============================================================================

def create_request(command: str, **kwargs) -> Message:
    """
    Create a request message.
    
    Args:
        command: Command name
        **kwargs: Request parameters
        
    Returns:
        Message instance
    """
    header = MessageHeader(
        message_type=MessageType.REQUEST.value,
        command=command,
    )
    return Message(header=header, content=kwargs)


def create_response(
    command: str,
    status_code: int = STATUS_SUCCESS,
    **kwargs
) -> Message:
    """
    Create a response message.
    
    Args:
        command: Original command being responded to
        status_code: HTTP-style status code
        **kwargs: Response data
        
    Returns:
        Message instance
    """
    header = MessageHeader(
        message_type=MessageType.RESPONSE.value,
        command=command,
        status_code=status_code,
    )
    return Message(header=header, content=kwargs)


def create_error_response(
    command: str,
    error_message: str,
    status_code: int = STATUS_INTERNAL_ERROR,
    **kwargs
) -> Message:
    """
    Create an error response message.
    
    Args:
        command: Original command that caused the error
        error_message: Error description
        status_code: HTTP-style error code
        **kwargs: Additional error details
        
    Returns:
        Message instance
    """
    content = {
        'error': error_message,
        **kwargs
    }
    return create_response(command, status_code=status_code, **content)


def create_data_message(command: str, data: bytes) -> Tuple[Message, bytes]:
    """
    Create a data message (header + raw binary data).
    
    This is used for efficient binary transfer (like file chunks).
    
    Args:
        command: Command associated with this data
        data: Binary data payload
        
    Returns:
        Tuple of (Message with header info, raw data bytes)
    """
    header = MessageHeader(
        message_type=MessageType.DATA.value,
        command=command,
        content_length=len(data),
    )
    
    # Calculate checksum of data
    import hashlib
    header.checksum = hashlib.sha256(data).hexdigest()
    
    message = Message(header=header, content={})
    return message, data


# ============================================================================
# Convenience Request Creation Functions
# ============================================================================

def create_handshake_request(library_id: str, client_capabilities: dict) -> Message:
    """
    Create a handshake request message.
    
    Args:
        library_id: Library identifier
        client_capabilities: Dictionary of client capabilities
        
    Returns:
        Message instance
    """
    return create_request(
        CMD_HANDSHAKE,
        library_id=library_id,
        client_capabilities=client_capabilities
    )


def create_put_start_request(
    filepath: str,
    file_size: int,
    checksum: str,
    chunk_size: int,
    resume: bool = False
) -> Message:
    """
    Create a PUT_START request message.
    
    Args:
        filepath: Remote file path
        file_size: Size of file in bytes
        checksum: File checksum
        chunk_size: Transfer chunk size
        resume: Whether to resume interrupted transfer
        
    Returns:
        Message instance
    """
    return create_request(
        CMD_PUT_START,
        filepath=filepath,
        file_size=file_size,
        checksum=checksum,
        chunk_size=chunk_size,
        resume=resume
    )


def create_get_start_request(filepath: str, offset: int = 0) -> Message:
    """
    Create a GET_START request message.
    
    Args:
        filepath: Remote file path
        offset: Byte offset to start download from (for resume)
        
    Returns:
        Message instance
    """
    return create_request(
        CMD_GET_START,
        filepath=filepath,
        offset=offset
    )


# ============================================================================
# Protocol Helper Functions
# ============================================================================

def validate_protocol_version(version: str) -> bool:
    """
    Check if protocol version is compatible.
    
    Args:
        version: Protocol version string (e.g., "1.0.0")
        
    Returns:
        True if compatible, False otherwise
    """
    try:
        # Simple major version check
        client_major = int(version.split('.')[0])
        server_major = int(PROTOCOL_VERSION.split('.')[0])
        return client_major == server_major
    except (ValueError, IndexError):
        return False


def is_request(message: Message) -> bool:
    """Check if message is a request."""
    return message.header.message_type == MessageType.REQUEST.value


def is_response(message: Message) -> bool:
    """Check if message is a response."""
    return message.header.message_type == MessageType.RESPONSE.value


def is_data(message: Message) -> bool:
    """Check if message is a data message."""
    return message.header.message_type == MessageType.DATA.value


def is_success(message: Message) -> bool:
    """Check if response indicates success (2xx status code)."""
    return 200 <= message.header.status_code < 300


def is_error(message: Message) -> bool:
    """Check if response indicates error (4xx or 5xx status code)."""
    return message.header.status_code >= 400


# ============================================================================
# Request/Response Data Structures
# ============================================================================

@dataclass
class HandshakeRequest:
    """Handshake request from client."""
    library_id: str
    protocol_version: str = PROTOCOL_VERSION
    client_info: Dict[str, str] = field(default_factory=dict)


@dataclass
class HandshakeResponse:
    """Handshake response from server."""
    session_id: str
    server_capabilities: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PutStartRequest:
    """Start a file upload."""
    filepath: str
    file_size: int
    checksum: str
    chunk_size: int
    modified_time: Optional[float] = None
    created_time: Optional[float] = None
    resume: bool = False
    resume_offset: int = 0


@dataclass
class PutStartResponse:
    """Response to PUT_START request."""
    temp_filepath: str
    resume_offset: int = 0


@dataclass
class PutChunkRequest:
    """Upload a file chunk."""
    filepath: str
    offset: int
    chunk_size: int
    is_final: bool = False


@dataclass
class GetStartRequest:
    """Start a file download."""
    filepath: str
    offset: int = 0
    chunk_size: Optional[int] = None


@dataclass
class GetStartResponse:
    """Response to GET_START request."""
    file_size: int
    checksum: str
    chunk_size: int


@dataclass
class FileInfo:
    """File metadata."""
    path: str
    size: int
    checksum: str
    created_time: float
    modified_time: float
    is_directory: bool = False
    permissions: Optional[str] = None


@dataclass
class ManifestResponse:
    """File manifest response."""
    files: list[FileInfo]
    total_count: int
    total_size: int


# ============================================================================
# Message Parsing Helpers
# ============================================================================

def parse_handshake_request(message: Message) -> HandshakeRequest:
    """Parse handshake request from message."""
    return HandshakeRequest(**message.content)


def parse_put_start_request(message: Message) -> PutStartRequest:
    """Parse PUT_START request from message."""
    return PutStartRequest(**message.content)


def parse_put_start_response(message: Message) -> PutStartResponse:
    """Parse PUT_START response from message."""
    return PutStartResponse(**message.content)


def parse_get_start_request(message: Message) -> GetStartRequest:
    """Parse GET_START request from message."""
    return GetStartRequest(**message.content)


def parse_get_start_response(message: Message) -> GetStartResponse:
    """Parse GET_START response from message."""
    return GetStartResponse(**message.content)
