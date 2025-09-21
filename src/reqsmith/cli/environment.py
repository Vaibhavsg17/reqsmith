"""
Environment management commands for the CLI.
"""
import json
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table

from ..core import EnvironmentImportExport


# Create environment subcommand app
env_app = typer.Typer(help="Manage environment variables")
console = Console()


@env_app.command("create")
def create_environment(
    name: str = typer.Argument(..., help="Environment name"),
    description: Optional[str] = typer.Option(None, "--description", help="Environment description"),
    ctx: typer.Context = typer.Context
):
    """Create a new environment."""
    state = ctx.obj
    
    try:
        success = state.env_manager.create_environment(name, description or "")
        
        if success:
            console.print(f"[green]Environment '{name}' created successfully[/green]")
        else:
            console.print(f"[red]Failed to create environment '{name}'[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error creating environment: {e}[/red]")
        raise typer.Exit(1)


@env_app.command("list")
def list_environments(
    details: bool = typer.Option(False, "--details", help="Show detailed information"),
    ctx: typer.Context = typer.Context
):
    """List all environments."""
    state = ctx.obj
    
    try:
        environments = state.env_manager.get_all_environments_info()
        
        if not environments:
            console.print("[yellow]No environments found[/yellow]")
            return
        
        current_env = state.env_manager.get_current_environment()
        
        if details:
            # Show detailed table
            table = Table(title="Environments")
            table.add_column("Name", style="cyan")
            table.add_column("Variables", style="yellow")
            table.add_column("Current", style="green")
            table.add_column("Created", style="blue")
            table.add_column("Description", style="white")
            
            for env_info in environments:
                is_current = "✓" if env_info['name'] == current_env else ""
                table.add_row(
                    env_info['name'],
                    str(env_info['variable_count']),
                    is_current,
                    env_info['formatted_created'],
                    env_info.get('description', '')[:50]
                )
            
            console.print(table)
        else:
            # Simple list
            console.print(f"\n[bold]Environments ({len(environments)})[/bold]")
            for env_info in environments:
                current_marker = " [green](current)[/green]" if env_info['name'] == current_env else ""
                console.print(f"  [cyan]{env_info['name']}[/cyan] ({env_info['variable_count']} variables){current_marker}")
        
    except Exception as e:
        console.print(f"[red]Error listing environments: {e}[/red]")
        raise typer.Exit(1)


@env_app.command("switch")
def switch_environment(
    name: str = typer.Argument(..., help="Environment name"),
    ctx: typer.Context = typer.Context
):
    """Switch to a different environment."""
    state = ctx.obj
    
    try:
        success = state.env_manager.switch_environment(name)
        
        if success:
            console.print(f"[green]Switched to environment '{name}'[/green]")
        else:
            console.print(f"[red]Failed to switch to environment '{name}'[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error switching environment: {e}[/red]")
        raise typer.Exit(1)


@env_app.command("current")
def current_environment(
    ctx: typer.Context = typer.Context
):
    """Show current environment."""
    state = ctx.obj
    
    try:
        current = state.env_manager.get_current_environment()
        
        if current:
            console.print(f"Current environment: [cyan]{current}[/cyan]")
            
            # Show variables
            variables = state.env_manager.list_variables(current)
            if variables:
                console.print(f"\nVariables ({len(variables)}):")
                for key, value in variables.items():
                    # Hide sensitive values
                    if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key', 'token']):
                        display_value = "***"
                    else:
                        display_value = value[:50] + "..." if len(value) > 50 else value
                    console.print(f"  {key} = {display_value}")
            else:
                console.print("\nNo variables defined")
        else:
            console.print("[yellow]No current environment set[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error getting current environment: {e}[/red]")
        raise typer.Exit(1)


@env_app.command("set")
def set_variable(
    key: str = typer.Argument(..., help="Variable name"),
    value: str = typer.Argument(..., help="Variable value"),
    environment: Optional[str] = typer.Option(None, "-e", "--env", help="Environment name (uses current if not specified)"),
    ctx: typer.Context = typer.Context
):
    """Set an environment variable."""
    state = ctx.obj
    
    try:
        env_name = environment or state.env_manager.get_current_environment()
        
        if not env_name:
            console.print("[red]No environment specified and no current environment set[/red]")
            raise typer.Exit(1)
        
        success = state.env_manager.set_variable(env_name, key, value)
        
        if success:
            console.print(f"[green]Set {key} in environment '{env_name}'[/green]")
        else:
            console.print(f"[red]Failed to set variable {key}[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error setting variable: {e}[/red]")
        raise typer.Exit(1)


@env_app.command("get")
def get_variable(
    key: str = typer.Argument(..., help="Variable name"),
    environment: Optional[str] = typer.Option(None, "-e", "--env", help="Environment name (uses current if not specified)"),
    ctx: typer.Context = typer.Context
):
    """Get an environment variable."""
    state = ctx.obj
    
    try:
        env_name = environment or state.env_manager.get_current_environment()
        
        if not env_name:
            console.print("[red]No environment specified and no current environment set[/red]")
            raise typer.Exit(1)
        
        value = state.env_manager.get_variable(env_name, key)
        
        if value is not None:
            console.print(f"{key} = {value}")
        else:
            console.print(f"[yellow]Variable '{key}' not found in environment '{env_name}'[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error getting variable: {e}[/red]")
        raise typer.Exit(1)


@env_app.command("unset")
def unset_variable(
    key: str = typer.Argument(..., help="Variable name"),
    environment: Optional[str] = typer.Option(None, "-e", "--env", help="Environment name (uses current if not specified)"),
    ctx: typer.Context = typer.Context
):
    """Remove an environment variable."""
    state = ctx.obj
    
    try:
        env_name = environment or state.env_manager.get_current_environment()
        
        if not env_name:
            console.print("[red]No environment specified and no current environment set[/red]")
            raise typer.Exit(1)
        
        success = state.env_manager.delete_variable(env_name, key)
        
        if success:
            console.print(f"[green]Removed {key} from environment '{env_name}'[/green]")
        else:
            console.print(f"[yellow]Variable '{key}' not found in environment '{env_name}'[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error removing variable: {e}[/red]")
        raise typer.Exit(1)


@env_app.command("vars")
def list_variables(
    environment: Optional[str] = typer.Option(None, "-e", "--env", help="Environment name (uses current if not specified)"),
    show_values: bool = typer.Option(False, "--show-values", help="Show variable values"),
    ctx: typer.Context = typer.Context
):
    """List variables in an environment."""
    state = ctx.obj
    
    try:
        env_name = environment or state.env_manager.get_current_environment()
        
        if not env_name:
            console.print("[red]No environment specified and no current environment set[/red]")
            raise typer.Exit(1)
        
        variables = state.env_manager.list_variables(env_name)
        
        if not variables:
            console.print(f"[yellow]No variables found in environment '{env_name}'[/yellow]")
            return
        
        console.print(f"\n[bold]Variables in '{env_name}' ({len(variables)})[/bold]")
        
        if show_values:
            for key, value in variables.items():
                # Hide sensitive values
                if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key', 'token']):
                    display_value = "***"
                else:
                    display_value = value
                console.print(f"  {key} = {display_value}")
        else:
            for key in variables.keys():
                console.print(f"  {key}")
        
    except Exception as e:
        console.print(f"[red]Error listing variables: {e}[/red]")
        raise typer.Exit(1)


@env_app.command("delete")
def delete_environment(
    name: str = typer.Argument(..., help="Environment name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    ctx: typer.Context = typer.Context
):
    """Delete an environment."""
    state = ctx.obj
    
    try:
        if not state.env_manager.environment_exists(name):
            console.print(f"[red]Environment '{name}' not found[/red]")
            raise typer.Exit(1)
        
        if not force:
            if not typer.confirm(f"Delete environment '{name}' and all its variables?"):
                console.print("Deletion cancelled")
                return
        
        success = state.env_manager.delete_environment(name)
        
        if success:
            console.print(f"[green]Environment '{name}' deleted successfully[/green]")
        else:
            console.print(f"[red]Failed to delete environment '{name}'[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error deleting environment: {e}[/red]")
        raise typer.Exit(1)


@env_app.command("copy")
def copy_environment(
    source: str = typer.Argument(..., help="Source environment name"),
    target: str = typer.Argument(..., help="Target environment name"),
    description: Optional[str] = typer.Option(None, "--description", help="Description for new environment"),
    ctx: typer.Context = typer.Context
):
    """Copy an environment."""
    state = ctx.obj
    
    try:
        success = state.env_manager.copy_environment(source, target, description or "")
        
        if success:
            console.print(f"[green]Environment '{source}' copied to '{target}'[/green]")
        else:
            console.print(f"[red]Failed to copy environment[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error copying environment: {e}[/red]")
        raise typer.Exit(1)


@env_app.command("export")
def export_environment(
    name: str = typer.Argument(..., help="Environment name"),
    file: str = typer.Argument(..., help="Export file path"),
    include_metadata: bool = typer.Option(True, "--metadata/--no-metadata", help="Include metadata"),
    ctx: typer.Context = typer.Context
):
    """Export environment to file."""
    state = ctx.obj
    
    try:
        export_util = EnvironmentImportExport(state.env_manager)
        
        success = export_util.export_environments_to_file(
            file_path=file,
            environment_names=[name],
            include_metadata=include_metadata
        )
        
        if success:
            console.print(f"[green]Environment '{name}' exported to {file}[/green]")
        else:
            console.print(f"[red]Failed to export environment[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error exporting environment: {e}[/red]")
        raise typer.Exit(1)


@env_app.command("import")
def import_environment(
    file: str = typer.Argument(..., help="Import file path"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing environments"),
    ctx: typer.Context = typer.Context
):
    """Import environment from file."""
    state = ctx.obj
    
    try:
        if not Path(file).exists():
            console.print(f"[red]Import file not found: {file}[/red]")
            raise typer.Exit(1)
        
        export_util = EnvironmentImportExport(state.env_manager)
        
        imported_count, skipped_count, errors = export_util.import_environments_from_file(
            file_path=file,
            overwrite=overwrite
        )
        
        console.print(f"[green]Import completed:[/green]")
        console.print(f"  Imported: {imported_count}")
        console.print(f"  Skipped: {skipped_count}")
        
        if errors:
            console.print(f"  Errors: {len(errors)}")
            for error in errors[:5]:  # Show first 5 errors
                console.print(f"    [red]{error}[/red]")
            if len(errors) > 5:
                console.print(f"    [dim]... and {len(errors) - 5} more errors[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error importing environment: {e}[/red]")
        raise typer.Exit(1)


@env_app.command("stats")
def environment_stats(
    ctx: typer.Context = typer.Context
):
    """Show environment statistics."""
    state = ctx.obj
    
    try:
        stats = state.env_manager.get_environment_statistics()
        
        console.print("\n[bold]Environment Statistics[/bold]")
        console.print("=" * 50)
        
        console.print(f"Total Environments: {stats['total_environments']}")
        console.print(f"Total Variables: {stats['total_variables']}")
        console.print(f"Average Variables: {stats.get('average_variables', 0):.1f}")
        console.print(f"Current Environment: {stats['current_environment'] or 'None'}")
        
        if stats.get('most_variables'):
            most_vars = stats['most_variables']
            console.print(f"Most Variables: {most_vars['name']} ({most_vars['count']} variables)")
        
        if stats.get('recently_modified'):
            recent = stats['recently_modified']
            console.print(f"Recently Modified: {recent['name']} ({recent['modified']})")
        
    except Exception as e:
        console.print(f"[red]Error getting environment statistics: {e}[/red]")
        raise typer.Exit(1)