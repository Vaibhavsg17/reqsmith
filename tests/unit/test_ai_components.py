"""
Unit tests for AI components.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.reqsmith.ai import GeminiClient, AIAssistant, ValidationResult, AIValidator


class TestGeminiClient:
    """Test cases for GeminiClient."""
    
    def test_init_without_api_key(self):
        """Test GeminiClient initialization without API key."""
        with patch.dict('os.environ', {}, clear=True):
            client = GeminiClient()
            assert client.api_key is None
            assert client.is_available() == False
    
    def test_init_with_api_key(self):
        """Test GeminiClient initialization with API key."""
        with patch('google.generativeai.configure') as mock_configure, \
             patch('google.generativeai.GenerativeModel') as mock_model:
            
            mock_model.return_value = Mock()
            
            client = GeminiClient("test-api-key")
            assert client.api_key == "test-api-key"
            mock_configure.assert_called_once_with(api_key="test-api-key")
    
    def test_init_without_gemini_package(self):
        """Test initialization when google-generativeai is not available."""
        with patch('src.reqsmith.ai.gemini_client.GEMINI_AVAILABLE', False):
            client = GeminiClient("test-key")
            assert client.is_available() == False
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_generate_content_success(self, mock_model_class, mock_configure):
        """Test successful content generation."""
        # Mock the model and response
        mock_response = Mock()
        mock_response.text = "Generated content"
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        client = GeminiClient("test-key")
        result = client.generate_content("Test prompt")
        
        assert result == "Generated content"
        mock_model.generate_content.assert_called_once_with("Test prompt")
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_generate_content_with_context(self, mock_model_class, mock_configure):
        """Test content generation with context."""
        mock_response = Mock()
        mock_response.text = "Generated content with context"
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        client = GeminiClient("test-key")
        result = client.generate_content("Test prompt", "Test context")
        
        assert result == "Generated content with context"
        
        # Check that context was included in the prompt
        call_args = mock_model.generate_content.call_args[0][0]
        assert "Context: Test context" in call_args
        assert "Prompt: Test prompt" in call_args
    
    def test_generate_content_not_available(self):
        """Test content generation when Gemini is not available."""
        client = GeminiClient()  # No API key
        
        with pytest.raises(RuntimeError, match="Gemini AI is not available"):
            client.generate_content("Test prompt")
    
    def test_validate_json_valid(self):
        """Test JSON validation with valid JSON."""
        with patch.object(GeminiClient, 'is_available', return_value=True):
            client = GeminiClient("test-key")
            
            valid_json = '{"name": "test", "value": 123}'
            result = client.validate_json(valid_json)
            
            assert result.is_valid == True
            assert result.explanation == "JSON is valid"
    
    def test_validate_json_invalid(self):
        """Test JSON validation with invalid JSON."""
        with patch.object(GeminiClient, 'is_available', return_value=True), \
             patch.object(GeminiClient, 'generate_content') as mock_generate:
            
            mock_generate.return_value = """
            ISSUES: Missing closing brace
            CORRECTED: {"name": "test", "value": 123}
            EXPLANATION: The JSON was missing a closing brace
            SUGGESTIONS: Use a JSON validator, Check bracket matching
            """
            
            client = GeminiClient("test-key")
            
            invalid_json = '{"name": "test", "value": 123'
            result = client.validate_json(invalid_json)
            
            assert result.is_valid == False
            assert len(result.suggestions) > 0
            assert result.corrected_content is not None
    
    def test_analyze_api_endpoint(self):
        """Test API endpoint analysis."""
        with patch.object(GeminiClient, 'is_available', return_value=True), \
             patch.object(GeminiClient, 'generate_content') as mock_generate:
            
            mock_generate.return_value = '''
            {
                "suggested_headers": {"Authorization": "Bearer token", "Content-Type": "application/json"},
                "suggested_params": {"limit": "number of results", "offset": "pagination offset"},
                "auth_suggestions": ["Bearer token", "API key"],
                "content_type": "application/json",
                "analysis": "This appears to be a REST API endpoint for user management",
                "confidence": 0.8
            }
            '''
            
            client = GeminiClient("test-key")
            result = client.analyze_api_endpoint("https://api.example.com/users", "GET")
            
            assert 'suggested_headers' in result
            assert 'analysis' in result
            assert result['confidence'] == 0.8
    
    def test_explain_status_code(self):
        """Test HTTP status code explanation."""
        with patch.object(GeminiClient, 'is_available', return_value=True), \
             patch.object(GeminiClient, 'generate_content') as mock_generate:
            
            mock_generate.return_value = "404 Not Found means the requested resource could not be found on the server."
            
            client = GeminiClient("test-key")
            explanation = client.explain_status_code(404)
            
            assert "404" in explanation
            assert "Not Found" in explanation


class TestAIAssistant:
    """Test cases for AIAssistant."""
    
    def test_init_with_client(self, mock_gemini_client):
        """Test AIAssistant initialization with Gemini client."""
        assistant = AIAssistant(mock_gemini_client)
        assert assistant.gemini_client == mock_gemini_client
        assert assistant.is_enabled() == True
    
    def test_init_without_client(self):
        """Test AIAssistant initialization without Gemini client."""
        with patch('src.reqsmith.ai.assistant.GeminiClient') as mock_client_class:
            mock_client = Mock()
            mock_client.is_available.return_value = False
            mock_client_class.return_value = mock_client
            
            assistant = AIAssistant()
            assert assistant.is_enabled() == False
    
    def test_suggest_headers(self, mock_gemini_client):
        """Test header suggestions."""
        mock_gemini_client.analyze_api_endpoint.return_value = {
            'suggested_headers': {
                'Authorization': 'Bearer token',
                'Content-Type': 'application/json'
            }
        }
        
        assistant = AIAssistant(mock_gemini_client)
        suggestions = assistant.suggest_headers("https://api.example.com/users", "GET")
        
        assert 'Authorization' in suggestions
        assert 'Content-Type' in suggestions
    
    def test_suggest_headers_with_existing(self, mock_gemini_client):
        """Test header suggestions with existing headers."""
        mock_gemini_client.analyze_api_endpoint.return_value = {
            'suggested_headers': {
                'Authorization': 'Bearer token',
                'Content-Type': 'application/json'
            }
        }
        
        assistant = AIAssistant(mock_gemini_client)
        existing_headers = {'Authorization': 'Bearer existing-token'}
        
        suggestions = assistant.suggest_headers(
            "https://api.example.com/users", "GET", existing_headers
        )
        
        # Should not suggest Authorization since it already exists
        assert 'Authorization' not in suggestions
        assert 'Content-Type' in suggestions
    
    def test_explain_status_code(self, mock_gemini_client):
        """Test status code explanation."""
        mock_gemini_client.explain_status_code.return_value = "404 means resource not found"
        
        assistant = AIAssistant(mock_gemini_client)
        explanation = assistant.explain_status_code(404)
        
        assert "404" in explanation
        assert "not found" in explanation.lower()
    
    def test_explain_status_code_not_available(self):
        """Test status code explanation when AI not available."""
        with patch('src.reqsmith.ai.assistant.GeminiClient') as mock_client_class:
            mock_client = Mock()
            mock_client.is_available.return_value = False
            mock_client_class.return_value = mock_client
            
            assistant = AIAssistant()
            explanation = assistant.explain_status_code(404)
            
            # Should fall back to basic explanation
            assert "404" in explanation
    
    def test_validate_request_structure(self, mock_gemini_client):
        """Test request structure validation."""
        assistant = AIAssistant(mock_gemini_client)
        
        request_data = {
            'method': 'POST',
            'url': 'https://api.example.com/users',
            'headers': {'Content-Type': 'application/json'},
            'body': '{"name": "test"}'
        }
        
        result = assistant.validate_request_structure(request_data)
        
        assert isinstance(result, ValidationResult)
    
    def test_validate_request_structure_json_body(self, mock_gemini_client):
        """Test request structure validation with JSON body."""
        mock_gemini_client.validate_json.return_value = ValidationResult(
            is_valid=True,
            suggestions=[],
            explanation="Valid JSON"
        )
        
        assistant = AIAssistant(mock_gemini_client)
        
        request_data = {
            'method': 'POST',
            'url': 'https://api.example.com/users',
            'headers': {'Content-Type': 'application/json'},
            'body': '{"name": "test"}'
        }
        
        result = assistant.validate_request_structure(request_data)
        
        # Should call JSON validation
        mock_gemini_client.validate_json.assert_called_once_with('{"name": "test"}')


class TestAIValidator:
    """Test cases for AIValidator."""
    
    def test_init(self):
        """Test AIValidator initialization."""
        validator = AIValidator()
        assert validator.ai_assistant is not None
    
    def test_init_with_assistant(self, mock_gemini_client):
        """Test AIValidator initialization with AI assistant."""
        assistant = AIAssistant(mock_gemini_client)
        validator = AIValidator(assistant)
        assert validator.ai_assistant == assistant
    
    def test_validate_json_structure_valid(self):
        """Test JSON structure validation with valid JSON."""
        validator = AIValidator()
        
        valid_json = '{"name": "test", "value": 123}'
        result = validator.validate_json_structure(valid_json)
        
        assert result.is_valid == True
    
    def test_validate_json_structure_invalid(self):
        """Test JSON structure validation with invalid JSON."""
        validator = AIValidator()
        
        invalid_json = '{"name": "test", "value": }'
        result = validator.validate_json_structure(invalid_json)
        
        assert result.is_valid == False
        assert len(result.suggestions) > 0
    
    def test_validate_url_format_valid(self):
        """Test URL format validation with valid URL."""
        validator = AIValidator()
        
        result = validator.validate_url_format("https://api.example.com/users")
        
        assert result.is_valid == True
    
    def test_validate_url_format_invalid(self):
        """Test URL format validation with invalid URL."""
        validator = AIValidator()
        
        result = validator.validate_url_format("invalid-url")
        
        assert result.is_valid == False
        assert len(result.suggestions) > 0
    
    def test_validate_headers_valid(self):
        """Test header validation with valid headers."""
        validator = AIValidator()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token"
        }
        
        result = validator.validate_headers(headers, "POST", "https://api.example.com")
        
        assert result.is_valid == True
    
    def test_validate_headers_missing_content_type(self):
        """Test header validation with missing Content-Type."""
        validator = AIValidator()
        
        headers = {
            "Authorization": "Bearer token"
        }
        
        result = validator.validate_headers(headers, "POST", "https://api.example.com")
        
        # Should suggest adding Content-Type
        assert any("Content-Type" in suggestion for suggestion in result.suggestions)
    
    def test_suggest_request_improvements(self):
        """Test request improvement suggestions."""
        validator = AIValidator()
        
        request_data = {
            'method': 'GET',
            'url': 'http://api.example.com/users',  # HTTP instead of HTTPS
            'headers': {},
            'body': ''
        }
        
        suggestions = validator.suggest_request_improvements(request_data)
        
        assert len(suggestions) > 0
        # Should suggest HTTPS
        assert any("https" in suggestion.lower() for suggestion in suggestions)
    
    def test_generate_examples_from_openapi(self, mock_gemini_client):
        """Test generating examples from OpenAPI spec."""
        # Mock the generate_examples_from_openapi method to return a parsed list
        mock_gemini_client.generate_examples_from_openapi.return_value = [
            {
                "method": "GET",
                "url": "/users/{id}",
                "headers": {"Authorization": "Bearer token"},
                "description": "Get user by ID"
            },
            {
                "method": "POST", 
                "url": "/users",
                "headers": {"Content-Type": "application/json"},
                "body": {"name": "John", "email": "john@example.com"},
                "description": "Create new user"
            }
        ]
        
        assistant = AIAssistant(mock_gemini_client)
        
        openapi_spec = {
            "paths": {
                "/users/{id}": {"get": {"summary": "Get user"}},
                "/users": {"post": {"summary": "Create user"}}
            }
        }
        
        examples = assistant.generate_examples_from_openapi(openapi_spec, "/users")
        
        assert isinstance(examples, list)
        # The actual parsing would depend on implementation
    
    def test_ai_assistant_fallback_behavior(self):
        """Test AI assistant fallback when Gemini is not available."""
        with patch('src.reqsmith.ai.assistant.GeminiClient') as mock_client_class:
            mock_client = Mock()
            mock_client.is_available.return_value = False
            mock_client_class.return_value = mock_client
            
            assistant = AIAssistant()
            
            # Should provide fallback responses
            headers = assistant.suggest_headers("https://api.example.com/users", "GET")
            assert isinstance(headers, dict)
            
            explanation = assistant.explain_status_code(404)
            assert isinstance(explanation, str)
            assert "404" in explanation
    
    def test_gemini_client_error_handling(self):
        """Test Gemini client error handling."""
        with patch('google.generativeai.configure') as mock_configure, \
             patch('google.generativeai.GenerativeModel') as mock_model_class:
            
            # Mock model to raise exception
            mock_model = Mock()
            mock_model.generate_content.side_effect = Exception("API Error")
            mock_model_class.return_value = mock_model
            
            client = GeminiClient("test-key")
            
            # Should handle exceptions gracefully
            result = client.generate_content("Test prompt")
            assert result is None or isinstance(result, str)
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation and methods."""
        result = ValidationResult(
            is_valid=False,
            suggestions=["Add missing comma", "Fix bracket"],
            explanation="JSON syntax error",
            corrected_content='{"fixed": "json"}'
        )
        
        assert result.is_valid == False
        assert len(result.suggestions) == 2
        assert result.explanation == "JSON syntax error"
        assert result.corrected_content == '{"fixed": "json"}'
    
    def test_ai_validator_comprehensive(self):
        """Test comprehensive AI validator functionality."""
        validator = AIValidator()
        
        # Test with various invalid inputs
        test_cases = [
            ('{"invalid": json}', False),  # Invalid JSON
            ('{"valid": "json"}', True),   # Valid JSON
            ('invalid-url', False),        # Invalid URL
            ('https://valid.com', True),   # Valid URL
        ]
        
        for test_input, expected_valid in test_cases:
            if 'json' in test_input:
                result = validator.validate_json_structure(test_input)
            else:
                result = validator.validate_url_format(test_input)
            
            assert result.is_valid == expected_valid
            if not expected_valid:
                assert len(result.suggestions) > 0