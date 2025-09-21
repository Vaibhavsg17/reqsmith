"""
Environment variable utilities for listing, filtering, and bulk operations.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
import logging

from ..storage import Environment
from .env_manager import EnvironmentManager


logger = logging.getLogger(__name__)


class EnvironmentVariableLister:
    """Utility for listing and filtering environment variables."""
    
    def __init__(self, env_manager: EnvironmentManager):
        """
        Initialize environment variable lister.
        
        Args:
            env_manager: EnvironmentManager instance
        """
        self.env_manager = env_manager
    
    def list_variables_with_details(self, env_name: str,
                                   include_metadata: bool = True) -> List[Dict[str, Any]]:
        """
        List variables with detailed information.
        
        Args:
            env_name: Environment name
            include_metadata: Whether to include metadata
            
        Returns:
            List of variable detail dictionaries
        """
        variables = self.env_manager.list_variables(env_name)
        if not variables:
            return []
        
        variable_details = []
        
        for key, value in variables.items():
            detail = {
                'name': key,
                'value': value,
                'length': len(value),
                'is_empty': len(value.strip()) == 0,
                'contains_variables': self._contains_variable_references(value),
                'type': self._detect_value_type(value)
            }
            
            if include_metadata:
                detail['metadata'] = {
                    'environment': env_name,
                    'is_sensitive': self._is_sensitive_variable(key, value),
                    'usage_hints': self._get_usage_hints(key, value)
                }
            
            variable_details.append(detail)
        
        return variable_details
    
    def filter_variables(self, env_name: str, 
                        name_pattern: Optional[str] = None,
                        value_pattern: Optional[str] = None,
                        variable_type: Optional[str] = None,
                        include_empty: bool = True) -> Dict[str, str]:
        """
        Filter variables based on criteria.
        
        Args:
            env_name: Environment name
            name_pattern: Regex pattern for variable names
            value_pattern: Regex pattern for variable values
            variable_type: Variable type filter (url, json, number, etc.)
            include_empty: Whether to include empty variables
            
        Returns:
            Dictionary of filtered variables
        """
        all_variables = self.env_manager.list_variables(env_name)
        filtered = {}
        
        for key, value in all_variables.items():
            # Filter by empty values
            if not include_empty and len(value.strip()) == 0:
                continue
            
            # Filter by name pattern
            if name_pattern:
                try:
                    if not re.search(name_pattern, key, re.IGNORECASE):
                        continue
                except re.error:
                    logger.warning(f"Invalid name pattern: {name_pattern}")
                    continue
            
            # Filter by value pattern
            if value_pattern:
                try:
                    if not re.search(value_pattern, value, re.IGNORECASE):
                        continue
                except re.error:
                    logger.warning(f"Invalid value pattern: {value_pattern}")
                    continue
            
            # Filter by variable type
            if variable_type:
                detected_type = self._detect_value_type(value)
                if detected_type != variable_type:
                    continue
            
            filtered[key] = value
        
        return filtered
    
    def search_variables(self, query: str, 
                        environments: Optional[List[str]] = None) -> Dict[str, Dict[str, str]]:
        """
        Search for variables across environments.
        
        Args:
            query: Search query (searches names and values)
            environments: List of environments to search (all if None)
            
        Returns:
            Dictionary mapping environment names to matching variables
        """
        if not query or not query.strip():
            return {}
        
        query = query.lower().strip()
        
        if environments is None:
            environments = self.env_manager.list_environments()
        
        results = {}
        
        for env_name in environments:
            variables = self.env_manager.list_variables(env_name)
            matching_vars = {}
            
            for key, value in variables.items():
                if (query in key.lower() or 
                    query in value.lower()):
                    matching_vars[key] = value
            
            if matching_vars:
                results[env_name] = matching_vars
        
        return results
    
    def get_variable_usage_across_environments(self, var_name: str) -> Dict[str, Optional[str]]:
        """
        Get usage of a variable across all environments.
        
        Args:
            var_name: Variable name to check
            
        Returns:
            Dictionary mapping environment names to variable values (None if not defined)
        """
        environments = self.env_manager.list_environments()
        usage = {}
        
        for env_name in environments:
            value = self.env_manager.get_variable(env_name, var_name)
            usage[env_name] = value
        
        return usage
    
    def find_duplicate_variables(self, environments: Optional[List[str]] = None) -> Dict[str, Dict[str, str]]:
        """
        Find variables with the same name but different values across environments.
        
        Args:
            environments: List of environments to check (all if None)
            
        Returns:
            Dictionary mapping variable names to environment-value mappings
        """
        if environments is None:
            environments = self.env_manager.list_environments()
        
        # Collect all variable names
        all_var_names = set()
        for env_name in environments:
            variables = self.env_manager.list_variables(env_name)
            all_var_names.update(variables.keys())
        
        duplicates = {}
        
        for var_name in all_var_names:
            values_by_env = {}
            unique_values = set()
            
            for env_name in environments:
                value = self.env_manager.get_variable(env_name, var_name)
                if value is not None:
                    values_by_env[env_name] = value
                    unique_values.add(value)
            
            # If variable exists in multiple environments with different values
            if len(values_by_env) > 1 and len(unique_values) > 1:
                duplicates[var_name] = values_by_env
        
        return duplicates
    
    def _contains_variable_references(self, value: str) -> bool:
        """Check if value contains variable references."""
        patterns = [
            r'\$\{[^}]+\}',      # ${VAR}
            r'\{\{[^}]+\}\}',    # {{VAR}}
            r'%[^%]+%',          # %VAR%
            r'\$[A-Z_][A-Z0-9_]*'  # $VAR
        ]
        
        for pattern in patterns:
            if re.search(pattern, value):
                return True
        
        return False
    
    def _detect_value_type(self, value: str) -> str:
        """Detect the type of a variable value."""
        if not value:
            return 'empty'
        
        value = value.strip()
        
        # URL detection
        if re.match(r'^https?://', value, re.IGNORECASE):
            return 'url'
        
        # JSON detection
        if (value.startswith('{') and value.endswith('}')) or \
           (value.startswith('[') and value.endswith(']')):
            try:
                json.loads(value)
                return 'json'
            except json.JSONDecodeError:
                pass
        
        # Number detection
        try:
            float(value)
            return 'number'
        except ValueError:
            pass
        
        # Boolean detection
        if value.lower() in ['true', 'false', 'yes', 'no', '1', '0']:
            return 'boolean'
        
        # Email detection
        if re.match(r'^[^@]+@[^@]+\.[^@]+$', value):
            return 'email'
        
        # Path detection
        if '/' in value or '\\' in value:
            return 'path'
        
        return 'string'
    
    def _is_sensitive_variable(self, name: str, value: str) -> bool:
        """Check if variable appears to contain sensitive information."""
        sensitive_keywords = [
            'password', 'passwd', 'pwd', 'secret', 'key', 'token', 
            'auth', 'credential', 'private', 'secure', 'api_key',
            'access_token', 'refresh_token', 'client_secret'
        ]
        
        name_lower = name.lower()
        
        for keyword in sensitive_keywords:
            if keyword in name_lower:
                return True
        
        # Check for patterns that look like tokens/keys
        if len(value) > 20 and re.match(r'^[A-Za-z0-9+/=_-]+$', value):
            return True
        
        return False
    
    def _get_usage_hints(self, name: str, value: str) -> List[str]:
        """Get usage hints for a variable."""
        hints = []
        
        # Type-based hints
        value_type = self._detect_value_type(value)
        if value_type == 'url':
            hints.append("Use in request URLs or endpoints")
        elif value_type == 'json':
            hints.append("Use as request body or configuration")
        elif value_type == 'number':
            hints.append("Use for timeouts, limits, or numeric parameters")
        
        # Name-based hints
        name_lower = name.lower()
        if 'host' in name_lower or 'server' in name_lower:
            hints.append("Use as base URL or hostname")
        elif 'port' in name_lower:
            hints.append("Use for server port configuration")
        elif 'timeout' in name_lower:
            hints.append("Use for request timeout settings")
        elif 'version' in name_lower:
            hints.append("Use for API version headers")
        
        return hints


class EnvironmentBulkOperations:
    """Utility for bulk operations on environment variables."""
    
    def __init__(self, env_manager: EnvironmentManager):
        """
        Initialize bulk operations utility.
        
        Args:
            env_manager: EnvironmentManager instance
        """
        self.env_manager = env_manager
    
    def bulk_set_variables(self, env_name: str, 
                          variables: Dict[str, str],
                          overwrite: bool = True) -> Tuple[int, int, List[str]]:
        """
        Set multiple variables in an environment.
        
        Args:
            env_name: Environment name
            variables: Dictionary of variables to set
            overwrite: Whether to overwrite existing variables
            
        Returns:
            Tuple of (set_count, skipped_count, error_messages)
        """
        if not self.env_manager.environment_exists(env_name):
            raise ValueError(f"Environment '{env_name}' not found")
        
        set_count = 0
        skipped_count = 0
        errors = []
        
        existing_vars = self.env_manager.list_variables(env_name)
        
        for key, value in variables.items():
            try:
                # Check if variable exists
                if key in existing_vars and not overwrite:
                    skipped_count += 1
                    continue
                
                # Set variable
                success = self.env_manager.set_variable(env_name, key, value)
                if success:
                    set_count += 1
                else:
                    errors.append(f"Failed to set variable: {key}")
                    
            except Exception as e:
                errors.append(f"Error setting variable {key}: {e}")
        
        return set_count, skipped_count, errors
    
    def bulk_delete_variables(self, env_name: str, 
                             variable_names: List[str]) -> Tuple[int, List[str]]:
        """
        Delete multiple variables from an environment.
        
        Args:
            env_name: Environment name
            variable_names: List of variable names to delete
            
        Returns:
            Tuple of (deleted_count, error_messages)
        """
        if not self.env_manager.environment_exists(env_name):
            raise ValueError(f"Environment '{env_name}' not found")
        
        deleted_count = 0
        errors = []
        
        for var_name in variable_names:
            try:
                success = self.env_manager.delete_variable(env_name, var_name)
                if success:
                    deleted_count += 1
                else:
                    errors.append(f"Variable not found: {var_name}")
            except Exception as e:
                errors.append(f"Error deleting variable {var_name}: {e}")
        
        return deleted_count, errors
    
    def bulk_rename_variables(self, env_name: str, 
                             rename_map: Dict[str, str]) -> Tuple[int, List[str]]:
        """
        Rename multiple variables in an environment.
        
        Args:
            env_name: Environment name
            rename_map: Dictionary mapping old names to new names
            
        Returns:
            Tuple of (renamed_count, error_messages)
        """
        if not self.env_manager.environment_exists(env_name):
            raise ValueError(f"Environment '{env_name}' not found")
        
        renamed_count = 0
        errors = []
        
        existing_vars = self.env_manager.list_variables(env_name)
        
        for old_name, new_name in rename_map.items():
            try:
                # Check if old variable exists
                if old_name not in existing_vars:
                    errors.append(f"Variable not found: {old_name}")
                    continue
                
                # Check if new name already exists
                if new_name in existing_vars:
                    errors.append(f"Target variable already exists: {new_name}")
                    continue
                
                # Get old value
                old_value = existing_vars[old_name]
                
                # Set new variable
                set_success = self.env_manager.set_variable(env_name, new_name, old_value)
                if not set_success:
                    errors.append(f"Failed to create new variable: {new_name}")
                    continue
                
                # Delete old variable
                delete_success = self.env_manager.delete_variable(env_name, old_name)
                if not delete_success:
                    errors.append(f"Failed to delete old variable: {old_name}")
                    # Try to clean up the new variable
                    self.env_manager.delete_variable(env_name, new_name)
                    continue
                
                renamed_count += 1
                
            except Exception as e:
                errors.append(f"Error renaming variable {old_name}: {e}")
        
        return renamed_count, errors
    
    def sync_variables_between_environments(self, source_env: str, target_env: str,
                                          variable_names: Optional[List[str]] = None,
                                          overwrite: bool = False) -> Tuple[int, int, List[str]]:
        """
        Sync variables between environments.
        
        Args:
            source_env: Source environment name
            target_env: Target environment name
            variable_names: List of variables to sync (all if None)
            overwrite: Whether to overwrite existing variables in target
            
        Returns:
            Tuple of (synced_count, skipped_count, error_messages)
        """
        if not self.env_manager.environment_exists(source_env):
            raise ValueError(f"Source environment '{source_env}' not found")
        
        if not self.env_manager.environment_exists(target_env):
            raise ValueError(f"Target environment '{target_env}' not found")
        
        source_vars = self.env_manager.list_variables(source_env)
        target_vars = self.env_manager.list_variables(target_env)
        
        # Determine variables to sync
        if variable_names is None:
            vars_to_sync = source_vars
        else:
            vars_to_sync = {k: v for k, v in source_vars.items() if k in variable_names}
        
        synced_count = 0
        skipped_count = 0
        errors = []
        
        for var_name, var_value in vars_to_sync.items():
            try:
                # Check if variable exists in target
                if var_name in target_vars and not overwrite:
                    skipped_count += 1
                    continue
                
                # Set variable in target
                success = self.env_manager.set_variable(target_env, var_name, var_value)
                if success:
                    synced_count += 1
                else:
                    errors.append(f"Failed to sync variable: {var_name}")
                    
            except Exception as e:
                errors.append(f"Error syncing variable {var_name}: {e}")
        
        return synced_count, skipped_count, errors


class EnvironmentImportExport:
    """Utility for importing and exporting environment configurations."""
    
    def __init__(self, env_manager: EnvironmentManager):
        """
        Initialize import/export utility.
        
        Args:
            env_manager: EnvironmentManager instance
        """
        self.env_manager = env_manager
    
    def export_environments_to_file(self, file_path: str,
                                   environment_names: Optional[List[str]] = None,
                                   include_metadata: bool = True,
                                   format_type: str = 'json') -> bool:
        """
        Export environments to file.
        
        Args:
            file_path: Path to export file
            environment_names: List of environments to export (all if None)
            include_metadata: Whether to include metadata
            format_type: Export format (json, yaml)
            
        Returns:
            True if export successful
        """
        if environment_names is None:
            environment_names = self.env_manager.list_environments()
        
        export_data = {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'environments': []
        }
        
        for env_name in environment_names:
            try:
                env_data = self.env_manager.export_environment(env_name, include_metadata)
                export_data['environments'].append(env_data)
            except Exception as e:
                logger.error(f"Failed to export environment {env_name}: {e}")
                continue
        
        try:
            # Create directory if it doesn't exist
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            if format_type.lower() == 'yaml':
                import yaml
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True)
            else:  # JSON
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to export environments to {file_path}: {e}")
            return False
    
    def import_environments_from_file(self, file_path: str,
                                     overwrite: bool = False) -> Tuple[int, int, List[str]]:
        """
        Import environments from file.
        
        Args:
            file_path: Path to import file
            overwrite: Whether to overwrite existing environments
            
        Returns:
            Tuple of (imported_count, skipped_count, error_messages)
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Import file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.lower().endswith(('.yaml', '.yml')):
                    import yaml
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            return self._import_environments_data(data, overwrite)
            
        except Exception as e:
            logger.error(f"Failed to import environments from {file_path}: {e}")
            raise ValueError(f"Import failed: {e}")
    
    def _import_environments_data(self, data: Dict[str, Any], 
                                 overwrite: bool) -> Tuple[int, int, List[str]]:
        """Import environments from parsed data."""
        if 'environments' not in data:
            raise ValueError("Invalid import data: missing 'environments' key")
        
        imported_count = 0
        skipped_count = 0
        errors = []
        
        for env_data in data['environments']:
            try:
                env_name = env_data.get('name')
                if not env_name:
                    errors.append("Environment missing name")
                    continue
                
                # Check if environment exists
                if self.env_manager.environment_exists(env_name):
                    if overwrite:
                        # Delete existing environment
                        try:
                            self.env_manager.delete_environment(env_name)
                        except ValueError:
                            # Can't delete current environment
                            errors.append(f"Cannot overwrite current environment: {env_name}")
                            continue
                    else:
                        skipped_count += 1
                        continue
                
                # Import environment
                success = self.env_manager.import_environment(env_data, overwrite=True)
                if success:
                    imported_count += 1
                else:
                    errors.append(f"Failed to import environment: {env_name}")
                    
            except Exception as e:
                errors.append(f"Error importing environment: {e}")
        
        return imported_count, skipped_count, errors