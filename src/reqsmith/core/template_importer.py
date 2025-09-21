"""
Template import/export functionality with support for JSON and YAML formats.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
import logging

from ..storage import RequestTemplate
from .template_manager import TemplateManager


logger = logging.getLogger(__name__)


class TemplateImporter:
    """Handles importing templates from various formats."""
    
    def __init__(self, template_manager: TemplateManager):
        """
        Initialize template importer.
        
        Args:
            template_manager: TemplateManager instance
        """
        self.template_manager = template_manager
    
    def import_from_file(self, file_path: str, 
                        format_type: Optional[str] = None,
                        overwrite: bool = False) -> Tuple[int, int, List[str]]:
        """
        Import templates from file.
        
        Args:
            file_path: Path to import file
            format_type: File format (json, yaml, postman, insomnia) - auto-detected if None
            overwrite: Whether to overwrite existing templates
            
        Returns:
            Tuple of (imported_count, skipped_count, error_messages)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Import file not found: {file_path}")
        
        # Auto-detect format if not specified
        if not format_type:
            format_type = self._detect_format(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if format_type == 'json':
                return self._import_from_json(content, overwrite)
            elif format_type == 'yaml':
                return self._import_from_yaml(content, overwrite)
            elif format_type == 'postman':
                return self._import_from_postman(content, overwrite)
            elif format_type == 'insomnia':
                return self._import_from_insomnia(content, overwrite)
            else:
                raise ValueError(f"Unsupported format: {format_type}")
                
        except Exception as e:
            logger.error(f"Failed to import from {file_path}: {e}")
            raise ValueError(f"Import failed: {e}")
    
    def import_from_json(self, json_data: Union[str, Dict], 
                        overwrite: bool = False) -> Tuple[int, int, List[str]]:
        """
        Import templates from JSON data.
        
        Args:
            json_data: JSON string or dictionary
            overwrite: Whether to overwrite existing templates
            
        Returns:
            Tuple of (imported_count, skipped_count, error_messages)
        """
        if isinstance(json_data, str):
            return self._import_from_json(json_data, overwrite)
        else:
            json_str = json.dumps(json_data)
            return self._import_from_json(json_str, overwrite)
    
    def import_from_yaml(self, yaml_data: str, 
                        overwrite: bool = False) -> Tuple[int, int, List[str]]:
        """
        Import templates from YAML data.
        
        Args:
            yaml_data: YAML string
            overwrite: Whether to overwrite existing templates
            
        Returns:
            Tuple of (imported_count, skipped_count, error_messages)
        """
        return self._import_from_yaml(yaml_data, overwrite)
    
    def _import_from_json(self, json_content: str, 
                         overwrite: bool) -> Tuple[int, int, List[str]]:
        """Import templates from JSON content."""
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        
        return self._import_templates_data(data, overwrite)
    
    def _import_from_yaml(self, yaml_content: str, 
                         overwrite: bool) -> Tuple[int, int, List[str]]:
        """Import templates from YAML content."""
        try:
            import yaml
            data = yaml.safe_load(yaml_content)
        except ImportError:
            raise ValueError("PyYAML is required for YAML import. Install with: pip install pyyaml")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
        
        return self._import_templates_data(data, overwrite)
    
    def _import_from_postman(self, postman_content: str, 
                            overwrite: bool) -> Tuple[int, int, List[str]]:
        """Import templates from Postman collection."""
        try:
            collection = json.loads(postman_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid Postman collection JSON: {e}")
        
        templates = self._convert_postman_to_templates(collection)
        return self._import_template_objects(templates, overwrite)
    
    def _import_from_insomnia(self, insomnia_content: str, 
                             overwrite: bool) -> Tuple[int, int, List[str]]:
        """Import templates from Insomnia export."""
        try:
            data = json.loads(insomnia_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid Insomnia export JSON: {e}")
        
        templates = self._convert_insomnia_to_templates(data)
        return self._import_template_objects(templates, overwrite)
    
    def _import_templates_data(self, data: Dict[str, Any], 
                              overwrite: bool) -> Tuple[int, int, List[str]]:
        """Import templates from parsed data."""
        if not isinstance(data, dict):
            raise ValueError("Import data must be a dictionary")
        
        # Handle different data structures
        if 'templates' in data:
            templates_data = data['templates']
        elif isinstance(data, list):
            templates_data = data
        else:
            # Assume the entire data is templates
            templates_data = data
        
        if not isinstance(templates_data, (list, dict)):
            raise ValueError("Templates data must be a list or dictionary")
        
        # Convert to list of template dictionaries
        if isinstance(templates_data, dict):
            template_list = []
            for name, template_data in templates_data.items():
                if isinstance(template_data, dict):
                    template_data['name'] = name
                    template_list.append(template_data)
            templates_data = template_list
        
        # Convert to RequestTemplate objects
        templates = []
        for template_data in templates_data:
            try:
                template = self._dict_to_template(template_data)
                templates.append(template)
            except Exception as e:
                logger.warning(f"Failed to parse template: {e}")
                continue
        
        return self._import_template_objects(templates, overwrite)
    
    def _import_template_objects(self, templates: List[RequestTemplate], 
                                overwrite: bool) -> Tuple[int, int, List[str]]:
        """Import RequestTemplate objects."""
        imported_count = 0
        skipped_count = 0
        errors = []
        
        for template in templates:
            try:
                # Check if template exists
                if self.template_manager.template_exists(template.name):
                    if overwrite:
                        # Update existing template
                        success = self.template_manager.update_template(
                            template.name,
                            method=template.method,
                            url=template.url,
                            headers=template.headers,
                            body=template.body,
                            params=template.params,
                            description=template.description,
                            tags=template.tags
                        )
                        if success:
                            imported_count += 1
                        else:
                            errors.append(f"Failed to update template: {template.name}")
                    else:
                        skipped_count += 1
                        logger.info(f"Skipped existing template: {template.name}")
                else:
                    # Create new template
                    success = self.template_manager.save_template(
                        template.name,
                        template.method,
                        template.url,
                        template.headers,
                        template.body,
                        template.params,
                        template.description,
                        template.tags
                    )
                    if success:
                        imported_count += 1
                    else:
                        errors.append(f"Failed to save template: {template.name}")
                        
            except Exception as e:
                errors.append(f"Error importing template {template.name}: {e}")
                logger.error(f"Error importing template {template.name}: {e}")
        
        return imported_count, skipped_count, errors
    
    def _dict_to_template(self, data: Dict[str, Any]) -> RequestTemplate:
        """Convert dictionary to RequestTemplate object."""
        # Required fields
        name = data.get('name', '')
        method = data.get('method', 'GET')
        url = data.get('url', '')
        
        if not name:
            raise ValueError("Template name is required")
        
        # Optional fields with defaults
        headers = data.get('headers', {})
        body = data.get('body', '')
        params = data.get('params', {})
        description = data.get('description', '')
        tags = data.get('tags', [])
        
        # Ensure tags is a list
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        return RequestTemplate(
            name=name,
            method=method.upper(),
            url=url,
            headers=headers,
            body=body,
            params=params,
            description=description,
            tags=tags
        )
    
    def _convert_postman_to_templates(self, collection: Dict[str, Any]) -> List[RequestTemplate]:
        """Convert Postman collection to RequestTemplate objects."""
        templates = []
        
        def process_item(item: Dict[str, Any], folder_name: str = ""):
            if 'request' in item:
                # This is a request item
                request = item['request']
                name = item.get('name', 'Unnamed Request')
                
                if folder_name:
                    name = f"{folder_name}/{name}"
                
                # Extract request details
                method = request.get('method', 'GET')
                
                # Handle URL
                url_data = request.get('url', {})
                if isinstance(url_data, str):
                    url = url_data
                else:
                    raw_url = url_data.get('raw', '')
                    url = raw_url
                
                # Extract headers
                headers = {}
                for header in request.get('header', []):
                    if not header.get('disabled', False):
                        headers[header.get('key', '')] = header.get('value', '')
                
                # Extract body
                body = ""
                body_data = request.get('body', {})
                if body_data.get('mode') == 'raw':
                    body = body_data.get('raw', '')
                
                # Create template
                template = RequestTemplate(
                    name=name,
                    method=method,
                    url=url,
                    headers=headers,
                    body=body,
                    description=item.get('description', ''),
                    tags=['postman', folder_name] if folder_name else ['postman']
                )
                templates.append(template)
            
            elif 'item' in item:
                # This is a folder
                folder_name = item.get('name', 'Folder')
                for sub_item in item['item']:
                    process_item(sub_item, folder_name)
        
        # Process collection items
        for item in collection.get('item', []):
            process_item(item)
        
        return templates
    
    def _convert_insomnia_to_templates(self, data: Dict[str, Any]) -> List[RequestTemplate]:
        """Convert Insomnia export to RequestTemplate objects."""
        templates = []
        
        resources = data.get('resources', [])
        
        for resource in resources:
            if resource.get('_type') == 'request':
                name = resource.get('name', 'Unnamed Request')
                method = resource.get('method', 'GET')
                url = resource.get('url', '')
                
                # Extract headers
                headers = {}
                for header in resource.get('headers', []):
                    if not header.get('disabled', False):
                        headers[header.get('name', '')] = header.get('value', '')
                
                # Extract body
                body = resource.get('body', {}).get('text', '')
                
                template = RequestTemplate(
                    name=name,
                    method=method,
                    url=url,
                    headers=headers,
                    body=body,
                    description=resource.get('description', ''),
                    tags=['insomnia']
                )
                templates.append(template)
        
        return templates
    
    def _detect_format(self, file_path: str) -> str:
        """Detect file format from extension and content."""
        file_path = file_path.lower()
        
        if file_path.endswith('.json'):
            # Check if it's a Postman collection
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'info' in data and 'schema' in data.get('info', {}):
                        if 'postman' in data['info']['schema']:
                            return 'postman'
                    elif 'resources' in data and '_type' in str(data):
                        return 'insomnia'
            except:
                pass
            
            return 'json'
        elif file_path.endswith(('.yaml', '.yml')):
            return 'yaml'
        else:
            return 'json'  # Default to JSON


class TemplateExporter:
    """Handles exporting templates to various formats."""
    
    def __init__(self, template_manager: TemplateManager):
        """
        Initialize template exporter.
        
        Args:
            template_manager: TemplateManager instance
        """
        self.template_manager = template_manager
    
    def export_to_file(self, file_path: str, 
                      template_names: Optional[List[str]] = None,
                      format_type: Optional[str] = None,
                      include_metadata: bool = True) -> bool:
        """
        Export templates to file.
        
        Args:
            file_path: Path to export file
            template_names: List of template names to export (all if None)
            format_type: Export format (json, yaml) - auto-detected if None
            include_metadata: Whether to include metadata
            
        Returns:
            True if export successful
        """
        # Auto-detect format if not specified
        if not format_type:
            format_type = self._detect_export_format(file_path)
        
        # Get templates to export
        if template_names is None:
            template_names = self.template_manager.list_templates()
        
        templates = []
        for name in template_names:
            template = self.template_manager.load_template(name)
            if template:
                templates.append(template)
        
        if not templates:
            raise ValueError("No templates to export")
        
        try:
            # Create directory if it doesn't exist
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            if format_type == 'json':
                return self._export_to_json(templates, file_path, include_metadata)
            elif format_type == 'yaml':
                return self._export_to_yaml(templates, file_path, include_metadata)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
                
        except Exception as e:
            logger.error(f"Failed to export to {file_path}: {e}")
            raise ValueError(f"Export failed: {e}")
    
    def export_to_json(self, template_names: Optional[List[str]] = None,
                      include_metadata: bool = True) -> str:
        """
        Export templates to JSON string.
        
        Args:
            template_names: List of template names to export (all if None)
            include_metadata: Whether to include metadata
            
        Returns:
            JSON string
        """
        if template_names is None:
            template_names = self.template_manager.list_templates()
        
        templates = []
        for name in template_names:
            template = self.template_manager.load_template(name)
            if template:
                templates.append(template)
        
        export_data = self._prepare_export_data(templates, include_metadata)
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    def export_to_yaml(self, template_names: Optional[List[str]] = None,
                      include_metadata: bool = True) -> str:
        """
        Export templates to YAML string.
        
        Args:
            template_names: List of template names to export (all if None)
            include_metadata: Whether to include metadata
            
        Returns:
            YAML string
        """
        try:
            import yaml
        except ImportError:
            raise ValueError("PyYAML is required for YAML export. Install with: pip install pyyaml")
        
        if template_names is None:
            template_names = self.template_manager.list_templates()
        
        templates = []
        for name in template_names:
            template = self.template_manager.load_template(name)
            if template:
                templates.append(template)
        
        export_data = self._prepare_export_data(templates, include_metadata)
        return yaml.dump(export_data, default_flow_style=False, allow_unicode=True)
    
    def _export_to_json(self, templates: List[RequestTemplate], 
                       file_path: str, include_metadata: bool) -> bool:
        """Export templates to JSON file."""
        export_data = self._prepare_export_data(templates, include_metadata)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return True
    
    def _export_to_yaml(self, templates: List[RequestTemplate], 
                       file_path: str, include_metadata: bool) -> bool:
        """Export templates to YAML file."""
        try:
            import yaml
        except ImportError:
            raise ValueError("PyYAML is required for YAML export. Install with: pip install pyyaml")
        
        export_data = self._prepare_export_data(templates, include_metadata)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True)
        
        return True
    
    def _prepare_export_data(self, templates: List[RequestTemplate], 
                            include_metadata: bool) -> Dict[str, Any]:
        """Prepare data for export."""
        export_data = {
            'version': '1.0',
            'exported_at': str(datetime.now().isoformat()),
            'templates': []
        }
        
        for template in templates:
            template_data = {
                'name': template.name,
                'method': template.method,
                'url': template.url,
                'headers': template.headers,
                'body': template.body,
                'params': template.params,
                'description': template.description,
                'tags': template.tags
            }
            
            if include_metadata:
                from datetime import datetime
                template_data['metadata'] = {
                    'created_at': template.created_at,
                    'last_used': template.last_used,
                    'usage_count': template.usage_count,
                    'formatted_created': datetime.fromtimestamp(template.created_at).strftime("%Y-%m-%d %H:%M:%S"),
                    'formatted_last_used': datetime.fromtimestamp(template.last_used).strftime("%Y-%m-%d %H:%M:%S")
                }
            
            export_data['templates'].append(template_data)
        
        return export_data
    
    def _detect_export_format(self, file_path: str) -> str:
        """Detect export format from file extension."""
        file_path = file_path.lower()
        
        if file_path.endswith(('.yaml', '.yml')):
            return 'yaml'
        else:
            return 'json'  # Default to JSON