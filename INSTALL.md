# Installation Guide

This guide covers different ways to install ReqSmith on your system.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation Methods

### 1. Install from PyPI (Recommended)

```bash
pip install reqsmith
```

For YAML configuration support:
```bash
pip install reqsmith[yaml]
```

For all optional features:
```bash
pip install reqsmith[all]
```

### 2. Install from Source

#### Clone and Install
```bash
git clone https://github.com/VesperAkshay/reqsmith.git
cd reqsmith
pip install .
```

#### Development Installation
```bash
git clone https://github.com/VesperAkshay/reqsmith.git
cd reqsmith
pip install -e .[dev]
```

### 3. Install with pipx (Isolated Installation)

```bash
pipx install reqsmith
```

This installs ReqSmith in an isolated environment while making it available globally.

## Verify Installation

After installation, verify that ReqSmith is working:

```bash
reqsmith --version
reqsmith --help
```

## Configuration

ReqSmith will create its configuration directory at `~/.reqsmith/` on first run.

### Initial Setup

1. **Set up Gemini AI (Optional)**:
   ```bash
   reqsmith config set ai.gemini_api_key "your-api-key-here"
   ```

2. **Configure default settings**:
   ```bash
   reqsmith config show
   reqsmith config set output.default_format table
   reqsmith config set network.timeout_seconds 60
   ```

3. **Test the installation**:
   ```bash
   reqsmith request get https://httpbin.org/get
   ```

## Environment Variables

You can override configuration using environment variables:

```bash
export REQSMITH_DEBUG=true
export REQSMITH_TIMEOUT=60
export REQSMITH_GEMINI_API_KEY="your-api-key"
```

See `reqsmith config env` for a full list of available environment variables.

## Troubleshooting

### Common Issues

1. **Command not found**: Make sure pip's bin directory is in your PATH
2. **Permission errors**: Use `pip install --user reqsmith` for user-only installation
3. **Python version**: Ensure you're using Python 3.8 or higher

### Getting Help

- Run `reqsmith help` for built-in help
- Check the [documentation](https://vesperakshay.github.io/reqsmith/)
- Report issues on [GitHub](https://github.com/VesperAkshay/reqsmith/issues)

## Uninstallation

To remove ReqSmith:

```bash
pip uninstall reqsmith
```

To also remove configuration and data:

```bash
rm -rf ~/.reqsmith/
```

## Development Setup

For contributing to ReqSmith:

```bash
git clone https://github.com/VesperAkshay/reqsmith.git
cd reqsmith

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
pip install -e .

# Run tests
pytest

# Run linting
black src tests
flake8 src tests
mypy src
```