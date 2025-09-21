"""
History management commands for the CLI.
"""
from datetime import datetime, timedelta
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table

from ..core import HistoryQueryEngine, HistoryRetryManager


# Create history subcommand app
history_app = typer.Typer(help="Manage request history")
console = Console()


@history_app.command("list")
def list_history(
    limit: Optional[int] = typer.Option(10, "-n", "--limit", help="Number of requests to show"),
    method: Optional[str] = typer.Option(None, "--method", help="Filter by HTTP method"),
    status: Optional[int] = typer.Option(None, "--status", help="Filter by status code"),
    url_pattern: Optional[str] = typer.Option(None, "--url", help="Filter by URL pattern"),
    template: Optional[str] = typer.Option(None, "--template", help="Filter by template"),
    environment: Optional[str] = typer.Option(None, "--env", help="Filter by environment"),
    days: Optional[int] = typer.Option(None, "--days", help="Show requests from last N days"),
    details: bool = typer.Option(False, "--details", help="Show detailed information"),
    ctx: typer.Context = typer.Context
):
    """List request history."""
    state = ctx.obj
    
    try:
        # Calculate date filter if specified
        date_from = None
        if days:
            date_from = datetime.now() - timedelta(days=days)
        
        # Get history
        history = state.history_manager.get_history(
            limit=limit,
            method_filter=method,
            status_filter=status,
            url_pattern=url_pattern,
            template_filter=template,
            environment_filter=environment,
            date_from=date_from
        )
        
        if not history:
            console.print("[yellow]No history found[/yellow]")
            return
        
        if details:
            # Show detailed table
            table = Table(title=f"Request History ({len(history)} entries)")
            table.add_column("#", style="dim", width=3)
            table.add_column("Time", style="blue")
            table.add_column("Method", style="cyan")
            table.add_column("URL", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Time", style="magenta")
            table.add_column("Size", style="white")
            table.add_column("Template", style="dim")
            
            for i, record in enumerate(reversed(history)):
                # Color status based on code
                if record.is_successful():
                    status_style = "green"
                else:
                    status_style = "red"
                
                table.add_row(
                    str(i),
                    record.get_formatted_timestamp().split()[1],  # Time only
                    record.method,
                    record.url[:40] + "..." if len(record.url) > 40 else record.url,
                    f"[{status_style}]{record.response_status}[/{status_style}]",
                    f"{record.response_time:.3f}s",
                    f"{record.response_size}B",
                    record.template_name or ""
                )
            
            console.print(table)
        else:
            # Simple list
            console.print(f"\n[bold]Request History ({len(history)} entries)[/bold]")
            
            for i, record in enumerate(reversed(history)):
                # Color status based on code
                if record.is_successful():
                    status_color = "green"
                else:
                    status_color = "red"
                
                cached_indicator = " [dim](cached)[/dim]" if record.cached else ""
                template_info = f" [dim]({record.template_name})[/dim]" if record.template_name else ""
                
                console.print(
                    f"  [{status_color}]{i:2d}.[/{status_color}] "
                    f"{record.method} {record.url} -> "
                    f"[{status_color}]{record.response_status}[/{status_color}] "
                    f"({record.response_time:.3f}s){cached_indicator}{template_info}"
                )
        
    except Exception as e:
        console.print(f"[red]Error listing history: {e}[/red]")
        raise typer.Exit(1)


@history_app.command("show")
def show_request(
    index: int = typer.Argument(..., help="Request index (0 = most recent)"),
    ctx: typer.Context = typer.Context
):
    """Show detailed information about a specific request."""
    state = ctx.obj
    
    try:
        record = state.history_manager.get_request_by_index(index)
        
        if not record:
            console.print(f"[red]No request found at index {index}[/red]")
            raise typer.Exit(1)
        
        # Display request details
        console.print(f"\n[bold]Request #{index}[/bold]")
        console.print("=" * 50)
        
        console.print(f"Time: {record.get_formatted_timestamp()}")
        console.print(f"Method: [blue]{record.method}[/blue]")
        console.print(f"URL: [green]{record.url}[/green]")
        
        # Status with color
        if record.is_successful():
            status_color = "green"
        else:
            status_color = "red"
        console.print(f"Status: [{status_color}]{record.response_status}[/{status_color}]")
        
        console.print(f"Response Time: [magenta]{record.response_time:.3f}s[/magenta]")
        console.print(f"Response Size: {record.response_size} bytes")
        
        if record.template_name:
            console.print(f"Template: [cyan]{record.template_name}[/cyan]")
        
        if record.environment:
            console.print(f"Environment: [yellow]{record.environment}[/yellow]")
        
        if record.cached:
            console.print("[dim]Response was cached[/dim]")
        
        # Request headers
        if record.headers:
            console.print("\n[bold]Request Headers:[/bold]")
            for key, value in record.headers.items():
                console.print(f"  {key}: {value}")
        
        # Request body
        if record.body:
            console.print(f"\n[bold]Request Body:[/bold]")
            console.print(record.body)
        
        # Query parameters
        if record.params:
            console.print(f"\n[bold]Query Parameters:[/bold]")
            for key, value in record.params.items():
                console.print(f"  {key}={value}")
        
    except Exception as e:
        console.print(f"[red]Error showing request: {e}[/red]")
        raise typer.Exit(1)


@history_app.command("retry")
def retry_request(
    index: Optional[int] = typer.Option(None, "--index", help="Request index to retry (0 = most recent)"),
    last: bool = typer.Option(False, "--last", help="Retry last request"),
    failed: bool = typer.Option(False, "--failed", help="Retry all failed requests"),
    method: Optional[str] = typer.Option(None, "--method", help="Retry requests with specific method"),
    status: Optional[int] = typer.Option(None, "--status", help="Retry requests with specific status"),
    limit: Optional[int] = typer.Option(None, "--limit", help="Limit number of requests to retry"),
    ctx: typer.Context = typer.Context
):
    """Retry requests from history."""
    state = ctx.obj
    
    try:
        retry_manager = HistoryRetryManager(state.history_manager, state.http_client)
        
        if last or (index is None and not failed and not method and not status):
            # Retry last request
            response = retry_manager.retry_last_request()
            
            if response:
                console.print(f"[green]Retried last request: {response.status_code}[/green]")
                state.response_formatter.format_response(response, "auto")
            else:
                console.print("[red]Failed to retry last request[/red]")
                raise typer.Exit(1)
        
        elif index is not None:
            # Retry specific request by index
            response = retry_manager.retry_request_by_index(index)
            
            if response:
                console.print(f"[green]Retried request #{index}: {response.status_code}[/green]")
                state.response_formatter.format_response(response, "auto")
            else:
                console.print(f"[red]Failed to retry request #{index}[/red]")
                raise typer.Exit(1)
        
        elif failed:
            # Retry all failed requests
            console.print("[blue]Retrying failed requests...[/blue]")
            
            results = retry_manager.retry_failed_requests(limit=limit)
            
            successful_retries = 0
            for original, retry_response in results:
                if retry_response and retry_response.is_success():
                    successful_retries += 1
                    console.print(f"[green]✓ {original.method} {original.url} -> {retry_response.status_code}[/green]")
                else:
                    console.print(f"[red]✗ {original.method} {original.url} -> Failed[/red]")
            
            console.print(f"\n[blue]Retry summary: {successful_retries}/{len(results)} successful[/blue]")
        
        else:
            # Retry by criteria
            results = retry_manager.retry_requests_by_criteria(
                method=method,
                status_code=status,
                limit=limit
            )
            
            if not results:
                console.print("[yellow]No matching requests found to retry[/yellow]")
                return
            
            successful_retries = 0
            for original, retry_response in results:
                if retry_response and retry_response.is_success():
                    successful_retries += 1
                    console.print(f"[green]✓ {original.method} {original.url} -> {retry_response.status_code}[/green]")
                else:
                    console.print(f"[red]✗ {original.method} {original.url} -> Failed[/red]")
            
            console.print(f"\n[blue]Retry summary: {successful_retries}/{len(results)} successful[/blue]")
        
    except Exception as e:
        console.print(f"[red]Error retrying request: {e}[/red]")
        raise typer.Exit(1)


@history_app.command("search")
def search_history(
    query: str = typer.Argument(..., help="Search query"),
    fields: Optional[List[str]] = typer.Option(None, "--field", help="Fields to search (url, method, template_name, environment)"),
    limit: Optional[int] = typer.Option(20, "--limit", help="Maximum results to show"),
    ctx: typer.Context = typer.Context
):
    """Search request history."""
    state = ctx.obj
    
    try:
        matching_records = state.history_manager.search_history(query, fields)
        
        if not matching_records:
            console.print(f"[yellow]No requests found matching '{query}'[/yellow]")
            return
        
        # Limit results
        if limit:
            matching_records = matching_records[-limit:]
        
        console.print(f"\n[bold]Found {len(matching_records)} requests matching '{query}':[/bold]")
        
        for i, record in enumerate(reversed(matching_records)):
            # Color status based on code
            if record.is_successful():
                status_color = "green"
            else:
                status_color = "red"
            
            template_info = f" [dim]({record.template_name})[/dim]" if record.template_name else ""
            
            console.print(
                f"  [{status_color}]{i:2d}.[/{status_color}] "
                f"{record.method} {record.url} -> "
                f"[{status_color}]{record.response_status}[/{status_color}] "
                f"({record.response_time:.3f}s){template_info}"
            )
        
    except Exception as e:
        console.print(f"[red]Error searching history: {e}[/red]")
        raise typer.Exit(1)


@history_app.command("stats")
def history_stats(
    days: Optional[int] = typer.Option(7, "--days", help="Number of days to analyze"),
    ctx: typer.Context = typer.Context
):
    """Show history statistics."""
    state = ctx.obj
    
    try:
        # Get overall statistics
        overall_stats = state.history_manager.get_history_statistics()
        
        # Get recent summary
        recent_summary = state.history_manager.get_history_summary(days)
        
        console.print(f"\n[bold]History Statistics[/bold]")
        console.print("=" * 50)
        
        console.print(f"Total Requests: {overall_stats.get('total_requests', 0)}")
        
        if overall_stats.get('date_range'):
            date_range = overall_stats['date_range']
            console.print(f"Date Range: {date_range['oldest']} - {date_range['newest']}")
        
        # Recent activity
        console.print(f"\n[bold]Last {days} Days:[/bold]")
        console.print(f"Total Requests: {recent_summary['total_requests']}")
        console.print(f"Successful: {recent_summary['successful_requests']}")
        console.print(f"Failed: {recent_summary['failed_requests']}")
        
        if recent_summary['total_requests'] > 0:
            console.print(f"Success Rate: {recent_summary['success_rate']:.1f}%")
            console.print(f"Average Response Time: {recent_summary['average_response_time']:.3f}s")
        
        # Method distribution
        if recent_summary.get('most_used_methods'):
            console.print(f"\n[bold]Methods Used:[/bold]")
            for method, count in recent_summary['most_used_methods'].items():
                console.print(f"  {method}: {count}")
        
        # Status distribution
        if recent_summary.get('status_distribution'):
            console.print(f"\n[bold]Status Codes:[/bold]")
            for status, count in sorted(recent_summary['status_distribution'].items()):
                console.print(f"  {status}: {count}")
        
        # Most requested URLs
        if recent_summary.get('most_requested_urls'):
            console.print(f"\n[bold]Most Requested URLs:[/bold]")
            for url, count in list(recent_summary['most_requested_urls'].items())[:5]:
                display_url = url[:60] + "..." if len(url) > 60 else url
                console.print(f"  {count}x {display_url}")
        
    except Exception as e:
        console.print(f"[red]Error getting history statistics: {e}[/red]")
        raise typer.Exit(1)


@history_app.command("clear")
def clear_history(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    ctx: typer.Context = typer.Context
):
    """Clear all request history."""
    state = ctx.obj
    
    try:
        if not force:
            if not typer.confirm("Clear all request history?"):
                console.print("Clear cancelled")
                return
        
        success = state.history_manager.clear_history()
        
        if success:
            console.print("[green]Request history cleared[/green]")
        else:
            console.print("[red]Failed to clear history[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error clearing history: {e}[/red]")
        raise typer.Exit(1)


@history_app.command("export")
def export_history(
    file: str = typer.Argument(..., help="Export file path"),
    format_type: str = typer.Option("json", "--format", help="Export format (json, csv)"),
    limit: Optional[int] = typer.Option(None, "--limit", help="Maximum records to export"),
    ctx: typer.Context = typer.Context
):
    """Export history to file."""
    state = ctx.obj
    
    try:
        success = state.history_manager.export_history(file, format_type, limit)
        
        if success:
            record_count = limit or len(state.history_manager.get_history())
            console.print(f"[green]Exported {record_count} history records to {file}[/green]")
        else:
            console.print(f"[red]Failed to export history[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error exporting history: {e}[/red]")
        raise typer.Exit(1)


@history_app.command("analyze")
def analyze_history(
    ctx: typer.Context = typer.Context
):
    """Analyze request patterns in history."""
    state = ctx.obj
    
    try:
        query_engine = HistoryQueryEngine(state.history_manager)
        patterns = query_engine.get_request_patterns()
        
        if 'error' in patterns:
            console.print(f"[red]{patterns['error']}[/red]")
            return
        
        console.print(f"\n[bold]Request Pattern Analysis[/bold]")
        console.print("=" * 50)
        
        console.print(f"Total Requests Analyzed: {patterns['total_requests']}")
        
        # Method distribution
        if patterns.get('method_distribution'):
            console.print(f"\n[bold]HTTP Methods:[/bold]")
            for method, count in patterns['method_distribution'].items():
                percentage = (count / patterns['total_requests']) * 100
                console.print(f"  {method}: {count} ({percentage:.1f}%)")
        
        # Domain distribution
        if patterns.get('domain_distribution'):
            console.print(f"\n[bold]Top Domains:[/bold]")
            for domain, count in patterns['domain_distribution'].items():
                console.print(f"  {domain}: {count}")
        
        # Time patterns
        if patterns.get('time_patterns'):
            time_patterns = patterns['time_patterns']
            
            if time_patterns.get('hourly'):
                console.print(f"\n[bold]Hourly Distribution:[/bold]")
                hourly = time_patterns['hourly']
                for hour in sorted(hourly.keys()):
                    console.print(f"  {hour:02d}:00: {hourly[hour]}")
            
            if time_patterns.get('daily'):
                console.print(f"\n[bold]Daily Distribution:[/bold]")
                for day, count in time_patterns['daily'].items():
                    console.print(f"  {day}: {count}")
        
        # Status distribution
        if patterns.get('status_distribution'):
            console.print(f"\n[bold]Response Status Categories:[/bold]")
            for category, count in patterns['status_distribution'].items():
                console.print(f"  {category.replace('_', ' ').title()}: {count}")
        
    except Exception as e:
        console.print(f"[red]Error analyzing history: {e}[/red]")
        raise typer.Exit(1)