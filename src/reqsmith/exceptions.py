"""
Custom exception hierarchy for ReqSmith.
"""

from typing import Optional, Dict, Any, List
from enum import Enum


class ErrorCategory(Enum):
    """Categories of errors for better error handling."""
    NETWORK = "network"
    STORAGE = "storage"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    TEMPLATE = "template"
    ENVIRONMENT = "environment"
    AI = "ai"
    SYSTEM = "system"


class ReqSmithError(Exception):
    """Base exception class for all ReqSmith errors."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        suggestions: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.suggestions = suggestions or []
        self.details = details or {}
        self.cause = cause
    
    def __str__(self) -> str:
        return self.message
    
    def get_user_message(self) -> str:
        """Get user-friendly error message with suggestions."""
        msg = f"❌ {self.message}"
        
        if self.suggestions:
            msg += "\n\n💡 Suggestions:"
            for i, suggestion in enumerate(self.suggestions, 1):
                msg += f"\n  {i}. {suggestion}"
        
        if self.details:
            # Show relevant context without overwhelming the user
            important_details = {k: v for k, v in self.details.items() 
                               if k in ['url', 'file_path', 'status_code', 'method']}
            if important_details:
                msg += "\n\n📋 Details:"
                for key, value in important_details.items():
                    if value is not None:
                        msg += f"\n  • {key.replace('_', ' ').title()}: {value}"
        
        return msg
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get detailed debug information."""
        return {
            "error_type": self.__class__.__name__,
            "category": self.category.value,
            "message": self.message,
            "suggestions": self.suggestions,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None
        }


class NetworkError(ReqSmithError):
    """Network-related errors."""
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        suggestions: Optional[List[str]] = None,
        cause: Optional[Exception] = None
    ):
        default_suggestions = [
            "Check your internet connection",
            "Verify the URL is correct and accessible",
            "Check if the server is running"
        ]
        
        if status_code:
            if status_code >= 500:
                default_suggestions.extend([
                    "The server is experiencing issues, try again later",
                    "Contact the API provider if the issue persists"
                ])
            elif status_code >= 400:
                default_suggestions.extend([
                    "Check your request parameters and authentication",
                    "Verify the endpoint exists and accepts your HTTP method"
                ])
        
        super().__init__(
            message,
            ErrorCategory.NETWORK,
            suggestions or default_suggestions,
            {"url": url, "status_code": status_code},
            cause
        )
        self.url = url
        self.status_code = status_code


class StorageError(ReqSmithError):
    """Storage-related errors."""
    
    def __init__(
        self,
        message: str,
        storage_path: Optional[str] = None,
        operation: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        cause: Optional[Exception] = None
    ):
        default_suggestions = [
            "Check if you have write permissions to the storage directory",
            "Ensure sufficient disk space is available",
            "Try running with elevated permissions if necessary"
        ]
        
        super().__init__(
            message,
            ErrorCategory.STORAGE,
            suggestions or default_suggestions,
            {"storage_path": storage_path, "operation": operation},
            cause
        )
        self.storage_path = storage_path
        self.operation = operation


class ConfigurationError(ReqSmithError):
    """Configuration-related errors."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        cause: Optional[Exception] = None
    ):
        default_suggestions = [
            "Check your configuration file syntax",
            "Use 'reqsmith config validate' to check configuration",
            "Reset to defaults with 'reqsmith config reset'"
        ]
        
        super().__init__(
            message,
            ErrorCategory.CONFIGURATION,
            suggestions or default_suggestions,
            {"config_key": config_key, "config_file": config_file},
            cause
        )
        self.config_key = config_key
        self.config_file = config_file


class ValidationError(ReqSmithError):
    """Validation-related errors."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        cause: Optional[Exception] = None
    ):
        default_suggestions = [
            "Check the format and syntax of your input",
            "Refer to the documentation for valid formats",
            "Use examples as a reference"
        ]
        
        super().__init__(
            message,
            ErrorCategory.VALIDATION,
            suggestions or default_suggestions,
            {"field": field, "value": value},
            cause
        )
        self.field = field
        self.value = value


class AuthenticationError(ReqSmithError):
    """Authentication-related errors."""
    
    def __init__(
        self,
        message: str,
        auth_type: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        cause: Optional[Exception] = None
    ):
        default_suggestions = [
            "Check your API key or authentication credentials",
            "Verify the authentication method is correct",
            "Ensure your credentials haven't expired"
        ]
        
        super().__init__(
            message,
            ErrorCategory.AUTHENTICATION,
            suggestions or default_suggestions,
            {"auth_type": auth_type},
            cause
        )
        self.auth_type = auth_type


class TemplateError(ReqSmithError):
    """Template-related errors."""
    
    def __init__(
        self,
        message: str,
        template_name: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        cause: Optional[Exception] = None
    ):
        default_suggestions = [
            "Check if the template exists with 'reqsmith template list'",
            "Verify template syntax and required variables",
            "Create the template if it doesn't exist"
        ]
        
        super().__init__(
            message,
            ErrorCategory.TEMPLATE,
            suggestions or default_suggestions,
            {"template_name": template_name},
            cause
        )
        self.template_name = template_name


class VariableSubstitutionError(TemplateError):
    """Variable substitution errors."""
    
    def __init__(
        self,
        message: str,
        variable_name: Optional[str] = None,
        variable_value: Optional[str] = None,
        function_name: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        cause: Optional[Exception] = None
    ):
        default_suggestions = [
            "Check if the variable is defined in your environment",
            "Verify variable syntax: ${var}, {{var}}, %VAR%, or $var",
            "Check function syntax if using functions: ${var|function}"
        ]
        
        super().__init__(
            message,
            template_name=None,
            suggestions=suggestions or default_suggestions,
            cause=cause
        )
        self.variable_name = variable_name
        self.variable_value = variable_value
        self.function_name = function_name


class EnvironmentError(ReqSmithError):
    """Environment-related errors."""
    
    def __init__(
        self,
        message: str,
        environment_name: Optional[str] = None,
        variable_name: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        cause: Optional[Exception] = None
    ):
        default_suggestions = [
            "Check if the environment exists with 'reqsmith env list'",
            "Create the environment if it doesn't exist",
            "Verify environment variable names and values"
        ]
        
        super().__init__(
            message,
            ErrorCategory.ENVIRONMENT,
            suggestions or default_suggestions,
            {"environment_name": environment_name, "variable_name": variable_name},
            cause
        )
        self.environment_name = environment_name
        self.variable_name = variable_name


class AIError(ReqSmithError):
    """AI-related errors."""
    
    def __init__(
        self,
        message: str,
        ai_service: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        cause: Optional[Exception] = None
    ):
        default_suggestions = [
            "Check your AI service API key configuration",
            "Verify internet connectivity for AI services",
            "AI features are optional - you can continue without them"
        ]
        
        super().__init__(
            message,
            ErrorCategory.AI,
            suggestions or default_suggestions,
            {"ai_service": ai_service},
            cause
        )
        self.ai_service = ai_service


class SystemError(ReqSmithError):
    """System-related errors."""
    
    def __init__(
        self,
        message: str,
        system_info: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        cause: Optional[Exception] = None
    ):
        default_suggestions = [
            "Check system resources (memory, disk space)",
            "Try restarting the application",
            "Report this issue if it persists"
        ]
        
        super().__init__(
            message,
            ErrorCategory.SYSTEM,
            suggestions or default_suggestions,
            system_info or {},
            cause
        )


# Specific error types for common scenarios
class ConnectionTimeoutError(NetworkError):
    """Connection timeout error."""
    
    def __init__(self, url: str, timeout: int, cause: Optional[Exception] = None):
        super().__init__(
            f"Connection to {url} timed out after {timeout} seconds",
            url=url,
            suggestions=[
                f"Increase timeout with --timeout {timeout * 2}",
                "Check if the server is responding slowly",
                "Verify your network connection"
            ],
            cause=cause
        )


class InvalidURLError(ValidationError):
    """Invalid URL error."""
    
    def __init__(self, url: str, cause: Optional[Exception] = None):
        super().__init__(
            f"Invalid URL format: {url}",
            field="url",
            value=url,
            suggestions=[
                "Ensure URL includes protocol (http:// or https://)",
                "Check for typos in the URL",
                "Example: https://api.example.com/endpoint"
            ],
            cause=cause
        )


class TemplateNotFoundError(TemplateError):
    """Template not found error."""
    
    def __init__(self, template_name: str, cause: Optional[Exception] = None):
        super().__init__(
            f"Template '{template_name}' not found",
            template_name=template_name,
            suggestions=[
                f"Create template with: reqsmith template save {template_name}",
                "List available templates with: reqsmith template list",
                "Check template name spelling"
            ],
            cause=cause
        )


class EnvironmentNotFoundError(EnvironmentError):
    """Environment not found error."""
    
    def __init__(self, environment_name: str, cause: Optional[Exception] = None):
        super().__init__(
            f"Environment '{environment_name}' not found",
            environment_name=environment_name,
            suggestions=[
                f"Create environment with: reqsmith env create {environment_name}",
                "List available environments with: reqsmith env list",
                "Check environment name spelling"
            ],
            cause=cause
        )


class StorageUnavailableError(StorageError):
    """Storage unavailable error with fallback suggestions."""
    
    def __init__(self, storage_path: str, cause: Optional[Exception] = None):
        super().__init__(
            f"Storage unavailable at {storage_path}",
            storage_path=storage_path,
            suggestions=[
                "Running in memory-only mode (data won't persist)",
                "Check directory permissions and disk space",
                "Specify alternative storage path with --storage"
            ],
            cause=cause
        )


class APIKeyMissingError(AuthenticationError):
    """API key missing error."""
    
    def __init__(self, service: str, cause: Optional[Exception] = None):
        super().__init__(
            f"{service} API key not configured",
            auth_type="api_key",
            suggestions=[
                f"Set API key with: reqsmith config set ai.{service.lower()}_api_key YOUR_KEY",
                f"Get API key from {service} developer console",
                "AI features will be disabled without API key"
            ],
            cause=cause
        )


def handle_exception(exc: Exception) -> ReqSmithError:
    """Convert standard exceptions to ReqSmith exceptions."""
    
    # Network-related exceptions
    if "timeout" in str(exc).lower():
        return ConnectionTimeoutError("unknown", 30, exc)
    
    if "connection" in str(exc).lower():
        return NetworkError(
            "Network connection failed",
            suggestions=[
                "Check your internet connection",
                "Verify the server is accessible",
                "Try again in a few moments"
            ],
            cause=exc
        )
    
    # File/Storage related exceptions
    if isinstance(exc, (FileNotFoundError, PermissionError, OSError)):
        return StorageError(
            f"Storage operation failed: {exc}",
            suggestions=[
                "Check file/directory permissions",
                "Ensure sufficient disk space",
                "Verify the path exists and is accessible"
            ],
            cause=exc
        )
    
    # JSON/Parsing errors
    if "json" in str(exc).lower() or isinstance(exc, ValueError):
        return ValidationError(
            f"Data validation failed: {exc}",
            suggestions=[
                "Check data format and syntax",
                "Ensure JSON is properly formatted",
                "Verify all required fields are present"
            ],
            cause=exc
        )
    
    # Generic system error
    return SystemError(
        f"Unexpected error: {exc}",
        suggestions=[
            "Try the operation again",
            "Check system resources",
            "Report this issue if it persists"
        ],
        cause=exc
    )