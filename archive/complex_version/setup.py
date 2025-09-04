#!/usr/bin/env python3
"""Setup script for Ayah App."""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def run_command(cmd, description=""):
    """Run a shell command and handle errors."""
    print(f"Running: {cmd}")
    if description:
        print(f"Description: {description}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    print(f"Python version: {sys.version}")


def setup_virtual_environment():
    """Create and activate virtual environment."""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("Virtual environment already exists")
        return True
    
    print("Creating virtual environment...")
    return run_command("python3 -m venv venv", "Creating virtual environment")


def install_dependencies():
    """Install Python dependencies."""
    print("Installing dependencies...")
    
    # Activate virtual environment and install
    if os.name == 'nt':  # Windows
        pip_cmd = "venv\\Scripts\\pip"
    else:  # Unix-like
        pip_cmd = "venv/bin/pip"
    
    commands = [
        f"{pip_cmd} install --upgrade pip",
        f"{pip_cmd} install -e .[dev]"
    ]
    
    for cmd in commands:
        if not run_command(cmd):
            return False
    
    return True


def setup_environment_file():
    """Setup .env file from example."""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print(".env file already exists")
        return True
    
    if not env_example.exists():
        print("Warning: .env.example not found")
        return False
    
    shutil.copy(env_example, env_file)
    print("Created .env file from .env.example")
    print("Please edit .env file with your configuration")
    return True


def create_directories():
    """Create necessary directories."""
    directories = [
        "data",
        "cache", 
        "logs",
        "static/css",
        "static/js",
        "templates"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {dir_path}")


def move_original_data():
    """Move original data files to new structure."""
    original_files = {
        "scripts/ayah-a-day.py": "legacy/original_script.py",
        "outputs/ayah-of-the-day.html": "legacy/original_output.html"
    }
    
    # Create legacy directory
    Path("legacy").mkdir(exist_ok=True)
    
    for old_path, new_path in original_files.items():
        old_file = Path(old_path)
        new_file = Path(new_path)
        
        if old_file.exists():
            shutil.move(str(old_file), str(new_file))
            print(f"Moved {old_path} to {new_path}")


def setup_data_files():
    """Check for required data files."""
    required_files = [
        "data/qpc-hafs.json",
        "data/en-taqi-usmani-simple.json", 
        "data/en-tafisr-ibn-kathir.json"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("Warning: The following required data files are missing:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        print("Please add these files before running the application.")
        return False
    
    print("All required data files found")
    return True


def run_tests():
    """Run test suite to verify installation."""
    print("Running test suite...")
    
    if os.name == 'nt':  # Windows
        pytest_cmd = "venv\\Scripts\\pytest"
    else:  # Unix-like
        pytest_cmd = "venv/bin/pytest"
    
    return run_command(f"{pytest_cmd} tests/ -v", "Running tests")


def main():
    """Main setup function."""
    print("=" * 60)
    print("Ayah App Setup Script")
    print("=" * 60)
    
    # Check Python version
    check_python_version()
    
    # Setup steps
    steps = [
        ("Creating virtual environment", setup_virtual_environment),
        ("Installing dependencies", install_dependencies),
        ("Setting up environment file", setup_environment_file),
        ("Creating directories", create_directories),
        ("Moving original files", move_original_data),
        ("Checking data files", setup_data_files),
    ]
    
    failed_steps = []
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        if not step_func():
            failed_steps.append(step_name)
            print(f"❌ {step_name} failed")
        else:
            print(f"✅ {step_name} completed")
    
    # Run tests (optional)
    print("\nRunning tests (optional)...")
    if run_tests():
        print("✅ Tests passed")
    else:
        print("⚠️ Some tests failed (this might be okay if data files are missing)")
    
    # Summary
    print("\n" + "=" * 60)
    print("Setup Summary")
    print("=" * 60)
    
    if failed_steps:
        print("❌ Setup completed with errors:")
        for step in failed_steps:
            print(f"  - {step}")
    else:
        print("✅ Setup completed successfully!")
    
    print("\nNext steps:")
    print("1. Edit .env file with your configuration")
    print("2. Add required data files to data/ directory")
    print("3. Run the application:")
    
    if os.name == 'nt':  # Windows
        print("   venv\\Scripts\\python -m src.ayah_app.app")
    else:  # Unix-like
        print("   venv/bin/python -m src.ayah_app.app")
    
    print("4. Visit http://localhost:5000")
    print("\nFor deployment instructions, see DEPLOYMENT.md")


if __name__ == "__main__":
    main()