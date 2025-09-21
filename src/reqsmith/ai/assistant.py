"""
AI assistant functionality using Gemini for API testing assistance.
"""
from typing import Dict, List, Optional, Any, Tuple
import json
import logging
from urllib.parse import urlparse

from .gemini_client import GeminiClient, ValidationResult


logger = logging.getLogger(__name__)


class AIAssistant:
    """AI assistant for API testing with Gemini integration."""
    
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        """
        Initialize AI assistant.
        
        Args:
            gemini_client: GeminiClient instance (creates new one if None)
        """
        self.gemini_client = gemini_client or GeminiClient()
        self._enabled = self.gemini_client.is_available()
    
    def is_enabled(self) -> bool:
        """
        Check if AI assistant is enabled and available.
        
        Returns:
            True if AI features are available
        """
        return self._enabled
    
    def suggest_headers(self, url: str, method: str, 
                       existing_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Suggest appropriate headers for an API request.
        
        Args:
            url: Request URL
            method: HTTP method
            existing_headers: Headers already set
            
        Returns:
            Dictionary of suggested headers
        """
        if not self.is_enabled():
            return {}
        
        try:
            analysis = self.gemini_client.analyze_api_endpoint(url, method)
            suggested = analysis.get('suggested_headers', {})
            
            # Filter out headers that are already set
            if existing_headers:
                suggested = {k: v for k, v in suggested.items() 
                           if k not in existing_headers}
            
            # Add method-specific suggestions
            method_headers = self._get_method_specific_headers(method, url)
            suggested.update(method_headers)
            
            return suggested
            
        except Exception as e:
            logger.error(f"Header suggestion failed: {e}")
            return {}
    
    def explain_status_code(self, status_code: int, 
                           request_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Explain HTTP status code in human-readable terms.
        
        Args:
            status_code: HTTP status code
            request_context: Optional context about the request
            
        Returns:
            Human-readable explanation
        """
        if not self.is_enabled():
            return self._get_basic_status_explanation(status_code)
        
        try:
            context_str = None
            if request_context:
                context_str = f"Method: {request_context.get('method', 'Unknown')}, URL: {request_context.get('url', 'Unknown')}"
            
            explanation = self.gemini_client.explain_status_code(status_code, context_str)
            return explanation
            
        except Exception as e:
            logger.error(f"Status code explanation failed: {e}")
            return self._get_basic_status_explanation(status_code)
    
    def validate_request_structure(self, request_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate request structure and suggest improvements.
        
        Args:
            request_data: Request data to validate
            
        Returns:
            ValidationResult with validation details
        """
        if not self.is_enabled():
            return ValidationResult(
                is_valid=True,
                suggestions=["AI validation not available"],
                explanation="Basic validation passed"
            )
        
        try:
            # Validate JSON body if present
            body = request_data.get('body', '')
            if body and self._looks_like_json(body):
                return self.gemini_client.validate_json(body)
            
            # General request structure validation
            suggestions = []
            
            # Check for common issues
            method = request_data.get('method', '').upper()
            url = request_data.get('url', '')
            headers = request_data.get('headers', {})
            
            if method in ['POST', 'PUT', 'PATCH'] and not body:
                suggestions.append("Consider adding request body for " + method + " requests")
            
            if not headers.get('Content-Type') and body:
                suggestions.append("Consider adding Content-Type header for requests with body")
            
            if not headers.get('Accept'):
                suggestions.append("Consider adding Accept header to specify expected response format")
            
            return ValidationResult(
                is_valid=True,
                suggestions=suggestions,
                explanation="Request structure looks good"
            )
            
        except Exception as e:
            logger.error(f"Request validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                suggestions=[f"Validation error: {str(e)}"],
                explanation="Validation failed due to error"
            )
    
    def generate_examples_from_openapi(self, spec: Dict[str, Any], 
                                     endpoint: str) -> List[Dict[str, Any]]:
        """
        Generate request examples from OpenAPI specification.
        
        Args:
            spec: OpenAPI specification
            endpoint: Specific endpoint path
            
        Returns:
            List of example requests
        """
        if not self.is_enabled():
            return []
        
        try:
            return self.gemini_client.generate_examples_from_openapi(spec, endpoint)
        except Exception as e:
            logger.error(f"OpenAPI example generation failed: {e}")
            return []
    
    def suggest_test_scenarios(self, endpoint_info: Dict[str, Any]) -> List[str]:
        """
        Suggest test scenarios for an API endpoint.
        
        Args:
            endpoint_info: Information about the endpoint
            
        Returns:
            List of test scenario suggestions
        """
        if not self.is_enabled():
            return self._get_basic_test_scenarios(endpoint_info)
        
        try:
            return self.gemini_client.suggest_test_cases(endpoint_info)
        except Exception as e:
            logger.error(f"Test scenario suggestion failed: {e}")
            return self._get_basic_test_scenarios(endpoint_info)
    
    def analyze_response_patterns(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze response patterns and provide insights.
        
        Args:
            responses: List of response data
            
        Returns:
            Analysis results and insights
        """
        if not self.is_enabled():
            return self._get_basic_response_analysis(responses)
        
        try:
            # Prepare data for analysis
            analysis_data = {
                'total_responses': len(responses),
                'status_codes': [r.get('status_code') for r in responses],
                'response_times': [r.get('response_time', 0) for r in responses],
                'endpoints': [r.get('url') for r in responses]
            }
            
            prompt = f"""
            Analyze these API response patterns and provide insights:
            
            Data: {json.dumps(analysis_data, indent=2)}
            
            Provide insights about:
            1. Performance patterns
            2. Error patterns
            3. Usage patterns
            4. Recommendations for improvement
            
            Respond in JSON format:
            {{
                "performance_insights": ["insight1", "insight2"],
                "error_insights": ["insight1", "insight2"],
                "usage_insights": ["insight1", "insight2"],
                "recommendations": ["rec1", "rec2"]
            }}
            """
            
            response = self.gemini_client.generate_content(prompt)
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {'analysis': response}
                
        except Exception as e:
            logger.error(f"Response pattern analysis failed: {e}")
            return self._get_basic_response_analysis(responses)
    
    def suggest_api_improvements(self, api_usage_data: Dict[str, Any]) -> List[str]:
        """
        Suggest API usage improvements based on usage patterns.
        
        Args:
            api_usage_data: Data about API usage patterns
            
        Returns:
            List of improvement suggestions
        """
        if not self.is_enabled():
            return ["AI suggestions not available"]
        
        try:
            prompt = f"""
            Based on this API usage data, suggest improvements for better API testing and usage:
            
            Usage data: {json.dumps(api_usage_data, indent=2)}
            
            Provide specific, actionable suggestions for:
            1. Performance optimization
            2. Error handling
            3. Testing strategy
            4. API design improvements
            5. Security considerations
            
            List each suggestion clearly.
            """
            
            response = self.gemini_client.generate_content(prompt)
            
            # Parse suggestions from response
            suggestions = [line.strip() for line in response.split('\n') 
                         if line.strip() and not line.strip().startswith('#')]
            
            return suggestions[:10]  # Limit to 10 suggestions
            
        except Exception as e:
            logger.error(f"API improvement suggestion failed: {e}")
            return [f"Suggestion generation failed: {str(e)}"]
    
    def explain_api_error(self, error_response: Dict[str, Any]) -> str:
        """
        Explain API error response in human terms.
        
        Args:
            error_response: Error response data
            
        Returns:
            Human-readable error explanation
        """
        if not self.is_enabled():
            return self._get_basic_error_explanation(error_response)
        
        try:
            prompt = f"""
            Explain this API error response in simple terms:
            
            Status Code: {error_response.get('status_code')}
            Response Body: {error_response.get('body', '')}
            Headers: {error_response.get('headers', {})}
            
            Provide:
            1. What went wrong
            2. Possible causes
            3. How to fix it
            4. Prevention tips
            
            Keep it concise and actionable.
            """
            
            return self.gemini_client.generate_content(prompt)
            
        except Exception as e:
            logger.error(f"Error explanation failed: {e}")
            return self._get_basic_error_explanation(error_response)
    
    def _get_method_specific_headers(self, method: str, url: str) -> Dict[str, str]:
        """Get method-specific header suggestions."""
        headers = {}
        
        # Parse URL for additional context
        parsed_url = urlparse(url)
        
        # Common headers based on method
        if method.upper() in ['POST', 'PUT', 'PATCH']:
            headers['Content-Type'] = 'application/json'
        
        # API-specific suggestions based on URL patterns
        if 'api' in parsed_url.path.lower():
            headers['Accept'] = 'application/json'
        
        if 'github' in parsed_url.netloc.lower():
            headers['User-Agent'] = 'ReqSmith-API-Tester'
        
        return headers
    
    def _looks_like_json(self, text: str) -> bool:
        """Check if text looks like JSON."""
        text = text.strip()
        return (text.startswith('{') and text.endswith('}')) or \
               (text.startswith('[') and text.endswith(']'))
    
    def _get_basic_status_explanation(self, status_code: int) -> str:
        """Get basic status code explanation without AI."""
        explanations = {
            200: "200 OK - Request successful",
            201: "201 Created - Resource created successfully",
            204: "204 No Content - Request successful, no response body",
            400: "400 Bad Request - Invalid request syntax or parameters",
            401: "401 Unauthorized - Authentication required or failed",
            403: "403 Forbidden - Access denied",
            404: "404 Not Found - Resource not found",
            405: "405 Method Not Allowed - HTTP method not supported",
            429: "429 Too Many Requests - Rate limit exceeded",
            500: "500 Internal Server Error - Server encountered an error",
            502: "502 Bad Gateway - Invalid response from upstream server",
            503: "503 Service Unavailable - Server temporarily unavailable"
        }
        
        return explanations.get(status_code, f"HTTP {status_code} - Status code explanation")
    
    def _get_basic_test_scenarios(self, endpoint_info: Dict[str, Any]) -> List[str]:
        """Get basic test scenarios without AI."""
        method = endpoint_info.get('method', 'GET').upper()
        
        scenarios = [
            f"Test {method} request with valid parameters",
            "Test with missing required parameters",
            "Test with invalid parameter values",
            "Test authentication/authorization",
            "Test rate limiting behavior"
        ]
        
        if method in ['POST', 'PUT', 'PATCH']:
            scenarios.extend([
                "Test with valid request body",
                "Test with invalid JSON body",
                "Test with missing required fields"
            ])
        
        return scenarios
    
    def _get_basic_response_analysis(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get basic response analysis without AI."""
        if not responses:
            return {'analysis': 'No responses to analyze'}
        
        status_codes = [r.get('status_code', 0) for r in responses]
        response_times = [r.get('response_time', 0) for r in responses]
        
        success_count = sum(1 for code in status_codes if 200 <= code < 300)
        error_count = len(responses) - success_count
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'total_responses': len(responses),
            'success_rate': (success_count / len(responses)) * 100,
            'error_rate': (error_count / len(responses)) * 100,
            'average_response_time': avg_response_time,
            'analysis': f"Analyzed {len(responses)} responses with {success_count} successful and {error_count} errors"
        }
    
    def _get_basic_error_explanation(self, error_response: Dict[str, Any]) -> str:
        """Get basic error explanation without AI."""
        status_code = error_response.get('status_code', 0)
        body = error_response.get('body', '')
        
        explanation = self._get_basic_status_explanation(status_code)
        
        if body:
            explanation += f"\n\nResponse details: {body[:200]}..."
        
        return explanation


class AIFeatureManager:
    """Manager for AI feature availability and configuration."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize AI feature manager.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.assistant = None
        self._initialize_assistant()
    
    def _initialize_assistant(self):
        """Initialize AI assistant if enabled."""
        if self.config.get('ai_enabled', False):
            try:
                gemini_client = GeminiClient(self.config.get('gemini_api_key'))
                self.assistant = AIAssistant(gemini_client)
                
                if not self.assistant.is_enabled():
                    logger.warning("AI assistant initialization failed")
                    self.assistant = None
                    
            except Exception as e:
                logger.error(f"Failed to initialize AI assistant: {e}")
                self.assistant = None
    
    def is_available(self) -> bool:
        """Check if AI features are available."""
        return self.assistant is not None and self.assistant.is_enabled()
    
    def get_assistant(self) -> Optional[AIAssistant]:
        """Get AI assistant instance."""
        return self.assistant
    
    def enable_ai(self, api_key: str) -> bool:
        """
        Enable AI features with API key.
        
        Args:
            api_key: Gemini API key
            
        Returns:
            True if AI was enabled successfully
        """
        try:
            self.config['ai_enabled'] = True
            self.config['gemini_api_key'] = api_key
            self._initialize_assistant()
            
            return self.is_available()
            
        except Exception as e:
            logger.error(f"Failed to enable AI: {e}")
            return False
    
    def disable_ai(self):
        """Disable AI features."""
        self.config['ai_enabled'] = False
        self.assistant = None
    
    def get_ai_status(self) -> Dict[str, Any]:
        """
        Get AI feature status.
        
        Returns:
            Dictionary with AI status information
        """
        return {
            'enabled': self.config.get('ai_enabled', False),
            'available': self.is_available(),
            'has_api_key': bool(self.config.get('gemini_api_key')),
            'features': {
                'header_suggestions': self.is_available(),
                'status_explanations': self.is_available(),
                'json_validation': self.is_available(),
                'openapi_examples': self.is_available(),
                'test_suggestions': self.is_available()
            }
        }