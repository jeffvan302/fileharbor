"""
End-to-End Test Scenarios for FileHarbor

Complete workflows from configuration to file transfer.
"""

import pytest
import tempfile
import time
import threading
from pathlib import Path

from fileharbor import FileHarborServer, FileHarborClient
from fileharbor.common.config_schema import (
    ServerConfig,
    ClientConfig,
    create_default_server_config,
    create_default_client_config,
)
from fileharbor.common.crypto import generate_ca, generate_client_certificate


class TestEndToEndScenarios:
    """End-to-end test scenarios simulating real usage."""
    
    @pytest.fixture
    def complete_setup(self):
        """Complete FileHarbor setup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            
            # Create library directory
            library_path = temp_dir / "library"
            library_path.mkdir()
            
            # Generate certificates
            ca_cert, ca_key = generate_ca("E2E Test CA")
            client_id = "e2e-client"
            client_cert, client_key = generate_client_certificate(
                ca_cert, ca_key, client_id, "E2E Test Client"
            )
            
            # Create server config
            server_config = create_default_server_config()
            server_config.server.host = "127.0.0.1"
            server_config.server.port = 18444
            server_config.security.ca_certificate = ca_cert
            server_config.security.ca_private_key = ca_key
            
            # Add library
            library_id = "e2e-library"
            from fileharbor.common.config_schema import LibraryConfig, ClientRecord
            server_config.libraries[library_id] = LibraryConfig(
                name="E2E Library",
                path=str(library_path),
                authorized_clients=[client_id],
                rate_limit_bps=0,
                idle_timeout=30
            )
            
            server_config.clients[client_id] = ClientRecord(
                name="E2E Client",
                certificate=client_cert,
                revoked=False
            )
            
            # Create client config
            client_config = create_default_client_config()
            client_config.server = server_config.server
            client_config.security.certificate = client_cert
            client_config.security.private_key = client_key
            client_config.security.ca_certificate = ca_cert
            client_config.library_id = library_id
            
            # Start server
            server = FileHarborServer(server_config)
            server_thread = threading.Thread(target=server.start, daemon=True)
            server_thread.start()
            time.sleep(1)
            
            yield {
                'server': server,
                'server_config': server_config,
                'client_config': client_config,
                'temp_dir': temp_dir,
                'library_path': library_path
            }
            
            server.stop()
    
    def test_complete_backup_workflow(self, complete_setup):
        """
        Scenario: Backup local directory to server.
        
        Steps:
        1. Create local files
        2. Upload directory structure
        3. Verify all files uploaded
        4. Get manifest
        5. Verify checksums
        """
        temp_dir = complete_setup['temp_dir']
        client_config = complete_setup['client_config']
        
        # 1. Create local directory structure
        local_dir = temp_dir / "backup_source"
        local_dir.mkdir()
        
        (local_dir / "documents").mkdir()
        (local_dir / "documents" / "report.txt").write_text("Quarterly Report")
        (local_dir / "documents" / "data.csv").write_text("col1,col2\n1,2\n3,4")
        
        (local_dir / "images").mkdir()
        (local_dir / "images" / "photo.jpg").write_bytes(b"JPEG_DATA")
        
        # 2. Upload directory structure
        with FileHarborClient(client_config) as client:
            # Create remote directories
            client.mkdir("documents")
            client.mkdir("images")
            
            # Upload files
            for file_path in local_dir.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(local_dir)
                    client.upload(str(file_path), str(relative_path))
        
        # 3. Verify all files uploaded
        with FileHarborClient(client_config) as client:
            assert client.exists("documents/report.txt")
            assert client.exists("documents/data.csv")
            assert client.exists("images/photo.jpg")
            
            # 4. Get manifest
            manifest = client.get_manifest()
            
            # 5. Verify checksums
            from fileharbor.utils.checksum import calculate_file_checksum
            
            files_dict = {f.path: f for f in manifest if not f.is_directory}
            
            for file_path in local_dir.rglob("*"):
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(local_dir))
                    
                    if relative_path in files_dict:
                        local_checksum = calculate_file_checksum(file_path)
                        remote_checksum = files_dict[relative_path].checksum
                        
                        assert local_checksum == remote_checksum
    
    def test_sync_workflow(self, complete_setup):
        """
        Scenario: Synchronize local changes to server.
        
        Steps:
        1. Upload initial files
        2. Modify local files
        3. Detect changes via checksum
        4. Upload only changed files
        5. Verify synchronization
        """
        temp_dir = complete_setup['temp_dir']
        client_config = complete_setup['client_config']
        
        local_dir = temp_dir / "sync_source"
        local_dir.mkdir()
        
        # 1. Upload initial files
        files = {
            "file1.txt": "Version 1",
            "file2.txt": "Version 1",
            "file3.txt": "Version 1"
        }
        
        for filename, content in files.items():
            (local_dir / filename).write_text(content)
        
        with FileHarborClient(client_config) as client:
            for filename in files:
                client.upload(str(local_dir / filename), f"sync/{filename}")
        
        # 2. Modify some files
        (local_dir / "file1.txt").write_text("Version 2")
        (local_dir / "file3.txt").write_text("Version 2")
        
        # 3 & 4. Detect changes and upload
        from fileharbor.utils.checksum import calculate_file_checksum
        
        with FileHarborClient(client_config) as client:
            # Get remote manifest
            manifest = client.get_manifest()
            remote_checksums = {
                f.path: f.checksum 
                for f in manifest 
                if not f.is_directory
            }
            
            # Check each local file
            uploaded = []
            for filename in files:
                local_file = local_dir / filename
                local_checksum = calculate_file_checksum(local_file)
                remote_path = f"sync/{filename}"
                
                remote_checksum = remote_checksums.get(remote_path)
                
                if local_checksum != remote_checksum:
                    client.upload(str(local_file), remote_path)
                    uploaded.append(filename)
        
        # 5. Verify only changed files were uploaded
        assert "file1.txt" in uploaded
        assert "file3.txt" in uploaded
        assert "file2.txt" not in uploaded  # Unchanged
    
    def test_disaster_recovery_workflow(self, complete_setup):
        """
        Scenario: Restore from backup after data loss.
        
        Steps:
        1. Upload backup files
        2. Simulate data loss (delete local)
        3. Download all files from server
        4. Verify restoration
        """
        temp_dir = complete_setup['temp_dir']
        client_config = complete_setup['client_config']
        
        local_dir = temp_dir / "original"
        local_dir.mkdir()
        
        # 1. Create and upload files
        test_data = {
            "important.txt": "Critical data",
            "config.json": '{"key": "value"}',
            "data.csv": "a,b,c\n1,2,3"
        }
        
        for filename, content in test_data.items():
            (local_dir / filename).write_text(content)
        
        with FileHarborClient(client_config) as client:
            for filename in test_data:
                client.upload(str(local_dir / filename), f"backup/{filename}")
        
        # 2. Simulate data loss
        for file in local_dir.iterdir():
            file.unlink()
        local_dir.rmdir()
        
        # 3. Restore from backup
        restore_dir = temp_dir / "restored"
        restore_dir.mkdir()
        
        with FileHarborClient(client_config) as client:
            # List backup files
            files = client.list_directory("backup")
            
            # Download each file
            for file_info in files:
                if not file_info.is_directory:
                    local_path = restore_dir / Path(file_info.path).name
                    client.download(file_info.path, str(local_path))
        
        # 4. Verify restoration
        for filename, original_content in test_data.items():
            restored_file = restore_dir / filename
            assert restored_file.exists()
            assert restored_file.read_text() == original_content
    
    def test_concurrent_user_workflow(self, complete_setup):
        """
        Scenario: Multiple users accessing shared library.
        
        Note: With library mutex, users access sequentially.
        
        Steps:
        1. User 1 uploads files
        2. User 2 downloads files
        3. User 2 uploads different files
        4. User 1 downloads new files
        """
        temp_dir = complete_setup['temp_dir']
        client_config = complete_setup['client_config']
        
        # User 1 actions
        user1_dir = temp_dir / "user1"
        user1_dir.mkdir()
        (user1_dir / "user1_file.txt").write_text("From User 1")
        
        with FileHarborClient(client_config) as client:
            client.upload(str(user1_dir / "user1_file.txt"), "shared/user1_file.txt")
        
        # User 2 actions
        user2_dir = temp_dir / "user2"
        user2_dir.mkdir()
        
        with FileHarborClient(client_config) as client:
            # Download user 1's file
            client.download("shared/user1_file.txt", str(user2_dir / "user1_file.txt"))
            
            # Upload own file
            (user2_dir / "user2_file.txt").write_text("From User 2")
            client.upload(str(user2_dir / "user2_file.txt"), "shared/user2_file.txt")
        
        # User 1 gets user 2's file
        with FileHarborClient(client_config) as client:
            client.download("shared/user2_file.txt", str(user1_dir / "user2_file.txt"))
        
        # Verify both users have both files
        assert (user1_dir / "user1_file.txt").read_text() == "From User 1"
        assert (user1_dir / "user2_file.txt").read_text() == "From User 2"
        assert (user2_dir / "user1_file.txt").read_text() == "From User 1"
        assert (user2_dir / "user2_file.txt").read_text() == "From User 2"
    
    def test_large_file_workflow(self, complete_setup):
        """
        Scenario: Transfer large file with progress tracking.
        
        Steps:
        1. Generate large file
        2. Upload with progress
        3. Verify checksum
        4. Download with progress
        5. Verify downloaded file
        """
        temp_dir = complete_setup['temp_dir']
        client_config = complete_setup['client_config']
        
        # 1. Generate 10MB file
        large_file = temp_dir / "large_file.bin"
        chunk = b"X" * (1024 * 1024)  # 1MB
        with open(large_file, 'wb') as f:
            for _ in range(10):
                f.write(chunk)
        
        from fileharbor.utils.checksum import calculate_file_checksum
        original_checksum = calculate_file_checksum(large_file)
        
        # 2. Upload with progress tracking
        progress_updates = []
        
        def track_progress(progress):
            progress_updates.append(progress.percentage)
        
        with FileHarborClient(client_config) as client:
            client.upload(
                str(large_file),
                "large/large_file.bin",
                progress_callback=track_progress
            )
            
            # 3. Verify checksum on server
            server_checksum = client.get_checksum("large/large_file.bin")
            assert server_checksum == original_checksum
        
        # Should have received multiple progress updates
        assert len(progress_updates) > 1
        assert progress_updates[-1] == 100.0
        
        # 4. Download with progress
        download_file = temp_dir / "downloaded_large.bin"
        
        with FileHarborClient(client_config) as client:
            client.download(
                "large/large_file.bin",
                str(download_file),
                progress_callback=track_progress
            )
        
        # 5. Verify downloaded file
        downloaded_checksum = calculate_file_checksum(download_file)
        assert downloaded_checksum == original_checksum


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
