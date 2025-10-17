"""
FileHarbor Configuration Backup and Restore

Utilities for backing up and restoring configuration files.
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from fileharbor.common.constants import (
    CONFIG_BACKUP_EXTENSION,
    CONFIG_BACKUP_DATE_FORMAT,
    MAX_CONFIG_BACKUPS,
)
from fileharbor.common.exceptions import ConfigurationError


class ConfigBackupManager:
    """Manages configuration file backups."""
    
    def __init__(self, config_path: str):
        """
        Initialize backup manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.backup_dir = self.config_path.parent / '.fileharbor_backups'
    
    def create_backup(self, comment: Optional[str] = None) -> str:
        """
        Create a backup of the configuration file.
        
        Args:
            comment: Optional comment to include in backup metadata
            
        Returns:
            Path to backup file
            
        Raises:
            ConfigurationError: If backup fails
        """
        if not self.config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {self.config_path}")
        
        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime(CONFIG_BACKUP_DATE_FORMAT)
        backup_name = f"{self.config_path.name}.{timestamp}{CONFIG_BACKUP_EXTENSION}"
        backup_path = self.backup_dir / backup_name
        
        # Copy configuration file
        try:
            shutil.copy2(self.config_path, backup_path)
        except Exception as e:
            raise ConfigurationError(f"Failed to create backup: {e}")
        
        # Create metadata file
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'original_file': str(self.config_path),
            'backup_file': str(backup_path),
            'comment': comment,
        }
        
        metadata_path = backup_path.with_suffix(backup_path.suffix + '.meta')
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            # Non-critical error, backup still created
            pass
        
        # Clean up old backups
        self._cleanup_old_backups()
        
        return str(backup_path)
    
    def list_backups(self) -> List[dict]:
        """
        List all available backups.
        
        Returns:
            List of backup information dictionaries
        """
        if not self.backup_dir.exists():
            return []
        
        backups = []
        
        # Find all backup files
        pattern = f"{self.config_path.name}.*{CONFIG_BACKUP_EXTENSION}"
        for backup_file in self.backup_dir.glob(pattern):
            # Get file stats
            stat = backup_file.stat()
            
            # Try to load metadata
            metadata_path = backup_file.with_suffix(backup_file.suffix + '.meta')
            metadata = {}
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except Exception:
                    pass
            
            backup_info = {
                'path': str(backup_file),
                'filename': backup_file.name,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'comment': metadata.get('comment'),
            }
            
            backups.append(backup_info)
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        return backups
    
    def restore_backup(self, backup_path: str, create_backup_first: bool = True) -> None:
        """
        Restore configuration from a backup.
        
        Args:
            backup_path: Path to backup file to restore
            create_backup_first: Whether to backup current config before restoring
            
        Raises:
            ConfigurationError: If restore fails
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            raise ConfigurationError(f"Backup file not found: {backup_path}")
        
        # Create backup of current config first
        if create_backup_first and self.config_path.exists():
            try:
                self.create_backup(comment="Auto-backup before restore")
            except Exception as e:
                # Log warning but continue
                print(f"Warning: Failed to create pre-restore backup: {e}")
        
        # Restore from backup
        try:
            shutil.copy2(backup_path, self.config_path)
        except Exception as e:
            raise ConfigurationError(f"Failed to restore backup: {e}")
    
    def delete_backup(self, backup_path: str) -> None:
        """
        Delete a backup file.
        
        Args:
            backup_path: Path to backup file to delete
            
        Raises:
            ConfigurationError: If deletion fails
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            raise ConfigurationError(f"Backup file not found: {backup_path}")
        
        try:
            # Delete backup file
            backup_path.unlink()
            
            # Delete metadata file if it exists
            metadata_path = backup_path.with_suffix(backup_path.suffix + '.meta')
            if metadata_path.exists():
                metadata_path.unlink()
                
        except Exception as e:
            raise ConfigurationError(f"Failed to delete backup: {e}")
    
    def _cleanup_old_backups(self) -> None:
        """
        Clean up old backups, keeping only the most recent ones.
        
        Keeps up to MAX_CONFIG_BACKUPS backups.
        """
        if not self.backup_dir.exists():
            return
        
        backups = self.list_backups()
        
        # Delete old backups if we have too many
        if len(backups) > MAX_CONFIG_BACKUPS:
            # Sort by creation time (oldest first)
            backups.sort(key=lambda x: x['created'])
            
            # Delete oldest backups
            for backup in backups[:-MAX_CONFIG_BACKUPS]:
                try:
                    self.delete_backup(backup['path'])
                except Exception:
                    # Ignore errors during cleanup
                    pass
    
    def get_backup_size(self) -> int:
        """
        Get total size of all backups in bytes.
        
        Returns:
            Total size of backups in bytes
        """
        if not self.backup_dir.exists():
            return 0
        
        total_size = 0
        for backup in self.list_backups():
            total_size += backup['size']
        
        return total_size
    
    def export_backup(self, backup_path: str, export_path: str) -> None:
        """
        Export a backup to a different location.
        
        Args:
            backup_path: Path to backup file
            export_path: Destination path
            
        Raises:
            ConfigurationError: If export fails
        """
        backup_path = Path(backup_path)
        export_path = Path(export_path)
        
        if not backup_path.exists():
            raise ConfigurationError(f"Backup file not found: {backup_path}")
        
        try:
            shutil.copy2(backup_path, export_path)
            
            # Also copy metadata if it exists
            metadata_path = backup_path.with_suffix(backup_path.suffix + '.meta')
            if metadata_path.exists():
                export_meta_path = export_path.with_suffix(export_path.suffix + '.meta')
                shutil.copy2(metadata_path, export_meta_path)
                
        except Exception as e:
            raise ConfigurationError(f"Failed to export backup: {e}")


def create_quick_backup(config_path: str, comment: Optional[str] = None) -> str:
    """
    Quick utility function to create a backup.
    
    Args:
        config_path: Path to configuration file
        comment: Optional comment
        
    Returns:
        Path to backup file
    """
    manager = ConfigBackupManager(config_path)
    return manager.create_backup(comment=comment)


def restore_from_backup(config_path: str, backup_path: str) -> None:
    """
    Quick utility function to restore from backup.
    
    Args:
        config_path: Path to configuration file
        backup_path: Path to backup file
    """
    manager = ConfigBackupManager(config_path)
    manager.restore_backup(backup_path)
