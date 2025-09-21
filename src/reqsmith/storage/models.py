"""
Data models for the API tester with serialization support.
"""
import json
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


class SerializationMixin:
    """Mixin class providing JSON serialization capabilities."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert dataclass to JSON string."""
        return json.dumps(self.to_dict(), default=str, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create instance from dictionary."""
        # Filter out any extra fields that aren't in the dataclass
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    @classmethod
    def from_json(cls, json_str: str):
        """Create instance from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def validate(self) -> bool:
        """Validate the data model. Override in subclasses."""
        return True


@dataclass
class RequestTemplate(SerializationMixin):
    """Template for storing reusable API requests."""
    
    name: str
    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    params: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    usage_count: int = 0
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    def validate(self) -> bool:
        """Validate template data."""
        if not self.name or not self.name.strip():
            return False
        
        if not self.method or self.method.upper() not in [
            'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'
        ]:
            return False
        
        if not self.url or not self.url.strip():
            return False
        
        # Validate headers are strings
        if not isinstance(self.headers, dict):
            return False
        
        for key, value in self.headers.items():
            if not isinstance(key, str) or not isinstance(value, str):
                return False
        
        return True
    
    def update_usage(self):
        """Update usage statistics."""
        self.last_used = time.time()
        self.usage_count += 1
    
    def get_display_name(self) -> str:
        """Get display name with method and URL."""
        return f"{self.method.upper()} {self.name}"


@dataclass
class RequestRecord(SerializationMixin):
    """Record of an executed API request."""
    
    timestamp: float
    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    params: Dict[str, str] = field(default_factory=dict)
    response_status: int = 0
    response_time: float = 0.0
    response_size: int = 0
    cached: bool = False
    template_name: Optional[str] = None
    environment: Optional[str] = None
    error_message: Optional[str] = None
    
    def validate(self) -> bool:
        """Validate request record."""
        if not self.method or not self.url:
            return False
        
        if self.response_status < 0 or self.response_status > 999:
            return False
        
        if self.response_time < 0:
            return False
        
        return True
    
    def get_formatted_timestamp(self) -> str:
        """Get human-readable timestamp."""
        dt = datetime.fromtimestamp(self.timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    
    def get_status_category(self) -> str:
        """Get status code category."""
        if 200 <= self.response_status < 300:
            return "success"
        elif 300 <= self.response_status < 400:
            return "redirect"
        elif 400 <= self.response_status < 500:
            return "client_error"
        elif 500 <= self.response_status < 600:
            return "server_error"
        else:
            return "unknown"
    
    def is_successful(self) -> bool:
        """Check if request was successful."""
        return 200 <= self.response_status < 400


@dataclass
class Environment(SerializationMixin):
    """Environment configuration with variables."""
    
    name: str
    variables: Dict[str, str] = field(default_factory=dict)
    is_active: bool = False
    created_at: float = field(default_factory=time.time)
    last_modified: float = field(default_factory=time.time)
    description: str = ""
    
    def validate(self) -> bool:
        """Validate environment data."""
        if not self.name or not self.name.strip():
            return False
        
        # Validate variables are string key-value pairs
        if not isinstance(self.variables, dict):
            return False
        
        for key, value in self.variables.items():
            if not isinstance(key, str) or not isinstance(value, str):
                return False
        
        return True
    
    def set_variable(self, key: str, value: str):
        """Set environment variable."""
        self.variables[key] = value
        self.last_modified = time.time()
    
    def get_variable(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable."""
        return self.variables.get(key, default)
    
    def delete_variable(self, key: str) -> bool:
        """Delete environment variable."""
        if key in self.variables:
            del self.variables[key]
            self.last_modified = time.time()
            return True
        return False
    
    def substitute_variables(self, text: str) -> str:
        """Substitute variables in text using ${VAR} syntax."""
        import re
        
        def replace_var(match):
            var_name = match.group(1)
            return self.variables.get(var_name, match.group(0))
        
        # Replace ${VAR} patterns
        return re.sub(r'\$\{([^}]+)\}', replace_var, text)


@dataclass
class CacheEntry(SerializationMixin):
    """Cache entry with metadata."""
    
    key: str
    data: Any
    created_at: float = field(default_factory=time.time)
    ttl: int = 0  # Time to live in seconds, 0 = no expiration
    size_bytes: int = 0
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    
    def validate(self) -> bool:
        """Validate cache entry."""
        if not self.key:
            return False
        
        if self.ttl < 0:
            return False
        
        return True
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl == 0:
            return False
        
        return time.time() > (self.created_at + self.ttl)
    
    def update_access(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()
    
    def get_age_seconds(self) -> float:
        """Get age of cache entry in seconds."""
        return time.time() - self.created_at


class ConfigurationKeys(Enum):
    """Configuration key constants."""
    
    # Storage settings
    CACHE_SIZE_MB = "cache_size_mb"
    STORAGE_PATH = "storage_path"
    HISTORY_LIMIT = "history_limit"
    
    # Request settings
    DEFAULT_TIMEOUT = "default_timeout"
    DEFAULT_HEADERS = "default_headers"
    RETRY_ATTEMPTS = "retry_attempts"
    
    # Display settings
    OUTPUT_FORMAT = "output_format"
    COLOR_ENABLED = "color_enabled"
    TABLE_MAX_ROWS = "table_max_rows"
    
    # Cache settings
    CACHE_TTL_DEFAULT = "cache_ttl_default"
    CACHE_ENABLED = "cache_enabled"
    
    # AI settings
    GEMINI_API_KEY = "gemini_api_key"
    AI_ENABLED = "ai_enabled"
    AI_SUGGESTIONS_ENABLED = "ai_suggestions_enabled"


@dataclass
class Configuration(SerializationMixin):
    """Application configuration."""
    
    # Storage settings
    cache_size_mb: int = 50
    storage_path: str = "~/.apitester"
    history_limit: int = 1000
    
    # Request settings
    default_timeout: int = 30
    default_headers: Dict[str, str] = field(default_factory=dict)
    retry_attempts: int = 3
    
    # Display settings
    output_format: str = "json"  # json, table, raw
    color_enabled: bool = True
    table_max_rows: int = 100
    
    # Cache settings
    cache_ttl_default: int = 3600  # 1 hour
    cache_enabled: bool = True
    
    # AI settings
    gemini_api_key: Optional[str] = None
    ai_enabled: bool = False
    ai_suggestions_enabled: bool = True
    
    def validate(self) -> bool:
        """Validate configuration."""
        if self.cache_size_mb <= 0:
            return False
        
        if self.history_limit <= 0:
            return False
        
        if self.default_timeout <= 0:
            return False
        
        if self.output_format not in ["json", "table", "raw"]:
            return False
        
        return True
    
    def get_effective_storage_path(self) -> str:
        """Get storage path with user expansion."""
        from pathlib import Path
        return str(Path(self.storage_path).expanduser())
    
    def is_ai_available(self) -> bool:
        """Check if AI features are available."""
        return self.ai_enabled and self.gemini_api_key is not None


# Validation functions for data integrity
def validate_json_serializable(obj: Any) -> bool:
    """Check if object is JSON serializable."""
    try:
        json.dumps(obj, default=str)
        return True
    except (TypeError, ValueError):
        return False


def validate_url(url: str) -> bool:
    """Basic URL validation."""
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None


def validate_http_method(method: str) -> bool:
    """Validate HTTP method."""
    valid_methods = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'}
    return method.upper() in valid_methods