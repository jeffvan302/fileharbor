"""
FileHarbor Network Utilities

Network helper functions for socket operations.
"""

import socket
import ssl
from typing import Optional, Tuple

from fileharbor.common.exceptions import NetworkError, TimeoutError as FHTimeoutError


def create_socket(timeout: Optional[float] = None) -> socket.socket:
    """
    Create a TCP socket with optional timeout.
    
    Args:
        timeout: Socket timeout in seconds (None = blocking)
        
    Returns:
        Socket object
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if timeout is not None:
        sock.settimeout(timeout)
    return sock


def send_all(sock: socket.socket, data: bytes) -> None:
    """
    Send all data through socket.
    
    Ensures all data is sent, handling partial sends.
    
    Args:
        sock: Socket object
        data: Data to send
        
    Raises:
        NetworkError: If send fails
    """
    total_sent = 0
    data_length = len(data)
    
    while total_sent < data_length:
        try:
            sent = sock.send(data[total_sent:])
            if sent == 0:
                raise NetworkError("Socket connection broken")
            total_sent += sent
        except socket.timeout:
            raise FHTimeoutError("Send operation timed out")
        except socket.error as e:
            raise NetworkError(f"Send failed: {e}")


def recv_all(sock: socket.socket, length: int) -> bytes:
    """
    Receive exact amount of data from socket.
    
    Blocks until all data is received.
    
    Args:
        sock: Socket object
        length: Number of bytes to receive
        
    Returns:
        Received data
        
    Raises:
        NetworkError: If receive fails
    """
    chunks = []
    bytes_received = 0
    
    while bytes_received < length:
        try:
            chunk = sock.recv(min(length - bytes_received, 65536))
            if not chunk:
                raise NetworkError("Socket connection broken")
            chunks.append(chunk)
            bytes_received += len(chunk)
        except socket.timeout:
            raise FHTimeoutError("Receive operation timed out")
        except socket.error as e:
            raise NetworkError(f"Receive failed: {e}")
    
    return b''.join(chunks)


def recv_with_timeout(
    sock: socket.socket,
    length: int,
    timeout: float
) -> bytes:
    """
    Receive data with timeout.
    
    Args:
        sock: Socket object
        length: Maximum number of bytes to receive
        timeout: Timeout in seconds
        
    Returns:
        Received data
        
    Raises:
        TimeoutError: If operation times out
        NetworkError: If receive fails
    """
    sock.settimeout(timeout)
    try:
        return sock.recv(length)
    except socket.timeout:
        raise FHTimeoutError("Receive operation timed out")
    except socket.error as e:
        raise NetworkError(f"Receive failed: {e}")


def is_port_available(host: str, port: int) -> bool:
    """
    Check if a port is available for binding.
    
    Args:
        host: Host address
        port: Port number
        
    Returns:
        True if port is available
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        sock.close()
        return True
    except socket.error:
        return False


def get_local_ip() -> str:
    """
    Get local IP address.
    
    Returns:
        Local IP address string
    """
    try:
        # Create a socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def resolve_hostname(hostname: str) -> str:
    """
    Resolve hostname to IP address.
    
    Args:
        hostname: Hostname to resolve
        
    Returns:
        IP address string
        
    Raises:
        NetworkError: If resolution fails
    """
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror as e:
        raise NetworkError(f"Failed to resolve hostname {hostname}: {e}")


def format_address(host: str, port: int) -> str:
    """
    Format address as string.
    
    Args:
        host: Host address
        port: Port number
        
    Returns:
        Formatted address (e.g., "192.168.1.1:8443")
    """
    return f"{host}:{port}"


def parse_address(address: str) -> Tuple[str, int]:
    """
    Parse address string to host and port.
    
    Args:
        address: Address string (e.g., "192.168.1.1:8443")
        
    Returns:
        Tuple of (host, port)
        
    Raises:
        ValueError: If address format is invalid
    """
    try:
        if ':' not in address:
            raise ValueError("Address must contain port")
        host, port_str = address.rsplit(':', 1)
        port = int(port_str)
        return host, port
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid address format: {address}") from e


def set_keepalive(sock: socket.socket, idle: int = 60, interval: int = 10, count: int = 5) -> None:
    """
    Enable TCP keepalive on socket.
    
    Args:
        sock: Socket object
        idle: Seconds before starting keepalive probes
        interval: Interval between keepalive probes
        count: Number of failed probes before declaring dead
    """
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    
    # Platform-specific keepalive options
    try:
        # Linux
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, idle)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, count)
    except (AttributeError, OSError):
        # Not supported on this platform
        pass


def set_socket_buffer_size(sock: socket.socket, send_size: int = 262144, recv_size: int = 262144) -> None:
    """
    Set socket buffer sizes.
    
    Args:
        sock: Socket object
        send_size: Send buffer size in bytes (default 256KB)
        recv_size: Receive buffer size in bytes (default 256KB)
    """
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, send_size)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, recv_size)


def close_socket_gracefully(sock: socket.socket) -> None:
    """
    Close socket gracefully.
    
    Args:
        sock: Socket object
    """
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass  # Socket may already be closed
    finally:
        sock.close()
