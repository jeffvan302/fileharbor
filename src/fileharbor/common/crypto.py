"""
FileHarbor Cryptographic Utilities

Certificate generation, encryption, and TLS configuration.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from fileharbor.common.constants import (
    CERT_KEY_SIZE,
    CERT_VALIDITY_DAYS,
    KEY_DERIVATION_ITERATIONS,
    SALT_SIZE,
    NONCE_SIZE,
)
from fileharbor.common.exceptions import (
    CryptoError,
    CertificateGenerationError,
    CertificateValidationError,
    KeyGenerationError,
    EncryptionError,
    DecryptionError,
)


# ============================================================================
# Certificate Authority Management
# ============================================================================

def generate_ca_certificate(
    common_name: str = "FileHarbor CA",
    organization: str = "FileHarbor",
    validity_days: int = CERT_VALIDITY_DAYS
) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
    """
    Generate a self-signed Certificate Authority certificate.
    
    Args:
        common_name: Common name for the CA
        organization: Organization name
        validity_days: Certificate validity period in days
        
    Returns:
        Tuple of (certificate, private_key)
        
    Raises:
        CertificateGenerationError: If generation fails
    """
    try:
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=CERT_KEY_SIZE,
            backend=default_backend()
        )
        
        # Build certificate subject
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        # Set validity period
        not_valid_before = datetime.now(timezone.utc)
        not_valid_after = not_valid_before + timedelta(days=validity_days)
        
        # Build certificate
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(not_valid_before)
            .not_valid_after(not_valid_after)
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=0),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_cert_sign=True,
                    crl_sign=True,
                    key_encipherment=False,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
                critical=False,
            )
            .sign(private_key, hashes.SHA256(), backend=default_backend())
        )
        
        return cert, private_key
        
    except Exception as e:
        raise CertificateGenerationError(f"Failed to generate CA certificate: {e}")


def generate_client_certificate(
    ca_cert: x509.Certificate,
    ca_private_key: rsa.RSAPrivateKey,
    client_id: str,
    client_name: str = "FileHarbor Client",
    validity_days: int = CERT_VALIDITY_DAYS
) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
    """
    Generate a client certificate signed by the CA.
    
    Args:
        ca_cert: CA certificate
        ca_private_key: CA private key
        client_id: Unique client identifier (UUID)
        client_name: Human-readable client name
        validity_days: Certificate validity period in days
        
    Returns:
        Tuple of (certificate, private_key)
        
    Raises:
        CertificateGenerationError: If generation fails
    """
    try:
        # Generate private key for client
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=CERT_KEY_SIZE,
            backend=default_backend()
        )
        
        # Build certificate subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FileHarbor"),
            x509.NameAttribute(NameOID.COMMON_NAME, client_name),
            x509.NameAttribute(NameOID.USER_ID, client_id),
        ])
        
        # Set validity period
        not_valid_before = datetime.now(timezone.utc)
        not_valid_after = not_valid_before + timedelta(days=validity_days)
        
        # Build certificate
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_cert.subject)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(not_valid_before)
            .not_valid_after(not_valid_after)
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    key_cert_sign=False,
                    crl_sign=False,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
                critical=True,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(
                    ca_private_key.public_key()
                ),
                critical=False,
            )
            .sign(ca_private_key, hashes.SHA256(), backend=default_backend())
        )
        
        return cert, private_key
        
    except Exception as e:
        raise CertificateGenerationError(f"Failed to generate client certificate: {e}")


# ============================================================================
# Certificate Serialization
# ============================================================================

def certificate_to_pem(cert: x509.Certificate) -> str:
    """
    Convert certificate to PEM string.
    
    Args:
        cert: Certificate object
        
    Returns:
        PEM-encoded certificate string
    """
    return cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')


def private_key_to_pem(key: rsa.RSAPrivateKey, password: Optional[str] = None) -> str:
    """
    Convert private key to PEM string.
    
    Args:
        key: Private key object
        password: Optional password to encrypt the key
        
    Returns:
        PEM-encoded private key string
    """
    encryption = serialization.NoEncryption()
    if password:
        encryption = serialization.BestAvailableEncryption(password.encode('utf-8'))
    
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption
    ).decode('utf-8')


def pem_to_certificate(pem_data: str) -> x509.Certificate:
    """
    Load certificate from PEM string.
    
    Args:
        pem_data: PEM-encoded certificate string
        
    Returns:
        Certificate object
        
    Raises:
        CertificateValidationError: If PEM data is invalid
    """
    try:
        return x509.load_pem_x509_certificate(
            pem_data.encode('utf-8'),
            backend=default_backend()
        )
    except Exception as e:
        raise CertificateValidationError(f"Failed to load certificate: {e}")


def pem_to_private_key(
    pem_data: str,
    password: Optional[str] = None
) -> rsa.RSAPrivateKey:
    """
    Load private key from PEM string.
    
    Args:
        pem_data: PEM-encoded private key string
        password: Optional password if key is encrypted
        
    Returns:
        Private key object
        
    Raises:
        KeyGenerationError: If PEM data is invalid
    """
    try:
        password_bytes = password.encode('utf-8') if password else None
        return serialization.load_pem_private_key(
            pem_data.encode('utf-8'),
            password=password_bytes,
            backend=default_backend()
        )
    except Exception as e:
        raise KeyGenerationError(f"Failed to load private key: {e}")


# ============================================================================
# Certificate Validation
# ============================================================================

def validate_certificate(
    cert: x509.Certificate,
    ca_cert: x509.Certificate
) -> bool:
    """
    Validate that a certificate is signed by the CA.
    
    Args:
        cert: Certificate to validate
        ca_cert: CA certificate
        
    Returns:
        True if valid
        
    Raises:
        CertificateValidationError: If validation fails
    """
    try:
        # Verify signature
        ca_public_key = ca_cert.public_key()
        ca_public_key.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            cert.signature_algorithm_parameters,
            cert.signature_hash_algorithm
        )
        return True
    except Exception as e:
        raise CertificateValidationError(f"Certificate validation failed: {e}")


def get_certificate_fingerprint(cert: x509.Certificate) -> str:
    """
    Get SHA-256 fingerprint of certificate.
    
    Args:
        cert: Certificate object
        
    Returns:
        Hex-encoded fingerprint string
    """
    fingerprint = cert.fingerprint(hashes.SHA256())
    return fingerprint.hex()


def extract_client_id_from_certificate(cert: x509.Certificate) -> Optional[str]:
    """
    Extract client ID from certificate subject.
    
    Args:
        cert: Certificate object
        
    Returns:
        Client ID (UUID) or None if not found
    """
    try:
        for attribute in cert.subject:
            if attribute.oid == NameOID.USER_ID:
                return attribute.value
        return None
    except Exception:
        return None


# ============================================================================
# Configuration File Encryption
# ============================================================================

def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """
    Derive encryption key from password using PBKDF2.
    
    Args:
        password: User password
        salt: Random salt
        
    Returns:
        32-byte encryption key
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KEY_DERIVATION_ITERATIONS,
        backend=default_backend()
    )
    return kdf.derive(password.encode('utf-8'))


def encrypt_data(data: bytes, password: str) -> bytes:
    """
    Encrypt data using AES-256-GCM.
    
    Args:
        data: Data to encrypt
        password: Encryption password
        
    Returns:
        Encrypted data with salt and nonce prepended
        
    Raises:
        EncryptionError: If encryption fails
    """
    try:
        # Generate random salt and nonce
        salt = secrets.token_bytes(SALT_SIZE)
        nonce = secrets.token_bytes(NONCE_SIZE)
        
        # Derive key from password
        key = derive_key_from_password(password, salt)
        
        # Encrypt data
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        
        # Format: salt (32) + nonce (12) + ciphertext + tag (16)
        return salt + nonce + ciphertext
        
    except Exception as e:
        raise EncryptionError(f"Encryption failed: {e}")


def decrypt_data(encrypted_data: bytes, password: str) -> bytes:
    """
    Decrypt data using AES-256-GCM.
    
    Args:
        encrypted_data: Encrypted data with salt and nonce
        password: Decryption password
        
    Returns:
        Decrypted data
        
    Raises:
        DecryptionError: If decryption fails
    """
    try:
        # Extract salt and nonce
        salt = encrypted_data[:SALT_SIZE]
        nonce = encrypted_data[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
        ciphertext = encrypted_data[SALT_SIZE + NONCE_SIZE:]
        
        # Derive key from password
        key = derive_key_from_password(password, salt)
        
        # Decrypt data
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        return plaintext
        
    except Exception as e:
        raise DecryptionError(f"Decryption failed: {e}")


# ============================================================================
# Certificate Revocation List (CRL) Management
# ============================================================================

def create_crl(
    ca_cert: x509.Certificate,
    ca_private_key: rsa.RSAPrivateKey,
    revoked_serials: list[int] = None
) -> x509.CertificateRevocationList:
    """
    Create a Certificate Revocation List.
    
    Args:
        ca_cert: CA certificate
        ca_private_key: CA private key
        revoked_serials: List of revoked certificate serial numbers
        
    Returns:
        CRL object
    """
    revoked_serials = revoked_serials or []
    
    builder = x509.CertificateRevocationListBuilder()
    builder = builder.issuer_name(ca_cert.subject)
    builder = builder.last_update(datetime.now(timezone.utc))
    builder = builder.next_update(datetime.now(timezone.utc) + timedelta(days=30))
    
    # Add revoked certificates
    for serial in revoked_serials:
        revoked_cert = (
            x509.RevokedCertificateBuilder()
            .serial_number(serial)
            .revocation_date(datetime.now(timezone.utc))
            .build(default_backend())
        )
        builder = builder.add_revoked_certificate(revoked_cert)
    
    crl = builder.sign(
        private_key=ca_private_key,
        algorithm=hashes.SHA256(),
        backend=default_backend()
    )
    
    return crl


def is_certificate_revoked(
    cert: x509.Certificate,
    crl: x509.CertificateRevocationList
) -> bool:
    """
    Check if a certificate is revoked.
    
    Args:
        cert: Certificate to check
        crl: Certificate Revocation List
        
    Returns:
        True if certificate is revoked
    """
    for revoked_cert in crl:
        if revoked_cert.serial_number == cert.serial_number:
            return True
    return False


# ============================================================================
# Utility Functions
# ============================================================================

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Token length in bytes
        
    Returns:
        Hex-encoded token string
    """
    return secrets.token_hex(length)
