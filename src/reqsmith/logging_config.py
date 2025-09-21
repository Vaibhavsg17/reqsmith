"""
Logging configuration and structured logging for ReqSmith.
"""

import os
import sys
import json
import time
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
from contextlib import contextmanager

from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text

from .config.settings import get_config


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log data
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if enabled
        if self.include_extra:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'exc_info',
                    'exc_text', 'stack_info'
                }:
                    extra_fields[key] = value
            
            if extra_fields:
                log_data["extra"] = extra_fields
        
        return json.dumps(log_data, default=str)


class PerformanceLogger:
    """Logger for performance monitoring and metrics."""
    
    def __init__(self, logger_name: str = "reqsmith.performance"):
        self.logger = logging.getLogger(logger_name)
        self.metrics = {}
    
    def log_request_performance(
        self,
        method: str,
        url: str,
        status_code: int,
        response_time: float,
        response_size: int,
        cached: bool = False
    ):
        """Log HTTP request performance metrics."""
        self.logger.info(
            "HTTP request completed",
            extra={
                "metric_type": "http_request",
                "method": method,
                "url": url,
                "status_code": status_code,
                "response_time_ms": response_time * 1000,
                "response_size_bytes": response_size,
                "cached": cached
            }
        )
        
        # Update internal metrics
        key = f"{method}_{status_code // 100}xx"
        if key not in self.metrics:
            self.metrics[key] = {"count": 0, "total_time": 0, "avg_time": 0}
        
        self.metrics[key]["count"] += 1
        self.metrics[key]["total_time"] += response_time
        self.metrics[key]["avg_time"] = self.metrics[key]["total_time"] / self.metrics[key]["count"]
    
    def log_storage_operation(
        self,
        operation: str,
        storage_type: str,
        duration: float,
        success: bool,
        size_bytes: Optional[int] = None
    ):
        """Log storage operation performance."""
        self.logger.info(
            "Storage operation completed",
            extra={
                "metric_type": "storage_operation",
                "operation": operation,
                "storage_type": storage_type,
                "duration_ms": duration * 1000,
                "success": success,
                "size_bytes": size_bytes
            }
        )
    
    def log_template_operation(
        self,
        operation: str,
        template_name: str,
        duration: float,
        success: bool
    ):
        """Log template operation performance."""
        self.logger.info(
            "Template operation completed",
            extra={
                "metric_type": "template_operation",
                "operation": operation,
                "template_name": template_name,
                "duration_ms": duration * 1000,
                "success": success
            }
        )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics."""
        return {
            "http_requests": self.metrics.copy(),
            "timestamp": datetime.now().isoformat()
        }


class DebugLogger:
    """Enhanced debug logging with request/response details."""
    
    def __init__(self, logger_name: str = "reqsmith.debug"):
        self.logger = logging.getLogger(logger_name)
        self.console = Console(file=sys.stderr)
    
    def log_request_details(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str] = None,
        params: Optional[Dict[str, str]] = None
    ):
        """Log detailed request information."""
        self.logger.debug(
            "Outgoing HTTP request",
            extra={
                "request_method": method,
                "request_url": url,
                "request_headers": headers,
                "request_body": body,
                "request_params": params
            }
        )
        
        # Also display in console if debug mode is active
        if self.logger.isEnabledFor(logging.DEBUG):
            self._display_request_debug(method, url, headers, body, params)
    
    def log_response_details(
        self,
        status_code: int,
        headers: Dict[str, str],
        body: str,
        response_time: float,
        size_bytes: int
    ):
        """Log detailed response information."""
        self.logger.debug(
            "Incoming HTTP response",
            extra={
                "response_status": status_code,
                "response_headers": headers,
                "response_body": body[:1000] if body else None,  # Truncate large responses
                "response_time_ms": response_time * 1000,
                "response_size_bytes": size_bytes
            }
        )
        
        # Also display in console if debug mode is active
        if self.logger.isEnabledFor(logging.DEBUG):
            self._display_response_debug(status_code, headers, body, response_time, size_bytes)
    
    def _display_request_debug(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[str],
        params: Optional[Dict[str, str]]
    ):
        """Display request debug info in console."""
        self.console.print(f"\n[bold blue]→ {method} {url}[/bold blue]")
        
        if params:
            self.console.print("[dim]Query Parameters:[/dim]")
            for key, value in params.items():
                self.console.print(f"  {key}: {value}")
        
        if headers:
            self.console.print("[dim]Headers:[/dim]")
            for key, value in headers.items():
                # Hide sensitive headers
                if key.lower() in ['authorization', 'x-api-key', 'cookie']:
                    value = "***hidden***"
                self.console.print(f"  {key}: {value}")
        
        if body:
            self.console.print("[dim]Body:[/dim]")
            # Pretty print JSON if possible
            try:
                import json
                parsed = json.loads(body)
                formatted = json.dumps(parsed, indent=2)
                self.console.print(f"  {formatted}")
            except:
                self.console.print(f"  {body}")
    
    def _display_response_debug(
        self,
        status_code: int,
        headers: Dict[str, str],
        body: str,
        response_time: float,
        size_bytes: int
    ):
        """Display response debug info in console."""
        status_color = "green" if 200 <= status_code < 300 else "red" if status_code >= 400 else "yellow"
        
        self.console.print(
            f"[bold {status_color}]← {status_code}[/bold {status_color}] "
            f"[dim]({response_time:.3f}s, {size_bytes} bytes)[/dim]"
        )
        
        if headers:
            self.console.print("[dim]Response Headers:[/dim]")
            for key, value in list(headers.items())[:5]:  # Show first 5 headers
                self.console.print(f"  {key}: {value}")
            if len(headers) > 5:
                self.console.print(f"  ... and {len(headers) - 5} more")
        
        if body:
            self.console.print("[dim]Response Body (first 500 chars):[/dim]")
            display_body = body[:500]
            if len(body) > 500:
                display_body += "..."
            
            # Pretty print JSON if possible
            try:
                import json
                parsed = json.loads(display_body)
                formatted = json.dumps(parsed, indent=2)
                self.console.print(f"  {formatted}")
            except:
                self.console.print(f"  {display_body}")


def setup_logging(
    debug: bool = False,
    verbose: bool = False,
    log_file: Optional[str] = None,
    structured: bool = False
) -> Dict[str, logging.Logger]:
    """
    Set up comprehensive logging configuration.
    
    Args:
        debug: Enable debug level logging
        verbose: Enable verbose (info level) logging
        log_file: Optional log file path
        structured: Use structured JSON logging
        
    Returns:
        Dictionary of configured loggers
    """
    # Determine log level
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configure root logger
    root_logger.setLevel(level)
    
    # Console handler with Rich formatting
    console_handler = RichHandler(
        console=Console(stderr=True),
        show_time=debug,
        show_path=debug,
        markup=True,
        rich_tracebacks=True
    )
    console_handler.setLevel(level)
    
    if not structured:
        console_format = "%(message)s"
        console_handler.setFormatter(logging.Formatter(console_format))
    
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use rotating file handler to prevent huge log files
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)  # Always debug level for files
            
            if structured:
                file_handler.setFormatter(StructuredFormatter())
            else:
                file_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                file_handler.setFormatter(logging.Formatter(file_format))
            
            root_logger.addHandler(file_handler)
            
        except Exception as e:
            logging.error(f"Failed to setup file logging: {e}")
    
    # Configure specific loggers
    loggers = {
        "main": logging.getLogger("reqsmith"),
        "http": logging.getLogger("reqsmith.http"),
        "storage": logging.getLogger("reqsmith.storage"),
        "template": logging.getLogger("reqsmith.template"),
        "environment": logging.getLogger("reqsmith.environment"),
        "ai": logging.getLogger("reqsmith.ai"),
        "performance": logging.getLogger("reqsmith.performance"),
        "debug": logging.getLogger("reqsmith.debug")
    }
    
    # Set levels for specific loggers
    for logger in loggers.values():
        logger.setLevel(level)
    
    # Suppress noisy third-party loggers unless in debug mode
    if not debug:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("google").setLevel(logging.WARNING)
    
    return loggers


@contextmanager
def performance_timer(operation: str, logger: Optional[PerformanceLogger] = None):
    """Context manager for timing operations."""
    start_time = time.time()
    success = True
    
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        duration = time.time() - start_time
        
        if logger:
            # Log to performance logger if provided
            logging.getLogger("reqsmith.performance").info(
                f"Operation '{operation}' completed",
                extra={
                    "operation": operation,
                    "duration_ms": duration * 1000,
                    "success": success
                }
            )
        else:
            # Log to debug logger
            logging.getLogger("reqsmith.debug").debug(
                f"Operation '{operation}' took {duration:.3f}s (success: {success})"
            )


def get_log_file_path() -> Optional[Path]:
    """Get the default log file path based on configuration."""
    try:
        config = get_config()
        log_dir = Path(config.storage.user_storage_path) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / "reqsmith.log"
    except Exception:
        return None


def configure_debug_mode():
    """Configure enhanced debug mode with detailed logging."""
    # Get or create log file path
    log_file = get_log_file_path()
    
    # Setup logging with debug enabled
    loggers = setup_logging(
        debug=True,
        verbose=True,
        log_file=str(log_file) if log_file else None,
        structured=True
    )
    
    # Log startup information
    main_logger = loggers["main"]
    main_logger.info("Debug mode enabled")
    main_logger.info(f"Log file: {log_file}")
    main_logger.info(f"Python version: {sys.version}")
    main_logger.info(f"Platform: {sys.platform}")
    
    return loggers


def log_system_info():
    """Log system information for debugging."""
    logger = logging.getLogger("reqsmith.debug")
    
    try:
        import platform
        import psutil
        
        logger.debug(
            "System information",
            extra={
                "platform": platform.platform(),
                "python_version": sys.version,
                "cpu_count": os.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "disk_usage": dict(psutil.disk_usage('/'))
            }
        )
    except ImportError:
        logger.debug("System info logging requires psutil package")
    except Exception as e:
        logger.debug(f"Failed to log system info: {e}")


# Global instances
_performance_logger: Optional[PerformanceLogger] = None
_debug_logger: Optional[DebugLogger] = None


def get_performance_logger() -> PerformanceLogger:
    """Get the global performance logger instance."""
    global _performance_logger
    if _performance_logger is None:
        _performance_logger = PerformanceLogger()
    return _performance_logger


def get_debug_logger() -> DebugLogger:
    """Get the global debug logger instance."""
    global _debug_logger
    if _debug_logger is None:
        _debug_logger = DebugLogger()
    return _debug_logger