"""
FileHarbor Client Configuration Loader

Loads and validates client configuration from file.
"""

import json
import getpass
from pathlib import Path
from typing import Optional

from fileharbor.common.config_schema import ClientConfig, load_config_from_file
from fileharbor.common.exceptions import ConfigurationError, DecryptionError
from fileharbor.config_tool.encryption import is_config_encrypted, decrypt_config_file


def load_client_config(config_path: str, password: Optional[str] = None) -> ClientConfig:
    """
    Load client configuration from file, handling encryption if needed.
    
    Args:
        config_path: Path to client configuration file
        password: Password for encrypted config (prompted if needed)
        
    Returns:
        ClientConfig object
        
    Raises:
        ConfigurationError: If config is invalid
        DecryptionError: If decryption fails
        FileNotFoundError: If config file doesn't exist
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    # Check if encrypted
    if is_config_encrypted(str(config_path)):
        if password is None:
            password = getpass.getpass("Enter configuration password: ")
        
        # Decrypt and parse
        try:
            config_json = decrypt_config_file(str(config_path), password)
            config_data = json.loads(config_json)
            config = ClientConfig.from_dict(config_data)
        except Exception as e:
            raise DecryptionError(f"Failed to decrypt configuration: {e}")
    else:
        # Load plain config
        try:
            config = load_config_from_file(str(config_path), ClientConfig)
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    # Validate configuration
    errors = config.validate()
    if errors:
        error_msg = "\n  - ".join(["Configuration validation failed:"] + errors)
        raise ConfigurationError(error_msg)
    
    return config


def validate_client_config(config: ClientConfig) -> None:
    """
    Perform additional client-specific validation.
    
    Args:
        config: Client configuration to validate
        
    Raises:
        ConfigurationError: If validation fails
    """
    # Validate server address
    if not config.server.host:
        raise ConfigurationError("Server host is required")
    
    if config.server.port <= 0 or config.server.port > 65535:
        raise ConfigurationError(f"Invalid server port: {config.server.port}")
    
    # Validate certificate
    if not config.security.certificate:
        raise ConfigurationError("Client certificate is required")
    
    if not config.security.private_key:
        raise ConfigurationError("Client private key is required")
    
    if not config.security.ca_certificate:
        raise ConfigurationError("CA certificate is required")
    
    # Validate library ID
    if not config.library_id:
        raise ConfigurationError("Library ID is required")
