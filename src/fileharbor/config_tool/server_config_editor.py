"""
FileHarbor Server Configuration Editor

CRUD operations for server configuration management.
"""

import uuid
from typing import Optional, List

from fileharbor.common.config_schema import (
    ServerConfig,
    LibraryConfig,
    ClientRecord,
)
from fileharbor.common.validators import validate_library_path
from fileharbor.common.exceptions import (
    ConfigurationError,
    LibraryNotFoundError,
    InvalidPathError,
)
from fileharbor.config_tool.certificate_manager import CertificateManager


class ServerConfigEditor:
    """Manages server configuration editing operations."""
    
    def __init__(self, config: ServerConfig):
        """
        Initialize configuration editor.
        
        Args:
            config: Server configuration object
        """
        self.config = config
        self.cert_manager = CertificateManager()
    
    # ========================================================================
    # Library Management
    # ========================================================================
    
    def add_library(
        self,
        name: str,
        path: str,
        rate_limit_bps: int = 0,
        idle_timeout: int = 300
    ) -> str:
        """
        Add a new library to the configuration.
        
        Args:
            name: Human-readable library name
            path: Filesystem path for the library
            rate_limit_bps: Rate limit in bytes per second (0 = unlimited)
            idle_timeout: Idle timeout in seconds
            
        Returns:
            Library UUID
            
        Raises:
            ConfigurationError: If library cannot be added
            InvalidPathError: If library path is invalid
        """
        # Validate library path
        try:
            validate_library_path(path)
        except Exception as e:
            raise InvalidPathError(f"Invalid library path: {e}")
        
        # Check for duplicate names
        for lib_id, lib in self.config.libraries.items():
            if lib.name == name:
                raise ConfigurationError(f"Library with name '{name}' already exists")
        
        # Generate library UUID
        library_id = str(uuid.uuid4())
        
        # Create library configuration
        library = LibraryConfig(
            name=name,
            path=path,
            authorized_clients=[],
            rate_limit_bps=rate_limit_bps,
            idle_timeout=idle_timeout
        )
        
        self.config.libraries[library_id] = library
        
        return library_id
    
    def remove_library(self, library_id: str) -> None:
        """
        Remove a library from the configuration.
        
        Args:
            library_id: Library UUID to remove
            
        Raises:
            LibraryNotFoundError: If library not found
        """
        if library_id not in self.config.libraries:
            raise LibraryNotFoundError(f"Library not found: {library_id}")
        
        del self.config.libraries[library_id]
    
    def update_library(
        self,
        library_id: str,
        name: Optional[str] = None,
        path: Optional[str] = None,
        rate_limit_bps: Optional[int] = None,
        idle_timeout: Optional[int] = None
    ) -> None:
        """
        Update library configuration.
        
        Args:
            library_id: Library UUID to update
            name: New name (optional)
            path: New path (optional)
            rate_limit_bps: New rate limit (optional)
            idle_timeout: New idle timeout (optional)
            
        Raises:
            LibraryNotFoundError: If library not found
            InvalidPathError: If new path is invalid
        """
        if library_id not in self.config.libraries:
            raise LibraryNotFoundError(f"Library not found: {library_id}")
        
        library = self.config.libraries[library_id]
        
        if name is not None:
            # Check for duplicate names
            for lib_id, lib in self.config.libraries.items():
                if lib_id != library_id and lib.name == name:
                    raise ConfigurationError(f"Library with name '{name}' already exists")
            library.name = name
        
        if path is not None:
            try:
                validate_library_path(path)
            except Exception as e:
                raise InvalidPathError(f"Invalid library path: {e}")
            library.path = path
        
        if rate_limit_bps is not None:
            library.rate_limit_bps = rate_limit_bps
        
        if idle_timeout is not None:
            library.idle_timeout = idle_timeout
    
    def list_libraries(self) -> List[tuple]:
        """
        List all libraries.
        
        Returns:
            List of (library_id, name, path, client_count) tuples
        """
        libraries = []
        for lib_id, lib in self.config.libraries.items():
            client_count = len(lib.authorized_clients)
            libraries.append((lib_id, lib.name, lib.path, client_count))
        
        return sorted(libraries, key=lambda x: x[1])  # Sort by name
    
    # ========================================================================
    # Client Management
    # ========================================================================
    
    def add_client(
        self,
        name: str,
        certificate: Optional[str] = None
    ) -> str:
        """
        Add a new client to the configuration.
        
        If certificate is not provided, generates a new certificate.
        
        Args:
            name: Human-readable client name
            certificate: Client certificate PEM (optional, generates if not provided)
            
        Returns:
            Client UUID
            
        Raises:
            ConfigurationError: If client cannot be added
        """
        # Check for duplicate names
        for client_id, client in self.config.clients.items():
            if client.name == name:
                raise ConfigurationError(f"Client with name '{name}' already exists")
        
        # Generate client certificate if not provided
        if certificate is None:
            if not self.config.security.ca_certificate:
                raise ConfigurationError(
                    "Cannot generate client certificate: CA not initialized"
                )
            
            client_id, cert_pem, key_pem, client_record = self.cert_manager.generate_client_cert(
                ca_cert_pem=self.config.security.ca_certificate,
                ca_key_pem=self.config.security.ca_private_key,
                client_name=name
            )
            
            self.config.clients[client_id] = client_record
            
            # Return client_id and private key (private key must be stored separately)
            return client_id
        else:
            # Use provided certificate
            client_id = str(uuid.uuid4())
            
            from datetime import datetime
            client_record = ClientRecord(
                name=name,
                certificate=certificate,
                created=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                revoked=False
            )
            
            self.config.clients[client_id] = client_record
            
            return client_id
    
    def remove_client(self, client_id: str) -> None:
        """
        Remove a client from the configuration.
        
        Also removes client from all library access lists.
        
        Args:
            client_id: Client UUID to remove
            
        Raises:
            ConfigurationError: If client not found
        """
        if client_id not in self.config.clients:
            raise ConfigurationError(f"Client not found: {client_id}")
        
        # Remove from all libraries
        for library in self.config.libraries.values():
            if client_id in library.authorized_clients:
                library.authorized_clients.remove(client_id)
        
        # Remove from clients
        del self.config.clients[client_id]
    
    def revoke_client(self, client_id: str) -> None:
        """
        Revoke a client certificate.
        
        Args:
            client_id: Client UUID to revoke
            
        Raises:
            ConfigurationError: If client not found
        """
        if client_id not in self.config.clients:
            raise ConfigurationError(f"Client not found: {client_id}")
        
        client = self.config.clients[client_id]
        
        # Mark as revoked
        client.revoked = True
        
        # Add to CRL
        self.config.security.crl = self.cert_manager.revoke_client_cert(
            client_cert_pem=client.certificate,
            crl=self.config.security.crl
        )
    
    def unrevoke_client(self, client_id: str) -> None:
        """
        Un-revoke a client certificate (remove from CRL).
        
        Args:
            client_id: Client UUID to un-revoke
            
        Raises:
            ConfigurationError: If client not found
        """
        if client_id not in self.config.clients:
            raise ConfigurationError(f"Client not found: {client_id}")
        
        client = self.config.clients[client_id]
        
        # Mark as not revoked
        client.revoked = False
        
        # Remove from CRL
        from fileharbor.common.crypto import pem_to_certificate
        cert = pem_to_certificate(client.certificate)
        serial_number = cert.serial_number
        
        if serial_number in self.config.security.crl:
            self.config.security.crl.remove(serial_number)
    
    def list_clients(self) -> List[tuple]:
        """
        List all clients.
        
        Returns:
            List of (client_id, name, revoked, library_count) tuples
        """
        clients = []
        for client_id, client in self.config.clients.items():
            # Count libraries this client has access to
            library_count = sum(
                1 for lib in self.config.libraries.values()
                if client_id in lib.authorized_clients
            )
            clients.append((client_id, client.name, client.revoked, library_count))
        
        return sorted(clients, key=lambda x: x[1])  # Sort by name
    
    # ========================================================================
    # Library-Client Access Management
    # ========================================================================
    
    def grant_library_access(self, library_id: str, client_id: str) -> None:
        """
        Grant a client access to a library.
        
        Args:
            library_id: Library UUID
            client_id: Client UUID
            
        Raises:
            LibraryNotFoundError: If library not found
            ConfigurationError: If client not found
        """
        if library_id not in self.config.libraries:
            raise LibraryNotFoundError(f"Library not found: {library_id}")
        
        if client_id not in self.config.clients:
            raise ConfigurationError(f"Client not found: {client_id}")
        
        library = self.config.libraries[library_id]
        
        if client_id not in library.authorized_clients:
            library.authorized_clients.append(client_id)
    
    def revoke_library_access(self, library_id: str, client_id: str) -> None:
        """
        Revoke a client's access to a library.
        
        Args:
            library_id: Library UUID
            client_id: Client UUID
            
        Raises:
            LibraryNotFoundError: If library not found
        """
        if library_id not in self.config.libraries:
            raise LibraryNotFoundError(f"Library not found: {library_id}")
        
        library = self.config.libraries[library_id]
        
        if client_id in library.authorized_clients:
            library.authorized_clients.remove(client_id)
    
    def list_library_clients(self, library_id: str) -> List[tuple]:
        """
        List all clients with access to a library.
        
        Args:
            library_id: Library UUID
            
        Returns:
            List of (client_id, client_name, revoked) tuples
            
        Raises:
            LibraryNotFoundError: If library not found
        """
        if library_id not in self.config.libraries:
            raise LibraryNotFoundError(f"Library not found: {library_id}")
        
        library = self.config.libraries[library_id]
        
        clients = []
        for client_id in library.authorized_clients:
            if client_id in self.config.clients:
                client = self.config.clients[client_id]
                clients.append((client_id, client.name, client.revoked))
        
        return sorted(clients, key=lambda x: x[1])  # Sort by name
    
    # ========================================================================
    # Server Settings
    # ========================================================================
    
    def update_server_settings(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        max_connections: Optional[int] = None,
        worker_threads: Optional[int] = None,
        idle_timeout: Optional[int] = None,
        chunk_size: Optional[int] = None
    ) -> None:
        """
        Update server settings.
        
        Args:
            host: Server host address
            port: Server port
            max_connections: Maximum concurrent connections
            worker_threads: Number of worker threads
            idle_timeout: Idle timeout in seconds
            chunk_size: Transfer chunk size in bytes
        """
        if host is not None:
            self.config.server.host = host
        
        if port is not None:
            from fileharbor.common.validators import validate_port
            validate_port(port)
            self.config.server.port = port
        
        if max_connections is not None:
            if max_connections < 1:
                raise ConfigurationError("Max connections must be >= 1")
            self.config.server.max_connections = max_connections
        
        if worker_threads is not None:
            if worker_threads < 1:
                raise ConfigurationError("Worker threads must be >= 1")
            self.config.server.worker_threads = worker_threads
        
        if idle_timeout is not None:
            if idle_timeout < 1:
                raise ConfigurationError("Idle timeout must be >= 1 second")
            self.config.server.idle_timeout = idle_timeout
        
        if chunk_size is not None:
            from fileharbor.common.validators import validate_chunk_size
            validate_chunk_size(chunk_size)
            self.config.server.chunk_size = chunk_size
    
    def update_logging_settings(
        self,
        level: Optional[str] = None,
        file: Optional[str] = None,
        max_size: Optional[int] = None,
        backup_count: Optional[int] = None
    ) -> None:
        """
        Update logging settings.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            file: Log file path (None for console only)
            max_size: Maximum log file size in bytes
            backup_count: Number of backup log files to keep
        """
        if level is not None:
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if level not in valid_levels:
                raise ConfigurationError(f"Invalid log level. Must be one of: {valid_levels}")
            self.config.logging.level = level
        
        if file is not None:
            self.config.logging.file = file
        
        if max_size is not None:
            if max_size < 1024:
                raise ConfigurationError("Log file max size must be >= 1024 bytes")
            self.config.logging.max_size = max_size
        
        if backup_count is not None:
            if backup_count < 0:
                raise ConfigurationError("Backup count must be >= 0")
            self.config.logging.backup_count = backup_count
    
    # ========================================================================
    # Certificate Authority
    # ========================================================================
    
    def initialize_ca(
        self,
        common_name: str = "FileHarbor CA",
        organization: str = "FileHarbor"
    ) -> None:
        """
        Initialize a new Certificate Authority.
        
        Args:
            common_name: CA common name
            organization: Organization name
            
        Raises:
            ConfigurationError: If CA already exists
        """
        if self.config.security.ca_certificate:
            raise ConfigurationError(
                "Certificate Authority already exists. "
                "Remove existing CA before creating a new one."
            )
        
        ca_cert_pem, ca_key_pem = self.cert_manager.generate_ca(
            common_name=common_name,
            organization=organization
        )
        
        self.config.security.ca_certificate = ca_cert_pem
        self.config.security.ca_private_key = ca_key_pem
        self.config.security.crl = []
