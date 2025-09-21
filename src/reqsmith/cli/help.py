"""
Comprehensive help system for the CLI.
"""
from typing import Dict, List, Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown


console = Console()


class HelpSystem:
    """Comprehensive help system with examples and tutorials."""
    
    def __init__(self):
        self.examples = self._load_examples()
        self.tutorials = self._load_tutorials()
        self.tips = self._load_tips()
    
    def show_getting_started(self):
        """Show getting started guide."""
        guide = """
# Getting Started with ReqSmith

ReqSmith is a powerful CLI tool for API testing with Postman-like functionality.

## Quick Start

1. **Make your first request:**
   ```bash
   reqsmith request get https://api.github.com/users/octocat
   ```

2. **Save a template:**
   ```bash
   reqsmith template save github-user \\
     --method GET \\
     --url "https://api.github.com/users/{username}" \\
     --description "Get GitHub user info"
   ```

3. **Create an environment:**
   ```bash
   reqsmith env create dev --description "Development environment"
   reqsmith env set API_BASE_URL "https://api.dev.example.com"
   ```

4. **Use template with environment:**
   ```bash
   reqsmith template use github-user --env dev
   ```

## Key Concepts

- **Templates**: Reusable request configurations
- **Environments**: Variable sets for different stages (dev, staging, prod)
- **History**: Automatic tracking of all requests
- **Caching**: Smart response caching with TTL

## Next Steps

- Run `reqsmith help examples` for common usage examples
- Run `reqsmith help tutorials` for detailed tutorials
- Run `reqsmith help tips` for productivity tips
        """
        
        console.print(Markdown(guide))
    
    def show_examples(self, category: Optional[str] = None):
        """Show usage examples."""
        if category and category in self.examples:
            examples = {category: self.examples[category]}
        else:
            examples = self.examples
        
        for cat, example_list in examples.items():
            console.print(f"\n[bold blue]{cat.title()} Examples[/bold blue]")
            console.print("=" * 50)
            
            for example in example_list:
                console.print(f"\n[bold]{example['title']}[/bold]")
                console.print(f"[dim]{example['description']}[/dim]")
                console.print(f"[green]$ {example['command']}[/green]")
                
                if 'output' in example:
                    console.print(f"[dim]{example['output']}[/dim]")
    
    def show_tutorials(self, topic: Optional[str] = None):
        """Show detailed tutorials."""
        if topic and topic in self.tutorials:
            tutorials = {topic: self.tutorials[topic]}
        else:
            tutorials = self.tutorials
        
        for topic_name, tutorial in tutorials.items():
            console.print(f"\n[bold blue]{tutorial['title']}[/bold blue]")
            console.print("=" * 60)
            console.print(Markdown(tutorial['content']))
    
    def show_tips(self):
        """Show productivity tips."""
        console.print("\n[bold blue]Productivity Tips[/bold blue]")
        console.print("=" * 50)
        
        for i, tip in enumerate(self.tips, 1):
            console.print(f"\n[bold yellow]{i}. {tip['title']}[/bold yellow]")
            console.print(f"[dim]{tip['description']}[/dim]")
            
            if 'example' in tip:
                console.print(f"[green]$ {tip['example']}[/green]")
    
    def show_command_help(self, command: str):
        """Show detailed help for a specific command."""
        command_help = {
            'request': self._get_request_help(),
            'template': self._get_template_help(),
            'env': self._get_env_help(),
            'history': self._get_history_help()
        }
        
        if command in command_help:
            console.print(command_help[command])
        else:
            console.print(f"[red]No detailed help available for '{command}'[/red]")
    
    def show_workflow_guide(self, workflow: str):
        """Show workflow-specific guides."""
        workflows = {
            'api-testing': self._get_api_testing_workflow(),
            'environment-management': self._get_env_management_workflow(),
            'template-organization': self._get_template_organization_workflow()
        }
        
        if workflow in workflows:
            console.print(workflows[workflow])
        else:
            available = ', '.join(workflows.keys())
            console.print(f"[red]Unknown workflow. Available: {available}[/red]")
    
    def _load_examples(self) -> Dict[str, List[Dict]]:
        """Load usage examples."""
        return {
            'basic': [
                {
                    'title': 'Simple GET Request',
                    'description': 'Make a basic GET request',
                    'command': 'reqsmith request get https://httpbin.org/get'
                },
                {
                    'title': 'POST with JSON Data',
                    'description': 'Send JSON data in POST request',
                    'command': 'reqsmith request post https://httpbin.org/post --json \'{"name": "John", "age": 30}\''
                },
                {
                    'title': 'Add Custom Headers',
                    'description': 'Include custom headers in request',
                    'command': 'reqsmith request get https://httpbin.org/headers -H "Authorization: Bearer token123" -H "User-Agent: ReqSmith/1.0"'
                }
            ],
            'templates': [
                {
                    'title': 'Save API Template',
                    'description': 'Create a reusable template',
                    'command': 'reqsmith template save user-api --method GET --url "https://api.example.com/users/${USER_ID}" --header "Authorization: Bearer ${API_TOKEN}"'
                },
                {
                    'title': 'Use Template',
                    'description': 'Execute a saved template',
                    'command': 'reqsmith template use user-api --env production'
                }
            ],
            'environments': [
                {
                    'title': 'Create Environment',
                    'description': 'Set up environment variables',
                    'command': 'reqsmith env create staging && reqsmith env set API_BASE_URL "https://staging.api.example.com"'
                },
                {
                    'title': 'Switch Environment',
                    'description': 'Change active environment',
                    'command': 'reqsmith env switch production'
                }
            ]
        }
    
    def _load_tutorials(self) -> Dict[str, Dict]:
        """Load detailed tutorials."""
        return {
            'getting-started': {
                'title': 'Getting Started Tutorial',
                'content': '''
## Installation and Setup

1. Install ReqSmith (installation method depends on your setup)
2. Verify installation: `reqsmith --version`
3. Check status: `reqsmith status`

## Your First API Request

Let's start with a simple GET request to a public API:

```bash
reqsmith request get https://jsonplaceholder.typicode.com/posts/1
```

This will:
- Make a GET request to the specified URL
- Display the response with syntax highlighting
- Automatically add the request to your history

## Working with Templates

Templates allow you to save and reuse request configurations:

```bash
# Save a template
reqsmith template save jsonplaceholder-post \\
  --method GET \\
  --url "https://jsonplaceholder.typicode.com/posts/${POST_ID}" \\
  --description "Get a specific post"

# Use the template
reqsmith template use jsonplaceholder-post
```

## Environment Variables

Environments help manage different configurations:

```bash
# Create environment
reqsmith env create development

# Set variables
reqsmith env set API_BASE_URL "https://dev.api.example.com"
reqsmith env set API_TOKEN "dev-token-123"

# Switch environment
reqsmith env switch development
```
                '''
            },
            'advanced-features': {
                'title': 'Advanced Features',
                'content': '''
## GraphQL Support

ReqSmith supports GraphQL queries:

```bash
reqsmith request graphql https://api.github.com/graphql \\
  --query 'query { viewer { login } }' \\
  --header "Authorization: Bearer YOUR_TOKEN"
```

## Response Caching

Enable caching for faster repeated requests:

```bash
# Enable caching for this request
reqsmith request get https://api.example.com/data --cache

# Clear cache when needed
reqsmith cleanup --cache
```

## Batch Requests

Execute multiple requests from a file:

```bash
# Create batch file (JSON format)
echo '[
  {"method": "GET", "url": "https://httpbin.org/get"},
  {"method": "POST", "url": "https://httpbin.org/post", "body": "test"}
]' > batch.json

# Execute batch
reqsmith request batch batch.json
```

## History and Retry

View and retry previous requests:

```bash
# View history
reqsmith history list --limit 10

# Retry last request
reqsmith history retry --last

# Retry failed requests
reqsmith history retry --failed
```
                '''
            }
        }
    
    def _load_tips(self) -> List[Dict]:
        """Load productivity tips."""
        return [
            {
                'title': 'Use Shell Completion',
                'description': 'Enable tab completion for faster command entry',
                'example': 'reqsmith completion install'
            },
            {
                'title': 'Organize Templates with Tags',
                'description': 'Use tags to categorize and find templates easily',
                'example': 'reqsmith template save api-endpoint --tag "user-management" --tag "v2"'
            },
            {
                'title': 'Use Environment Variables',
                'description': 'Store sensitive data like API keys in environment variables',
                'example': 'reqsmith env set API_KEY "$(cat ~/.secrets/api_key)"'
            },
            {
                'title': 'Save Responses for Analysis',
                'description': 'Save responses to files for later analysis',
                'example': 'reqsmith request get https://api.example.com/data -o response.json'
            },
            {
                'title': 'Use History for Debugging',
                'description': 'Analyze request patterns and retry failed requests',
                'example': 'reqsmith history analyze'
            }
        ]
    
    def _get_request_help(self) -> Panel:
        """Get detailed help for request commands."""
        content = """
[bold]Request Commands[/bold]

The request command group allows you to make HTTP requests with various methods and options.

[bold blue]Available Methods:[/bold blue]
• get     - Send GET request
• post    - Send POST request  
• put     - Send PUT request
• patch   - Send PATCH request
• delete  - Send DELETE request
• graphql - Send GraphQL query

[bold blue]Common Options:[/bold blue]
• -H, --header    - Add custom headers (key:value)
• -p, --param     - Add query parameters (key=value)
• -o, --output    - Save response to file
• -f, --format    - Response format (auto, json, xml, raw, table)
• -t, --template  - Use saved template
• -e, --env       - Use environment variables
• --cache         - Enable response caching

[bold blue]Examples:[/bold blue]
reqsmith request get https://api.example.com/users
reqsmith request post https://api.example.com/users --json '{"name": "John"}'
reqsmith request get https://api.example.com/data -H "Authorization: Bearer token"
        """
        
        return Panel(content, title="Request Command Help", border_style="blue")
    
    def _get_template_help(self) -> Panel:
        """Get detailed help for template commands."""
        content = """
[bold]Template Commands[/bold]

Templates allow you to save and reuse request configurations.

[bold blue]Available Commands:[/bold blue]
• save     - Save new template
• list     - List all templates
• show     - Show template details
• use      - Execute template
• delete   - Delete template
• export   - Export templates to file
• import   - Import templates from file
• search   - Search templates
• stats    - Show template statistics

[bold blue]Template Features:[/bold blue]
• Variable substitution with ${VAR} syntax
• Parameter overrides at execution time
• Tags for organization
• Usage tracking and statistics
• Import/export in JSON, YAML, Postman formats

[bold blue]Examples:[/bold blue]
reqsmith template save api-call --method GET --url "https://api.example.com/users/${USER_ID}"
reqsmith template use api-call --env production
reqsmith template list --tag "user-management"
        """
        
        return Panel(content, title="Template Command Help", border_style="green")
    
    def _get_env_help(self) -> Panel:
        """Get detailed help for environment commands."""
        content = """
[bold]Environment Commands[/bold]

Environments help manage variables for different stages (dev, staging, prod).

[bold blue]Available Commands:[/bold blue]
• create   - Create new environment
• list     - List all environments
• switch   - Switch active environment
• current  - Show current environment
• set      - Set environment variable
• get      - Get environment variable
• unset    - Remove environment variable
• vars     - List variables in environment
• delete   - Delete environment
• copy     - Copy environment
• export   - Export environment to file
• import   - Import environment from file
• stats    - Show environment statistics

[bold blue]Variable Substitution:[/bold blue]
• ${VAR} or {{VAR}} syntax in templates and requests
• Automatic substitution in URLs, headers, and body
• Support for nested variables and default values

[bold blue]Examples:[/bold blue]
reqsmith env create staging
reqsmith env set API_BASE_URL "https://staging.api.example.com"
reqsmith env switch production
        """
        
        return Panel(content, title="Environment Command Help", border_style="yellow")
    
    def _get_history_help(self) -> Panel:
        """Get detailed help for history commands."""
        content = """
[bold]History Commands[/bold]

History automatically tracks all requests and provides analysis tools.

[bold blue]Available Commands:[/bold blue]
• list     - List request history
• show     - Show detailed request info
• retry    - Retry previous requests
• search   - Search history
• stats    - Show history statistics
• clear    - Clear all history
• export   - Export history to file
• analyze  - Analyze request patterns

[bold blue]Filtering Options:[/bold blue]
• --method     - Filter by HTTP method
• --status     - Filter by status code
• --url        - Filter by URL pattern
• --template   - Filter by template name
• --env        - Filter by environment
• --days       - Show recent requests

[bold blue]Examples:[/bold blue]
reqsmith history list --limit 20 --method GET
reqsmith history retry --failed
reqsmith history search "api.example.com"
        """
        
        return Panel(content, title="History Command Help", border_style="magenta")
    
    def _get_api_testing_workflow(self) -> Panel:
        """Get API testing workflow guide."""
        content = """
[bold]API Testing Workflow[/bold]

A systematic approach to API testing with ReqSmith.

[bold blue]1. Environment Setup[/bold blue]
reqsmith env create testing
reqsmith env set API_BASE_URL "https://api.example.com"
reqsmith env set API_TOKEN "your-test-token"

[bold blue]2. Create Test Templates[/bold blue]
reqsmith template save user-list --method GET --url "${API_BASE_URL}/users"
reqsmith template save user-create --method POST --url "${API_BASE_URL}/users" --json '{"name": "Test User"}'

[bold blue]3. Execute Tests[/bold blue]
reqsmith template use user-list --env testing
reqsmith template use user-create --env testing

[bold blue]4. Analyze Results[/bold blue]
reqsmith history stats --days 1
reqsmith history list --status 200
reqsmith history retry --failed

[bold blue]5. Export Results[/bold blue]
reqsmith history export test-results.json --limit 50
        """
        
        return Panel(content, title="API Testing Workflow", border_style="cyan")
    
    def _get_env_management_workflow(self) -> Panel:
        """Get environment management workflow guide."""
        content = """
[bold]Environment Management Workflow[/bold]

Best practices for managing multiple environments.

[bold blue]1. Create Environment Hierarchy[/bold blue]
reqsmith env create local
reqsmith env create development  
reqsmith env create staging
reqsmith env create production

[bold blue]2. Set Common Variables[/bold blue]
# Local environment
reqsmith env switch local
reqsmith env set API_BASE_URL "http://localhost:3000"
reqsmith env set DEBUG_MODE "true"

# Production environment  
reqsmith env switch production
reqsmith env set API_BASE_URL "https://api.example.com"
reqsmith env set DEBUG_MODE "false"

[bold blue]3. Use Environment-Specific Templates[/bold blue]
reqsmith template save health-check --url "${API_BASE_URL}/health"
reqsmith template use health-check --env local
reqsmith template use health-check --env production

[bold blue]4. Environment Maintenance[/bold blue]
reqsmith env export production prod-backup.json
reqsmith env stats
reqsmith env copy production production-backup
        """
        
        return Panel(content, title="Environment Management", border_style="green")
    
    def _get_template_organization_workflow(self) -> Panel:
        """Get template organization workflow guide."""
        content = """
[bold]Template Organization Workflow[/bold]

Strategies for organizing and managing templates effectively.

[bold blue]1. Use Descriptive Names[/bold blue]
reqsmith template save user-api-get-by-id --method GET --url "/users/${USER_ID}"
reqsmith template save user-api-create --method POST --url "/users"

[bold blue]2. Apply Consistent Tags[/bold blue]
reqsmith template save user-endpoint --tag "user-management" --tag "v2-api"
reqsmith template save order-endpoint --tag "order-management" --tag "v2-api"

[bold blue]3. Add Descriptions[/bold blue]
reqsmith template save complex-query --description "Complex user search with filters and pagination"

[bold blue]4. Regular Maintenance[/bold blue]
reqsmith template list --sort usage_count
reqsmith template search "deprecated"
reqsmith template stats

[bold blue]5. Import/Export for Sharing[/bold blue]
reqsmith template export team-templates.json --tag "shared"
reqsmith template import postman-collection.json --format postman
        """
        
        return Panel(content, title="Template Organization", border_style="blue")


# Create global help system instance
help_system = HelpSystem()


# Help command functions for CLI integration
def show_getting_started():
    """Show getting started guide."""
    help_system.show_getting_started()


def show_examples(category: Optional[str] = None):
    """Show usage examples."""
    help_system.show_examples(category)


def show_tutorials(topic: Optional[str] = None):
    """Show detailed tutorials."""
    help_system.show_tutorials(topic)


def show_tips():
    """Show productivity tips."""
    help_system.show_tips()


def show_command_help(command: str):
    """Show detailed help for a specific command."""
    help_system.show_command_help(command)


def show_workflow_guide(workflow: str):
    """Show workflow-specific guides."""
    help_system.show_workflow_guide(workflow)


def show_help_menu():
    """Show main help menu with available topics."""
    console.print("\n[bold blue]ReqSmith Help System[/bold blue]")
    console.print("=" * 50)
    
    console.print("\n[bold]Available Help Topics:[/bold]")
    
    topics = [
        ("getting-started", "Basic introduction and quick start"),
        ("examples", "Common usage examples"),
        ("tutorials", "Detailed step-by-step tutorials"),
        ("tips", "Productivity tips and best practices"),
        ("workflows", "Complete workflow guides")
    ]
    
    for topic, description in topics:
        console.print(f"  [cyan]{topic:<15}[/cyan] {description}")
    
    console.print("\n[bold]Command-Specific Help:[/bold]")
    commands = ["request", "template", "env", "history"]
    
    for command in commands:
        console.print(f"  [green]reqsmith help {command}[/green]")
    
    console.print("\n[bold]Usage:[/bold]")
    console.print("  reqsmith help <topic>")
    console.print("  reqsmith help examples [category]")
    console.print("  reqsmith help tutorials [topic]")
    console.print("  reqsmith help workflows <workflow>")