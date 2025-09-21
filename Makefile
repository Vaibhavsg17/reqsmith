# Makefile for ReqSmith development

.PHONY: help install install-dev test test-cov lint format clean build upload docs

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install package"
	@echo "  install-dev  - Install package in development mode"
	@echo "  test         - Run tests"
	@echo "  test-cov     - Run tests with coverage"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code"
	@echo "  clean        - Clean build artifacts"
	@echo "  build        - Build package"
	@echo "  upload       - Upload to PyPI"
	@echo "  docs         - Build documentation"

# Installation
install:
	pip install .

install-dev:
	pip install -e .[dev]

# Testing
test:
	pytest

test-cov:
	pytest --cov=src/reqsmith --cov-report=html --cov-report=term

# Code quality
lint:
	flake8 src tests
	mypy src
	black --check src tests
	isort --check-only src tests

format:
	black src tests
	isort src tests

# Build and distribution
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

upload: build
	python -m twine upload dist/*

upload-test: build
	python -m twine upload --repository testpypi dist/*

# Documentation
docs:
	cd docs && make html

docs-serve:
	cd docs/_build/html && python -m http.server 8000

# Development helpers
setup-dev:
	python -m venv venv
	. venv/bin/activate && pip install -r requirements-dev.txt
	. venv/bin/activate && pip install -e .

pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

# Version management
version-patch:
	bump2version patch

version-minor:
	bump2version minor

version-major:
	bump2version major

# Docker (if needed)
docker-build:
	docker build -t reqsmith .

docker-run:
	docker run -it --rm reqsmith

# Security checks
security:
	bandit -r src/
	safety check