"""
Unit tests for response formatters.
"""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from rich.console import Console

from src.reqsmith.formatters import ResponseFormatter, TableFormatter, ResponseSaver
from src.reqsmith.core.http_client import Response


class TestResponseFormatter:
    """Test cases for ResponseFormatter."""
    
    def test_init(self):
        """Test ResponseFormatter initialization."""
        console = Console()
        formatter = ResponseFormatter(console)
        assert formatter.console == console
    
    def test_init_without_console(self):
        """Test ResponseFormatter initialization without console."""
        formatter = ResponseFormatter()
        assert formatter.console is not None
    
    def test_colorize_status_success(self):
        """Test status colorization for success codes."""
        formatter = ResponseFormatter()
        
        # 2xx codes should be green
        status_text = formatter.colorize_status(200)
        assert hasattr(status_text, 'style')
        assert "green" in str(status_text.style)
        
        status_text = formatter.colorize_status(201)
        assert "green" in str(status_text.style)
    
    def test_colorize_status_redirect(self):
        """Test status colorization for redirect codes."""
        formatter = ResponseFormatter()
        
        # 3xx codes should be cyan
        status_text = formatter.colorize_status(301)
        assert hasattr(status_text, 'style')
        assert "cyan" in str(status_text.style)
        
        status_text = formatter.colorize_status(302)
        assert "cyan" in str(status_text.style)
    
    def test_colorize_status_client_error(self):
        """Test status colorization for client error codes."""
        formatter = ResponseFormatter()
        
        # 4xx codes should be yellow
        status_text = formatter.colorize_status(400)
        assert hasattr(status_text, 'style')
        assert "yellow" in str(status_text.style)
        
        status_text = formatter.colorize_status(404)
        assert "yellow" in str(status_text.style)
    
    def test_colorize_status_server_error(self):
        """Test status colorization for server error codes."""
        formatter = ResponseFormatter()
        
        # 5xx codes should be red
        status_text = formatter.colorize_status(500)
        assert hasattr(status_text, 'style')
        assert "red" in str(status_text.style)
        
        status_text = formatter.colorize_status(502)
        assert "red" in str(status_text.style)
    
    def test_pretty_print_json_valid(self):
        """Test JSON pretty printing with valid JSON."""
        formatter = ResponseFormatter()
        
        json_str = '{"name": "test", "value": 123}'
        
        with patch.object(formatter.console, 'print') as mock_print:
            formatter.pretty_print_json(json_str)
            mock_print.assert_called_once()
    
    def test_pretty_print_json_invalid(self):
        """Test JSON pretty printing with invalid JSON."""
        formatter = ResponseFormatter()
        
        invalid_json = '{"name": "test", "value": }'
        
        with patch.object(formatter.console, 'print') as mock_print:
            formatter.pretty_print_json(invalid_json)
            mock_print.assert_called_once()
            # Should print error message
            call_args = mock_print.call_args[0][0]
            assert "Invalid JSON" in str(call_args)
    
    def test_pretty_print_xml(self):
        """Test XML pretty printing."""
        formatter = ResponseFormatter()
        
        xml_str = '<?xml version="1.0"?><root><item>test</item></root>'
        
        with patch.object(formatter.console, 'print') as mock_print:
            formatter.pretty_print_xml(xml_str)
            mock_print.assert_called_once()
    
    def test_format_headers(self):
        """Test header formatting."""
        formatter = ResponseFormatter()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token"
        }
        
        with patch.object(formatter.console, 'print') as mock_print:
            formatter.format_headers(headers)
            mock_print.assert_called_once()
    
    def test_detect_response_format_json(self):
        """Test response format detection for JSON."""
        formatter = ResponseFormatter()
        
        response = Mock()
        response.headers = {"Content-Type": "application/json"}
        response.text = '{"test": true}'
        
        format_type = formatter._detect_response_format(response)
        assert format_type == "json"
    
    def test_detect_response_format_xml(self):
        """Test response format detection for XML."""
        formatter = ResponseFormatter()
        
        response = Mock()
        response.headers = {"Content-Type": "application/xml"}
        response.text = '<?xml version="1.0"?><root></root>'
        
        format_type = formatter._detect_response_format(response)
        assert format_type == "xml"
    
    def test_detect_response_format_auto_json(self):
        """Test automatic format detection for JSON content."""
        formatter = ResponseFormatter()
        
        response = Mock()
        response.headers = {}
        response.text = '{"test": true}'
        
        format_type = formatter._detect_response_format(response)
        assert format_type == "json"


class TestTableFormatter:
    """Test cases for TableFormatter."""
    
    def test_init(self):
        """Test TableFormatter initialization."""
        console = Console()
        formatter = TableFormatter(console, max_rows=50)
        assert formatter.console == console
        assert formatter.max_rows == 50
    
    def test_detect_table_structure_valid(self):
        """Test table structure detection with valid data."""
        formatter = TableFormatter()
        
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"}
        ]
        
        assert formatter.detect_table_structure(data) == True
    
    def test_detect_table_structure_invalid_not_list(self):
        """Test table structure detection with non-list data."""
        formatter = TableFormatter()
        
        data = {"id": 1, "name": "Alice"}
        
        assert formatter.detect_table_structure(data) == False
    
    def test_detect_table_structure_invalid_empty(self):
        """Test table structure detection with empty list."""
        formatter = TableFormatter()
        
        data = []
        
        assert formatter.detect_table_structure(data) == False
    
    def test_detect_table_structure_invalid_not_dicts(self):
        """Test table structure detection with non-dict items."""
        formatter = TableFormatter()
        
        data = ["item1", "item2", "item3"]
        
        assert formatter.detect_table_structure(data) == False
    
    def test_format_as_table_valid_data(self):
        """Test table formatting with valid data."""
        formatter = TableFormatter()
        
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"}
        ]
        
        with patch.object(formatter.console, 'print') as mock_print:
            formatter.format_as_table(data)
            mock_print.assert_called()
    
    def test_format_as_table_json_string(self):
        """Test table formatting with JSON string input."""
        formatter = TableFormatter()
        
        json_data = '[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]'
        
        with patch.object(formatter.console, 'print') as mock_print:
            formatter.format_as_table(json_data)
            mock_print.assert_called()
    
    def test_format_as_table_invalid_json(self):
        """Test table formatting with invalid JSON string."""
        formatter = TableFormatter()
        
        invalid_json = '{"invalid": json}'
        
        with patch.object(formatter.console, 'print') as mock_print:
            formatter.format_as_table(invalid_json)
            mock_print.assert_called()
            # Should print error message
            call_args = str(mock_print.call_args_list)
            assert "Invalid JSON" in call_args
    
    def test_determine_columns(self):
        """Test column determination logic."""
        formatter = TableFormatter()
        
        data = [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
            {"id": 3, "name": "Charlie"}  # Missing email
        ]
        
        columns = formatter._determine_columns(data)
        
        # Should include columns that appear in most items
        assert "id" in columns
        assert "name" in columns
        assert "email" in columns
    
    def test_format_cell_value_string(self):
        """Test cell value formatting for strings."""
        formatter = TableFormatter()
        
        # Normal string
        assert formatter._format_cell_value("test") == "test"
        
        # Long string (should be truncated)
        long_string = "x" * 100
        result = formatter._format_cell_value(long_string)
        assert len(result) <= 50
        assert "..." in result
    
    def test_format_cell_value_special_types(self):
        """Test cell value formatting for special types."""
        formatter = TableFormatter()
        
        # None
        result = formatter._format_cell_value(None)
        assert "null" in result
        
        # Boolean
        assert "true" in formatter._format_cell_value(True)
        assert "false" in formatter._format_cell_value(False)
        
        # Number
        assert formatter._format_cell_value(123) == "123"
        assert formatter._format_cell_value(3.14) == "3.14"


class TestResponseSaver:
    """Test cases for ResponseSaver."""
    
    def test_init(self, temp_dir):
        """Test ResponseSaver initialization."""
        saver = ResponseSaver(temp_dir)
        assert str(saver.default_directory) == temp_dir
    
    def test_save_response_full(self, temp_dir, mock_response):
        """Test saving full response."""
        saver = ResponseSaver(temp_dir)
        
        file_path = saver.save_response(mock_response, format_type="full")
        
        # Check that file was created
        assert Path(file_path).exists()
        
        # Check file content
        with open(file_path, 'r') as f:
            content = f.read()
            assert "REQUEST" in content
            assert "RESPONSE" in content
            assert mock_response.method in content
            assert mock_response.url in content
    
    def test_save_response_body_only(self, temp_dir, mock_response):
        """Test saving response body only."""
        saver = ResponseSaver(temp_dir)
        
        file_path = saver.save_response(mock_response, format_type="body")
        
        # Check that file was created
        assert Path(file_path).exists()
        
        # Check file content
        with open(file_path, 'r') as f:
            content = f.read()
            assert content == mock_response.text
    
    def test_save_response_json(self, temp_dir, mock_response):
        """Test saving response as JSON."""
        saver = ResponseSaver(temp_dir)
        
        file_path = saver.save_response_json(mock_response)
        
        # Check that file was created
        assert Path(file_path).exists()
        assert file_path.endswith('.json')
        
        # Check file content is valid JSON
        with open(file_path, 'r') as f:
            import json
            data = json.load(f)
            assert 'request' in data
            assert 'response' in data
            assert 'metadata' in data
    
    def test_save_multiple_responses(self, temp_dir):
        """Test saving multiple responses."""
        saver = ResponseSaver(temp_dir)
        
        responses = []
        for i in range(3):
            response = Mock()
            response.method = "GET"
            response.url = f"https://api.example.com/{i}"
            response.status_code = 200
            response.headers = {"Content-Type": "application/json"}  # Proper dict instead of Mock
            response.text = '{"data": "test"}'
            response.content = b'{"data": "test"}'
            response.request_headers = {"User-Agent": "test"}  # Proper dict
            response.request_body = ""
            response.elapsed_time = 0.5
            response.size_bytes = 100
            responses.append(response)
        
        saved_files = saver.save_multiple_responses(responses)
        
        assert len(saved_files) == 3
        for file_path in saved_files:
            assert Path(file_path).exists()
    
    def test_generate_filename(self, temp_dir, mock_response):
        """Test automatic filename generation."""
        saver = ResponseSaver(temp_dir)
        
        filename = saver._generate_filename(mock_response)
        
        # Should contain method and status code
        assert mock_response.method.lower() in filename
        assert str(mock_response.status_code) in filename
        assert filename.endswith('.txt')
    
    def test_get_extension_from_content_type(self, temp_dir):
        """Test file extension detection from content type."""
        saver = ResponseSaver(temp_dir)
        
        assert saver._get_extension_from_content_type("application/json") == ".json"
        assert saver._get_extension_from_content_type("application/xml") == ".xml"
        assert saver._get_extension_from_content_type("text/html") == ".html"
        assert saver._get_extension_from_content_type("image/png") == ".png"
        assert saver._get_extension_from_content_type("unknown/type") == ".bin"