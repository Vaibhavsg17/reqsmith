#!/usr/bin/env python3
"""
Release preparation script for ReqSmith.
Helps prepare and publish releases to PyPI.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import json


def run_command(cmd, check=True, capture_output=False):
    """Run a shell command and return the result."""
    print(f"🔧 Running: {cmd}")
    result = subprocess.run(
        cmd, 
        shell=True, 
        check=check, 
        capture_output=capture_output,
        text=True
    )
    if capture_output:
        return result.stdout.strip()
    return result.returncode == 0


def get_current_version():
    """Get the current version from __version__.py"""
    version_file = Path(__file__).parent.parent / "src" / "reqsmith" / "__version__.py"
    
    if version_file.exists():
        with open(version_file, "r") as f:
            exec(f.read())
            return locals().get("__version__", "0.1.0")
    return "0.1.0"


def update_version(new_version):
    """Update the version in __version__.py"""
    version_file = Path(__file__).parent.parent / "src" / "reqsmith" / "__version__.py"
    
    # Parse version parts
    parts = new_version.split(".")
    if len(parts) != 3:
        raise ValueError("Version must be in format x.y.z")
    
    major, minor, patch = parts
    
    content = f'''"""
Version information for ReqSmith
"""

__version__ = "{new_version}"
__version_info__ = ({major}, {minor}, {patch})

# Build information
__build__ = "release"
__author__ = "ReqSmith Team"
__email__ = "team@reqsmith.dev"
__license__ = "MIT"
__copyright__ = "Copyright 2024 ReqSmith Team"

# Package metadata
__title__ = "ReqSmith"
__description__ = "Command-line API testing tool with hybrid caching and optional AI assistance"
__url__ = "https://github.com/VesperAkshay/reqsmith"
__repository__ = "https://github.com/VesperAkshay/reqsmith.git"
__documentation__ = "https://reqsmith.dev/docs"
'''
    
    with open(version_file, "w") as f:
        f.write(content)
    
    print(f"✅ Updated version to {new_version}")


def clean_build_artifacts():
    """Clean build artifacts and caches."""
    print("🧹 Cleaning build artifacts...")
    
    artifacts = [
        "build/",
        "dist/",
        "*.egg-info/",
        "**/__pycache__/",
        "**/*.pyc",
        "**/*.pyo"
    ]
    
    import glob
    for pattern in artifacts:
        for path in glob.glob(pattern, recursive=True):
            path_obj = Path(path)
            if path_obj.exists():
                if path_obj.is_dir():
                    shutil.rmtree(path_obj, ignore_errors=True)
                else:
                    path_obj.unlink(missing_ok=True)
    
    print("✅ Build artifacts cleaned")


def run_tests():
    """Run the test suite."""
    print("🧪 Running tests...")
    
    if not run_command("python -m pytest tests/ -v --tb=short", check=False):
        print("❌ Tests failed! Please fix tests before releasing.")
        return False
    
    print("✅ All tests passed")
    return True


def run_linting():
    """Run code quality checks."""
    print("🔍 Running code quality checks...")
    
    # Try to run linting tools if available
    linting_commands = [
        "python -m flake8 src/ --max-line-length=100 --ignore=E203,W503",
        "python -m black --check src/",
        "python -m isort --check-only src/"
    ]
    
    all_passed = True
    for cmd in linting_commands:
        if not run_command(cmd, check=False):
            print(f"⚠️  Linting check failed: {cmd}")
            all_passed = False
    
    if all_passed:
        print("✅ Code quality checks passed")
    else:
        print("⚠️  Some linting checks failed (non-blocking)")
    
    return True  # Non-blocking for now


def build_package():
    """Build the package for distribution."""
    print("📦 Building package...")
    
    # Clean first
    clean_build_artifacts()
    
    # Build wheel and source distribution
    if not run_command("python -m build"):
        print("❌ Package build failed")
        return False
    
    print("✅ Package built successfully")
    return True


def check_pypi_credentials():
    """Check if PyPI credentials are configured."""
    print("🔐 Checking PyPI credentials...")
    
    # Check for .pypirc or environment variables
    pypirc_file = Path.home() / ".pypirc"
    has_pypirc = pypirc_file.exists()
    has_env_vars = os.getenv("TWINE_USERNAME") and os.getenv("TWINE_PASSWORD")
    
    if has_pypirc:
        print("✅ Found .pypirc file")
    elif has_env_vars:
        print("✅ Found PyPI credentials in environment variables")
    else:
        print("❌ No PyPI credentials found")
        print("   Set up credentials using one of these methods:")
        print("   1. Create ~/.pypirc file")
        print("   2. Set TWINE_USERNAME and TWINE_PASSWORD environment variables")
        print("   3. Use 'python -m twine upload --help' for more options")
        return False
    
    return True


def upload_to_pypi(test=False):
    """Upload package to PyPI."""
    repository = "testpypi" if test else "pypi"
    print(f"🚀 Uploading to {'Test ' if test else ''}PyPI...")
    
    # Check if dist/ contains files
    dist_dir = Path("dist")
    if not dist_dir.exists() or not list(dist_dir.glob("*")):
        print("❌ No distribution files found. Run build first.")
        return False
    
    # Upload command
    upload_cmd = f"python -m twine upload --repository {repository} dist/*"
    
    if test:
        upload_cmd = "python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*"
    
    if not run_command(upload_cmd):
        print(f"❌ Upload to {'Test ' if test else ''}PyPI failed")
        return False
    
    print(f"✅ Successfully uploaded to {'Test ' if test else ''}PyPI")
    return True


def create_git_tag(version):
    """Create and push git tag for the release."""
    print(f"🏷️  Creating git tag v{version}...")
    
    # Create tag
    if not run_command(f"git tag -a v{version} -m 'Release version {version}'"):
        print("❌ Failed to create git tag")
        return False
    
    # Push tag
    if not run_command(f"git push origin v{version}"):
        print("❌ Failed to push git tag")
        return False
    
    print(f"✅ Created and pushed git tag v{version}")
    return True


def commit_version_changes(version):
    """Commit version changes."""
    print("💾 Committing version changes...")
    
    if not run_command("git add src/reqsmith/__version__.py"):
        return False
    
    if not run_command(f"git commit -m 'Bump version to {version}'"):
        print("ℹ️  No changes to commit (version might already be updated)")
    
    return True


def main():
    """Main release process."""
    print("🚀 ReqSmith Release Preparation")
    print("=" * 40)
    
    current_version = get_current_version()
    print(f"📋 Current version: {current_version}")
    
    # Ask for new version
    print("\n📝 Version bump options:")
    print("1. Patch (0.2.0 -> 0.2.1)")
    print("2. Minor (0.2.0 -> 0.3.0)")
    print("3. Major (0.2.0 -> 1.0.0)")
    print("4. Custom version")
    print("5. Use current version")
    
    choice = input("Enter your choice (1-5): ").strip()
    
    if choice == "1":
        # Patch version
        parts = current_version.split(".")
        new_version = f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
    elif choice == "2":
        # Minor version
        parts = current_version.split(".")
        new_version = f"{parts[0]}.{int(parts[1]) + 1}.0"
    elif choice == "3":
        # Major version
        parts = current_version.split(".")
        new_version = f"{int(parts[0]) + 1}.0.0"
    elif choice == "4":
        # Custom version
        new_version = input("Enter new version (x.y.z): ").strip()
    elif choice == "5":
        # Use current version
        new_version = current_version
    else:
        print("❌ Invalid choice")
        return False
    
    print(f"\n🎯 Target version: {new_version}")
    
    # Update version if different
    if new_version != current_version:
        update_version(new_version)
        commit_version_changes(new_version)
    
    # Run checks
    if not run_tests():
        return False
    
    run_linting()  # Non-blocking
    
    # Build package
    if not build_package():
        return False
    
    # Check PyPI credentials
    if not check_pypi_credentials():
        print("\n⚠️  PyPI credentials not configured. You can:")
        print("1. Set up credentials and run upload manually")
        print("2. Continue with just building the package")
        
        skip_upload = input("Skip upload? (y/N): ").lower().strip() == "y"
        if skip_upload:
            print("✅ Package built successfully. Upload manually with:")
            print("   python -m twine upload dist/*")
            return True
        else:
            return False
    
    # Ask about test upload
    test_upload = input("Upload to Test PyPI first? (Y/n): ").lower().strip()
    if test_upload != "n":
        if not upload_to_pypi(test=True):
            return False
        
        proceed = input("Test upload successful. Continue to production PyPI? (Y/n): ").lower().strip()
        if proceed == "n":
            print("✅ Test upload completed. Upload to production PyPI manually when ready:")
            print("   python -m twine upload dist/*")
            return True
    
    # Upload to production PyPI
    if not upload_to_pypi(test=False):
        return False
    
    # Create git tag
    create_git_tag(new_version)
    
    print(f"\n🎉 Release {new_version} completed successfully!")
    print(f"📦 Package available at: https://pypi.org/project/reqsmith/{new_version}/")
    print("🏷️  Git tag created and pushed")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Release process interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Release process failed: {e}")
        sys.exit(1)
