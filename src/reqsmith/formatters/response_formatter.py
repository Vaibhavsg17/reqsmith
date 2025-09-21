"""
Response formatter with Rich integration for colored and formatted output.
"""
import json
import xml.dom.minidom
from typing import Any, Dict, Optional, Union
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.columns import Columns
from rich.tree import Tree
from rich import box
import logging

from ..core.http_client import Response


logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Formats API responses with color coding and syntax highlighting."""
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize response formatter.
        
        Args:
            console: Rich console instance (creates new one if None)
        """
        self.console = console or Console()
    
    def format_response(self, response: Response, format_type: str = "auto") -> None:
        """
        Format and display complete response.
        
        Args:
            response: Response object to format
            format_type: Format type (auto, json, xml, raw, table)
        """
        # Display response status and headers
        self._display_response_header(response)
        
        # Display response body based on format type
        if format_type == "auto":
            format_type = self._detect_response_format(response)
        
        self._display_response_body(response, format_type)
        
        # Display response metadata
        self._display_response_metadata(response)
    
    def colorize_status(self, status_code: int) -> Text:
        """
        Colorize HTTP status code based on category.
        
        Args:
            status_code: HTTP status code
            
        Returns:
            Rich Text object with colored status
        """
        status_text = str(status_code)
        
        if 200 <= status_code < 300:
            # Success - Green
            return Text(status_text, style="bold green")
        elif 300 <= status_code < 400:
            # Redirect - Cyan
            return Text(status_text, style="bold cyan")
        elif 400 <= status_code < 500:
            # Client Error - Yellow
            return Text(status_text, style="bold yellow")
        elif 500 <= status_code < 600:
            # Server Error - Red
            return Text(status_text, style="bold red")
        else:
            # Unknown - White
            return Text(status_text, style="bold white")
    
    def pretty_print_json(self, json_data: Union[str, Dict, Any], 
                         title: Optional[str] = None) -> None:
        """
        Pretty print JSON with syntax highlighting.
        
        Args:
            json_data: JSON data (string or object)
            title: Optional title for the panel
        """
        try:
            if isinstance(json_data, str):
                # Parse string to ensure it's valid JSON
                parsed = json.loads(json_data)
                formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            else:
                formatted = json.dumps(json_data, indent=2, ensure_ascii=False)
            
            syntax = Syntax(formatted, "json", theme="monokai", line_numbers=True)
            
            if title:
                panel = Panel(syntax, title=title, border_style="blue")
                self.console.print(panel)
            else:
                self.console.print(syntax)
                
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to format JSON: {e}")
            self.console.print(f"[red]Invalid JSON data: {e}[/red]")
    
    def pretty_print_xml(self, xml_data: str, title: Optional[str] = None) -> None:
        """
        Pretty print XML with formatting.
        
        Args:
            xml_data: XML string
            title: Optional title for the panel
        """
        try:
            # Parse and format XML
            dom = xml.dom.minidom.parseString(xml_data)
            formatted = dom.toprettyxml(indent="  ")
            
            # Remove empty lines
            lines = [line for line in formatted.split('\n') if line.strip()]
            formatted = '\n'.join(lines)
            
            syntax = Syntax(formatted, "xml", theme="monokai", line_numbers=True)
            
            if title:
                panel = Panel(syntax, title=title, border_style="green")
                self.console.print(panel)
            else:
                self.console.print(syntax)
                
        except Exception as e:
            logger.error(f"Failed to format XML: {e}")
            self.console.print(f"[red]Invalid XML data: {e}[/red]")
    
    def pretty_print_html(self, html_data: str, title: Optional[str] = None) -> None:
        """
        Pretty print HTML with syntax highlighting.
        
        Args:
            html_data: HTML string
            title: Optional title for the panel
        """
        try:
            syntax = Syntax(html_data, "html", theme="monokai", line_numbers=True)
            
            if title:
                panel = Panel(syntax, title=title, border_style="magenta")
                self.console.print(panel)
            else:
                self.console.print(syntax)
                
        except Exception as e:
            logger.error(f"Failed to format HTML: {e}")
            self.console.print(f"[red]Error formatting HTML: {e}[/red]")
    
    def format_headers(self, headers: Dict[str, str], title: str = "Headers") -> None:
        """
        Format and display HTTP headers.
        
        Args:
            headers: Dictionary of headers
            title: Title for the headers section
        """
        if not headers:
            return
        
        table = Table(title=title, box=box.ROUNDED)
        table.add_column("Header", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")
        
        for key, value in headers.items():
            table.add_row(key, value)
        
        self.console.print(table)
    
    def format_raw_text(self, text: str, title: Optional[str] = None) -> None:
        """
        Format raw text response.
        
        Args:
            text: Raw text content
            title: Optional title for the panel
        """
        if title:
            panel = Panel(text, title=title, border_style="white")
            self.console.print(panel)
        else:
            self.console.print(text)
    
    def _display_response_header(self, response: Response) -> None:
        """Display response status line and basic info."""
        # Status line
        status_text = self.colorize_status(response.status_code)
        method_text = Text(response.method, style="bold blue")
        url_text = Text(response.url, style="dim")
        
        header_line = Text.assemble(
            method_text, " ", status_text, " ", url_text
        )
        
        self.console.print()
        self.console.print(header_line)
        self.console.print("─" * 80, style="dim")
    
    def _display_response_body(self, response: Response, format_type: str) -> None:
        """Display formatted response body."""
        if not response.text.strip():
            self.console.print("[dim]Empty response body[/dim]")
            return
        
        if format_type == "json":
            self.pretty_print_json(response.text, "Response Body")
        elif format_type == "xml":
            self.pretty_print_xml(response.text, "Response Body")
        elif format_type == "html":
            self.pretty_print_html(response.text, "Response Body")
        elif format_type == "table":
            self._try_display_as_table(response.text)
        else:  # raw
            self.format_raw_text(response.text, "Response Body")
    
    def _display_response_metadata(self, response: Response) -> None:
        """Display response metadata (headers, timing, size)."""
        self.console.print()
        
        # Create metadata table
        metadata_table = Table(title="Response Metadata", box=box.SIMPLE)
        metadata_table.add_column("Property", style="cyan")
        metadata_table.add_column("Value", style="white")
        
        metadata_table.add_row("Status Code", str(response.status_code))
        metadata_table.add_row("Response Time", f"{response.elapsed_time:.3f}s")
        metadata_table.add_row("Content Size", f"{response.size_bytes} bytes")
        metadata_table.add_row("Content Type", 
                              response.headers.get("Content-Type", "Unknown"))
        
        self.console.print(metadata_table)
        
        # Display headers if present
        if response.headers:
            self.console.print()
            self.format_headers(response.headers, "Response Headers")
    
    def _detect_response_format(self, response: Response) -> str:
        """Detect appropriate format for response content."""
        content_type = response.headers.get("Content-Type", "").lower()
        
        if "application/json" in content_type or "text/json" in content_type:
            return "json"
        elif "application/xml" in content_type or "text/xml" in content_type:
            return "xml"
        elif "text/html" in content_type:
            return "html"
        else:
            # Try to detect from content
            text = response.text.strip()
            if text.startswith(('{', '[')):
                try:
                    json.loads(text)
                    return "json"
                except json.JSONDecodeError:
                    pass
            
            if text.startswith('<?xml') or text.startswith('<'):
                return "xml"
            
            return "raw"
    
    def _try_display_as_table(self, content: str) -> None:
        """Try to display JSON array content as a table."""
        try:
            data = json.loads(content)
            
            if isinstance(data, list) and data and isinstance(data[0], dict):
                # Display as table using TableFormatter
                from .table_formatter import TableFormatter
                table_formatter = TableFormatter(self.console)
                table_formatter.format_as_table(data)
            else:
                # Fall back to JSON formatting
                self.pretty_print_json(content, "Response Body")
                
        except (json.JSONDecodeError, KeyError, IndexError):
            # Fall back to raw text
            self.format_raw_text(content, "Response Body")


class CompactResponseFormatter(ResponseFormatter):
    """Compact version of response formatter for minimal output."""
    
    def format_response(self, response: Response, format_type: str = "auto") -> None:
        """Format response in compact mode."""
        # Single line status
        status_text = self.colorize_status(response.status_code)
        timing_text = Text(f"{response.elapsed_time:.3f}s", style="dim")
        size_text = Text(f"{response.size_bytes}B", style="dim")
        
        compact_line = Text.assemble(
            status_text, " ", timing_text, " ", size_text
        )
        
        self.console.print(compact_line)
        
        # Body only if not empty
        if response.text.strip():
            if format_type == "auto":
                format_type = self._detect_response_format(response)
            
            if format_type == "json":
                try:
                    data = json.loads(response.text)
                    # Show compact JSON
                    compact_json = json.dumps(data, separators=(',', ':'))
                    if len(compact_json) > 100:
                        compact_json = compact_json[:97] + "..."
                    self.console.print(compact_json)
                except json.JSONDecodeError:
                    self.console.print(response.text[:100] + "..." if len(response.text) > 100 else response.text)
            else:
                # Show truncated content
                content = response.text[:100] + "..." if len(response.text) > 100 else response.text
                self.console.print(content)


class ResponseSaver:
    """Utility for saving responses to files."""
    
    @staticmethod
    def save_response(response: Response, file_path: str, 
                     include_headers: bool = True,
                     format_json: bool = True) -> bool:
        """
        Save response to file.
        
        Args:
            response: Response object to save
            file_path: Path to save file
            include_headers: Whether to include headers in saved file
            format_json: Whether to format JSON responses
            
        Returns:
            True if successfully saved
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if include_headers:
                    # Write status line
                    f.write(f"{response.method} {response.url}\n")
                    f.write(f"Status: {response.status_code}\n")
                    f.write(f"Response Time: {response.elapsed_time:.3f}s\n")
                    f.write(f"Content Size: {response.size_bytes} bytes\n\n")
                    
                    # Write headers
                    f.write("Headers:\n")
                    for key, value in response.headers.items():
                        f.write(f"{key}: {value}\n")
                    f.write("\n")
                
                # Write body
                f.write("Response Body:\n")
                
                if format_json and response.headers.get("Content-Type", "").startswith("application/json"):
                    try:
                        data = json.loads(response.text)
                        formatted = json.dumps(data, indent=2, ensure_ascii=False)
                        f.write(formatted)
                    except json.JSONDecodeError:
                        f.write(response.text)
                else:
                    f.write(response.text)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save response to {file_path}: {e}")
            return False
    
    @staticmethod
    def save_response_body_only(response: Response, file_path: str) -> bool:
        """
        Save only response body to file.
        
        Args:
            response: Response object
            file_path: Path to save file
            
        Returns:
            True if successfully saved
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            return True
            
        except Exception as e:
            logger.error(f"Failed to save response body to {file_path}: {e}")
            return False
    
    @staticmethod
    def save_response_binary(response: Response, file_path: str) -> bool:
        """
        Save binary response content to file.
        
        Args:
            response: Response object
            file_path: Path to save file
            
        Returns:
            True if successfully saved
        """
        try:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return True
            
        except Exception as e:
            logger.error(f"Failed to save binary response to {file_path}: {e}")
            return False