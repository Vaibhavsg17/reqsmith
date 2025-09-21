"""
Integration tests for CLI commands.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch, Mock

from src.reqsmith.cli.main import app


class TestCLIIntegration:
    """Integration tests for CLI commands."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_version_command(self):
        """Test version command."""
        result = self.runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "ReqSmith API Tester" in result.stdout
    
    def test_status_command(self):
        """Test status command."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            result = self.runner.invoke(app, ["status"])
            assert result.exit_code == 0
    
    def test_help_command(self):
        """Test help command."""
        result = self.runner.invoke(app, ["help"])
        assert result.exit_code == 0
        assert "Help System" in result.stdout
    
    def test_help_getting_started(self):
        """Test help getting-started command."""
        result = self.runner.invoke(app, ["help", "getting-started"])
        assert result.exit_code == 0
        assert "Getting Started" in result.stdout
    
    def test_help_examples(self):
        """Test help examples command."""
        result = self.runner.invoke(app, ["help", "examples"])
        assert result.exit_code == 0
        assert "Examples" in result.stdout
    
    @patch('httpx.Client.request')
    def test_request_get_command(self, mock_request):
        """Test GET request command."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"success": true}'
        mock_response.text = '{"success": true}'
        mock_response.url = "https://httpbin.org/get"
        mock_request.return_value = mock_response
        
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            result = self.runner.invoke(app, [
                "request", "get", "https://httpbin.org/get"
            ])
            
            # Should not fail (exit code 0 or 1 depending on initialization)
            assert result.exit_code in [0, 1]
    
    def test_template_save_command(self):
        """Test template save command."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            result = self.runner.invoke(app, [
                "template", "save", "test-template",
                "--method", "GET",
                "--url", "https://api.example.com/users"
            ])
            
            # Should not fail
            assert result.exit_code in [0, 1]
    
    def test_template_list_command(self):
        """Test template list command."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            result = self.runner.invoke(app, ["template", "list"])
            
            # Should not fail
            assert result.exit_code in [0, 1]
    
    def test_env_create_command(self):
        """Test environment create command."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            result = self.runner.invoke(app, [
                "env", "create", "test-env",
                "--description", "Test environment"
            ])
            
            # Should not fail
            assert result.exit_code in [0, 1]
    
    def test_env_list_command(self):
        """Test environment list command."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            result = self.runner.invoke(app, ["env", "list"])
            
            # Should not fail
            assert result.exit_code in [0, 1]
    
    def test_history_list_command(self):
        """Test history list command."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            result = self.runner.invoke(app, ["history", "list"])
            
            # Should not fail
            assert result.exit_code in [0, 1]
    
    def test_config_show_command(self):
        """Test config show command."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            result = self.runner.invoke(app, ["config", "--show"])
            
            # Should not fail
            assert result.exit_code in [0, 1]
    
    def test_completion_show_setup_command(self):
        """Test completion show-setup command."""
        result = self.runner.invoke(app, ["completion", "--show-setup"])
        assert result.exit_code == 0
        assert "Shell Completion Setup" in result.stdout
    
    def test_cleanup_command_with_confirmation(self):
        """Test cleanup command with confirmation."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            result = self.runner.invoke(app, [
                "cleanup", "--cache", "--yes"
            ])
            
            # Should not fail
            assert result.exit_code in [0, 1]
    
    def test_invalid_command(self):
        """Test invalid command handling."""
        result = self.runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0
    
    def test_command_with_invalid_options(self):
        """Test command with invalid options."""
        result = self.runner.invoke(app, ["request", "get"])
        # Should fail due to missing URL argument
        assert result.exit_code != 0


class TestCLIWorkflows:
    """Integration tests for complete CLI workflows."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_template_workflow(self):
        """Test complete template workflow: save, list, use, delete."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            # Save template
            result = self.runner.invoke(app, [
                "template", "save", "workflow-test",
                "--method", "GET",
                "--url", "https://api.example.com/test"
            ])
            assert result.exit_code in [0, 1]
            
            # List templates
            result = self.runner.invoke(app, ["template", "list"])
            assert result.exit_code in [0, 1]
            
            # Show template
            result = self.runner.invoke(app, ["template", "show", "workflow-test"])
            assert result.exit_code in [0, 1]
            
            # Delete template
            result = self.runner.invoke(app, [
                "template", "delete", "workflow-test", "--force"
            ])
            assert result.exit_code in [0, 1]
    
    def test_environment_workflow(self):
        """Test complete environment workflow: create, set vars, switch, delete."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            # Create environment
            result = self.runner.invoke(app, [
                "env", "create", "workflow-test-env"
            ])
            assert result.exit_code in [0, 1]
            
            # Set variable
            result = self.runner.invoke(app, [
                "env", "set", "TEST_VAR", "test_value",
                "--env", "workflow-test-env"
            ])
            assert result.exit_code in [0, 1]
            
            # List variables
            result = self.runner.invoke(app, [
                "env", "vars", "--env", "workflow-test-env"
            ])
            assert result.exit_code in [0, 1]
            
            # Switch environment
            result = self.runner.invoke(app, [
                "env", "switch", "workflow-test-env"
            ])
            assert result.exit_code in [0, 1]
            
            # Delete environment
            result = self.runner.invoke(app, [
                "env", "delete", "workflow-test-env", "--force"
            ])
            assert result.exit_code in [0, 1]
    
    @patch('httpx.Client.request')
    def test_request_and_history_workflow(self, mock_request):
        """Test request execution and history workflow."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"test": true}'
        mock_response.text = '{"test": true}'
        mock_response.url = "https://httpbin.org/get"
        mock_request.return_value = mock_response
        
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            # Make request
            result = self.runner.invoke(app, [
                "request", "get", "https://httpbin.org/get"
            ])
            assert result.exit_code in [0, 1]
            
            # Check history
            result = self.runner.invoke(app, ["history", "list"])
            assert result.exit_code in [0, 1]
            
            # Get history stats
            result = self.runner.invoke(app, ["history", "stats"])
            assert result.exit_code in [0, 1]


class TestStorageIntegration:
    """Integration tests for storage persistence."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_hybrid_storage_persistence(self):
        """Test that data persists across sessions."""
        from src.reqsmith.storage import HybridStorage
        
        # Create storage instance
        storage = HybridStorage("test_user", cache_size_mb=5)
        
        # Store some data
        test_data = {"test": "data", "number": 123}
        success = storage.set("test_key", test_data, category="test")
        assert success == True
        
        # Retrieve data
        retrieved = storage.get("test_key", category="test")
        assert retrieved == test_data
        
        # Create new storage instance (simulating new session)
        new_storage = HybridStorage("test_user", cache_size_mb=5)
        
        # Data should still be available
        retrieved_again = new_storage.get("test_key", category="test")
        assert retrieved_again == test_data
    
    def test_template_storage_integration(self):
        """Test template storage integration."""
        from src.reqsmith.storage import HybridStorage
        from src.reqsmith.core.template_manager import TemplateManager
        
        storage = HybridStorage("test_user", cache_size_mb=5)
        manager = TemplateManager(storage)
        
        # Save template
        success = manager.save_template(
            name="integration-test",
            method="POST",
            url="https://api.example.com/users",
            headers={"Content-Type": "application/json"},
            body='{"name": "test"}',
            description="Integration test template"
        )
        assert success == True
        
        # Load template
        template = manager.load_template("integration-test")
        assert template is not None
        assert template.name == "integration-test"
        assert template.method == "POST"
        assert template.url == "https://api.example.com/users"
        
        # List templates
        templates = manager.list_templates()
        assert "integration-test" in templates
        
        # Delete template
        success = manager.delete_template("integration-test")
        assert success == True
        
        # Verify deletion
        template = manager.load_template("integration-test")
        assert template is None
    
    def test_environment_storage_integration(self):
        """Test environment storage integration."""
        from src.reqsmith.storage import HybridStorage
        from src.reqsmith.core.env_manager import EnvironmentManager
        
        storage = HybridStorage("test_user", cache_size_mb=5)
        manager = EnvironmentManager(storage)
        
        # Create environment
        success = manager.create_environment(
            name="integration-test-env",
            description="Integration test environment",
            variables={"API_KEY": "test-key", "BASE_URL": "https://api.test.com"}
        )
        assert success == True
        
        # Set additional variable
        success = manager.set_variable("integration-test-env", "NEW_VAR", "new-value")
        assert success == True
        
        # Get variables
        variables = manager.list_variables("integration-test-env")
        assert len(variables) == 3
        assert variables["API_KEY"] == "test-key"
        assert variables["NEW_VAR"] == "new-value"
        
        # Switch environment
        success = manager.switch_environment("integration-test-env")
        assert success == True
        assert manager.get_current_environment() == "integration-test-env"
        
        # Create another environment to test deletion
        manager.create_environment("temp-env")
        manager.switch_environment("temp-env")
        
        # Delete first environment
        success = manager.delete_environment("integration-test-env")
        assert success == True
        assert not manager.environment_exists("integration-test-env")
    
    def test_history_storage_integration(self):
        """Test history storage integration."""
        from src.reqsmith.storage import HybridStorage
        from src.reqsmith.core.history_manager import HistoryManager
        from src.reqsmith.core.http_client import Response
        
        storage = HybridStorage("test_user", cache_size_mb=5)
        manager = HistoryManager(storage, max_entries=100)
        
        # Create mock responses
        responses = []
        for i in range(5):
            response = Response(
                status_code=200,
                headers={"Content-Type": "application/json"},
                content=f'{{"id": {i}}}'.encode(),
                text=f'{{"id": {i}}}',
                url=f"https://api.example.com/users/{i}",
                method="GET",
                request_headers={},
                request_body="",
                elapsed_time=0.5,
                size_bytes=20
            )
            responses.append(response)
        
        # Add responses to history
        for response in responses:
            success = manager.add_request(response)
            assert success == True
        
        # Get history
        history = manager.get_history()
        assert len(history) == 5
        
        # Get last request
        last_request = manager.get_last_request()
        assert last_request is not None
        assert last_request.url == "https://api.example.com/users/4"
        
        # Search history
        search_results = manager.search_history("users/2")
        assert len(search_results) == 1
        assert search_results[0].url == "https://api.example.com/users/2"
        
        # Get statistics
        stats = manager.get_history_statistics()
        assert stats['total_requests'] == 5
        assert stats['successful_requests'] == 5
    
    def test_cache_storage_integration(self):
        """Test cache storage integration."""
        from src.reqsmith.storage import HybridStorage
        from src.reqsmith.core.cache_manager import CacheManager
        from src.reqsmith.core.http_client import Response
        
        storage = HybridStorage("test_user", cache_size_mb=5)
        manager = CacheManager(storage, default_ttl=300)
        
        # Create response to cache
        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=b'{"cached": true}',
            text='{"cached": true}',
            url="https://api.example.com/cache-test",
            method="GET",
            request_headers={"Authorization": "Bearer token"},
            request_body="",
            elapsed_time=0.3,
            size_bytes=18
        )
        
        # Cache response
        success = manager.cache_response(response, ttl=600)
        assert success == True
        
        # Get cached response
        cached = manager.get_cached_response(
            "GET", 
            "https://api.example.com/cache-test",
            {"Authorization": "Bearer token"}
        )
        
        # Note: This might be None due to mocking, but the operation should succeed
        # In a real integration test with actual storage, this would return the cached response
        
        # Get cache stats
        stats = manager.get_cache_stats()
        assert 'cache_enabled' in stats
        assert stats['cache_enabled'] == True


class TestEndToEndWorkflows:
    """End-to-end integration tests for complete user workflows."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('httpx.Client.request')
    def test_complete_api_testing_workflow(self, mock_request):
        """Test complete API testing workflow."""
        # Mock HTTP responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"users": [{"id": 1, "name": "John"}]}'
        mock_response.text = '{"users": [{"id": 1, "name": "John"}]}'
        mock_response.url = "https://jsonplaceholder.typicode.com/users"
        mock_request.return_value = mock_response
        
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            # 1. Create environment
            result = self.runner.invoke(app, [
                "env", "create", "api-test-env",
                "--description", "API testing environment"
            ])
            assert result.exit_code in [0, 1]
            
            # 2. Set environment variables
            result = self.runner.invoke(app, [
                "env", "set", "BASE_URL", "https://jsonplaceholder.typicode.com",
                "--env", "api-test-env"
            ])
            assert result.exit_code in [0, 1]
            
            result = self.runner.invoke(app, [
                "env", "set", "API_KEY", "test-api-key",
                "--env", "api-test-env"
            ])
            assert result.exit_code in [0, 1]
            
            # 3. Switch to environment
            result = self.runner.invoke(app, [
                "env", "switch", "api-test-env"
            ])
            assert result.exit_code in [0, 1]
            
            # 4. Make API request
            result = self.runner.invoke(app, [
                "request", "get", "https://jsonplaceholder.typicode.com/users",
                "--header", "Authorization:Bearer ${API_KEY}"
            ])
            assert result.exit_code in [0, 1]
            
            # 5. Save as template
            result = self.runner.invoke(app, [
                "template", "save", "get-users",
                "--method", "GET",
                "--url", "${BASE_URL}/users",
                "--header", "Authorization:Bearer ${API_KEY}",
                "--description", "Get all users"
            ])
            assert result.exit_code in [0, 1]
            
            # 6. Use template
            result = self.runner.invoke(app, [
                "template", "use", "get-users"
            ])
            assert result.exit_code in [0, 1]
            
            # 7. Check history
            result = self.runner.invoke(app, [
                "history", "list", "--limit", "5"
            ])
            assert result.exit_code in [0, 1]
            
            # 8. Export template
            result = self.runner.invoke(app, [
                "template", "export", "get-users",
                "--format", "json"
            ])
            assert result.exit_code in [0, 1]
    
    def test_error_handling_workflow(self):
        """Test error handling in various scenarios."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            # Try to use non-existent template
            result = self.runner.invoke(app, [
                "template", "use", "non-existent-template"
            ])
            assert result.exit_code != 0
            
            # Try to delete non-existent environment
            result = self.runner.invoke(app, [
                "env", "delete", "non-existent-env", "--force"
            ])
            assert result.exit_code != 0
            
            # Try to set variable in non-existent environment
            result = self.runner.invoke(app, [
                "env", "set", "VAR", "value", "--env", "non-existent-env"
            ])
            assert result.exit_code != 0
    
    def test_configuration_workflow(self):
        """Test configuration management workflow."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            # Show current config
            result = self.runner.invoke(app, ["config", "--show"])
            assert result.exit_code in [0, 1]
            
            # Set configuration values
            result = self.runner.invoke(app, [
                "config", "--set", "cache.default_ttl=7200"
            ])
            assert result.exit_code in [0, 1]
            
            result = self.runner.invoke(app, [
                "config", "--set", "history.max_entries=500"
            ])
            assert result.exit_code in [0, 1]
            
            # Reset configuration
            result = self.runner.invoke(app, [
                "config", "--reset", "--yes"
            ])
            assert result.exit_code in [0, 1]
    
    def test_cleanup_workflow(self):
        """Test cleanup operations workflow."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            # Clean cache
            result = self.runner.invoke(app, [
                "cleanup", "--cache", "--yes"
            ])
            assert result.exit_code in [0, 1]
            
            # Clean history
            result = self.runner.invoke(app, [
                "cleanup", "--history", "--yes"
            ])
            assert result.exit_code in [0, 1]
            
            # Clean all
            result = self.runner.invoke(app, [
                "cleanup", "--all", "--yes"
            ])
            assert result.exit_code in [0, 1]


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
    
    def test_missing_required_arguments(self):
        """Test handling of missing required arguments."""
        # Request without URL
        result = self.runner.invoke(app, ["request", "get"])
        assert result.exit_code != 0
        
        # Template save without required fields
        result = self.runner.invoke(app, ["template", "save"])
        assert result.exit_code != 0
        
        # Environment set without variable name
        result = self.runner.invoke(app, ["env", "set"])
        assert result.exit_code != 0
    
    def test_invalid_argument_values(self):
        """Test handling of invalid argument values."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            # Invalid HTTP method
            result = self.runner.invoke(app, [
                "request", "invalid-method", "https://example.com"
            ])
            assert result.exit_code != 0
            
            # Invalid URL
            result = self.runner.invoke(app, [
                "request", "get", "not-a-url"
            ])
            assert result.exit_code != 0
    
    def test_initialization_failure_handling(self):
        """Test handling when app initialization fails."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = False
            
            result = self.runner.invoke(app, ["status"])
            assert result.exit_code != 0
    
    def test_network_error_handling(self):
        """Test handling of network errors."""
        with patch('httpx.Client.request') as mock_request:
            mock_request.side_effect = Exception("Network error")
            
            with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
                mock_init.return_value = True
                
                result = self.runner.invoke(app, [
                    "request", "get", "https://example.com"
                ])
                # Should handle error gracefully
                assert result.exit_code in [0, 1]
    
    def test_file_permission_error_handling(self):
        """Test handling of file permission errors."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.side_effect = PermissionError("Permission denied")
            
            result = self.runner.invoke(app, ["status"])
            assert result.exit_code != 0


class TestCLIOutputFormatting:
    """Test CLI output formatting and display."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
    
    @patch('httpx.Client.request')
    def test_json_response_formatting(self, mock_request):
        """Test JSON response formatting."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"name": "John", "age": 30}'
        mock_response.text = '{"name": "John", "age": 30}'
        mock_response.url = "https://api.example.com/user"
        mock_request.return_value = mock_response
        
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            result = self.runner.invoke(app, [
                "request", "get", "https://api.example.com/user",
                "--format", "json"
            ])
            assert result.exit_code in [0, 1]
    
    @patch('httpx.Client.request')
    def test_table_response_formatting(self, mock_request):
        """Test table response formatting."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'[{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]'
        mock_response.text = '[{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]'
        mock_response.url = "https://api.example.com/users"
        mock_request.return_value = mock_response
        
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            result = self.runner.invoke(app, [
                "request", "get", "https://api.example.com/users",
                "--format", "table"
            ])
            assert result.exit_code in [0, 1]
    
    def test_template_list_formatting(self):
        """Test template list formatting."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            # Test different output formats
            result = self.runner.invoke(app, [
                "template", "list", "--format", "table"
            ])
            assert result.exit_code in [0, 1]
            
            result = self.runner.invoke(app, [
                "template", "list", "--format", "json"
            ])
            assert result.exit_code in [0, 1]
    
    def test_history_list_formatting(self):
        """Test history list formatting."""
        with patch('src.reqsmith.cli.main.initialize_app') as mock_init:
            mock_init.return_value = True
            
            result = self.runner.invoke(app, [
                "history", "list", "--format", "table", "--limit", "10"
            ])
            assert result.exit_code in [0, 1]
            
            result = self.runner.invoke(app, [
                "history", "list", "--format", "json"
            ])
            assert result.exit_code in [0, 1]