"""
Memory cache implementation with LRU eviction and size limits.
"""
import time
from typing import Any, Optional, Dict, List
from collections import OrderedDict
import sys
import pickle


class MemoryCache:
    """In-memory cache with LRU eviction and size limits."""
    
    def __init__(self, max_size_mb: int = 25):
        """
        Initialize memory cache with size limit.
        
        Args:
            max_size_mb: Maximum cache size in megabytes
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.current_size_bytes = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache and move to end (most recently used).
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if key not in self.cache:
            return None
            
        entry = self.cache[key]
        
        # Check TTL expiration
        if entry.get('ttl') and time.time() > entry['expires_at']:
            del self.cache[key]
            self.current_size_bytes -= entry['size']
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (optional)
            
        Returns:
            True if successfully cached
        """
        try:
            # Calculate size of the value
            value_size = self._calculate_size(value)
            
            # Remove existing entry if present
            if key in self.cache:
                old_entry = self.cache[key]
                self.current_size_bytes -= old_entry['size']
                del self.cache[key]
            
            # Check if single item exceeds max size
            if value_size > self.max_size_bytes:
                return False
            
            # Evict items if necessary
            while (self.current_size_bytes + value_size > self.max_size_bytes 
                   and self.cache):
                self.evict_lru()
            
            # Create cache entry
            entry = {
                'value': value,
                'size': value_size,
                'created_at': time.time()
            }
            
            if ttl:
                entry['ttl'] = ttl
                entry['expires_at'] = time.time() + ttl
            
            # Add to cache
            self.cache[key] = entry
            self.current_size_bytes += value_size
            
            return True
            
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted
        """
        if key in self.cache:
            entry = self.cache[key]
            self.current_size_bytes -= entry['size']
            del self.cache[key]
            return True
        return False
    
    def evict_lru(self) -> None:
        """Evict least recently used item."""
        if self.cache:
            key, entry = self.cache.popitem(last=False)
            self.current_size_bytes -= entry['size']
    
    def clear(self) -> bool:
        """
        Clear all cached items.
        
        Returns:
            True if cache was cleared
        """
        self.cache.clear()
        self.current_size_bytes = 0
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'total_items': len(self.cache),
            'size_bytes': self.current_size_bytes,
            'size_mb': round(self.current_size_bytes / (1024 * 1024), 2),
            'max_size_mb': self.max_size_bytes / (1024 * 1024),
            'utilization_percent': round(
                (self.current_size_bytes / self.max_size_bytes) * 100, 2
            )
        }
    
    def list_keys(self, pattern: str = "*") -> List[str]:
        """
        List cache keys matching pattern.
        
        Args:
            pattern: Pattern to match (basic wildcard support)
            
        Returns:
            List of matching keys
        """
        if pattern == "*":
            return list(self.cache.keys())
        
        # Basic pattern matching
        keys = []
        for key in self.cache.keys():
            if pattern in key:
                keys.append(key)
        return keys
    
    def _calculate_size(self, value: Any) -> int:
        """
        Calculate approximate size of value in bytes.
        
        Args:
            value: Value to measure
            
        Returns:
            Size in bytes
        """
        try:
            return len(pickle.dumps(value))
        except Exception:
            # Fallback to sys.getsizeof for non-picklable objects
            return sys.getsizeof(value)