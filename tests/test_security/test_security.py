"""
Security Tests for FileHarbor

Tests authentication, authorization, path traversal prevention, and CRL.
"""

import pytest
import tempfile
from pathlib import Path

from fileharbor.common.validators import validate_path
from fileharbor.common.exceptions import (
    PathTraversalError,
    InvalidPathError,
    AuthenticationError,
    CertificateRevokedError,
)
from fileharbor.common.crypto import (
    generate_ca,
    generate_client_certificate,
    pem_to_certificate,
    get_certificate_fingerprint,
)
from fileharbor.server.auth import ServerAuthenticator
from fileharbor.server.library_manager import LibraryManager
from fileharbor.common.config_schema import (
    ServerConfig,
    SecurityConfig,
    LibraryConfig,
    ClientRecord,
    ServerSettings,
    LoggingConfig,
)


class TestPathSecurity:
    """Tests for path traversal prevention."""
    
    def test_valid_relative_path(self):
        """Test valid relative path is accepted."""
        with tempfile.TemporaryDirectory() as base:
            result = validate_path("documents/file.txt", base)
            assert "documents" in result
            assert "file.txt" in result
    
    def test_path_traversal_blocked(self):
        """Test path traversal attempts are blocked."""
        with tempfile.TemporaryDirectory() as base:
            # Various traversal attempts
            dangerous_paths = [
                "../../../etc/passwd",
                "docs/../../etc/passwd",
                "./../../secrets.txt",
                "..\\..\\windows\\system32",
                "docs/../../../root",
            ]
            
            for path in dangerous_paths:
                with pytest.raises(PathTraversalError):
                    validate_path(path, base)
    
    def test_absolute_path_blocked(self):
        """Test absolute paths are blocked."""
        with tempfile.TemporaryDirectory() as base:
            with pytest.raises(InvalidPathError):
                validate_path("/etc/passwd", base)
    
    def test_symlink_escape_blocked(self):
        """Test symlink escapes are blocked."""
        with tempfile.TemporaryDirectory() as base:
            base_path = Path(base)
            
            # Create directory outside base
            outside = base_path.parent / "outside"
            outside.mkdir(exist_ok=True)
            
            # Create symlink inside base pointing outside
            link = base_path / "escape"
            try:
                link.symlink_to(outside)
                
                # Following the symlink should be blocked
                with pytest.raises(PathTraversalError):
                    validate_path("escape/file.txt", base)
            finally:
                if link.exists():
                    link.unlink()
                if outside.exists():
                    outside.rmdir()
    
    def test_unicode_bypass_blocked(self):
        """Test Unicode path bypass attempts are blocked."""
        with tempfile.TemporaryDirectory() as base:
            # Unicode dots and slashes
            dangerous = [
                "docs\u2024\u2024/secrets.txt",  # Unicode dots
                "docs\u2215\u2215secrets.txt",  # Unicode slashes
            ]
            
            for path in dangerous:
                # Should either be blocked or normalized safely
                try:
                    result = validate_path(path, base)
                    # If accepted, must be within base
                    assert base in result
                except (PathTraversalError, InvalidPathError):
                    pass  # Correctly blocked


class TestAuthenticationSecurity:
    """Tests for certificate authentication and CRL."""
    
    def test_valid_certificate_accepted(self):
        """Test valid client certificate is accepted."""
        # Generate CA and client cert
        ca_cert, ca_key = generate_ca("Test CA")
        client_id = "test-client-123"
        client_cert, client_key = generate_client_certificate(
            ca_cert, ca_key, client_id, "Test Client"
        )
        
        # Create config with client
        config = ServerConfig(
            version="1.0.0",
            server=ServerSettings(
                host="127.0.0.1",
                port=8443,
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
            libraries={},
            clients={
                client_id: ClientRecord(
                    name="Test Client",
                    certificate=client_cert,
                    revoked=False
                )
            },
            logging=LoggingConfig(level="INFO", file=None)
        )
        
        # Create authenticator
        auth = ServerAuthenticator(config)
        
        # Validate certificate
        validated_id = auth.validate_client_certificate(client_cert)
        assert validated_id == client_id
    
    def test_revoked_certificate_rejected(self):
        """Test revoked certificate is rejected."""
        # Generate CA and client cert
        ca_cert, ca_key = generate_ca("Test CA")
        client_id = "revoked-client"
        client_cert, client_key = generate_client_certificate(
            ca_cert, ca_key, client_id, "Revoked Client"
        )
        
        # Get certificate serial number for CRL
        cert_obj = pem_to_certificate(client_cert)
        serial = cert_obj.serial_number
        
        # Create config with revoked client
        config = ServerConfig(
            version="1.0.0",
            server=ServerSettings(
                host="127.0.0.1",
                port=8443,
                worker_threads=2,
                max_connections=5,
                idle_timeout=30,
                chunk_size=8192
            ),
            security=SecurityConfig(
                ca_certificate=ca_cert,
                ca_private_key=ca_key,
                crl=[serial]  # Certificate revoked
            ),
            libraries={},
            clients={
                client_id: ClientRecord(
                    name="Revoked Client",
                    certificate=client_cert,
                    revoked=True
                )
            },
            logging=LoggingConfig(level="INFO", file=None)
        )
        
        # Create authenticator
        auth = ServerAuthenticator(config)
        
        # Validation should fail
        with pytest.raises(CertificateRevokedError):
            auth.validate_client_certificate(client_cert)
    
    def test_unknown_client_rejected(self):
        """Test certificate not in config is rejected."""
        # Generate CA and client cert
        ca_cert, ca_key = generate_ca("Test CA")
        client_id = "unknown-client"
        client_cert, client_key = generate_client_certificate(
            ca_cert, ca_key, client_id, "Unknown Client"
        )
        
        # Create config WITHOUT this client
        config = ServerConfig(
            version="1.0.0",
            server=ServerSettings(
                host="127.0.0.1",
                port=8443,
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
            libraries={},
            clients={},  # No clients configured
            logging=LoggingConfig(level="INFO", file=None)
        )
        
        # Create authenticator
        auth = ServerAuthenticator(config)
        
        # Validation should fail
        with pytest.raises(AuthenticationError):
            auth.validate_client_certificate(client_cert)
    
    def test_wrong_ca_rejected(self):
        """Test certificate signed by wrong CA is rejected."""
        # Generate two CAs
        ca1_cert, ca1_key = generate_ca("CA 1")
        ca2_cert, ca2_key = generate_ca("CA 2")
        
        # Generate client cert with CA 2
        client_id = "client-wrong-ca"
        client_cert, client_key = generate_client_certificate(
            ca2_cert, ca2_key, client_id, "Wrong CA Client"
        )
        
        # Create config with CA 1
        config = ServerConfig(
            version="1.0.0",
            server=ServerSettings(
                host="127.0.0.1",
                port=8443,
                worker_threads=2,
                max_connections=5,
                idle_timeout=30,
                chunk_size=8192
            ),
            security=SecurityConfig(
                ca_certificate=ca1_cert,  # Different CA
                ca_private_key=ca1_key,
                crl=[]
            ),
            libraries={},
            clients={
                client_id: ClientRecord(
                    name="Wrong CA Client",
                    certificate=client_cert,
                    revoked=False
                )
            },
            logging=LoggingConfig(level="INFO", file=None)
        )
        
        # Create authenticator
        auth = ServerAuthenticator(config)
        
        # Certificate fingerprint won't match
        # This should fail validation
        with pytest.raises((AuthenticationError, Exception)):
            auth.validate_client_certificate(client_cert)


class TestAuthorizationSecurity:
    """Tests for library access control."""
    
    def test_authorized_client_granted(self):
        """Test authorized client can access library."""
        with tempfile.TemporaryDirectory() as tmpdir:
            library_id = "lib-123"
            client_id = "client-456"
            
            # Generate certificates
            ca_cert, ca_key = generate_ca("Test CA")
            client_cert, client_key = generate_client_certificate(
                ca_cert, ca_key, client_id, "Test Client"
            )
            
            # Create config
            config = ServerConfig(
                version="1.0.0",
                server=ServerSettings(
                    host="127.0.0.1",
                    port=8443,
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
                libraries={
                    library_id: LibraryConfig(
                        name="Test Library",
                        path=tmpdir,
                        authorized_clients=[client_id],  # Client authorized
                        rate_limit_bps=0,
                        idle_timeout=30
                    )
                },
                clients={
                    client_id: ClientRecord(
                        name="Test Client",
                        certificate=client_cert,
                        revoked=False
                    )
                },
                logging=LoggingConfig(level="INFO", file=None)
            )
            
            # Create library manager
            lib_mgr = LibraryManager(config)
            
            # Should succeed
            assert lib_mgr.check_client_access(library_id, client_id) is True
    
    def test_unauthorized_client_denied(self):
        """Test unauthorized client cannot access library."""
        with tempfile.TemporaryDirectory() as tmpdir:
            library_id = "lib-123"
            client_id = "client-456"
            other_client = "other-789"
            
            # Generate certificates
            ca_cert, ca_key = generate_ca("Test CA")
            
            # Create config
            config = ServerConfig(
                version="1.0.0",
                server=ServerSettings(
                    host="127.0.0.1",
                    port=8443,
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
                libraries={
                    library_id: LibraryConfig(
                        name="Test Library",
                        path=tmpdir,
                        authorized_clients=[client_id],  # Only one client
                        rate_limit_bps=0,
                        idle_timeout=30
                    )
                },
                clients={},
                logging=LoggingConfig(level="INFO", file=None)
            )
            
            # Create library manager
            lib_mgr = LibraryManager(config)
            
            # Should fail
            from fileharbor.common.exceptions import LibraryAccessDeniedError
            with pytest.raises(LibraryAccessDeniedError):
                lib_mgr.check_client_access(library_id, other_client)


class TestEncryptionSecurity:
    """Tests for configuration encryption."""
    
    def test_encryption_roundtrip(self):
        """Test config can be encrypted and decrypted."""
        from fileharbor.config_tool.encryption import (
            encrypt_config_file,
            decrypt_config_file
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test config
            config_path = Path(tmpdir) / "test_config.json"
            config_path.write_text('{"test": "data"}')
            
            # Encrypt
            password = "test_password_123"
            encrypt_config_file(str(config_path), password)
            
            encrypted_path = str(config_path) + '.encrypted'
            assert Path(encrypted_path).exists()
            
            # Decrypt
            decrypted = decrypt_config_file(encrypted_path, password)
            assert '{"test": "data"}' in decrypted
    
    def test_wrong_password_fails(self):
        """Test decryption with wrong password fails."""
        from fileharbor.config_tool.encryption import (
            encrypt_config_file,
            decrypt_config_file
        )
        from fileharbor.common.exceptions import DecryptionError
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and encrypt config
            config_path = Path(tmpdir) / "test_config.json"
            config_path.write_text('{"test": "data"}')
            
            password = "correct_password"
            encrypt_config_file(str(config_path), password)
            
            encrypted_path = str(config_path) + '.encrypted'
            
            # Try with wrong password
            with pytest.raises(DecryptionError):
                decrypt_config_file(encrypted_path, "wrong_password")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
