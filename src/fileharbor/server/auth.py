"""
FileHarbor Server Authentication

Certificate validation and access control.
"""

import ssl
from typing import Optional, Tuple

from cryptography import x509

from fileharbor.common.config_schema import ServerConfig
from fileharbor.common.crypto import (
    pem_to_certificate,
    extract_client_id_from_certificate,
    get_certificate_fingerprint,
)
from fileharbor.common.exceptions import (
    AuthenticationError,
    CertificateError,
    CertificateRevokedError,
    LibraryAccessDeniedError,
)


class ServerAuthenticator:
    """Handles client authentication and authorization."""
    
    def __init__(self, config: ServerConfig):
        """
        Initialize authenticator.
        
        Args:
            config: Server configuration
        """
        self.config = config
        self.ca_cert = pem_to_certificate(config.security.ca_certificate)
    
    def validate_client_certificate(self, cert_pem: str) -> str:
        """
        Validate client certificate and extract client ID.
        
        Args:
            cert_pem: Client certificate in PEM format
            
        Returns:
            Client ID (UUID)
            
        Raises:
            CertificateError: If certificate is invalid
            CertificateRevokedError: If certificate is revoked
            AuthenticationError: If client not found in config
        """
        try:
            client_cert = pem_to_certificate(cert_pem)
        except Exception as e:
            raise CertificateError(f"Invalid certificate format: {e}")
        
        # Extract client ID from certificate
        client_id = extract_client_id_from_certificate(client_cert)
        if not client_id:
            raise CertificateError("Certificate does not contain client ID")
        
        # Check if certificate is in the revocation list
        if self._is_revoked(client_cert):
            raise CertificateRevokedError(client_id)
        
        # Verify client exists in configuration
        if client_id not in self.config.clients:
            raise AuthenticationError(f"Client not found in configuration: {client_id}")
        
        # Verify certificate matches what's in config
        client_record = self.config.clients[client_id]
        if client_record.revoked:
            raise CertificateRevokedError(client_id)
        
        stored_cert = pem_to_certificate(client_record.certificate)
        if get_certificate_fingerprint(client_cert) != get_certificate_fingerprint(stored_cert):
            raise CertificateError("Certificate fingerprint does not match stored certificate")
        
        return client_id
    
    def check_library_access(self, client_id: str, library_id: str) -> bool:
        """
        Check if client has access to a library.
        
        Args:
            client_id: Client UUID
            library_id: Library UUID
            
        Returns:
            True if client has access
            
        Raises:
            LibraryAccessDeniedError: If access is denied
        """
        if library_id not in self.config.libraries:
            raise LibraryAccessDeniedError(f"Library not found: {library_id}")
        
        library = self.config.libraries[library_id]
        
        if client_id not in library.authorized_clients:
            client_name = self.config.clients.get(client_id, {}).name if client_id in self.config.clients else "Unknown"
            raise LibraryAccessDeniedError(
                f"Client '{client_name}' does not have access to library '{library.name}'"
            )
        
        return True
    
    def get_client_name(self, client_id: str) -> str:
        """
        Get human-readable name for client.
        
        Args:
            client_id: Client UUID
            
        Returns:
            Client name or "Unknown"
        """
        if client_id in self.config.clients:
            return self.config.clients[client_id].name
        return "Unknown"
    
    def get_client_rate_limit(self, client_id: str) -> int:
        """
        Get rate limit for client.
        
        Args:
            client_id: Client UUID
            
        Returns:
            Rate limit in bytes per second (0 = unlimited)
        """
        if client_id in self.config.clients:
            return self.config.clients[client_id].rate_limit_bps
        return 0  # Unlimited if client not found
    
    def get_library_config(self, library_id: str):
        """
        Get library configuration.
        
        Args:
            library_id: Library UUID
            
        Returns:
            LibraryConfig object or None
        """
        return self.config.libraries.get(library_id)
    
    def _is_revoked(self, cert: x509.Certificate) -> bool:
        """
        Check if certificate is in the CRL.
        
        Args:
            cert: Certificate to check
            
        Returns:
            True if revoked
        """
        serial_number = cert.serial_number
        return serial_number in self.config.security.crl
    
    def create_ssl_context(self) -> ssl.SSLContext:
        """
        Create SSL context for server with mTLS.
        
        Returns:
            Configured SSL context
        """
        # Create SSL context for TLS 1.3
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        
        # Require client certificates (mutual TLS)
        context.verify_mode = ssl.CERT_REQUIRED
        
        # Load server certificate and key (using CA as server cert)
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as cert_file:
            cert_file.write(self.config.security.ca_certificate)
            cert_path = cert_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as key_file:
            key_file.write(self.config.security.ca_private_key)
            key_path = key_file.name
        
        try:
            context.load_cert_chain(cert_path, key_path)
        finally:
            import os
            os.unlink(cert_path)
            os.unlink(key_path)
        
        # Load CA certificate for client verification
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as ca_file:
            ca_file.write(self.config.security.ca_certificate)
            ca_path = ca_file.name
        
        try:
            context.load_verify_locations(ca_path)
        finally:
            import os
            os.unlink(ca_path)
        
        return context


def extract_client_cert_from_ssl(ssl_socket) -> Optional[str]:
    """
    Extract client certificate from SSL socket.
    
    Args:
        ssl_socket: SSL socket with client connection
        
    Returns:
        Client certificate in PEM format or None
    """
    try:
        cert_binary = ssl_socket.getpeercert(binary_form=True)
        if cert_binary:
            cert = x509.load_der_x509_certificate(cert_binary)
            from cryptography.hazmat.primitives import serialization
            cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')
            return cert_pem
    except Exception:
        return None
    
    return None
