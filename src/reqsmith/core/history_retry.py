"""
History querying and retry functionality for request history.
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging

from ..storage import RequestRecord
from ..core.http_client import HTTPClient, Response
from .history_manager import HistoryManager


logger = logging.getLogger(__name__)


class HistoryQueryEngine:
    """Advanced querying engine for request history."""
    
    def __init__(self, history_manager: HistoryManager):
        """
        Initialize history query engine.
        
        Args:
            history_manager: HistoryManager instance
        """
        self.history_manager = history_manager
    
    def query_by_time_range(self, start_time: datetime, end_time: datetime,
                           limit: Optional[int] = None) -> List[RequestRecord]:
        """
        Query history by time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum number of records to return
            
        Returns:
            List of RequestRecord objects in time range
        """
        return self.history_manager.get_history(
            limit=limit,
            date_from=start_time,
            date_to=end_time
        )
    
    def query_by_status_codes(self, status_codes: List[int],
                             limit: Optional[int] = None) -> List[RequestRecord]:
        """
        Query history by status codes.
        
        Args:
            status_codes: List of status codes to match
            limit: Maximum number of records to return
            
        Returns:
            List of RequestRecord objects with matching status codes
        """
        all_records = self.history_manager.get_history()
        matching_records = []
        
        for record in all_records:
            if record.response_status in status_codes:
                matching_records.append(record)
                if limit and len(matching_records) >= limit:
                    break
        
        return matching_records
    
    def query_successful_requests(self, limit: Optional[int] = None) -> List[RequestRecord]:
        """
        Query successful requests (2xx and 3xx status codes).
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of successful RequestRecord objects
        """
        all_records = self.history_manager.get_history()
        successful_records = []
        
        for record in all_records:
            if record.is_successful():
                successful_records.append(record)
                if limit and len(successful_records) >= limit:
                    break
        
        return successful_records
    
    def query_failed_requests(self, limit: Optional[int] = None) -> List[RequestRecord]:
        """
        Query failed requests (4xx and 5xx status codes).
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of failed RequestRecord objects
        """
        all_records = self.history_manager.get_history()
        failed_records = []
        
        for record in all_records:
            if not record.is_successful():
                failed_records.append(record)
                if limit and len(failed_records) >= limit:
                    break
        
        return failed_records
    
    def query_by_response_time(self, min_time: Optional[float] = None,
                              max_time: Optional[float] = None,
                              limit: Optional[int] = None) -> List[RequestRecord]:
        """
        Query history by response time range.
        
        Args:
            min_time: Minimum response time in seconds
            max_time: Maximum response time in seconds
            limit: Maximum number of records to return
            
        Returns:
            List of RequestRecord objects within response time range
        """
        all_records = self.history_manager.get_history()
        matching_records = []
        
        for record in all_records:
            if min_time is not None and record.response_time < min_time:
                continue
            if max_time is not None and record.response_time > max_time:
                continue
            
            matching_records.append(record)
            if limit and len(matching_records) >= limit:
                break
        
        return matching_records
    
    def query_by_template(self, template_name: str,
                         limit: Optional[int] = None) -> List[RequestRecord]:
        """
        Query history by template name.
        
        Args:
            template_name: Template name to match
            limit: Maximum number of records to return
            
        Returns:
            List of RequestRecord objects using the template
        """
        return self.history_manager.get_history(
            limit=limit,
            template_filter=template_name
        )
    
    def query_by_environment(self, environment_name: str,
                            limit: Optional[int] = None) -> List[RequestRecord]:
        """
        Query history by environment name.
        
        Args:
            environment_name: Environment name to match
            limit: Maximum number of records to return
            
        Returns:
            List of RequestRecord objects using the environment
        """
        return self.history_manager.get_history(
            limit=limit,
            environment_filter=environment_name
        )
    
    def query_recent_requests(self, hours: int = 24,
                             limit: Optional[int] = None) -> List[RequestRecord]:
        """
        Query recent requests within specified hours.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of records to return
            
        Returns:
            List of recent RequestRecord objects
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return self.query_by_time_range(cutoff_time, datetime.now(), limit)
    
    def query_duplicate_requests(self, limit: Optional[int] = None) -> Dict[str, List[RequestRecord]]:
        """
        Find duplicate requests (same method and URL).
        
        Args:
            limit: Maximum number of duplicate groups to return
            
        Returns:
            Dictionary mapping request signatures to lists of duplicate records
        """
        all_records = self.history_manager.get_history()
        request_groups = {}
        
        for record in all_records:
            signature = f"{record.method}:{record.url}"
            if signature not in request_groups:
                request_groups[signature] = []
            request_groups[signature].append(record)
        
        # Filter to only groups with duplicates
        duplicates = {sig: records for sig, records in request_groups.items() 
                     if len(records) > 1}
        
        # Sort by number of duplicates (descending)
        sorted_duplicates = dict(sorted(duplicates.items(), 
                                      key=lambda x: len(x[1]), reverse=True))
        
        if limit:
            sorted_duplicates = dict(list(sorted_duplicates.items())[:limit])
        
        return sorted_duplicates
    
    def get_request_patterns(self) -> Dict[str, Any]:
        """
        Analyze request patterns in history.
        
        Returns:
            Dictionary with pattern analysis
        """
        all_records = self.history_manager.get_history()
        
        if not all_records:
            return {'error': 'No history records found'}
        
        # Analyze patterns
        method_patterns = {}
        url_patterns = {}
        time_patterns = {'hourly': {}, 'daily': {}}
        status_patterns = {}
        
        for record in all_records:
            # Method patterns
            method = record.method
            method_patterns[method] = method_patterns.get(method, 0) + 1
            
            # URL patterns (domain extraction)
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(record.url)
                domain = parsed_url.netloc
                url_patterns[domain] = url_patterns.get(domain, 0) + 1
            except:
                pass
            
            # Time patterns
            dt = datetime.fromtimestamp(record.timestamp)
            hour = dt.hour
            day = dt.strftime('%A')
            
            time_patterns['hourly'][hour] = time_patterns['hourly'].get(hour, 0) + 1
            time_patterns['daily'][day] = time_patterns['daily'].get(day, 0) + 1
            
            # Status patterns
            status_category = record.get_status_category()
            status_patterns[status_category] = status_patterns.get(status_category, 0) + 1
        
        return {
            'total_requests': len(all_records),
            'method_distribution': method_patterns,
            'domain_distribution': dict(sorted(url_patterns.items(), 
                                             key=lambda x: x[1], reverse=True)[:10]),
            'time_patterns': time_patterns,
            'status_distribution': status_patterns
        }


class HistoryRetryManager:
    """Manager for retrying requests from history."""
    
    def __init__(self, history_manager: HistoryManager, http_client: HTTPClient):
        """
        Initialize history retry manager.
        
        Args:
            history_manager: HistoryManager instance
            http_client: HTTPClient instance for making requests
        """
        self.history_manager = history_manager
        self.http_client = http_client
    
    def retry_last_request(self) -> Optional[Response]:
        """
        Retry the last request from history.
        
        Returns:
            Response object or None if no history or retry failed
        """
        last_request = self.history_manager.get_last_request()
        if not last_request:
            logger.warning("No requests in history to retry")
            return None
        
        return self.retry_request_record(last_request)
    
    def retry_request_by_index(self, index: int) -> Optional[Response]:
        """
        Retry a request by its index in history.
        
        Args:
            index: Index of request to retry (0 = most recent)
            
        Returns:
            Response object or None if index invalid or retry failed
        """
        request_record = self.history_manager.get_request_by_index(index)
        if not request_record:
            logger.warning(f"No request found at index {index}")
            return None
        
        return self.retry_request_record(request_record)
    
    def retry_request_record(self, record: RequestRecord) -> Optional[Response]:
        """
        Retry a specific request record.
        
        Args:
            record: RequestRecord to retry
            
        Returns:
            Response object or None if retry failed
        """
        try:
            logger.info(f"Retrying request: {record.method} {record.url}")
            
            # Make the request
            response = self.http_client.send_request(
                method=record.method,
                url=record.url,
                headers=record.headers,
                body=record.body if record.body else None,
                params=record.params if record.params else None
            )
            
            # Add the retry to history
            self.history_manager.add_request(
                response,
                template_name=record.template_name,
                environment=record.environment,
                cached=False
            )
            
            logger.info(f"Retry completed: {response.status_code}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to retry request: {e}")
            return None
    
    def retry_failed_requests(self, limit: Optional[int] = None,
                             max_retries: int = 3) -> List[Tuple[RequestRecord, Optional[Response]]]:
        """
        Retry all failed requests from history.
        
        Args:
            limit: Maximum number of failed requests to retry
            max_retries: Maximum retry attempts per request
            
        Returns:
            List of tuples (original_record, retry_response)
        """
        query_engine = HistoryQueryEngine(self.history_manager)
        failed_requests = query_engine.query_failed_requests(limit)
        
        results = []
        
        for record in failed_requests:
            retry_response = None
            
            for attempt in range(max_retries):
                try:
                    retry_response = self.retry_request_record(record)
                    if retry_response and retry_response.is_success():
                        break  # Success, no need to retry again
                except Exception as e:
                    logger.warning(f"Retry attempt {attempt + 1} failed: {e}")
                    continue
            
            results.append((record, retry_response))
        
        return results
    
    def retry_requests_by_criteria(self, method: Optional[str] = None,
                                  status_code: Optional[int] = None,
                                  url_pattern: Optional[str] = None,
                                  limit: Optional[int] = None) -> List[Tuple[RequestRecord, Optional[Response]]]:
        """
        Retry requests matching specific criteria.
        
        Args:
            method: HTTP method filter
            status_code: Status code filter
            url_pattern: URL pattern filter
            limit: Maximum number of requests to retry
            
        Returns:
            List of tuples (original_record, retry_response)
        """
        matching_requests = self.history_manager.get_history(
            limit=limit,
            method_filter=method,
            status_filter=status_code,
            url_pattern=url_pattern
        )
        
        results = []
        
        for record in matching_requests:
            retry_response = self.retry_request_record(record)
            results.append((record, retry_response))
        
        return results
    
    def create_retry_batch(self, indices: List[int]) -> 'RetryBatch':
        """
        Create a batch of requests to retry.
        
        Args:
            indices: List of history indices to include in batch
            
        Returns:
            RetryBatch object
        """
        records = []
        for index in indices:
            record = self.history_manager.get_request_by_index(index)
            if record:
                records.append(record)
        
        return RetryBatch(self, records)


class RetryBatch:
    """Batch of requests to retry with progress tracking."""
    
    def __init__(self, retry_manager: HistoryRetryManager, records: List[RequestRecord]):
        """
        Initialize retry batch.
        
        Args:
            retry_manager: HistoryRetryManager instance
            records: List of RequestRecord objects to retry
        """
        self.retry_manager = retry_manager
        self.records = records
        self.results = []
        self.completed = 0
        self.successful = 0
        self.failed = 0
    
    def execute(self, progress_callback: Optional[callable] = None) -> List[Tuple[RequestRecord, Optional[Response]]]:
        """
        Execute the retry batch.
        
        Args:
            progress_callback: Optional callback function for progress updates
            
        Returns:
            List of tuples (original_record, retry_response)
        """
        self.results = []
        self.completed = 0
        self.successful = 0
        self.failed = 0
        
        total_requests = len(self.records)
        
        for i, record in enumerate(self.records):
            try:
                retry_response = self.retry_manager.retry_request_record(record)
                
                if retry_response and retry_response.is_success():
                    self.successful += 1
                else:
                    self.failed += 1
                
                self.results.append((record, retry_response))
                self.completed += 1
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(self.completed, total_requests, record, retry_response)
                
            except Exception as e:
                logger.error(f"Error in batch retry: {e}")
                self.results.append((record, None))
                self.failed += 1
                self.completed += 1
        
        return self.results
    
    def get_progress(self) -> Dict[str, Any]:
        """
        Get current progress of batch execution.
        
        Returns:
            Dictionary with progress information
        """
        total = len(self.records)
        return {
            'total_requests': total,
            'completed': self.completed,
            'successful': self.successful,
            'failed': self.failed,
            'remaining': total - self.completed,
            'progress_percent': (self.completed / total * 100) if total > 0 else 0
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of batch execution results.
        
        Returns:
            Dictionary with execution summary
        """
        if not self.results:
            return {'error': 'Batch not executed yet'}
        
        success_rate = (self.successful / len(self.results) * 100) if self.results else 0
        
        return {
            'total_requests': len(self.results),
            'successful_retries': self.successful,
            'failed_retries': self.failed,
            'success_rate': round(success_rate, 2),
            'execution_completed': self.completed == len(self.records)
        }