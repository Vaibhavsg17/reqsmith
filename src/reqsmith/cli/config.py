"""
Configuration management CLI commands.
"""
import os
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from ..config.settings import get_config, save_config, reload_config, ReqSmithConfig

console = Console()
config_app = typer.Typer(help="Configuration management commands")


@config_app.command("show")
def show_config(
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json, yaml"),
    section: Optional[str] = typer.Option(None, "--section", "-s", help="Show specific section only")
):
    """Show current configuration."""
    config = get_config()
    
    if format == "json":
        import json
        if section:
            config_data = config.get_config_summary()
            if section in config_data:
                console.print(json.dumps(config_data[section], indent=2))
            else:
                console.print(f"[red]Section '{section}' not found[/red]")
                raise typer.Exit(1)
        else:
            console.print(json.dumps(config.get_config_summary(), indent=2))
        return
    
    if format == "yaml":
        try:
            import yaml
            config_data = config.get_config_summary()
            if section and section in config_data:
                console.print(yaml.dump({section: config_data[section]}, default_flow_style=False))
            else:
                console.print(yaml.dump(config_data, default_flow_style=False))
        except ImportError:
            console.print("[red]PyYAML not installed. Use 'pip install pyyaml' to enable YAML output[/red]")
            raise typer.Exit(1)
        return
    
    # Table format (default)
    config_summary = config.get_config_summary()
    
    if section:
        if section not in config_summary:
            console.print(f"[red]Section '{section}' not found[/red]")
            console.print(f"Available sections: {', '.join(config_summary.keys())}")
            raise typer.Exit(1)
        
        _show_section_table(section, config_summary[section])
    else:
        _show_full_config_table(config_summary)


def _show_full_config_table(config_summary: dict):
    """Show full configuration in table format."""
    console.print("\n[bold]ReqSmith Configuration[/bold]")
    console.print("=" * 50)
    
    for section_name, section_data in config_summary.items():
        if isinstance(section_data, dict):
            _show_section_table(section_name, section_data)
        else:
            console.print(f"[bold]{section_name}:[/bold] {section_data}")
    
    console.print()


def _show_section_table(section_name: str, section_data: dict):
    """Show a configuration section in table format."""
    table = Table(title=f"{section_name.title()} Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    for key, value in section_data.items():
        # Hide sensitive values
        if 'key' in key.lower() or 'secret' in key.lower() or 'password' in key.lower():
            if value and str(value) != "None":
                display_value = "[dim]***hidden***[/dim]"
            else:
                display_value = "[dim]not set[/dim]"
        else:
            display_value = str(value)
        
        table.add_row(key, display_value)
    
    console.print(table)
    console.print()


@config_app.command("set")
def set_config(
    key: str = typer.Argument(..., help="Configuration key (e.g., 'storage.memory_cache_size_mb')"),
    value: str = typer.Argument(..., help="Configuration value"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save configuration to file")
):
    """Set a configuration value."""
    config = get_config()
    
    if config.update_setting(key, value):
        console.print(f"[green]✓[/green] Set {key} = {value}")
        
        if save:
            if save_config():
                console.print("[green]✓[/green] Configuration saved")
            else:
                console.print("[red]✗[/red] Failed to save configuration")
                raise typer.Exit(1)
    else:
        console.print(f"[red]✗[/red] Failed to set {key} = {value}")
        console.print("Use 'reqsmith config show' to see available configuration keys")
        raise typer.Exit(1)


@config_app.command("reset")
def reset_config(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
    section: Optional[str] = typer.Option(None, "--section", "-s", help="Reset specific section only")
):
    """Reset configuration to defaults."""
    if not confirm:
        if section:
            message = f"Reset {section} configuration to defaults?"
        else:
            message = "Reset ALL configuration to defaults?"
        
        if not typer.confirm(message):
            console.print("Configuration reset cancelled")
            return
    
    if section:
        # Reset specific section
        config = get_config()
        default_config = ReqSmithConfig.get_default()
        
        if section == "storage":
            config.storage = default_config.storage
        elif section == "ai":
            config.ai = default_config.ai
        elif section == "output":
            config.output = default_config.output
        elif section == "network":
            config.network = default_config.network
        else:
            console.print(f"[red]Unknown section: {section}[/red]")
            console.print("Available sections: storage, ai, output, network")
            raise typer.Exit(1)
        
        console.print(f"[green]✓[/green] Reset {section} configuration to defaults")
    else:
        # Reset entire configuration
        config = ReqSmithConfig.get_default()
        console.print("[green]✓[/green] Reset all configuration to defaults")
    
    if save_config():
        console.print("[green]✓[/green] Configuration saved")
    else:
        console.print("[red]✗[/red] Failed to save configuration")
        raise typer.Exit(1)


@config_app.command("validate")
def validate_config():
    """Validate current configuration."""
    config = get_config()
    errors = config.validate()
    
    if not errors:
        console.print("[green]✓[/green] Configuration is valid")
    else:
        console.print("[red]✗[/red] Configuration validation failed:")
        for error in errors:
            console.print(f"  • {error}")
        raise typer.Exit(1)


@config_app.command("path")
def show_config_path():
    """Show configuration file path."""
    config = get_config()
    config_path = config.config_file_path or str(ReqSmithConfig.get_default_config_path())
    
    console.print(f"Configuration file: [cyan]{config_path}[/cyan]")
    
    if Path(config_path).exists():
        console.print("[green]✓[/green] File exists")
    else:
        console.print("[yellow]![/yellow] File does not exist (using defaults)")


@config_app.command("reload")
def reload_config_cmd(
    config_file: Optional[str] = typer.Option(None, "--file", "-f", help="Configuration file path")
):
    """Reload configuration from file."""
    try:
        config_path = Path(config_file) if config_file else None
        config = reload_config(config_path)
        
        # Validate reloaded configuration
        errors = config.validate()
        if errors:
            console.print("[yellow]![/yellow] Configuration loaded with warnings:")
            for error in errors:
                console.print(f"  • {error}")
        else:
            console.print("[green]✓[/green] Configuration reloaded successfully")
        
        if config_file:
            console.print(f"Loaded from: [cyan]{config_file}[/cyan]")
        else:
            console.print(f"Loaded from: [cyan]{config.config_file_path}[/cyan]")
            
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to reload configuration: {e}")
        raise typer.Exit(1)


@config_app.command("export")
def export_config(
    output_file: str = typer.Argument(..., help="Output file path"),
    format: str = typer.Option("json", "--format", "-f", help="Export format: json, yaml"),
    include_sensitive: bool = typer.Option(False, "--include-sensitive", help="Include sensitive values")
):
    """Export configuration to file."""
    config = get_config()
    config_data = config.to_dict()
    
    # Remove sensitive data unless explicitly requested
    if not include_sensitive:
        if "ai" in config_data and "gemini_api_key" in config_data["ai"]:
            config_data["ai"]["gemini_api_key"] = None
    
    output_path = Path(output_file)
    
    try:
        if format == "yaml":
            try:
                import yaml
                with open(output_path, 'w') as f:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
            except ImportError:
                console.print("[red]PyYAML not installed. Use 'pip install pyyaml' to enable YAML export[/red]")
                raise typer.Exit(1)
        else:
            # JSON format
            import json
            with open(output_path, 'w') as f:
                json.dump(config_data, f, indent=2)
        
        console.print(f"[green]✓[/green] Configuration exported to [cyan]{output_path}[/cyan]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to export configuration: {e}")
        raise typer.Exit(1)


@config_app.command("import")
def import_config(
    input_file: str = typer.Argument(..., help="Input file path"),
    merge: bool = typer.Option(False, "--merge", help="Merge with existing configuration"),
    backup: bool = typer.Option(True, "--backup/--no-backup", help="Create backup of current config")
):
    """Import configuration from file."""
    input_path = Path(input_file)
    
    if not input_path.exists():
        console.print(f"[red]✗[/red] File not found: {input_path}")
        raise typer.Exit(1)
    
    try:
        # Create backup if requested
        if backup:
            current_config = get_config()
            backup_path = Path(current_config.config_file_path).with_suffix('.bak')
            if current_config.save_to_file(backup_path):
                console.print(f"[green]✓[/green] Backup created: [cyan]{backup_path}[/cyan]")
        
        # Load new configuration
        if input_path.suffix.lower() in ['.yaml', '.yml']:
            try:
                import yaml
                with open(input_path, 'r') as f:
                    config_data = yaml.safe_load(f)
            except ImportError:
                console.print("[red]PyYAML not installed. Use 'pip install pyyaml' to import YAML files[/red]")
                raise typer.Exit(1)
        else:
            # Assume JSON
            import json
            with open(input_path, 'r') as f:
                config_data = json.load(f)
        
        if merge:
            # Merge with existing configuration
            current_config = get_config()
            current_data = current_config.to_dict()
            _deep_merge(current_data, config_data)
            config_data = current_data
        
        # Create and validate new configuration
        new_config = ReqSmithConfig.from_dict(config_data)
        errors = new_config.validate()
        
        if errors:
            console.print("[red]✗[/red] Imported configuration is invalid:")
            for error in errors:
                console.print(f"  • {error}")
            raise typer.Exit(1)
        
        # Save the new configuration
        if new_config.save_to_file():
            console.print(f"[green]✓[/green] Configuration imported from [cyan]{input_path}[/cyan]")
            
            # Reload to apply changes
            reload_config()
        else:
            console.print("[red]✗[/red] Failed to save imported configuration")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to import configuration: {e}")
        raise typer.Exit(1)


def _deep_merge(target: dict, source: dict):
    """Deep merge source dictionary into target dictionary."""
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value


@config_app.command("env")
def show_env_overrides():
    """Show available environment variable overrides."""
    console.print("\n[bold]Environment Variable Overrides[/bold]")
    console.print("=" * 50)
    
    table = Table()
    table.add_column("Environment Variable", style="cyan")
    table.add_column("Configuration Path", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Current Value", style="magenta")
    
    for env_var, (config_path, value_type) in ReqSmithConfig.ENV_MAPPINGS.items():
        current_value = os.getenv(env_var, "[dim]not set[/dim]")
        table.add_row(env_var, config_path, value_type.__name__, str(current_value))
    
    console.print(table)
    console.print()
    console.print("[dim]Set environment variables to override configuration values.[/dim]")
    console.print("[dim]Example: export REQSMITH_DEBUG=true[/dim]")


if __name__ == "__main__":
    config_app()