"""
FileHarbor - Secure File Transfer Library with mTLS

A production-ready Python library for secure file transfer using mutual TLS authentication,
with support for resumable transfers, rate limiting, and comprehensive access control.

Example:
    from fileharbor import FileHarborClient
    
    with FileHarborClient('client_config.json') as client:
        client.upload('local.txt', 'remote.txt', show_progress=True)
        client.download('remote.txt', 'copy.txt', show_progress=True)
"""

from fileharbor.__version__ import __version__

# Client API
from fileharbor.client import (
    FileHarborClient,
    AsyncFileHarborClient,
    load_client_config,
    TransferProgress,
    ProgressCallback,
    create_console_progress_callback,
)

# Server API
from fileharbor.server import FileHarborServer, load_server_config

# Common types
from fileharbor.common.protocol import FileInfo
from fileharbor.common.config_schema import ClientConfig, ServerConfig

__all__ = [
    '__version__',
    # Client
    'FileHarborClient',
    'AsyncFileHarborClient',
    'load_client_config',
    'TransferProgress',
    'ProgressCallback',
    'create_console_progress_callback',
    # Server
    'FileHarborServer',
    'load_server_config',
    # Common
    'FileInfo',
    'ClientConfig',
    'ServerConfig',
]
