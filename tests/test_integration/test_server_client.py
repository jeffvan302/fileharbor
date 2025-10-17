"""
Integration Tests for FileHarbor Server and Client

Tests the complete system with server and client working together.
"""

import pytest
import tempfile
import threading
import time
from pathlib import Path
import secrets

from fileharbor import FileHarborServer, FileHarborClient
from fileharbor.common.config_schema import (
    ServerConfig,
    ClientConfig,
    ServerSettings,
    SecurityConfig,
    LibraryConfig,
    ClientRecord,
    LoggingConfig,
    TransferSettings,
    ConnectionSettings,
)
from fileharbor.common.crypto import generate_ca, generate_client_certificate


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_library_path(temp_dir):
    """Create test library directory."""
    library_path = temp_dir / "test_library"
    library_path.mkdir()
    return library_path


@pytest.fixture
def server_config(test_library_path):
    """Create test server configuration."""
    # Generate CA
    ca_cert, ca_key = generate_ca("Test CA")
    
    # Generate client certificate
    client_id = secrets.token_hex(8)
    client_cert, client_key = generate_client_certificate(
        ca_cert,
        ca_key,
        client_id,
        "Test Client"
    )
    
    # Create library
    library_id = secrets.token_hex(8)
    library = LibraryConfig(
        name="Test Library",
        path=str(test_library_path),
        authorized_clients=[client_id],
        rate_limit_bps=0,
        idle_timeout=30
    )
    
    # Create client record
    client_record = ClientRecord(
        name="Test Client",
        certificate=client_cert,
        revoked=False
    )
    
    # Create server config
    config = ServerConfig(
        version="1.0.0",
        server=ServerSettings(
            host="127.0.0.1",
            port=18443,  # Use different port for testing
            worker_threads=2,
            max_connections=5,
            idle_timeout=30,
            chunk_size=8192
        ),
        security=SecurityConfig(
            ca_certificate=ca_cert,
            ca_private_key=ca_key,
            crl=[]
        ),
        libraries={library_id: library},
        clients={client_id: client_record},
        logging=LoggingConfig(
            level="INFO",
            file=None
        )
    )
    
    return config, library_id, client_id, client_cert, client_key, ca_cert


@pytest.fixture
def client_config(server_config):
    """Create test client configuration."""
    config, library_id, client_id, client_cert, client_key, ca_cert = server_config
    
    client_cfg = ClientConfig(
        version="1.0.0",
        server=config.server,
        security=SecurityConfig(
            certificate=client_cert,
            private_key=client_key,
            ca_certificate=ca_cert,
            crl=[]
        ),
        library_id=library_id,
        connection=ConnectionSettings(
            timeout=10,
            retry_attempts=3
        ),
        transfer=TransferSettings(
            chunk_size=8192
        )
    )
    
    return client_cfg


@pytest.fixture
def running_server(server_config):
    """Start server in background thread."""
    config, *_ = server_config
    server = FileHarborServer(config)
    
    # Start server in thread
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(1)
    
    yield server
    
    # Stop server
    server.stop()


class TestIntegration:
    """Integration tests for FileHarbor system."""
    
    def test_server_startup(self, server_config):
        """Test server can start and stop."""
        config, *_ = server_config
        server = FileHarborServer(config)
        
        # Start in thread
        thread = threading.Thread(target=server.start, daemon=True)
        thread.start()
        time.sleep(0.5)
        
        # Check server is running
        assert server.running is True
        
        # Stop server
        server.stop()
        assert server.running is False
    
    def test_client_connection(self, running_server, client_config):
        """Test client can connect to server."""
        client = FileHarborClient(client_config)
        
        # Connect
        client.connect()
        assert client.is_connected()
        
        # Ping
        assert client.ping() is True
        
        # Disconnect
        client.disconnect()
        assert not client.is_connected()
    
    def test_context_manager(self, running_server, client_config):
        """Test client context manager."""
        with FileHarborClient(client_config) as client:
            assert client.is_connected()
            assert client.ping() is True
    
    def test_upload_download(self, running_server, client_config, temp_dir):
        """Test file upload and download."""
        # Create test file
        local_file = temp_dir / "test.txt"
        local_file.write_text("Hello, FileHarbor!")
        
        with FileHarborClient(client_config) as client:
            # Upload
            client.upload(str(local_file), "test.txt")
            
            # Verify exists
            assert client.exists("test.txt")
            
            # Download
            download_file = temp_dir / "downloaded.txt"
            client.download("test.txt", str(download_file))
            
            # Verify content
            assert download_file.read_text() == "Hello, FileHarbor!"
    
    def test_large_file_transfer(self, running_server, client_config, temp_dir):
        """Test transfer of larger file with chunking."""
        # Create 1MB test file
        local_file = temp_dir / "large.bin"
        local_file.write_bytes(b"X" * (1024 * 1024))
        
        with FileHarborClient(client_config) as client:
            # Upload
            client.upload(str(local_file), "large.bin")
            
            # Download
            download_file = temp_dir / "large_downloaded.bin"
            client.download("large.bin", str(download_file))
            
            # Verify size and content
            assert download_file.stat().st_size == local_file.stat().st_size
            assert download_file.read_bytes() == local_file.read_bytes()
    
    def test_resumable_upload(self, running_server, client_config, temp_dir):
        """Test resumable upload."""
        # Create test file
        local_file = temp_dir / "resume_test.txt"
        local_file.write_text("This is a test of resumable upload")
        
        with FileHarborClient(client_config) as client:
            # Start upload but don't complete (simulate interruption)
            # In real scenario, connection would drop mid-transfer
            
            # Upload with resume enabled
            client.upload(str(local_file), "resume_test.txt", resume=True)
            
            # Verify uploaded
            assert client.exists("resume_test.txt")
    
    def test_directory_operations(self, running_server, client_config):
        """Test directory operations."""
        with FileHarborClient(client_config) as client:
            # Create directory
            client.mkdir("test_dir")
            
            # Verify exists
            assert client.exists("test_dir")
            
            # List should show it
            files = client.list_directory("/")
            dir_names = [f.path for f in files if f.is_directory]
            assert "test_dir" in dir_names
            
            # Remove directory
            client.rmdir("test_dir")
            
            # Verify removed
            assert not client.exists("test_dir")
    
    def test_file_operations(self, running_server, client_config, temp_dir):
        """Test various file operations."""
        local_file = temp_dir / "ops_test.txt"
        local_file.write_text("Operations test")
        
        with FileHarborClient(client_config) as client:
            # Upload
            client.upload(str(local_file), "original.txt")
            
            # Rename
            client.rename("original.txt", "renamed.txt")
            assert not client.exists("original.txt")
            assert client.exists("renamed.txt")
            
            # Get stats
            info = client.stat("renamed.txt")
            assert info.size == local_file.stat().st_size
            assert info.checksum  # Should have checksum
            
            # Delete
            client.delete("renamed.txt")
            assert not client.exists("renamed.txt")
    
    def test_list_recursive(self, running_server, client_config, temp_dir):
        """Test recursive directory listing."""
        # Create test files
        file1 = temp_dir / "file1.txt"
        file1.write_text("File 1")
        
        file2 = temp_dir / "file2.txt"
        file2.write_text("File 2")
        
        with FileHarborClient(client_config) as client:
            # Create directory structure
            client.mkdir("subdir")
            
            # Upload files
            client.upload(str(file1), "file1.txt")
            client.upload(str(file2), "subdir/file2.txt")
            
            # List recursively
            files = client.list_directory("/", recursive=True)
            paths = [f.path for f in files]
            
            assert "file1.txt" in paths
            assert "subdir" in paths or "subdir/file2.txt" in paths
    
    def test_manifest(self, running_server, client_config, temp_dir):
        """Test getting file manifest."""
        # Create and upload files
        for i in range(3):
            file = temp_dir / f"file{i}.txt"
            file.write_text(f"Content {i}")
        
        with FileHarborClient(client_config) as client:
            # Upload files
            for i in range(3):
                client.upload(str(temp_dir / f"file{i}.txt"), f"file{i}.txt")
            
            # Get manifest
            manifest = client.get_manifest()
            
            # Should have files with checksums
            file_manifest = [f for f in manifest if not f.is_directory]
            assert len(file_manifest) >= 3
            
            for f in file_manifest:
                if f.path.startswith("file"):
                    assert f.checksum  # Should have checksum
    
    def test_checksum_verification(self, running_server, client_config, temp_dir):
        """Test checksum calculation."""
        local_file = temp_dir / "checksum_test.txt"
        content = "Test checksum calculation"
        local_file.write_text(content)
        
        with FileHarborClient(client_config) as client:
            # Upload
            client.upload(str(local_file), "checksum_test.txt")
            
            # Get checksum from server
            server_checksum = client.get_checksum("checksum_test.txt")
            
            # Calculate local checksum
            from fileharbor.utils.checksum import calculate_file_checksum
            local_checksum = calculate_file_checksum(local_file)
            
            # Should match
            assert server_checksum.lower() == local_checksum.lower()
    
    def test_progress_callback(self, running_server, client_config, temp_dir):
        """Test progress callback functionality."""
        # Create larger file
        local_file = temp_dir / "progress_test.bin"
        local_file.write_bytes(b"X" * (100 * 1024))  # 100 KB
        
        progress_updates = []
        
        def progress_callback(progress):
            progress_updates.append({
                'percentage': progress.percentage,
                'bytes': progress.bytes_transferred
            })
        
        with FileHarborClient(client_config) as client:
            client.upload(
                str(local_file),
                "progress_test.bin",
                progress_callback=progress_callback
            )
        
        # Should have received progress updates
        assert len(progress_updates) > 0
        
        # Last update should be 100%
        assert progress_updates[-1]['percentage'] == 100.0
    
    def test_concurrent_operations(self, running_server, client_config, temp_dir):
        """Test multiple clients can operate concurrently."""
        # Note: With library mutex, only one client at a time per library
        # This tests that they can connect and operate sequentially
        
        file1 = temp_dir / "concurrent1.txt"
        file1.write_text("Concurrent 1")
        
        file2 = temp_dir / "concurrent2.txt"
        file2.write_text("Concurrent 2")
        
        # First client
        with FileHarborClient(client_config) as client1:
            client1.upload(str(file1), "concurrent1.txt")
        
        # Second client
        with FileHarborClient(client_config) as client2:
            client2.upload(str(file2), "concurrent2.txt")
            
            # Both files should exist
            assert client2.exists("concurrent1.txt")
            assert client2.exists("concurrent2.txt")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
