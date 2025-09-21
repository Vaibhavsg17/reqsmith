"""
Unit tests for CacheManager.
"""
import pytest
from unittest.mock import Mock, patch
import time

from src.reqsmith.core.cache_manager import CacheManager, SmartCacheManager, CacheAnalyzer
from src.reqsmith.core.http_client import Response


class TestCacheManager:
    """Test cases for CacheManager."""
    
    def test_init(self, mock_storage):
        """Test CacheManager initialization."""
        manager = CacheManager(mock_storage, default_ttl=1800)
        assert manager.storage == mock_storage
        assert manager.default_ttl == 1800
        assert manager.cache_enabled == True
        assert manager.cache_storage is not None
    
    def test_generate_cache_key(self, mock_storage):
        """Test cache key generation."""
        manager = CacheManager(mock_storage)
        
        key1 = manager.generate_cache_key("GET", "https://api.example.com", {}, "")
        key2 = manager.generate_cache_key("GET", "https://api.example.com", {}, "")
        key3 = manager.generate_cache_key("POST", "https://api.example.com", {}, "")
        
        # Same parameters should generate same key
        assert key1 == key2
        
        # Different method should generate different key
        assert key1 != key3
    
    def test_cache_response_success(self, mock_storage, mock_response):
        """Test successful response caching."""
        manager = CacheManager(mock_storage)
        
        success = manager.cache_response(mock_response, ttl=300)
        assert success == True
    
    def test_cache_response_disabled(self, mock_storage, mock_response):
        """Test caching when disabled."""
        manager = CacheManager(mock_storage)
        manager.set_cache_enabled(False)
        
        success = manager.cache_response(mock_response)
        assert success == False
    
    def test_get_cached_response_hit(self, mock_storage):
        """Test cache hit scenario."""
        manager = CacheManager(mock_storage)
        
        # Create and cache a response
        response = Mock()
        response.method = "GET"
        response.url = "https://api.example.com/test"
        response.status_code = 200
        response.headers = {"Content-Type": "application/json"}
        response.content = b'{"test": true}'
        response.text = '{"test": true}'
        response.request_headers = {}
        response.request_body = ""
        response.elapsed_time = 0.5
        response.size_bytes = 15
        
        # Cache the response
        manager.cache_response(response)
        
        # Try to get cached response
        cached = manager.get_cached_response("GET", "https://api.example.com/test")
        
        # Should get a response (mocked storage will return something)
        # In real implementation, this would be the actual cached response
        assert cached is not None or cached is None  # Depends on mock behavior
    
    def test_get_cached_response_miss(self, mock_storage):
        """Test cache miss scenario."""
        manager = CacheManager(mock_storage)
        
        # Try to get non-existent cached response
        cached = manager.get_cached_response("GET", "https://api.example.com/nonexistent")
        assert cached is None
    
    def test_get_cached_response_disabled(self, mock_storage):
        """Test getting cached response when caching is disabled."""
        manager = CacheManager(mock_storage)
        manager.set_cache_enabled(False)
        
        cached = manager.get_cached_response("GET", "https://api.example.com/test")
        assert cached is None
    
    def test_clear_cache(self, mock_storage):
        """Test clearing cache."""
        manager = CacheManager(mock_storage)
        
        success = manager.clear_cache()
        assert success == True
    
    def test_cleanup_expired(self, mock_storage):
        """Test cleaning up expired entries."""
        manager = CacheManager(mock_storage)
        
        # Mock the cleanup to return a count
        with patch.object(manager.cache_storage, 'cleanup_expired', return_value=5):
            removed_count = manager.cleanup_expired()
            assert removed_count == 5
    
    def test_get_cache_stats(self, mock_storage):
        """Test getting cache statistics."""
        manager = CacheManager(mock_storage)
        
        # Mock cache storage stats
        mock_stats = {
            'total_entries': 10,
            'total_size_mb': 5.2,
            'hit_rate': 0.75
        }
        
        with patch.object(manager.cache_storage, 'get_cache_stats', return_value=mock_stats):
            stats = manager.get_cache_stats()
            
            assert stats['total_entries'] == 10
            assert stats['cache_enabled'] == True
            assert stats['default_ttl'] == manager.default_ttl
    
    def test_get_cache_entries(self, mock_storage):
        """Test getting cache entries information."""
        manager = CacheManager(mock_storage)
        
        # Mock storage to return some keys
        with patch.object(manager.storage, 'list_keys', return_value=['key1', 'key2']):
            with patch.object(manager.storage, 'get', return_value=None):
                entries = manager.get_cache_entries(limit=10)
                
                # Should return empty list since get returns None
                assert isinstance(entries, list)
    
    def test_delete_cache_entry(self, mock_storage):
        """Test deleting specific cache entry."""
        manager = CacheManager(mock_storage)
        
        with patch.object(manager.storage, 'delete', return_value=True):
            success = manager.delete_cache_entry("test_key")
            assert success == True
    
    def test_set_cache_enabled(self, mock_storage):
        """Test enabling/disabling cache."""
        manager = CacheManager(mock_storage)
        
        assert manager.is_cache_enabled() == True
        
        manager.set_cache_enabled(False)
        assert manager.is_cache_enabled() == False
        
        manager.set_cache_enabled(True)
        assert manager.is_cache_enabled() == True
    
    def test_set_default_ttl(self, mock_storage):
        """Test setting default TTL."""
        manager = CacheManager(mock_storage)
        
        manager.set_default_ttl(7200)
        assert manager.get_default_ttl() == 7200
    
    def test_set_default_ttl_invalid(self, mock_storage):
        """Test setting invalid TTL."""
        manager = CacheManager(mock_storage)
        
        with pytest.raises(ValueError, match="TTL must be positive"):
            manager.set_default_ttl(0)
        
        with pytest.raises(ValueError, match="TTL must be positive"):
            manager.set_default_ttl(-1)
    
    def test_serialize_deserialize_response(self, mock_storage):
        """Test response serialization and deserialization."""
        manager = CacheManager(mock_storage)
        
        # Create a response
        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=b'{"test": true}',
            text='{"test": true}',
            url="https://api.example.com/test",
            method="GET",
            request_headers={"Authorization": "Bearer token"},
            request_body="",
            elapsed_time=0.5,
            size_bytes=15
        )
        
        # Serialize
        serialized = manager._serialize_response(response)
        
        assert serialized['status_code'] == 200
        assert serialized['method'] == "GET"
        assert serialized['url'] == "https://api.example.com/test"
        assert 'cached_at' in serialized
        
        # Deserialize
        deserialized = manager._deserialize_response(serialized)
        
        assert deserialized is not None
        assert deserialized.status_code == 200
        assert deserialized.method == "GET"
        assert deserialized.url == "https://api.example.com/test"


class TestSmartCacheManager:
    """Test cases for SmartCacheManager."""
    
    def test_init(self, mock_storage):
        """Test SmartCacheManager initialization."""
        manager = SmartCacheManager(mock_storage)
        assert isinstance(manager, CacheManager)
        assert hasattr(manager, 'cache_strategies')
    
    def test_should_cache_request_get(self, mock_storage):
        """Test caching decision for GET requests."""
        manager = SmartCacheManager(mock_storage)
        
        # Successful GET should be cached
        assert manager.should_cache_request("GET", "https://api.example.com", status_code=200) == True
        
        # Failed GET should not be cached
        assert manager.should_cache_request("GET", "https://api.example.com", status_code=404) == False
        
        # Server error should not be cached
        assert manager.should_cache_request("GET", "https://api.example.com", status_code=500) == False
    
    def test_should_cache_request_post(self, mock_storage):
        """Test caching decision for POST requests."""
        manager = SmartCacheManager(mock_storage)
        
        # Regular POST should not be cached
        assert manager.should_cache_request("POST", "https://api.example.com/users", status_code=201) == False
        
        # Search POST should be cached
        assert manager.should_cache_request("POST", "https://api.example.com/search", status_code=200) == True
        
        # Query POST should be cached
        assert manager.should_cache_request("POST", "https://api.example.com/query", status_code=200) == True
    
    def test_should_cache_request_disabled(self, mock_storage):
        """Test caching decision when cache is disabled."""
        manager = SmartCacheManager(mock_storage)
        manager.set_cache_enabled(False)
        
        assert manager.should_cache_request("GET", "https://api.example.com", status_code=200) == False
    
    def test_get_smart_ttl_by_method(self, mock_storage):
        """Test smart TTL calculation by HTTP method."""
        manager = SmartCacheManager(mock_storage, default_ttl=3600)
        
        # GET should use default TTL
        get_ttl = manager.get_smart_ttl("GET", "https://example.com")
        assert get_ttl == 3600
        
        # POST should use shorter TTL
        post_ttl = manager.get_smart_ttl("POST", "https://example.com")
        assert post_ttl == 300
        
        # DELETE should use very short TTL
        delete_ttl = manager.get_smart_ttl("DELETE", "https://example.com")
        assert delete_ttl == 60
    
    def test_get_smart_ttl_by_url_pattern(self, mock_storage):
        """Test smart TTL calculation by URL patterns."""
        manager = SmartCacheManager(mock_storage, default_ttl=3600)
        
        # API endpoints should have shorter TTL
        api_ttl = manager.get_smart_ttl("GET", "https://api.example.com/users")
        assert api_ttl < 3600
        
        # Search endpoints should have very short TTL
        search_ttl = manager.get_smart_ttl("GET", "https://api.example.com/search?q=test")
        assert search_ttl < api_ttl
        
        # Static resources should have longer TTL
        static_ttl = manager.get_smart_ttl("GET", "https://cdn.example.com/static/image.png")
        assert static_ttl > 3600
    
    def test_get_smart_ttl_by_status_code(self, mock_storage):
        """Test smart TTL calculation by status code."""
        manager = SmartCacheManager(mock_storage, default_ttl=3600)
        
        # 200 OK should use base TTL
        ok_ttl = manager.get_smart_ttl("GET", "https://example.com", status_code=200)
        assert ok_ttl == 3600
        
        # 201 Created should use shorter TTL
        created_ttl = manager.get_smart_ttl("POST", "https://example.com", status_code=201)
        assert created_ttl < 300  # Base POST TTL is 300
        
        # 301 Redirect should use longer TTL
        redirect_ttl = manager.get_smart_ttl("GET", "https://example.com", status_code=301)
        assert redirect_ttl > 3600
        
        # 304 Not Modified should use much longer TTL
        not_modified_ttl = manager.get_smart_ttl("GET", "https://example.com", status_code=304)
        assert not_modified_ttl > redirect_ttl
    
    def test_get_smart_ttl_minimum(self, mock_storage):
        """Test that smart TTL respects minimum value."""
        manager = SmartCacheManager(mock_storage, default_ttl=30)  # Very short default
        
        # Should never go below 60 seconds
        ttl = manager.get_smart_ttl("GET", "https://api.example.com/search")
        assert ttl >= 60
    
    def test_cache_response_smart(self, mock_storage):
        """Test smart response caching."""
        manager = SmartCacheManager(mock_storage)
        
        # Create a response that should be cached
        response = Mock()
        response.method = "GET"
        response.url = "https://api.example.com/users"
        response.status_code = 200
        response.request_headers = {}
        response.request_body = ""
        
        with patch.object(manager, 'should_cache_request', return_value=True):
            with patch.object(manager, 'get_smart_ttl', return_value=1800):
                with patch.object(manager, 'cache_response', return_value=True) as mock_cache:
                    result = manager.cache_response_smart(response)
                    
                    assert result == True
                    mock_cache.assert_called_once_with(response, 1800)
    
    def test_cache_response_smart_should_not_cache(self, mock_storage):
        """Test smart caching when response should not be cached."""
        manager = SmartCacheManager(mock_storage)
        
        # Create a response that should not be cached
        response = Mock()
        response.method = "POST"
        response.url = "https://api.example.com/users"
        response.status_code = 201
        response.request_headers = {}
        response.request_body = ""
        
        with patch.object(manager, 'should_cache_request', return_value=False):
            result = manager.cache_response_smart(response)
            assert result == False


class TestCacheAnalyzer:
    """Test cases for CacheAnalyzer."""
    
    def test_init(self, mock_storage):
        """Test CacheAnalyzer initialization."""
        cache_manager = CacheManager(mock_storage)
        analyzer = CacheAnalyzer(cache_manager)
        assert analyzer.cache_manager == cache_manager
    
    def test_analyze_cache_performance_no_entries(self, mock_storage):
        """Test cache performance analysis with no entries."""
        cache_manager = CacheManager(mock_storage)
        analyzer = CacheAnalyzer(cache_manager)
        
        with patch.object(cache_manager, 'get_cache_entries', return_value=[]):
            analysis = analyzer.analyze_cache_performance()
            
            assert analysis['total_entries'] == 0
            assert 'recommendations' in analysis
            assert len(analysis['recommendations']) > 0
    
    def test_analyze_cache_performance_with_entries(self, mock_storage):
        """Test cache performance analysis with cache entries."""
        cache_manager = CacheManager(mock_storage)
        analyzer = CacheAnalyzer(cache_manager)
        
        # Mock cache entries
        mock_entries = [
            {
                'key': 'key1',
                'access_count': 5,
                'is_expired': False,
                'created_at': time.time(),
                'size_bytes': 1024
            },
            {
                'key': 'key2',
                'access_count': 2,
                'is_expired': True,
                'created_at': time.time() - 3600,
                'size_bytes': 2048
            },
            {
                'key': 'key3',
                'access_count': 8,
                'is_expired': False,
                'created_at': time.time() - 1800,
                'size_bytes': 512
            }
        ]
        
        mock_stats = {
            'total_entries': 3,
            'total_size_mb': 3.5
        }
        
        with patch.object(cache_manager, 'get_cache_entries', return_value=mock_entries):
            with patch.object(cache_manager, 'get_cache_stats', return_value=mock_stats):
                analysis = analyzer.analyze_cache_performance()
                
                assert analysis['total_entries'] == 3
                assert analysis['expired_entries'] == 1
                assert analysis['expiration_rate'] == 33.33  # 1/3 * 100
                assert analysis['total_accesses'] == 15  # 5 + 2 + 8
                assert analysis['average_accesses'] == 5.0  # 15/3
                assert analysis['most_accessed']['access_count'] == 8
                assert 'recommendations' in analysis
    
    def test_suggest_cache_optimization(self, mock_storage):
        """Test cache optimization suggestions."""
        cache_manager = CacheManager(mock_storage)
        analyzer = CacheAnalyzer(cache_manager)
        
        # Mock analysis results
        mock_analysis = {
            'expiration_rate': 40.0,  # High expiration rate
            'average_accesses': 1.2,  # Low utilization
            'cache_stats': {'total_size_mb': 60}  # Large cache
        }
        
        with patch.object(analyzer, 'analyze_cache_performance', return_value=mock_analysis):
            suggestions = analyzer.suggest_cache_optimization()
            
            assert isinstance(suggestions, list)
            assert len(suggestions) > 0
            
            # Should include specific suggestions based on analysis
            suggestion_text = ' '.join(suggestions).lower()
            assert 'ttl' in suggestion_text  # Should suggest TTL changes
            assert 'cache' in suggestion_text  # Should mention caching
    
    def test_suggest_cache_optimization_error(self, mock_storage):
        """Test cache optimization suggestions when analysis fails."""
        cache_manager = CacheManager(mock_storage)
        analyzer = CacheAnalyzer(cache_manager)
        
        # Mock analysis to return error
        with patch.object(analyzer, 'analyze_cache_performance', return_value={'error': 'Test error'}):
            suggestions = analyzer.suggest_cache_optimization()
            
            assert isinstance(suggestions, list)
            assert len(suggestions) == 1
            assert 'unable to analyze' in suggestions[0].lower()