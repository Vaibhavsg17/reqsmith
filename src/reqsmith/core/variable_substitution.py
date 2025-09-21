"""
Variable substitution engine with support for multiple syntaxes and advanced features.
"""
import re
import base64
import urllib.parse
from typing import Dict, List, Optional, Any, Tuple, Callable
import logging

from ..storage import Environment
from ..exceptions import ReqSmithError, VariableSubstitutionError


logger = logging.getLogger(__name__)


class VariableSubstitutionEngine:
    """Advanced variable substitution engine with multiple syntax support."""
    
    def __init__(self):
        """Initialize the substitution engine."""
        # Supported variable syntaxes
        self.syntaxes = {
            'dollar_brace': r'\$\{([^}]+)\}',      # ${VAR}
            'double_brace': r'\{\{([^}]+)\}\}',    # {{VAR}}
            'percent': r'%([^%]+)%',               # %VAR%
            'env': r'\$([A-Z_][A-Z0-9_]*)',        # $VAR (environment style)
        }
        
        # Default syntax order (first match wins)
        self.syntax_order = ['dollar_brace', 'double_brace', 'percent', 'env']
        
        # Custom functions for variable processing
        self.functions = {
            'upper': lambda x: x.upper(),
            'lower': lambda x: x.lower(),
            'title': lambda x: x.title(),
            'trim': lambda x: x.strip(),
            'len': lambda x: str(len(x)),
            'reverse': lambda x: x[::-1],
            'urlencode': lambda x: self._url_encode(x),
            'base64': lambda x: self._base64_encode(x),
            'default': lambda x, default='': x if x else default,
            'replace': lambda x, old_new: self._replace_function(x, old_new),
            'substr': lambda x, params: self._substr_function(x, params),
            'split': lambda x, delimiter=',': x.split(delimiter),
            'join': lambda x, delimiter=',': delimiter.join(x) if isinstance(x, list) else x,
            'strip_prefix': lambda x, prefix: x[len(prefix):] if x.startswith(prefix) else x,
            'strip_suffix': lambda x, suffix: x[:-len(suffix)] if x.endswith(suffix) else x,
        }
    
    def substitute_variables(self, text: str, environment: Environment,
                           strict_mode: bool = False,
                           enabled_syntaxes: Optional[List[str]] = None,
                           show_warnings: bool = True) -> str:
        """
        Substitute variables in text using environment values.
        
        Args:
            text: Text containing variables
            environment: Environment with variable values
            strict_mode: If True, raise error for undefined variables
            enabled_syntaxes: List of enabled syntaxes (all if None)
            show_warnings: Whether to log warnings for undefined variables
            
        Returns:
            Text with variables substituted
            
        Raises:
            ValueError: If strict_mode is True and undefined variables found
        """
        if not text or not isinstance(text, str):
            return text or ""
        
        result = text
        undefined_vars = []
        substitution_stats = {}
        
        # Use specified syntaxes or all
        syntaxes_to_use = enabled_syntaxes or self.syntax_order
        
        for syntax_name in syntaxes_to_use:
            if syntax_name not in self.syntaxes:
                continue
            
            pattern = self.syntaxes[syntax_name]
            before_substitution = result
            result, syntax_undefined = self._substitute_with_pattern(
                result, pattern, environment, syntax_name
            )
            
            # Track substitution statistics
            if before_substitution != result:
                substitution_stats[syntax_name] = substitution_stats.get(syntax_name, 0) + 1
            
            undefined_vars.extend(syntax_undefined)
        
        # Log warnings for undefined variables if requested
        if show_warnings and undefined_vars:
            unique_vars = list(set(undefined_vars))
            logger.warning(f"Undefined variables found: {', '.join(unique_vars)}")
            logger.info(f"Available variables: {list(environment.variables.keys())}")
        
        if strict_mode and undefined_vars:
            unique_vars = list(set(undefined_vars))
            available_vars = list(environment.variables.keys())
            error_msg = f"Undefined variables: {', '.join(unique_vars)}"
            if available_vars:
                error_msg += f"\nAvailable variables: {', '.join(available_vars)}"
            raise ValueError(error_msg)
        
        # Log substitution statistics in debug mode
        if substitution_stats:
            logger.debug(f"Variable substitution statistics: {substitution_stats}")
        
        return result
    
    def substitute_with_defaults(self, text: str, environment: Environment,
                                defaults: Optional[Dict[str, str]] = None) -> str:
        """
        Substitute variables with fallback to default values.
        
        Args:
            text: Text containing variables
            environment: Environment with variable values
            defaults: Default values for variables
            
        Returns:
            Text with variables substituted
        """
        if not text or not isinstance(text, str):
            return text or ""
        
        defaults = defaults or {}
        result = text
        
        for syntax_name in self.syntax_order:
            pattern = self.syntaxes[syntax_name]
            
            def replace_func(match):
                var_expr = match.group(1)
                var_name, func_chain = self._parse_variable_expression(var_expr)
                
                # Get value from environment or defaults
                value = environment.get_variable(var_name)
                if value is None:
                    value = defaults.get(var_name, '')
                
                # Apply function chain
                if func_chain and value:
                    value = self._apply_function_chain(value, func_chain)
                
                return value
            
            result = re.sub(pattern, replace_func, result)
        
        return result
    
    def substitute_with_context(self, text: str, context: Dict[str, Any],
                               environment: Optional[Environment] = None) -> str:
        """
        Substitute variables using a context dictionary and optional environment.
        
        Args:
            text: Text containing variables
            context: Context dictionary with variable values
            environment: Optional environment for additional variables
            
        Returns:
            Text with variables substituted
        """
        if not text or not isinstance(text, str):
            return text or ""
        
        result = text
        
        for syntax_name in self.syntax_order:
            pattern = self.syntaxes[syntax_name]
            
            def replace_func(match):
                var_expr = match.group(1)
                var_name, func_chain = self._parse_variable_expression(var_expr)
                
                # Get value from context first, then environment
                value = None
                if var_name in context:
                    value = str(context[var_name])
                elif environment:
                    value = environment.get_variable(var_name)
                
                if value is None:
                    logger.warning(f"Undefined variable: {var_name}")
                    return match.group(0)  # Return original if not found
                
                # Apply function chain
                if func_chain and value:
                    value = self._apply_function_chain(value, func_chain)
                
                return value
            
            result = re.sub(pattern, replace_func, result)
        
        return result
    
    def find_variables(self, text: str, 
                      enabled_syntaxes: Optional[List[str]] = None) -> List[str]:
        """
        Find all variable references in text.
        
        Args:
            text: Text to search
            enabled_syntaxes: List of enabled syntaxes (all if None)
            
        Returns:
            List of unique variable names found
        """
        if not text or not isinstance(text, str):
            return []
        
        variables = set()
        syntaxes_to_use = enabled_syntaxes or self.syntax_order
        
        for syntax_name in syntaxes_to_use:
            if syntax_name not in self.syntaxes:
                continue
            
            pattern = self.syntaxes[syntax_name]
            matches = re.findall(pattern, text)
            
            for match in matches:
                var_name, _ = self._parse_variable_expression(match)
                variables.add(var_name)
        
        return sorted(list(variables))
    
    def validate_variables(self, text: str, environment: Environment,
                          enabled_syntaxes: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
        """
        Validate that all variables in text are defined in environment.
        
        Args:
            text: Text to validate
            environment: Environment to check against
            enabled_syntaxes: List of enabled syntaxes (all if None)
            
        Returns:
            Tuple of (all_defined, undefined_variables)
        """
        variables = self.find_variables(text, enabled_syntaxes)
        undefined = []
        
        for var in variables:
            if environment.get_variable(var) is None:
                undefined.append(var)
        
        return len(undefined) == 0, undefined
    
    def preview_substitution(self, text: str, environment: Environment,
                           enabled_syntaxes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Preview variable substitution without actually performing it.
        
        Args:
            text: Text to preview
            environment: Environment with variable values
            enabled_syntaxes: List of enabled syntaxes (all if None)
            
        Returns:
            Dictionary with preview information
        """
        variables = self.find_variables(text, enabled_syntaxes)
        
        preview_info = {
            'original_text': text,
            'variables_found': variables,
            'variable_values': {},
            'undefined_variables': [],
            'substituted_text': ''
        }
        
        # Get variable values
        for var in variables:
            value = environment.get_variable(var)
            if value is not None:
                preview_info['variable_values'][var] = value
            else:
                preview_info['undefined_variables'].append(var)
        
        # Perform substitution
        try:
            preview_info['substituted_text'] = self.substitute_variables(
                text, environment, strict_mode=False, enabled_syntaxes=enabled_syntaxes
            )
        except Exception as e:
            preview_info['error'] = str(e)
        
        return preview_info
    
    def _substitute_with_pattern(self, text: str, pattern: str, 
                                environment: Environment, 
                                syntax_name: str) -> Tuple[str, List[str]]:
        """Substitute variables using a specific pattern."""
        undefined_vars = []
        
        def replace_func(match):
            var_expr = match.group(1)
            var_name, func_chain = self._parse_variable_expression(var_expr)
            
            value = environment.get_variable(var_name)
            if value is None:
                undefined_vars.append(var_name)
                logger.warning(f"Undefined variable: {var_name} (syntax: {syntax_name})")
                return match.group(0)  # Return original if not found
            
            # Apply function chain
            if func_chain and value:
                try:
                    value = self._apply_function_chain(value, func_chain)
                except Exception as e:
                    logger.warning(f"Function chain error for {var_name}: {e}")
                    return value  # Return original value if function fails
            
            return value
        
        result = re.sub(pattern, replace_func, text)
        return result, undefined_vars
    
    def _parse_variable_expression(self, expr: str) -> Tuple[str, List[str]]:
        """
        Parse variable expression to extract name and function chain.
        
        Examples:
        - "VAR" -> ("VAR", [])
        - "VAR|upper" -> ("VAR", ["upper"])
        - "VAR|upper|trim" -> ("VAR", ["upper", "trim"])
        - "VAR|default:fallback" -> ("VAR", ["default:fallback"])
        
        Args:
            expr: Variable expression
            
        Returns:
            Tuple of (variable_name, function_chain)
        """
        if '|' not in expr:
            return expr.strip(), []
        
        parts = expr.split('|')
        var_name = parts[0].strip()
        func_chain = [part.strip() for part in parts[1:] if part.strip()]
        
        return var_name, func_chain
    
    def _apply_function_chain(self, value: str, func_chain: List[str]) -> str:
        """Apply a chain of functions to a value."""
        result = value
        
        for func_expr in func_chain:
            if ':' in func_expr:
                # Function with arguments
                func_name, args_str = func_expr.split(':', 1)
                args = [arg.strip() for arg in args_str.split(',')]
            else:
                # Function without arguments
                func_name = func_expr
                args = []
            
            if func_name in self.functions:
                try:
                    if args:
                        result = self.functions[func_name](result, *args)
                    else:
                        result = self.functions[func_name](result)
                except Exception as e:
                    logger.warning(f"Function {func_name} failed: {e}")
                    break  # Stop processing chain on error
            else:
                logger.warning(f"Unknown function: {func_name}")
                break
        
        return result
    
    def add_custom_function(self, name: str, func: Callable) -> None:
        """
        Add a custom function for variable processing.
        
        Args:
            name: Function name
            func: Function that takes a string and returns a string
        """
        self.functions[name] = func
    
    def remove_custom_function(self, name: str) -> bool:
        """
        Remove a custom function.
        
        Args:
            name: Function name
            
        Returns:
            True if function was removed
        """
        if name in self.functions:
            del self.functions[name]
            return True
        return False
    
    def get_available_functions(self) -> List[str]:
        """Get list of available function names."""
        return list(self.functions.keys())


class NestedVariableResolver:
    """Resolves nested variable references with circular dependency detection."""
    
    def __init__(self, substitution_engine: VariableSubstitutionEngine):
        """
        Initialize nested variable resolver.
        
        Args:
            substitution_engine: VariableSubstitutionEngine instance
        """
        self.engine = substitution_engine
        self.max_depth = 10  # Maximum nesting depth
    
    def resolve_nested_variables(self, text: str, environment: Environment,
                                max_iterations: int = 10) -> str:
        """
        Resolve nested variable references.
        
        Args:
            text: Text with potentially nested variables
            environment: Environment with variable values
            max_iterations: Maximum resolution iterations
            
        Returns:
            Text with all nested variables resolved
            
        Raises:
            ValueError: If circular dependencies detected or max iterations exceeded
        """
        result = text
        previous_results = set()
        
        for iteration in range(max_iterations):
            # Perform substitution
            new_result = self.engine.substitute_variables(result, environment)
            
            # Check if we've seen this result before (circular dependency)
            if new_result in previous_results:
                raise ValueError("Circular variable dependency detected")
            
            # Check if no more changes (resolution complete)
            if new_result == result:
                return new_result
            
            previous_results.add(result)
            result = new_result
        
        raise ValueError(f"Maximum iterations ({max_iterations}) exceeded for nested variable resolution")
    
    def detect_circular_dependencies(self, environment: Environment) -> List[List[str]]:
        """
        Detect circular dependencies in environment variables.
        
        Args:
            environment: Environment to check
            
        Returns:
            List of circular dependency chains
        """
        circular_deps = []
        
        for var_name, var_value in environment.variables.items():
            if self._has_circular_dependency(var_name, var_value, environment):
                # Find the actual circular chain
                chain = self._find_circular_chain(var_name, environment)
                if chain and chain not in circular_deps:
                    circular_deps.append(chain)
        
        return circular_deps
    
    def _has_circular_dependency(self, var_name: str, var_value: str, 
                                environment: Environment, 
                                visited: Optional[set] = None) -> bool:
        """Check if a variable has circular dependency."""
        if visited is None:
            visited = set()
        
        if var_name in visited:
            return True
        
        visited.add(var_name)
        
        # Find variables referenced in this variable's value
        referenced_vars = self.engine.find_variables(var_value)
        
        for ref_var in referenced_vars:
            ref_value = environment.get_variable(ref_var)
            if ref_value and self._has_circular_dependency(ref_var, ref_value, environment, visited.copy()):
                return True
        
        return False
    
    def _find_circular_chain(self, start_var: str, environment: Environment) -> Optional[List[str]]:
        """Find the circular dependency chain starting from a variable."""
        def dfs(var_name: str, path: List[str]) -> Optional[List[str]]:
            if var_name in path:
                # Found circular dependency
                cycle_start = path.index(var_name)
                return path[cycle_start:] + [var_name]
            
            var_value = environment.get_variable(var_name)
            if not var_value:
                return None
            
            referenced_vars = self.engine.find_variables(var_value)
            for ref_var in referenced_vars:
                result = dfs(ref_var, path + [var_name])
                if result:
                    return result
            
            return None
        
        return dfs(start_var, [])
    
    def _url_encode(self, text: str) -> str:
        """URL encode a string."""
        try:
            return urllib.parse.quote(text, safe='')
        except Exception:
            return text
    
    def _base64_encode(self, text: str) -> str:
        """Base64 encode a string."""
        try:
            return base64.b64encode(text.encode()).decode()
        except Exception:
            return text
    
    def _replace_function(self, text: str, old_new: str) -> str:
        """Replace function: replace:old:new"""
        try:
            parts = old_new.split(':', 1)
            if len(parts) == 2:
                old, new = parts
                return text.replace(old, new)
        except Exception:
            pass
        return text
    
    def _substr_function(self, text: str, params: str) -> str:
        """Substring function: substr:start:length or substr:start"""
        try:
            parts = params.split(':')
            if len(parts) >= 1:
                start = int(parts[0])
                if len(parts) >= 2:
                    length = int(parts[1])
                    return text[start:start+length]
                else:
                    return text[start:]
        except Exception:
            pass
        return text