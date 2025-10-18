"""
FileHarbor Configuration Schemas

JSON schema definitions and validation for server and client configurations.
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from fileharbor.__version__ import CURRENT_CONFIG_VERSION, MIN_CONFIG_VERSION
from fileharbor.common.constants import (
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    DEFAULT_WORKER_THREADS,
    DEFAULT_IDLE_TIMEOUT,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_LOG_LEVEL,
    DEFAULT_RATE_LIMIT,
)
from fileharbor.common.exceptions import (
    InvalidConfigError,
    ConfigVersionError,
)


# ============================================================================
# Server Configuration
# ============================================================================

@dataclass
class ServerNetworkConfig:
    """Server network configuration."""
    host: str = DEFAULT_SERVER_HOST
    port: int = DEFAULT_SERVER_PORT
    max_connections: int = 100
    worker_threads: int = DEFAULT_WORKER_THREADS
    idle_timeout: int = DEFAULT_IDLE_TIMEOUT
    chunk_size: int = DEFAULT_CHUNK_SIZE


@dataclass
class SecurityConfig:
    """Security configuration (certificates and CRL)."""
    ca_certificate: str = ""  # PEM format
    ca_private_key: str = ""  # PEM format
    crl: List[int] = field(default_factory=list)  # List of revoked cert serial numbers


@dataclass
class LibraryConfig:
    """Library configuration."""
    name: str
    path: str
    authorized_clients: List[str] = field(default_factory=list)  # List of client UUIDs
    rate_limit_bps: int = DEFAULT_RATE_LIMIT
    idle_timeout: int = DEFAULT_IDLE_TIMEOUT


@dataclass
class ClientRecord:
    """Client certificate record."""
    name: str
    certificate: str  # PEM format
    created: str  # ISO 8601 timestamp
    revoked: bool = False
    private_key: str = ""  # PEM format - stored for client export
    rate_limit_bps: int = DEFAULT_RATE_LIMIT  # Per-client rate limit (0 = unlimited)


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = DEFAULT_LOG_LEVEL
    file: Optional[str] = None
    max_size: int = 10485760  # 10 MB
    backup_count: int = 5


@dataclass
class ServerConfig:
    """Complete server configuration."""
    version: str = CURRENT_CONFIG_VERSION
    server: ServerNetworkConfig = field(default_factory=ServerNetworkConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    libraries: Dict[str, LibraryConfig] = field(default_factory=dict)
    clients: Dict[str, ClientRecord] = field(default_factory=dict)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'version': self.version,
            'server': asdict(self.server),
            'security': asdict(self.security),
            'libraries': {
                lib_id: asdict(lib_config)
                for lib_id, lib_config in self.libraries.items()
            },
            'clients': {
                client_id: asdict(client_record)
                for client_id, client_record in self.clients.items()
            },
            'logging': asdict(self.logging),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServerConfig':
        """Load from dictionary."""
        # Validate version
        version = data.get('version', '0.0.0')
        if not cls._is_version_compatible(version):
            raise ConfigVersionError(version, MIN_CONFIG_VERSION)
        
        # Parse nested structures
        server = ServerNetworkConfig(**data.get('server', {}))
        security = SecurityConfig(**data.get('security', {}))
        logging_config = LoggingConfig(**data.get('logging', {}))
        
        # Parse libraries
        libraries = {}
        for lib_id, lib_data in data.get('libraries', {}).items():
            libraries[lib_id] = LibraryConfig(**lib_data)
        
        # Parse clients
        clients = {}
        for client_id, client_data in data.get('clients', {}).items():
            clients[client_id] = ClientRecord(**client_data)
        
        return cls(
            version=version,
            server=server,
            security=security,
            libraries=libraries,
            clients=clients,
            logging=logging_config,
        )
    
    @staticmethod
    def _is_version_compatible(version: str) -> bool:
        """Check if version is compatible."""
        try:
            # Parse version numbers
            v_parts = [int(x) for x in version.split('.')]
            min_parts = [int(x) for x in MIN_CONFIG_VERSION.split('.')]
            
            # Major version must match
            if v_parts[0] != min_parts[0]:
                return False
            
            # Minor version must be >= minimum
            if v_parts[1] < min_parts[1]:
                return False
            
            return True
        except (ValueError, IndexError):
            return False
    
    def validate(self) -> List[str]:
        """
        Validate configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate server config
        if self.server.port < 1 or self.server.port > 65535:
            errors.append(f"Invalid port: {self.server.port}")
        
        if self.server.worker_threads < 1:
            errors.append(f"Worker threads must be >= 1: {self.server.worker_threads}")
        
        if self.server.chunk_size < 1024:
            errors.append(f"Chunk size must be >= 1024 bytes: {self.server.chunk_size}")
        
        # Validate security config
        if not self.security.ca_certificate:
            errors.append("CA certificate is required")
        
        if not self.security.ca_private_key:
            errors.append("CA private key is required")
        
        # Validate libraries
        for lib_id, lib in self.libraries.items():
            if not lib.name:
                errors.append(f"Library {lib_id} missing name")
            
            if not lib.path:
                errors.append(f"Library {lib_id} missing path")
            
            # Check that authorized clients exist
            for client_id in lib.authorized_clients:
                if client_id not in self.clients:
                    errors.append(
                        f"Library {lib_id} references non-existent client {client_id}"
                    )
        
        # Validate clients
        for client_id, client in self.clients.items():
            if not client.name:
                errors.append(f"Client {client_id} missing name")
            
            if not client.certificate:
                errors.append(f"Client {client_id} missing certificate")
        
        # Validate logging
        if self.logging.level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            errors.append(f"Invalid log level: {self.logging.level}")
        
        return errors


# ============================================================================
# Client Configuration
# ============================================================================

@dataclass
class ClientServerConfig:
    """Server connection configuration for client."""
    host: str
    port: int
    ca_certificate: str  # PEM format


@dataclass
class ClientAuthConfig:
    """Client authentication configuration."""
    certificate: str  # PEM format
    private_key: str  # PEM format
    library_id: str


@dataclass
class ClientTransferConfig:
    """Client transfer configuration."""
    chunk_size: int = DEFAULT_CHUNK_SIZE
    compression: bool = False
    verify_checksums: bool = True


@dataclass
class ClientConfig:
    """Complete client configuration."""
    version: str = CURRENT_CONFIG_VERSION
    server: Optional[ClientServerConfig] = None
    client: Optional[ClientAuthConfig] = None
    transfer: ClientTransferConfig = field(default_factory=ClientTransferConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            'version': self.version,
            'transfer': asdict(self.transfer),
        }
        
        if self.server:
            result['server'] = asdict(self.server)
        
        if self.client:
            result['client'] = asdict(self.client)
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClientConfig':
        """Load from dictionary."""
        # Validate version
        version = data.get('version', '0.0.0')
        if not cls._is_version_compatible(version):
            raise ConfigVersionError(version, MIN_CONFIG_VERSION)
        
        # Parse nested structures
        server = None
        if 'server' in data:
            server = ClientServerConfig(**data['server'])
        
        client = None
        if 'client' in data:
            client = ClientAuthConfig(**data['client'])
        
        transfer = ClientTransferConfig(**data.get('transfer', {}))
        
        return cls(
            version=version,
            server=server,
            client=client,
            transfer=transfer,
        )
    
    @staticmethod
    def _is_version_compatible(version: str) -> bool:
        """Check if version is compatible."""
        try:
            v_parts = [int(x) for x in version.split('.')]
            min_parts = [int(x) for x in MIN_CONFIG_VERSION.split('.')]
            
            if v_parts[0] != min_parts[0]:
                return False
            
            if v_parts[1] < min_parts[1]:
                return False
            
            return True
        except (ValueError, IndexError):
            return False
    
    def validate(self) -> List[str]:
        """
        Validate configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate server config
        if not self.server:
            errors.append("Server configuration is required")
        else:
            if not self.server.host:
                errors.append("Server host is required")
            
            if self.server.port < 1 or self.server.port > 65535:
                errors.append(f"Invalid port: {self.server.port}")
            
            if not self.server.ca_certificate:
                errors.append("Server CA certificate is required")
        
        # Validate client config
        if not self.client:
            errors.append("Client configuration is required")
        else:
            if not self.client.certificate:
                errors.append("Client certificate is required")
            
            if not self.client.private_key:
                errors.append("Client private key is required")
            
            if not self.client.library_id:
                errors.append("Library ID is required")
        
        # Validate transfer config
        if self.transfer.chunk_size < 1024:
            errors.append(f"Chunk size must be >= 1024 bytes: {self.transfer.chunk_size}")
        
        return errors


# ============================================================================
# Configuration File I/O
# ============================================================================

def load_config_from_file(filepath: str, config_class) -> Any:
    """
    Load configuration from JSON file.
    
    Args:
        filepath: Path to config file
        config_class: ServerConfig or ClientConfig class
        
    Returns:
        Configuration object
        
    Raises:
        InvalidConfigError: If config is invalid
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config = config_class.from_dict(data)
        
        # Validate
        errors = config.validate()
        if errors:
            raise InvalidConfigError(f"Configuration validation failed: {', '.join(errors)}")
        
        return config
        
    except json.JSONDecodeError as e:
        raise InvalidConfigError(f"Invalid JSON format: {e}")
    except FileNotFoundError:
        raise InvalidConfigError(f"Configuration file not found: {filepath}")
    except Exception as e:
        if isinstance(e, InvalidConfigError):
            raise
        raise InvalidConfigError(f"Failed to load configuration: {e}")


def save_config_to_file(config: Any, filepath: str) -> None:
    """
    Save configuration to JSON file.
    
    Args:
        config: ServerConfig or ClientConfig object
        filepath: Path to save config file
        
    Raises:
        InvalidConfigError: If save fails
    """
    try:
        # Validate before saving
        errors = config.validate()
        if errors:
            raise InvalidConfigError(f"Configuration validation failed: {', '.join(errors)}")
        
        data = config.to_dict()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')  # Add trailing newline
        
    except Exception as e:
        if isinstance(e, InvalidConfigError):
            raise
        raise InvalidConfigError(f"Failed to save configuration: {e}")


def create_default_server_config() -> ServerConfig:
    """Create a default server configuration."""
    return ServerConfig()


def create_default_client_config() -> ClientConfig:
    """Create a default client configuration."""
    return ClientConfig()
