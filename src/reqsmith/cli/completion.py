"""
Command autocompletion support for the CLI.
"""
import os
from pathlib import Path
from typing import List, Optional
import typer
from rich.console import Console

from ..storage import HybridStorage
from ..core import TemplateManager, EnvironmentManager


console = Console()


def complete_template_names(ctx: typer.Context, param: typer.CallbackParam, incomplete: str) -> List[str]:
    """
    Autocomplete template names.
    
    Args:
        ctx: Typer context
        param: Parameter being completed
        incomplete: Partial input from user
        
    Returns:
        List of matching template names
    """
    try:
        # Get application state from context
        state = getattr(ctx, 'obj', None)
        if not state or not state.template_manager:
            return []
        
        # Get all template names
        template_names = state.template_manager.list_templates()
        
        # Filter by incomplete input
        if incomplete:
            matching_names = [name for name in template_names 
                            if name.lower().startswith(incomplete.lower())]
        else:
            matching_names = template_names
        
        return matching_names[:20]  # Limit to 20 suggestions
        
    except Exception:
        return []


def complete_environment_names(ctx: typer.Context, param: typer.CallbackParam, incomplete: str) -> List[str]:
    """
    Autocomplete environment names.
    
    Args:
        ctx: Typer context
        param: Parameter being completed
        incomplete: Partial input from user
        
    Returns:
        List of matching environment names
    """
    try:
        # Get application state from context
        state = getattr(ctx, 'obj', None)
        if not state or not state.env_manager:
            return []
        
        # Get all environment names
        env_names = state.env_manager.list_environments()
        
        # Filter by incomplete input
        if incomplete:
            matching_names = [name for name in env_names 
                            if name.lower().startswith(incomplete.lower())]
        else:
            matching_names = env_names
        
        return matching_names[:20]  # Limit to 20 suggestions
        
    except Exception:
        return []


def complete_variable_names(ctx: typer.Context, param: typer.CallbackParam, incomplete: str) -> List[str]:
    """
    Autocomplete variable names from current environment.
    
    Args:
        ctx: Typer context
        param: Parameter being completed
        incomplete: Partial input from user
        
    Returns:
        List of matching variable names
    """
    try:
        # Get application state from context
        state = getattr(ctx, 'obj', None)
        if not state or not state.env_manager:
            return []
        
        # Get current environment
        current_env = state.env_manager.get_current_environment()
        if not current_env:
            return []
        
        # Get variable names
        variables = state.env_manager.list_variables(current_env)
        var_names = list(variables.keys())
        
        # Filter by incomplete input
        if incomplete:
            matching_names = [name for name in var_names 
                            if name.lower().startswith(incomplete.lower())]
        else:
            matching_names = var_names
        
        return matching_names[:20]  # Limit to 20 suggestions
        
    except Exception:
        return []


def complete_http_methods(ctx: typer.Context, param: typer.CallbackParam, incomplete: str) -> List[str]:
    """
    Autocomplete HTTP methods.
    
    Args:
        ctx: Typer context
        param: Parameter being completed
        incomplete: Partial input from user
        
    Returns:
        List of matching HTTP methods
    """
    methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD']
    
    if incomplete:
        matching_methods = [method for method in methods 
                          if method.lower().startswith(incomplete.lower())]
    else:
        matching_methods = methods
    
    return matching_methods


def complete_response_formats(ctx: typer.Context, param: typer.CallbackParam, incomplete: str) -> List[str]:
    """
    Autocomplete response format options.
    
    Args:
        ctx: Typer context
        param: Parameter being completed
        incomplete: Partial input from user
        
    Returns:
        List of matching format options
    """
    formats = ['auto', 'json', 'xml', 'html', 'raw', 'table']
    
    if incomplete:
        matching_formats = [fmt for fmt in formats 
                          if fmt.lower().startswith(incomplete.lower())]
    else:
        matching_formats = formats
    
    return matching_formats


def complete_file_paths(ctx: typer.Context, param: typer.CallbackParam, incomplete: str) -> List[str]:
    """
    Autocomplete file paths.
    
    Args:
        ctx: Typer context
        param: Parameter being completed
        incomplete: Partial input from user
        
    Returns:
        List of matching file paths
    """
    try:
        if not incomplete:
            # Show files in current directory
            path = Path('.')
        else:
            # Parse the incomplete path
            path = Path(incomplete)
            if path.is_dir():
                # If it's a directory, show contents
                search_dir = path
                prefix = str(path)
            else:
                # If it's a partial filename, show matching files in parent directory
                search_dir = path.parent
                prefix = str(path.parent) if str(path.parent) != '.' else ''
        
        matches = []
        
        if search_dir.exists() and search_dir.is_dir():
            for item in search_dir.iterdir():
                item_path = str(item)
                
                # Filter by incomplete input
                if incomplete and not item_path.startswith(incomplete):
                    continue
                
                # Add trailing slash for directories
                if item.is_dir():
                    item_path += '/'
                
                matches.append(item_path)
        
        return sorted(matches)[:20]  # Limit to 20 suggestions
        
    except Exception:
        return []


def complete_export_formats(ctx: typer.Context, param: typer.CallbackParam, incomplete: str) -> List[str]:
    """
    Autocomplete export format options.
    
    Args:
        ctx: Typer context
        param: Parameter being completed
        incomplete: Partial input from user
        
    Returns:
        List of matching export formats
    """
    formats = ['json', 'yaml', 'csv']
    
    if incomplete:
        matching_formats = [fmt for fmt in formats 
                          if fmt.lower().startswith(incomplete.lower())]
    else:
        matching_formats = formats
    
    return matching_formats


def complete_import_formats(ctx: typer.Context, param: typer.CallbackParam, incomplete: str) -> List[str]:
    """
    Autocomplete import format options.
    
    Args:
        ctx: Typer context
        param: Parameter being completed
        incomplete: Partial input from user
        
    Returns:
        List of matching import formats
    """
    formats = ['json', 'yaml', 'postman', 'insomnia']
    
    if incomplete:
        matching_formats = [fmt for fmt in formats 
                          if fmt.lower().startswith(incomplete.lower())]
    else:
        matching_formats = formats
    
    return matching_formats


def complete_sort_options(ctx: typer.Context, param: typer.CallbackParam, incomplete: str) -> List[str]:
    """
    Autocomplete sort options for templates.
    
    Args:
        ctx: Typer context
        param: Parameter being completed
        incomplete: Partial input from user
        
    Returns:
        List of matching sort options
    """
    options = ['name', 'created_at', 'last_used', 'usage_count']
    
    if incomplete:
        matching_options = [opt for opt in options 
                          if opt.lower().startswith(incomplete.lower())]
    else:
        matching_options = options
    
    return matching_options


def complete_search_fields(ctx: typer.Context, param: typer.CallbackParam, incomplete: str) -> List[str]:
    """
    Autocomplete search field options.
    
    Args:
        ctx: Typer context
        param: Parameter being completed
        incomplete: Partial input from user
        
    Returns:
        List of matching search fields
    """
    fields = ['name', 'description', 'url', 'tags', 'method', 'template_name', 'environment']
    
    if incomplete:
        matching_fields = [field for field in fields 
                         if field.lower().startswith(incomplete.lower())]
    else:
        matching_fields = fields
    
    return matching_fields


def complete_status_codes(ctx: typer.Context, param: typer.CallbackParam, incomplete: str) -> List[str]:
    """
    Autocomplete common HTTP status codes.
    
    Args:
        ctx: Typer context
        param: Parameter being completed
        incomplete: Partial input from user
        
    Returns:
        List of matching status codes
    """
    common_codes = [
        '200', '201', '202', '204',  # Success
        '301', '302', '304',         # Redirection
        '400', '401', '403', '404', '405', '409', '422',  # Client Error
        '500', '502', '503', '504'   # Server Error
    ]
    
    if incomplete:
        matching_codes = [code for code in common_codes 
                        if code.startswith(incomplete)]
    else:
        matching_codes = common_codes
    
    return matching_codes


def complete_template_tags(ctx: typer.Context, param: typer.CallbackParam, incomplete: str) -> List[str]:
    """
    Autocomplete template tags.
    
    Args:
        ctx: Typer context
        param: Parameter being completed
        incomplete: Partial input from user
        
    Returns:
        List of matching template tags
    """
    try:
        # Get application state from context
        state = getattr(ctx, 'obj', None)
        if not state or not state.template_manager:
            return []
        
        # Get all tags
        all_tags = state.template_manager.get_all_tags()
        
        # Filter by incomplete input
        if incomplete:
            matching_tags = [tag for tag in all_tags 
                           if tag.lower().startswith(incomplete.lower())]
        else:
            matching_tags = all_tags
        
        return matching_tags[:20]  # Limit to 20 suggestions
        
    except Exception:
        return []


def setup_shell_completion():
    """
    Setup shell completion for the CLI.
    
    This function provides instructions for setting up shell completion
    for bash, zsh, and fish shells.
    """
    console.print("\n[bold]Shell Completion Setup[/bold]")
    console.print("=" * 50)
    
    console.print("\n[bold blue]Bash:[/bold blue]")
    console.print("Add this to your ~/.bashrc:")
    console.print("[dim]eval \"$(_REQSMITH_COMPLETE=bash_source reqsmith)\"[/dim]")
    
    console.print("\n[bold blue]Zsh:[/bold blue]")
    console.print("Add this to your ~/.zshrc:")
    console.print("[dim]eval \"$(_REQSMITH_COMPLETE=zsh_source reqsmith)\"[/dim]")
    
    console.print("\n[bold blue]Fish:[/bold blue]")
    console.print("Add this to your ~/.config/fish/completions/reqsmith.fish:")
    console.print("[dim]eval (env _REQSMITH_COMPLETE=fish_source reqsmith)[/dim]")
    
    console.print("\n[bold yellow]Note:[/bold yellow] Restart your shell or source the config file after adding the completion.")


def install_shell_completion(shell: str = "auto"):
    """
    Install shell completion for the specified shell.
    
    Args:
        shell: Shell type (bash, zsh, fish, auto)
    """
    if shell == "auto":
        # Try to detect shell
        shell_env = os.environ.get('SHELL', '')
        if 'bash' in shell_env:
            shell = 'bash'
        elif 'zsh' in shell_env:
            shell = 'zsh'
        elif 'fish' in shell_env:
            shell = 'fish'
        else:
            console.print("[yellow]Could not detect shell. Please specify --shell option.[/yellow]")
            return False
    
    try:
        if shell == 'bash':
            bashrc = Path.home() / '.bashrc'
            completion_line = 'eval "$(_REQSMITH_COMPLETE=bash_source reqsmith)"'
            
        elif shell == 'zsh':
            zshrc = Path.home() / '.zshrc'
            completion_line = 'eval "$(_REQSMITH_COMPLETE=zsh_source reqsmith)"'
            
        elif shell == 'fish':
            fish_dir = Path.home() / '.config' / 'fish' / 'completions'
            fish_dir.mkdir(parents=True, exist_ok=True)
            fish_file = fish_dir / 'reqsmith.fish'
            completion_line = 'eval (env _REQSMITH_COMPLETE=fish_source reqsmith)'
            
        else:
            console.print(f"[red]Unsupported shell: {shell}[/red]")
            return False
        
        console.print(f"[green]Shell completion for {shell} would be installed.[/green]")
        console.print(f"[dim]Command: {completion_line}[/dim]")
        
        # Note: Actual installation would require writing to shell config files
        # This is a placeholder for the completion installation logic
        
        return True
        
    except Exception as e:
        console.print(f"[red]Failed to install completion: {e}[/red]")
        return False


# Completion mappings for easy reference
COMPLETION_FUNCTIONS = {
    'template_names': complete_template_names,
    'environment_names': complete_environment_names,
    'variable_names': complete_variable_names,
    'http_methods': complete_http_methods,
    'response_formats': complete_response_formats,
    'file_paths': complete_file_paths,
    'export_formats': complete_export_formats,
    'import_formats': complete_import_formats,
    'sort_options': complete_sort_options,
    'search_fields': complete_search_fields,
    'status_codes': complete_status_codes,
    'template_tags': complete_template_tags
}