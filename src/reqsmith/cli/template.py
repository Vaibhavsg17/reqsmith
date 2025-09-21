"""
Template management commands for the CLI.
"""
import json
import time
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..core import TemplateImporter, TemplateExporter


# Create template subcommand app
template_app = typer.Typer(help="Manage request templates")
console = Console()


@template_app.command("save")
def save_template(
    name: str = typer.Argument(..., help="Template name"),
    method: str = typer.Option("GET", "-m", "--method", help="HTTP method"),
    url: str = typer.Option(..., "-u", "--url", help="Request URL"),
    headers: Optional[List[str]] = typer.Option(None, "-H", "--header", help="Request headers (key:value)"),
    body: Optional[str] = typer.Option(None, "-d", "--data", help="Request body"),
    body_file: Optional[str] = typer.Option(None, "--body-file", help="Read body from file"),
    params: Optional[List[str]] = typer.Option(None, "-p", "--param", help="Query parameters (key=value)"),
    description: Optional[str] = typer.Option(None, "--description", help="Template description"),
    tags: Optional[List[str]] = typer.Option(None, "--tag", help="Template tags"),
    ctx: typer.Context = typer.Context
):
    """Save a new request template."""
    state = ctx.obj
    
    try:
        # Parse headers and params
        parsed_headers = _parse_headers(headers) if headers else {}
        parsed_params = _parse_params(params) if params else {}
        
        # Get body from file if specified
        if body_file:
            with open(body_file, 'r', encoding='utf-8') as f:
                body = f.read()
        
        # Save template
        success = state.template_manager.save_template(
            name=name,
            method=method.upper(),
            url=url,
            headers=parsed_headers,
            body=body or "",
            params=parsed_params,
            description=description or "",
            tags=tags or []
        )
        
        if success:
            console.print(f"[green]Template '{name}' saved successfully[/green]")
        else:
            console.print(f"[red]Failed to save template '{name}'[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error saving template: {e}[/red]")
        raise typer.Exit(1)


@template_app.command("list")
def list_templates(
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
    sort_by: str = typer.Option("name", "--sort", help="Sort by (name, created_at, last_used, usage_count)"),
    details: bool = typer.Option(False, "--details", help="Show detailed information"),
    ctx: typer.Context = typer.Context
):
    """List all templates."""
    state = ctx.obj
    
    try:
        template_names = state.template_manager.list_templates(tag_filter=tag, sort_by=sort_by)
        
        if not template_names:
            console.print("[yellow]No templates found[/yellow]")
            return
        
        if details:
            # Show detailed table
            table = Table(title="Request Templates")
            table.add_column("Name", style="cyan")
            table.add_column("Method", style="blue")
            table.add_column("URL", style="green")
            table.add_column("Usage", style="yellow")
            table.add_column("Tags", style="magenta")
            table.add_column("Description", style="white")
            
            for name in template_names:
                metadata = state.template_manager.get_template_metadata(name)
                if metadata:
                    table.add_row(
                        name,
                        metadata['method'],
                        metadata['url'][:50] + "..." if len(metadata['url']) > 50 else metadata['url'],
                        str(metadata['usage_count']),
                        ", ".join(metadata['tags'][:3]),
                        metadata['description'][:30] + "..." if len(metadata['description']) > 30 else metadata['description']
                    )
            
            console.print(table)
        else:
            # Simple list
            console.print(f"\n[bold]Templates ({len(template_names)})[/bold]")
            for name in template_names:
                template = state.template_manager.load_template(name)
                if template:
                    console.print(f"  [cyan]{name}[/cyan] - {template.method} {template.url}")
        
    except Exception as e:
        console.print(f"[red]Error listing templates: {e}[/red]")
        raise typer.Exit(1)


@template_app.command("show")
def show_template(
    name: str = typer.Argument(..., help="Template name"),
    ctx: typer.Context = typer.Context
):
    """Show template details."""
    state = ctx.obj
    
    try:
        template = state.template_manager.load_template(name)
        if not template:
            console.print(f"[red]Template '{name}' not found[/red]")
            raise typer.Exit(1)
        
        # Display template details
        console.print(f"\n[bold]Template: {name}[/bold]")
        console.print(f"Method: [blue]{template.method}[/blue]")
        console.print(f"URL: [green]{template.url}[/green]")
        
        if template.description:
            console.print(f"Description: {template.description}")
        
        if template.tags:
            console.print(f"Tags: [magenta]{', '.join(template.tags)}[/magenta]")
        
        console.print(f"Usage Count: [yellow]{template.usage_count}[/yellow]")
        console.print(f"Created: {template.get_formatted_timestamp()}")
        
        if template.headers:
            console.print("\n[bold]Headers:[/bold]")
            for key, value in template.headers.items():
                console.print(f"  {key}: {value}")
        
        if template.params:
            console.print("\n[bold]Parameters:[/bold]")
            for key, value in template.params.items():
                console.print(f"  {key}={value}")
        
        if template.body:
            console.print("\n[bold]Body:[/bold]")
            # Try to format as JSON if possible
            try:
                parsed_json = json.loads(template.body)
                formatted_json = json.dumps(parsed_json, indent=2)
                console.print(Panel(formatted_json, title="JSON Body"))
            except json.JSONDecodeError:
                console.print(Panel(template.body, title="Request Body"))
        
    except Exception as e:
        console.print(f"[red]Error showing template: {e}[/red]")
        raise typer.Exit(1)


@template_app.command("use")
def use_template(
    name: str = typer.Argument(..., help="Template name"),
    override_url: Optional[str] = typer.Option(None, "--url", help="Override URL"),
    override_method: Optional[str] = typer.Option(None, "--method", help="Override method"),
    headers: Optional[List[str]] = typer.Option(None, "-H", "--header", help="Additional headers (key:value)"),
    params: Optional[List[str]] = typer.Option(None, "-p", "--param", help="Additional parameters (key=value)"),
    variables: Optional[List[str]] = typer.Option(None, "--var", help="Template variables (key=value)"),
    body: Optional[str] = typer.Option(None, "-d", "--data", help="Override body"),
    environment: Optional[str] = typer.Option(None, "-e", "--env", help="Use environment"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Save response to file"),
    format_type: str = typer.Option("auto", "-f", "--format", help="Response format"),
    cache: bool = typer.Option(True, "--cache/--no-cache", help="Use response caching"),
    preview: bool = typer.Option(False, "--preview", help="Preview request without executing"),
    ctx: typer.Context = typer.Context
):
    """Execute a template with optional overrides."""
    state = ctx.obj
    
    try:
        from ..core import TemplateExecutor
        
        # Check if template exists
        if not state.template_manager.template_exists(name):
            console.print(f"[red]Template '{name}' not found[/red]")
            raise typer.Exit(1)
        
        # Prepare overrides
        overrides = {}
        if override_url:
            overrides['url'] = override_url
        if override_method:
            overrides['method'] = override_method.upper()
        if headers:
            overrides['headers'] = _parse_headers(headers)
        if params:
            overrides['params'] = _parse_params(params)
        if body:
            overrides['body'] = body
        
        # Get environment
        env_obj = None
        if environment:
            # Check if environment exists first
            if not state.env_manager.environment_exists(environment):
                console.print(f"[red]Environment '{environment}' not found[/red]")
                raise typer.Exit(1)
            env_obj = state.env_manager.get_environment_obj(environment)
        elif state.env_manager.get_current_environment():
            env_obj = state.env_manager.get_current_environment_obj()
        
        # Handle variables passed via --var flag
        if variables:
            from ..storage import Environment
            
            # Parse variables
            parsed_variables = {}
            for var in variables:
                if '=' not in var:
                    console.print(f"[red]Invalid variable format: {var}. Use key=value[/red]")
                    raise typer.Exit(1)
                key, value = var.split('=', 1)
                parsed_variables[key.strip()] = value
            
            # Create temporary environment or merge with existing
            if env_obj:
                # Merge variables with existing environment
                merged_vars = env_obj.variables.copy()
                merged_vars.update(parsed_variables)
                env_obj = Environment(
                    name=env_obj.name,
                    variables=merged_vars,
                    description=env_obj.description,
                    created_at=env_obj.created_at,
                    last_modified=env_obj.last_modified
                )
            else:
                # Create temporary environment with variables
                env_obj = Environment(
                    name="_temp_vars",
                    variables=parsed_variables,
                    description="Temporary environment for template variables",
                    created_at=time.time(),
                    last_modified=time.time()
                )
        
        # Execute template
        executor = TemplateExecutor(state.template_manager)
        
        if preview:
            # Preview mode
            request_data = executor.preview_template_execution(name, env_obj, overrides)
            
            console.print(f"\n[bold]Template Preview: {name}[/bold]")
            console.print(f"Method: [blue]{request_data['method']}[/blue]")
            console.print(f"URL: [green]{request_data['url']}[/green]")
            
            if request_data['headers']:
                console.print("\n[bold]Headers:[/bold]")
                for key, value in request_data['headers'].items():
                    console.print(f"  {key}: {value}")
            
            if request_data['params']:
                console.print("\n[bold]Parameters:[/bold]")
                for key, value in request_data['params'].items():
                    console.print(f"  {key}={value}")
            
            if request_data['body']:
                console.print(f"\n[bold]Body:[/bold]\n{request_data['body']}")
            
            return
        
        # Execute template
        request_data = executor.execute_template(name, env_obj, overrides)
        
        # Make the request
        response = state.http_client.send_request(
            method=request_data['method'],
            url=request_data['url'],
            headers=request_data['headers'],
            body=request_data['body'] if request_data['body'] else None,
            params=request_data['params']
        )
        
        # Cache response if enabled
        if cache and state.cache_manager.is_cache_enabled():
            state.cache_manager.cache_response(response)
        
        # Add to history
        state.history_manager.add_request(response, name, environment, cached=False)
        
        # Display response
        if output:
            from ..formatters import ResponseSaver
            saver = ResponseSaver()
            saver.save_response(response, output)
            console.print(f"[green]Response saved to {output}[/green]")
        
        state.response_formatter.format_response(response, format_type)
        
    except Exception as e:
        console.print(f"[red]Error using template: {e}[/red]")
        raise typer.Exit(1)


@template_app.command("delete")
def delete_template(
    name: str = typer.Argument(..., help="Template name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    ctx: typer.Context = typer.Context
):
    """Delete a template."""
    state = ctx.obj
    
    try:
        if not state.template_manager.template_exists(name):
            console.print(f"[red]Template '{name}' not found[/red]")
            raise typer.Exit(1)
        
        if not force:
            if not typer.confirm(f"Delete template '{name}'?"):
                console.print("Deletion cancelled")
                return
        
        success = state.template_manager.delete_template(name)
        
        if success:
            console.print(f"[green]Template '{name}' deleted successfully[/green]")
        else:
            console.print(f"[red]Failed to delete template '{name}'[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error deleting template: {e}[/red]")
        raise typer.Exit(1)


@template_app.command("export")
def export_templates(
    file: str = typer.Argument(..., help="Export file path"),
    templates: Optional[List[str]] = typer.Option(None, "--template", help="Specific templates to export"),
    format_type: str = typer.Option("json", "--format", help="Export format (json, yaml)"),
    include_metadata: bool = typer.Option(True, "--metadata/--no-metadata", help="Include metadata"),
    ctx: typer.Context = typer.Context
):
    """Export templates to file."""
    state = ctx.obj
    
    try:
        exporter = TemplateExporter(state.template_manager)
        
        success = exporter.export_to_file(
            file_path=file,
            template_names=templates,
            format_type=format_type,
            include_metadata=include_metadata
        )
        
        if success:
            template_count = len(templates) if templates else len(state.template_manager.list_templates())
            console.print(f"[green]Exported {template_count} templates to {file}[/green]")
        else:
            console.print(f"[red]Failed to export templates[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error exporting templates: {e}[/red]")
        raise typer.Exit(1)


@template_app.command("import")
def import_templates(
    file: str = typer.Argument(..., help="Import file path"),
    format_type: Optional[str] = typer.Option(None, "--format", help="Import format (json, yaml, postman, insomnia)"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing templates"),
    ctx: typer.Context = typer.Context
):
    """Import templates from file."""
    state = ctx.obj
    
    try:
        if not Path(file).exists():
            console.print(f"[red]Import file not found: {file}[/red]")
            raise typer.Exit(1)
        
        importer = TemplateImporter(state.template_manager)
        
        imported_count, skipped_count, errors = importer.import_from_file(
            file_path=file,
            format_type=format_type,
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
        console.print(f"[red]Error importing templates: {e}[/red]")
        raise typer.Exit(1)


@template_app.command("search")
def search_templates(
    query: str = typer.Argument(..., help="Search query"),
    fields: Optional[List[str]] = typer.Option(None, "--field", help="Fields to search (name, description, url, tags)"),
    ctx: typer.Context = typer.Context
):
    """Search templates."""
    state = ctx.obj
    
    try:
        matching_templates = state.template_manager.search_templates(query, fields)
        
        if not matching_templates:
            console.print(f"[yellow]No templates found matching '{query}'[/yellow]")
            return
        
        console.print(f"\n[bold]Found {len(matching_templates)} templates matching '{query}':[/bold]")
        
        for name in matching_templates:
            template = state.template_manager.load_template(name)
            if template:
                console.print(f"  [cyan]{name}[/cyan] - {template.method} {template.url}")
                if template.description:
                    console.print(f"    {template.description}")
        
    except Exception as e:
        console.print(f"[red]Error searching templates: {e}[/red]")
        raise typer.Exit(1)


@template_app.command("stats")
def template_stats(
    ctx: typer.Context = typer.Context
):
    """Show template statistics."""
    state = ctx.obj
    
    try:
        stats = state.template_manager.get_template_statistics()
        
        console.print("\n[bold]Template Statistics[/bold]")
        console.print("=" * 50)
        
        console.print(f"Total Templates: {stats['total_templates']}")
        console.print(f"Total Usage: {stats['total_usage']}")
        console.print(f"Average Usage: {stats.get('average_usage', 0):.1f}")
        
        if stats['most_used']:
            console.print(f"Most Used: {stats['most_used']} ({stats['most_used_count']} times)")
        
        if stats['recently_created']:
            console.print(f"Recently Created: {stats['recently_created']}")
        
        if stats['methods_distribution']:
            console.print("\n[bold]Methods Distribution:[/bold]")
            for method, count in stats['methods_distribution'].items():
                console.print(f"  {method}: {count}")
        
        if stats['tags_distribution']:
            console.print("\n[bold]Top Tags:[/bold]")
            sorted_tags = sorted(stats['tags_distribution'].items(), key=lambda x: x[1], reverse=True)
            for tag, count in sorted_tags[:10]:
                console.print(f"  {tag}: {count}")
        
    except Exception as e:
        console.print(f"[red]Error getting template statistics: {e}[/red]")
        raise typer.Exit(1)


def _parse_headers(headers: List[str]) -> dict:
    """Parse header strings into dictionary."""
    parsed = {}
    for header in headers:
        if ':' in header:
            key, value = header.split(':', 1)
            parsed[key.strip()] = value.strip()
    return parsed


def _parse_params(params: List[str]) -> dict:
    """Parse parameter strings into dictionary."""
    parsed = {}
    for param in params:
        if '=' in param:
            key, value = param.split('=', 1)
            parsed[key.strip()] = value.strip()
    return parsed