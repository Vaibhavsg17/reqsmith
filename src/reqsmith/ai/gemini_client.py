"""
Google Gemini API client for AI-powered features.
"""
import os
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of AI validation."""
    is_valid: bool
    suggestions: List[str]
    corrected_content: Optional[str] = None
    confidence: float = 0.0
    explanation: str = ""


class GeminiClient:
    """Client for Google Gemini AI API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Gemini API key (will try environment variable and config if None)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        # If no API key from env, try config
        if not self.api_key:
            try:
                from ..config.settings import get_config
                config = get_config()
                self.api_key = config.get_gemini_api_key()
            except Exception:
                pass
        
        self.model = None
        self._available = False
        
        if not GEMINI_AVAILABLE:
            logger.warning("google-generativeai package not installed. AI features disabled.")
            return
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Try the newer model names first
                try:
                    self.model = genai.GenerativeModel('gemini-1.5-flash')
                except:
                    try:
                        self.model = genai.GenerativeModel('gemini-1.5-pro')
                    except:
                        self.model = genai.GenerativeModel('gemini-pro')
                self._available = True
                logger.info("Gemini AI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self._available = False
        else:
            logger.info("No Gemini API key provided. AI features disabled.")
    
    def is_available(self) -> bool:
        """
        Check if Gemini AI is available.
        
        Returns:
            True if Gemini client is ready to use
        """
        return self._available and self.model is not None
    
    def generate_content(self, prompt: str, context: Optional[str] = None) -> str:
        """
        Generate content using Gemini.
        
        Args:
            prompt: The prompt to send to Gemini
            context: Optional context to include
            
        Returns:
            Generated content
            
        Raises:
            RuntimeError: If Gemini is not available
            Exception: If generation fails
        """
        if not self.is_available():
            raise RuntimeError("Gemini AI is not available")
        
        try:
            full_prompt = prompt
            if context:
                full_prompt = f"Context: {context}\n\nPrompt: {prompt}"
            
            response = self.model.generate_content(full_prompt)
            
            if response.text:
                return response.text.strip()
            else:
                raise Exception("Empty response from Gemini")
                
        except Exception as e:
            logger.error(f"Gemini content generation failed: {e}")
            return None
    
    def validate_json(self, json_str: str) -> ValidationResult:
        """
        Validate and suggest corrections for JSON using Gemini.
        
        Args:
            json_str: JSON string to validate
            
        Returns:
            ValidationResult with validation details
        """
        if not self.is_available():
            return ValidationResult(
                is_valid=False,
                suggestions=["Gemini AI not available for validation"],
                explanation="AI validation requires Gemini API key"
            )
        
        # First try basic JSON validation
        try:
            json.loads(json_str)
            return ValidationResult(
                is_valid=True,
                suggestions=[],
                explanation="JSON is valid"
            )
        except json.JSONDecodeError as e:
            # Use Gemini to suggest corrections
            prompt = f"""
            The following JSON is invalid: {str(e)}
            
            JSON content:
            {json_str}
            
            Please:
            1. Identify the specific issues
            2. Provide a corrected version
            3. Explain what was wrong
            4. Give suggestions to avoid similar errors
            
            Respond in this format:
            ISSUES: [list of issues]
            CORRECTED: [corrected JSON]
            EXPLANATION: [explanation]
            SUGGESTIONS: [suggestions]
            """
            
            try:
                response = self.generate_content(prompt)
                return self._parse_validation_response(response, False)
            except Exception as ai_error:
                logger.error(f"AI validation failed: {ai_error}")
                return ValidationResult(
                    is_valid=False,
                    suggestions=[f"JSON error: {str(e)}", "AI validation unavailable"],
                    explanation=f"JSON parsing failed: {str(e)}"
                )
    
    def analyze_api_endpoint(self, url: str, method: str) -> Dict[str, Any]:
        """
        Analyze API endpoint and suggest headers/parameters.
        
        Args:
            url: API endpoint URL
            method: HTTP method
            
        Returns:
            Dictionary with analysis and suggestions
        """
        if not self.is_available():
            return {
                'suggested_headers': {},
                'suggested_params': {},
                'analysis': 'AI analysis not available',
                'confidence': 0.0
            }
        
        prompt = f"""
        Analyze this API endpoint and suggest appropriate headers and parameters:
        
        Method: {method}
        URL: {url}
        
        Based on the URL pattern and method, suggest:
        1. Common headers that might be required
        2. Likely query parameters
        3. Authentication requirements
        4. Content-Type suggestions
        
        Respond in JSON format:
        {{
            "suggested_headers": {{"header": "value"}},
            "suggested_params": {{"param": "description"}},
            "auth_suggestions": ["suggestion1", "suggestion2"],
            "content_type": "suggested content type",
            "analysis": "brief analysis",
            "confidence": 0.8
        }}
        """
        
        try:
            response = self.generate_content(prompt)
            # Try to parse JSON response
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Fallback if response isn't valid JSON
                return {
                    'suggested_headers': {},
                    'suggested_params': {},
                    'analysis': response,
                    'confidence': 0.5
                }
        except Exception as e:
            logger.error(f"API endpoint analysis failed: {e}")
            return {
                'suggested_headers': {},
                'suggested_params': {},
                'analysis': f'Analysis failed: {str(e)}',
                'confidence': 0.0
            }
    
    def explain_status_code(self, status_code: int, context: Optional[str] = None) -> str:
        """
        Explain HTTP status code in human-readable terms.
        
        Args:
            status_code: HTTP status code
            context: Optional context about the request
            
        Returns:
            Human-readable explanation
        """
        if not self.is_available():
            return f"HTTP {status_code} - AI explanation not available"
        
        prompt = f"""
        Explain HTTP status code {status_code} in simple, human-readable terms.
        
        Include:
        1. What this status code means
        2. Common causes
        3. Suggested actions for developers
        4. Whether this indicates success, client error, or server error
        
        {f"Request context: {context}" if context else ""}
        
        Keep the explanation concise but helpful.
        """
        
        try:
            return self.generate_content(prompt)
        except Exception as e:
            logger.error(f"Status code explanation failed: {e}")
            return f"HTTP {status_code} - Unable to generate AI explanation"
    
    def generate_examples_from_openapi(self, spec: Dict[str, Any], endpoint: str) -> List[Dict[str, Any]]:
        """
        Generate request examples from OpenAPI specification.
        
        Args:
            spec: OpenAPI specification dictionary
            endpoint: Specific endpoint to generate examples for
            
        Returns:
            List of example requests
        """
        if not self.is_available():
            return []
        
        prompt = f"""
        Based on this OpenAPI specification, generate example requests for the endpoint: {endpoint}
        
        OpenAPI spec (relevant parts):
        {json.dumps(spec, indent=2)[:2000]}  # Limit size
        
        Generate 2-3 realistic example requests including:
        1. Required parameters
        2. Optional parameters
        3. Request body examples
        4. Different scenarios (success cases)
        
        Respond in JSON format as an array of request objects:
        [
            {{
                "method": "GET",
                "url": "/api/users/123",
                "headers": {{"Authorization": "Bearer token"}},
                "body": null,
                "description": "Get user by ID"
            }}
        ]
        """
        
        try:
            response = self.generate_content(prompt)
            try:
                examples = json.loads(response)
                return examples if isinstance(examples, list) else []
            except json.JSONDecodeError:
                logger.error("Failed to parse OpenAPI examples response as JSON")
                return []
        except Exception as e:
            logger.error(f"OpenAPI example generation failed: {e}")
            return []
    
    def suggest_test_cases(self, endpoint_info: Dict[str, Any]) -> List[str]:
        """
        Suggest test cases for an API endpoint.
        
        Args:
            endpoint_info: Information about the endpoint
            
        Returns:
            List of test case suggestions
        """
        if not self.is_available():
            return ["AI test suggestions not available"]
        
        prompt = f"""
        Based on this API endpoint information, suggest comprehensive test cases:
        
        Endpoint info:
        {json.dumps(endpoint_info, indent=2)}
        
        Suggest test cases covering:
        1. Happy path scenarios
        2. Edge cases
        3. Error conditions
        4. Security considerations
        5. Performance considerations
        
        Provide a list of specific, actionable test cases.
        """
        
        try:
            response = self.generate_content(prompt)
            # Split response into individual test cases
            test_cases = [line.strip() for line in response.split('\n') 
                         if line.strip() and not line.strip().startswith('#')]
            return test_cases[:10]  # Limit to 10 suggestions
        except Exception as e:
            logger.error(f"Test case suggestion failed: {e}")
            return [f"Test suggestion failed: {str(e)}"]
    
    def _parse_validation_response(self, response: str, is_valid: bool) -> ValidationResult:
        """Parse Gemini validation response into ValidationResult."""
        try:
            lines = response.split('\n')
            issues = []
            corrected = None
            explanation = ""
            suggestions = []
            
            current_section = None
            for line in lines:
                line = line.strip()
                if line.startswith('ISSUES:'):
                    current_section = 'issues'
                    issues.append(line[7:].strip())
                elif line.startswith('CORRECTED:'):
                    current_section = 'corrected'
                    corrected = line[10:].strip()
                elif line.startswith('EXPLANATION:'):
                    current_section = 'explanation'
                    explanation = line[12:].strip()
                elif line.startswith('SUGGESTIONS:'):
                    current_section = 'suggestions'
                    suggestions.append(line[12:].strip())
                elif line and current_section:
                    if current_section == 'issues':
                        issues.append(line)
                    elif current_section == 'corrected':
                        corrected = (corrected + '\n' + line) if corrected else line
                    elif current_section == 'explanation':
                        explanation = (explanation + ' ' + line) if explanation else line
                    elif current_section == 'suggestions':
                        suggestions.append(line)
            
            return ValidationResult(
                is_valid=is_valid,
                suggestions=suggestions or issues,
                corrected_content=corrected,
                confidence=0.8,
                explanation=explanation
            )
            
        except Exception as e:
            logger.error(f"Failed to parse validation response: {e}")
            return ValidationResult(
                is_valid=is_valid,
                suggestions=["Failed to parse AI response"],
                explanation="AI response parsing failed"
            )


class SecureKeyManager:
    """Secure management of API keys."""
    
    def __init__(self, storage_path: str):
        """
        Initialize key manager.
        
        Args:
            storage_path: Path to store encrypted keys
        """
        self.storage_path = storage_path
        self._ensure_storage_dir()
    
    def store_api_key(self, key: str, service: str = "gemini") -> bool:
        """
        Store API key securely.
        
        Args:
            key: API key to store
            service: Service name (default: gemini)
            
        Returns:
            True if key was stored successfully
        """
        try:
            # In a real implementation, this would use proper encryption
            # For now, we'll use basic encoding (NOT secure for production)
            import base64
            
            encoded_key = base64.b64encode(key.encode()).decode()
            key_file = os.path.join(self.storage_path, f"{service}_key.enc")
            
            with open(key_file, 'w') as f:
                f.write(encoded_key)
            
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            
            logger.info(f"API key for {service} stored securely")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store API key: {e}")
            return False
    
    def load_api_key(self, service: str = "gemini") -> Optional[str]:
        """
        Load API key securely.
        
        Args:
            service: Service name (default: gemini)
            
        Returns:
            Decrypted API key or None if not found
        """
        try:
            key_file = os.path.join(self.storage_path, f"{service}_key.enc")
            
            if not os.path.exists(key_file):
                return None
            
            with open(key_file, 'r') as f:
                encoded_key = f.read().strip()
            
            # Decode the key (NOT secure for production)
            import base64
            decoded_key = base64.b64decode(encoded_key.encode()).decode()
            
            return decoded_key
            
        except Exception as e:
            logger.error(f"Failed to load API key: {e}")
            return None
    
    def delete_api_key(self, service: str = "gemini") -> bool:
        """
        Delete stored API key.
        
        Args:
            service: Service name (default: gemini)
            
        Returns:
            True if key was deleted successfully
        """
        try:
            key_file = os.path.join(self.storage_path, f"{service}_key.enc")
            
            if os.path.exists(key_file):
                os.remove(key_file)
                logger.info(f"API key for {service} deleted")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete API key: {e}")
            return False
    
    def has_api_key(self, service: str = "gemini") -> bool:
        """
        Check if API key exists for service.
        
        Args:
            service: Service name (default: gemini)
            
        Returns:
            True if API key exists
        """
        key_file = os.path.join(self.storage_path, f"{service}_key.enc")
        return os.path.exists(key_file)
    
    def _ensure_storage_dir(self):
        """Ensure storage directory exists with proper permissions."""
        try:
            os.makedirs(self.storage_path, mode=0o700, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create key storage directory: {e}")


def check_gemini_availability() -> tuple[bool, str]:
    """
    Check if Gemini AI is available.
    
    Returns:
        Tuple of (is_available, status_message)
    """
    if not GEMINI_AVAILABLE:
        return False, "google-generativeai package not installed"
    
    # Try to get API key from environment first, then config
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        try:
            from ..config.settings import get_config
            config = get_config()
            api_key = config.get_gemini_api_key()
        except Exception:
            pass
    
    if not api_key:
        return False, "GEMINI_API_KEY environment variable not set and no API key in configuration"
    
    try:
        # Test connection
        genai.configure(api_key=api_key)
        # Try the newer model names first
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
        except:
            try:
                model = genai.GenerativeModel('gemini-1.5-pro')
            except:
                model = genai.GenerativeModel('gemini-pro')
        
        # Simple test
        response = model.generate_content("Hello")
        if response.text:
            return True, "Gemini AI is available and working"
        else:
            return False, "Gemini API test failed"
            
    except Exception as e:
        return False, f"Gemini connection failed: {str(e)}"