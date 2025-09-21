# ReqSmith

A powerful command-line API testing tool with hybrid caching and optional AI assistance.

## Features

- **HTTP/REST API Testing**: Support for GET, POST, PUT, PATCH, DELETE, OPTIONS methods
- **GraphQL Support**: Native GraphQL query and mutation testing
- **Hybrid Caching**: Memory + disk-based caching for improved performance
- **Template Management**: Save and reuse request templates
- **Environment Variables**: Manage different environments (dev, staging, prod)
- **Request History**: Track and replay previous requests
- **Rich Output**: Color-coded responses with JSON/XML formatting
- **AI Assistance**: Optional Gemini AI integration for request validation and suggestions
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Requirements

- Python 3.9 or higher
- Network connectivity for API testing

## Installation

```bash
pip install reqsmith
```

## Quick Start

```bash
# Simple GET request
reqsmith get https://api.example.com/users

# POST request with JSON body
reqsmith post https://api.example.com/users -d '{"name": "John", "email": "john@example.com"}'

# Save request as template
reqsmith save-template user-create --method POST --url https://api.example.com/users -d '{"name": "{{name}}", "email": "{{email}}"}'

# Use template with variables
reqsmith use-template user-create --var name="Jane" --var email="jane@example.com"
```

## Configuration

ReqSmith stores configuration in `~/.reqsmith/config.json`. You can customize:

- Storage settings (cache sizes, paths)
- Network settings (timeouts, retries)
- Output formatting preferences
- AI features (Gemini API key)

## AI Features

ReqSmith includes powerful AI assistance using Google's Gemini API for enhanced API testing.

### Setup AI Features

1. **Get a Gemini API Key:**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in with your Google account
   - Create a new API key

2. **Configure the API Key:**

   **Option A: Using ReqSmith configuration (recommended)**
   ```bash
   # Run the interactive setup
   python dev_scripts/setup_ai.py
   
   # Or configure directly
   reqsmith config set ai.gemini_api_key "your-api-key-here"
   ```

   **Option B: Environment variable**
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

3. **Test AI Integration:**
   ```bash
   python dev_scripts/test_ai_integration.py
   ```

### AI Capabilities

- **Smart Header Suggestions**: Get appropriate headers for API endpoints
- **JSON Validation**: Intelligent validation with detailed explanations
- **Status Code Explanations**: Natural language explanations of HTTP status codes
- **Test Scenario Generation**: AI-generated test scenarios for endpoints
- **API Analysis**: Intelligent analysis of API endpoints and patterns

### Usage Examples

```bash
# Get AI-suggested headers
reqsmith request get https://api.github.com/user --ai-headers

# AI-powered JSON validation
reqsmith validate --json '{"name": "test"}' --ai-suggest

# Natural language status explanations
reqsmith explain-status 404

# Generate test scenarios
reqsmith analyze https://api.example.com/users --generate-tests
```

## Development

```bash
# Clone the repository
git clone https://github.com/VesperAkshay/reqsmith.git
cd reqsmith

# Install in development mode
pip install -e .

# Run tests
pytest
```

## License

MIT License - see LICENSE file for details.