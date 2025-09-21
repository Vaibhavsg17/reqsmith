"""
Error handling and graceful degradation for ReqSmith.
"""

import sys
import traceback
import logging
from typing import Optional, Dict, Any, Callable, TypeVar, Union
from functools import wraps
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .exceptions import (
    ReqSmithError, ErrorCategory, StorageError, StorageUnavailableError,
    NetworkError, ConfigurationError, handle_exception
)

logger = logging.getLogger(__name__)
console = Console()

T = TypeVar('T')


class ErrorHandler:
    """Centralized error handling with graceful degradation."""
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.fallback_modes = {
            "storage": False,  # Whether we're in memory-only mode
            "ai": False,       # Whether AI features are disabled
            "network": False,  # Whether we're in offline mode
        }
        self.error_counts = {category.value: 0 for category in ErrorCategory}
    
    def handle_error(
        self,
        error: Union[Exception, ReqSmithError],
        context: Optional[str] = None,
        fatal: bool = False
    ) -> Optional[ReqSmithError]:
        """
        Handle an error with appropriate user feedback and graceful degradation.
        
        Args:
            error: The error to handle
            context: Additional context about where the error occurred
            fatal: Whether this error should terminate the application
            
        Returns:
            ReqSmithError instance or None if handled gracefully
        """
        # Convert standard exceptions to ReqSmith exceptions
        if not isinstance(error, ReqSmithError):
            error = handle_exception(error)
        
        # Track error statistics
        self.error_counts[error.category.value] += 1
        
        # Log the error
        if self.debug_mode:
            logger.debug(f"Error in {context}: {error.get_debug_info()}")
        else:
            logger.error(f"Error in {context}: {error.message}")
        
        # Handle specific error categories with graceful degradation
        handled = self._handle_category_specific(error, context)
        
        if handled and not fatal:
            return None
        
        # Display error to user
        self._display_error(error, context, fatal)
        
        if fatal:
            sys.exit(1)
        
        return error
    
    def _handle_category_specific(self, error: ReqSmithError, context: Optional[str]) -> bool:
        """Handle category-specific errors with graceful degradation."""
        
        if error.category == ErrorCategory.STORAGE:
            return self._handle_storage_error(error, context)
        elif error.category == ErrorCategory.AI:
            return self._handle_ai_error(error, context)
        elif error.category == ErrorCategory.NETWORK:
            return self._handle_network_error(error, context)
        elif error.category == ErrorCategory.CONFIGURATION:
            return self._handle_config_error(error, context)
        
        return False
    
    def _handle_storage_error(self, error: StorageError, context: Optional[str]) -> bool:
        """Handle storage errors with memory-only fallback."""
        if not self.fallback_modes["storage"]:
            self.fallback_modes["storage"] = True
            
            console.print(Panel(
                Text.from_markup(
                    f"[yellow]Storage Warning[/yellow]\n\n"
                    f"{error.message}\n\n"
                    f"[dim]Switching to memory-only mode. Data will not persist between sessions.[/dim]"
                ),
                title="Storage Fallback",
                border_style="yellow"
            ))
            
            logger.warning(f"Storage fallback activated: {error.message}")
            return True
        
        return False
    
    def _handle_ai_error(self, error: ReqSmithError, context: Optional[str]) -> bool:
        """Handle AI errors by disabling AI features."""
        if not self.fallback_modes["ai"]:
            self.fallback_modes["ai"] = True
            
            console.print(Panel(
                Text.from_markup(
                    f"[yellow]AI Features Disabled[/yellow]\n\n"
                    f"{error.message}\n\n"
                    f"[dim]Continuing without AI assistance. Core functionality remains available.[/dim]"
                ),
                title="AI Fallback",
                border_style="yellow"
            ))
            
            logger.warning(f"AI features disabled: {error.message}")
            return True
        
        return False
    
    def _handle_network_error(self, error: NetworkError, context: Optional[str]) -> bool:
        """Handle network errors with retry suggestions."""
        # For now, just log and continue - could implement retry logic here
        logger.warning(f"Network error in {context}: {error.message}")
        return False
    
    def _handle_config_error(self, error: ConfigurationError, context: Optional[str]) -> bool:
        """Handle configuration errors with defaults."""
        logger.warning(f"Configuration error in {context}: {error.message}")
        console.print(f"[yellow]Configuration issue: {error.message}[/yellow]")
        console.print("[dim]Using default configuration values[/dim]")
        return False
    
    def _display_error(self, error: ReqSmithError, context: Optional[str], fatal: bool):
        """Display error to user with appropriate formatting."""
        
        # Choose color based on severity
        if fatal:
            color = "red"
            title = "Fatal Error"
        elif error.category in [ErrorCategory.NETWORK, ErrorCategory.STORAGE]:
            color = "yellow"
            title = "Warning"
        else:
            color = "red"
            title = "Error"
        
        # Build error message
        message_parts = []
        
        if context:
            message_parts.append(f"[bold]Context:[/bold] {context}")
        
        message_parts.append(f"[bold]Error:[/bold] {error.message}")
        
        if error.suggestions:
            message_parts.append("\n[bold]Suggestions:[/bold]")
            for i, suggestion in enumerate(error.suggestions, 1):
                message_parts.append(f"  {i}. {suggestion}")
        
        if self.debug_mode and error.cause:
            message_parts.append(f"\n[dim]Caused by: {error.cause}[/dim]")
        
        # Display the error panel
        console.print(Panel(
            Text.from_markup("\n".join(message_parts)),
            title=title,
            border_style=color
        ))
        
        # In debug mode, also show the full traceback
        if self.debug_mode and error.cause:
            console.print("\n[dim]Full traceback:[/dim]")
            if hasattr(error.cause, '__traceback__'):
                traceback.print_exception(
                    type(error.cause),
                    error.cause,
                    error.cause.__traceback__
                )
    
    def is_fallback_active(self, mode: str) -> bool:
        """Check if a fallback mode is active."""
        return self.fallback_modes.get(mode, False)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors encountered."""
        return {
            "error_counts": self.error_counts.copy(),
            "fallback_modes": self.fallback_modes.copy(),
            "total_errors": sum(self.error_counts.values())
        }


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def set_debug_mode(debug: bool):
    """Set debug mode for error handling."""
    get_error_handler().debug_mode = debug


def handle_error(
    error: Union[Exception, ReqSmithError],
    context: Optional[str] = None,
    fatal: bool = False
) -> Optional[ReqSmithError]:
    """Handle an error using the global error handler."""
    return get_error_handler().handle_error(error, context, fatal)


def safe_execute(
    func: Callable[..., T],
    *args,
    context: Optional[str] = None,
    default: Optional[T] = None,
    **kwargs
) -> Optional[T]:
    """
    Safely execute a function with error handling.
    
    Args:
        func: Function to execute
        *args: Positional arguments for the function
        context: Context description for error reporting
        default: Default value to return on error
        **kwargs: Keyword arguments for the function
        
    Returns:
        Function result or default value on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handle_error(e, context or func.__name__)
        return default


def error_boundary(context: Optional[str] = None, fatal: bool = False):
    """
    Decorator for adding error boundaries to functions.
    
    Args:
        context: Context description for error reporting
        fatal: Whether errors should be fatal
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handle_error(e, context or func.__name__, fatal)
                return None
        return wrapper
    return decorator


def require_storage(func: Callable[..., T]) -> Callable[..., Optional[T]]:
    """
    Decorator that checks if storage is available before executing function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Optional[T]:
        error_handler = get_error_handler()
        if error_handler.is_fallback_active("storage"):
            console.print("[yellow]Storage operation skipped (memory-only mode)[/yellow]")
            return None
        
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if isinstance(e, (FileNotFoundError, PermissionError, OSError)):
                # This might trigger storage fallback
                handle_error(e, f"storage operation in {func.__name__}")
                return None
            raise
    
    return wrapper


def require_network(func: Callable[..., T]) -> Callable[..., Optional[T]]:
    """
    Decorator that handles network-related errors gracefully.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Optional[T]:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "network" in str(e).lower() or "connection" in str(e).lower():
                handle_error(e, f"network operation in {func.__name__}")
                return None
            raise
    
    return wrapper


def graceful_shutdown(signal_num: int, frame):
    """Handle graceful shutdown on signals."""
    console.print("\n[yellow]Shutting down gracefully...[/yellow]")
    
    # Get error summary
    error_handler = get_error_handler()
    summary = error_handler.get_error_summary()
    
    if summary["total_errors"] > 0:
        console.print(f"[dim]Session completed with {summary['total_errors']} errors[/dim]")
    
    sys.exit(0)


class MemoryOnlyMode:
    """Context manager for memory-only mode operations."""
    
    def __init__(self, reason: str = "Storage unavailable"):
        self.reason = reason
        self.original_mode = False
    
    def __enter__(self):
        error_handler = get_error_handler()
        self.original_mode = error_handler.fallback_modes["storage"]
        error_handler.fallback_modes["storage"] = True
        
        if not self.original_mode:
            console.print(f"[yellow]Entering memory-only mode: {self.reason}[/yellow]")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        error_handler = get_error_handler()
        error_handler.fallback_modes["storage"] = self.original_mode
        
        if not self.original_mode:
            console.print("[dim]Exiting memory-only mode[/dim]")


def validate_system_requirements() -> bool:
    """
    Validate system requirements and setup graceful degradation.
    
    Returns:
        True if all requirements are met, False if running in degraded mode
    """
    error_handler = get_error_handler()
    degraded = False
    
    # Check storage availability
    try:
        from .config.settings import get_config
        config = get_config()
        storage_path = Path(config.storage.user_storage_path)
        
        # Try to create storage directory
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # Test write permissions
        test_file = storage_path / ".test_write"
        test_file.write_text("test")
        test_file.unlink()
        
    except Exception as e:
        handle_error(
            StorageUnavailableError(str(storage_path), e),
            "system validation"
        )
        degraded = True
    
    # Check AI availability (non-critical)
    try:
        import google.generativeai
    except ImportError:
        logger.info("Google Generative AI not available - AI features disabled")
        error_handler.fallback_modes["ai"] = True
        degraded = True
    
    return not degraded