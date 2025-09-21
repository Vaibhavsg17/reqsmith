"""
Setup configuration for ReqSmith CLI
"""

import os
from pathlib import Path
from setuptools import setup, find_packages

# Read version from version file
def get_version():
    version_file = Path(__file__).parent / "src" / "reqsmith" / "__version__.py"
    if version_file.exists():
        with open(version_file, "r", encoding="utf-8") as f:
            exec(f.read())
            return locals()["__version__"]
    return "0.1.0"

# Read long description from README
def get_long_description():
    readme_file = Path(__file__).parent / "README.md"
    if readme_file.exists():
        with open(readme_file, "r", encoding="utf-8") as f:
            return f.read()
    return "ReqSmith - Command-line API testing tool"

# Read requirements from requirements.txt
def get_requirements():
    requirements_file = Path(__file__).parent / "requirements.txt"
    if requirements_file.exists():
        with open(requirements_file, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    # Fallback to hardcoded requirements
    return [
        "typer>=0.9.0",
        "rich>=13.0.0",
        "httpx>=0.24.0",
        "python-dotenv>=1.0.0",
        "google-generativeai>=0.3.0",
        "cryptography>=41.0.0",
        "pydantic>=2.0.0",
        "click>=8.0.0",
    ]

setup(
    name="reqsmith",
    version=get_version(),
    author="ReqSmith Team",
    author_email="team@reqsmith.dev",
    description="Command-line API testing tool with hybrid caching and optional AI assistance",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/VesperAkshay/reqsmith",
    project_urls={
        "Bug Reports": "https://github.com/VesperAkshay/reqsmith/issues",
        "Source": "https://github.com/VesperAkshay/reqsmith",
        "Documentation": "https://vesperakshay.github.io/reqsmith/",
    },
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    package_data={
        "reqsmith": ["py.typed"],
        "reqsmith.config": ["*.json", "*.yaml"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Testing",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: System :: Networking",
        "Topic :: Utilities",
        "Environment :: Console",
    ],
    keywords="api testing cli http rest graphql automation",
    python_requires=">=3.9",
    install_requires=get_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-mock>=3.10.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "isort>=5.12.0",
            "pre-commit>=3.0.0",
        ],
        "yaml": [
            "PyYAML>=6.0",
        ],
        "all": [
            "PyYAML>=6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "reqsmith=reqsmith.cli.main:cli_main",
        ],
    },
    zip_safe=False,
)