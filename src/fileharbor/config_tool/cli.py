"""
FileHarbor Configuration Tool CLI

Interactive command-line tool for managing FileHarbor server configurations.

Usage:
    fileharbor-config <config_file>
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Optional

from fileharbor.__version__ import __version__
from fileharbor.common.config_schema import (
    ServerConfig,
    create_default_server_config,
    save_config_to_file,
    load_config_from_file,
)
from fileharbor.common.exceptions import (
    FileHarborException,
    ConfigurationError,
)
from fileharbor.config_tool.menu import Menu, MenuItem
from fileharbor.config_tool.server_config_editor import ServerConfigEditor
from fileharbor.config_tool.certificate_manager import CertificateManager
from fileharbor.config_tool.client_config_exporter import ClientConfigExporter
from fileharbor.config_tool.backup import ConfigBackupManager
from fileharbor.config_tool.encryption import (
    is_config_encrypted,
    load_config_with_password,
    save_config_with_encryption,
)


class FileHarborConfigTool:
    """Main configuration tool application."""
    
    def __init__(self, config_path: str):
        """
        Initialize configuration tool.
        
        Args:
            config_path: Path to server configuration file
        """
        self.config_path = Path(config_path)
        self.config: Optional[ServerConfig] = None
        self.editor: Optional[ServerConfigEditor] = None
        self.cert_manager = CertificateManager()
        self.backup_manager = ConfigBackupManager(str(self.config_path))
        self.modified = False
    
    def run(self) -> int:
        """
        Run the configuration tool.
        
        Returns:
            Exit code (0 for success, 1 for error)
        """
        try:
            # Load or create configuration
            if not self._load_or_create_config():
                return 1
            
            # Initialize editor
            self.editor = ServerConfigEditor(self.config)
            
            # Run main menu
            self._main_menu()
            
            # Prompt to save if modified
            if self.modified:
                if Menu.confirm("Configuration has been modified. Save changes?", default=True):
                    self._save_config()
                    Menu.display_success("Configuration saved successfully!")
            
            return 0
            
        except KeyboardInterrupt:
            print("\n\nExiting...")
            return 0
        except Exception as e:
            Menu.display_error(f"Fatal error: {e}")
            return 1
    
    def _load_or_create_config(self) -> bool:
        """
        Load existing configuration or create a new one.
        
        Returns:
            True if successful, False otherwise
        """
        if self.config_path.exists():
            # Load existing configuration
            try:
                # Check if encrypted
                password = None
                if is_config_encrypted(str(self.config_path)):
                    import getpass
                    password = getpass.getpass("Configuration file is encrypted. Enter password: ")
                
                config_dict = load_config_with_password(str(self.config_path), password)
                self.config = ServerConfig.from_dict(config_dict)
                
                # Validate
                errors = self.config.validate()
                if errors:
                    Menu.display_warning("Configuration has validation errors:")
                    for error in errors:
                        print(f"  - {error}")
                    Menu.pause()
                
                Menu.display_success(f"Loaded configuration from {self.config_path}")
                return True
                
            except Exception as e:
                Menu.display_error(f"Failed to load configuration: {e}")
                return False
        else:
            # Create new configuration
            Menu.clear_screen()
            Menu.display_header("Create New Server Configuration")
            
            if not Menu.confirm(
                f"Configuration file '{self.config_path}' does not exist.\nCreate new configuration?",
                default=True
            ):
                return False
            
            self.config = create_default_server_config()
            
            # Initialize CA
            print("\nInitializing Certificate Authority...")
            org_name = Menu.prompt_string("Organization name", default="FileHarbor")
            
            try:
                self.editor = ServerConfigEditor(self.config)
                self.editor.initialize_ca(
                    common_name=f"{org_name} CA",
                    organization=org_name
                )
                Menu.display_success("Certificate Authority created successfully!")
            except Exception as e:
                Menu.display_error(f"Failed to create CA: {e}")
                return False
            
            self.modified = True
            Menu.pause()
            return True
    
    def _save_config(self, encrypt: bool = False) -> None:
        """
        Save configuration to file.
        
        Args:
            encrypt: Whether to encrypt the configuration
        """
        # Create backup first
        if self.config_path.exists():
            try:
                backup_path = self.backup_manager.create_backup(comment="Auto-backup before save")
                print(f"  Backup created: {backup_path}")
            except Exception as e:
                print(f"  Warning: Failed to create backup: {e}")
        
        # Save configuration
        password = None
        if encrypt:
            import getpass
            password = getpass.getpass("Enter encryption password: ")
        
        save_config_with_encryption(
            config_dict=self.config.to_dict(),
            config_path=str(self.config_path),
            encrypt=encrypt,
            password=password
        )
        
        self.modified = False
    
    # ========================================================================
    # Main Menu
    # ========================================================================
    
    def _main_menu(self) -> None:
        """Display and run the main menu."""
        menu = Menu("FileHarbor Configuration Tool", [
            MenuItem("Server Settings", action=self._server_settings_menu),
            MenuItem("Manage Libraries", action=self._libraries_menu),
            MenuItem("Manage Clients", action=self._clients_menu),
            MenuItem("Export Client Configuration", action=self._export_client_config),
            MenuItem("Backup & Restore", action=self._backup_menu),
            MenuItem("Configuration Encryption", action=self._encryption_menu),
            MenuItem("Save Configuration", action=self._menu_save_config),
            MenuItem("Exit", action=lambda: 'exit'),
        ])
        
        menu.run()
    
    # ========================================================================
    # Server Settings Menu
    # ========================================================================
    
    def _server_settings_menu(self) -> None:
        """Server settings submenu."""
        menu = Menu("Server Settings", [
            MenuItem("View Current Settings", action=self._view_server_settings),
            MenuItem("Edit Network Settings", action=self._edit_network_settings),
            MenuItem("Edit Logging Settings", action=self._edit_logging_settings),
            MenuItem("View Certificate Authority Info", action=self._view_ca_info),
            MenuItem("Back", action=lambda: 'back'),
        ])
        
        menu.run()
    
    def _view_server_settings(self) -> None:
        """View current server settings."""
        Menu.display_header("Current Server Settings")
        
        Menu.display_info_box("Network Configuration", {
            "Host": self.config.server.host,
            "Port": self.config.server.port,
            "Max Connections": self.config.server.max_connections,
            "Worker Threads": self.config.server.worker_threads,
            "Idle Timeout": f"{self.config.server.idle_timeout} seconds",
            "Chunk Size": self.config.server.chunk_size,
        })
        
        Menu.display_info_box("Logging Configuration", {
            "Log Level": self.config.logging.level,
            "Log File": self.config.logging.file or "Console only",
            "Max Log Size": self.config.logging.max_size,
            "Backup Count": self.config.logging.backup_count,
        })
        
        Menu.pause()
    
    def _edit_network_settings(self) -> None:
        """Edit network settings."""
        Menu.display_header("Edit Network Settings")
        
        print("Leave blank to keep current value.\n")
        
        host = Menu.prompt_string("Host", default=self.config.server.host, required=False)
        port = Menu.prompt_int("Port", default=self.config.server.port, min_value=1, max_value=65535)
        threads = Menu.prompt_int("Worker Threads", default=self.config.server.worker_threads, min_value=1)
        
        try:
            self.editor.update_server_settings(
                host=host if host else None,
                port=port,
                worker_threads=threads
            )
            self.modified = True
            Menu.display_success("Network settings updated!")
        except Exception as e:
            Menu.display_error(f"Failed to update settings: {e}")
        
        Menu.pause()
    
    def _edit_logging_settings(self) -> None:
        """Edit logging settings."""
        Menu.display_header("Edit Logging Settings")
        
        levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        print("Available log levels:")
        for i, level in enumerate(levels, 1):
            print(f"  {i}. {level}")
        
        level_choice = Menu.prompt_int("\nSelect log level", min_value=1, max_value=len(levels))
        
        if level_choice:
            level = levels[level_choice - 1]
            
            try:
                self.editor.update_logging_settings(level=level)
                self.modified = True
                Menu.display_success("Logging settings updated!")
            except Exception as e:
                Menu.display_error(f"Failed to update settings: {e}")
        
        Menu.pause()
    
    def _view_ca_info(self) -> None:
        """View Certificate Authority information."""
        if not self.config.security.ca_certificate:
            Menu.display_warning("Certificate Authority not initialized!")
            Menu.pause()
            return
        
        Menu.display_header("Certificate Authority Information")
        
        try:
            ca_info = self.cert_manager.get_ca_info(self.config.security.ca_certificate)
            Menu.display_info_box("CA Details", {
                "Subject": ca_info['subject'],
                "Serial Number": ca_info['serial_number'],
                "Fingerprint": ca_info['fingerprint'][:32] + "...",
                "Valid From": ca_info['not_valid_before'],
                "Valid Until": ca_info['not_valid_after'],
            })
        except Exception as e:
            Menu.display_error(f"Failed to get CA info: {e}")
        
        Menu.pause()
    
    # ========================================================================
    # Libraries Menu
    # ========================================================================
    
    def _libraries_menu(self) -> None:
        """Libraries management submenu."""
        menu = Menu("Manage Libraries", [
            MenuItem("List Libraries", action=self._list_libraries),
            MenuItem("Add Library", action=self._add_library),
            MenuItem("Edit Library", action=self._edit_library),
            MenuItem("Remove Library", action=self._remove_library),
            MenuItem("Manage Library Access", action=self._manage_library_access),
            MenuItem("Back", action=lambda: 'back'),
        ])
        
        menu.run()
    
    def _list_libraries(self) -> None:
        """List all libraries."""
        Menu.display_header("Libraries")
        
        libraries = self.editor.list_libraries()
        
        if not libraries:
            print("No libraries configured.")
        else:
            Menu.display_table(
                ["Name", "Path", "Clients"],
                [[name, path, str(count)] for _, name, path, count in libraries]
            )
        
        Menu.pause()
    
    def _add_library(self) -> None:
        """Add a new library."""
        Menu.display_header("Add New Library")
        
        name = Menu.prompt_string("Library name")
        if not name:
            return
        
        path = Menu.prompt_string("Library path")
        if not path:
            return
        
        try:
            library_id = self.editor.add_library(name=name, path=path)
            self.modified = True
            Menu.display_success(f"Library '{name}' added successfully!")
            print(f"Library ID: {library_id}")
        except Exception as e:
            Menu.display_error(f"Failed to add library: {e}")
        
        Menu.pause()
    
    def _edit_library(self) -> None:
        """Edit an existing library."""
        libraries = self.editor.list_libraries()
        
        if not libraries:
            Menu.display_warning("No libraries to edit.")
            Menu.pause()
            return
        
        choices = [(lib_id, f"{name} ({path})") for lib_id, name, path, _ in libraries]
        index = Menu.prompt_choice_from_list("Select library to edit:", choices)
        
        if index is None:
            return
        
        library_id = choices[index][0]
        library = self.config.libraries[library_id]
        
        Menu.display_header(f"Edit Library: {library.name}")
        print("Leave blank to keep current value.\n")
        
        name = Menu.prompt_string("Library name", default=library.name, required=False)
        path = Menu.prompt_string("Library path", default=library.path, required=False)
        
        try:
            self.editor.update_library(
                library_id=library_id,
                name=name if name else None,
                path=path if path else None
            )
            self.modified = True
            Menu.display_success("Library updated successfully!")
        except Exception as e:
            Menu.display_error(f"Failed to update library: {e}")
        
        Menu.pause()
    
    def _remove_library(self) -> None:
        """Remove a library."""
        libraries = self.editor.list_libraries()
        
        if not libraries:
            Menu.display_warning("No libraries to remove.")
            Menu.pause()
            return
        
        choices = [(lib_id, f"{name} ({path})") for lib_id, name, path, _ in libraries]
        index = Menu.prompt_choice_from_list("Select library to remove:", choices)
        
        if index is None:
            return
        
        library_id = choices[index][0]
        library_name = self.config.libraries[library_id].name
        
        if not Menu.confirm(f"Remove library '{library_name}'?", default=False):
            return
        
        try:
            self.editor.remove_library(library_id)
            self.modified = True
            Menu.display_success("Library removed successfully!")
        except Exception as e:
            Menu.display_error(f"Failed to remove library: {e}")
        
        Menu.pause()
    
    def _manage_library_access(self) -> None:
        """Manage client access to libraries."""
        libraries = self.editor.list_libraries()
        
        if not libraries:
            Menu.display_warning("No libraries configured.")
            Menu.pause()
            return
        
        choices = [(lib_id, name) for lib_id, name, _, _ in libraries]
        index = Menu.prompt_choice_from_list("Select library:", choices)
        
        if index is None:
            return
        
        library_id = choices[index][0]
        self._library_access_menu(library_id)
    
    def _library_access_menu(self, library_id: str) -> None:
        """Manage access for a specific library."""
        library = self.config.libraries[library_id]
        
        menu = Menu(f"Library Access: {library.name}", [
            MenuItem("View Authorized Clients", action=lambda: self._view_library_clients(library_id)),
            MenuItem("Grant Access to Client", action=lambda: self._grant_library_access(library_id)),
            MenuItem("Revoke Access from Client", action=lambda: self._revoke_library_access(library_id)),
            MenuItem("Back", action=lambda: 'back'),
        ])
        
        menu.run()
    
    def _view_library_clients(self, library_id: str) -> None:
        """View clients with access to a library."""
        library = self.config.libraries[library_id]
        Menu.display_header(f"Authorized Clients: {library.name}")
        
        clients = self.editor.list_library_clients(library_id)
        
        if not clients:
            print("No clients have access to this library.")
        else:
            Menu.display_table(
                ["Client Name", "Revoked"],
                [[name, "Yes" if revoked else "No"] for _, name, revoked in clients]
            )
        
        Menu.pause()
    
    def _grant_library_access(self, library_id: str) -> None:
        """Grant a client access to a library."""
        all_clients = self.editor.list_clients()
        library_clients = {client_id for client_id, _, _ in self.editor.list_library_clients(library_id)}
        
        # Filter out clients that already have access
        available_clients = [
            (client_id, name)
            for client_id, name, _, _ in all_clients
            if client_id not in library_clients
        ]
        
        if not available_clients:
            Menu.display_warning("No clients available to grant access.")
            Menu.pause()
            return
        
        index = Menu.prompt_choice_from_list("Select client to grant access:", available_clients)
        
        if index is None:
            return
        
        client_id = available_clients[index][0]
        
        try:
            self.editor.grant_library_access(library_id, client_id)
            self.modified = True
            Menu.display_success("Access granted successfully!")
        except Exception as e:
            Menu.display_error(f"Failed to grant access: {e}")
        
        Menu.pause()
    
    def _revoke_library_access(self, library_id: str) -> None:
        """Revoke a client's access to a library."""
        clients = self.editor.list_library_clients(library_id)
        
        if not clients:
            Menu.display_warning("No clients have access to this library.")
            Menu.pause()
            return
        
        choices = [(client_id, name) for client_id, name, _ in clients]
        index = Menu.prompt_choice_from_list("Select client to revoke access:", choices)
        
        if index is None:
            return
        
        client_id = choices[index][0]
        
        try:
            self.editor.revoke_library_access(library_id, client_id)
            self.modified = True
            Menu.display_success("Access revoked successfully!")
        except Exception as e:
            Menu.display_error(f"Failed to revoke access: {e}")
        
        Menu.pause()
    
    # ========================================================================
    # Clients Menu
    # ========================================================================
    
    def _clients_menu(self) -> None:
        """Clients management submenu."""
        menu = Menu("Manage Clients", [
            MenuItem("List Clients", action=self._list_clients),
            MenuItem("Add Client", action=self._add_client),
            MenuItem("Remove Client", action=self._remove_client),
            MenuItem("Revoke Client Certificate", action=self._revoke_client),
            MenuItem("Set Client Rate Limit", action=self._set_client_rate_limit),
            MenuItem("Back", action=lambda: 'back'),
        ])
        
        menu.run()
    
    def _list_clients(self) -> None:
        """List all clients."""
        Menu.display_header("Clients")
        
        clients = self.editor.list_clients()
        
        if not clients:
            print("No clients configured.")
        else:
            # Add rate limit information
            rows = []
            for client_id, name, revoked, lib_count in clients:
                rate_limit = self.editor.get_client_rate_limit(client_id)
                if rate_limit == 0:
                    rate_str = "Unlimited"
                else:
                    rate_str = f"{rate_limit / (1024 * 1024):.2f} MB/s"
                
                rows.append([name, "Yes" if revoked else "No", str(lib_count), rate_str])
            
            Menu.display_table(
                ["Name", "Revoked", "Libraries", "Rate Limit"],
                rows
            )
        
        Menu.pause()
    
    def _add_client(self) -> None:
        """Add a new client."""
        Menu.display_header("Add New Client")
        
        if not self.config.security.ca_certificate:
            Menu.display_error("Certificate Authority not initialized! Cannot create client certificate.")
            Menu.pause()
            return
        
        name = Menu.prompt_string("Client name")
        if not name:
            return
        
        try:
            client_id = self.editor.add_client(name=name)
            self.modified = True
            Menu.display_success(f"Client '{name}' added successfully!")
            print(f"Client ID: {client_id}")
            print("\nNote: Client certificate has been generated.")
            print("You can export client configuration using 'Export Client Configuration' menu.")
        except Exception as e:
            Menu.display_error(f"Failed to add client: {e}")
        
        Menu.pause()
    
    def _remove_client(self) -> None:
        """Remove a client."""
        clients = self.editor.list_clients()
        
        if not clients:
            Menu.display_warning("No clients to remove.")
            Menu.pause()
            return
        
        choices = [(client_id, name) for client_id, name, _, _ in clients]
        index = Menu.prompt_choice_from_list("Select client to remove:", choices)
        
        if index is None:
            return
        
        client_id = choices[index][0]
        client_name = self.config.clients[client_id].name
        
        if not Menu.confirm(f"Remove client '{client_name}'?", default=False):
            return
        
        try:
            self.editor.remove_client(client_id)
            self.modified = True
            Menu.display_success("Client removed successfully!")
        except Exception as e:
            Menu.display_error(f"Failed to remove client: {e}")
        
        Menu.pause()
    
    def _revoke_client(self) -> None:
        """Revoke a client certificate."""
        clients = self.editor.list_clients()
        
        if not clients:
            Menu.display_warning("No clients configured.")
            Menu.pause()
            return
        
        # Filter non-revoked clients
        active_clients = [(client_id, name) for client_id, name, revoked, _ in clients if not revoked]
        
        if not active_clients:
            Menu.display_warning("No active clients to revoke.")
            Menu.pause()
            return
        
        index = Menu.prompt_choice_from_list("Select client to revoke:", active_clients)
        
        if index is None:
            return
        
        client_id = active_clients[index][0]
        client_name = self.config.clients[client_id].name
        
        if not Menu.confirm(f"Revoke certificate for client '{client_name}'?", default=False):
            return
        
        try:
            self.editor.revoke_client(client_id)
            self.modified = True
            Menu.display_success("Client certificate revoked successfully!")
        except Exception as e:
            Menu.display_error(f"Failed to revoke client: {e}")
        
        Menu.pause()
    
    def _set_client_rate_limit(self) -> None:
        """Set rate limit for a client."""
        Menu.display_header("Set Client Rate Limit")
        
        clients = self.editor.list_clients()
        
        if not clients:
            Menu.display_warning("No clients configured.")
            Menu.pause()
            return
        
        # Select client
        choices = [(client_id, f"{name} ({'Revoked' if revoked else 'Active'})")
                   for client_id, name, revoked, _ in clients]
        
        index = Menu.prompt_choice_from_list("Select client:", choices)
        
        if index is None:
            return
        
        client_id = choices[index][0]
        client_name = self.config.clients[client_id].name
        
        # Get current rate limit
        current_rate = self.editor.get_client_rate_limit(client_id)
        if current_rate == 0:
            current_str = "unlimited"
        else:
            current_str = f"{current_rate / (1024 * 1024):.2f} MB/s"
        
        print(f"\nCurrent rate limit: {current_str}")
        print("\nEnter new rate limit:")
        print("  - Enter 0 for unlimited")
        print("  - Enter value in KB/s (e.g., 1024 for 1 MB/s)")
        print("  - Minimum: 1 KB/s (1024 bytes/s)")
        
        try:
            rate_input = input("\nRate limit (KB/s): ").strip()
            
            if not rate_input:
                Menu.display_warning("Cancelled.")
                Menu.pause()
                return
            
            rate_kbps = float(rate_input)
            
            if rate_kbps < 0:
                Menu.display_error("Rate limit cannot be negative.")
                Menu.pause()
                return
            
            # Convert KB/s to bytes/s
            rate_bps = int(rate_kbps * 1024)
            
            # Set the rate limit
            self.editor.set_client_rate_limit(client_id, rate_bps)
            self.modified = True
            
            if rate_bps == 0:
                display_rate = "unlimited"
            else:
                display_rate = f"{rate_bps / (1024 * 1024):.2f} MB/s ({rate_kbps:.0f} KB/s)"
            
            Menu.display_success(f"Rate limit for '{client_name}' set to: {display_rate}")
            
        except ValueError as e:
            Menu.display_error(f"Invalid input: {e}")
        except Exception as e:
            Menu.display_error(f"Failed to set rate limit: {e}")
        
        Menu.pause()
    
    # ========================================================================
    # Export Client Configuration
    # ========================================================================
    
    def _export_client_config(self) -> None:
        """Export client configuration."""
        libraries = self.editor.list_libraries()
        
        if not libraries:
            Menu.display_warning("No libraries configured.")
            Menu.pause()
            return
        
        Menu.display_header("Export Client Configuration")
        
        # Select library
        lib_choices = [(lib_id, name) for lib_id, name, _, _ in libraries]
        lib_index = Menu.prompt_choice_from_list("Select library:", lib_choices)
        
        if lib_index is None:
            return
        
        library_id = lib_choices[lib_index][0]
        
        # Select client
        exporter = ClientConfigExporter(self.config)
        exportable = exporter.list_exportable_clients(library_id)
        
        if not exportable:
            Menu.display_warning("No clients have access to this library.")
            Menu.pause()
            return
        
        client_choices = [(client_id, f"{name} {'(REVOKED)' if revoked else ''}")
                          for client_id, name, revoked in exportable]
        client_index = Menu.prompt_choice_from_list("Select client:", client_choices)
        
        if client_index is None:
            return
        
        client_id = client_choices[client_index][0]
        
        # Get server host
        server_host = Menu.prompt_string(
            "Server hostname/IP",
            default=self.config.server.host if self.config.server.host != '0.0.0.0' else None
        )
        if not server_host:
            return
        
        # Get output path
        default_output = f"client_config_{client_id[:8]}.json"
        output_path = Menu.prompt_string("Output file path", default=default_output)
        if not output_path:
            return
        
        # Ask about encryption
        encrypt = Menu.confirm("Encrypt client configuration?", default=True)
        
        try:
            exporter.export_client_config(
                library_id=library_id,
                client_id=client_id,
                output_path=output_path,
                server_host=server_host,
                encrypt=encrypt
            )
            Menu.display_success(f"Client configuration exported to: {output_path}")
        except Exception as e:
            Menu.display_error(f"Failed to export configuration: {e}")
        
        Menu.pause()
    
    # ========================================================================
    # Backup & Restore
    # ========================================================================
    
    def _backup_menu(self) -> None:
        """Backup and restore submenu."""
        menu = Menu("Backup & Restore", [
            MenuItem("Create Backup", action=self._create_backup),
            MenuItem("List Backups", action=self._list_backups),
            MenuItem("Restore from Backup", action=self._restore_backup),
            MenuItem("Delete Backup", action=self._delete_backup),
            MenuItem("Back", action=lambda: 'back'),
        ])
        
        menu.run()
    
    def _create_backup(self) -> None:
        """Create a configuration backup."""
        Menu.display_header("Create Backup")
        
        comment = Menu.prompt_string("Backup comment (optional)", required=False)
        
        try:
            backup_path = self.backup_manager.create_backup(comment=comment)
            Menu.display_success(f"Backup created: {backup_path}")
        except Exception as e:
            Menu.display_error(f"Failed to create backup: {e}")
        
        Menu.pause()
    
    def _list_backups(self) -> None:
        """List all backups."""
        Menu.display_header("Available Backups")
        
        backups = self.backup_manager.list_backups()
        
        if not backups:
            print("No backups available.")
        else:
            from fileharbor.utils import format_file_size
            Menu.display_table(
                ["Filename", "Created", "Size", "Comment"],
                [[b['filename'][:40], b['created'][:19], format_file_size(b['size']),
                  b['comment'] or ""] for b in backups]
            )
        
        Menu.pause()
    
    def _restore_backup(self) -> None:
        """Restore from a backup."""
        backups = self.backup_manager.list_backups()
        
        if not backups:
            Menu.display_warning("No backups available.")
            Menu.pause()
            return
        
        choices = [(b['path'], f"{b['filename']} - {b['created'][:19]}") for b in backups]
        index = Menu.prompt_choice_from_list("Select backup to restore:", choices)
        
        if index is None:
            return
        
        backup_path = choices[index][0]
        
        if not Menu.confirm("This will replace the current configuration. Continue?", default=False):
            return
        
        try:
            self.backup_manager.restore_backup(backup_path, create_backup_first=True)
            Menu.display_success("Configuration restored successfully!")
            print("Reloading configuration...")
            
            # Reload configuration
            config_dict = load_config_with_password(str(self.config_path), None)
            self.config = ServerConfig.from_dict(config_dict)
            self.editor = ServerConfigEditor(self.config)
            self.modified = False
            
        except Exception as e:
            Menu.display_error(f"Failed to restore backup: {e}")
        
        Menu.pause()
    
    def _delete_backup(self) -> None:
        """Delete a backup."""
        backups = self.backup_manager.list_backups()
        
        if not backups:
            Menu.display_warning("No backups available.")
            Menu.pause()
            return
        
        choices = [(b['path'], f"{b['filename']} - {b['created'][:19]}") for b in backups]
        index = Menu.prompt_choice_from_list("Select backup to delete:", choices)
        
        if index is None:
            return
        
        backup_path = choices[index][0]
        
        if not Menu.confirm("Delete this backup?", default=False):
            return
        
        try:
            self.backup_manager.delete_backup(backup_path)
            Menu.display_success("Backup deleted successfully!")
        except Exception as e:
            Menu.display_error(f"Failed to delete backup: {e}")
        
        Menu.pause()
    
    # ========================================================================
    # Encryption Menu
    # ========================================================================
    
    def _encryption_menu(self) -> None:
        """Configuration encryption submenu."""
        is_encrypted = is_config_encrypted(str(self.config_path))
        
        status = "encrypted" if is_encrypted else "not encrypted"
        Menu.display_header(f"Configuration Encryption (Currently: {status})")
        
        if is_encrypted:
            if Menu.confirm("Configuration is encrypted. Remove encryption?", default=False):
                try:
                    self._save_config(encrypt=False)
                    Menu.display_success("Encryption removed!")
                except Exception as e:
                    Menu.display_error(f"Failed to remove encryption: {e}")
        else:
            if Menu.confirm("Configuration is not encrypted. Encrypt it?", default=True):
                try:
                    self._save_config(encrypt=True)
                    Menu.display_success("Configuration encrypted!")
                except Exception as e:
                    Menu.display_error(f"Failed to encrypt configuration: {e}")
        
        Menu.pause()
    
    def _menu_save_config(self) -> None:
        """Save configuration from menu."""
        try:
            self._save_config()
            Menu.display_success("Configuration saved successfully!")
        except Exception as e:
            Menu.display_error(f"Failed to save configuration: {e}")
        
        Menu.pause()


def main():
    """Main entry point for the configuration tool CLI."""
    parser = argparse.ArgumentParser(
        description="FileHarbor Configuration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fileharbor-config server_config.json          Create or edit configuration
  fileharbor-config /path/to/config.json        Use absolute path

For more information, visit: https://github.com/yourusername/fileharbor
        """
    )
    
    parser.add_argument(
        'config_file',
        help='Path to server configuration file'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'FileHarbor Configuration Tool v{__version__}'
    )
    
    args = parser.parse_args()
    
    # Run configuration tool
    tool = FileHarborConfigTool(args.config_file)
    sys.exit(tool.run())


if __name__ == '__main__':
    main()
