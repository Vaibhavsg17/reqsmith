"""
Request execution commands for the CLI.
"""
import json
from pathlib import Path
from typing import Optional, Dict, List
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core import HTTPClient, Response, RequestBuilder
from ..storage import RequestRecord
from ..exceptions import ReqSmithError, NetworkError, ValidationError


# Create request subcommand app
request_app = typer.Typer(help="Execute HTTP requests")
console = Console()


def _handle_request_error(error: Exception, url: str = "", context: str = "request") -> None:
    """
    Handle request errors with user-friendly messages.
    
    Args:
        error: The exception that occurred
        url: The URL being requested (for context)
        context: Additional context about the operation
    """
    error_str = str(error).lower()
    
    if "connection" in error_str or "connectionerror" in error_str:
        console.print(f"[red]❌ Connection failed[/red]")
        console.print(f"[dim]Unable to connect to {url}[/dim]")
        console.print(f"[yellow]💡 Suggestions:[/yellow]")
        console.print(f"[yellow]  • Check your internet connection[/yellow]")
        console.print(f"[yellow]  • Verify the URL is correct and accessible[/yellow]")
        console.print(f"[yellow]  • Check if the server is running[/yellow]")
    elif "timeout" in error_str:
        console.print(f"[red]❌ Request timed out[/red]")
        console.print(f"[dim]Server took too long to respond[/dim]")
        console.print(f"[yellow]💡 Suggestions:[/yellow]")
        console.print(f"[yellow]  • Try increasing timeout with --timeout[/yellow]")
        console.print(f"[yellow]  • Check server status and load[/yellow]")
        console.print(f"[yellow]  • Try again later if server is overloaded[/yellow]")
    elif "dns" in error_str or "name resolution" in error_str or "getaddrinfo failed" in error_str:
        console.print(f"[red]❌ Domain not found[/red]")
        console.print(f"[dim]Cannot resolve hostname in URL: {url}[/dim]")
        console.print(f"[yellow]💡 Suggestions:[/yellow]")
        console.print(f"[yellow]  • Verify the domain name is spelled correctly[/yellow]")
        console.print(f"[yellow]  • Check if the website exists[/yellow]")
        console.print(f"[yellow]  • Try accessing the URL in a web browser[/yellow]")
    elif "ssl" in error_str or "certificate" in error_str:
        console.print(f"[red]❌ SSL/TLS Certificate error[/red]")
        console.print(f"[dim]Problem with secure connection to {url}[/dim]")
        console.print(f"[yellow]💡 Suggestions:[/yellow]")
        console.print(f"[yellow]  • Check if the SSL certificate is valid[/yellow]")
        console.print(f"[yellow]  • Try using --insecure flag if testing[/yellow]")
        console.print(f"[yellow]  • Contact the website administrator[/yellow]")
    elif "json" in error_str and "decode" in error_str:
        console.print(f"[red]❌ Invalid JSON response[/red]")
        console.print(f"[dim]Server returned malformed JSON data[/dim]")
        console.print(f"[yellow]💡 Suggestions:[/yellow]")
        console.print(f"[yellow]  • Try --format raw to see the actual response[/yellow]")
        console.print(f"[yellow]  • Check if the endpoint returns JSON[/yellow]")
        console.print(f"[yellow]  • Verify request parameters and headers[/yellow]")
    elif "401" in error_str or "unauthorized" in error_str:
        console.print(f"[red]❌ Authentication required[/red]")
        console.print(f"[dim]Server returned 401 Unauthorized[/dim]")
        console.print(f"[yellow]💡 Suggestions:[/yellow]")
        console.print(f"[yellow]  • Add authentication headers (-H 'Authorization: Bearer TOKEN')[/yellow]")
        console.print(f"[yellow]  • Check if your API key is valid[/yellow]")
        console.print(f"[yellow]  • Verify the authentication method required[/yellow]")
    elif "403" in error_str or "forbidden" in error_str:
        console.print(f"[red]❌ Access forbidden[/red]")
        console.print(f"[dim]Server returned 403 Forbidden[/dim]")
        console.print(f"[yellow]💡 Suggestions:[/yellow]")
        console.print(f"[yellow]  • Check if you have permission to access this resource[/yellow]")
        console.print(f"[yellow]  • Verify your authentication credentials[/yellow]")
        console.print(f"[yellow]  • Contact the API provider for access[/yellow]")
    elif "404" in error_str or "not found" in error_str:
        console.print(f"[red]❌ Resource not found[/red]")
        console.print(f"[dim]Server returned 404 Not Found[/dim]")
        console.print(f"[yellow]💡 Suggestions:[/yellow]")
        console.print(f"[yellow]  • Check if the URL path is correct[/yellow]")
        console.print(f"[yellow]  • Verify the resource exists[/yellow]")
        console.print(f"[yellow]  • Check API documentation for correct endpoints[/yellow]")
    elif "500" in error_str or "internal server error" in error_str:
        console.print(f"[red]❌ Server error[/red]")
        console.print(f"[dim]Server returned 500 Internal Server Error[/dim]")
        console.print(f"[yellow]💡 Suggestions:[/yellow]")
        console.print(f"[yellow]  • Server is experiencing issues, try again later[/yellow]")
        console.print(f"[yellow]  • Contact the API provider if issue persists[/yellow]")
        console.print(f"[yellow]  • Check your request data for any issues[/yellow]")
    else:
        console.print(f"[red]❌ {context.title()} failed[/red]")
        console.print(f"[dim]Error: {error}[/dim]")
        console.print(f"[yellow]💡 Suggestions:[/yellow]")
        console.print(f"[yellow]  • Check the URL format and network connection[/yellow]")
        console.print(f"[yellow]  • Try with --debug for more detailed error information[/yellow]")
        console.print(f"[yellow]  • Review the request parameters and headers[/yellow]")


@request_app.command("get")
def get_request(
    url: str = typer.Argument(..., help="Request URL"),
    headers: Optional[List[str]] = typer.Option(None, "-H", "--header", help="Request headers (key:value)"),
    params: Optional[List[str]] = typer.Option(None, "-p", "--param", help="Query parameters (key=value)"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Save response to file"),
    format_type: str = typer.Option("auto", "-f", "--format", help="Response format (auto, json, xml, raw, table)"),
    timeout: Optional[int] = typer.Option(None, "--timeout", help="Request timeout in seconds"),
    follow_redirects: bool = typer.Option(True, "--follow-redirects/--no-follow-redirects", help="Follow redirects"),
    cache: bool = typer.Option(True, "--cache/--no-cache", help="Use response caching"),
    template: Optional[str] = typer.Option(None, "-t", "--template", help="Use template"),
    environment: Optional[str] = typer.Option(None, "-e", "--env", help="Use environment"),
    ctx: typer.Context = typer.Context
):
    """Send a GET request."""
    state = ctx.obj
    
    try:
        # Parse headers and params
        parsed_headers = _parse_headers(headers) if headers else {}
        parsed_params = _parse_params(params) if params else {}
        
        # Apply template if specified
        if template:
            request_data = _apply_template(state, template, environment, {
                'method': 'GET',
                'url': url,
                'headers': parsed_headers,
                'params': parsed_params
            })
            url = request_data['url']
            parsed_headers = request_data['headers']
            parsed_params = request_data['params']
        
        # Check cache first
        if cache and state.cache_manager.is_cache_enabled():
            cached_response = state.cache_manager.get_cached_response('GET', url, parsed_headers)
            if cached_response:
                console.print("[dim]Using cached response[/dim]")
                _display_response(state, cached_response, format_type, output)
                return
        
        # Make request
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"GET {url}", total=None)
            
            response = state.http_client.get(url, headers=parsed_headers, params=parsed_params)
        
        # Cache response if enabled
        if cache and state.cache_manager.is_cache_enabled():
            state.cache_manager.cache_response(response)
        
        # Add to history
        state.history_manager.add_request(response, template, environment, cached=False)
        
        # Display response
        _display_response(state, response, format_type, output)
        
    except Exception as e:
        _handle_request_error(e, url, "GET request")
        raise typer.Exit(1)


@request_app.command("post")
def post_request(
    url: str = typer.Argument(..., help="Request URL"),
    data: Optional[str] = typer.Option(None, "-d", "--data", help="Request body data"),
    file: Optional[str] = typer.Option(None, "--file", help="Read request body from file"),
    json_data: Optional[str] = typer.Option(None, "--json", help="JSON request body"),
    headers: Optional[List[str]] = typer.Option(None, "-H", "--header", help="Request headers (key:value)"),
    params: Optional[List[str]] = typer.Option(None, "-p", "--param", help="Query parameters (key=value)"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Save response to file"),
    format_type: str = typer.Option("auto", "-f", "--format", help="Response format (auto, json, xml, raw, table)"),
    timeout: Optional[int] = typer.Option(None, "--timeout", help="Request timeout in seconds"),
    cache: bool = typer.Option(False, "--cache/--no-cache", help="Use response caching"),
    template: Optional[str] = typer.Option(None, "-t", "--template", help="Use template"),
    environment: Optional[str] = typer.Option(None, "-e", "--env", help="Use environment"),
    ctx: typer.Context = typer.Context
):
    """Send a POST request."""
    state = ctx.obj
    
    try:
        # Parse headers and params
        parsed_headers = _parse_headers(headers) if headers else {}
        parsed_params = _parse_params(params) if params else {}
        
        # Determine request body
        body = _get_request_body(data, file, json_data, parsed_headers)
        
        # Apply template if specified
        if template:
            request_data = _apply_template(state, template, environment, {
                'method': 'POST',
                'url': url,
                'headers': parsed_headers,
                'body': body,
                'params': parsed_params
            })
            url = request_data['url']
            parsed_headers = request_data['headers']
            body = request_data['body']
            parsed_params = request_data['params']
        
        # Make request
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"POST {url}", total=None)
            
            response = state.http_client.post(url, headers=parsed_headers, body=body, params=parsed_params)
        
        # Cache response if enabled
        if cache and state.cache_manager.is_cache_enabled():
            state.cache_manager.cache_response(response)
        
        # Add to history
        state.history_manager.add_request(response, template, environment, cached=False)
        
        # Display response
        _display_response(state, response, format_type, output)
        
    except Exception as e:
        console.print(f"[red]Request failed: {e}[/red]")
        raise typer.Exit(1)


@request_app.command("put")
def put_request(
    url: str = typer.Argument(..., help="Request URL"),
    data: Optional[str] = typer.Option(None, "-d", "--data", help="Request body data"),
    file: Optional[str] = typer.Option(None, "--file", help="Read request body from file"),
    json_data: Optional[str] = typer.Option(None, "--json", help="JSON request body"),
    headers: Optional[List[str]] = typer.Option(None, "-H", "--header", help="Request headers (key:value)"),
    params: Optional[List[str]] = typer.Option(None, "-p", "--param", help="Query parameters (key=value)"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Save response to file"),
    format_type: str = typer.Option("auto", "-f", "--format", help="Response format (auto, json, xml, raw, table)"),
    cache: bool = typer.Option(False, "--cache/--no-cache", help="Use response caching"),
    template: Optional[str] = typer.Option(None, "-t", "--template", help="Use template"),
    environment: Optional[str] = typer.Option(None, "-e", "--env", help="Use environment"),
    ctx: typer.Context = typer.Context
):
    """Send a PUT request."""
    _send_request_with_body(ctx, 'PUT', url, data, file, json_data, headers, params, 
                           output, format_type, cache, template, environment)


@request_app.command("patch")
def patch_request(
    url: str = typer.Argument(..., help="Request URL"),
    data: Optional[str] = typer.Option(None, "-d", "--data", help="Request body data"),
    file: Optional[str] = typer.Option(None, "--file", help="Read request body from file"),
    json_data: Optional[str] = typer.Option(None, "--json", help="JSON request body"),
    headers: Optional[List[str]] = typer.Option(None, "-H", "--header", help="Request headers (key:value)"),
    params: Optional[List[str]] = typer.Option(None, "-p", "--param", help="Query parameters (key=value)"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Save response to file"),
    format_type: str = typer.Option("auto", "-f", "--format", help="Response format (auto, json, xml, raw, table)"),
    cache: bool = typer.Option(False, "--cache/--no-cache", help="Use response caching"),
    template: Optional[str] = typer.Option(None, "-t", "--template", help="Use template"),
    environment: Optional[str] = typer.Option(None, "-e", "--env", help="Use environment"),
    ctx: typer.Context = typer.Context
):
    """Send a PATCH request."""
    _send_request_with_body(ctx, 'PATCH', url, data, file, json_data, headers, params, 
                           output, format_type, cache, template, environment)


@request_app.command("delete")
def delete_request(
    url: str = typer.Argument(..., help="Request URL"),
    headers: Optional[List[str]] = typer.Option(None, "-H", "--header", help="Request headers (key:value)"),
    params: Optional[List[str]] = typer.Option(None, "-p", "--param", help="Query parameters (key=value)"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Save response to file"),
    format_type: str = typer.Option("auto", "-f", "--format", help="Response format (auto, json, xml, raw, table)"),
    cache: bool = typer.Option(False, "--cache/--no-cache", help="Use response caching"),
    template: Optional[str] = typer.Option(None, "-t", "--template", help="Use template"),
    environment: Optional[str] = typer.Option(None, "-e", "--env", help="Use environment"),
    ctx: typer.Context = typer.Context
):
    """Send a DELETE request."""
    state = ctx.obj
    
    try:
        # Parse headers and params
        parsed_headers = _parse_headers(headers) if headers else {}
        parsed_params = _parse_params(params) if params else {}
        
        # Apply template if specified
        if template:
            request_data = _apply_template(state, template, environment, {
                'method': 'DELETE',
                'url': url,
                'headers': parsed_headers,
                'params': parsed_params
            })
            url = request_data['url']
            parsed_headers = request_data['headers']
            parsed_params = request_data['params']
        
        # Make request
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"DELETE {url}", total=None)
            
            response = state.http_client.delete(url, headers=parsed_headers, params=parsed_params)
        
        # Add to history
        state.history_manager.add_request(response, template, environment, cached=False)
        
        # Display response
        _display_response(state, response, format_type, output)
        
    except Exception as e:
        console.print(f"[red]Request failed: {e}[/red]")
        raise typer.Exit(1)


@request_app.command("graphql")
def graphql_request(
    url: str = typer.Argument(..., help="GraphQL endpoint URL"),
    query: Optional[str] = typer.Option(None, "-q", "--query", help="GraphQL query string"),
    query_file: Optional[str] = typer.Option(None, "--query-file", help="Read GraphQL query from file"),
    variables: Optional[str] = typer.Option(None, "--variables", help="GraphQL variables (JSON)"),
    variables_file: Optional[str] = typer.Option(None, "--variables-file", help="Read variables from file"),
    operation: Optional[str] = typer.Option(None, "--operation", help="Operation name"),
    headers: Optional[List[str]] = typer.Option(None, "-H", "--header", help="Request headers (key:value)"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Save response to file"),
    format_type: str = typer.Option("json", "-f", "--format", help="Response format (json, table, raw)"),
    cache: bool = typer.Option(False, "--cache/--no-cache", help="Use response caching"),
    template: Optional[str] = typer.Option(None, "-t", "--template", help="Use template"),
    environment: Optional[str] = typer.Option(None, "-e", "--env", help="Use environment"),
    ctx: typer.Context = typer.Context
):
    """Send a GraphQL request."""
    state = ctx.obj
    
    try:
        # Get GraphQL query
        if query_file:
            with open(query_file, 'r', encoding='utf-8') as f:
                graphql_query = f.read()
        elif query:
            graphql_query = query
        else:
            console.print("[red]Either --query or --query-file must be specified[/red]")
            raise typer.Exit(1)
        
        # Get variables
        graphql_variables = None
        if variables_file:
            with open(variables_file, 'r', encoding='utf-8') as f:
                graphql_variables = json.load(f)
        elif variables:
            graphql_variables = json.loads(variables)
        
        # Parse headers
        parsed_headers = _parse_headers(headers) if headers else {}
        
        # Apply template if specified
        if template:
            request_data = _apply_template(state, template, environment, {
                'method': 'POST',
                'url': url,
                'headers': parsed_headers,
                'body': json.dumps({
                    'query': graphql_query,
                    'variables': graphql_variables,
                    'operationName': operation
                })
            })
            url = request_data['url']
            parsed_headers = request_data['headers']
        
        # Make GraphQL request
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"GraphQL {url}", total=None)
            
            response = state.http_client.send_graphql_query(
                url, graphql_query, graphql_variables, parsed_headers, operation
            )
        
        # Cache response if enabled
        if cache and state.cache_manager.is_cache_enabled():
            state.cache_manager.cache_response(response)
        
        # Add to history
        state.history_manager.add_request(response, template, environment, cached=False)
        
        # Display response
        _display_response(state, response, format_type, output)
        
    except Exception as e:
        console.print(f"[red]GraphQL request failed: {e}[/red]")
        raise typer.Exit(1)


@request_app.command("batch")
def batch_request(
    file: str = typer.Argument(..., help="Batch request file (JSON)"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", help="Directory to save responses"),
    format_type: str = typer.Option("auto", "-f", "--format", help="Response format"),
    parallel: int = typer.Option(1, "--parallel", help="Number of parallel requests"),
    delay: float = typer.Option(0.0, "--delay", help="Delay between requests in seconds"),
    environment: Optional[str] = typer.Option(None, "-e", "--env", help="Use environment"),
    ctx: typer.Context = typer.Context
):
    """Execute batch requests from a file."""
    state = ctx.obj
    
    try:
        # Load batch file
        with open(file, 'r', encoding='utf-8') as f:
            batch_data = json.load(f)
        
        requests = batch_data.get('requests', [])
        if not requests:
            console.print("[red]No requests found in batch file[/red]")
            raise typer.Exit(1)
        
        console.print(f"[blue]Executing {len(requests)} requests...[/blue]")
        
        # Execute requests
        with Progress(console=console) as progress:
            task = progress.add_task("Processing requests...", total=len(requests))
            
            for i, request_data in enumerate(requests):
                try:
                    # Extract request details
                    method = request_data.get('method', 'GET').upper()
                    url = request_data.get('url', '')
                    headers = request_data.get('headers', {})
                    body = request_data.get('body', '')
                    params = request_data.get('params', {})
                    
                    # Apply environment variables if specified
                    if environment:
                        env_obj = state.env_manager.get_current_environment_obj()
                        if env_obj:
                            url = state.substitution_engine.substitute_variables(url, env_obj)
                            body = state.substitution_engine.substitute_variables(body, env_obj)
                    
                    # Make request
                    response = state.http_client.send_request(method, url, headers, body, params)
                    
                    # Add to history
                    state.history_manager.add_request(response, None, environment, cached=False)
                    
                    # Save response if output directory specified
                    if output_dir:
                        output_file = Path(output_dir) / f"response_{i+1:03d}_{method.lower()}.txt"
                        _save_response_to_file(response, str(output_file))
                    
                    # Display brief status
                    status_color = "green" if response.is_success() else "red"
                    console.print(f"[{status_color}]{i+1:3d}. {method} {url} -> {response.status_code}[/{status_color}]")
                    
                    progress.update(task, advance=1)
                    
                    # Add delay if specified
                    if delay > 0 and i < len(requests) - 1:
                        import time
                        time.sleep(delay)
                        
                except Exception as e:
                    console.print(f"[red]{i+1:3d}. Request failed: {e}[/red]")
                    progress.update(task, advance=1)
                    continue
        
        console.print(f"[green]Batch execution completed[/green]")
        
    except Exception as e:
        console.print(f"[red]Batch execution failed: {e}[/red]")
        raise typer.Exit(1)


def _send_request_with_body(ctx, method: str, url: str, data: Optional[str], 
                           file: Optional[str], json_data: Optional[str],
                           headers: Optional[List[str]], params: Optional[List[str]],
                           output: Optional[str], format_type: str, cache: bool,
                           template: Optional[str], environment: Optional[str]):
    """Helper function for requests with body."""
    state = ctx.obj
    
    try:
        # Parse headers and params
        parsed_headers = _parse_headers(headers) if headers else {}
        parsed_params = _parse_params(params) if params else {}
        
        # Determine request body
        body = _get_request_body(data, file, json_data, parsed_headers)
        
        # Apply template if specified
        if template:
            request_data = _apply_template(state, template, environment, {
                'method': method,
                'url': url,
                'headers': parsed_headers,
                'body': body,
                'params': parsed_params
            })
            url = request_data['url']
            parsed_headers = request_data['headers']
            body = request_data['body']
            parsed_params = request_data['params']
        
        # Make request
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"{method} {url}", total=None)
            
            response = state.http_client.send_request(method, url, parsed_headers, body, parsed_params)
        
        # Cache response if enabled
        if cache and state.cache_manager.is_cache_enabled():
            state.cache_manager.cache_response(response)
        
        # Add to history
        state.history_manager.add_request(response, template, environment, cached=False)
        
        # Display response
        _display_response(state, response, format_type, output)
        
    except Exception as e:
        console.print(f"[red]Request failed: {e}[/red]")
        raise typer.Exit(1)


def _parse_headers(headers: List[str]) -> Dict[str, str]:
    """Parse header strings into dictionary."""
    parsed = {}
    for header in headers:
        if ':' in header:
            key, value = header.split(':', 1)
            parsed[key.strip()] = value.strip()
    return parsed


def _parse_params(params: List[str]) -> Dict[str, str]:
    """Parse parameter strings into dictionary."""
    parsed = {}
    for param in params:
        if '=' in param:
            key, value = param.split('=', 1)
            parsed[key.strip()] = value.strip()
    return parsed


def _get_request_body(data: Optional[str], file: Optional[str], 
                     json_data: Optional[str], headers: Dict[str, str]) -> str:
    """Get request body from various sources."""
    if json_data:
        # Set content type if not already set
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        return json_data
    elif file:
        with open(file, 'r', encoding='utf-8') as f:
            return f.read()
    elif data:
        return data
    else:
        return ""


def _apply_template(state, template_name: str, environment_name: Optional[str], 
                   overrides: Dict[str, any]) -> Dict[str, any]:
    """Apply template with optional environment and overrides."""
    from ..core import TemplateExecutor
    
    executor = TemplateExecutor(state.template_manager)
    
    # Get environment if specified
    env_obj = None
    if environment_name:
        env_obj = state.env_manager.load_environment(environment_name)
    elif state.env_manager.get_current_environment():
        env_obj = state.env_manager.get_current_environment_obj()
    
    # Execute template
    return executor.execute_template(template_name, env_obj, overrides)


def _display_response(state, response: Response, format_type: str, output: Optional[str]):
    """Display response using the response formatter."""
    # Save to file if specified
    if output:
        _save_response_to_file(response, output)
        console.print(f"[green]Response saved to {output}[/green]")
    
    # Display response
    state.response_formatter.format_response(response, format_type)


def _save_response_to_file(response: Response, file_path: str):
    """Save response to file."""
    from ..formatters import ResponseSaver
    
    saver = ResponseSaver()
    saver.save_response(response, file_path, format_type="full")