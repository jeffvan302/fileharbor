"""
FileHarbor Certificate Manager

Certificate Authority and client certificate management.
"""

import uuid
from datetime import datetime
from typing import Tuple, Optional

from fileharbor.common.crypto import (
    generate_ca_certificate,
    generate_client_certificate,
    certificate_to_pem,
    private_key_to_pem,
    pem_to_certificate,
    pem_to_private_key,
    get_certificate_fingerprint,
)
from fileharbor.common.config_schema import ClientRecord
from fileharbor.common.exceptions import (
    CertificateGenerationError,
    CryptoError,
)


class CertificateManager:
    """Manages certificate operations for FileHarbor."""
    
    def __init__(self):
        """Initialize certificate manager."""
        pass
    
    def generate_ca(
        self,
        common_name: str = "FileHarbor CA",
        organization: str = "FileHarbor"
    ) -> Tuple[str, str]:
        """
        Generate a new Certificate Authority.
        
        Args:
            common_name: CA common name
            organization: Organization name
            
        Returns:
            Tuple of (ca_certificate_pem, ca_private_key_pem)
            
        Raises:
            CertificateGenerationError: If generation fails
        """
        try:
            ca_cert, ca_key = generate_ca_certificate(
                common_name=common_name,
                organization=organization
            )
            
            ca_cert_pem = certificate_to_pem(ca_cert)
            ca_key_pem = private_key_to_pem(ca_key)
            
            return ca_cert_pem, ca_key_pem
            
        except Exception as e:
            raise CertificateGenerationError(f"Failed to generate CA: {e}")
    
    def generate_client_cert(
        self,
        ca_cert_pem: str,
        ca_key_pem: str,
        client_name: str,
        client_id: Optional[str] = None
    ) -> Tuple[str, str, str, ClientRecord]:
        """
        Generate a client certificate signed by the CA.
        
        Args:
            ca_cert_pem: CA certificate in PEM format
            ca_key_pem: CA private key in PEM format
            client_name: Human-readable client name
            client_id: Client UUID (generated if not provided)
            
        Returns:
            Tuple of (client_id, client_cert_pem, client_key_pem, client_record)
            
        Raises:
            CertificateGenerationError: If generation fails
        """
        try:
            # Load CA certificate and key
            ca_cert = pem_to_certificate(ca_cert_pem)
            ca_key = pem_to_private_key(ca_key_pem)
            
            # Generate client ID if not provided
            if client_id is None:
                client_id = str(uuid.uuid4())
            
            # Generate client certificate
            client_cert, client_key = generate_client_certificate(
                ca_cert=ca_cert,
                ca_private_key=ca_key,
                client_id=client_id,
                client_name=client_name
            )
            
            # Convert to PEM
            client_cert_pem = certificate_to_pem(client_cert)
            client_key_pem = private_key_to_pem(client_key)
            
            # Create client record (includes private key for export)
            client_record = ClientRecord(
                name=client_name,
                certificate=client_cert_pem,
                created=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                revoked=False,
                private_key=client_key_pem  # Store for client config export
            )
            
            return client_id, client_cert_pem, client_key_pem, client_record
            
        except Exception as e:
            raise CertificateGenerationError(f"Failed to generate client certificate: {e}")
    
    def get_ca_info(self, ca_cert_pem: str) -> dict:
        """
        Get information about a CA certificate.
        
        Args:
            ca_cert_pem: CA certificate in PEM format
            
        Returns:
            Dictionary with CA information
        """
        try:
            ca_cert = pem_to_certificate(ca_cert_pem)
            
            return {
                'subject': ca_cert.subject.rfc4514_string(),
                'issuer': ca_cert.issuer.rfc4514_string(),
                'serial_number': ca_cert.serial_number,
                'fingerprint': get_certificate_fingerprint(ca_cert),
                'not_valid_before': ca_cert.not_valid_before_utc.isoformat(),
                'not_valid_after': ca_cert.not_valid_after_utc.isoformat(),
            }
        except Exception as e:
            raise CryptoError(f"Failed to get CA info: {e}")
    
    def get_client_cert_info(self, client_cert_pem: str) -> dict:
        """
        Get information about a client certificate.
        
        Args:
            client_cert_pem: Client certificate in PEM format
            
        Returns:
            Dictionary with certificate information
        """
        try:
            client_cert = pem_to_certificate(client_cert_pem)
            
            # Extract client ID from certificate
            client_id = None
            for attr in client_cert.subject:
                if attr.oid.dotted_string == '0.9.2342.19200300.100.1.1':  # UID OID
                    client_id = attr.value
                    break
            
            return {
                'subject': client_cert.subject.rfc4514_string(),
                'issuer': client_cert.issuer.rfc4514_string(),
                'serial_number': client_cert.serial_number,
                'fingerprint': get_certificate_fingerprint(client_cert),
                'client_id': client_id,
                'not_valid_before': client_cert.not_valid_before_utc.isoformat(),
                'not_valid_after': client_cert.not_valid_after_utc.isoformat(),
            }
        except Exception as e:
            raise CryptoError(f"Failed to get client certificate info: {e}")
    
    def revoke_client_cert(
        self,
        client_cert_pem: str,
        crl: list
    ) -> list:
        """
        Revoke a client certificate by adding to CRL.
        
        Args:
            client_cert_pem: Client certificate to revoke
            crl: Current certificate revocation list (list of serial numbers)
            
        Returns:
            Updated CRL
        """
        try:
            client_cert = pem_to_certificate(client_cert_pem)
            serial_number = client_cert.serial_number
            
            # Add to CRL if not already present
            if serial_number not in crl:
                crl.append(serial_number)
            
            return crl
            
        except Exception as e:
            raise CryptoError(f"Failed to revoke certificate: {e}")
    
    def is_cert_revoked(
        self,
        client_cert_pem: str,
        crl: list
    ) -> bool:
        """
        Check if a certificate is revoked.
        
        Args:
            client_cert_pem: Client certificate to check
            crl: Certificate revocation list (list of serial numbers)
            
        Returns:
            True if certificate is revoked
        """
        try:
            client_cert = pem_to_certificate(client_cert_pem)
            serial_number = client_cert.serial_number
            
            return serial_number in crl
            
        except Exception as e:
            raise CryptoError(f"Failed to check revocation status: {e}")
    
    def validate_ca_key_pair(
        self,
        ca_cert_pem: str,
        ca_key_pem: str
    ) -> bool:
        """
        Validate that a CA certificate and private key match.
        
        Args:
            ca_cert_pem: CA certificate in PEM format
            ca_key_pem: CA private key in PEM format
            
        Returns:
            True if certificate and key match
        """
        try:
            ca_cert = pem_to_certificate(ca_cert_pem)
            ca_key = pem_to_private_key(ca_key_pem)
            
            # Check if public keys match
            cert_public_key = ca_cert.public_key()
            key_public_key = ca_key.public_key()
            
            # Compare public key parameters
            from cryptography.hazmat.primitives import serialization
            
            cert_public_bytes = cert_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            key_public_bytes = key_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return cert_public_bytes == key_public_bytes
            
        except Exception as e:
            raise CryptoError(f"Failed to validate CA key pair: {e}")
