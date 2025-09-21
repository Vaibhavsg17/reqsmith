"""
Unit tests for HistoryManager.
"""
import pytest
from unittest.mock import Mock, patch
import time
from datetime import datetime, timedelta

from src.reqsmith.core.history_manager import HistoryManager
from src.reqsmith.storage import RequestRecord
from src.reqsmith.core.http_client import Response


class TestHistoryManager:
    """Test cases for HistoryManager."""
    
    def test_init(self, mock_storage):
        """Test HistoryManager initialization."""
        manager = HistoryManager(mock_storage, max_entries=500)
        assert manager.storage == mock_storage
        assert manager.max_entries == 500
        assert manager.history_storage is not None
    
    def test_add_request_success(self, history_manager, mock_response):
        """Test successful request addition to history."""
        success = history_manager.add_request(
            mock_response,
            template_name="test-template",
            environment="test-env"
        )
        
        assert success == True
    
    def test_add_request_with_cache_flag(self, history_manager, mock_response):
        """Test adding cached request to history."""
        success = history_manager.add_request(
            mock_response,
            cached=True
        )
        
        assert success == True
    
    def test_get_history_all(self, history_manager):
        """Test getting all history entries."""
        # Add multiple requests
        for i in range(3):
            response = Mock()
            response.method = "GET"
            response.url = f"https://api.example.com/{i}"
            response.status_code = 200
            response.request_headers = {}
            response.request_body = ""
            response.elapsed_time = 0.5
            response.size_bytes = 100
            
            history_manager.add_request(response)
        
        history = history_manager.get_history()
        assert len(history) == 3
    
    def test_get_history_with_limit(self, history_manager):
        """Test getting history with limit."""
        # Add multiple requests
        for i in range(5):
            response = Mock()
            response.method = "GET"
            response.url = f"https://api.example.com/{i}"
            response.status_code = 200
            response.request_headers = {}
            response.request_body = ""
            response.elapsed_time = 0.5
            response.size_bytes = 100
            
            history_manager.add_request(response)
        
        history = history_manager.get_history(limit=3)
        assert len(history) == 3
    
    def test_get_history_with_method_filter(self, history_manager):
        """Test getting history with method filter."""
        # Add requests with different methods
        methods = ["GET", "POST", "GET", "PUT", "GET"]
        for i, method in enumerate(methods):
            response = Mock()
            response.method = method
            response.url = f"https://api.example.com/{i}"
            response.status_code = 200
            response.request_headers = {}
            response.request_body = ""
            response.elapsed_time = 0.5
            response.size_bytes = 100
            
            history_manager.add_request(response)
        
        get_history = history_manager.get_history(method_filter="GET")
        assert len(get_history) == 3
        for record in get_history:
            assert record.method == "GET"
    
    def test_get_history_with_status_filter(self, history_manager):
        """Test getting history with status filter."""
        # Add requests with different status codes
        statuses = [200, 404, 200, 500, 200]
        for i, status in enumerate(statuses):
            response = Mock()
            response.method = "GET"
            response.url = f"https://api.example.com/{i}"
            response.status_code = status
            response.request_headers = {}
            response.request_body = ""
            response.elapsed_time = 0.5
            response.size_bytes = 100
            
            history_manager.add_request(response)
        
        success_history = history_manager.get_history(status_filter=200)
        assert len(success_history) == 3
        for record in success_history:
            assert record.response_status == 200
    
    def test_get_history_with_url_pattern(self, history_manager):
        """Test getting history with URL pattern filter."""
        urls = [
            "https://api.example.com/users",
            "https://api.example.com/orders",
            "https://api.example.com/users/123",
            "https://different.com/api"
        ]
        
        for url in urls:
            response = Mock()
            response.method = "GET"
            response.url = url
            response.status_code = 200
            response.request_headers = {}
            response.request_body = ""
            response.elapsed_time = 0.5
            response.size_bytes = 100
            
            history_manager.add_request(response)
        
        user_history = history_manager.get_history(url_pattern="users")
        assert len(user_history) == 2
        for record in user_history:
            assert "users" in record.url
    
    def test_get_last_request(self, history_manager, mock_response):
        """Test getting the last request."""
        # Initially no history
        last_request = history_manager.get_last_request()
        assert last_request is None
        
        # Add a request
        history_manager.add_request(mock_response)
        
        last_request = history_manager.get_last_request()
        assert last_request is not None
        assert last_request.url == mock_response.url
    
    def test_get_request_by_index(self, history_manager):
        """Test getting request by index."""
        # Add multiple requests
        urls = ["url1", "url2", "url3"]
        for url in urls:
            response = Mock()
            response.method = "GET"
            response.url = url
            response.status_code = 200
            response.request_headers = {}
            response.request_body = ""
            response.elapsed_time = 0.5
            response.size_bytes = 100
            
            history_manager.add_request(response)
        
        # Get by index (0 = most recent)
        request_0 = history_manager.get_request_by_index(0)
        assert request_0.url == "url3"  # Most recent
        
        request_1 = history_manager.get_request_by_index(1)
        assert request_1.url == "url2"
        
        request_2 = history_manager.get_request_by_index(2)
        assert request_2.url == "url1"  # Oldest
        
        # Invalid index
        invalid_request = history_manager.get_request_by_index(10)
        assert invalid_request is None
    
    def test_search_history(self, history_manager):
        """Test searching history."""
        # Add requests with different characteristics
        requests_data = [
            ("GET", "https://api.example.com/users", "user-template", "dev"),
            ("POST", "https://api.example.com/orders", "order-template", "prod"),
            ("GET", "https://api.example.com/products", "product-template", "dev"),
            ("DELETE", "https://api.example.com/users/123", None, "test")
        ]
        
        for method, url, template, env in requests_data:
            response = Mock()
            response.method = method
            response.url = url
            response.status_code = 200
            response.request_headers = {}
            response.request_body = ""
            response.elapsed_time = 0.5
            response.size_bytes = 100
            
            history_manager.add_request(response, template_name=template, environment=env)
        
        # Search by URL
        user_results = history_manager.search_history("users")
        assert len(user_results) == 2
        
        # Search by method
        get_results = history_manager.search_history("GET")
        assert len(get_results) == 2
        
        # Search by template
        template_results = history_manager.search_history("user-template")
        assert len(template_results) == 1
        
        # Search by environment
        dev_results = history_manager.search_history("dev")
        assert len(dev_results) == 2
    
    def test_clear_history(self, history_manager, mock_response):
        """Test clearing history."""
        # Add some requests
        for i in range(3):
            history_manager.add_request(mock_response)
        
        # Verify history exists
        history = history_manager.get_history()
        assert len(history) == 3
        
        # Clear history
        success = history_manager.clear_history()
        assert success == True
        
        # Verify history is empty
        history = history_manager.get_history()
        assert len(history) == 0
    
    def test_delete_history_entries(self, history_manager):
        """Test deleting specific history entries."""
        # Add multiple requests
        for i in range(5):
            response = Mock()
            response.method = "GET"
            response.url = f"https://api.example.com/{i}"
            response.status_code = 200
            response.request_headers = {}
            response.request_body = ""
            response.elapsed_time = 0.5
            response.size_bytes = 100
            
            history_manager.add_request(response)
        
        # Delete entries at indices 0 and 2 (most recent and third most recent)
        deleted_count = history_manager.delete_history_entries([0, 2])
        assert deleted_count == 2
        
        # Verify remaining entries
        remaining_history = history_manager.get_history()
        assert len(remaining_history) == 3
    
    def test_get_history_statistics(self, history_manager):
        """Test getting history statistics."""
        # Add requests with different characteristics
        statuses = [200, 200, 404, 500, 200]
        methods = ["GET", "POST", "GET", "GET", "PUT"]
        
        for i, (status, method) in enumerate(zip(statuses, methods)):
            response = Mock()
            response.method = method
            response.url = f"https://api.example.com/{i}"
            response.status_code = status
            response.request_headers = {}
            response.request_body = ""
            response.elapsed_time = 0.5 + (i * 0.1)
            response.size_bytes = 100
            
            history_manager.add_request(response)
        
        stats = history_manager.get_history_statistics()
        
        assert 'total_requests' in stats
        assert 'successful_requests' in stats
        assert 'failed_requests' in stats
        assert 'method_distribution' in stats
        assert 'status_distribution' in stats
    
    def test_get_history_summary(self, history_manager):
        """Test getting history summary."""
        # Add some recent requests
        for i in range(3):
            response = Mock()
            response.method = "GET"
            response.url = f"https://api.example.com/{i}"
            response.status_code = 200 if i < 2 else 404
            response.request_headers = {}
            response.request_body = ""
            response.elapsed_time = 0.5
            response.size_bytes = 100
            
            history_manager.add_request(response)
        
        summary = history_manager.get_history_summary(days=7)
        
        assert summary['period_days'] == 7
        assert summary['total_requests'] == 3
        assert summary['successful_requests'] == 2
        assert summary['failed_requests'] == 1
        assert 'success_rate' in summary
        assert 'average_response_time' in summary
        assert 'most_used_methods' in summary
    
    def test_export_history_json(self, history_manager, temp_dir, mock_response):
        """Test exporting history to JSON."""
        import json
        from pathlib import Path
        
        # Add some requests
        for i in range(2):
            history_manager.add_request(mock_response)
        
        export_path = Path(temp_dir) / "history_export.json"
        success = history_manager.export_history(str(export_path), format_type="json")
        
        assert success == True
        assert export_path.exists()
        
        # Verify export content
        with open(export_path, 'r') as f:
            data = json.load(f)
            assert 'exported_at' in data
            assert 'total_records' in data
            assert 'records' in data
            assert len(data['records']) == 2
    
    def test_export_history_csv(self, history_manager, temp_dir, mock_response):
        """Test exporting history to CSV."""
        import csv
        from pathlib import Path
        
        # Add some requests
        for i in range(2):
            history_manager.add_request(mock_response)
        
        export_path = Path(temp_dir) / "history_export.csv"
        success = history_manager.export_history(str(export_path), format_type="csv")
        
        assert success == True
        assert export_path.exists()
        
        # Verify CSV content
        with open(export_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) == 3  # Header + 2 data rows
            assert 'Timestamp' in rows[0]  # Header row
    
    def test_set_max_entries(self, history_manager):
        """Test setting maximum entries limit."""
        # Add more requests than the new limit
        for i in range(10):
            response = Mock()
            response.method = "GET"
            response.url = f"https://api.example.com/{i}"
            response.status_code = 200
            response.request_headers = {}
            response.request_body = ""
            response.elapsed_time = 0.5
            response.size_bytes = 100
            
            history_manager.add_request(response)
        
        # Set lower limit
        success = history_manager.set_max_entries(5)
        assert success == True
        assert history_manager.get_max_entries() == 5
        
        # Verify history was trimmed
        history = history_manager.get_history()
        assert len(history) <= 5
    
    def test_set_max_entries_invalid(self, history_manager):
        """Test setting invalid maximum entries."""
        with pytest.raises(ValueError, match="Max entries must be positive"):
            history_manager.set_max_entries(0)
        
        with pytest.raises(ValueError, match="Max entries must be positive"):
            history_manager.set_max_entries(-1)
    
    def test_history_with_date_filters(self, history_manager):
        """Test history filtering by date range."""
        # Create requests with different timestamps
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        timestamps = [week_ago, yesterday, now]
        
        for i, timestamp in enumerate(timestamps):
            response = Mock()
            response.method = "GET"
            response.url = f"https://api.example.com/{i}"
            response.status_code = 200
            response.request_headers = {}
            response.request_body = ""
            response.elapsed_time = 0.5
            response.size_bytes = 100
            
            # Mock the timestamp
            with patch('time.time', return_value=timestamp.timestamp()):
                history_manager.add_request(response)
        
        # Filter by date range
        recent_history = history_manager.get_history(
            date_from=yesterday - timedelta(hours=1),
            date_to=now + timedelta(hours=1)
        )
        
        # Should get yesterday and today's requests
        assert len(recent_history) == 2