"""
Disk-based storage manager for user-specific persistent data.
"""
import json
import os
import pickle
import time
from pathlib import Path
from typing import Any, Optional, List, Dict
import logging


logger = logging.getLogger(__name__)


class DiskManager:
    """Manages disk-based storage for user-specific data."""
    
    def __init__(self, user_storage_path: str):
        """
        Initialize disk manager with user storage path.
        
        Args:
            user_storage_path: Base path for user storage
        """
        self.user_storage_path = Path(user_storage_path).expanduser()
        self.ensure_user_directory()
    
    def save(self, key: str, value: Any, category: str = "general") -> bool:
        """
        Save value to disk with category organization.
        
        Args:
            key: Storage key
            value: Value to save
            category: Storage category (templates, environments, etc.)
            
        Returns:
            True if successfully saved
        """
        try:
            category_path = self.user_storage_path / category
            category_path.mkdir(exist_ok=True)
            
            file_path = category_path / f"{key}.json"
            
            # Serialize value
            if isinstance(value, (dict, list, str, int, float, bool, type(None))):
                # JSON serializable
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(value, f, indent=2, default=str)
            else:
                # Use pickle for complex objects
                pickle_path = category_path / f"{key}.pkl"
                with open(pickle_path, 'wb') as f:
                    pickle.dump(value, f)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save {key} to disk: {e}")
            return False
    
    def load(self, key: str, category: str = "general") -> Optional[Any]:
        """
        Load value from disk.
        
        Args:
            key: Storage key
            category: Storage category
            
        Returns:
            Loaded value or None if not found
        """
        try:
            category_path = self.user_storage_path / category
            
            # Try JSON first
            json_path = category_path / f"{key}.json"
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            # Try pickle
            pickle_path = category_path / f"{key}.pkl"
            if pickle_path.exists():
                with open(pickle_path, 'rb') as f:
                    return pickle.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load {key} from disk: {e}")
            return None
    
    def delete(self, key: str, category: str = "general") -> bool:
        """
        Delete key from disk storage.
        
        Args:
            key: Storage key
            category: Storage category
            
        Returns:
            True if successfully deleted
        """
        try:
            category_path = self.user_storage_path / category
            
            # Try to delete both JSON and pickle versions
            json_path = category_path / f"{key}.json"
            pickle_path = category_path / f"{key}.pkl"
            
            deleted = False
            if json_path.exists():
                json_path.unlink()
                deleted = True
            
            if pickle_path.exists():
                pickle_path.unlink()
                deleted = True
            
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete {key} from disk: {e}")
            return False
    
    def list_files(self, category: str = "general", pattern: str = "*") -> List[str]:
        """
        List files in category matching pattern.
        
        Args:
            category: Storage category
            pattern: File pattern to match
            
        Returns:
            List of file keys (without extensions)
        """
        try:
            category_path = self.user_storage_path / category
            if not category_path.exists():
                return []
            
            files = []
            for file_path in category_path.iterdir():
                if file_path.is_file():
                    # Remove extension to get key
                    key = file_path.stem
                    if pattern == "*" or pattern in key:
                        files.append(key)
            
            return sorted(list(set(files)))  # Remove duplicates and sort
            
        except Exception as e:
            logger.error(f"Failed to list files in {category}: {e}")
            return []
    
    def ensure_user_directory(self) -> bool:
        """
        Ensure user storage directory exists with proper structure and permissions.
        
        Returns:
            True if directory structure is ready
        """
        try:
            # Create main user directory with proper permissions
            self.user_storage_path.mkdir(parents=True, exist_ok=True, mode=0o700)
            
            # Verify we can write to the directory
            test_file = self.user_storage_path / ".write_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
            except Exception as e:
                logger.error(f"Cannot write to user directory {self.user_storage_path}: {e}")
                return False
            
            # Create category subdirectories
            categories = [
                "templates",
                "environments", 
                "history",
                "cache",
                "config"
            ]
            
            for category in categories:
                category_path = self.user_storage_path / category
                category_path.mkdir(exist_ok=True, mode=0o700)
            
            # Create metadata files for tracking
            metadata_file = self.user_storage_path / "metadata.json"
            if not metadata_file.exists():
                metadata = {
                    "created_at": time.time(),
                    "version": "1.0",
                    "categories": categories
                }
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
            
            return True
            
        except PermissionError as e:
            logger.error(f"Permission denied creating user directory: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to create user directory structure: {e}")
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about disk storage usage.
        
        Returns:
            Dictionary with storage information
        """
        try:
            total_size = 0
            file_count = 0
            
            for root, dirs, files in os.walk(self.user_storage_path):
                for file in files:
                    file_path = Path(root) / file
                    try:
                        total_size += file_path.stat().st_size
                        file_count += 1
                    except OSError:
                        continue
            
            return {
                'storage_path': str(self.user_storage_path),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'categories': self.list_categories()
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            return {
                'storage_path': str(self.user_storage_path),
                'error': str(e)
            }
    
    def list_categories(self) -> List[str]:
        """
        List available storage categories.
        
        Returns:
            List of category names
        """
        try:
            categories = []
            for item in self.user_storage_path.iterdir():
                if item.is_dir():
                    categories.append(item.name)
            return sorted(categories)
            
        except Exception:
            return []
    
    def cleanup_empty_categories(self) -> bool:
        """
        Remove empty category directories.
        
        Returns:
            True if cleanup completed successfully
        """
        try:
            for category_path in self.user_storage_path.iterdir():
                if category_path.is_dir() and not any(category_path.iterdir()):
                    category_path.rmdir()
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup empty categories: {e}")
            return False