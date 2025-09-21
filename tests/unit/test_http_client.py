"""
Unit tests for HTTPClient.
"""
import pytest
from unittest.mock import Mock, patch
import httpx

from src.reqsmith.core.http_client import HTTPClient, FileHTTPClient, GraphQLClient, Response


class TestHTTPClient:
    """Test cases for HTTPClient."""
    
    def test_init(self):
        """Test HTTPClient initialization."""
        client = HTTPClient(timeout=30, retry_attempts=3)
        assert client.timeout == 30
        assert client.retry_attempts == 3
        assert client.default_headers == {}
    
    def test_init_with_default_headers(self):
        """Test HTTPClient initialization with default headers."""
        headers = {"User-Agent": "TestAgent"}
        client = HTTPClient(default_headers=headers)
        assert client.default_headers == headers
    
    @patch('httpx.Client.request')
    def test_send_request_success(self, mock_request):
        """Test successful HTTP request."""
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"success": true}'
        mock_response.text = '{"success": true}'
        mock_response.url = "https://api.example.com/test"
        mock_request.return_value = mock_response
        
        client = HTTPClient()
        response = client.send_request("GET", "https://api.example.com/test")
        
        assert isinstance(response, Response)
        assert response.status_code == 200
        assert response.text == '{"success": true}'
        assert response.method == "GET"
    
    @patch('httpx.Client.request')
    def test_send_request_with_headers(self, mock_request):
        """Test HTTP request with custom headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b''
        mock_response.text = ''
        mock_response.url = "https://api.example.com/test"
        mock_request.return_value = mock_response
        
        client = HTTPClient()
        headers = {"Authorization": "Bearer token"}
        response = client.send_request("GET", "https://api.example.com/test", headers=headers)
        
        # Verify headers were passed to httpx
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args[1]
        assert "Authorization" in call_kwargs["headers"]
    
    @patch('httpx.Client.request')
    def test_send_request_with_retry(self, mock_request):
        """Test HTTP request retry mechanism."""
        # First call fails, second succeeds
        mock_request.side_effect = [
            httpx.RequestError("Connection failed"),
            Mock(status_code=200, headers={}, content=b'', text='', url="test")
        ]
        
        client = HTTPClient(retry_attempts=2)
        response = client.send_request("GET", "https://api.example.com/test")
        
        assert mock_request.call_count == 2
        assert response.status_code == 200
    
    def test_validate_method(self):
        """Test HTTP method validation."""
        client = HTTPClient()
        
        assert client._validate_method("GET") == True
        assert client._validate_method("POST") == True
        assert client._validate_method("INVALID") == False
    
    def test_validate_url(self):
        """Test URL validation."""
        client = HTTPClient()
        
        assert client._validate_url("https://api.example.com") == True
        assert client._validate_url("http://localhost:8080") == True
        assert client._validate_url("invalid-url") == False
    
    def test_validate_request(self):
        """Test request validation."""
        client = HTTPClient()
        
        # Valid request
        assert client.validate_request("GET", "https://api.example.com") == True
        
        # Invalid method
        assert client.validate_request("INVALID", "https://api.example.com") == False
        
        # Invalid URL
        assert client.validate_request("GET", "invalid-url") == False
    
    def test_convenience_methods(self):
        """Test convenience methods (get, post, etc.)."""
        client = HTTPClient()
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = Mock()
            
            client.get("https://api.example.com")
            mock_send.assert_called_with("GET", "https://api.example.com", headers=None, params=None)
            
            client.post("https://api.example.com", body="test")
            mock_send.assert_called_with("POST", "https://api.example.com", headers=None, body="test", params=None, files=None)


class TestFileHTTPClient:
    """Test cases for FileHTTPClient."""
    
    def test_detect_content_type_json(self):
        """Test content type detection for JSON."""
        client = FileHTTPClient()
        
        content_type = client._detect_content_type("test.json", '{"key": "value"}')
        assert content_type == "application/json"
    
    def test_detect_content_type_xml(self):
        """Test content type detection for XML."""
        client = FileHTTPClient()
        
        content_type = client._detect_content_type("test.xml", '<?xml version="1.0"?><root></root>')
        assert content_type == "application/xml"
    
    @patch('builtins.open', create=True)
    def test_send_request_from_file(self, mock_open):
        """Test sending request with body from file."""
        mock_open.return_value.__enter__.return_value.read.return_value = '{"test": true}'
        
        client = FileHTTPClient()
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = Mock()
            
            client.send_request_from_file("POST", "https://api.example.com", "test.json")
            
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            assert args[0] == "POST"
            assert args[1] == "https://api.example.com"
            assert kwargs["body"] == '{"test": true}'


class TestGraphQLClient:
    """Test cases for GraphQLClient."""
    
    def test_init(self):
        """Test GraphQLClient initialization."""
        client = GraphQLClient("https://api.example.com/graphql")
        assert client.endpoint_url == "https://api.example.com/graphql"
        assert "application/json" in client.default_headers["Content-Type"]
    
    def test_validate_graphql_query_valid(self):
        """Test GraphQL query validation with valid query."""
        client = GraphQLClient("https://api.example.com/graphql")
        
        query = "query { user(id: 1) { name email } }"
        assert client._validate_graphql_query(query) == True
    
    def test_validate_graphql_query_invalid(self):
        """Test GraphQL query validation with invalid query."""
        client = GraphQLClient("https://api.example.com/graphql")
        
        # Missing closing brace
        query = "query { user(id: 1) { name email }"
        assert client._validate_graphql_query(query) == False
        
        # Empty query
        assert client._validate_graphql_query("") == False
    
    def test_query_method(self):
        """Test GraphQL query method."""
        client = GraphQLClient("https://api.example.com/graphql")
        
        with patch.object(client, 'send_graphql_query') as mock_send:
            mock_send.return_value = Mock()
            
            query = "query { users { id name } }"
            client.query(query)
            
            mock_send.assert_called_with("https://api.example.com/graphql", query, None, None)


class TestResponse:
    """Test cases for Response class."""
    
    def test_response_creation(self):
        """Test Response object creation."""
        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=b'{"test": true}',
            text='{"test": true}',
            url="https://api.example.com",
            method="GET",
            request_headers={},
            request_body="",
            elapsed_time=0.5,
            size_bytes=15
        )
        
        assert response.status_code == 200
        assert response.method == "GET"
        assert response.size_bytes == 15
    
    def test_response_json_parsing(self):
        """Test JSON parsing in Response."""
        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=b'{"test": true}',
            text='{"test": true}',
            url="https://api.example.com",
            method="GET",
            request_headers={},
            request_body="",
            elapsed_time=0.5,
            size_bytes=15
        )
        
        json_data = response.json()
        assert json_data == {"test": True}
    
    def test_response_json_parsing_invalid(self):
        """Test JSON parsing with invalid JSON."""
        response = Response(
            status_code=200,
            headers={},
            content=b'invalid json',
            text='invalid json',
            url="https://api.example.com",
            method="GET",
            request_headers={},
            request_body="",
            elapsed_time=0.5,
            size_bytes=12
        )
        
        with pytest.raises(ValueError):
            response.json()
    
    def test_response_status_checks(self):
        """Test response status check methods."""
        # Success response
        success_response = Response(
            status_code=200, headers={}, content=b'', text='',
            url="test", method="GET", request_headers={}, request_body="",
            elapsed_time=0, size_bytes=0
        )
        assert success_response.is_success() == True
        assert success_response.is_client_error() == False
        
        # Client error response
        error_response = Response(
            status_code=404, headers={}, content=b'', text='',
            url="test", method="GET", request_headers={}, request_body="",
            elapsed_time=0, size_bytes=0
        )
        assert error_response.is_success() == False
        assert error_response.is_client_error() == True