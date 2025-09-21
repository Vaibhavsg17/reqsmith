"""
Template manager for saving, loading, and managing request templates.
"""
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from ..storage import (
    HybridStorage, 
    TemplateStorage, 
    RequestTemplate,
    validate_http_method,
    validate_url
)


logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages request templates with CRUD operations and validation."""
    
    def __init__(self, storage: HybridStorage):
        """
        Initialize template manager.
        
        Args:
            storage: HybridStorage instance for persistence
        """
        self.storage = storage
        self.template_storage = TemplateStorage(storage)
    
    def save_template(self, name: str, method: str, url: str,
                     headers: Optional[Dict[str, str]] = None,
                     body: Optional[str] = None,
                     params: Optional[Dict[str, str]] = None,
                     description: str = "",
                     tags: Optional[List[str]] = None) -> bool:
        """
        Save a new request template.
        
        Args:
            name: Template name (must be unique)
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            params: Query parameters
            description: Template description
            tags: Template tags for categorization
            
        Returns:
            True if template was saved successfully
            
        Raises:
            ValueError: If template data is invalid
        """
        # Validate inputs
        if not name or not name.strip():
            raise ValueError("Template name cannot be empty")
        
        name = name.strip()
        
        # Check if template already exists
        if self.template_exists(name):
            raise ValueError(f"Template '{name}' already exists")
        
        # Validate HTTP method
        if not validate_http_method(method):
            raise ValueError(f"Invalid HTTP method: {method}")
        
        # Validate URL
        if not validate_url(url):
            raise ValueError(f"Invalid URL: {url}")
        
        # Create template object
        template = RequestTemplate(
            name=name,
            method=method.upper(),
            url=url,
            headers=headers or {},
            body=body or "",
            params=params or {},
            description=description,
            tags=tags or [],
            created_at=time.time(),
            last_used=time.time(),
            usage_count=0
        )
        
        # Validate template
        if not template.validate():
            raise ValueError("Template validation failed")
        
        # Save template
        success = self.template_storage.save_template(template)
        if success:
            logger.info(f"Template '{name}' saved successfully")
        else:
            logger.error(f"Failed to save template '{name}'")
        
        return success
    
    def load_template(self, name: str) -> Optional[RequestTemplate]:
        """
        Load a template by name.
        
        Args:
            name: Template name
            
        Returns:
            RequestTemplate object or None if not found
        """
        if not name or not name.strip():
            return None
        
        template = self.template_storage.load_template(name.strip())
        if template:
            logger.debug(f"Template '{name}' loaded successfully")
        else:
            logger.debug(f"Template '{name}' not found")
        
        return template
    
    def update_template(self, name: str, **kwargs) -> bool:
        """
        Update an existing template.
        
        Args:
            name: Template name
            **kwargs: Fields to update (method, url, headers, body, params, description, tags)
            
        Returns:
            True if template was updated successfully
            
        Raises:
            ValueError: If template doesn't exist or update data is invalid
        """
        template = self.load_template(name)
        if not template:
            raise ValueError(f"Template '{name}' not found")
        
        # Update fields
        if 'method' in kwargs:
            method = kwargs['method']
            if not validate_http_method(method):
                raise ValueError(f"Invalid HTTP method: {method}")
            template.method = method.upper()
        
        if 'url' in kwargs:
            url = kwargs['url']
            if not validate_url(url):
                raise ValueError(f"Invalid URL: {url}")
            template.url = url
        
        if 'headers' in kwargs:
            template.headers = kwargs['headers'] or {}
        
        if 'body' in kwargs:
            template.body = kwargs['body'] or ""
        
        if 'params' in kwargs:
            template.params = kwargs['params'] or {}
        
        if 'description' in kwargs:
            template.description = kwargs['description'] or ""
        
        if 'tags' in kwargs:
            template.tags = kwargs['tags'] or []
        
        # Update modification time
        template.last_used = time.time()
        
        # Validate updated template
        if not template.validate():
            raise ValueError("Updated template validation failed")
        
        # Save updated template
        success = self.template_storage.save_template(template)
        if success:
            logger.info(f"Template '{name}' updated successfully")
        else:
            logger.error(f"Failed to update template '{name}'")
        
        return success
    
    def delete_template(self, name: str) -> bool:
        """
        Delete a template.
        
        Args:
            name: Template name
            
        Returns:
            True if template was deleted successfully
        """
        if not name or not name.strip():
            return False
        
        name = name.strip()
        
        # Check if template exists
        if not self.template_exists(name):
            logger.warning(f"Template '{name}' not found for deletion")
            return False
        
        success = self.template_storage.delete_template(name)
        if success:
            logger.info(f"Template '{name}' deleted successfully")
        else:
            logger.error(f"Failed to delete template '{name}'")
        
        return success
    
    def list_templates(self, tag_filter: Optional[str] = None,
                      sort_by: str = "name") -> List[str]:
        """
        List all template names.
        
        Args:
            tag_filter: Optional tag to filter by
            sort_by: Sort criteria (name, created_at, last_used, usage_count)
            
        Returns:
            List of template names
        """
        template_names = self.template_storage.list_templates()
        
        if tag_filter:
            # Filter by tag
            filtered_names = []
            for name in template_names:
                template = self.load_template(name)
                if template and tag_filter in template.tags:
                    filtered_names.append(name)
            template_names = filtered_names
        
        # Sort templates
        if sort_by != "name":
            template_data = []
            for name in template_names:
                template = self.load_template(name)
                if template:
                    template_data.append((name, template))
            
            if sort_by == "created_at":
                template_data.sort(key=lambda x: x[1].created_at, reverse=True)
            elif sort_by == "last_used":
                template_data.sort(key=lambda x: x[1].last_used, reverse=True)
            elif sort_by == "usage_count":
                template_data.sort(key=lambda x: x[1].usage_count, reverse=True)
            
            template_names = [name for name, _ in template_data]
        else:
            template_names.sort()
        
        return template_names
    
    def get_template_metadata(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metadata about templates.
        
        Args:
            name: Optional specific template name
            
        Returns:
            Dictionary with template metadata
        """
        if name:
            # Get metadata for specific template
            template = self.load_template(name)
            if not template:
                return {}
            
            return {
                'name': template.name,
                'method': template.method,
                'url': template.url,
                'description': template.description,
                'tags': template.tags,
                'created_at': template.created_at,
                'last_used': template.last_used,
                'usage_count': template.usage_count,
                'formatted_created': datetime.fromtimestamp(template.created_at).strftime("%Y-%m-%d %H:%M:%S"),
                'formatted_last_used': datetime.fromtimestamp(template.last_used).strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            # Get metadata for all templates
            return self.template_storage.get_template_metadata()
    
    def template_exists(self, name: str) -> bool:
        """
        Check if a template exists.
        
        Args:
            name: Template name
            
        Returns:
            True if template exists
        """
        return self.load_template(name) is not None
    
    def search_templates(self, query: str, search_fields: Optional[List[str]] = None) -> List[str]:
        """
        Search templates by query string.
        
        Args:
            query: Search query
            search_fields: Fields to search in (name, description, url, tags)
            
        Returns:
            List of matching template names
        """
        if not query or not query.strip():
            return []
        
        query = query.lower().strip()
        search_fields = search_fields or ['name', 'description', 'url', 'tags']
        
        matching_templates = []
        template_names = self.template_storage.list_templates()
        
        for name in template_names:
            template = self.load_template(name)
            if not template:
                continue
            
            # Search in specified fields
            if 'name' in search_fields and query in template.name.lower():
                matching_templates.append(name)
                continue
            
            if 'description' in search_fields and query in template.description.lower():
                matching_templates.append(name)
                continue
            
            if 'url' in search_fields and query in template.url.lower():
                matching_templates.append(name)
                continue
            
            if 'tags' in search_fields:
                for tag in template.tags:
                    if query in tag.lower():
                        matching_templates.append(name)
                        break
        
        return matching_templates
    
    def get_templates_by_tag(self, tag: str) -> List[str]:
        """
        Get all templates with a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of template names with the tag
        """
        return self.list_templates(tag_filter=tag)
    
    def get_all_tags(self) -> List[str]:
        """
        Get all unique tags used in templates.
        
        Returns:
            List of unique tags
        """
        all_tags = set()
        template_names = self.template_storage.list_templates()
        
        for name in template_names:
            template = self.load_template(name)
            if template:
                all_tags.update(template.tags)
        
        return sorted(list(all_tags))
    
    def update_template_usage(self, name: str) -> bool:
        """
        Update template usage statistics.
        
        Args:
            name: Template name
            
        Returns:
            True if usage was updated successfully
        """
        template = self.load_template(name)
        if not template:
            return False
        
        template.update_usage()
        
        success = self.template_storage.save_template(template)
        if success:
            logger.debug(f"Updated usage for template '{name}'")
        
        return success
    
    def get_template_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about all templates.
        
        Returns:
            Dictionary with template statistics
        """
        template_names = self.template_storage.list_templates()
        
        if not template_names:
            return {
                'total_templates': 0,
                'total_usage': 0,
                'most_used': None,
                'recently_created': None,
                'methods_distribution': {},
                'tags_distribution': {}
            }
        
        templates = []
        total_usage = 0
        methods = {}
        tags = {}
        
        for name in template_names:
            template = self.load_template(name)
            if template:
                templates.append(template)
                total_usage += template.usage_count
                
                # Count methods
                method = template.method
                methods[method] = methods.get(method, 0) + 1
                
                # Count tags
                for tag in template.tags:
                    tags[tag] = tags.get(tag, 0) + 1
        
        # Find most used template
        most_used = max(templates, key=lambda t: t.usage_count) if templates else None
        
        # Find most recently created template
        recently_created = max(templates, key=lambda t: t.created_at) if templates else None
        
        return {
            'total_templates': len(templates),
            'total_usage': total_usage,
            'average_usage': total_usage / len(templates) if templates else 0,
            'most_used': most_used.name if most_used else None,
            'most_used_count': most_used.usage_count if most_used else 0,
            'recently_created': recently_created.name if recently_created else None,
            'methods_distribution': methods,
            'tags_distribution': tags
        }
    
    def validate_template_data(self, method: str, url: str, 
                              headers: Optional[Dict[str, str]] = None,
                              body: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate template data without saving.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate method
        if not validate_http_method(method):
            return False, f"Invalid HTTP method: {method}"
        
        # Validate URL
        if not validate_url(url):
            return False, f"Invalid URL: {url}"
        
        # Validate headers
        if headers:
            for key, value in headers.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    return False, f"Invalid header: {key}={value}"
        
        # Validate JSON body if content-type is JSON
        if body and headers and headers.get('Content-Type', '').startswith('application/json'):
            try:
                import json
                json.loads(body)
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON body: {e}"
        
        return True, None