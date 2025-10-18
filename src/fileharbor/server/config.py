"""
FileHarbor Server Configuration Loader

Loads and validates server configuration from file.
"""

from pathlib import Path
from typing import Optional

from fileharbor.common.config_schema import ServerConfig, load_config_from_file
from fileharbor.common.exceptions import ConfigurationError, DecryptionError
from fileharbor.config_tool.encryption import load_config_with_password


def load_server_config(config_path: str, password: Optional[str] = None) -> ServerConfig:
    """
    Load server configuration from file, handling encryption if needed.
    
    Args:
        config_path: Path to server configuration file
        password: Password for encrypted config (prompted if needed)
        
    Returns:
        ServerConfig object
        
    Raises:
        ConfigurationError: If config is invalid
        DecryptionError: If decryption fails
        FileNotFoundError: If config file doesn't exist
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    # Load configuration (handles both encrypted and plain)
    try:
        config_data = load_config_with_password(str(config_path), password)
        config = ServerConfig.from_dict(config_data)
    except DecryptionError:
        # Re-raise decryption errors as-is
        raise
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration: {e}")
    
    # Validate configuration
    errors = config.validate()
    if errors:
        error_msg = "\n  - ".join(["Configuration validation failed:"] + errors)
        raise ConfigurationError(error_msg)
    
    return config


def validate_server_config(config: ServerConfig) -> None:
    """
    Perform additional server-specific validation.
    
    Args:
        config: Server configuration to validate
        
    Raises:
        ConfigurationError: If validation fails
    """
    # Validate library paths exist
    for lib_id, library in config.libraries.items():
        lib_path = Path(library.path)
        if not lib_path.exists():
            raise ConfigurationError(
                f"Library path does not exist: {library.name} -> {library.path}"
            )
        if not lib_path.is_dir():
            raise ConfigurationError(
                f"Library path is not a directory: {library.name} -> {library.path}"
            )
    
    # Validate CA exists
    if not config.security.ca_certificate:
        raise ConfigurationError("CA certificate is required but not found in configuration")
    
    if not config.security.ca_private_key:
        raise ConfigurationError("CA private key is required but not found in configuration")
    
    # Validate at least one library exists
    if not config.libraries:
        raise ConfigurationError("At least one library must be configured")
    
    print("✅ Configuration validation successful")
