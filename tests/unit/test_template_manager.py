"""
Unit tests for TemplateManager and EnvironmentManager.
"""
import pytest
from unittest.mock import Mock, patch
import time

from src.reqsmith.core.template_manager import TemplateManager
from src.reqsmith.core.env_manager import EnvironmentManager
from src.reqsmith.storage import RequestTemplate, Environment


class TestTemplateManager:
    """Test cases for TemplateManager."""
    
    def test_init(self, mock_storage):
        """Test TemplateManager initialization."""
        manager = TemplateManager(mock_storage)
        assert manager.storage == mock_storage
        assert manager.template_storage is not None
    
    def test_save_template_success(self, template_manager):
        """Test successful template saving."""
        success = template_manager.save_template(
            name="test-template",
            method="GET",
            url="https://api.example.com/users",
            headers={"Authorization": "Bearer token"},
            description="Test template"
        )
        
        assert success == True
    
    def test_save_template_invalid_name(self, template_manager):
        """Test template saving with invalid name."""
        with pytest.raises(ValueError, match="Template name cannot be empty"):
            template_manager.save_template(
                name="",
                method="GET",
                url="https://api.example.com/users"
            )
    
    def test_save_template_invalid_method(self, template_manager):
        """Test template saving with invalid HTTP method."""
        with pytest.raises(ValueError, match="Invalid HTTP method"):
            template_manager.save_template(
                name="test-template",
                method="INVALID",
                url="https://api.example.com/users"
            )
    
    def test_save_template_invalid_url(self, template_manager):
        """Test template saving with invalid URL."""
        with pytest.raises(ValueError, match="Invalid URL"):
            template_manager.save_template(
                name="test-template",
                method="GET",
                url="invalid-url"
            )
    
    def test_save_template_duplicate_name(self, template_manager):
        """Test template saving with duplicate name."""
        # Save first template
        template_manager.save_template(
            name="duplicate-template",
            method="GET",
            url="https://api.example.com/users"
        )
        
        # Try to save another with same name
        with pytest.raises(ValueError, match="already exists"):
            template_manager.save_template(
                name="duplicate-template",
                method="POST",
                url="https://api.example.com/users"
            )
    
    def test_load_template_success(self, template_manager, sample_template):
        """Test successful template loading."""
        # Save template first
        template_manager.save_template(
            name=sample_template.name,
            method=sample_template.method,
            url=sample_template.url,
            headers=sample_template.headers,
            body=sample_template.body,
            params=sample_template.params,
            description=sample_template.description,
            tags=sample_template.tags
        )
        
        # Load template
        loaded_template = template_manager.load_template(sample_template.name)
        
        assert loaded_template is not None
        assert loaded_template.name == sample_template.name
        assert loaded_template.method == sample_template.method
        assert loaded_template.url == sample_template.url
    
    def test_load_template_not_found(self, template_manager):
        """Test loading non-existent template."""
        template = template_manager.load_template("non-existent")
        assert template is None
    
    def test_update_template_success(self, template_manager, sample_template):
        """Test successful template update."""
        # Save template first
        template_manager.save_template(
            name=sample_template.name,
            method=sample_template.method,
            url=sample_template.url
        )
        
        # Update template
        success = template_manager.update_template(
            sample_template.name,
            method="POST",
            url="https://api.example.com/updated"
        )
        
        assert success == True
        
        # Verify update
        updated_template = template_manager.load_template(sample_template.name)
        assert updated_template.method == "POST"
        assert updated_template.url == "https://api.example.com/updated"
    
    def test_update_template_not_found(self, template_manager):
        """Test updating non-existent template."""
        with pytest.raises(ValueError, match="not found"):
            template_manager.update_template("non-existent", method="POST")
    
    def test_delete_template_success(self, template_manager, sample_template):
        """Test successful template deletion."""
        # Save template first
        template_manager.save_template(
            name=sample_template.name,
            method=sample_template.method,
            url=sample_template.url
        )
        
        # Delete template
        success = template_manager.delete_template(sample_template.name)
        assert success == True
        
        # Verify deletion
        template = template_manager.load_template(sample_template.name)
        assert template is None
    
    def test_delete_template_not_found(self, template_manager):
        """Test deleting non-existent template."""
        success = template_manager.delete_template("non-existent")
        assert success == False
    
    def test_list_templates(self, template_manager):
        """Test listing templates."""
        # Save multiple templates
        templates = ["template1", "template2", "template3"]
        for name in templates:
            template_manager.save_template(
                name=name,
                method="GET",
                url=f"https://api.example.com/{name}"
            )
        
        # List templates
        template_list = template_manager.list_templates()
        
        assert len(template_list) == 3
        for name in templates:
            assert name in template_list
    
    def test_list_templates_with_tag_filter(self, template_manager):
        """Test listing templates with tag filter."""
        # Save templates with different tags
        template_manager.save_template(
            name="template1",
            method="GET",
            url="https://api.example.com/1",
            tags=["api", "v1"]
        )
        template_manager.save_template(
            name="template2",
            method="GET",
            url="https://api.example.com/2",
            tags=["api", "v2"]
        )
        template_manager.save_template(
            name="template3",
            method="GET",
            url="https://api.example.com/3",
            tags=["web"]
        )
        
        # Filter by tag
        api_templates = template_manager.list_templates(tag_filter="api")
        assert len(api_templates) == 2
        assert "template1" in api_templates
        assert "template2" in api_templates
        assert "template3" not in api_templates
    
    def test_template_exists(self, template_manager, sample_template):
        """Test template existence check."""
        # Template doesn't exist initially
        assert template_manager.template_exists(sample_template.name) == False
        
        # Save template
        template_manager.save_template(
            name=sample_template.name,
            method=sample_template.method,
            url=sample_template.url
        )
        
        # Template exists now
        assert template_manager.template_exists(sample_template.name) == True
    
    def test_search_templates(self, template_manager):
        """Test template search functionality."""
        # Save templates with different content
        template_manager.save_template(
            name="user-api",
            method="GET",
            url="https://api.example.com/users",
            description="Get users from API"
        )
        template_manager.save_template(
            name="order-api",
            method="GET",
            url="https://api.example.com/orders",
            description="Get orders from API"
        )
        template_manager.save_template(
            name="web-scraper",
            method="GET",
            url="https://website.example.com",
            description="Scrape website data"
        )
        
        # Search by name
        results = template_manager.search_templates("user")
        assert "user-api" in results
        assert len(results) == 1
        
        # Search by URL
        results = template_manager.search_templates("api.example.com")
        assert "user-api" in results
        assert "order-api" in results
        assert "web-scraper" not in results
    
    def test_get_template_metadata(self, template_manager, sample_template):
        """Test getting template metadata."""
        # Save template
        template_manager.save_template(
            name=sample_template.name,
            method=sample_template.method,
            url=sample_template.url,
            description=sample_template.description,
            tags=sample_template.tags
        )
        
        # Get metadata
        metadata = template_manager.get_template_metadata(sample_template.name)
        
        assert metadata is not None
        assert metadata['name'] == sample_template.name
        assert metadata['method'] == sample_template.method
        assert metadata['url'] == sample_template.url
        assert metadata['description'] == sample_template.description
        assert metadata['tags'] == sample_template.tags
        assert 'created_at' in metadata
        assert 'usage_count' in metadata
    
    def test_update_template_usage(self, template_manager, sample_template):
        """Test updating template usage statistics."""
        # Save template
        template_manager.save_template(
            name=sample_template.name,
            method=sample_template.method,
            url=sample_template.url
        )
        
        # Update usage
        success = template_manager.update_template_usage(sample_template.name)
        assert success == True
        
        # Verify usage was updated
        template = template_manager.load_template(sample_template.name)
        assert template.usage_count == 1
    
    def test_get_template_statistics(self, template_manager):
        """Test getting template statistics."""
        # Save multiple templates with different usage
        for i in range(3):
            template_manager.save_template(
                name=f"template{i}",
                method="GET",
                url=f"https://api.example.com/{i}",
                tags=["api", f"v{i}"]
            )
            
            # Update usage for some templates
            for _ in range(i + 1):
                template_manager.update_template_usage(f"template{i}")
        
        # Get statistics
        stats = template_manager.get_template_statistics()
        
        assert stats['total_templates'] == 3
        assert stats['total_usage'] == 6  # 1 + 2 + 3
        assert stats['most_used'] == "template2"
        assert 'methods_distribution' in stats
        assert 'tags_distribution' in stats
    
    def test_validate_template_data(self, template_manager):
        """Test template data validation."""
        # Valid data
        is_valid, error = template_manager.validate_template_data(
            method="GET",
            url="https://api.example.com/users"
        )
        assert is_valid == True
        assert error is None
        
        # Invalid method
        is_valid, error = template_manager.validate_template_data(
            method="INVALID",
            url="https://api.example.com/users"
        )
        assert is_valid == False
        assert "Invalid HTTP method" in error
        
        # Invalid URL
        is_valid, error = template_manager.validate_template_data(
            method="GET",
            url="invalid-url"
        )
        assert is_valid == False
        assert "Invalid URL" in error


class TestEnvironmentManager:
    """Test cases for EnvironmentManager."""
    
    def test_init(self, mock_storage):
        """Test EnvironmentManager initialization."""
        manager = EnvironmentManager(mock_storage)
        assert manager.storage == mock_storage
        assert manager.env_storage is not None
    
    def test_create_environment_success(self, env_manager):
        """Test successful environment creation."""
        success = env_manager.create_environment(
            name="test-env",
            description="Test environment",
            variables={"API_KEY": "test-key"}
        )
        
        assert success == True
        assert env_manager.environment_exists("test-env") == True
    
    def test_create_environment_invalid_name(self, env_manager):
        """Test environment creation with invalid name."""
        with pytest.raises(ValueError, match="Environment name cannot be empty"):
            env_manager.create_environment(name="")
        
        with pytest.raises(ValueError, match="Invalid environment name"):
            env_manager.create_environment(name="test/env")  # Invalid character
    
    def test_create_environment_duplicate(self, env_manager):
        """Test environment creation with duplicate name."""
        env_manager.create_environment("duplicate-env")
        
        with pytest.raises(ValueError, match="already exists"):
            env_manager.create_environment("duplicate-env")
    
    def test_delete_environment_success(self, env_manager):
        """Test successful environment deletion."""
        env_manager.create_environment("delete-me")
        env_manager.create_environment("keep-me")
        env_manager.switch_environment("keep-me")
        
        success = env_manager.delete_environment("delete-me")
        assert success == True
        assert env_manager.environment_exists("delete-me") == False
    
    def test_delete_current_environment_fails(self, env_manager):
        """Test that deleting current environment fails."""
        env_manager.create_environment("current-env")
        env_manager.switch_environment("current-env")
        
        with pytest.raises(ValueError, match="Cannot delete current environment"):
            env_manager.delete_environment("current-env")
    
    def test_set_and_get_variable(self, env_manager):
        """Test setting and getting environment variables."""
        env_manager.create_environment("test-env")
        
        success = env_manager.set_variable("test-env", "API_KEY", "secret123")
        assert success == True
        
        value = env_manager.get_variable("test-env", "API_KEY")
        assert value == "secret123"
    
    def test_get_variable_with_default(self, env_manager):
        """Test getting variable with default value."""
        env_manager.create_environment("test-env")
        
        value = env_manager.get_variable("test-env", "NONEXISTENT", "default")
        assert value == "default"
    
    def test_delete_variable(self, env_manager):
        """Test deleting environment variable."""
        env_manager.create_environment("test-env")
        env_manager.set_variable("test-env", "DELETE_ME", "value")
        
        success = env_manager.delete_variable("test-env", "DELETE_ME")
        assert success == True
        
        value = env_manager.get_variable("test-env", "DELETE_ME")
        assert value is None
    
    def test_list_variables(self, env_manager):
        """Test listing environment variables."""
        env_manager.create_environment("test-env")
        env_manager.set_variable("test-env", "VAR1", "value1")
        env_manager.set_variable("test-env", "VAR2", "value2")
        
        variables = env_manager.list_variables("test-env")
        assert len(variables) == 2
        assert variables["VAR1"] == "value1"
        assert variables["VAR2"] == "value2"
    
    def test_switch_environment(self, env_manager):
        """Test switching between environments."""
        env_manager.create_environment("env1")
        env_manager.create_environment("env2")
        
        success = env_manager.switch_environment("env1")
        assert success == True
        assert env_manager.get_current_environment() == "env1"
        
        success = env_manager.switch_environment("env2")
        assert success == True
        assert env_manager.get_current_environment() == "env2"
    
    def test_switch_to_nonexistent_environment(self, env_manager):
        """Test switching to non-existent environment."""
        with pytest.raises(ValueError, match="not found"):
            env_manager.switch_environment("nonexistent")
    
    def test_list_environments(self, env_manager):
        """Test listing all environments."""
        env_manager.create_environment("env1")
        env_manager.create_environment("env2")
        env_manager.create_environment("env3")
        
        environments = env_manager.list_environments()
        assert len(environments) == 3
        assert "env1" in environments
        assert "env2" in environments
        assert "env3" in environments
    
    def test_get_environment_info(self, env_manager):
        """Test getting environment information."""
        env_manager.create_environment("test-env", "Test description")
        
        info = env_manager.get_environment_info("test-env")
        assert info is not None
        assert info['name'] == "test-env"
        assert info['description'] == "Test description"
        assert info['variable_count'] == 0
        assert 'created_at' in info
        assert 'formatted_created' in info
    
    def test_copy_environment(self, env_manager):
        """Test copying environment."""
        env_manager.create_environment("source-env")
        env_manager.set_variable("source-env", "VAR1", "value1")
        env_manager.set_variable("source-env", "VAR2", "value2")
        
        success = env_manager.copy_environment("source-env", "target-env", "Copied env")
        assert success == True
        
        # Verify copy
        variables = env_manager.list_variables("target-env")
        assert len(variables) == 2
        assert variables["VAR1"] == "value1"
        assert variables["VAR2"] == "value2"
    
    def test_merge_environments(self, env_manager):
        """Test merging environments."""
        env_manager.create_environment("target-env")
        env_manager.set_variable("target-env", "EXISTING", "old_value")
        
        env_manager.create_environment("source-env")
        env_manager.set_variable("source-env", "NEW_VAR", "new_value")
        env_manager.set_variable("source-env", "EXISTING", "new_value")
        
        # Merge without overwrite
        success = env_manager.merge_environments("target-env", "source-env", overwrite=False)
        assert success == True
        
        variables = env_manager.list_variables("target-env")
        assert variables["NEW_VAR"] == "new_value"
        assert variables["EXISTING"] == "old_value"  # Should not be overwritten
        
        # Merge with overwrite
        success = env_manager.merge_environments("target-env", "source-env", overwrite=True)
        assert success == True
        
        variables = env_manager.list_variables("target-env")
        assert variables["EXISTING"] == "new_value"  # Should be overwritten
    
    def test_export_environment(self, env_manager):
        """Test exporting environment."""
        env_manager.create_environment("export-env", "Export test")
        env_manager.set_variable("export-env", "VAR1", "value1")
        
        export_data = env_manager.export_environment("export-env")
        
        assert export_data['name'] == "export-env"
        assert export_data['description'] == "Export test"
        assert export_data['variables']['VAR1'] == "value1"
        assert 'metadata' in export_data
    
    def test_import_environment(self, env_manager):
        """Test importing environment."""
        import_data = {
            'name': 'imported-env',
            'description': 'Imported environment',
            'variables': {
                'VAR1': 'value1',
                'VAR2': 'value2'
            }
        }
        
        success = env_manager.import_environment(import_data)
        assert success == True
        
        # Verify import
        assert env_manager.environment_exists("imported-env") == True
        variables = env_manager.list_variables("imported-env")
        assert len(variables) == 2
        assert variables["VAR1"] == "value1"
    
    def test_get_environment_statistics(self, env_manager):
        """Test getting environment statistics."""
        env_manager.create_environment("env1")
        env_manager.set_variable("env1", "VAR1", "value1")
        env_manager.set_variable("env1", "VAR2", "value2")
        
        env_manager.create_environment("env2")
        env_manager.set_variable("env2", "VAR1", "value1")
        
        stats = env_manager.get_environment_statistics()
        
        assert stats['total_environments'] == 2
        assert stats['total_variables'] == 3
        assert stats['average_variables'] == 1.5
        assert 'most_variables' in stats
        assert 'recently_modified' in stats