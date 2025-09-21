"""
Core module for HTTP client and request handling.
"""

from .http_client import HTTPClient, FileHTTPClient, GraphQLClient, Response
from .request_validator import (
    RequestValidator,
    RequestPreprocessor, 
    RequestBuilder
)
from .template_manager import TemplateManager
from .template_executor import TemplateExecutor, TemplateParameterOverride
from .template_importer import TemplateImporter, TemplateExporter
from .env_manager import EnvironmentManager
from .variable_substitution import VariableSubstitutionEngine, NestedVariableResolver
from .env_utils import (
    EnvironmentVariableLister,
    EnvironmentBulkOperations,
    EnvironmentImportExport
)
from .history_manager import HistoryManager
from .history_retry import HistoryQueryEngine, HistoryRetryManager, RetryBatch
from .cache_manager import CacheManager, SmartCacheManager, CacheAnalyzer

__all__ = [
    # HTTP clients
    'HTTPClient',
    'FileHTTPClient', 
    'GraphQLClient',
    'Response',
    
    # Request validation and preprocessing
    'RequestValidator',
    'RequestPreprocessor',
    'RequestBuilder',
    
    # Template management
    'TemplateManager',
    'TemplateExecutor',
    'TemplateParameterOverride',
    'TemplateImporter',
    'TemplateExporter',
    
    # Environment management
    'EnvironmentManager',
    'VariableSubstitutionEngine',
    'NestedVariableResolver',
    'EnvironmentVariableLister',
    'EnvironmentBulkOperations',
    'EnvironmentImportExport',
    
    # History and caching
    'HistoryManager',
    'HistoryQueryEngine',
    'HistoryRetryManager',
    'RetryBatch',
    'CacheManager',
    'SmartCacheManager',
    'CacheAnalyzer'
]