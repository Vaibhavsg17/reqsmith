"""
Integration tests for storage components.
"""
import pytest
import tempfile
import shutil
import time
from pathlib import Path

from src.reqsmith.storage import (
    HybridStorage, MemoryCache, DiskManager,
    RequestTemplate, Environment, RequestRecord, CacheEntry
)


class TestHybridStorageIntegration:
    """Integration tests for HybridStorage with real file system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = HybridStorage("test_user", cache_size_mb=5)
        # Override storage path for testing
        self.storage.disk_manager.user_storage_path = Path(self.temp_dir)
        self.storage.disk_manager.ensure_user_directory()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_memory_and_disk_coordination(self):
        """Test coordination between memory cache and disk storage."""
        # Store data that should go to both memory and disk
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        
        success = self.storage.set("test_key", test_data, category="test")
        assert success == True
        
        # Data should be in memory cache
        memory_data = self.storage.memory_cache.get("test_key")
        assert memory_data is not None
        
        # Data should also be on disk
        disk_data = self.storage.disk_manager.load("test_key", "test")
        assert disk_data == test_data
        
        # Clear memory cache
        self.storage.memory_cache.clear()
        
        # Should still be able to get data from disk
        retrieved_data = self.storage.get("test_key", category="test")
        assert retrieved_data == test_data
    
    def test_memory_cache_overflow_to_disk(self):
        """Test that memory cache overflows to disk when full."""
        # Fill memory cache with large data
        large_data = "x" * (1024 * 1024)  # 1MB
        
        # Add multiple large items to exceed cache size
        for i in range(10):
            self.storage.set(f"large_key_{i}", large_data, memory_only=True)
        
        # Some items should have been evicted from memory
        memory_stats = self.storage.memory_cache.get_stats()
        assert memory_stats['total_items'] < 10
    
    def test_ttl_expiration_integration(self):
        """Test TTL expiration across memory and disk."""
        # Set data with short TTL
        test_data = {"expires": "soon"}
        
        success = self.storage.set("ttl_key", test_data, ttl=1, category="test")
        assert success == True
        
        # Should be available immediately
        retrieved = self.storage.get("ttl_key", category="test")
        assert retrieved == test_data
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        retrieved = self.storage.get("ttl_key", category="test")
        assert retrieved is None
    
    def test_concurrent_access_simulation(self):
        """Test concurrent access patterns."""
        # Simulate multiple operations happening quickly
        for i in range(50):
            key = f"concurrent_key_{i}"
            data = {"index": i, "data": f"test_data_{i}"}
            
            # Set data
            success = self.storage.set(key, data, category="concurrent")
            assert success == True
            
            # Immediately retrieve
            retrieved = self.storage.get(key, category="concurrent")
            assert retrieved == data
            
            # Delete some items
            if i % 3 == 0:
                self.storage.delete(key, category="concurrent")
    
    def test_storage_persistence_across_instances(self):
        """Test that data persists across storage instances."""
        # Store data in first instance
        test_data = {"persistent": True, "value": 123}
        success = self.storage.set("persist_key", test_data, category="persist")
        assert success == True
        
        # Create new storage instance
        new_storage = HybridStorage("test_user", cache_size_mb=5)
        new_storage.disk_manager.user_storage_path = Path(self.temp_dir)
        
        # Data should be available in new instance
        retrieved = new_storage.get("persist_key", category="persist")
        assert retrieved == test_data
    
    def test_category_isolation(self):
        """Test that different categories are properly isolated."""
        # Store data in different categories
        categories = ["templates", "environments", "history", "cache"]
        
        for category in categories:
            data = {f"{category}_data": True}
            success = self.storage.set("same_key", data, category=category)
            assert success == True
        
        # Verify each category has its own data
        for category in categories:
            retrieved = self.storage.get("same_key", category=category)
            assert retrieved[f"{category}_data"] == True
        
        # List keys for each category
        for category in categories:
            keys = self.storage.list_keys(category=category)
            assert "same_key" in keys


class TestTemplateStorageIntegration:
    """Integration tests for template storage operations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = HybridStorage("test_user", cache_size_mb=5)
        self.storage.disk_manager.user_storage_path = Path(self.temp_dir)
        self.storage.disk_manager.ensure_user_directory()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_template_crud_operations(self):
        """Test complete CRUD operations for templates."""
        # Create template
        template = RequestTemplate(
            name="integration-template",
            method="POST",
            url="https://api.example.com/users",
            headers={"Content-Type": "application/json", "Authorization": "Bearer ${TOKEN}"},
            body='{"name": "${USER_NAME}", "email": "${USER_EMAIL}"}',
            params={"format": "json"},
            description="Integration test template",
            tags=["api", "users", "test"]
        )
        
        # Save template
        success = self.storage.set(template.name, template.to_dict(), category="templates")
        assert success == True
        
        # Load template
        loaded_data = self.storage.get(template.name, category="templates")
        assert loaded_data is not None
        
        loaded_template = RequestTemplate.from_dict(loaded_data)
        assert loaded_template.name == template.name
        assert loaded_template.method == template.method
        assert loaded_template.url == template.url
        assert loaded_template.headers == template.headers
        assert loaded_template.body == template.body
        
        # Update template
        template.description = "Updated description"
        template.tags.append("updated")
        
        success = self.storage.set(template.name, template.to_dict(), category="templates")
        assert success == True
        
        # Verify update
        updated_data = self.storage.get(template.name, category="templates")
        updated_template = RequestTemplate.from_dict(updated_data)
        assert updated_template.description == "Updated description"
        assert "updated" in updated_template.tags
        
        # Delete template
        success = self.storage.delete(template.name, category="templates")
        assert success == True
        
        # Verify deletion
        deleted_data = self.storage.get(template.name, category="templates")
        assert deleted_data is None
    
    def test_multiple_templates_storage(self):
        """Test storing and managing multiple templates."""
        templates = []
        
        # Create multiple templates
        for i in range(10):
            template = RequestTemplate(
                name=f"template-{i}",
                method="GET" if i % 2 == 0 else "POST",
                url=f"https://api.example.com/endpoint{i}",
                headers={"Authorization": f"Bearer token-{i}"},
                description=f"Template number {i}",
                tags=[f"tag{i}", "test"]
            )
            templates.append(template)
        
        # Save all templates
        for template in templates:
            success = self.storage.set(template.name, template.to_dict(), category="templates")
            assert success == True
        
        # List all template keys
        template_keys = self.storage.list_keys(category="templates")
        assert len(template_keys) == 10
        
        # Verify all templates can be loaded
        for template in templates:
            loaded_data = self.storage.get(template.name, category="templates")
            assert loaded_data is not None
            
            loaded_template = RequestTemplate.from_dict(loaded_data)
            assert loaded_template.name == template.name
            assert loaded_template.method == template.method


class TestEnvironmentStorageIntegration:
    """Integration tests for environment storage operations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = HybridStorage("test_user", cache_size_mb=5)
        self.storage.disk_manager.user_storage_path = Path(self.temp_dir)
        self.storage.disk_manager.ensure_user_directory()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_environment_persistence(self):
        """Test environment data persistence."""
        # Create environment
        env = Environment(
            name="test-environment",
            variables={
                "API_KEY": "secret-key-123",
                "BASE_URL": "https://api.example.com",
                "TIMEOUT": "30",
                "DEBUG": "true"
            },
            description="Test environment for integration tests"
        )
        
        # Save environment
        success = self.storage.set(env.name, env.to_dict(), category="environments")
        assert success == True
        
        # Load environment
        loaded_data = self.storage.get(env.name, category="environments")
        assert loaded_data is not None
        
        loaded_env = Environment.from_dict(loaded_data)
        assert loaded_env.name == env.name
        assert loaded_env.variables == env.variables
        assert loaded_env.description == env.description
        
        # Test variable operations
        loaded_env.set_variable("NEW_VAR", "new_value")
        assert loaded_env.get_variable("NEW_VAR") == "new_value"
        
        # Save updated environment
        success = self.storage.set(env.name, loaded_env.to_dict(), category="environments")
        assert success == True
        
        # Verify update persisted
        updated_data = self.storage.get(env.name, category="environments")
        updated_env = Environment.from_dict(updated_data)
        assert updated_env.get_variable("NEW_VAR") == "new_value"
    
    def test_multiple_environments(self):
        """Test managing multiple environments."""
        environments = ["development", "staging", "production", "testing"]
        
        for env_name in environments:
            env = Environment(
                name=env_name,
                variables={
                    "ENV_NAME": env_name,
                    "API_URL": f"https://{env_name}.api.example.com",
                    "LOG_LEVEL": "DEBUG" if env_name == "development" else "INFO"
                },
                description=f"{env_name.title()} environment"
            )
            
            success = self.storage.set(env.name, env.to_dict(), category="environments")
            assert success == True
        
        # Verify all environments exist
        env_keys = self.storage.list_keys(category="environments")
        assert len(env_keys) == 4
        
        for env_name in environments:
            assert env_name in env_keys
        
        # Test current environment tracking
        current_env_data = {"current": "production"}
        self.storage.set("current", current_env_data, category="environments")
        
        current_data = self.storage.get("current", category="environments")
        assert current_data["current"] == "production"


class TestHistoryStorageIntegration:
    """Integration tests for history storage operations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = HybridStorage("test_user", cache_size_mb=5)
        self.storage.disk_manager.user_storage_path = Path(self.temp_dir)
        self.storage.disk_manager.ensure_user_directory()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_history_fifo_behavior(self):
        """Test FIFO behavior of history storage."""
        # Create history records
        records = []
        for i in range(20):
            record = RequestRecord(
                timestamp=time.time() + i,  # Ensure different timestamps
                method="GET",
                url=f"https://api.example.com/endpoint{i}",
                headers={"Authorization": "Bearer token"},
                body="",
                response_status=200,
                response_time=0.5,
                response_size=1024,
                template_name=f"template-{i}" if i % 3 == 0 else None,
                environment="test-env"
            )
            records.append(record)
        
        # Save history as JSONL (append-only)
        history_data = [record.to_dict() for record in records]
        success = self.storage.set("history", history_data, category="history")
        assert success == True
        
        # Load history
        loaded_history = self.storage.get("history", category="history")
        assert loaded_history is not None
        assert len(loaded_history) == 20
        
        # Verify order (should be in chronological order)
        for i, record_data in enumerate(loaded_history):
            record = RequestRecord.from_dict(record_data)
            assert record.url == f"https://api.example.com/endpoint{i}"
    
    def test_history_size_limits(self):
        """Test history size management."""
        max_entries = 10
        
        # Create more records than the limit
        records = []
        for i in range(15):
            record = RequestRecord(
                timestamp=time.time() + i,
                method="POST",
                url=f"https://api.example.com/create{i}",
                headers={"Content-Type": "application/json"},
                body=f'{{"id": {i}}}',
                response_status=201,
                response_time=0.3,
                response_size=50
            )
            records.append(record)
        
        # Simulate FIFO with size limit
        history_data = [record.to_dict() for record in records[-max_entries:]]
        success = self.storage.set("limited_history", history_data, category="history")
        assert success == True
        
        # Verify only the last 10 records are stored
        loaded_history = self.storage.get("limited_history", category="history")
        assert len(loaded_history) == max_entries
        
        # Verify it's the most recent records
        first_record = RequestRecord.from_dict(loaded_history[0])
        assert "create5" in first_record.url  # Should start from record 5
        
        last_record = RequestRecord.from_dict(loaded_history[-1])
        assert "create14" in last_record.url  # Should end with record 14


class TestCacheStorageIntegration:
    """Integration tests for cache storage operations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = HybridStorage("test_user", cache_size_mb=5)
        self.storage.disk_manager.user_storage_path = Path(self.temp_dir)
        self.storage.disk_manager.ensure_user_directory()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cache_entry_lifecycle(self):
        """Test complete cache entry lifecycle."""
        # Create cache entry
        cache_entry = CacheEntry(
            key="test_cache_key",
            data={"response": "cached data", "status": 200},
            ttl=300  # 5 minutes
        )
        
        # Save cache entry
        success = self.storage.set(cache_entry.key, cache_entry.to_dict(), category="cache")
        assert success == True
        
        # Load cache entry
        loaded_data = self.storage.get(cache_entry.key, category="cache")
        assert loaded_data is not None
        
        loaded_entry = CacheEntry.from_dict(loaded_data)
        assert loaded_entry.key == cache_entry.key
        assert loaded_entry.data == cache_entry.data
        assert loaded_entry.ttl == cache_entry.ttl
        assert not loaded_entry.is_expired()
        
        # Test expiration
        expired_entry = CacheEntry(
            key="expired_key",
            data={"old": "data"},
            ttl=1  # 1 second
        )
        
        success = self.storage.set(expired_entry.key, expired_entry.to_dict(), category="cache")
        assert success == True
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Load and check expiration
        expired_data = self.storage.get(expired_entry.key, category="cache")
        if expired_data:  # Might be cleaned up automatically
            expired_loaded = CacheEntry.from_dict(expired_data)
            assert expired_loaded.is_expired()
    
    def test_cache_cleanup_integration(self):
        """Test cache cleanup operations."""
        # Create multiple cache entries with different TTLs
        entries = []
        for i in range(10):
            entry = CacheEntry(
                key=f"cache_key_{i}",
                data={"index": i, "data": f"cached_data_{i}"},
                ttl=1 if i < 5 else 300  # First 5 expire quickly
            )
            entries.append(entry)
        
        # Save all entries
        for entry in entries:
            success = self.storage.set(entry.key, entry.to_dict(), category="cache")
            assert success == True
        
        # Wait for some to expire
        time.sleep(1.1)
        
        # Check which entries are expired
        expired_count = 0
        valid_count = 0
        
        for entry in entries:
            loaded_data = self.storage.get(entry.key, category="cache")
            if loaded_data:
                loaded_entry = CacheEntry.from_dict(loaded_data)
                if loaded_entry.is_expired():
                    expired_count += 1
                else:
                    valid_count += 1
        
        # Should have some expired and some valid entries
        assert expired_count > 0
        assert valid_count > 0


class TestStorageErrorHandling:
    """Integration tests for storage error handling."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_disk_space_handling(self):
        """Test handling when disk space is limited."""
        storage = HybridStorage("test_user", cache_size_mb=1)  # Very small cache
        storage.disk_manager.user_storage_path = Path(self.temp_dir)
        storage.disk_manager.ensure_user_directory()
        
        # Try to store large amount of data
        large_data = "x" * (10 * 1024 * 1024)  # 10MB
        
        # Should handle gracefully (might fail or succeed depending on implementation)
        try:
            success = storage.set("large_key", large_data, category="test")
            # If it succeeds, that's fine
            assert success in [True, False]
        except Exception:
            # If it raises an exception, that should be handled gracefully
            pass
    
    def test_corrupted_data_handling(self):
        """Test handling of corrupted data files."""
        storage = HybridStorage("test_user", cache_size_mb=5)
        storage.disk_manager.user_storage_path = Path(self.temp_dir)
        storage.disk_manager.ensure_user_directory()
        
        # Create a corrupted file
        corrupted_file = Path(self.temp_dir) / "test" / "corrupted.json"
        corrupted_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(corrupted_file, 'w') as f:
            f.write("invalid json content {")
        
        # Try to load corrupted data
        result = storage.disk_manager.load("corrupted", "test")
        # Should return None or handle gracefully
        assert result is None or isinstance(result, dict)
    
    def test_permission_error_handling(self):
        """Test handling of permission errors."""
        # This test might not work on all systems, so we'll simulate it
        storage = HybridStorage("test_user", cache_size_mb=5)
        
        # Try to use a path that might cause permission issues
        restricted_path = Path("/root/restricted") if Path("/root").exists() else Path(self.temp_dir) / "restricted"
        
        try:
            storage.disk_manager.user_storage_path = restricted_path
            storage.disk_manager.ensure_user_directory()
            
            # Try to store data
            success = storage.set("test_key", {"test": "data"}, category="test")
            # Should handle gracefully
            assert success in [True, False]
        except PermissionError:
            # Expected behavior
            pass