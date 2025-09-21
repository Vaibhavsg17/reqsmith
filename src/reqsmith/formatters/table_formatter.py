"""
Table formatter for displaying array responses in tabular format.
"""
import json
from typing import List, Dict, Any, Optional, Union, Set
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich import box
import logging


logger = logging.getLogger(__name__)


class TableFormatter:
    """Formats array data as Rich tables with intelligent column handling."""
    
    def __init__(self, console: Optional[Console] = None, max_rows: int = 100):
        """
        Initialize table formatter.
        
        Args:
            console: Rich console instance
            max_rows: Maximum number of rows to display
        """
        self.console = console or Console()
        self.max_rows = max_rows
    
    def format_as_table(self, data: Union[List[Dict], str], 
                       title: Optional[str] = None) -> None:
        """
        Format data as a table if possible.
        
        Args:
            data: List of dictionaries or JSON string
            title: Optional table title
        """
        try:
            # Parse JSON string if needed
            if isinstance(data, str):
                parsed_data = json.loads(data)
            else:
                parsed_data = data
            
            # Check if data can be displayed as table
            if not self.detect_table_structure(parsed_data):
                self.console.print("[yellow]Data cannot be displayed as table[/yellow]")
                return
            
            # Create and display table
            table = self.create_rich_table(parsed_data, title)
            self.console.print(table)
            
            # Show pagination info if data was truncated
            if len(parsed_data) > self.max_rows:
                self.console.print(f"[dim]Showing {self.max_rows} of {len(parsed_data)} rows[/dim]")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for table formatting: {e}")
            self.console.print(f"[red]Invalid JSON data: {e}[/red]")
        except Exception as e:
            logger.error(f"Failed to format table: {e}")
            self.console.print(f"[red]Error formatting table: {e}[/red]")
    
    def detect_table_structure(self, data: Any) -> bool:
        """
        Detect if data can be displayed as a table.
        
        Args:
            data: Data to analyze
            
        Returns:
            True if data can be displayed as table
        """
        # Must be a list
        if not isinstance(data, list):
            return False
        
        # Must not be empty
        if not data:
            return False
        
        # All items must be dictionaries
        if not all(isinstance(item, dict) for item in data):
            return False
        
        # Check if there are common keys across items
        if len(data) == 1:
            return True
        
        # Get keys from first few items to determine structure
        sample_size = min(5, len(data))
        key_sets = [set(item.keys()) for item in data[:sample_size]]
        
        # Check for some common keys
        common_keys = set.intersection(*key_sets) if key_sets else set()
        
        # Need at least one common key
        return len(common_keys) > 0
    
    def create_rich_table(self, data: List[Dict], title: Optional[str] = None) -> Table:
        """
        Create Rich table from list of dictionaries.
        
        Args:
            data: List of dictionaries
            title: Optional table title
            
        Returns:
            Rich Table object
        """
        if not data:
            return Table(title=title or "Empty Table")
        
        # Limit rows for display
        display_data = data[:self.max_rows]
        
        # Determine columns
        headers = self._determine_columns(display_data)
        
        # Create table
        table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold cyan")
        
        # Add columns with appropriate styling
        for header in headers:
            table.add_column(header, overflow="fold", max_width=30)
        
        # Add rows
        for item in display_data:
            row_values = []
            for header in headers:
                value = item.get(header, "")
                formatted_value = self._format_cell_value(value)
                row_values.append(formatted_value)
            
            table.add_row(*row_values)
        
        return table
    
    def create_nested_table(self, data: List[Dict], title: Optional[str] = None,
                           max_depth: int = 2) -> Table:
        """
        Create table that handles nested objects by flattening them.
        
        Args:
            data: List of dictionaries with potential nested objects
            title: Optional table title
            max_depth: Maximum nesting depth to flatten
            
        Returns:
            Rich Table object
        """
        if not data:
            return Table(title=title or "Empty Table")
        
        # Flatten nested objects
        flattened_data = []
        for item in data[:self.max_rows]:
            flattened_item = self._flatten_dict(item, max_depth=max_depth)
            flattened_data.append(flattened_item)
        
        return self.create_rich_table(flattened_data, title)
    
    def create_summary_table(self, data: List[Dict], title: Optional[str] = None) -> Table:
        """
        Create summary table showing data statistics.
        
        Args:
            data: List of dictionaries
            title: Optional table title
            
        Returns:
            Rich Table with summary statistics
        """
        if not data:
            return Table(title=title or "Empty Summary")
        
        # Analyze data structure
        total_rows = len(data)
        all_keys = set()
        key_counts = {}
        
        for item in data:
            if isinstance(item, dict):
                for key in item.keys():
                    all_keys.add(key)
                    key_counts[key] = key_counts.get(key, 0) + 1
        
        # Create summary table
        table = Table(title=title or "Data Summary", box=box.SIMPLE)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Total Rows", str(total_rows))
        table.add_row("Total Columns", str(len(all_keys)))
        
        # Show most common columns
        if key_counts:
            sorted_keys = sorted(key_counts.items(), key=lambda x: x[1], reverse=True)
            common_keys = [f"{key} ({count})" for key, count in sorted_keys[:5]]
            table.add_row("Common Columns", ", ".join(common_keys))
        
        return table
    
    def _determine_columns(self, data: List[Dict]) -> List[str]:
        """Determine which columns to display based on data analysis."""
        if not data:
            return []
        
        # Count frequency of each key
        key_counts = {}
        for item in data:
            for key in item.keys():
                key_counts[key] = key_counts.get(key, 0) + 1
        
        # Sort keys by frequency (most common first)
        sorted_keys = sorted(key_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Take keys that appear in at least 50% of items, up to 10 columns
        threshold = len(data) * 0.5
        selected_keys = []
        
        for key, count in sorted_keys:
            if count >= threshold and len(selected_keys) < 10:
                selected_keys.append(key)
        
        # If no keys meet threshold, take the most common ones
        if not selected_keys:
            selected_keys = [key for key, _ in sorted_keys[:10]]
        
        return selected_keys
    
    def _format_cell_value(self, value: Any) -> str:
        """Format a cell value for display in table."""
        if value is None:
            return "[dim]null[/dim]"
        elif isinstance(value, bool):
            return "[green]true[/green]" if value else "[red]false[/red]"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            # Truncate long strings
            if len(value) > 50:
                return value[:47] + "..."
            return value
        elif isinstance(value, (list, dict)):
            # Show compact representation of complex objects
            try:
                compact = json.dumps(value, separators=(',', ':'))
                if len(compact) > 50:
                    return compact[:47] + "..."
                return compact
            except (TypeError, ValueError):
                return str(type(value).__name__)
        else:
            return str(value)
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '.', 
                     max_depth: int = 2, current_depth: int = 0) -> Dict:
        """
        Flatten nested dictionary.
        
        Args:
            d: Dictionary to flatten
            parent_key: Parent key prefix
            sep: Separator for nested keys
            max_depth: Maximum depth to flatten
            current_depth: Current nesting depth
            
        Returns:
            Flattened dictionary
        """
        items = []
        
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict) and current_depth < max_depth:
                items.extend(
                    self._flatten_dict(v, new_key, sep, max_depth, current_depth + 1).items()
                )
            elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and current_depth < max_depth:
                # Handle list of objects by taking first item
                items.extend(
                    self._flatten_dict(v[0], f"{new_key}[0]", sep, max_depth, current_depth + 1).items()
                )
            else:
                items.append((new_key, v))
        
        return dict(items)


class PaginatedTableFormatter(TableFormatter):
    """Table formatter with pagination support."""
    
    def __init__(self, console: Optional[Console] = None, 
                 rows_per_page: int = 20):
        """
        Initialize paginated table formatter.
        
        Args:
            console: Rich console instance
            rows_per_page: Number of rows per page
        """
        super().__init__(console, max_rows=rows_per_page)
        self.rows_per_page = rows_per_page
    
    def format_paginated_table(self, data: List[Dict], 
                              page: int = 1,
                              title: Optional[str] = None) -> None:
        """
        Format table with pagination.
        
        Args:
            data: List of dictionaries
            page: Page number (1-based)
            title: Optional table title
        """
        if not data:
            self.console.print("[yellow]No data to display[/yellow]")
            return
        
        total_rows = len(data)
        total_pages = (total_rows + self.rows_per_page - 1) // self.rows_per_page
        
        # Validate page number
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages
        
        # Calculate slice indices
        start_idx = (page - 1) * self.rows_per_page
        end_idx = min(start_idx + self.rows_per_page, total_rows)
        
        # Get page data
        page_data = data[start_idx:end_idx]
        
        # Create table with pagination info in title
        page_title = f"{title or 'Data'} (Page {page}/{total_pages})"
        table = self.create_rich_table(page_data, page_title)
        
        self.console.print(table)
        
        # Show navigation info
        nav_info = f"Showing rows {start_idx + 1}-{end_idx} of {total_rows}"
        self.console.print(f"[dim]{nav_info}[/dim]")


class CSVTableFormatter:
    """Formatter for converting table data to CSV format."""
    
    @staticmethod
    def to_csv(data: List[Dict], include_headers: bool = True) -> str:
        """
        Convert table data to CSV format.
        
        Args:
            data: List of dictionaries
            include_headers: Whether to include header row
            
        Returns:
            CSV formatted string
        """
        if not data:
            return ""
        
        import csv
        import io
        
        # Determine all possible columns
        all_keys = set()
        for item in data:
            if isinstance(item, dict):
                all_keys.update(item.keys())
        
        headers = sorted(list(all_keys))
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        if include_headers:
            writer.writerow(headers)
        
        for item in data:
            row = []
            for header in headers:
                value = item.get(header, "")
                # Convert complex objects to JSON strings
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, separators=(',', ':'))
                row.append(str(value))
            writer.writerow(row)
        
        return output.getvalue()
    
    @staticmethod
    def save_csv(data: List[Dict], file_path: str, 
                include_headers: bool = True) -> bool:
        """
        Save table data as CSV file.
        
        Args:
            data: List of dictionaries
            file_path: Path to save CSV file
            include_headers: Whether to include header row
            
        Returns:
            True if successfully saved
        """
        try:
            csv_content = CSVTableFormatter.to_csv(data, include_headers)
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                f.write(csv_content)
            return True
        except Exception as e:
            logger.error(f"Failed to save CSV to {file_path}: {e}")
            return False