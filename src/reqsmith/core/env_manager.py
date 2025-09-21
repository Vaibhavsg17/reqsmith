"""
Environment manager for managing environment variables across different stages.
"""
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

from ..storage import (
    HybridStorage,
    EnvironmentStorage,
    Environment
)


logger = logging.getLogger(__name__)


class EnvironmentManager:
    """Manages environment variables for different stages (dev, staging, prod, etc.)."""
    
    def __init__(self, storage: HybridStorage):
        """
        Initialize environment manager.
        
        Args:
            storage: HybridStorage instance for persistence
        """
        self.storage = storage
        self.env_storage = EnvironmentStorage(storage)
        self._current_environment = None
        
        # Load current environment on initialization
        self._load_current_environment()
    
    def create_environment(self, name: str, description: str = "",
                          variables: Optional[Dict[str, str]] = None) -> bool:
        """
        Create a new environment.
        
        Args:
            name: Environment name
            description: Environment description
            variables: Initial variables
            
        Returns:
            True if environment was created successfully
            
        Raises:
            ValueError: If environment name is invalid or already exists
        """
        if not name or not name.strip():
            raise ValueError("Environment name cannot be empty")
        
        name = name.strip()
        
        # Check if environment already exists
        if self.environment_exists(name):
            raise ValueError(f"Environment '{name}' already exists")
        
        # Validate environment name
        if not self._is_valid_environment_name(name):
            raise ValueError(f"Invalid environment name: {name}")
        
        # Create environment object
        environment = Environment(
            name=name,
            variables=variables or {},
            description=description,
            created_at=time.time(),
            last_modified=time.time()
        )
        
        # Validate environment
        if not environment.validate():
            raise ValueError("Environment validation failed")
        
        # Save environment
        success = self.env_storage.save_environment(environment)
        if success:
            logger.info(f"Environment '{name}' created successfully")
        else:
            logger.error(f"Failed to create environment '{name}'")
        
        return success
    
    def delete_environment(self, name: str) -> bool:
        """
        Delete an environment.
        
        Args:
            name: Environment name
            
        Returns:
            True if environment was deleted successfully
        """
        if not name or not name.strip():
            return False
        
        name = name.strip()
        
        # Check if environment exists
        if not self.environment_exists(name):
            logger.warning(f"Environment '{name}' not found for deletion")
            return False
        
        # Don't allow deletion of current environment
        if self.get_current_environment() == name:
            raise ValueError(f"Cannot delete current environment '{name}'. Switch to another environment first.")
        
        success = self.env_storage.delete_environment(name)
        if success:
            logger.info(f"Environment '{name}' deleted successfully")
        else:
            logger.error(f"Failed to delete environment '{name}'")
        
        return success
    
    def set_variable(self, env_name: str, key: str, value: str) -> bool:
        """
        Set a variable in an environment.
        
        Args:
            env_name: Environment name
            key: Variable key
            value: Variable value
            
        Returns:
            True if variable was set successfully
        """
        if not env_name or not key:
            return False
        
        env_name = env_name.strip()
        key = key.strip()
        
        # Load environment
        environment = self.env_storage.load_environment(env_name)
        if not environment:
            raise ValueError(f"Environment '{env_name}' not found")
        
        # Validate variable name
        if not self._is_valid_variable_name(key):
            raise ValueError(f"Invalid variable name: {key}")
        
        # Set variable
        environment.set_variable(key, value)
        
        # Save updated environment
        success = self.env_storage.save_environment(environment)
        if success:
            logger.debug(f"Variable '{key}' set in environment '{env_name}'")
        else:
            logger.error(f"Failed to set variable '{key}' in environment '{env_name}'")
        
        return success
    
    def get_variable(self, env_name: str, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a variable from an environment.
        
        Args:
            env_name: Environment name
            key: Variable key
            default: Default value if variable not found
            
        Returns:
            Variable value or default
        """
        if not env_name or not key:
            return default
        
        environment = self.env_storage.load_environment(env_name.strip())
        if not environment:
            return default
        
        return environment.get_variable(key.strip(), default)
    
    def delete_variable(self, env_name: str, key: str) -> bool:
        """
        Delete a variable from an environment.
        
        Args:
            env_name: Environment name
            key: Variable key
            
        Returns:
            True if variable was deleted successfully
        """
        if not env_name or not key:
            return False
        
        env_name = env_name.strip()
        key = key.strip()
        
        # Load environment
        environment = self.env_storage.load_environment(env_name)
        if not environment:
            return False
        
        # Delete variable
        success = environment.delete_variable(key)
        if success:
            # Save updated environment
            self.env_storage.save_environment(environment)
            logger.debug(f"Variable '{key}' deleted from environment '{env_name}'")
        
        return success
    
    def list_variables(self, env_name: str) -> Dict[str, str]:
        """
        List all variables in an environment.
        
        Args:
            env_name: Environment name
            
        Returns:
            Dictionary of variables
        """
        if not env_name:
            return {}
        
        environment = self.env_storage.load_environment(env_name.strip())
        if not environment:
            return {}
        
        return environment.variables.copy()
    
    def switch_environment(self, env_name: str) -> bool:
        """
        Switch to a different environment.
        
        Args:
            env_name: Environment name to switch to
            
        Returns:
            True if environment was switched successfully
        """
        if not env_name:
            return False
        
        env_name = env_name.strip()
        
        # Check if environment exists
        if not self.environment_exists(env_name):
            raise ValueError(f"Environment '{env_name}' not found")
        
        # Set as current environment
        success = self.env_storage.set_current_environment(env_name)
        if success:
            self._current_environment = env_name
            logger.info(f"Switched to environment '{env_name}'")
        else:
            logger.error(f"Failed to switch to environment '{env_name}'")
        
        return success
    
    def get_current_environment(self) -> Optional[str]:
        """
        Get the name of the current active environment.
        
        Returns:
            Current environment name or None
        """
        if self._current_environment:
            return self._current_environment
        
        # Try to load from storage
        current = self.env_storage.get_current_environment()
        if current:
            self._current_environment = current
        
        return self._current_environment
    
    def get_current_environment_obj(self) -> Optional[Environment]:
        """
        Get the current active environment object.
        
        Returns:
            Current Environment object or None
        """
        current_name = self.get_current_environment()
        if current_name:
            return self.env_storage.load_environment(current_name)
        return None
    
    def get_environment_obj(self, name: str) -> Optional[Environment]:
        """
        Get an environment object by name.
        
        Args:
            name: Environment name
            
        Returns:
            Environment object or None if not found
        """
        if not name or not name.strip():
            return None
        return self.env_storage.load_environment(name.strip())
    
    def list_environments(self) -> List[str]:
        """
        List all environment names.
        
        Returns:
            List of environment names
        """
        return self.env_storage.list_environments()
    
    def environment_exists(self, name: str) -> bool:
        """
        Check if an environment exists.
        
        Args:
            name: Environment name
            
        Returns:
            True if environment exists
        """
        if not name:
            return False
        
        return self.env_storage.load_environment(name.strip()) is not None
    
    def get_environment_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an environment.
        
        Args:
            name: Environment name
            
        Returns:
            Dictionary with environment information
        """
        environment = self.env_storage.load_environment(name)
        if not environment:
            return None
        
        return {
            'name': environment.name,
            'description': environment.description,
            'variable_count': len(environment.variables),
            'created_at': environment.created_at,
            'last_modified': environment.last_modified,
            'formatted_created': datetime.fromtimestamp(environment.created_at).strftime("%Y-%m-%d %H:%M:%S"),
            'formatted_modified': datetime.fromtimestamp(environment.last_modified).strftime("%Y-%m-%d %H:%M:%S"),
            'is_current': self.get_current_environment() == name
        }
    
    def get_all_environments_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all environments.
        
        Returns:
            List of environment information dictionaries
        """
        env_names = self.list_environments()
        environments_info = []
        
        for name in env_names:
            info = self.get_environment_info(name)
            if info:
                environments_info.append(info)
        
        # Sort by name
        environments_info.sort(key=lambda x: x['name'])
        
        return environments_info
    
    def update_environment_description(self, name: str, description: str) -> bool:
        """
        Update environment description.
        
        Args:
            name: Environment name
            description: New description
            
        Returns:
            True if description was updated successfully
        """
        environment = self.env_storage.load_environment(name)
        if not environment:
            return False
        
        environment.description = description
        environment.last_modified = time.time()
        
        return self.env_storage.save_environment(environment)
    
    def copy_environment(self, source_name: str, target_name: str,
                        description: str = "") -> bool:
        """
        Copy an environment with all its variables.
        
        Args:
            source_name: Source environment name
            target_name: Target environment name
            description: Description for new environment
            
        Returns:
            True if environment was copied successfully
        """
        # Load source environment
        source_env = self.env_storage.load_environment(source_name)
        if not source_env:
            raise ValueError(f"Source environment '{source_name}' not found")
        
        # Check if target already exists
        if self.environment_exists(target_name):
            raise ValueError(f"Target environment '{target_name}' already exists")
        
        # Create new environment with copied variables
        return self.create_environment(
            target_name,
            description or f"Copy of {source_name}",
            source_env.variables.copy()
        )
    
    def merge_environments(self, target_name: str, source_name: str,
                          overwrite: bool = False) -> bool:
        """
        Merge variables from source environment into target environment.
        
        Args:
            target_name: Target environment name
            source_name: Source environment name
            overwrite: Whether to overwrite existing variables
            
        Returns:
            True if environments were merged successfully
        """
        # Load environments
        target_env = self.env_storage.load_environment(target_name)
        source_env = self.env_storage.load_environment(source_name)
        
        if not target_env:
            raise ValueError(f"Target environment '{target_name}' not found")
        
        if not source_env:
            raise ValueError(f"Source environment '{source_name}' not found")
        
        # Merge variables
        merged_count = 0
        for key, value in source_env.variables.items():
            if key not in target_env.variables or overwrite:
                target_env.set_variable(key, value)
                merged_count += 1
        
        if merged_count > 0:
            success = self.env_storage.save_environment(target_env)
            if success:
                logger.info(f"Merged {merged_count} variables from '{source_name}' to '{target_name}'")
            return success
        
        return True  # No variables to merge, but operation is successful
    
    def export_environment(self, name: str, include_metadata: bool = True) -> Dict[str, Any]:
        """
        Export environment data.
        
        Args:
            name: Environment name
            include_metadata: Whether to include metadata
            
        Returns:
            Dictionary with environment data
        """
        environment = self.env_storage.load_environment(name)
        if not environment:
            raise ValueError(f"Environment '{name}' not found")
        
        export_data = {
            'name': environment.name,
            'description': environment.description,
            'variables': environment.variables.copy()
        }
        
        if include_metadata:
            export_data['metadata'] = {
                'created_at': environment.created_at,
                'last_modified': environment.last_modified,
                'formatted_created': datetime.fromtimestamp(environment.created_at).strftime("%Y-%m-%d %H:%M:%S"),
                'formatted_modified': datetime.fromtimestamp(environment.last_modified).strftime("%Y-%m-%d %H:%M:%S")
            }
        
        return export_data
    
    def import_environment(self, data: Dict[str, Any], overwrite: bool = False) -> bool:
        """
        Import environment data.
        
        Args:
            data: Environment data dictionary
            overwrite: Whether to overwrite existing environment
            
        Returns:
            True if environment was imported successfully
        """
        name = data.get('name')
        if not name:
            raise ValueError("Environment name is required for import")
        
        # Check if environment exists
        if self.environment_exists(name):
            if not overwrite:
                raise ValueError(f"Environment '{name}' already exists")
            # Delete existing environment first
            self.delete_environment(name)
        
        # Create environment
        return self.create_environment(
            name,
            data.get('description', ''),
            data.get('variables', {})
        )
    
    def _load_current_environment(self) -> None:
        """Load current environment from storage."""
        current = self.env_storage.get_current_environment()
        if current:
            self._current_environment = current
    
    def _is_valid_environment_name(self, name: str) -> bool:
        """Validate environment name."""
        if not name or len(name.strip()) == 0:
            return False
        
        # Check for invalid characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            if char in name:
                return False
        
        # Check length
        if len(name) > 50:
            return False
        
        return True
    
    def _is_valid_variable_name(self, name: str) -> bool:
        """Validate variable name."""
        if not name or len(name.strip()) == 0:
            return False
        
        # Variable names should be alphanumeric with underscores
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            return False
        
        # Check length
        if len(name) > 100:
            return False
        
        return True
    
    def get_environment_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about all environments.
        
        Returns:
            Dictionary with environment statistics
        """
        environments = self.get_all_environments_info()
        
        if not environments:
            return {
                'total_environments': 0,
                'total_variables': 0,
                'current_environment': None,
                'most_variables': None,
                'recently_modified': None
            }
        
        total_variables = sum(env['variable_count'] for env in environments)
        
        # Find environment with most variables
        most_vars_env = max(environments, key=lambda x: x['variable_count'])
        
        # Find most recently modified
        recent_env = max(environments, key=lambda x: x['last_modified'])
        
        return {
            'total_environments': len(environments),
            'total_variables': total_variables,
            'average_variables': total_variables / len(environments),
            'current_environment': self.get_current_environment(),
            'most_variables': {
                'name': most_vars_env['name'],
                'count': most_vars_env['variable_count']
            },
            'recently_modified': {
                'name': recent_env['name'],
                'modified': recent_env['formatted_modified']
            }
        }