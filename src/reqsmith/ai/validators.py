"""
Gemini-powered validation and suggestion utilities.
"""
import json
import re
from typing import Dict, List, Optional, Any, Tuple
import logging

from .gemini_client import GeminiClient, ValidationResult
from .assistant import AIAssistant


logger = logging.getLogger(__name__)


class AIValidator:
    """AI-powered validator using Gemini for intelligent validation."""
    
    def __init__(self, ai_assistant: Optional[AIAssistant] = None):
        """
        Initialize AI validator.
        
        Args:
            ai_assistant: AIAssistant instance
        """
        self.ai_assistant = ai_assistant or AIAssistant()
    
    def validate_json_structure(self, json_str: str, 
                               expected_schema: Optional[Dict] = None) -> ValidationResult:
        """
        Validate JSON structure with AI assistance.
        
        Args:
            json_str: JSON string to validate
            expected_schema: Optional expected schema
            
        Returns:
            ValidationResult with detailed feedback
        """
        if not self.ai_assistant.is_enabled():
            return self._basic_json_validation(json_str)
        
        try:
            # First do basic validation
            basic_result = self._basic_json_validation(json_str)
            if not basic_result.is_valid:
                # Use AI to suggest corrections
                return self.ai_assistant.gemini_client.validate_json(json_str)
            
            # If basic validation passes, check against schema if provided
            if expected_schema:
                return self._validate_against_schema(json_str, expected_schema)
            
            return basic_result
            
        except Exception as e:
            logger.error(f"AI JSON validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                suggestions=[f"Validation error: {str(e)}"],
                explanation="AI validation failed"
            )
    
    def validate_api_request(self, request_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate complete API request structure.
        
        Args:
            request_data: Request data to validate
            
        Returns:
            ValidationResult with suggestions
        """
        if not self.ai_assistant.is_enabled():
            return self._basic_request_validation(request_data)
        
        try:
            return self.ai_assistant.validate_request_structure(request_data)
        except Exception as e:
            logger.error(f"AI request validation failed: {e}")
            return self._basic_request_validation(request_data)
    
    def validate_url_format(self, url: str) -> ValidationResult:
        """
        Validate URL format with AI suggestions.
        
        Args:
            url: URL to validate
            
        Returns:
            ValidationResult with URL validation details
        """
        # Basic URL validation first
        basic_valid = self._is_valid_url(url)
        
        if not self.ai_assistant.is_enabled():
            return ValidationResult(
                is_valid=basic_valid,
                suggestions=[] if basic_valid else ["Invalid URL format"],
                explanation="Basic URL validation"
            )
        
        try:
            if not basic_valid:
                # Use AI to suggest URL corrections
                prompt = f"""
                This URL appears to be invalid: {url}
                
                Please:
                1. Identify what's wrong with the URL
                2. Suggest a corrected version
                3. Provide tips for valid URL formatting
                
                Respond in this format:
                ISSUES: [list of issues]
                CORRECTED: [corrected URL]
                SUGGESTIONS: [formatting tips]
                """
                
                response = self.ai_assistant.gemini_client.generate_content(prompt)
                return self._parse_url_validation_response(response, False)
            
            # URL is valid, check for best practices
            suggestions = []
            
            if not url.startswith(('http://', 'https://')):
                suggestions.append("Consider using https:// for secure connections")
            
            if ' ' in url:
                suggestions.append("URLs should not contain spaces - use %20 encoding")
            
            return ValidationResult(
                is_valid=True,
                suggestions=suggestions,
                explanation="URL format is valid"
            )
            
        except Exception as e:
            logger.error(f"AI URL validation failed: {e}")
            return ValidationResult(
                is_valid=basic_valid,
                suggestions=[] if basic_valid else ["Invalid URL format"],
                explanation="Basic URL validation (AI unavailable)"
            )
    
    def validate_headers(self, headers: Dict[str, str], 
                        method: str, url: str) -> ValidationResult:
        """
        Validate HTTP headers with AI suggestions.
        
        Args:
            headers: Headers to validate
            method: HTTP method
            url: Request URL
            
        Returns:
            ValidationResult with header validation
        """
        if not self.ai_assistant.is_enabled():
            return self._basic_header_validation(headers, method)
        
        try:
            prompt = f"""
            Validate these HTTP headers for a {method} request to {url}:
            
            Headers: {json.dumps(headers, indent=2)}
            
            Check for:
            1. Required headers that might be missing
            2. Incorrect header values
            3. Security considerations
            4. Best practices
            
            Respond with:
            VALID: true/false
            ISSUES: [list of issues]
            SUGGESTIONS: [list of suggestions]
            MISSING: [list of recommended headers to add]
            """
            
            response = self.ai_assistant.gemini_client.generate_content(prompt)
            return self._parse_header_validation_response(response)
            
        except Exception as e:
            logger.error(f"AI header validation failed: {e}")
            return self._basic_header_validation(headers, method)
    
    def suggest_request_improvements(self, request_data: Dict[str, Any]) -> List[str]:
        """
        Suggest improvements for API request.
        
        Args:
            request_data: Request data to analyze
            
        Returns:
            List of improvement suggestions
        """
        if not self.ai_assistant.is_enabled():
            return self._basic_request_suggestions(request_data)
        
        try:
            prompt = f"""
            Analyze this API request and suggest improvements:
            
            Request: {json.dumps(request_data, indent=2)}
            
            Suggest improvements for:
            1. Performance optimization
            2. Security best practices
            3. Error handling
            4. API usage patterns
            5. Request structure
            
            Provide specific, actionable suggestions.
            """
            
            response = self.ai_assistant.gemini_client.generate_content(prompt)
            
            # Parse suggestions from response
            suggestions = [line.strip() for line in response.split('\n') 
                         if line.strip() and not line.strip().startswith('#')]
            
            return suggestions[:8]  # Limit to 8 suggestions
            
        except Exception as e:
            logger.error(f"AI request improvement failed: {e}")
            return self._basic_request_suggestions(request_data)
    
    def _basic_json_validation(self, json_str: str) -> ValidationResult:
        """Basic JSON validation without AI."""
        try:
            json.loads(json_str)
            return ValidationResult(
                is_valid=True,
                suggestions=[],
                explanation="JSON is valid"
            )
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                suggestions=[f"JSON error: {str(e)}"],
                explanation=f"JSON parsing failed: {str(e)}"
            )
    
    def _basic_request_validation(self, request_data: Dict[str, Any]) -> ValidationResult:
        """Basic request validation without AI."""
        suggestions = []
        
        method = request_data.get('method', '').upper()
        url = request_data.get('url', '')
        headers = request_data.get('headers', {})
        body = request_data.get('body', '')
        
        # Basic checks
        if not method:
            suggestions.append("HTTP method is required")
        
        if not url:
            suggestions.append("URL is required")
        
        if method in ['POST', 'PUT', 'PATCH'] and not body:
            suggestions.append(f"Consider adding request body for {method} requests")
        
        if body and not headers.get('Content-Type'):
            suggestions.append("Consider adding Content-Type header when sending body")
        
        return ValidationResult(
            is_valid=len(suggestions) == 0,
            suggestions=suggestions,
            explanation="Basic request validation"
        )
    
    def _basic_header_validation(self, headers: Dict[str, str], method: str) -> ValidationResult:
        """Basic header validation without AI."""
        suggestions = []
        
        # Check for common missing headers
        if method.upper() in ['POST', 'PUT', 'PATCH']:
            if 'Content-Type' not in headers:
                suggestions.append("Consider adding Content-Type header for requests with body")
        
        if 'Accept' not in headers:
            suggestions.append("Consider adding Accept header to specify expected response format")
        
        # Check for invalid header names
        for header_name in headers.keys():
            if not re.match(r'^[a-zA-Z0-9\-_]+$', header_name):
                suggestions.append(f"Header name '{header_name}' contains invalid characters")
        
        return ValidationResult(
            is_valid=True,
            suggestions=suggestions,
            explanation="Basic header validation"
        )
    
    def _basic_request_suggestions(self, request_data: Dict[str, Any]) -> List[str]:
        """Basic request suggestions without AI."""
        suggestions = []
        
        method = request_data.get('method', '').upper()
        url = request_data.get('url', '')
        headers = request_data.get('headers', {})
        
        # Security suggestions
        if url.startswith('http://'):
            suggestions.append("Consider using HTTPS for secure communication")
        
        if 'Authorization' not in headers and 'api' in url.lower():
            suggestions.append("API endpoints often require authentication headers")
        
        # Performance suggestions
        if 'Accept-Encoding' not in headers:
            suggestions.append("Add Accept-Encoding header to enable compression")
        
        # Best practices
        if 'User-Agent' not in headers:
            suggestions.append("Add User-Agent header to identify your application")
        
        return suggestions
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL has valid format."""
        try:
            from urllib.parse import urlparse
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _validate_against_schema(self, json_str: str, schema: Dict) -> ValidationResult:
        """Validate JSON against schema using AI."""
        try:
            prompt = f"""
            Validate this JSON against the expected schema:
            
            JSON: {json_str}
            
            Expected Schema: {json.dumps(schema, indent=2)}
            
            Check for:
            1. Missing required fields
            2. Incorrect data types
            3. Invalid values
            4. Extra unexpected fields
            
            Respond with:
            VALID: true/false
            ISSUES: [list of validation issues]
            SUGGESTIONS: [suggestions to fix issues]
            """
            
            response = self.ai_assistant.gemini_client.generate_content(prompt)
            return self._parse_schema_validation_response(response)
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return ValidationResult(
                is_valid=True,
                suggestions=[f"Schema validation error: {str(e)}"],
                explanation="Schema validation failed"
            )
    
    def _parse_url_validation_response(self, response: str, is_valid: bool) -> ValidationResult:
        """Parse AI URL validation response."""
        try:
            lines = response.split('\n')
            issues = []
            corrected = None
            suggestions = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('ISSUES:'):
                    issues.append(line[7:].strip())
                elif line.startswith('CORRECTED:'):
                    corrected = line[10:].strip()
                elif line.startswith('SUGGESTIONS:'):
                    suggestions.append(line[12:].strip())
            
            return ValidationResult(
                is_valid=is_valid,
                suggestions=suggestions or issues,
                corrected_content=corrected,
                explanation="AI URL validation"
            )
            
        except Exception:
            return ValidationResult(
                is_valid=is_valid,
                suggestions=["Failed to parse AI response"],
                explanation="URL validation parsing failed"
            )
    
    def _parse_header_validation_response(self, response: str) -> ValidationResult:
        """Parse AI header validation response."""
        try:
            lines = response.split('\n')
            is_valid = True
            issues = []
            suggestions = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('VALID:'):
                    is_valid = 'true' in line.lower()
                elif line.startswith('ISSUES:'):
                    issues.append(line[7:].strip())
                elif line.startswith('SUGGESTIONS:'):
                    suggestions.append(line[12:].strip())
                elif line.startswith('MISSING:'):
                    suggestions.append(f"Consider adding: {line[8:].strip()}")
            
            return ValidationResult(
                is_valid=is_valid,
                suggestions=suggestions + issues,
                explanation="AI header validation"
            )
            
        except Exception:
            return ValidationResult(
                is_valid=True,
                suggestions=["Failed to parse AI response"],
                explanation="Header validation parsing failed"
            )
    
    def _parse_schema_validation_response(self, response: str) -> ValidationResult:
        """Parse AI schema validation response."""
        try:
            lines = response.split('\n')
            is_valid = True
            issues = []
            suggestions = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('VALID:'):
                    is_valid = 'true' in line.lower()
                elif line.startswith('ISSUES:'):
                    issues.append(line[7:].strip())
                elif line.startswith('SUGGESTIONS:'):
                    suggestions.append(line[12:].strip())
            
            return ValidationResult(
                is_valid=is_valid,
                suggestions=suggestions + issues,
                explanation="AI schema validation"
            )
            
        except Exception:
            return ValidationResult(
                is_valid=True,
                suggestions=["Failed to parse AI response"],
                explanation="Schema validation parsing failed"
            )


class SmartSuggestionEngine:
    """Smart suggestion engine powered by Gemini AI."""
    
    def __init__(self, ai_assistant: Optional[AIAssistant] = None):
        """
        Initialize suggestion engine.
        
        Args:
            ai_assistant: AIAssistant instance
        """
        self.ai_assistant = ai_assistant or AIAssistant()
    
    def suggest_api_endpoints(self, base_url: str, 
                            existing_endpoints: List[str] = None) -> List[Dict[str, str]]:
        """
        Suggest API endpoints based on base URL and existing endpoints.
        
        Args:
            base_url: Base API URL
            existing_endpoints: List of known endpoints
            
        Returns:
            List of suggested endpoints with methods
        """
        if not self.ai_assistant.is_enabled():
            return self._basic_endpoint_suggestions(base_url)
        
        try:
            prompt = f"""
            Based on this API base URL and existing endpoints, suggest additional common endpoints:
            
            Base URL: {base_url}
            Existing endpoints: {existing_endpoints or []}
            
            Suggest realistic API endpoints that commonly exist for this type of API.
            Include the HTTP method and a brief description.
            
            Respond in JSON format:
            [
                {{"method": "GET", "path": "/users", "description": "List users"}},
                {{"method": "POST", "path": "/users", "description": "Create user"}}
            ]
            """
            
            response = self.ai_assistant.gemini_client.generate_content(prompt)
            try:
                suggestions = json.loads(response)
                return suggestions if isinstance(suggestions, list) else []
            except json.JSONDecodeError:
                return self._basic_endpoint_suggestions(base_url)
                
        except Exception as e:
            logger.error(f"Endpoint suggestion failed: {e}")
            return self._basic_endpoint_suggestions(base_url)
    
    def suggest_request_parameters(self, endpoint: str, method: str) -> Dict[str, List[str]]:
        """
        Suggest request parameters for an endpoint.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            
        Returns:
            Dictionary with parameter suggestions
        """
        if not self.ai_assistant.is_enabled():
            return self._basic_parameter_suggestions(endpoint, method)
        
        try:
            prompt = f"""
            Suggest appropriate parameters for this API endpoint:
            
            Method: {method}
            Endpoint: {endpoint}
            
            Suggest:
            1. Query parameters (for filtering, pagination, etc.)
            2. Path parameters (if any in the URL)
            3. Request body fields (for POST/PUT/PATCH)
            4. Headers that might be useful
            
            Respond in JSON format:
            {{
                "query_params": ["param1", "param2"],
                "path_params": ["id", "slug"],
                "body_fields": ["name", "email"],
                "headers": ["Authorization", "Content-Type"]
            }}
            """
            
            response = self.ai_assistant.gemini_client.generate_content(prompt)
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return self._basic_parameter_suggestions(endpoint, method)
                
        except Exception as e:
            logger.error(f"Parameter suggestion failed: {e}")
            return self._basic_parameter_suggestions(endpoint, method)
    
    def suggest_test_data(self, endpoint_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest test data for an endpoint.
        
        Args:
            endpoint_info: Information about the endpoint
            
        Returns:
            Dictionary with test data suggestions
        """
        if not self.ai_assistant.is_enabled():
            return self._basic_test_data_suggestions(endpoint_info)
        
        try:
            prompt = f"""
            Generate realistic test data for this API endpoint:
            
            Endpoint info: {json.dumps(endpoint_info, indent=2)}
            
            Generate:
            1. Valid test data examples
            2. Edge case test data
            3. Invalid data for error testing
            
            Respond in JSON format with examples for different scenarios.
            """
            
            response = self.ai_assistant.gemini_client.generate_content(prompt)
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return self._basic_test_data_suggestions(endpoint_info)
                
        except Exception as e:
            logger.error(f"Test data suggestion failed: {e}")
            return self._basic_test_data_suggestions(endpoint_info)
    
    def _basic_endpoint_suggestions(self, base_url: str) -> List[Dict[str, str]]:
        """Basic endpoint suggestions without AI."""
        return [
            {"method": "GET", "path": "/health", "description": "Health check"},
            {"method": "GET", "path": "/version", "description": "API version"},
            {"method": "GET", "path": "/docs", "description": "API documentation"}
        ]
    
    def _basic_parameter_suggestions(self, endpoint: str, method: str) -> Dict[str, List[str]]:
        """Basic parameter suggestions without AI."""
        suggestions = {
            "query_params": [],
            "path_params": [],
            "body_fields": [],
            "headers": ["Authorization", "Content-Type", "Accept"]
        }
        
        # Common query parameters
        if method.upper() == 'GET':
            suggestions["query_params"] = ["limit", "offset", "sort", "filter"]
        
        # Path parameters from URL
        if '{' in endpoint or ':' in endpoint:
            suggestions["path_params"] = ["id"]
        
        # Body fields for write operations
        if method.upper() in ['POST', 'PUT', 'PATCH']:
            suggestions["body_fields"] = ["name", "description", "status"]
        
        return suggestions
    
    def _basic_test_data_suggestions(self, endpoint_info: Dict[str, Any]) -> Dict[str, Any]:
        """Basic test data suggestions without AI."""
        return {
            "valid_examples": {
                "name": "Test User",
                "email": "test@example.com",
                "id": 123
            },
            "edge_cases": {
                "empty_string": "",
                "very_long_string": "x" * 1000,
                "special_characters": "!@#$%^&*()"
            },
            "invalid_data": {
                "null_values": None,
                "wrong_type": "string_instead_of_number"
            }
        }