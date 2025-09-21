"""
Request validation and preprocessing utilities.
"""
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, Tuple, Union
from urllib.parse import urlparse, parse_qs
import mimetypes
import os
import logging


logger = logging.getLogger(__name__)


class RequestValidator:
    """Validates and preprocesses HTTP requests."""
    
    @staticmethod
    def validate_url(url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate URL format and accessibility.
        
        Args:
            url: URL to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url or not url.strip():
            return False, "URL cannot be empty"
        
        try:
            parsed = urlparse(url.strip())
            
            # Check for scheme
            if not parsed.scheme:
                return False, "URL must include a scheme (http:// or https://)"
            
            # Check for valid schemes
            if parsed.scheme.lower() not in ['http', 'https']:
                return False, f"Unsupported scheme: {parsed.scheme}"
            
            # Check for hostname
            if not parsed.netloc:
                return False, "URL must include a hostname"
            
            return True, None
            
        except Exception as e:
            return False, f"Invalid URL format: {e}"
    
    @staticmethod
    def validate_method(method: str) -> Tuple[bool, Optional[str]]:
        """
        Validate HTTP method.
        
        Args:
            method: HTTP method to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not method or not method.strip():
            return False, "HTTP method cannot be empty"
        
        valid_methods = {
            'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 
            'OPTIONS', 'HEAD', 'TRACE', 'CONNECT'
        }
        
        method = method.upper().strip()
        
        if method not in valid_methods:
            return False, f"Unsupported HTTP method: {method}"
        
        return True, None
    
    @staticmethod
    def validate_headers(headers: Dict[str, str]) -> Tuple[bool, Optional[str]]:
        """
        Validate HTTP headers.
        
        Args:
            headers: Dictionary of headers to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(headers, dict):
            return False, "Headers must be a dictionary"
        
        for key, value in headers.items():
            # Check key format
            if not isinstance(key, str) or not key.strip():
                return False, f"Header key must be a non-empty string: {key}"
            
            # Check value format
            if not isinstance(value, str):
                return False, f"Header value must be a string: {key}={value}"
            
            # Check for invalid characters in header names
            invalid_chars = [' ', '\t', '\n', '\r', ':', '(', ')', '<', '>', '@', 
                           ',', ';', '\\', '"', '/', '[', ']', '?', '=', '{', '}']
            
            for char in invalid_chars:
                if char in key:
                    return False, f"Invalid character '{char}' in header name: {key}"
        
        return True, None
    
    @staticmethod
    def validate_json_body(body: str) -> Tuple[bool, Optional[str], Optional[Any]]:
        """
        Validate JSON request body.
        
        Args:
            body: JSON string to validate
            
        Returns:
            Tuple of (is_valid, error_message, parsed_json)
        """
        if not body or not body.strip():
            return True, None, None
        
        try:
            parsed = json.loads(body)
            return True, None, parsed
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}", None
    
    @staticmethod
    def validate_xml_body(body: str) -> Tuple[bool, Optional[str]]:
        """
        Validate XML request body.
        
        Args:
            body: XML string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not body or not body.strip():
            return True, None
        
        try:
            ET.fromstring(body)
            return True, None
        except ET.ParseError as e:
            return False, f"Invalid XML: {e}"
    
    @staticmethod
    def validate_method_body_combination(method: str, body: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate method and body combination.
        
        Args:
            method: HTTP method
            body: Request body
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        method = method.upper()
        
        # Methods that typically don't have bodies
        no_body_methods = {'GET', 'HEAD', 'DELETE', 'OPTIONS'}
        
        # Methods that typically have bodies
        body_methods = {'POST', 'PUT', 'PATCH'}
        
        if method in no_body_methods and body and body.strip():
            return False, f"{method} requests typically should not have a body"
        
        if method in body_methods and not body:
            # This is a warning, not an error
            logger.warning(f"{method} requests typically should have a body")
        
        return True, None


class RequestPreprocessor:
    """Preprocesses requests before sending."""
    
    @staticmethod
    def detect_content_type(body: str, file_path: Optional[str] = None) -> Optional[str]:
        """
        Detect content type from body content or file extension.
        
        Args:
            body: Request body content
            file_path: Optional file path for extension-based detection
            
        Returns:
            Detected content type or None
        """
        # File extension based detection
        if file_path:
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type:
                return content_type
        
        # Content-based detection
        if not body or not body.strip():
            return None
        
        body = body.strip()
        
        # JSON detection
        if (body.startswith('{') and body.endswith('}')) or \
           (body.startswith('[') and body.endswith(']')):
            try:
                json.loads(body)
                return 'application/json'
            except json.JSONDecodeError:
                pass
        
        # XML detection
        if body.startswith('<?xml') or body.startswith('<'):
            try:
                ET.fromstring(body)
                return 'application/xml'
            except ET.ParseError:
                pass
        
        # Form data detection
        if '=' in body and '&' in body:
            return 'application/x-www-form-urlencoded'
        
        # Default to plain text
        return 'text/plain'
    
    @staticmethod
    def auto_add_headers(headers: Dict[str, str], method: str, 
                        body: Optional[str] = None, 
                        file_path: Optional[str] = None) -> Dict[str, str]:
        """
        Automatically add common headers based on request characteristics.
        
        Args:
            headers: Existing headers
            method: HTTP method
            body: Request body
            file_path: Optional file path
            
        Returns:
            Updated headers dictionary
        """
        updated_headers = headers.copy()
        
        # Add Content-Type if not present and body exists
        if body and 'Content-Type' not in updated_headers:
            content_type = RequestPreprocessor.detect_content_type(body, file_path)
            if content_type:
                updated_headers['Content-Type'] = content_type
        
        # Add Content-Length if not present and body exists
        if body and 'Content-Length' not in updated_headers:
            updated_headers['Content-Length'] = str(len(body.encode('utf-8')))
        
        # Add Accept header if not present
        if 'Accept' not in updated_headers:
            updated_headers['Accept'] = 'application/json, application/xml, text/plain, */*'
        
        # Add User-Agent if not present
        if 'User-Agent' not in updated_headers:
            updated_headers['User-Agent'] = 'ReqSmith-API-Tester/1.0'
        
        return updated_headers
    
    @staticmethod
    def process_form_data(data: Dict[str, str]) -> Tuple[str, str]:
        """
        Process form data into URL-encoded format.
        
        Args:
            data: Form data dictionary
            
        Returns:
            Tuple of (encoded_body, content_type)
        """
        from urllib.parse import urlencode
        
        encoded = urlencode(data)
        return encoded, 'application/x-www-form-urlencoded'
    
    @staticmethod
    def load_body_from_file(file_path: str) -> Tuple[str, Optional[str]]:
        """
        Load request body from file.
        
        Args:
            file_path: Path to file containing request body
            
        Returns:
            Tuple of (body_content, detected_content_type)
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be read
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Request body file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            content_type = RequestPreprocessor.detect_content_type(content, file_path)
            return content, content_type
            
        except UnicodeDecodeError:
            # Try binary mode for non-text files
            try:
                with open(file_path, 'rb') as f:
                    content = f.read().decode('utf-8', errors='replace')
                
                content_type = RequestPreprocessor.detect_content_type(content, file_path)
                return content, content_type
                
            except Exception as e:
                raise ValueError(f"Cannot read file {file_path}: {e}")
        
        except Exception as e:
            raise ValueError(f"Error reading file {file_path}: {e}")
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize URL format.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        url = url.strip()
        
        # Add scheme if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Remove trailing slash unless it's the root
        if url.endswith('/') and url.count('/') > 3:
            url = url.rstrip('/')
        
        return url
    
    @staticmethod
    def parse_curl_command(curl_command: str) -> Dict[str, Any]:
        """
        Parse a curl command into request components.
        
        Args:
            curl_command: Curl command string
            
        Returns:
            Dictionary with parsed request components
        """
        import shlex
        
        # Remove 'curl' from the beginning
        if curl_command.strip().startswith('curl'):
            curl_command = curl_command.strip()[4:].strip()
        
        try:
            # Parse command line arguments
            args = shlex.split(curl_command)
        except ValueError as e:
            raise ValueError(f"Invalid curl command syntax: {e}")
        
        request_data = {
            'method': 'GET',
            'url': '',
            'headers': {},
            'body': '',
            'params': {}
        }
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            if arg in ['-X', '--request']:
                if i + 1 < len(args):
                    request_data['method'] = args[i + 1].upper()
                    i += 1
            
            elif arg in ['-H', '--header']:
                if i + 1 < len(args):
                    header = args[i + 1]
                    if ':' in header:
                        key, value = header.split(':', 1)
                        request_data['headers'][key.strip()] = value.strip()
                    i += 1
            
            elif arg in ['-d', '--data', '--data-raw']:
                if i + 1 < len(args):
                    request_data['body'] = args[i + 1]
                    if request_data['method'] == 'GET':
                        request_data['method'] = 'POST'
                    i += 1
            
            elif arg in ['-G', '--get']:
                request_data['method'] = 'GET'
            
            elif not arg.startswith('-'):
                # This should be the URL
                request_data['url'] = arg
            
            i += 1
        
        return request_data


class RequestBuilder:
    """Builds complete request objects with validation."""
    
    def __init__(self):
        self.validator = RequestValidator()
        self.preprocessor = RequestPreprocessor()
    
    def build_request(self, method: str, url: str,
                     headers: Optional[Dict[str, str]] = None,
                     body: Optional[str] = None,
                     params: Optional[Dict[str, str]] = None,
                     body_file: Optional[str] = None,
                     auto_headers: bool = True) -> Dict[str, Any]:
        """
        Build and validate a complete request.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            params: Query parameters
            body_file: Path to file containing request body
            auto_headers: Whether to automatically add common headers
            
        Returns:
            Dictionary with validated request data
            
        Raises:
            ValueError: If request validation fails
        """
        # Load body from file if specified
        if body_file:
            body, detected_content_type = self.preprocessor.load_body_from_file(body_file)
            if not headers:
                headers = {}
            if 'Content-Type' not in headers and detected_content_type:
                headers['Content-Type'] = detected_content_type
        
        # Initialize defaults
        headers = headers or {}
        params = params or {}
        
        # Normalize URL
        url = self.preprocessor.normalize_url(url)
        
        # Validate components
        url_valid, url_error = self.validator.validate_url(url)
        if not url_valid:
            raise ValueError(f"Invalid URL: {url_error}")
        
        method_valid, method_error = self.validator.validate_method(method)
        if not method_valid:
            raise ValueError(f"Invalid method: {method_error}")
        
        headers_valid, headers_error = self.validator.validate_headers(headers)
        if not headers_valid:
            raise ValueError(f"Invalid headers: {headers_error}")
        
        # Validate method-body combination
        combo_valid, combo_error = self.validator.validate_method_body_combination(method, body)
        if not combo_valid:
            raise ValueError(f"Invalid method-body combination: {combo_error}")
        
        # Validate body based on content type
        if body and headers.get('Content-Type', '').startswith('application/json'):
            json_valid, json_error, _ = self.validator.validate_json_body(body)
            if not json_valid:
                raise ValueError(f"Invalid JSON body: {json_error}")
        
        elif body and headers.get('Content-Type', '').startswith('application/xml'):
            xml_valid, xml_error = self.validator.validate_xml_body(body)
            if not xml_valid:
                raise ValueError(f"Invalid XML body: {xml_error}")
        
        # Auto-add headers if requested
        if auto_headers:
            headers = self.preprocessor.auto_add_headers(headers, method, body, body_file)
        
        return {
            'method': method.upper(),
            'url': url,
            'headers': headers,
            'body': body or '',
            'params': params
        }