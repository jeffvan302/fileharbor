"""
FileHarbor Client Configuration Exporter

Export client configurations from server configuration.
"""

from pathlib import Path
from typing import Optional

from fileharbor.common.config_schema import (
    ServerConfig,
    ClientConfig,
    ClientServerConfig,
    ClientAuthConfig,
    ClientTransferConfig,
    save_config_to_file,
)
from fileharbor.common.exceptions import (
    ConfigurationError,
    LibraryNotFoundError,
)
from fileharbor.config_tool.encryption import save_config_with_encryption


class ClientConfigExporter:
    """Exports client configurations from server configuration."""
    
    def __init__(self, server_config: ServerConfig):
        """
        Initialize client config exporter.
        
        Args:
            server_config: Server configuration object
        """
        self.server_config = server_config
    
    def export_client_config(
        self,
        library_id: str,
        client_id: str,
        output_path: str,
        server_host: Optional[str] = None,
        encrypt: bool = False,
        password: Optional[str] = None
    ) -> str:
        """
        Export a client configuration for a specific library.
        
        Args:
            library_id: Library UUID to access
            client_id: Client UUID
            output_path: Path to save client configuration
            server_host: Server hostname/IP (defaults to config value)
            encrypt: Whether to encrypt the configuration
            password: Encryption password (prompts if not provided and encrypt=True)
            
        Returns:
            Path to exported configuration file
            
        Raises:
            LibraryNotFoundError: If library not found
            ConfigurationError: If client not authorized or export fails
        """
        # Validate library exists
        if library_id not in self.server_config.libraries:
            raise LibraryNotFoundError(f"Library not found: {library_id}")
        
        library = self.server_config.libraries[library_id]
        
        # Validate client exists
        if client_id not in self.server_config.clients:
            raise ConfigurationError(f"Client not found: {client_id}")
        
        client = self.server_config.clients[client_id]
        
        # Validate client is authorized for library
        if client_id not in library.authorized_clients:
            raise ConfigurationError(
                f"Client '{client.name}' is not authorized for library '{library.name}'"
            )
        
        # Check if client is revoked
        if client.revoked:
            raise ConfigurationError(
                f"Client '{client.name}' certificate has been revoked"
            )
        
        # Determine server host
        if server_host is None:
            server_host = self.server_config.server.host
            # If server is listening on all interfaces (0.0.0.0), we need a specific host
            if server_host == '0.0.0.0':
                raise ConfigurationError(
                    "Server is configured to listen on all interfaces (0.0.0.0). "
                    "Please specify the actual server hostname or IP address."
                )
        
        # Create client configuration
        client_config = ClientConfig(
            server=ClientServerConfig(
                host=server_host,
                port=self.server_config.server.port,
                ca_certificate=self.server_config.security.ca_certificate,
            ),
            client=ClientAuthConfig(
                certificate=client.certificate,
                private_key=self._get_client_private_key(client_id),
                library_id=library_id,
            ),
            transfer=ClientTransferConfig(
                chunk_size=self.server_config.server.chunk_size,
                compression=False,
                verify_checksums=True,
            ),
        )
        
        # Save configuration
        try:
            save_config_with_encryption(
                config_dict=client_config.to_dict(),
                config_path=output_path,
                encrypt=encrypt,
                password=password
            )
        except Exception as e:
            raise ConfigurationError(f"Failed to save client configuration: {e}")
        
        return output_path
    
    def _get_client_private_key(self, client_id: str) -> str:
        """
        Get client private key.
        
        Note: In a real implementation, private keys would be stored separately
        or generated on-demand. For this implementation, we'll generate a warning
        that the private key needs to be provided separately.
        
        Args:
            client_id: Client UUID
            
        Returns:
            Private key PEM or placeholder message
        """
        # In a real implementation, you would either:
        # 1. Store private keys separately (not recommended for security)
        # 2. Generate them on-demand during certificate creation
        # 3. Have the user provide them
        
        # For now, we'll return a placeholder that indicates the key needs to be provided
        return "[PRIVATE_KEY_PLACEHOLDER - Must be provided from certificate generation]"
    
    def list_exportable_clients(self, library_id: str) -> list:
        """
        List all clients that can be exported for a library.
        
        Args:
            library_id: Library UUID
            
        Returns:
            List of (client_id, client_name, revoked) tuples
            
        Raises:
            LibraryNotFoundError: If library not found
        """
        if library_id not in self.server_config.libraries:
            raise LibraryNotFoundError(f"Library not found: {library_id}")
        
        library = self.server_config.libraries[library_id]
        
        exportable = []
        for client_id in library.authorized_clients:
            if client_id in self.server_config.clients:
                client = self.server_config.clients[client_id]
                exportable.append((client_id, client.name, client.revoked))
        
        return exportable
    
    def validate_export_possible(self, library_id: str, client_id: str) -> dict:
        """
        Validate if a client configuration can be exported.
        
        Args:
            library_id: Library UUID
            client_id: Client UUID
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
        }
        
        # Check library exists
        if library_id not in self.server_config.libraries:
            result['valid'] = False
            result['errors'].append(f"Library not found: {library_id}")
            return result
        
        # Check client exists
        if client_id not in self.server_config.clients:
            result['valid'] = False
            result['errors'].append(f"Client not found: {client_id}")
            return result
        
        library = self.server_config.libraries[library_id]
        client = self.server_config.clients[client_id]
        
        # Check client is authorized
        if client_id not in library.authorized_clients:
            result['valid'] = False
            result['errors'].append(
                f"Client '{client.name}' is not authorized for library '{library.name}'"
            )
        
        # Check if client is revoked
        if client.revoked:
            result['warnings'].append(
                f"Client '{client.name}' certificate has been revoked"
            )
        
        # Check if server host is valid
        if self.server_config.server.host == '0.0.0.0':
            result['warnings'].append(
                "Server is configured to listen on all interfaces. "
                "You will need to specify the actual server hostname when exporting."
            )
        
        return result


def export_client_config_quick(
    server_config: ServerConfig,
    library_id: str,
    client_id: str,
    output_path: str,
    server_host: Optional[str] = None,
    encrypt: bool = False,
    password: Optional[str] = None
) -> str:
    """
    Quick utility function to export a client configuration.
    
    Args:
        server_config: Server configuration object
        library_id: Library UUID
        client_id: Client UUID
        output_path: Path to save configuration
        server_host: Server hostname/IP (optional)
        encrypt: Whether to encrypt configuration
        password: Encryption password (optional)
        
    Returns:
        Path to exported configuration file
    """
    exporter = ClientConfigExporter(server_config)
    return exporter.export_client_config(
        library_id=library_id,
        client_id=client_id,
        output_path=output_path,
        server_host=server_host,
        encrypt=encrypt,
        password=password
    )
