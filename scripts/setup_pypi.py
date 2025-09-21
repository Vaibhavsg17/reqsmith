#!/usr/bin/env python3
"""
PyPI setup and configuration script for ReqSmith.
Helps set up PyPI credentials and prepare for publishing.
"""

import os
import sys
from pathlib import Path
import getpass
import subprocess


def create_pypirc():
    """Create .pypirc file with PyPI credentials."""
    print("🔐 Setting up PyPI credentials")
    print("=" * 30)
    
    print("You need PyPI account credentials to publish packages.")
    print("If you don't have an account, create one at: https://pypi.org/account/register/")
    print("For Test PyPI, create account at: https://test.pypi.org/account/register/")
    print()
    
    username = input("PyPI username: ").strip()
    if not username:
        print("❌ Username is required")
        return False
    
    password = getpass.getpass("PyPI password (or API token): ")
    if not password:
        print("❌ Password is required")
        return False
    
    test_username = input("Test PyPI username (or press Enter to use same): ").strip()
    if not test_username:
        test_username = username
    
    test_password = getpass.getpass("Test PyPI password (or press Enter to use same): ")
    if not test_password:
        test_password = password
    
    # Create .pypirc content
    pypirc_content = f"""[distutils]
index-servers =
    pypi
    testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = {username}
password = {password}

[testpypi]
repository = https://test.pypi.org/legacy/
username = {test_username}
password = {test_password}
"""
    
    # Write .pypirc file
    pypirc_path = Path.home() / ".pypirc"
    
    if pypirc_path.exists():
        backup = input(f".pypirc already exists. Create backup? (Y/n): ").lower().strip()
        if backup != "n":
            backup_path = pypirc_path.with_suffix(".pypirc.backup")
            pypirc_path.rename(backup_path)
            print(f"✅ Backup created: {backup_path}")
    
    with open(pypirc_path, "w") as f:
        f.write(pypirc_content)
    
    # Set secure permissions
    os.chmod(pypirc_path, 0o600)
    
    print(f"✅ PyPI credentials saved to {pypirc_path}")
    print("🔒 File permissions set to 600 (user read/write only)")
    
    return True


def install_build_tools():
    """Install required build and upload tools."""
    print("🔧 Installing build tools...")
    
    tools = [
        "build",
        "twine",
        "setuptools",
        "wheel"
    ]
    
    for tool in tools:
        print(f"  Installing {tool}...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "--upgrade", tool
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Failed to install {tool}")
            print(result.stderr)
            return False
    
    print("✅ All build tools installed successfully")
    return True


def verify_setup():
    """Verify that everything is set up correctly."""
    print("🔍 Verifying setup...")
    
    # Check if .pypirc exists
    pypirc_path = Path.home() / ".pypirc"
    if pypirc_path.exists():
        print("✅ .pypirc file found")
    else:
        print("❌ .pypirc file not found")
        return False
    
    # Check build tools
    tools = ["build", "twine"]
    for tool in tools:
        result = subprocess.run([
            sys.executable, "-m", tool, "--help"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {tool} is available")
        else:
            print(f"❌ {tool} is not available")
            return False
    
    # Check project structure
    required_files = [
        "pyproject.toml",
        "setup.py",
        "README.md",
        "src/reqsmith/__init__.py",
        "src/reqsmith/__version__.py"
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path} found")
        else:
            print(f"❌ {file_path} not found")
            return False
    
    print("✅ Setup verification completed successfully")
    return True


def show_next_steps():
    """Show next steps for publishing."""
    print("\n🎯 Next Steps")
    print("=" * 15)
    print()
    print("1. Test your package build:")
    print("   python scripts/release.py")
    print()
    print("2. Or manually build and test:")
    print("   python -m build")
    print("   python -m twine upload --repository testpypi dist/*")
    print()
    print("3. Install from Test PyPI to verify:")
    print("   pip install --index-url https://test.pypi.org/simple/ reqsmith")
    print()
    print("4. If everything works, upload to production PyPI:")
    print("   python -m twine upload dist/*")
    print()
    print("5. Verify installation from PyPI:")
    print("   pip install reqsmith")
    print()
    print("📚 Documentation:")
    print("   PyPI: https://packaging.python.org/tutorials/packaging-projects/")
    print("   Twine: https://twine.readthedocs.io/")


def main():
    """Main setup process."""
    print("🚀 ReqSmith PyPI Setup")
    print("=" * 25)
    print()
    
    print("This script will help you set up PyPI publishing for ReqSmith.")
    print("You'll need PyPI account credentials.")
    print()
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ pyproject.toml not found. Run this script from the project root.")
        return False
    
    # Install build tools
    install_tools = input("Install/upgrade build tools (build, twine, etc.)? (Y/n): ").lower().strip()
    if install_tools != "n":
        if not install_build_tools():
            return False
    
    # Set up credentials
    setup_creds = input("Set up PyPI credentials? (Y/n): ").lower().strip()
    if setup_creds != "n":
        if not create_pypirc():
            return False
    
    # Verify setup
    if not verify_setup():
        print("❌ Setup verification failed")
        return False
    
    print("\n🎉 PyPI setup completed successfully!")
    
    # Show next steps
    show_next_steps()
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Setup interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)
