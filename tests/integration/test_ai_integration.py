"""
Integration tests for AI features with actual Gemini API.
These tests require a valid GEMINI_API_KEY environment variable.
"""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock

from reqsmith.ai import GeminiClient, AIAssistant, check_gemini_availability
from reqsmith.ai.validators import AIValidator


@pytest.fixture
def gemini_api_key():
    """Get Gemini API key from environment."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        pytest.skip("GEMINI_API_KEY environment variable not set")
    return api_key


@pytest.fixture
def gemini_client(gemini_api_key):
    """Create a real Gemini client for testing."""
    return GeminiClient(gemini_api_key)


@pytest.fixture
def ai_assistant(gemini_client):
    """Create an AI assistant with real Gemini client."""
    return AIAssistant(gemini_client)


class TestGeminiAvailability:
    """Test Gemini availability and setup."""
    
    def test_availability_check_with_key(self, gemini_api_key):
        """Test availability check with valid key."""
        with patch.dict(os.environ, {'GEMINI_API_KEY': gemini_api_key}):
            is_available, message = check_gemini_availability()
            assert is_available
            assert "available" in message.lower()
    
    def test_availability_check_without_key(self):
        """Test availability check without key."""
        with patch.dict(os.environ, {}, clear=True):
            is_available, message = check_gemini_availability()
            assert not is_available
            assert "api key" in message.lower()


class TestGeminiClientIntegration:
    """Integration tests for Gemini client with real API."""
    
    def test_client_initialization(self, gemini_api_key):
        """Test client initializes correctly."""
        client = GeminiClient(gemini_api_key)
        assert client.is_available()
    
    def test_content_generation(self, gemini_client):
        """Test content generation with real API."""
        response = gemini_client.generate_content("Say hello briefly")
        
        assert response is not None
        assert len(response) > 0
        assert isinstance(response, str)
    
    def test_json_validation_valid(self, gemini_client):
        """Test JSON validation with valid JSON."""
        valid_json = '{"name": "test", "value": 123, "active": true}'
        result = gemini_client.validate_json(valid_json)
        
        assert result.is_valid
        assert result.data is not None
        assert result.data["name"] == "test"
        assert result.error_message is None
    
    def test_json_validation_invalid(self, gemini_client):
        """Test JSON validation with invalid JSON."""
        invalid_json = '{"name": "test", "value": 123, "active":}'
        result = gemini_client.validate_json(invalid_json)
        
        assert not result.is_valid
        assert result.data is None
        assert result.error_message is not None
    
    def test_api_endpoint_analysis(self, gemini_client):
        """Test API endpoint analysis."""
        analysis = gemini_client.analyze_api_endpoint(
            "https://api.github.com/user", "GET"
        )
        
        assert isinstance(analysis, dict)
        assert "suggested_headers" in analysis
        assert isinstance(analysis["suggested_headers"], dict)
    
    def test_status_code_explanation(self, gemini_client):
        """Test status code explanation."""
        explanation = gemini_client.explain_status_code(404)
        
        assert isinstance(explanation, str)
        assert "404" in explanation
        assert len(explanation) > 10
    
    def test_error_handling_invalid_key(self):
        """Test error handling with invalid API key."""
        client = GeminiClient("invalid_key")
        assert not client.is_available()
    
    def test_rate_limiting_handling(self, gemini_client):
        """Test handling of rate limits (if they occur)."""
        # Make multiple requests quickly
        responses = []
        for i in range(3):
            response = gemini_client.generate_content(f"Say number {i}")
            responses.append(response)
        
        # All should succeed or gracefully handle rate limits
        assert all(r is not None for r in responses)


class TestAIAssistantIntegration:
    """Integration tests for AI assistant with real API."""
    
    def test_assistant_initialization(self, ai_assistant):
        """Test assistant initializes correctly."""
        assert ai_assistant.is_enabled()
    
    def test_header_suggestions(self, ai_assistant):
        """Test header suggestions for various endpoints."""
        headers = ai_assistant.suggest_headers(
            "https://api.github.com/repos", "GET"
        )
        
        assert isinstance(headers, dict)
        assert len(headers) > 0
    
    def test_status_code_explanation(self, ai_assistant):
        """Test status code explanation through assistant."""
        explanation = ai_assistant.explain_status_code(401)
        
        assert isinstance(explanation, str)
        assert "401" in explanation
        assert "unauthorized" in explanation.lower()
    
    def test_test_scenario_generation(self, ai_assistant):
        """Test generation of test scenarios."""
        endpoint_info = {
            "method": "POST",
            "url": "/api/users",
            "description": "Create a new user",
            "parameters": {
                "name": "string",
                "email": "string"
            }
        }
        
        scenarios = ai_assistant.suggest_test_scenarios(endpoint_info)
        
        assert isinstance(scenarios, list)
        assert len(scenarios) > 0
        assert all(isinstance(s, str) for s in scenarios)
    
    def test_json_validation_through_assistant(self, ai_assistant):
        """Test JSON validation through assistant."""
        json_str = '{"user": {"id": 1, "name": "test"}}'
        result = ai_assistant.gemini_client.validate_json(json_str)
        
        assert result.is_valid
        assert result.data["user"]["name"] == "test"


class TestAIValidatorIntegration:
    """Integration tests for AI validator with real API."""
    
    def test_validator_with_real_api(self, gemini_api_key):
        """Test AI validator with real API."""
        validator = AIValidator(gemini_api_key)
        
        # Test response validation
        response_data = {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "body": '{"message": "success", "data": [1, 2, 3]}'
        }
        
        issues = validator.validate_response(response_data)
        assert isinstance(issues, list)
    
    def test_schema_validation(self, gemini_api_key):
        """Test schema validation with AI assistance."""
        validator = AIValidator(gemini_api_key)
        
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name"]
        }
        
        valid_data = {"name": "John", "age": 30}
        invalid_data = {"age": "thirty"}  # age should be integer
        
        # These should use AI to provide better error messages
        valid_issues = validator.validate_against_schema(valid_data, schema)
        invalid_issues = validator.validate_against_schema(invalid_data, schema)
        
        assert len(valid_issues) == 0
        assert len(invalid_issues) > 0


class TestRealWorldScenarios:
    """Test real-world API testing scenarios with AI."""
    
    def test_rest_api_analysis(self, ai_assistant):
        """Test analysis of a real REST API endpoint."""
        # Analyze GitHub API
        analysis = ai_assistant.gemini_client.analyze_api_endpoint(
            "https://api.github.com/repos/owner/repo/issues", "POST"
        )
        
        assert "suggested_headers" in analysis
        headers = analysis["suggested_headers"]
        
        # Should suggest appropriate headers for GitHub API
        assert any("authorization" in k.lower() for k in headers.keys())
        assert any("content-type" in k.lower() for k in headers.keys())
    
    def test_graphql_endpoint_analysis(self, ai_assistant):
        """Test analysis of GraphQL endpoint."""
        analysis = ai_assistant.gemini_client.analyze_api_endpoint(
            "https://api.github.com/graphql", "POST"
        )
        
        assert "suggested_headers" in analysis
        # GraphQL typically needs specific headers
        headers = analysis["suggested_headers"]
        assert any("content-type" in k.lower() for k in headers.keys())
    
    def test_authentication_suggestions(self, ai_assistant):
        """Test authentication header suggestions."""
        # Test API that typically requires auth
        headers = ai_assistant.suggest_headers(
            "https://api.stripe.com/v1/charges", "POST"
        )
        
        # Should suggest authorization header
        assert any("authorization" in k.lower() for k in headers.keys())
    
    def test_complex_json_validation(self, ai_assistant):
        """Test validation of complex, nested JSON."""
        complex_json = '''
        {
            "user": {
                "profile": {
                    "personal": {
                        "name": "John Doe",
                        "age": 30,
                        "contacts": {
                            "emails": ["john@example.com", "john.doe@work.com"],
                            "phones": ["+1-555-123-4567"]
                        }
                    },
                    "professional": {
                        "title": "Software Engineer",
                        "company": "TechCorp",
                        "skills": ["Python", "JavaScript", "API Design"]
                    }
                },
                "settings": {
                    "notifications": {
                        "email": true,
                        "sms": false,
                        "push": true
                    },
                    "privacy": {
                        "profile_visibility": "public",
                        "contact_visibility": "friends"
                    }
                }
            },
            "metadata": {
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "version": "2.1",
                "source": "api_v2"
            }
        }
        '''
        
        result = ai_assistant.gemini_client.validate_json(complex_json)
        
        assert result.is_valid
        assert result.data["user"]["profile"]["personal"]["name"] == "John Doe"
        assert len(result.data["user"]["profile"]["professional"]["skills"]) == 3


@pytest.mark.slow
class TestPerformanceAndReliability:
    """Test performance and reliability of AI integration."""
    
    def test_concurrent_requests(self, gemini_client):
        """Test handling of concurrent AI requests."""
        import concurrent.futures
        
        def make_request(i):
            return gemini_client.generate_content(f"Say number {i}")
        
        # Make concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        assert all(r is not None for r in results)
        assert len(results) == 5
    
    def test_large_content_handling(self, gemini_client):
        """Test handling of large content."""
        # Generate a large JSON structure
        large_json = {
            "users": [
                {
                    "id": i,
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "data": {
                        "preferences": {
                            "theme": "dark" if i % 2 else "light",
                            "notifications": True,
                            "features": [f"feature_{j}" for j in range(10)]
                        }
                    }
                }
                for i in range(100)
            ]
        }
        
        import json
        large_json_str = json.dumps(large_json)
        
        result = gemini_client.validate_json(large_json_str)
        assert result.is_valid
    
    def test_error_recovery(self, gemini_api_key):
        """Test error recovery and graceful degradation."""
        # Test with temporarily invalid client
        invalid_client = GeminiClient("invalid_key")
        assistant = AIAssistant(invalid_client)
        
        # Should not crash, should handle gracefully
        assert not assistant.is_enabled()
        
        # Switching to valid client should work
        valid_client = GeminiClient(gemini_api_key)
        assistant.gemini_client = valid_client
        assistant._enabled = valid_client.is_available()
        
        assert assistant.is_enabled()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
