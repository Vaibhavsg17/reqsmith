"""
Specialized storage operations for different data types.
"""
import json
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
from .hybrid_storage import HybridStorage
from .models import RequestTemplate, RequestRecord, Environment, CacheEntry


logger = logging.getLogger(__name__)


class TemplateStorage:
    """Storage operations for request templates."""
    
    def __init__(self, storage: HybridStorage):
        self.storage = storage
        self.category = "templates"
    
    def save_template(self, template: RequestTemplate) -> bool:
        """
        Save request template to storage.
        
        Args:
            template: RequestTemplate to save
            
        Returns:
            True if successfully saved
        """
        if not template.validate():
            logger.error(f"Invalid template data for {template.name}")
            return False
        
        try:
            template_data = template.to_dict()
            return self.storage.set(template.name, template_data, self.category)
        except Exception as e:
            logger.error(f"Failed to save template {template.name}: {e}")
            return False
    
    def load_template(self, name: str) -> Optional[RequestTemplate]:
        """
        Load request template from storage.
        
        Args:
            name: Template name
            
        Returns:
            RequestTemplate or None if not found
        """
        try:
            template_data = self.storage.get(name, self.category)
            if template_data:
                return RequestTemplate.from_dict(template_data)
            return None
        except Exception as e:
            logger.error(f"Failed to load template {name}: {e}")
            return None
    
    def list_templates(self) -> List[str]:
        """
        List all template names.
        
        Returns:
            List of template names
        """
        try:
            return self.storage.list_keys(self.category)
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []
    
    def delete_template(self, name: str) -> bool:
        """
        Delete template from storage.
        
        Args:
            name: Template name
            
        Returns:
            True if successfully deleted
        """
        try:
            return self.storage.delete(name, self.category)
        except Exception as e:
            logger.error(f"Failed to delete template {name}: {e}")
            return False
    
    def get_template_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about all templates.
        
        Returns:
            Dictionary with template metadata
        """
        templates = []
        for name in self.list_templates():
            template = self.load_template(name)
            if template:
                templates.append({
                    'name': name,
                    'method': template.method,
                    'url': template.url,
                    'created_at': template.created_at,
                    'last_used': template.last_used,
                    'usage_count': template.usage_count,
                    'description': template.description,
                    'tags': template.tags
                })
        
        return {
            'total_count': len(templates),
            'templates': templates
        }


class EnvironmentStorage:
    """Storage operations for environment variables."""
    
    def __init__(self, storage: HybridStorage):
        self.storage = storage
        self.category = "environments"
        self.current_env_key = "_current_environment"
    
    def save_environment(self, environment: Environment) -> bool:
        """
        Save environment to storage.
        
        Args:
            environment: Environment to save
            
        Returns:
            True if successfully saved
        """
        if not environment.validate():
            logger.error(f"Invalid environment data for {environment.name}")
            return False
        
        try:
            env_data = environment.to_dict()
            return self.storage.set(environment.name, env_data, self.category)
        except Exception as e:
            logger.error(f"Failed to save environment {environment.name}: {e}")
            return False
    
    def load_environment(self, name: str) -> Optional[Environment]:
        """
        Load environment from storage.
        
        Args:
            name: Environment name
            
        Returns:
            Environment or None if not found
        """
        try:
            env_data = self.storage.get(name, self.category)
            if env_data:
                return Environment.from_dict(env_data)
            return None
        except Exception as e:
            logger.error(f"Failed to load environment {name}: {e}")
            return None
    
    def list_environments(self) -> List[str]:
        """
        List all environment names.
        
        Returns:
            List of environment names
        """
        try:
            envs = self.storage.list_keys(self.category)
            # Filter out internal keys
            return [env for env in envs if not env.startswith('_')]
        except Exception as e:
            logger.error(f"Failed to list environments: {e}")
            return []
    
    def delete_environment(self, name: str) -> bool:
        """
        Delete environment from storage.
        
        Args:
            name: Environment name
            
        Returns:
            True if successfully deleted
        """
        try:
            # Don't allow deletion of current environment without switching
            current_env = self.get_current_environment()
            if current_env == name:
                logger.warning(f"Cannot delete current environment {name}")
                return False
            
            return self.storage.delete(name, self.category)
        except Exception as e:
            logger.error(f"Failed to delete environment {name}: {e}")
            return False
    
    def set_current_environment(self, name: str) -> bool:
        """
        Set current active environment.
        
        Args:
            name: Environment name
            
        Returns:
            True if successfully set
        """
        try:
            # Verify environment exists
            if name and not self.load_environment(name):
                logger.error(f"Environment {name} does not exist")
                return False
            
            return self.storage.set(self.current_env_key, name, self.category, memory_only=True)
        except Exception as e:
            logger.error(f"Failed to set current environment to {name}: {e}")
            return False
    
    def get_current_environment(self) -> Optional[str]:
        """
        Get current active environment name.
        
        Returns:
            Current environment name or None
        """
        try:
            return self.storage.get(self.current_env_key, self.category)
        except Exception as e:
            logger.error(f"Failed to get current environment: {e}")
            return None
    
    def get_current_environment_obj(self) -> Optional[Environment]:
        """
        Get current active environment object.
        
        Returns:
            Current Environment object or None
        """
        current_name = self.get_current_environment()
        if current_name:
            return self.load_environment(current_name)
        return None


class HistoryStorage:
    """Storage operations for request history using JSONL format."""
    
    def __init__(self, storage: HybridStorage, max_entries: int = 1000):
        self.storage = storage
        self.category = "history"
        self.max_entries = max_entries
        self.history_key = "requests"
        self.metadata_key = "metadata"
    
    def add_request(self, record: RequestRecord) -> bool:
        """
        Add request record to history.
        
        Args:
            record: RequestRecord to add
            
        Returns:
            True if successfully added
        """
        if not record.validate():
            logger.error("Invalid request record data")
            return False
        
        try:
            # Load existing history
            history = self._load_history_list()
            
            # Add new record
            history.append(record.to_dict())
            
            # Maintain size limit (FIFO)
            if len(history) > self.max_entries:
                history = history[-self.max_entries:]
            
            # Save updated history
            return self._save_history_list(history)
            
        except Exception as e:
            logger.error(f"Failed to add request to history: {e}")
            return False
    
    def get_history(self, limit: Optional[int] = None) -> List[RequestRecord]:
        """
        Get request history.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of RequestRecord objects
        """
        try:
            history_data = self._load_history_list()
            
            # Apply limit
            if limit:
                history_data = history_data[-limit:]
            
            # Convert to RequestRecord objects
            records = []
            for record_data in history_data:
                try:
                    record = RequestRecord.from_dict(record_data)
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse history record: {e}")
                    continue
            
            return records
            
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []
    
    def get_last_request(self) -> Optional[RequestRecord]:
        """
        Get the most recent request.
        
        Returns:
            Last RequestRecord or None
        """
        history = self.get_history(limit=1)
        return history[0] if history else None
    
    def clear_history(self) -> bool:
        """
        Clear all request history.
        
        Returns:
            True if successfully cleared
        """
        try:
            return self._save_history_list([])
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            return False
    
    def get_history_stats(self) -> Dict[str, Any]:
        """
        Get history statistics.
        
        Returns:
            Dictionary with history statistics
        """
        try:
            history = self.get_history()
            
            if not history:
                return {
                    'total_requests': 0,
                    'date_range': None,
                    'methods': {},
                    'status_codes': {}
                }
            
            # Calculate statistics
            methods = {}
            status_codes = {}
            successful_requests = 0
            failed_requests = 0
            
            for record in history:
                # Count methods
                method = record.method.upper()
                methods[method] = methods.get(method, 0) + 1
                
                # Count status codes
                status = record.response_status
                status_codes[status] = status_codes.get(status, 0) + 1
                
                # Count success/failure
                if 200 <= status < 400:
                    successful_requests += 1
                else:
                    failed_requests += 1
            
            return {
                'total_requests': len(history),
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'method_distribution': methods,
                'status_distribution': status_codes,
                'date_range': {
                    'oldest': history[0].get_formatted_timestamp(),
                    'newest': history[-1].get_formatted_timestamp()
                },
                # Keep old keys for backward compatibility
                'methods': methods,
                'status_codes': status_codes
            }
            
        except Exception as e:
            logger.error(f"Failed to get history stats: {e}")
            return {'error': str(e)}
    
    def _load_history_list(self) -> List[Dict[str, Any]]:
        """Load history as list of dictionaries."""
        history_data = self.storage.get(self.history_key, self.category)
        return history_data if history_data else []
    
    def _save_history_list(self, history: List[Dict[str, Any]]) -> bool:
        """Save history list to storage."""
        # Update metadata
        metadata = {
            'total_entries': len(history),
            'last_updated': time.time(),
            'max_entries': self.max_entries
        }
        self.storage.set(self.metadata_key, metadata, self.category)
        
        # Save history
        return self.storage.set(self.history_key, history, self.category)


class CacheStorage:
    """Storage operations for response caching with TTL."""
    
    def __init__(self, storage: HybridStorage):
        self.storage = storage
        self.category = "cache"
    
    def cache_response(self, cache_key: str, response_data: Any, ttl: int = 3600) -> bool:
        """
        Cache response data with TTL.
        
        Args:
            cache_key: Unique cache key
            response_data: Response data to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successfully cached
        """
        try:
            cache_entry = CacheEntry(
                key=cache_key,
                data=response_data,
                ttl=ttl,
                size_bytes=len(str(response_data))
            )
            
            if not cache_entry.validate():
                logger.error(f"Invalid cache entry for key {cache_key}")
                return False
            
            return self.storage.set(cache_key, cache_entry.to_dict(), self.category, ttl=ttl)
            
        except Exception as e:
            logger.error(f"Failed to cache response for key {cache_key}: {e}")
            return False
    
    def get_cached_response(self, cache_key: str) -> Optional[Any]:
        """
        Get cached response data.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached response data or None if not found/expired
        """
        try:
            cache_data = self.storage.get(cache_key, self.category)
            if not cache_data:
                return None
            
            cache_entry = CacheEntry.from_dict(cache_data)
            
            # Check if expired
            if cache_entry.is_expired():
                self.storage.delete(cache_key, self.category)
                return None
            
            # Update access statistics
            cache_entry.update_access()
            self.storage.set(cache_key, cache_entry.to_dict(), self.category)
            
            return cache_entry.data
            
        except Exception as e:
            logger.error(f"Failed to get cached response for key {cache_key}: {e}")
            return None
    
    def clear_cache(self) -> bool:
        """
        Clear all cached responses.
        
        Returns:
            True if successfully cleared
        """
        try:
            return self.storage.clear_cache(self.category)
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    def generate_cache_key(self, method: str, url: str, headers: Dict[str, str], 
                          body: str = "") -> str:
        """
        Generate cache key from request parameters.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            
        Returns:
            Generated cache key
        """
        import hashlib
        
        # Create a string representation of the request
        key_parts = [
            method.upper(),
            url,
            json.dumps(sorted(headers.items())),
            body
        ]
        
        key_string = "|".join(key_parts)
        
        # Generate hash
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            cache_keys = self.storage.list_keys(self.category)
            
            total_entries = 0
            total_size = 0
            expired_count = 0
            
            for key in cache_keys:
                cache_data = self.storage.get(key, self.category)
                if cache_data:
                    try:
                        cache_entry = CacheEntry.from_dict(cache_data)
                        total_entries += 1
                        total_size += cache_entry.size_bytes
                        
                        if cache_entry.is_expired():
                            expired_count += 1
                    except Exception:
                        continue
            
            return {
                'total_entries': total_entries,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'expired_entries': expired_count,
                'active_entries': total_entries - expired_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {'error': str(e)}
    
    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            Number of entries removed
        """
        try:
            cache_keys = self.storage.list_keys(self.category)
            removed_count = 0
            
            for key in cache_keys:
                cache_data = self.storage.get(key, self.category)
                if cache_data:
                    try:
                        cache_entry = CacheEntry.from_dict(cache_data)
                        if cache_entry.is_expired():
                            self.storage.delete(key, self.category)
                            removed_count += 1
                    except Exception:
                        continue
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired cache: {e}")
            return 0