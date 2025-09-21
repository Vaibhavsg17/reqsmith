"""
Hybrid storage system combining memory cache and disk persistence.
"""
import time
import hashlib
from typing import Any, Optional, List, Dict
import logging
from .memory_cache import MemoryCache
from .disk_manager import DiskManager


logger = logging.getLogger(__name__)


class HybridStorage:
    """
    Hybrid storage system that combines in-memory caching with disk persistence.
    
    Features:
    - Fast memory access for frequently used data
    - Persistent disk storage for durability
    - LRU eviction from memory to disk when memory is full
    - Configurable cache sizes and TTL
    """
    
    def __init__(self, user_id: str, cache_size_mb: int = 50):
        """
        Initialize hybrid storage system.
        
        Args:
            user_id: Unique user identifier for storage isolation
            cache_size_mb: Maximum memory cache size in MB
        """
        self.user_id = user_id
        self.cache_size_mb = cache_size_mb
        
        # Initialize storage components
        storage_path = f"~/.apitester/{user_id}"
        self.memory_cache = MemoryCache(max_size_mb=cache_size_mb)
        self.disk_manager = DiskManager(storage_path)
        
        # Track memory-only vs persistent data
        self.memory_only_keys = set()
        self.fallback_mode = False
        
        # Initialize storage
        self._initialize_storage()
    
    def get(self, key: str, category: str = "general") -> Optional[Any]:
        """
        Get value from hybrid storage (memory first, then disk).
        
        Args:
            key: Storage key
            category: Storage category
            
        Returns:
            Stored value or None if not found
        """
        cache_key = self._make_cache_key(key, category)
        
        # Try memory cache first
        value = self.memory_cache.get(cache_key)
        if value is not None:
            return value
        
        # Try disk storage if not in memory-only mode
        if not self.fallback_mode and cache_key not in self.memory_only_keys:
            value = self.disk_manager.load(key, category)
            if value is not None:
                # Load into memory cache for faster future access
                self.memory_cache.set(cache_key, value)
                return value
        
        return None
    
    def set(self, key: str, value: Any, category: str = "general", 
            ttl: Optional[int] = None, memory_only: bool = False) -> bool:
        """
        Set value in hybrid storage.
        
        Args:
            key: Storage key
            value: Value to store
            category: Storage category
            ttl: Time to live in seconds (memory cache only)
            memory_only: If True, store only in memory
            
        Returns:
            True if successfully stored
        """
        cache_key = self._make_cache_key(key, category)
        
        # Always try to store in memory cache
        memory_success = self.memory_cache.set(cache_key, value, ttl)
        
        # Store to disk unless memory_only or fallback mode
        disk_success = True
        if not memory_only and not self.fallback_mode:
            disk_success = self.disk_manager.save(key, value, category)
            if not disk_success:
                logger.warning(f"Failed to save {key} to disk, keeping in memory only")
                self.memory_only_keys.add(cache_key)
        else:
            self.memory_only_keys.add(cache_key)
        
        return memory_success or disk_success
    
    def delete(self, key: str, category: str = "general") -> bool:
        """
        Delete key from hybrid storage.
        
        Args:
            key: Storage key
            category: Storage category
            
        Returns:
            True if key was deleted from at least one storage
        """
        cache_key = self._make_cache_key(key, category)
        
        # Delete from memory
        memory_deleted = self.memory_cache.delete(cache_key)
        
        # Delete from disk
        disk_deleted = False
        if not self.fallback_mode:
            disk_deleted = self.disk_manager.delete(key, category)
        
        # Remove from memory-only tracking
        self.memory_only_keys.discard(cache_key)
        
        return memory_deleted or disk_deleted
    
    def list_keys(self, category: str = "general", pattern: str = "*") -> List[str]:
        """
        List keys from hybrid storage.
        
        Args:
            category: Storage category
            pattern: Pattern to match
            
        Returns:
            List of matching keys
        """
        keys = set()
        
        # Get keys from memory cache
        cache_pattern = self._make_cache_key(pattern, category)
        memory_keys = self.memory_cache.list_keys(cache_pattern)
        for cache_key in memory_keys:
            # Extract original key from cache key
            if cache_key.startswith(f"{category}:"):
                original_key = cache_key[len(f"{category}:"):]
                keys.add(original_key)
        
        # Get keys from disk storage
        if not self.fallback_mode:
            disk_keys = self.disk_manager.list_files(category, pattern)
            keys.update(disk_keys)
        
        return sorted(list(keys))
    
    def clear_cache(self, category: Optional[str] = None) -> bool:
        """
        Clear cache (memory and optionally disk).
        
        Args:
            category: Specific category to clear, or None for all
            
        Returns:
            True if cache was cleared
        """
        if category:
            # Clear specific category
            keys_to_remove = []
            for cache_key in self.memory_cache.list_keys("*"):
                if cache_key.startswith(f"{category}:"):
                    keys_to_remove.append(cache_key)
            
            for cache_key in keys_to_remove:
                self.memory_cache.delete(cache_key)
                self.memory_only_keys.discard(cache_key)
        else:
            # Clear all memory cache
            self.memory_cache.clear()
            self.memory_only_keys.clear()
        
        return True
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        memory_stats = self.memory_cache.get_stats()
        
        stats = {
            'memory_cache': memory_stats,
            'memory_only_keys': len(self.memory_only_keys),
            'fallback_mode': self.fallback_mode,
            'user_id': self.user_id
        }
        
        # Add disk storage stats if available
        if not self.fallback_mode:
            try:
                disk_stats = self.disk_manager.get_storage_info()
                stats['disk_storage'] = disk_stats
            except Exception as e:
                stats['disk_storage'] = {'error': str(e)}
        
        return stats
    
    def sync_to_disk(self, force: bool = False) -> bool:
        """
        Sync memory-only data to disk.
        
        Args:
            force: Force sync even if disk was previously unavailable
            
        Returns:
            True if sync completed successfully
        """
        if self.fallback_mode and not force:
            return False
        
        success_count = 0
        total_count = 0
        
        # Try to sync memory-only keys to disk
        keys_to_sync = list(self.memory_only_keys)
        for cache_key in keys_to_sync:
            total_count += 1
            
            # Parse cache key to get category and key
            if ":" in cache_key:
                category, key = cache_key.split(":", 1)
                value = self.memory_cache.get(cache_key)
                
                if value is not None:
                    if self.disk_manager.save(key, value, category):
                        self.memory_only_keys.discard(cache_key)
                        success_count += 1
        
        # Update fallback mode status
        if force and success_count > 0:
            self.fallback_mode = False
        
        return success_count == total_count
    
    def _initialize_storage(self) -> None:
        """Initialize storage components and check availability."""
        try:
            # Test disk storage availability
            test_key = f"_test_{int(time.time())}"
            if self.disk_manager.save(test_key, "test", "config"):
                self.disk_manager.delete(test_key, "config")
                self.fallback_mode = False
                logger.info("Hybrid storage initialized with disk persistence")
            else:
                self.fallback_mode = True
                logger.warning("Disk storage unavailable, running in memory-only mode")
        except Exception as e:
            self.fallback_mode = True
            logger.warning(f"Failed to initialize disk storage: {e}")
    
    def _make_cache_key(self, key: str, category: str) -> str:
        """
        Create cache key with category prefix.
        
        Args:
            key: Original key
            category: Storage category
            
        Returns:
            Cache key with category prefix
        """
        return f"{category}:{key}"
    
    def get_user_storage_path(self) -> str:
        """
        Get the user storage path.
        
        Returns:
            Path to user storage directory
        """
        return str(self.disk_manager.user_storage_path)
    
    def is_disk_available(self) -> bool:
        """
        Check if disk storage is available.
        
        Returns:
            True if disk storage is working
        """
        return not self.fallback_mode