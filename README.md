# FileHarbor

**Secure File Transfer Library with mTLS Authentication**

FileHarbor is a Python library for secure, resumable file transfers between clients and servers using mutual TLS (mTLS) authentication. It provides a robust solution for transferring files with strong security guarantees, built-in integrity checking, and support for resuming interrupted transfers.

## Features

### Security
- **Mutual TLS (mTLS) Authentication**: Client and server authenticate each other using X.509 certificates
- **Self-Signed CA**: Built-in Certificate Authority for generating and signing client certificates
- **Certificate Revocation**: Support for Certificate Revocation Lists (CRL)
- **Encrypted Configuration**: Optional AES-256-GCM encryption for configuration files
- **Path Traversal Protection**: Robust validation prevents directory traversal attacks

### File Operations
- **Resumable Transfers**: Automatic resume of interrupted uploads and downloads
- **Chunked Transfer**: Configurable chunk sizes for efficient memory usage
- **File Locking**: Prevents concurrent writes to the same file
- **Metadata Preservation**: Maintains file timestamps across transfers
- **Checksum Verification**: SHA-256 checksums ensure data integrity

### Performance
- **Multi-threaded Server**: Concurrent client handling with configurable thread pool
- **Rate Limiting**: Per-client bandwidth throttling
- **Connection Pooling**: Efficient connection reuse on client side
- **Streaming I/O**: Memory-efficient handling of large files
- **Optional Compression**: zlib compression for network transfer

### Management
- **Library System**: Organize files into logical libraries with access control
- **Access Control**: Fine-grained permissions per client per library
- **Interactive Configuration Tool**: User-friendly CLI for server setup
- **Audit Logging**: Comprehensive logging of all operations
- **Progress Callbacks**: Real-time transfer progress monitoring

## Installation

### From PyPI (when published)
```bash
pip install fileharbor
```

### From Source
```bash
git clone https://github.com/yourusername/fileharbor.git
cd fileharbor
pip install -e .
```

### Development Installation
```bash
pip install -e ".[dev]"
```

## Quick Start

### 1. Create Server Configuration

Start the configuration tool:
```bash
fileharbor-config /path/to/server_config.json
```

The tool will guide you through:
- Creating a Certificate Authority
- Setting up libraries
- Generating client certificates
- Configuring server settings

### 2. Export Client Configuration

In the configuration tool, export a client configuration for your library. This will create a `client_config.json` file that contains:
- Server connection details
- Client certificate and private key
- Library access information

### 3. Start the Server

```bash
fileharbor-server /path/to/server_config.json
```

If your configuration is encrypted:
```bash
fileharbor-server /path/to/server_config.json --password mypassword
```

### 4. Use the Client Library

```python
from fileharbor import FileHarborClient

# Connect to server
with FileHarborClient('client_config.json', password='secret') as client:
    # Upload a file
    client.upload('local_file.txt', 'remote_file.txt')
    
    # Download a file
    client.download('remote_file.txt', 'local_copy.txt')
    
    # List files
    files = client.list_files('/')
    for file_info in files:
        print(f"{file_info['path']} - {file_info['size']} bytes")
    
    # Delete a file
    client.delete('remote_file.txt')
```

### Progress Monitoring

```python
def progress_callback(bytes_transferred, bytes_total, rate_bps, eta_seconds):
    percentage = (bytes_transferred / bytes_total) * 100
    rate_mbps = rate_bps / (1024 * 1024)
    print(f"Progress: {percentage:.1f}% - {rate_mbps:.2f} MB/s - ETA: {eta_seconds}s")

with FileHarborClient('client_config.json') as client:
    client.upload(
        'large_file.bin',
        'remote_file.bin',
        progress_callback=progress_callback
    )
```

### Async Support

```python
from fileharbor import AsyncFileHarborClient

async def transfer_files():
    async with AsyncFileHarborClient('client_config.json') as client:
        await client.upload_async('local_file.txt', 'remote_file.txt')
        await client.download_async('remote_file.txt', 'local_copy.txt')

import asyncio
asyncio.run(transfer_files())
```

## Configuration

### Server Configuration Format

```json
{
  "version": "1.0.0",
  "server": {
    "host": "0.0.0.0",
    "port": 8443,
    "max_connections": 100,
    "worker_threads": 4,
    "idle_timeout": 300,
    "chunk_size": 8388608
  },
  "security": {
    "ca_certificate": "-----BEGIN CERTIFICATE-----\n...",
    "ca_private_key": "-----BEGIN PRIVATE KEY-----\n...",
    "crl": []
  },
  "libraries": {
    "lib-uuid-1": {
      "name": "Production Data",
      "path": "/data/production",
      "authorized_clients": ["client-uuid-1", "client-uuid-2"],
      "rate_limit_bps": 0,
      "idle_timeout": 300
    }
  },
  "clients": {
    "client-uuid-1": {
      "name": "Web Application",
      "certificate": "-----BEGIN CERTIFICATE-----\n...",
      "created": "2025-10-16T12:00:00.000000Z",
      "revoked": false
    }
  },
  "logging": {
    "level": "INFO",
    "file": null,
    "max_size": 10485760,
    "backup_count": 5
  }
}
```

### Client Configuration Format

```json
{
  "version": "1.0.0",
  "server": {
    "host": "fileserver.example.com",
    "port": 8443,
    "ca_certificate": "-----BEGIN CERTIFICATE-----\n..."
  },
  "client": {
    "certificate": "-----BEGIN CERTIFICATE-----\n...",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...",
    "library_id": "lib-uuid-1"
  },
  "transfer": {
    "chunk_size": 8388608,
    "compression": false,
    "verify_checksums": true
  }
}
```

## Architecture

### Components

1. **Server** (`fileharbor-server`): Handles incoming connections, authenticates clients, and processes file operations
2. **Client Library** (`fileharbor.client`): Python API for applications to transfer files
3. **Configuration Tool** (`fileharbor-config`): Interactive CLI for managing server configuration

### Security Model

- Each server has a Certificate Authority (CA) that signs all client certificates
- Clients authenticate with their certificate during TLS handshake
- Server validates client certificate against CA and CRL
- Each library has an access control list of authorized clients
- All communication is encrypted using TLS 1.3

### File Transfer Protocol

FileHarbor uses a custom protocol over TLS:

1. **Handshake**: Client authenticates and specifies library
2. **Commands**: Client sends operations (PUT, GET, DELETE, etc.)
3. **Chunked Transfer**: Large files transferred in configurable chunks
4. **Checksum Verification**: SHA-256 checksums verified on both ends
5. **Resume Support**: Partial transfers can be resumed from last checkpoint

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/fileharbor
```

### Type Checking

```bash
mypy src/fileharbor
```

## Requirements

- Python 3.13 or higher
- cryptography >= 42.0.0

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please read CONTRIBUTING.md for guidelines.

## Security

If you discover a security vulnerability, please email security@fileharbor.example.com instead of using the issue tracker.

## Roadmap

- [ ] Windows service support
- [ ] systemd service configuration
- [ ] Web-based management interface
- [ ] Advanced monitoring and metrics
- [ ] Cloud storage backend support (S3, Azure Blob, etc.)
- [ ] Bandwidth scheduling
- [ ] Multi-region replication

## Support

- Documentation: https://fileharbor.readthedocs.io
- Issues: https://github.com/yourusername/fileharbor/issues
- Discussions: https://github.com/yourusername/fileharbor/discussions
