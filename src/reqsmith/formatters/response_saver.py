"""
Enhanced response saving functionality with multiple format support.
"""
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from ..core.http_client import Response


logger = logging.getLogger(__name__)


class ResponseSaver:
    """Enhanced utility for saving responses in various formats."""
    
    def __init__(self, default_directory: Optional[str] = None):
        """
        Initialize response saver.
        
        Args:
            default_directory: Default directory for saving responses
        """
        self.default_directory = Path(default_directory) if default_directory else Path.cwd()
        self.default_directory.mkdir(parents=True, exist_ok=True)
    
    def save_response(self, response: Response, file_path: Optional[str] = None,
                     format_type: str = "full", include_metadata: bool = True) -> str:
        """
        Save response to file with automatic naming if path not provided.
        
        Args:
            response: Response object to save
            file_path: Optional file path (auto-generated if None)
            format_type: Save format (full, body, headers, metadata)
            include_metadata: Whether to include response metadata
            
        Returns:
            Path to saved file
            
        Raises:
            ValueError: If save operation fails
        """
        if not file_path:
            file_path = self._generate_filename(response)
        
        file_path = Path(file_path)
        
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if format_type == "full":
                self._save_full_response(response, file_path, include_metadata)
            elif format_type == "body":
                self._save_body_only(response, file_path)
            elif format_type == "headers":
                self._save_headers_only(response, file_path)
            elif format_type == "metadata":
                self._save_metadata_only(response, file_path)
            else:
                raise ValueError(f"Unknown format type: {format_type}")
            
            logger.info(f"Response saved to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save response to {file_path}: {e}")
            raise ValueError(f"Save operation failed: {e}")
    
    def save_response_json(self, response: Response, file_path: Optional[str] = None,
                          pretty_print: bool = True) -> str:
        """
        Save response as JSON file.
        
        Args:
            response: Response object
            file_path: Optional file path
            pretty_print: Whether to format JSON nicely
            
        Returns:
            Path to saved file
        """
        if not file_path:
            file_path = self._generate_filename(response, extension=".json")
        
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            response_data = {
                "request": {
                    "method": response.method,
                    "url": response.url,
                    "headers": response.request_headers,
                    "body": response.request_body
                },
                "response": {
                    "status_code": response.status_code,
                    "headers": response.headers,
                    "body": response.text,
                    "elapsed_time": response.elapsed_time,
                    "size_bytes": response.size_bytes
                },
                "metadata": {
                    "saved_at": datetime.now().isoformat(),
                    "content_type": response.headers.get("Content-Type", "unknown")
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if pretty_print:
                    json.dump(response_data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(response_data, f, separators=(',', ':'), ensure_ascii=False)
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save JSON response to {file_path}: {e}")
            raise ValueError(f"JSON save operation failed: {e}")
    
    def save_response_binary(self, response: Response, file_path: Optional[str] = None) -> str:
        """
        Save binary response content.
        
        Args:
            response: Response object
            file_path: Optional file path
            
        Returns:
            Path to saved file
        """
        if not file_path:
            # Try to determine extension from content type
            content_type = response.headers.get("Content-Type", "")
            extension = self._get_extension_from_content_type(content_type)
            file_path = self._generate_filename(response, extension=extension)
        
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save binary response to {file_path}: {e}")
            raise ValueError(f"Binary save operation failed: {e}")
    
    def save_multiple_responses(self, responses: List[Response], 
                               directory: Optional[str] = None,
                               format_type: str = "full") -> List[str]:
        """
        Save multiple responses to files.
        
        Args:
            responses: List of Response objects
            directory: Directory to save files (uses default if None)
            format_type: Save format for all responses
            
        Returns:
            List of saved file paths
        """
        if directory:
            save_dir = Path(directory)
        else:
            save_dir = self.default_directory / f"responses_{int(time.time())}"
        
        save_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        
        for i, response in enumerate(responses):
            try:
                filename = f"response_{i+1:03d}_{response.method.lower()}_{response.status_code}.txt"
                file_path = save_dir / filename
                
                saved_path = self.save_response(response, str(file_path), format_type)
                saved_files.append(saved_path)
                
            except Exception as e:
                logger.error(f"Failed to save response {i+1}: {e}")
                continue
        
        return saved_files
    
    def save_response_summary(self, responses: List[Response], 
                             file_path: Optional[str] = None) -> str:
        """
        Save summary of multiple responses.
        
        Args:
            responses: List of Response objects
            file_path: Optional file path
            
        Returns:
            Path to saved summary file
        """
        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = self.default_directory / f"response_summary_{timestamp}.txt"
        
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("Response Summary Report\n")
                f.write("=" * 50 + "\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write(f"Total Responses: {len(responses)}\n\n")
                
                # Summary statistics
                status_counts = {}
                total_time = 0
                total_size = 0
                
                for response in responses:
                    status_counts[response.status_code] = status_counts.get(response.status_code, 0) + 1
                    total_time += response.elapsed_time
                    total_size += response.size_bytes
                
                f.write("Status Code Distribution:\n")
                for status, count in sorted(status_counts.items()):
                    f.write(f"  {status}: {count} responses\n")
                
                f.write(f"\nTotal Response Time: {total_time:.3f}s\n")
                f.write(f"Average Response Time: {total_time/len(responses):.3f}s\n")
                f.write(f"Total Data Size: {total_size} bytes\n")
                f.write(f"Average Response Size: {total_size//len(responses)} bytes\n\n")
                
                # Individual response details
                f.write("Individual Responses:\n")
                f.write("-" * 50 + "\n")
                
                for i, response in enumerate(responses, 1):
                    f.write(f"{i}. {response.method} {response.url}\n")
                    f.write(f"   Status: {response.status_code}\n")
                    f.write(f"   Time: {response.elapsed_time:.3f}s\n")
                    f.write(f"   Size: {response.size_bytes} bytes\n")
                    f.write(f"   Content-Type: {response.headers.get('Content-Type', 'unknown')}\n\n")
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save response summary to {file_path}: {e}")
            raise ValueError(f"Summary save operation failed: {e}")
    
    def _save_full_response(self, response: Response, file_path: Path, 
                           include_metadata: bool) -> None:
        """Save complete response with headers and body."""
        with open(file_path, 'w', encoding='utf-8') as f:
            # Request information
            f.write("REQUEST\n")
            f.write("=" * 50 + "\n")
            f.write(f"{response.method} {response.url}\n\n")
            
            if response.request_headers:
                f.write("Request Headers:\n")
                for key, value in response.request_headers.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")
            
            if response.request_body:
                f.write("Request Body:\n")
                f.write(response.request_body)
                f.write("\n\n")
            
            # Response information
            f.write("RESPONSE\n")
            f.write("=" * 50 + "\n")
            f.write(f"Status Code: {response.status_code}\n")
            
            if include_metadata:
                f.write(f"Response Time: {response.elapsed_time:.3f}s\n")
                f.write(f"Content Size: {response.size_bytes} bytes\n")
                f.write(f"Saved At: {datetime.now().isoformat()}\n")
            
            f.write("\n")
            
            if response.headers:
                f.write("Response Headers:\n")
                for key, value in response.headers.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")
            
            f.write("Response Body:\n")
            f.write(response.text)
    
    def _save_body_only(self, response: Response, file_path: Path) -> None:
        """Save only response body."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
    
    def _save_headers_only(self, response: Response, file_path: Path) -> None:
        """Save only response headers."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"Status Code: {response.status_code}\n")
            f.write(f"Response Time: {response.elapsed_time:.3f}s\n\n")
            
            for key, value in response.headers.items():
                f.write(f"{key}: {value}\n")
    
    def _save_metadata_only(self, response: Response, file_path: Path) -> None:
        """Save only response metadata."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("Response Metadata\n")
            f.write("=" * 20 + "\n")
            f.write(f"URL: {response.url}\n")
            f.write(f"Method: {response.method}\n")
            f.write(f"Status Code: {response.status_code}\n")
            f.write(f"Response Time: {response.elapsed_time:.3f}s\n")
            f.write(f"Content Size: {response.size_bytes} bytes\n")
            f.write(f"Content Type: {response.headers.get('Content-Type', 'unknown')}\n")
            f.write(f"Saved At: {datetime.now().isoformat()}\n")
    
    def _generate_filename(self, response: Response, extension: str = ".txt") -> str:
        """Generate automatic filename for response."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Clean URL for filename
        url_part = response.url.replace("://", "_").replace("/", "_").replace("?", "_")
        if len(url_part) > 50:
            url_part = url_part[:50]
        
        filename = f"response_{timestamp}_{response.method.lower()}_{response.status_code}_{url_part}{extension}"
        
        return str(self.default_directory / filename)
    
    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Get file extension from content type."""
        content_type = content_type.lower()
        
        if "json" in content_type:
            return ".json"
        elif "xml" in content_type:
            return ".xml"
        elif "html" in content_type:
            return ".html"
        elif "css" in content_type:
            return ".css"
        elif "javascript" in content_type:
            return ".js"
        elif "image/png" in content_type:
            return ".png"
        elif "image/jpeg" in content_type:
            return ".jpg"
        elif "image/gif" in content_type:
            return ".gif"
        elif "application/pdf" in content_type:
            return ".pdf"
        else:
            return ".bin"


class ResponseExporter:
    """Export responses to various formats for analysis."""
    
    @staticmethod
    def export_to_har(responses: List[Response], file_path: str) -> bool:
        """
        Export responses to HAR (HTTP Archive) format.
        
        Args:
            responses: List of Response objects
            file_path: Path to save HAR file
            
        Returns:
            True if successfully exported
        """
        try:
            har_data = {
                "log": {
                    "version": "1.2",
                    "creator": {
                        "name": "ReqSmith API Tester",
                        "version": "1.0"
                    },
                    "entries": []
                }
            }
            
            for response in responses:
                entry = {
                    "startedDateTime": datetime.now().isoformat(),
                    "time": response.elapsed_time * 1000,  # HAR uses milliseconds
                    "request": {
                        "method": response.method,
                        "url": response.url,
                        "headers": [{"name": k, "value": v} for k, v in response.request_headers.items()],
                        "postData": {
                            "mimeType": response.request_headers.get("Content-Type", "text/plain"),
                            "text": response.request_body
                        } if response.request_body else {}
                    },
                    "response": {
                        "status": response.status_code,
                        "statusText": "OK" if response.is_success() else "Error",
                        "headers": [{"name": k, "value": v} for k, v in response.headers.items()],
                        "content": {
                            "size": response.size_bytes,
                            "mimeType": response.headers.get("Content-Type", "text/plain"),
                            "text": response.text
                        }
                    }
                }
                
                har_data["log"]["entries"].append(entry)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(har_data, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to export HAR to {file_path}: {e}")
            return False
    
    @staticmethod
    def export_to_csv(responses: List[Response], file_path: str) -> bool:
        """
        Export response summary to CSV.
        
        Args:
            responses: List of Response objects
            file_path: Path to save CSV file
            
        Returns:
            True if successfully exported
        """
        try:
            import csv
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    "Method", "URL", "Status Code", "Response Time (s)", 
                    "Size (bytes)", "Content Type"
                ])
                
                # Write data
                for response in responses:
                    writer.writerow([
                        response.method,
                        response.url,
                        response.status_code,
                        f"{response.elapsed_time:.3f}",
                        response.size_bytes,
                        response.headers.get("Content-Type", "unknown")
                    ])
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to export CSV to {file_path}: {e}")
            return False