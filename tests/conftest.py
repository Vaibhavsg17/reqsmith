"""
Pytest configuration and fixtures for ReqSmith tests.
"""
import pytest
import tempfile
import shutil
import os
import glob
from pathlib import Path
from unittest.mock import Mock, MagicMock

from src.reqsmith.storage import HybridStorage, RequestTemplate, Environment, RequestRecord
from src.reqsmith.core import HTTPClient, TemplateManager, EnvironmentManager, HistoryManager


@pytest.fixture(scope="function", autouse=True)
def cleanup_test_data():
    """Automatically cleanup test data before and after each test."""
    # Cleanup before test - ensure clean state
    test_storage_paths = []
    
    # Collect any existing test storage paths
    import glob
    import tempfile
    temp_base = tempfile.gettempdir()
    test_patterns = [
        os.path.join(temp_base, "tmp*reqsmith*"),
        os.path.join(temp_base, "tmp*test_user*"),
        os.path.join(temp_base, "tmp*storage*"),
        os.path.join(temp_base, "tmp*test_cache*"),
        os.path.join(temp_base, "tmp*test_templates*"),
        os.path.join(temp_base, "tmp*test_history*"),
    ]
    
    for pattern in test_patterns:
        test_storage_paths.extend(glob.glob(pattern))
    
    # Clean up any leftover test directories
    for path_str in test_storage_paths:
        try:
            path = Path(path_str)
            if path.exists() and path.is_dir() and "test" in str(path):
                shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass  # Ignore cleanup errors
    
    yield
    
    # Cleanup after test - additional safety cleanup
    for pattern in test_patterns:
        for path_str in glob.glob(pattern):
            try:
                path = Path(path_str)
                if path.exists() and path.is_dir() and "test" in str(path):
                    shutil.rmtree(path, ignore_errors=True)
            except Exception:
                pass


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests with enhanced cleanup."""
    import uuid
    temp_path = tempfile.mkdtemp(prefix="reqsmith_test_", suffix=f"_{uuid.uuid4().hex[:8]}")
    
    # Ensure directory is readable/writable
    os.chmod(temp_path, 0o755)
    
    yield temp_path
    
    # Enhanced cleanup with retry mechanism
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if os.path.exists(temp_path):
                # Change permissions to ensure deletion
                for root, dirs, files in os.walk(temp_path):
                    for d in dirs:
                        os.chmod(os.path.join(root, d), 0o755)
                    for f in files:
                        os.chmod(os.path.join(root, f), 0o644)
                shutil.rmtree(temp_path, ignore_errors=False)
                break
        except (OSError, PermissionError) as e:
            if attempt == max_retries - 1:
                # Final attempt - use ignore_errors
                shutil.rmtree(temp_path, ignore_errors=True)
            else:
                import time
                time.sleep(0.1)  # Brief delay before retry


@pytest.fixture
def mock_storage(temp_dir):
    """Create a mock HybridStorage instance with proper cleanup."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    storage = HybridStorage(f"test_user_{unique_id}", cache_size_mb=10)
    
    # Override storage path to use our controlled temp directory
    storage.disk_manager.user_storage_path = Path(temp_dir)
    storage.disk_manager.ensure_user_directory()
    
    yield storage
    
    # Comprehensive cleanup
    try:
        # Clear memory cache
        storage.memory_cache.clear()
        
        # Clear all categories from disk storage
        categories = ["templates", "environments", "history", "cache", "test"]
        for category in categories:
            try:
                storage.clear(category)
            except Exception:
                pass
                
        # Additional direct filesystem cleanup
        if storage.disk_manager.user_storage_path.exists():
            shutil.rmtree(storage.disk_manager.user_storage_path, ignore_errors=True)
            
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture
def template_manager(mock_storage):
    """Create a TemplateManager instance for testing with enhanced cleanup."""
    manager = TemplateManager(mock_storage)
    yield manager
    
    # Enhanced cleanup with error handling
    try:
        templates = manager.list_templates()
        for template_name in templates:
            try:
                manager.delete_template(template_name)
            except Exception:
                pass  # Continue cleaning other templates
    except Exception:
        pass  # Ignore errors during cleanup


@pytest.fixture
def env_manager(mock_storage):
    """Create an EnvironmentManager instance for testing with enhanced cleanup."""
    manager = EnvironmentManager(mock_storage)
    yield manager
    
    # Enhanced cleanup with error handling
    try:
        environments = manager.list_environments()
        for env_name in environments:
            if env_name != "default":  # Preserve default environment
                try:
                    manager.delete_environment(env_name)
                except Exception:
                    pass  # Continue cleaning other environments
        
        # Clear current environment safely
        try:
            manager._current_environment = None
        except Exception:
            pass
    except Exception:
        pass  # Ignore errors during cleanup


@pytest.fixture
def history_manager(mock_storage):
    """Create a HistoryManager instance for testing with enhanced cleanup."""
    manager = HistoryManager(mock_storage, max_entries=100)
    yield manager
    
    # Enhanced cleanup with error handling
    try:
        manager.clear_history()
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture
def http_client():
    """Create an HTTPClient instance for testing."""
    return HTTPClient(timeout=5, retry_attempts=1)


@pytest.fixture
def sample_template():
    """Create a sample RequestTemplate for testing."""
    return RequestTemplate(
        name="test-template",
        method="GET",
        url="https://api.example.com/users/${USER_ID}",
        headers={"Authorization": "Bearer ${API_TOKEN}"},
        body="",
        params={"limit": "10"},
        description="Test template",
        tags=["test", "api"]
    )


@pytest.fixture
def sample_environment():
    """Create a sample Environment for testing."""
    return Environment(
        name="test-env",
        variables={
            "API_TOKEN": "test-token-123",
            "USER_ID": "42",
            "BASE_URL": "https://api.example.com"
        },
        description="Test environment"
    )


@pytest.fixture
def sample_request_record():
    """Create a sample RequestRecord for testing."""
    import time
    return RequestRecord(
        timestamp=time.time(),
        method="GET",
        url="https://api.example.com/users/42",
        headers={"Authorization": "Bearer test-token"},
        body="",
        response_status=200,
        response_time=0.5,
        response_size=1024,
        template_name="test-template",
        environment="test-env"
    )


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""
    from src.reqsmith.core.http_client import Response
    
    return Response(
        status_code=200,
        headers={"Content-Type": "application/json"},
        content=b'{"id": 42, "name": "Test User"}',
        text='{"id": 42, "name": "Test User"}',
        url="https://api.example.com/users/42",
        method="GET",
        request_headers={"Authorization": "Bearer test-token"},
        request_body="",
        elapsed_time=0.5,
        size_bytes=32
    )


@pytest.fixture
def mock_gemini_client():
    """Create a mock Gemini client for AI testing."""
    from src.reqsmith.ai import ValidationResult
    
    mock_client = Mock()
    mock_client.is_available.return_value = True
    mock_client.generate_content.return_value = "Mock AI response"
    mock_client.validate_json.return_value = ValidationResult(
        is_valid=True,
        suggestions=[],
        explanation="Valid JSON"
    )
    mock_client.analyze_api_endpoint.return_value = {
        'suggested_headers': {'Content-Type': 'application/json'},
        'analysis': 'Mock analysis'
    }
    return mock_client