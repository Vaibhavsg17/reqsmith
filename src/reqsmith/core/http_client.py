"""
HTTP client for making API requests with retry and timeout support.
"""
import time
import json
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
import httpx
import logging


logger = logging.getLogger(__name__)


@dataclass
class Response:
    """Response object containing request and response data."""
    
    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    url: str
    method: str
    request_headers: Dict[str, str]
    request_body: str
    elapsed_time: float
    size_bytes: int
    
    def json(self) -> Any:
        """Parse response as JSON."""
        try:
            return json.loads(self.text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")
    
    def is_success(self) -> bool:
        """Check if response indicates success (2xx status)."""
        return 200 <= self.status_code < 300
    
    def is_redirect(self) -> bool:
        """Check if response is a redirect (3xx status)."""
        return 300 <= self.status_code < 400
    
    def is_client_error(self) -> bool:
        """Check if response is a client error (4xx status)."""
        return 400 <= self.status_code < 500
    
    def is_server_error(self) -> bool:
        """Check if response is a server error (5xx status)."""
        return 500 <= self.status_code < 600


class HTTPClient:
    """HTTP client with support for various methods, retries, and timeouts."""
    
    def __init__(self, timeout: int = 30, retry_attempts: int = 3, 
                 default_headers: Optional[Dict[str, str]] = None):
        """
        Initialize HTTP client.
        
        Args:
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts for failed requests
            default_headers: Default headers to include in all requests
        """
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.default_headers = default_headers or {}
        
        # Create httpx client with configuration
        self.client = httpx.Client(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            verify=True  # SSL verification enabled by default
        )
    
    def send_request(self, method: str, url: str, 
                    headers: Optional[Dict[str, str]] = None,
                    body: Optional[str] = None,
                    params: Optional[Dict[str, str]] = None,
                    files: Optional[Dict[str, Any]] = None) -> Response:
        """
        Send HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            url: Request URL
            headers: Request headers
            body: Request body
            params: Query parameters
            files: Files to upload
            
        Returns:
            Response object
            
        Raises:
            httpx.RequestError: For network-related errors
            ValueError: For invalid parameters
        """
        method = method.upper()
        if not self._validate_method(method):
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        if not self._validate_url(url):
            raise ValueError(f"Invalid URL: {url}")
        
        # Merge headers
        request_headers = self.default_headers.copy()
        if headers:
            request_headers.update(headers)
        
        # Prepare request data
        request_data = self._prepare_request_data(body, files)
        
        # Retry logic
        last_exception = None
        for attempt in range(self.retry_attempts + 1):
            try:
                start_time = time.time()
                
                # Make the request
                response = self.client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    params=params,
                    **request_data
                )
                
                elapsed_time = time.time() - start_time
                
                # Create response object
                return self._create_response(
                    response, method, url, request_headers, 
                    body or "", elapsed_time
                )
                
            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < self.retry_attempts:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {self.retry_attempts + 1} attempts: {e}")
        
        # If we get here, all retries failed
        raise last_exception
    
    def get(self, url: str, headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, str]] = None) -> Response:
        """Send GET request."""
        return self.send_request("GET", url, headers=headers, params=params)
    
    def post(self, url: str, headers: Optional[Dict[str, str]] = None,
             body: Optional[str] = None, params: Optional[Dict[str, str]] = None,
             files: Optional[Dict[str, Any]] = None) -> Response:
        """Send POST request."""
        return self.send_request("POST", url, headers=headers, body=body, 
                               params=params, files=files)
    
    def put(self, url: str, headers: Optional[Dict[str, str]] = None,
            body: Optional[str] = None, params: Optional[Dict[str, str]] = None) -> Response:
        """Send PUT request."""
        return self.send_request("PUT", url, headers=headers, body=body, params=params)
    
    def patch(self, url: str, headers: Optional[Dict[str, str]] = None,
              body: Optional[str] = None, params: Optional[Dict[str, str]] = None) -> Response:
        """Send PATCH request."""
        return self.send_request("PATCH", url, headers=headers, body=body, params=params)
    
    def delete(self, url: str, headers: Optional[Dict[str, str]] = None,
               params: Optional[Dict[str, str]] = None) -> Response:
        """Send DELETE request."""
        return self.send_request("DELETE", url, headers=headers, params=params)
    
    def options(self, url: str, headers: Optional[Dict[str, str]] = None,
                params: Optional[Dict[str, str]] = None) -> Response:
        """Send OPTIONS request."""
        return self.send_request("OPTIONS", url, headers=headers, params=params)
    
    def head(self, url: str, headers: Optional[Dict[str, str]] = None,
             params: Optional[Dict[str, str]] = None) -> Response:
        """Send HEAD request."""
        return self.send_request("HEAD", url, headers=headers, params=params)
    
    def send_graphql_query(self, url: str, query: str,
                          variables: Optional[Dict[str, Any]] = None,
                          headers: Optional[Dict[str, str]] = None,
                          operation_name: Optional[str] = None) -> Response:
        """
        Send GraphQL query or mutation.
        
        Args:
            url: GraphQL endpoint URL
            query: GraphQL query or mutation string
            variables: GraphQL variables
            headers: Request headers
            operation_name: Operation name for multi-operation documents
            
        Returns:
            Response object
        """
        # Validate GraphQL query
        if not self._validate_graphql_query(query):
            raise ValueError("Invalid GraphQL query syntax")
        
        # Prepare GraphQL request payload
        payload = {
            "query": query
        }
        
        if variables:
            payload["variables"] = variables
        
        if operation_name:
            payload["operationName"] = operation_name
        
        # Set GraphQL headers
        graphql_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if headers:
            graphql_headers.update(headers)
        
        # Send POST request with GraphQL payload
        body = json.dumps(payload)
        return self.send_request("POST", url, headers=graphql_headers, body=body)
    
    def send_graphql_mutation(self, url: str, mutation: str,
                             variables: Optional[Dict[str, Any]] = None,
                             headers: Optional[Dict[str, str]] = None) -> Response:
        """
        Send GraphQL mutation (convenience method).
        
        Args:
            url: GraphQL endpoint URL
            mutation: GraphQL mutation string
            variables: GraphQL variables
            headers: Request headers
            
        Returns:
            Response object
        """
        return self.send_graphql_query(url, mutation, variables, headers)
    
    def validate_request(self, method: str, url: str, 
                        headers: Optional[Dict[str, str]] = None,
                        body: Optional[str] = None) -> bool:
        """
        Validate request parameters without sending.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            
        Returns:
            True if request is valid
        """
        try:
            # Validate method
            if not self._validate_method(method.upper()):
                return False
            
            # Validate URL
            if not self._validate_url(url):
                return False
            
            # Validate headers
            if headers:
                for key, value in headers.items():
                    if not isinstance(key, str) or not isinstance(value, str):
                        return False
            
            # Validate body for JSON content
            if body and headers and headers.get('Content-Type', '').startswith('application/json'):
                try:
                    json.loads(body)
                except json.JSONDecodeError:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def _validate_method(self, method: str) -> bool:
        """Validate HTTP method."""
        valid_methods = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'}
        return method.upper() in valid_methods
    
    def _validate_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            # Use httpx's URL validation
            parsed = httpx.URL(url)
            # Ensure it has a valid scheme and host
            return bool(parsed.scheme in ('http', 'https') and parsed.host)
        except Exception:
            return False
    
    def _prepare_request_data(self, body: Optional[str], 
                            files: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare request data based on content type."""
        request_data = {}
        
        if files:
            request_data['files'] = files
        elif body:
            request_data['content'] = body.encode('utf-8')
        
        return request_data
    
    def _create_response(self, httpx_response: httpx.Response, method: str, 
                        url: str, request_headers: Dict[str, str], 
                        request_body: str, elapsed_time: float) -> Response:
        """Create Response object from httpx response."""
        return Response(
            status_code=httpx_response.status_code,
            headers=dict(httpx_response.headers),
            content=httpx_response.content,
            text=httpx_response.text,
            url=str(httpx_response.url),
            method=method,
            request_headers=request_headers,
            request_body=request_body,
            elapsed_time=elapsed_time,
            size_bytes=len(httpx_response.content)
        )


class FileHTTPClient(HTTPClient):
    """Extended HTTP client with file-based request body support."""
    
    def send_request_from_file(self, method: str, url: str,
                              body_file: str,
                              headers: Optional[Dict[str, str]] = None,
                              params: Optional[Dict[str, str]] = None) -> Response:
        """
        Send request with body loaded from file.
        
        Args:
            method: HTTP method
            url: Request URL
            body_file: Path to file containing request body
            headers: Request headers
            params: Query parameters
            
        Returns:
            Response object
        """
        try:
            with open(body_file, 'r', encoding='utf-8') as f:
                body = f.read()
            
            # Auto-detect content type if not specified
            if headers is None:
                headers = {}
            
            if 'Content-Type' not in headers:
                content_type = self._detect_content_type(body_file, body)
                if content_type:
                    headers['Content-Type'] = content_type
            
            return self.send_request(method, url, headers=headers, 
                                   body=body, params=params)
            
        except FileNotFoundError:
            raise ValueError(f"Request body file not found: {body_file}")
        except Exception as e:
            raise ValueError(f"Failed to read request body file: {e}")
    
    def _detect_content_type(self, file_path: str, content: str) -> Optional[str]:
        """Detect content type based on file extension and content."""
        import os
        
        _, ext = os.path.splitext(file_path.lower())
        
        # File extension based detection
        if ext == '.json':
            return 'application/json'
        elif ext == '.xml':
            return 'application/xml'
        elif ext == '.txt':
            return 'text/plain'
        elif ext == '.html':
            return 'text/html'
        elif ext == '.graphql' or ext == '.gql':
            return 'application/json'  # GraphQL queries are sent as JSON
        
        # Content-based detection
        try:
            json.loads(content)
            return 'application/json'
        except json.JSONDecodeError:
            pass
        
        if content.strip().startswith('<?xml'):
            return 'application/xml'
        
        # Check if content looks like GraphQL
        if self._looks_like_graphql(content):
            return 'application/json'
        
        return 'text/plain'
    
    def _validate_graphql_query(self, query: str) -> bool:
        """
        Basic GraphQL query validation.
        
        Args:
            query: GraphQL query string
            
        Returns:
            True if query appears to be valid GraphQL
        """
        if not query or not query.strip():
            return False
        
        query = query.strip()
        
        # Check for basic GraphQL structure
        if not ('{' in query and '}' in query):
            return False
        
        # Check for GraphQL keywords
        graphql_keywords = ['query', 'mutation', 'subscription', 'fragment']
        has_keyword = any(keyword in query.lower() for keyword in graphql_keywords)
        
        # If no explicit keyword, check if it looks like a query
        if not has_keyword:
            # Anonymous queries are valid if they start with '{'
            if not query.startswith('{'):
                return False
        
        # Basic bracket matching
        open_brackets = query.count('{')
        close_brackets = query.count('}')
        
        if open_brackets != close_brackets:
            return False
        
        # Check for invalid characters that would break GraphQL
        invalid_chars = ['<', '>', '&']
        for char in invalid_chars:
            if char in query:
                return False
        
        return True


class GraphQLClient(HTTPClient):
    """Specialized HTTP client for GraphQL operations."""
    
    def __init__(self, endpoint_url: str, **kwargs):
        """
        Initialize GraphQL client.
        
        Args:
            endpoint_url: GraphQL endpoint URL
            **kwargs: Additional HTTPClient arguments
        """
        super().__init__(**kwargs)
        self.endpoint_url = endpoint_url
        
        # Set default GraphQL headers
        self.default_headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def query(self, query: str, variables: Optional[Dict[str, Any]] = None,
              headers: Optional[Dict[str, str]] = None) -> Response:
        """
        Execute GraphQL query.
        
        Args:
            query: GraphQL query string
            variables: Query variables
            headers: Additional headers
            
        Returns:
            Response object
        """
        return self.send_graphql_query(self.endpoint_url, query, variables, headers)
    
    def mutate(self, mutation: str, variables: Optional[Dict[str, Any]] = None,
               headers: Optional[Dict[str, str]] = None) -> Response:
        """
        Execute GraphQL mutation.
        
        Args:
            mutation: GraphQL mutation string
            variables: Mutation variables
            headers: Additional headers
            
        Returns:
            Response object
        """
        return self.send_graphql_mutation(self.endpoint_url, mutation, variables, headers)
    
    def introspect(self, headers: Optional[Dict[str, str]] = None) -> Response:
        """
        Perform GraphQL introspection query.
        
        Args:
            headers: Additional headers
            
        Returns:
            Response object with schema information
        """
        introspection_query = """
        query IntrospectionQuery {
          __schema {
            queryType { name }
            mutationType { name }
            subscriptionType { name }
            types {
              ...FullType
            }
            directives {
              name
              description
              locations
              args {
                ...InputValue
              }
            }
          }
        }
        
        fragment FullType on __Type {
          kind
          name
          description
          fields(includeDeprecated: true) {
            name
            description
            args {
              ...InputValue
            }
            type {
              ...TypeRef
            }
            isDeprecated
            deprecationReason
          }
          inputFields {
            ...InputValue
          }
          interfaces {
            ...TypeRef
          }
          enumValues(includeDeprecated: true) {
            name
            description
            isDeprecated
            deprecationReason
          }
          possibleTypes {
            ...TypeRef
          }
        }
        
        fragment InputValue on __InputValue {
          name
          description
          type { ...TypeRef }
          defaultValue
        }
        
        fragment TypeRef on __Type {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                  ofType {
                    kind
                    name
                    ofType {
                      kind
                      name
                      ofType {
                        kind
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        return self.query(introspection_query, headers=headers)
    
    def _validate_graphql_query(self, query: str) -> bool:
        """
        Validate GraphQL query syntax.
        
        Args:
            query: GraphQL query string
            
        Returns:
            True if query appears valid, False otherwise
        """
        if not query or not isinstance(query, str):
            return False
        
        query = query.strip()
        if not query:
            return False
        
        # Basic GraphQL query validation
        # Check for required keywords
        required_keywords = ['query', 'mutation', 'subscription']
        has_keyword = any(keyword in query.lower() for keyword in required_keywords)
        
        if not has_keyword:
            return False
        
        # Check for balanced braces
        open_braces = query.count('{')
        close_braces = query.count('}')
        
        return open_braces == close_braces and open_braces > 0