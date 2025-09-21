"""
Main CLI application entry point with Typer integration.
"""
import sys
import signal
import logging
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console

from ..storage import HybridStorage
from ..config.settings import get_config, ReqSmithConfig
from ..error_handler import (
    get_error_handler, set_debug_mode, handle_error, graceful_shutdown,
    validate_system_requirements, error_boundary
)
from ..logging_config import setup_logging, configure_debug_mode, get_log_file_path
from ..exceptions import ReqSmithError, SystemError
from ..core import (
    HTTPClient, TemplateManager, EnvironmentManager, HistoryManager, 
    CacheManager, VariableSubstitutionEngine
)
from ..formatters import ResponseFormatter
from .request import request_app
from .template import template_app
from .environment import env_app
from .history import history_app


# Create main Typer app
app = typer.Typer(
    name="reqsmith",
    help="ReqSmith - A powerful API testing CLI tool with Postman-like functionality",
    add_completion=False,
    rich_markup_mode="rich"
)

# Global console for rich output
console = Console()

# Global application state
class AppState:
    def __init__(self):
        self.storage: Optional[HybridStorage] = None
        self.config: Optional[ReqSmithConfig] = None
        self.http_client: Optional[HTTPClient] = None
        self.template_manager: Optional[TemplateManager] = None
        self.env_manager: Optional[EnvironmentManager] = None
        self.history_manager: Optional[HistoryManager] = None
        self.cache_manager: Optional[CacheManager] = None
        self.response_formatter: Optional[ResponseFormatter] = None
        self.substitution_engine: Optional[VariableSubstitutionEngine] = None

# Global state instance
state = AppState()


def setup_app_logging(verbose: bool = False, debug: bool = False):
    """Setup application logging configuration."""
    # Set debug mode in error handler
    set_debug_mode(debug)
    
    # Get log file path
    log_file = get_log_file_path()
    
    if debug:
        # Use comprehensive debug logging
        configure_debug_mode()
    else:
        # Use standard logging
        from ..logging_config import setup_logging
        setup_logging(
            debug=debug,
            verbose=verbose,
            log_file=str(log_file) if log_file else None,
            structured=False
        )


@error_boundary("application initialization", fatal=True)
def initialize_app(config_file: Optional[str] = None, 
                  storage_path: Optional[str] = None,
                  cache_size: Optional[int] = None) -> bool:
    """
    Initialize application components with error handling.
    
    Args:
        config_file: Path to configuration file
        storage_path: Custom storage path
        cache_size: Cache size in MB
        
    Returns:
        True if initialization successful
    """
    try:
        # Validate system requirements first
        system_ok = validate_system_requirements()
        if not system_ok:
            console.print("[yellow]Running in degraded mode due to system limitations[/yellow]")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, graceful_shutdown)
        signal.signal(signal.SIGTERM, graceful_shutdown)
        # Load configuration
        if config_file:
            state.config = ReqSmithConfig.load_from_file(Path(config_file))
        else:
            state.config = get_config()
        
        # Override config with command line options
        if storage_path:
            state.config.storage.user_storage_path = storage_path
        if cache_size:
            state.config.storage.memory_cache_size_mb = cache_size
        
        # Initialize storage
        user_id = "default"  # TODO: Get from system or config
        state.storage = HybridStorage(user_id, state.config.storage.memory_cache_size_mb)
        
        # Initialize core components
        state.http_client = HTTPClient(
            timeout=state.config.network.timeout_seconds,
            retry_attempts=state.config.network.max_retries,
            default_headers=state.config.network.default_headers
        )
        
        state.template_manager = TemplateManager(state.storage)
        state.env_manager = EnvironmentManager(state.storage)
        state.history_manager = HistoryManager(state.storage, state.config.storage.history_limit)
        state.cache_manager = CacheManager(state.storage, state.config.storage.cache_ttl_seconds)
        state.response_formatter = ResponseFormatter(console)
        state.substitution_engine = VariableSubstitutionEngine()
        
        # Set cache enabled state (assuming cache is enabled by default)
        state.cache_manager.set_cache_enabled(True)
        
        return True
        
    except Exception as e:
        console.print(f"[red]Failed to initialize application: {e}[/red]")
        return False


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug output"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    storage_path: Optional[str] = typer.Option(None, "--storage", help="Custom storage path"),
    cache_size: Optional[int] = typer.Option(None, "--cache-size", help="Cache size in MB"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output")
):
    """
    ReqSmith - A powerful API testing CLI tool.
    
    ReqSmith provides Postman-like functionality for testing REST and GraphQL APIs
    directly from the terminal with features like templates, environments, history,
    and response caching.
    """
    # Setup logging
    setup_app_logging(verbose, debug)
    
    # Disable colors if requested
    if no_color:
        console._color_system = None
    
    # Initialize application
    if not initialize_app(config_file, storage_path, cache_size):
        raise typer.Exit(1)
    
    # Store state in context for subcommands
    ctx.obj = state


@app.command()
def version():
    """Show version information."""
    console.print("ReqSmith API Tester v1.0.0")
    console.print("A powerful CLI tool for API testing and development")


@app.command()
def status():
    """Show application status and configuration."""
    if not state.storage:
        console.print("[red]Application not initialized[/red]")
        return
    
    # Get statistics
    storage_stats = state.storage.get_cache_stats()
    cache_stats = state.cache_manager.get_cache_stats()
    history_stats = state.history_manager.get_history_statistics()
    
    # Display status
    console.print("\n[bold]ReqSmith Status[/bold]")
    console.print("=" * 50)
    
    console.print(f"Storage Path: {state.storage.get_user_storage_path()}")
    console.print(f"Cache Enabled: {'Yes' if state.cache_manager.is_cache_enabled() else 'No'}")
    console.print(f"Current Environment: {state.env_manager.get_current_environment() or 'None'}")
    
    console.print(f"\n[bold]Storage Statistics[/bold]")
    console.print(f"Memory Cache: {storage_stats.get('memory_cache', {}).get('size_mb', 0):.1f} MB")
    console.print(f"Disk Available: {'Yes' if state.storage.is_disk_available() else 'No'}")
    
    console.print(f"\n[bold]Cache Statistics[/bold]")
    console.print(f"Total Entries: {cache_stats.get('total_entries', 0)}")
    console.print(f"Cache Size: {cache_stats.get('total_size_mb', 0):.1f} MB")
    
    console.print(f"\n[bold]History Statistics[/bold]")
    console.print(f"Total Requests: {history_stats.get('total_requests', 0)}")
    
    # Template and environment counts
    templates = state.template_manager.list_templates()
    environments = state.env_manager.list_environments()
    
    console.print(f"\n[bold]Content Statistics[/bold]")
    console.print(f"Templates: {len(templates)}")
    console.print(f"Environments: {len(environments)}")


# Import the new config CLI
from .config import config_app

# Add the config subcommand
app.add_typer(config_app, name="config", help="Configuration management")


@app.command()
def cleanup(
    cache: bool = typer.Option(False, "--cache", help="Clean up expired cache entries"),
    history: bool = typer.Option(False, "--history", help="Clean up old history entries"),
    all_data: bool = typer.Option(False, "--all", help="Clean up all data"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts")
):
    """Clean up application data."""
    if not any([cache, history, all_data]):
        console.print("Specify what to clean up: --cache, --history, or --all")
        return
    
    if all_data and not confirm:
        if not typer.confirm("This will delete ALL data including templates and environments. Continue?"):
            console.print("Cleanup cancelled")
            return
    
    cleaned_items = []
    
    if cache or all_data:
        if all_data:
            state.cache_manager.clear_cache()
            cleaned_items.append("All cache data")
        else:
            removed = state.cache_manager.cleanup_expired()
            cleaned_items.append(f"{removed} expired cache entries")
    
    if history or all_data:
        if all_data:
            state.history_manager.clear_history()
            cleaned_items.append("All history data")
        else:
            # TODO: Implement history cleanup by age
            cleaned_items.append("Old history entries")
    
    if all_data:
        # Clear templates and environments
        templates = state.template_manager.list_templates()
        for template in templates:
            state.template_manager.delete_template(template)
        
        environments = state.env_manager.list_environments()
        for env in environments:
            try:
                state.env_manager.delete_environment(env)
            except ValueError:
                pass  # Skip current environment
        
        cleaned_items.extend(["All templates", "All environments"])
    
    console.print(f"[green]Cleaned up: {', '.join(cleaned_items)}[/green]")


@app.command()
def help(
    topic: Optional[str] = typer.Argument(None, help="Help topic (getting-started, examples, tutorials, tips, workflows)"),
    command: Optional[str] = typer.Option(None, "--command", help="Show help for specific command"),
    category: Optional[str] = typer.Option(None, "--category", help="Example category"),
    workflow: Optional[str] = typer.Option(None, "--workflow", help="Workflow guide")
):
    """Show comprehensive help and documentation."""
    from .help import (
        show_getting_started, show_examples, show_tutorials, 
        show_tips, show_command_help, show_workflow_guide, show_help_menu
    )
    
    if command:
        show_command_help(command)
    elif workflow:
        show_workflow_guide(workflow)
    elif topic == "getting-started":
        show_getting_started()
    elif topic == "examples":
        show_examples(category)
    elif topic == "tutorials":
        show_tutorials(category)
    elif topic == "tips":
        show_tips()
    elif topic == "workflows":
        console.print("[yellow]Specify a workflow with --workflow option[/yellow]")
        console.print("Available workflows: api-testing, environment-management, template-organization")
    elif topic:
        console.print(f"[red]Unknown help topic: {topic}[/red]")
        show_help_menu()
    else:
        show_help_menu()


@app.command()
def completion(
    install: bool = typer.Option(False, "--install", help="Install shell completion"),
    shell: str = typer.Option("auto", "--shell", help="Shell type (bash, zsh, fish, auto)"),
    show_setup: bool = typer.Option(False, "--show-setup", help="Show setup instructions")
):
    """Manage shell completion."""
    from .completion import setup_shell_completion, install_shell_completion
    
    if install:
        success = install_shell_completion(shell)
        if not success:
            raise typer.Exit(1)
    elif show_setup:
        setup_shell_completion()
    else:
        console.print("Use --install to install completion or --show-setup for manual setup instructions")


# Add subcommand apps
app.add_typer(request_app, name="request", help="Make HTTP requests")
app.add_typer(template_app, name="template", help="Manage request templates")
app.add_typer(env_app, name="env", help="Manage environment variables")
app.add_typer(history_app, name="history", help="Manage request history")


def cli_main():
    """Main entry point for the CLI application with comprehensive error handling."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        
        # Show error summary if any errors occurred
        error_handler = get_error_handler()
        summary = error_handler.get_error_summary()
        if summary["total_errors"] > 0:
            console.print(f"[dim]Session completed with {summary['total_errors']} errors[/dim]")
        
        sys.exit(1)
    except ReqSmithError as e:
        # Handle our custom errors
        handle_error(e, "CLI execution", fatal=True)
    except Exception as e:
        # Handle unexpected errors
        error = SystemError(
            f"Unexpected error occurred: {e}",
            suggestions=[
                "Try running the command again",
                "Check if all required dependencies are installed",
                "Run with --debug for more detailed error information",
                "Report this issue if it persists"
            ],
            cause=e
        )
        handle_error(error, "CLI execution", fatal=True)


if __name__ == "__main__":
    cli_main()