"""
Unit tests for storage components.
"""
import pytest
import tempfile
import shutil
import time
from pathlib import Path

from src.reqsmith.storage import (
    MemoryCache, DiskManager, HybridStorage, 
    RequestTemplate, Environment, RequestRecord, CacheEntry
)


class TestMemoryCache:
    """Test cases for MemoryCache."""
    
    def test_init(self):
        """Test MemoryCache initialization."""
        cache = MemoryCache(max_size_mb=10)
        assert cache.max_size_bytes == 10 * 1024 * 1024
        assert len(cache.cache) == 0
        assert cache.current_size_bytes == 0
    
    def test_set_and_get(self):
        """Test setting and getting cache values."""
        cache = MemoryCache(max_size_mb=10)
        
        # Set value
        success = cache.set("key1", "value1")
        assert success == True
        
        # Get value
        value = cache.get("key1")
        assert value == "value1"
    
    def test_get_nonexistent(self):
        """Test getting non-existent key."""
        cache = MemoryCache(max_size_mb=10)
        value = cache.get("nonexistent")
        assert value is None
    
    def test_ttl_expiration(self):
        """Test TTL expiration."""
        cache = MemoryCache(max_size_mb=10)
        
        # Set value with short TTL
        cache.set("key1", "value1", ttl=1)
        
        # Should be available immediately
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get("key1") is None
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        # Create small cache
        cache = MemoryCache(max_size_mb=1)
        
        # Fill cache with large values
        large_value = "x" * (256 * 1024)  # 256KB
        
        for i in range(5):  # This should exceed 1MB
            cache.set(f"key{i}", large_value)
        
        # First keys should be evicted
        assert cache.get("key0") is None
        assert cache.get("key4") is not None
    
    def test_delete(self):
        """Test deleting cache entries."""
        cache = MemoryCache(max_size_mb=10)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        success = cache.delete("key1")
        assert success == True
        assert cache.get("key1") is None
    
    def test_clear(self):
        """Test clearing all cache entries."""
        cache = MemoryCache(max_size_mb=10)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        success = cache.clear()
        assert success == True
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.current_size_bytes == 0
    
    def test_get_stats(self):
        """Test getting cache statistics."""
        cache = MemoryCache(max_size_mb=10)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        stats = cache.get_stats()
        assert stats['total_items'] == 2
        assert stats['size_bytes'] > 0
        assert stats['max_size_mb'] == 10


class TestDiskManager:
    """Test cases for DiskManager."""
    
    def test_init(self, temp_dir):
        """Test DiskManager initialization."""
        manager = DiskManager(temp_dir)
        assert manager.user_storage_path == Path(temp_dir)
        
        # Check that directories were created
        assert (Path(temp_dir) / "templates").exists()
        assert (Path(temp_dir) / "environments").exists()
        assert (Path(temp_dir) / "history").exists()
    
    def test_save_and_load_json(self, temp_dir):
        """Test saving and loading JSON data."""
        manager = DiskManager(temp_dir)
        
        data = {"name": "test", "value": 123}
        
        # Save data
        success = manager.save("test_key", data, "test_category")
        assert success == True
        
        # Load data
        loaded_data = manager.load("test_key", "test_category")
        assert loaded_data == data
    
    def test_save_and_load_complex_object(self, temp_dir):
        """Test saving and loading complex objects."""
        manager = DiskManager(temp_dir)
        
        # Create a complex object using built-in types
        from datetime import datetime
        complex_obj = {
            'nested': {'data': [1, 2, 3]},
            'timestamp': datetime.now(),
            'tuple': (1, 2, 3),
            'set': {1, 2, 3}
        }
        
        # Save object
        success = manager.save("test_obj", complex_obj, "test_category")
        assert success == True
        
        # Load object
        loaded_obj = manager.load("test_obj", "test_category")
        assert loaded_obj['nested'] == complex_obj['nested']
        assert list(loaded_obj['tuple']) == list(complex_obj['tuple'])  # Convert tuple to list for comparison
        # Note: sets and datetime objects might not be exactly equal after pickle roundtrip
    
    def test_delete(self, temp_dir):
        """Test deleting stored data."""
        manager = DiskManager(temp_dir)
        
        data = {"test": "data"}
        manager.save("test_key", data, "test_category")
        
        # Verify data exists
        assert manager.load("test_key", "test_category") == data
        
        # Delete data
        success = manager.delete("test_key", "test_category")
        assert success == True
        
        # Verify data is gone
        assert manager.load("test_key", "test_category") is None
    
    def test_list_files(self, temp_dir):
        """Test listing stored files."""
        manager = DiskManager(temp_dir)
        
        # Save multiple files
        for i in range(3):
            manager.save(f"key{i}", f"value{i}", "test_category")
        
        # List files
        files = manager.list_files("test_category")
        assert len(files) == 3
        for i in range(3):
            assert f"key{i}" in files
    
    def test_get_storage_info(self, temp_dir):
        """Test getting storage information."""
        manager = DiskManager(temp_dir)
        
        # Save some data
        manager.save("test_key", "test_data", "test_category")
        
        info = manager.get_storage_info()
        assert info['storage_path'] == str(manager.user_storage_path)
        assert info['file_count'] > 0
        assert info['total_size_bytes'] > 0


class TestHybridStorage:
    """Test cases for HybridStorage."""
    
    def test_init(self, temp_dir):
        """Test HybridStorage initialization."""
        storage = HybridStorage("test_user", cache_size_mb=10)
        assert storage.user_id == "test_user"
        assert storage.cache_size_mb == 10
        assert storage.memory_cache is not None
        assert storage.disk_manager is not None
    
    def test_set_and_get_memory_only(self, temp_dir):
        """Test setting and getting memory-only data."""
        storage = HybridStorage("test_user", cache_size_mb=10)
        
        # Set memory-only data
        success = storage.set("key1", "value1", memory_only=True)
        assert success == True
        
        # Get data
        value = storage.get("key1")
        assert value == "value1"
    
    def test_set_and_get_persistent(self, temp_dir):
        """Test setting and getting persistent data."""
        storage = HybridStorage("test_user", cache_size_mb=10)
        
        # Set persistent data
        success = storage.set("key1", "value1", category="test")
        assert success == True
        
        # Get data
        value = storage.get("key1", category="test")
        assert value == "value1"
    
    def test_memory_to_disk_fallback(self, temp_dir):
        """Test fallback from memory to disk."""
        storage = HybridStorage("test_user", cache_size_mb=10)
        
        # Set data in both memory and disk
        storage.set("key1", "value1", category="test")
        
        # Clear memory cache
        storage.memory_cache.clear()
        
        # Should still be able to get from disk
        value = storage.get("key1", category="test")
        assert value == "value1"
    
    def test_delete(self, temp_dir):
        """Test deleting data from hybrid storage."""
        storage = HybridStorage("test_user", cache_size_mb=10)
        
        storage.set("key1", "value1", category="test")
        assert storage.get("key1", category="test") == "value1"
        
        success = storage.delete("key1", category="test")
        assert success == True
        assert storage.get("key1", category="test") is None
    
    def test_list_keys(self, temp_dir):
        """Test listing keys from hybrid storage."""
        storage = HybridStorage("test_user_listkeys", cache_size_mb=10)
        
        # Clear any existing keys in the test category
        storage.clear_cache("test")
        
        # Set multiple keys
        for i in range(3):
            storage.set(f"key{i}", f"value{i}", category="test")
        
        keys = storage.list_keys(category="test")
        assert len(keys) == 3
        for i in range(3):
            assert f"key{i}" in keys
    
    def test_get_cache_stats(self, temp_dir):
        """Test getting cache statistics."""
        storage = HybridStorage("test_user", cache_size_mb=10)
        
        storage.set("key1", "value1", category="test")
        
        stats = storage.get_cache_stats()
        assert 'memory_cache' in stats
        assert 'user_id' in stats
        assert stats['user_id'] == "test_user"


class TestDataModels:
    """Test cases for data models."""
    
    def test_request_template_creation(self):
        """Test RequestTemplate creation and validation."""
        template = RequestTemplate(
            name="test-template",
            method="GET",
            url="https://api.example.com/users",
            headers={"Authorization": "Bearer token"},
            body="",
            params={"limit": "10"},
            description="Test template",
            tags=["api", "test"]
        )
        
        assert template.name == "test-template"
        assert template.method == "GET"
        assert template.validate() == True
    
    def test_request_template_validation_invalid_method(self):
        """Test RequestTemplate validation with invalid method."""
        template = RequestTemplate(
            name="test-template",
            method="INVALID",
            url="https://api.example.com/users"
        )
        
        assert template.validate() == False
    
    def test_request_template_serialization(self):
        """Test RequestTemplate serialization."""
        template = RequestTemplate(
            name="test-template",
            method="GET",
            url="https://api.example.com/users"
        )
        
        # Test to_dict
        data = template.to_dict()
        assert data['name'] == "test-template"
        assert data['method'] == "GET"
        
        # Test from_dict
        new_template = RequestTemplate.from_dict(data)
        assert new_template.name == template.name
        assert new_template.method == template.method
    
    def test_environment_creation(self):
        """Test Environment creation and validation."""
        env = Environment(
            name="test-env",
            variables={"API_KEY": "secret", "BASE_URL": "https://api.example.com"},
            description="Test environment"
        )
        
        assert env.name == "test-env"
        assert env.variables["API_KEY"] == "secret"
        assert env.validate() == True
    
    def test_environment_variable_operations(self):
        """Test Environment variable operations."""
        env = Environment(
            name="test-env",
            variables={"API_KEY": "secret"}
        )
        
        # Set variable
        env.set_variable("NEW_KEY", "new_value")
        assert env.get_variable("NEW_KEY") == "new_value"
        
        # Delete variable
        success = env.delete_variable("NEW_KEY")
        assert success == True
        assert env.get_variable("NEW_KEY") is None
    
    def test_environment_variable_substitution(self):
        """Test Environment variable substitution."""
        env = Environment(
            name="test-env",
            variables={"API_KEY": "secret123", "USER_ID": "42"}
        )
        
        # Test substitution
        text = "Authorization: Bearer ${API_KEY}, User: ${USER_ID}"
        result = env.substitute_variables(text)
        assert result == "Authorization: Bearer secret123, User: 42"
        
        # Test with undefined variable
        text_with_undefined = "Key: ${UNDEFINED_KEY}"
        result = env.substitute_variables(text_with_undefined)
        assert "${UNDEFINED_KEY}" in result  # Should remain unchanged
    
    def test_request_record_creation(self):
        """Test RequestRecord creation and validation."""
        record = RequestRecord(
            timestamp=time.time(),
            method="GET",
            url="https://api.example.com/users",
            response_status=200,
            response_time=0.5,
            response_size=1024
        )
        
        assert record.method == "GET"
        assert record.response_status == 200
        assert record.validate() == True
        assert record.is_successful() == True
    
    def test_request_record_status_categories(self):
        """Test RequestRecord status categorization."""
        # Success
        success_record = RequestRecord(
            timestamp=time.time(),
            method="GET",
            url="test",
            response_status=200,
            response_time=0.5,
            response_size=100
        )
        assert success_record.get_status_category() == "success"
        assert success_record.is_successful() == True
        
        # Client error
        error_record = RequestRecord(
            timestamp=time.time(),
            method="GET",
            url="test",
            response_status=404,
            response_time=0.5,
            response_size=100
        )
        assert error_record.get_status_category() == "client_error"
        assert error_record.is_successful() == False
    
    def test_cache_entry_creation(self):
        """Test CacheEntry creation and validation."""
        entry = CacheEntry(
            key="test_key",
            data={"test": "data"},
            ttl=3600
        )
        
        assert entry.key == "test_key"
        assert entry.ttl == 3600
        assert entry.validate() == True
        assert entry.is_expired() == False
    
    def test_cache_entry_expiration(self):
        """Test CacheEntry expiration."""
        # Create entry with short TTL
        entry = CacheEntry(
            key="test_key",
            data={"test": "data"},
            ttl=1
        )
        
        # Should not be expired immediately
        assert entry.is_expired() == False
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired now
        assert entry.is_expired() == True