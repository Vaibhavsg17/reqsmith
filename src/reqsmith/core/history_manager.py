"""
History manager for storing and retrieving request history with persistence.
"""
import time
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging

from ..storage import (
    HybridStorage,
    HistoryStorage,
    RequestRecord
)
from ..core.http_client import Response


logger = logging.getLogger(__name__)


class HistoryManager:
    """Manages request history with FIFO persistence and configurable size limits."""
    
    def __init__(self, storage: HybridStorage, max_entries: int = 1000):
        """
        Initialize history manager.
        
        Args:
            storage: HybridStorage instance for persistence
            max_entries: Maximum number of history entries to keep
        """
        self.storage = storage
        self.history_storage = HistoryStorage(storage, max_entries)
        self.max_entries = max_entries
    
    def add_request(self, response: Response, template_name: Optional[str] = None,
                   environment: Optional[str] = None, cached: bool = False) -> bool:
        """
        Add a request to history.
        
        Args:
            response: Response object from the request
            template_name: Name of template used (if any)
            environment: Environment used (if any)
            cached: Whether the response was cached
            
        Returns:
            True if request was added to history successfully
        """
        try:
            # Create request record
            record = RequestRecord(
                timestamp=time.time(),
                method=response.method,
                url=response.url,
                headers=response.request_headers,
                body=response.request_body,
                response_status=response.status_code,
                response_time=response.elapsed_time,
                response_size=response.size_bytes,
                cached=cached,
                template_name=template_name,
                environment=environment
            )
            
            # Validate record
            if not record.validate():
                logger.error("Invalid request record")
                return False
            
            # Add to storage
            success = self.history_storage.add_request(record)
            if success:
                logger.debug(f"Added request to history: {response.method} {response.url}")
            else:
                logger.error(f"Failed to add request to history: {response.method} {response.url}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding request to history: {e}")
            return False
    
    def get_history(self, limit: Optional[int] = None,
                   method_filter: Optional[str] = None,
                   status_filter: Optional[int] = None,
                   url_pattern: Optional[str] = None,
                   template_filter: Optional[str] = None,
                   environment_filter: Optional[str] = None,
                   date_from: Optional[datetime] = None,
                   date_to: Optional[datetime] = None) -> List[RequestRecord]:
        """
        Get request history with optional filtering.
        
        Args:
            limit: Maximum number of records to return
            method_filter: Filter by HTTP method
            status_filter: Filter by response status code
            url_pattern: Filter by URL pattern (substring match)
            template_filter: Filter by template name
            environment_filter: Filter by environment name
            date_from: Filter records from this date
            date_to: Filter records to this date
            
        Returns:
            List of RequestRecord objects
        """
        try:
            # Get all history records
            all_records = self.history_storage.get_history()
            
            # Apply filters
            filtered_records = self._apply_filters(
                all_records, method_filter, status_filter, url_pattern,
                template_filter, environment_filter, date_from, date_to
            )
            
            # Apply limit
            if limit and limit > 0:
                filtered_records = filtered_records[-limit:]
            
            return filtered_records
            
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []
    
    def get_last_request(self) -> Optional[RequestRecord]:
        """
        Get the most recent request from history.
        
        Returns:
            Last RequestRecord or None if history is empty
        """
        try:
            return self.history_storage.get_last_request()
        except Exception as e:
            logger.error(f"Error getting last request: {e}")
            return None
    
    def get_request_by_index(self, index: int) -> Optional[RequestRecord]:
        """
        Get a request by its index in history (0 = most recent).
        
        Args:
            index: Index of request (0-based, 0 = most recent)
            
        Returns:
            RequestRecord or None if index is invalid
        """
        try:
            history = self.history_storage.get_history()
            if 0 <= index < len(history):
                # Reverse index since we want 0 to be most recent
                return history[-(index + 1)]
            return None
        except Exception as e:
            logger.error(f"Error getting request by index {index}: {e}")
            return None
    
    def search_history(self, query: str, search_fields: Optional[List[str]] = None) -> List[RequestRecord]:
        """
        Search history records by query string.
        
        Args:
            query: Search query
            search_fields: Fields to search in (url, method, template_name, environment)
            
        Returns:
            List of matching RequestRecord objects
        """
        if not query or not query.strip():
            return []
        
        query = query.lower().strip()
        search_fields = search_fields or ['url', 'method', 'template_name', 'environment']
        
        try:
            all_records = self.history_storage.get_history()
            matching_records = []
            
            for record in all_records:
                # Search in specified fields
                if 'url' in search_fields and query in record.url.lower():
                    matching_records.append(record)
                    continue
                
                if 'method' in search_fields and query in record.method.lower():
                    matching_records.append(record)
                    continue
                
                if 'template_name' in search_fields and record.template_name:
                    if query in record.template_name.lower():
                        matching_records.append(record)
                        continue
                
                if 'environment' in search_fields and record.environment:
                    if query in record.environment.lower():
                        matching_records.append(record)
                        continue
            
            return matching_records
            
        except Exception as e:
            logger.error(f"Error searching history: {e}")
            return []
    
    def clear_history(self) -> bool:
        """
        Clear all request history.
        
        Returns:
            True if history was cleared successfully
        """
        try:
            success = self.history_storage.clear_history()
            if success:
                logger.info("Request history cleared")
            else:
                logger.error("Failed to clear request history")
            return success
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            return False
    
    def delete_history_entries(self, indices: List[int]) -> int:
        """
        Delete specific history entries by index.
        
        Args:
            indices: List of indices to delete (0-based, 0 = most recent)
            
        Returns:
            Number of entries successfully deleted
        """
        try:
            history = self.history_storage.get_history()
            if not history:
                return 0
            
            # Convert indices to actual positions and sort in reverse order
            valid_indices = []
            for index in indices:
                if 0 <= index < len(history):
                    # Convert to actual position (reverse index)
                    actual_pos = len(history) - 1 - index
                    valid_indices.append(actual_pos)
            
            # Sort in reverse order to maintain indices when deleting
            valid_indices.sort(reverse=True)
            
            # Remove entries
            deleted_count = 0
            for pos in valid_indices:
                if 0 <= pos < len(history):
                    history.pop(pos)
                    deleted_count += 1
            
            # Save updated history
            if deleted_count > 0:
                # Convert RequestRecord objects to dictionaries before saving
                history_dicts = [record.to_dict() if hasattr(record, 'to_dict') else record for record in history]
                self.history_storage._save_history_list(history_dicts)
                logger.info(f"Deleted {deleted_count} history entries")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting history entries: {e}")
            return 0
    
    def get_history_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about request history.
        
        Returns:
            Dictionary with history statistics
        """
        try:
            return self.history_storage.get_history_stats()
        except Exception as e:
            logger.error(f"Error getting history statistics: {e}")
            return {'error': str(e)}
    
    def get_history_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get summary of recent history activity.
        
        Args:
            days: Number of days to include in summary
            
        Returns:
            Dictionary with history summary
        """
        try:
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            recent_records = []
            
            all_records = self.history_storage.get_history()
            for record in all_records:
                if record.timestamp >= cutoff_time:
                    recent_records.append(record)
            
            if not recent_records:
                return {
                    'period_days': days,
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': 0,
                    'average_response_time': 0,
                    'most_used_methods': {},
                    'most_requested_urls': {},
                    'status_distribution': {}
                }
            
            # Calculate statistics
            total_requests = len(recent_records)
            successful_requests = sum(1 for r in recent_records if r.is_successful())
            failed_requests = total_requests - successful_requests
            
            total_response_time = sum(r.response_time for r in recent_records)
            avg_response_time = total_response_time / total_requests
            
            # Method distribution
            methods = {}
            for record in recent_records:
                method = record.method
                methods[method] = methods.get(method, 0) + 1
            
            # URL distribution (top 10)
            urls = {}
            for record in recent_records:
                url = record.url
                urls[url] = urls.get(url, 0) + 1
            
            most_requested_urls = dict(sorted(urls.items(), key=lambda x: x[1], reverse=True)[:10])
            
            # Status code distribution
            statuses = {}
            for record in recent_records:
                status = record.response_status
                statuses[status] = statuses.get(status, 0) + 1
            
            return {
                'period_days': days,
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'success_rate': (successful_requests / total_requests) * 100,
                'average_response_time': round(avg_response_time, 3),
                'most_used_methods': methods,
                'most_requested_urls': most_requested_urls,
                'status_distribution': statuses
            }
            
        except Exception as e:
            logger.error(f"Error getting history summary: {e}")
            return {'error': str(e)}
    
    def export_history(self, file_path: str, format_type: str = 'json',
                      limit: Optional[int] = None) -> bool:
        """
        Export history to file.
        
        Args:
            file_path: Path to export file
            format_type: Export format (json, csv)
            limit: Maximum number of records to export
            
        Returns:
            True if export successful
        """
        try:
            history = self.history_storage.get_history(limit)
            
            if format_type.lower() == 'csv':
                return self._export_history_csv(history, file_path)
            else:
                return self._export_history_json(history, file_path)
                
        except Exception as e:
            logger.error(f"Error exporting history: {e}")
            return False
    
    def _apply_filters(self, records: List[RequestRecord],
                      method_filter: Optional[str],
                      status_filter: Optional[int],
                      url_pattern: Optional[str],
                      template_filter: Optional[str],
                      environment_filter: Optional[str],
                      date_from: Optional[datetime],
                      date_to: Optional[datetime]) -> List[RequestRecord]:
        """Apply filters to history records."""
        filtered = records
        
        if method_filter:
            filtered = [r for r in filtered if r.method.upper() == method_filter.upper()]
        
        if status_filter:
            filtered = [r for r in filtered if r.response_status == status_filter]
        
        if url_pattern:
            filtered = [r for r in filtered if url_pattern.lower() in r.url.lower()]
        
        if template_filter:
            filtered = [r for r in filtered if r.template_name == template_filter]
        
        if environment_filter:
            filtered = [r for r in filtered if r.environment == environment_filter]
        
        if date_from:
            from_timestamp = date_from.timestamp()
            filtered = [r for r in filtered if r.timestamp >= from_timestamp]
        
        if date_to:
            to_timestamp = date_to.timestamp()
            filtered = [r for r in filtered if r.timestamp <= to_timestamp]
        
        return filtered
    
    def _export_history_json(self, history: List[RequestRecord], file_path: str) -> bool:
        """Export history to JSON file."""
        import json
        from pathlib import Path
        
        try:
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'total_records': len(history),
                'records': [record.to_dict() for record in history]
            }
            
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting history to JSON: {e}")
            return False
    
    def _export_history_csv(self, history: List[RequestRecord], file_path: str) -> bool:
        """Export history to CSV file."""
        import csv
        from pathlib import Path
        
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    'Timestamp', 'Method', 'URL', 'Status Code', 'Response Time (s)',
                    'Response Size (bytes)', 'Template', 'Environment', 'Cached'
                ])
                
                # Write data
                for record in history:
                    writer.writerow([
                        record.get_formatted_timestamp(),
                        record.method,
                        record.url,
                        record.response_status,
                        f"{record.response_time:.3f}",
                        record.response_size,
                        record.template_name or '',
                        record.environment or '',
                        'Yes' if record.cached else 'No'
                    ])
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting history to CSV: {e}")
            return False
    
    def get_max_entries(self) -> int:
        """Get maximum number of history entries."""
        return self.max_entries
    
    def set_max_entries(self, max_entries: int) -> bool:
        """
        Set maximum number of history entries.
        
        Args:
            max_entries: New maximum number of entries
            
        Returns:
            True if limit was updated successfully
        """
        if max_entries <= 0:
            raise ValueError("Max entries must be positive")
        
        try:
            self.max_entries = max_entries
            self.history_storage.max_entries = max_entries
            
            # Trim history if necessary
            current_history = self.history_storage.get_history()
            if len(current_history) > max_entries:
                trimmed_history = current_history[-max_entries:]
                self.history_storage._save_history_list(trimmed_history)
                logger.info(f"Trimmed history to {max_entries} entries")
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting max entries: {e}")
            return False