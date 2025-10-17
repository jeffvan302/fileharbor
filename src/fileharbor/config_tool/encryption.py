"""
FileHarbor Configuration File Encryption

Utilities for encrypting and decrypting configuration files.
"""

import json
import getpass
from pathlib import Path
from typing import Optional

from fileharbor.common.crypto import encrypt_data, decrypt_data
from fileharbor.common.exceptions import (
    EncryptionError,
    DecryptionError,
    ConfigurationError,
)


def encrypt_config_file(
    config_path: str,
    password: Optional[str] = None,
    output_path: Optional[str] = None
) -> str:
    """
    Encrypt a configuration file.
    
    Args:
        config_path: Path to configuration file to encrypt
        password: Encryption password (prompts if not provided)
        output_path: Output path (defaults to input_path + .encrypted)
        
    Returns:
        Path to encrypted file
        
    Raises:
        EncryptionError: If encryption fails
        ConfigurationError: If file not found
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")
    
    # Get password if not provided
    if password is None:
        password = getpass.getpass("Enter encryption password: ")
        password_confirm = getpass.getpass("Confirm password: ")
        
        if password != password_confirm:
            raise EncryptionError("Passwords do not match")
        
        if len(password) < 8:
            raise EncryptionError("Password must be at least 8 characters")
    
    # Read configuration file
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = f.read()
    except Exception as e:
        raise ConfigurationError(f"Failed to read configuration file: {e}")
    
    # Encrypt data
    try:
        encrypted_data = encrypt_data(config_data.encode('utf-8'), password)
    except Exception as e:
        raise EncryptionError(f"Encryption failed: {e}")
    
    # Determine output path
    if output_path is None:
        output_path = str(config_path) + '.encrypted'
    
    # Write encrypted file
    try:
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)
    except Exception as e:
        raise EncryptionError(f"Failed to write encrypted file: {e}")
    
    return output_path


def decrypt_config_file(
    encrypted_path: str,
    password: Optional[str] = None,
    output_path: Optional[str] = None
) -> str:
    """
    Decrypt a configuration file.
    
    Args:
        encrypted_path: Path to encrypted configuration file
        password: Decryption password (prompts if not provided)
        output_path: Output path (defaults to input without .encrypted)
        
    Returns:
        Path to decrypted file
        
    Raises:
        DecryptionError: If decryption fails
        ConfigurationError: If file not found
    """
    encrypted_path = Path(encrypted_path)
    
    if not encrypted_path.exists():
        raise ConfigurationError(f"Encrypted file not found: {encrypted_path}")
    
    # Get password if not provided
    if password is None:
        password = getpass.getpass("Enter decryption password: ")
    
    # Read encrypted file
    try:
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()
    except Exception as e:
        raise ConfigurationError(f"Failed to read encrypted file: {e}")
    
    # Decrypt data
    try:
        decrypted_data = decrypt_data(encrypted_data, password)
    except Exception as e:
        raise DecryptionError(f"Decryption failed - incorrect password or corrupted file: {e}")
    
    # Determine output path
    if output_path is None:
        if str(encrypted_path).endswith('.encrypted'):
            output_path = str(encrypted_path)[:-10]  # Remove .encrypted
        else:
            output_path = str(encrypted_path) + '.decrypted'
    
    # Write decrypted file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(decrypted_data.decode('utf-8'))
    except Exception as e:
        raise DecryptionError(f"Failed to write decrypted file: {e}")
    
    return output_path


def is_config_encrypted(config_path: str) -> bool:
    """
    Check if a configuration file is encrypted.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        True if file appears to be encrypted
    """
    try:
        with open(config_path, 'rb') as f:
            # Read first few bytes
            header = f.read(100)
            
            # Try to parse as JSON
            try:
                f.seek(0)
                json.load(f)
                return False  # Successfully parsed as JSON, not encrypted
            except (json.JSONDecodeError, UnicodeDecodeError):
                return True  # Cannot parse as JSON, likely encrypted
    except Exception:
        return False


def load_config_with_password(
    config_path: str,
    password: Optional[str] = None
) -> dict:
    """
    Load configuration file, decrypting if necessary.
    
    Args:
        config_path: Path to configuration file
        password: Password if file is encrypted (prompts if not provided)
        
    Returns:
        Configuration dictionary
        
    Raises:
        ConfigurationError: If loading fails
        DecryptionError: If decryption fails
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")
    
    # Check if encrypted
    if is_config_encrypted(str(config_path)):
        # Get password if not provided
        if password is None:
            password = getpass.getpass("Configuration file is encrypted. Enter password: ")
        
        # Read and decrypt
        try:
            with open(config_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = decrypt_data(encrypted_data, password)
            config_json = decrypted_data.decode('utf-8')
            
            return json.loads(config_json)
        except Exception as e:
            raise DecryptionError(f"Failed to decrypt configuration: {e}")
    else:
        # Read as plain JSON
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")


def save_config_with_encryption(
    config_dict: dict,
    config_path: str,
    encrypt: bool = False,
    password: Optional[str] = None
) -> None:
    """
    Save configuration file, optionally encrypting it.
    
    Args:
        config_dict: Configuration dictionary
        config_path: Path to save configuration
        encrypt: Whether to encrypt the file
        password: Encryption password (prompts if encrypt=True and not provided)
        
    Raises:
        ConfigurationError: If saving fails
        EncryptionError: If encryption fails
    """
    # Convert to JSON
    try:
        config_json = json.dumps(config_dict, indent=2, ensure_ascii=False) + '\n'
    except Exception as e:
        raise ConfigurationError(f"Failed to serialize configuration: {e}")
    
    if encrypt:
        # Get password if not provided
        if password is None:
            password = getpass.getpass("Enter encryption password: ")
            password_confirm = getpass.getpass("Confirm password: ")
            
            if password != password_confirm:
                raise EncryptionError("Passwords do not match")
            
            if len(password) < 8:
                raise EncryptionError("Password must be at least 8 characters")
        
        # Encrypt and save
        try:
            encrypted_data = encrypt_data(config_json.encode('utf-8'), password)
            
            with open(config_path, 'wb') as f:
                f.write(encrypted_data)
        except Exception as e:
            raise EncryptionError(f"Failed to encrypt and save configuration: {e}")
    else:
        # Save as plain JSON
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_json)
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
