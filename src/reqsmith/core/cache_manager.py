"""
Response caching system with TTL-based caching and cache management.
"""
import time
import hashlib
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import logging

from ..storage import (
    HybridStorage,
    CacheStorage,
    CacheEntry
)
from ..core.http_client import Response


logger = logging.getLogger(__name__)


class CacheManager:
    """Manages response caching with TTL-based expiration and intelligent cache keys."""
    
    def __init__(self, storage: HybridStorage, default_ttl: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            storage: HybridStorage instance for persistence
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.storage = storage
        self.cache_storage = CacheStorage(storage)
        self.default_ttl = default_ttl
        self.cache_enabled = True
    
    def get_cached_response(self, method: str, url: str, 
                           headers: Optional[Dict[str, str]] = None,
                           body: Optional[str] = None) -> Optional[Response]:
        """
        Get cached response for a request.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            
        Returns:
            Cached Response object or None if not cached or expired
        """
        if not self.cache_enabled:
            return None
        
        try:
            cache_key = self.generate_cache_key(method, url, headers or {}, body or "")
            cached_data = self.cache_storage.get_cached_response(cache_key)
            
            if cached_data:
                # Reconstruct Response object from cached data
                response = self._deserialize_response(cached_data)
                if response:
                    logger.debug(f"Cache hit for {method} {url}")
                    return response
                else:
                    logger.warning(f"Failed to deserialize cached response for {cache_key}")
            
            logger.debug(f"Cache miss for {method} {url}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached response: {e}")
            return None
    
    def cache_response(self, response: Response, ttl: Optional[int] = None) -> bool:
        """
        Cache a response.
        
        Args:
            response: Response object to cache
            ttl: Time to live in seconds (uses default if None)
            
        Returns:
            True if response was cached successfully
        """
        if not self.cache_enabled:
            return False
        
        try:
            cache_key = self.generate_cache_key(
                response.method, 
                response.url, 
                response.request_headers, 
                response.request_body
            )
            
            # Serialize response for caching
            response_data = self._serialize_response(response)
            
            # Use provided TTL or default
            cache_ttl = ttl if ttl is not None else self.default_ttl
            
            success = self.cache_storage.cache_response(cache_key, response_data, cache_ttl)
            
            if success:
                logger.debug(f"Cached response for {response.method} {response.url} (TTL: {cache_ttl}s)")
            else:
                logger.warning(f"Failed to cache response for {response.method} {response.url}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching response: {e}")
            return False
    
    def generate_cache_key(self, method: str, url: str, 
                          headers: Dict[str, str], body: str = "") -> str:
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
        return self.cache_storage.generate_cache_key(method, url, headers, body)
    
    def clear_cache(self) -> bool:
        """
        Clear all cached responses.
        
        Returns:
            True if cache was cleared successfully
        """
        try:
            success = self.cache_storage.clear_cache()
            if success:
                logger.info("Response cache cleared")
            else:
                logger.error("Failed to clear response cache")
            return success
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            Number of entries removed
        """
        try:
            removed_count = self.cache_storage.cleanup_expired()
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} expired cache entries")
            return removed_count
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            stats = self.cache_storage.get_cache_stats()
            stats['cache_enabled'] = self.cache_enabled
            stats['default_ttl'] = self.default_ttl
            return stats
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}
    
    def get_cache_entries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get information about cache entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of cache entry information
        """
        try:
            cache_keys = self.storage.list_keys("cache")
            entries = []
            
            for key in cache_keys:
                cache_data = self.storage.get(key, "cache")
                if cache_data:
                    try:
                        cache_entry = CacheEntry.from_dict(cache_data)
                        entry_info = {
                            'key': cache_entry.key,
                            'created_at': cache_entry.created_at,
                            'ttl': cache_entry.ttl,
                            'size_bytes': cache_entry.size_bytes,
                            'access_count': cache_entry.access_count,
                            'last_accessed': cache_entry.last_accessed,
                            'age_seconds': cache_entry.get_age_seconds(),
                            'is_expired': cache_entry.is_expired(),
                            'formatted_created': datetime.fromtimestamp(cache_entry.created_at).strftime("%Y-%m-%d %H:%M:%S"),
                            'formatted_accessed': datetime.fromtimestamp(cache_entry.last_accessed).strftime("%Y-%m-%d %H:%M:%S")
                        }
                        entries.append(entry_info)
                    except Exception:
                        continue
            
            # Sort by creation time (newest first)
            entries.sort(key=lambda x: x['created_at'], reverse=True)
            
            if limit:
                entries = entries[:limit]
            
            return entries
            
        except Exception as e:
            logger.error(f"Error getting cache entries: {e}")
            return []
    
    def delete_cache_entry(self, cache_key: str) -> bool:
        """
        Delete a specific cache entry.
        
        Args:
            cache_key: Cache key to delete
            
        Returns:
            True if entry was deleted
        """
        try:
            success = self.storage.delete(cache_key, "cache")
            if success:
                logger.debug(f"Deleted cache entry: {cache_key}")
            return success
        except Exception as e:
            logger.error(f"Error deleting cache entry {cache_key}: {e}")
            return False
    
    def set_cache_enabled(self, enabled: bool) -> None:
        """
        Enable or disable caching.
        
        Args:
            enabled: Whether caching should be enabled
        """
        self.cache_enabled = enabled
        logger.info(f"Cache {'enabled' if enabled else 'disabled'}")
    
    def is_cache_enabled(self) -> bool:
        """
        Check if caching is enabled.
        
        Returns:
            True if caching is enabled
        """
        return self.cache_enabled
    
    def set_default_ttl(self, ttl: int) -> None:
        """
        Set default TTL for cache entries.
        
        Args:
            ttl: Default TTL in seconds
        """
        if ttl <= 0:
            raise ValueError("TTL must be positive")
        
        self.default_ttl = ttl
        logger.info(f"Default cache TTL set to {ttl} seconds")
    
    def get_default_ttl(self) -> int:
        """
        Get default TTL for cache entries.
        
        Returns:
            Default TTL in seconds
        """
        return self.default_ttl
    
    def _serialize_response(self, response: Response) -> Dict[str, Any]:
        """Serialize Response object for caching."""
        return {
            'status_code': response.status_code,
            'headers': response.headers,
            'content': response.content.decode('utf-8', errors='replace'),
            'text': response.text,
            'url': response.url,
            'method': response.method,
            'request_headers': response.request_headers,
            'request_body': response.request_body,
            'elapsed_time': response.elapsed_time,
            'size_bytes': response.size_bytes,
            'cached_at': time.time()
        }
    
    def _deserialize_response(self, data: Dict[str, Any]) -> Optional[Response]:
        """Deserialize cached data back to Response object."""
        try:
            # Import Response class
            from ..core.http_client import Response
            
            # Create Response object with cached data
            response = Response(
                status_code=data['status_code'],
                headers=data['headers'],
                content=data['content'].encode('utf-8'),
                text=data['text'],
                url=data['url'],
                method=data['method'],
                request_headers=data['request_headers'],
                request_body=data['request_body'],
                elapsed_time=data['elapsed_time'],
                size_bytes=data['size_bytes']
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error deserializing cached response: {e}")
            return None


class SmartCacheManager(CacheManager):
    """Enhanced cache manager with intelligent caching strategies."""
    
    def __init__(self, storage: HybridStorage, default_ttl: int = 3600):
        """
        Initialize smart cache manager.
        
        Args:
            storage: HybridStorage instance
            default_ttl: Default TTL in seconds
        """
        super().__init__(storage, default_ttl)
        self.cache_strategies = {
            'GET': self._get_strategy,
            'POST': self._post_strategy,
            'PUT': self._put_strategy,
            'PATCH': self._patch_strategy,
            'DELETE': self._delete_strategy
        }
    
    def should_cache_request(self, method: str, url: str, 
                           headers: Optional[Dict[str, str]] = None,
                           status_code: Optional[int] = None) -> bool:
        """
        Determine if a request should be cached based on intelligent rules.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            status_code: Response status code
            
        Returns:
            True if request should be cached
        """
        if not self.cache_enabled:
            return False
        
        # Don't cache error responses
        if status_code and status_code >= 400:
            return False
        
        # Use method-specific strategy
        strategy = self.cache_strategies.get(method.upper(), self._default_strategy)
        return strategy(url, headers, status_code)
    
    def get_smart_ttl(self, method: str, url: str, 
                     headers: Optional[Dict[str, str]] = None,
                     status_code: Optional[int] = None) -> int:
        """
        Get intelligent TTL based on request characteristics.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            status_code: Response status code
            
        Returns:
            Recommended TTL in seconds
        """
        # Base TTL on method
        method_ttls = {
            'GET': self.default_ttl,
            'POST': 300,  # 5 minutes
            'PUT': 600,   # 10 minutes
            'PATCH': 600, # 10 minutes
            'DELETE': 60  # 1 minute
        }
        
        base_ttl = method_ttls.get(method.upper(), self.default_ttl)
        
        # Adjust based on URL patterns
        if '/api/' in url.lower() or 'api.' in url.lower():
            base_ttl = int(base_ttl * 0.5)  # API responses change more frequently
        
        if any(param in url.lower() for param in ['search', 'query', 'filter']):
            base_ttl = int(base_ttl * 0.3)  # Search results change frequently
        
        if any(static in url.lower() for static in ['static', 'assets', 'cdn']):
            base_ttl = int(base_ttl * 5)  # Static resources can be cached longer
        
        # Adjust based on status code
        if status_code:
            if status_code == 200:
                pass  # Use base TTL
            elif status_code in [201, 202]:
                base_ttl = int(base_ttl * 0.5)  # Created/Accepted responses
            elif status_code in [301, 302]:
                base_ttl = int(base_ttl * 2)  # Redirects can be cached longer
            elif status_code == 304:
                base_ttl = int(base_ttl * 3)  # Not Modified
        
        return max(60, base_ttl)  # Minimum 1 minute TTL
    
    def cache_response_smart(self, response: Response) -> bool:
        """
        Cache response using intelligent caching strategy.
        
        Args:
            response: Response object to cache
            
        Returns:
            True if response was cached
        """
        if not self.should_cache_request(
            response.method, response.url, 
            response.request_headers, response.status_code
        ):
            return False
        
        smart_ttl = self.get_smart_ttl(
            response.method, response.url,
            response.request_headers, response.status_code
        )
        
        return self.cache_response(response, smart_ttl)
    
    def _get_strategy(self, url: str, headers: Optional[Dict[str, str]], 
                     status_code: Optional[int]) -> bool:
        """Caching strategy for GET requests."""
        # Always cache successful GET requests
        return status_code is None or 200 <= status_code < 400
    
    def _post_strategy(self, url: str, headers: Optional[Dict[str, str]], 
                      status_code: Optional[int]) -> bool:
        """Caching strategy for POST requests."""
        # Cache POST requests only if they're idempotent (like search)
        if any(keyword in url.lower() for keyword in ['search', 'query', 'filter']):
            return status_code is None or 200 <= status_code < 400
        return False
    
    def _put_strategy(self, url: str, headers: Optional[Dict[str, str]], 
                     status_code: Optional[int]) -> bool:
        """Caching strategy for PUT requests."""
        # Cache successful PUT responses briefly
        return status_code is not None and 200 <= status_code < 300
    
    def _patch_strategy(self, url: str, headers: Optional[Dict[str, str]], 
                       status_code: Optional[int]) -> bool:
        """Caching strategy for PATCH requests."""
        # Cache successful PATCH responses briefly
        return status_code is not None and 200 <= status_code < 300
    
    def _delete_strategy(self, url: str, headers: Optional[Dict[str, str]], 
                        status_code: Optional[int]) -> bool:
        """Caching strategy for DELETE requests."""
        # Cache successful DELETE responses very briefly
        return status_code is not None and 200 <= status_code < 300
    
    def _default_strategy(self, url: str, headers: Optional[Dict[str, str]], 
                         status_code: Optional[int]) -> bool:
        """Default caching strategy for unknown methods."""
        return False


class CacheAnalyzer:
    """Analyzer for cache performance and optimization."""
    
    def __init__(self, cache_manager: CacheManager):
        """
        Initialize cache analyzer.
        
        Args:
            cache_manager: CacheManager instance
        """
        self.cache_manager = cache_manager
    
    def analyze_cache_performance(self) -> Dict[str, Any]:
        """
        Analyze cache performance and provide insights.
        
        Returns:
            Dictionary with cache performance analysis
        """
        try:
            stats = self.cache_manager.get_cache_stats()
            entries = self.cache_manager.get_cache_entries()
            
            if not entries:
                return {
                    'total_entries': 0,
                    'recommendations': ['No cache entries found. Consider enabling caching for frequently accessed endpoints.']
                }
            
            # Analyze access patterns
            total_accesses = sum(entry['access_count'] for entry in entries)
            avg_accesses = total_accesses / len(entries) if entries else 0
            
            # Find most/least accessed entries
            most_accessed = max(entries, key=lambda x: x['access_count']) if entries else None
            least_accessed = min(entries, key=lambda x: x['access_count']) if entries else None
            
            # Analyze expiration patterns
            expired_count = sum(1 for entry in entries if entry['is_expired'])
            expiration_rate = (expired_count / len(entries)) * 100 if entries else 0
            
            # Generate recommendations
            recommendations = []
            
            if avg_accesses < 2:
                recommendations.append("Low cache hit rate detected. Consider adjusting TTL values or caching strategy.")
            
            if expiration_rate > 50:
                recommendations.append("High expiration rate detected. Consider increasing TTL for frequently accessed resources.")
            
            if stats.get('total_size_mb', 0) > 100:
                recommendations.append("Cache size is large. Consider implementing cache size limits or cleanup policies.")
            
            if not recommendations:
                recommendations.append("Cache performance looks good!")
            
            return {
                'total_entries': len(entries),
                'expired_entries': expired_count,
                'expiration_rate': round(expiration_rate, 2),
                'total_accesses': total_accesses,
                'average_accesses': round(avg_accesses, 2),
                'most_accessed': {
                    'key': most_accessed['key'][:50] + '...' if most_accessed and len(most_accessed['key']) > 50 else most_accessed['key'] if most_accessed else None,
                    'access_count': most_accessed['access_count'] if most_accessed else 0
                },
                'least_accessed': {
                    'key': least_accessed['key'][:50] + '...' if least_accessed and len(least_accessed['key']) > 50 else least_accessed['key'] if least_accessed else None,
                    'access_count': least_accessed['access_count'] if least_accessed else 0
                },
                'cache_stats': stats,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Error analyzing cache performance: {e}")
            return {'error': str(e)}
    
    def suggest_cache_optimization(self) -> List[str]:
        """
        Suggest cache optimization strategies.
        
        Returns:
            List of optimization suggestions
        """
        analysis = self.analyze_cache_performance()
        suggestions = []
        
        if 'error' in analysis:
            return ['Unable to analyze cache performance']
        
        # Based on analysis results
        if analysis['expiration_rate'] > 30:
            suggestions.append("Consider increasing TTL for frequently accessed resources")
        
        if analysis['average_accesses'] < 1.5:
            suggestions.append("Low cache utilization - review caching strategy")
        
        if analysis.get('cache_stats', {}).get('total_size_mb', 0) > 50:
            suggestions.append("Implement cache size limits and LRU eviction")
        
        # Add general suggestions
        suggestions.extend([
            "Use smart caching strategies based on HTTP methods",
            "Implement cache warming for critical endpoints",
            "Monitor cache hit rates and adjust TTL accordingly",
            "Consider using cache tags for better invalidation"
        ])
        
        return suggestions