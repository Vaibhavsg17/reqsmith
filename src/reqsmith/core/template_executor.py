"""
Template executor with parameter override and variable substitution support.
"""
import re
from typing import Dict, Any, Optional, List, Tuple
import logging

from ..storage import RequestTemplate, Environment
from .template_manager import TemplateManager


logger = logging.getLogger(__name__)


class TemplateExecutor:
    """Executes templates with parameter overrides and variable substitution."""
    
    def __init__(self, template_manager: TemplateManager):
        """
        Initialize template executor.
        
        Args:
            template_manager: TemplateManager instance
        """
        self.template_manager = template_manager
    
    def execute_template(self, template_name: str,
                        environment: Optional[Environment] = None,
                        overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute template with optional parameter overrides and variable substitution.
        
        Args:
            template_name: Name of template to execute
            environment: Environment for variable substitution
            overrides: Parameter overrides (method, url, headers, body, params)
            
        Returns:
            Dictionary with resolved request parameters
            
        Raises:
            ValueError: If template not found or execution fails
        """
        # Load template
        template = self.template_manager.load_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Update usage statistics
        self.template_manager.update_template_usage(template_name)
        
        # Start with template values
        request_data = {
            'method': template.method,
            'url': template.url,
            'headers': template.headers.copy(),
            'body': template.body,
            'params': template.params.copy()
        }
        
        # Apply overrides
        if overrides:
            request_data = self._apply_overrides(request_data, overrides)
        
        # Apply variable substitution
        if environment:
            request_data = self._apply_variable_substitution(request_data, environment)
        
        # Validate final request data
        self._validate_request_data(request_data)
        
        return request_data
    
    def preview_template_execution(self, template_name: str,
                                  environment: Optional[Environment] = None,
                                  overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Preview template execution without updating usage statistics.
        
        Args:
            template_name: Name of template to preview
            environment: Environment for variable substitution
            overrides: Parameter overrides
            
        Returns:
            Dictionary with resolved request parameters
        """
        # Load template
        template = self.template_manager.load_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Start with template values
        request_data = {
            'method': template.method,
            'url': template.url,
            'headers': template.headers.copy(),
            'body': template.body,
            'params': template.params.copy()
        }
        
        # Apply overrides
        if overrides:
            request_data = self._apply_overrides(request_data, overrides)
        
        # Apply variable substitution
        if environment:
            request_data = self._apply_variable_substitution(request_data, environment)
        
        return request_data
    
    def _apply_overrides(self, request_data: Dict[str, Any], 
                        overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply parameter overrides to request data.
        
        Args:
            request_data: Original request data
            overrides: Override parameters
            
        Returns:
            Updated request data
        """
        # Override method
        if 'method' in overrides:
            method = overrides['method']
            if isinstance(method, str) and method.strip():
                request_data['method'] = method.upper().strip()
        
        # Override URL
        if 'url' in overrides:
            url = overrides['url']
            if isinstance(url, str) and url.strip():
                request_data['url'] = url.strip()
        
        # Override/merge headers
        if 'headers' in overrides:
            headers = overrides['headers']
            if isinstance(headers, dict):
                # Merge with existing headers
                request_data['headers'].update(headers)
        
        # Override body
        if 'body' in overrides:
            body = overrides['body']
            if isinstance(body, str):
                request_data['body'] = body
        
        # Override/merge params
        if 'params' in overrides:
            params = overrides['params']
            if isinstance(params, dict):
                # Merge with existing params
                request_data['params'].update(params)
        
        return request_data
    
    def _apply_variable_substitution(self, request_data: Dict[str, Any],
                                   environment: Environment) -> Dict[str, Any]:
        """
        Apply variable substitution to request data.
        
        Args:
            request_data: Request data with variables
            environment: Environment with variable values
            
        Returns:
            Request data with variables substituted
        """
        # Substitute in URL
        request_data['url'] = self._substitute_variables(request_data['url'], environment)
        
        # Substitute in headers
        substituted_headers = {}
        for key, value in request_data['headers'].items():
            substituted_key = self._substitute_variables(key, environment)
            substituted_value = self._substitute_variables(value, environment)
            substituted_headers[substituted_key] = substituted_value
        request_data['headers'] = substituted_headers
        
        # Substitute in body
        request_data['body'] = self._substitute_variables(request_data['body'], environment)
        
        # Substitute in params
        substituted_params = {}
        for key, value in request_data['params'].items():
            substituted_key = self._substitute_variables(key, environment)
            substituted_value = self._substitute_variables(value, environment)
            substituted_params[substituted_key] = substituted_value
        request_data['params'] = substituted_params
        
        return request_data
    
    def _substitute_variables(self, text: str, environment: Environment) -> str:
        """
        Substitute variables in text using ${VAR} and {{VAR}} syntax.
        
        Args:
            text: Text with variables
            environment: Environment with variable values
            
        Returns:
            Text with variables substituted
        """
        if not text or not isinstance(text, str):
            return text
        
        # Handle ${VAR} syntax
        def replace_dollar_var(match):
            var_name = match.group(1)
            value = environment.get_variable(var_name)
            if value is not None:
                return value
            else:
                logger.warning(f"Undefined variable: ${{{var_name}}}")
                return match.group(0)  # Return original if not found
        
        # Handle {{VAR}} syntax
        def replace_brace_var(match):
            var_name = match.group(1)
            value = environment.get_variable(var_name)
            if value is not None:
                return value
            else:
                logger.warning(f"Undefined variable: {{{{{var_name}}}}}")
                return match.group(0)  # Return original if not found
        
        # Apply substitutions
        text = re.sub(r'\$\{([^}]+)\}', replace_dollar_var, text)
        text = re.sub(r'\{\{([^}]+)\}\}', replace_brace_var, text)
        
        return text
    
    def _validate_request_data(self, request_data: Dict[str, Any]) -> None:
        """
        Validate final request data.
        
        Args:
            request_data: Request data to validate
            
        Raises:
            ValueError: If request data is invalid
        """
        # Validate method
        method = request_data.get('method', '')
        if not method or not isinstance(method, str):
            raise ValueError("Invalid or missing HTTP method")
        
        # Validate URL
        url = request_data.get('url', '')
        if not url or not isinstance(url, str):
            raise ValueError("Invalid or missing URL")
        
        # Check for unresolved variables
        self._check_unresolved_variables(request_data)
    
    def _check_unresolved_variables(self, request_data: Dict[str, Any]) -> None:
        """
        Check for unresolved variables in request data.
        
        Args:
            request_data: Request data to check
            
        Raises:
            ValueError: If unresolved variables are found
        """
        unresolved_vars = []
        
        # Check URL
        url_vars = self._find_variables(request_data['url'])
        unresolved_vars.extend(url_vars)
        
        # Check headers
        for key, value in request_data['headers'].items():
            unresolved_vars.extend(self._find_variables(key))
            unresolved_vars.extend(self._find_variables(value))
        
        # Check body
        body_vars = self._find_variables(request_data['body'])
        unresolved_vars.extend(body_vars)
        
        # Check params
        for key, value in request_data['params'].items():
            unresolved_vars.extend(self._find_variables(key))
            unresolved_vars.extend(self._find_variables(value))
        
        if unresolved_vars:
            unique_vars = list(set(unresolved_vars))
            raise ValueError(f"Unresolved variables found: {', '.join(unique_vars)}")
    
    def _find_variables(self, text: str) -> List[str]:
        """
        Find variable references in text.
        
        Args:
            text: Text to search
            
        Returns:
            List of variable names found
        """
        if not text or not isinstance(text, str):
            return []
        
        variables = []
        
        # Find ${VAR} patterns
        dollar_vars = re.findall(r'\$\{([^}]+)\}', text)
        variables.extend(dollar_vars)
        
        # Find {{VAR}} patterns
        brace_vars = re.findall(r'\{\{([^}]+)\}\}', text)
        variables.extend(brace_vars)
        
        return variables
    
    def get_template_variables(self, template_name: str) -> List[str]:
        """
        Get all variables used in a template.
        
        Args:
            template_name: Name of template
            
        Returns:
            List of variable names used in template
            
        Raises:
            ValueError: If template not found
        """
        template = self.template_manager.load_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        variables = []
        
        # Check URL
        variables.extend(self._find_variables(template.url))
        
        # Check headers
        for key, value in template.headers.items():
            variables.extend(self._find_variables(key))
            variables.extend(self._find_variables(value))
        
        # Check body
        variables.extend(self._find_variables(template.body))
        
        # Check params
        for key, value in template.params.items():
            variables.extend(self._find_variables(key))
            variables.extend(self._find_variables(value))
        
        # Return unique variables
        return list(set(variables))
    
    def validate_template_with_environment(self, template_name: str,
                                         environment: Environment) -> Tuple[bool, List[str]]:
        """
        Validate that template can be executed with given environment.
        
        Args:
            template_name: Name of template
            environment: Environment to validate against
            
        Returns:
            Tuple of (is_valid, missing_variables)
        """
        try:
            template_vars = self.get_template_variables(template_name)
            missing_vars = []
            
            for var in template_vars:
                if environment.get_variable(var) is None:
                    missing_vars.append(var)
            
            return len(missing_vars) == 0, missing_vars
            
        except ValueError:
            return False, []


class TemplateParameterOverride:
    """Helper class for managing template parameter overrides."""
    
    def __init__(self):
        self.overrides = {}
    
    def set_method(self, method: str) -> 'TemplateParameterOverride':
        """Set method override."""
        self.overrides['method'] = method
        return self
    
    def set_url(self, url: str) -> 'TemplateParameterOverride':
        """Set URL override."""
        self.overrides['url'] = url
        return self
    
    def add_header(self, key: str, value: str) -> 'TemplateParameterOverride':
        """Add header override."""
        if 'headers' not in self.overrides:
            self.overrides['headers'] = {}
        self.overrides['headers'][key] = value
        return self
    
    def set_headers(self, headers: Dict[str, str]) -> 'TemplateParameterOverride':
        """Set all headers override."""
        self.overrides['headers'] = headers
        return self
    
    def set_body(self, body: str) -> 'TemplateParameterOverride':
        """Set body override."""
        self.overrides['body'] = body
        return self
    
    def add_param(self, key: str, value: str) -> 'TemplateParameterOverride':
        """Add query parameter override."""
        if 'params' not in self.overrides:
            self.overrides['params'] = {}
        self.overrides['params'][key] = value
        return self
    
    def set_params(self, params: Dict[str, str]) -> 'TemplateParameterOverride':
        """Set all query parameters override."""
        self.overrides['params'] = params
        return self
    
    def get_overrides(self) -> Dict[str, Any]:
        """Get all overrides as dictionary."""
        return self.overrides.copy()
    
    def clear(self) -> 'TemplateParameterOverride':
        """Clear all overrides."""
        self.overrides.clear()
        return self