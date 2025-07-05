#!/usr/bin/env python3
"""
Setup utilities for the Bot Repetitions Analysis API
"""

import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

def create_directories():
    """Create required directories."""
    directories = [
        "app",
        "app/api", 
        "app/services",
        "config",
        "data/temp",
        "data/output",
        "data/archive",
        "logs",
        "utils",
        "scripts",
        "tests",
        "docs"
    ]
    
    print("📁 Creating directory structure...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {directory}")
    
    print("✅ Directory structure created")

def check_dependencies() -> bool:
    """Check if required dependencies are installed."""
    required_packages = [
        'fastapi', 'uvicorn', 'pandas', 'gspread', 
        'google-auth', 'requests', 'pydantic'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   • {package}")
        print("\n📦 Install missing packages:")
        print("   pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies found")
    return True

def check_config_files() -> Dict[str, bool]:
    """Check if configuration files exist."""
    config_files = {
        'config/cred.json': False,
        'config/service-account-key.json': False
    }
    
    print("🔍 Checking configuration files...")
    for file_path in config_files:
        if Path(file_path).exists():
            config_files[file_path] = True
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path}")
    
    return config_files

def create_sample_config():
    """Create sample configuration files."""
    print("📝 Creating sample configuration files...")
    
    # Sample OAuth config
    oauth_config = {
        "installed": {
            "client_id": "your-client-id.apps.googleusercontent.com",
            "project_id": "your-project-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "your-client-secret",
            "redirect_uris": ["http://localhost"]
        }
    }
    
    with open('config/cred.json.sample', 'w') as f:
        json.dump(oauth_config, f, indent=2)
    print("   ✅ config/cred.json.sample")
    
    # Sample service account config
    service_account_config = {
        "type": "service_account",
        "project_id": "your-project-id",
        "private_key_id": "your-private-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n",
        "client_email": "bot-analysis@your-project-id.iam.gserviceaccount.com",
        "client_id": "your-client-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/bot-analysis%40your-project-id.iam.gserviceaccount.com"
    }
    
    with open('config/service-account-key.json.sample', 'w') as f:
        json.dump(service_account_config, f, indent=2)
    print("   ✅ config/service-account-key.json.sample")

def create_gitignore():
    """Create .gitignore file."""
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
logs/*.log
*.log

# Data files
data/temp/*
data/output/*
data/archive/*
!data/temp/.gitkeep
!data/output/.gitkeep
!data/archive/.gitkeep

# Configuration files (sensitive)
config/cred.json
config/service-account-key.json
*.pickle

# Environment variables
.env
.env.local

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/

# Documentation
docs/_build/
"""
    
    with open('.gitignore', 'w') as f:
        f.write(gitignore_content)
    print("✅ .gitignore created")

def create_placeholder_files():
    """Create placeholder files for empty directories."""
    placeholder_dirs = [
        "data/temp",
        "data/output", 
        "data/archive",
        "logs"
    ]
    
    for directory in placeholder_dirs:
        placeholder_file = Path(directory) / ".gitkeep"
        placeholder_file.touch()

def main():
    """Main setup function."""
    print("🚀 Bot Repetitions Analysis API Setup")
    print("=" * 50)
    
    # Create directories
    create_directories()
    
    # Create placeholder files
    create_placeholder_files()
    
    # Check dependencies
    if not check_dependencies():
        print("\n⚠️  Please install dependencies before proceeding")
    
    # Check config files
    config_status = check_config_files()
    
    # Create sample configs if needed
    if not any(config_status.values()):
        create_sample_config()
        print("\n📋 Next steps:")
        print("1. Copy config/cred.json.sample to config/cred.json")
        print("2. Update config/cred.json with your Google OAuth credentials")
        print("3. Or set up Service Account authentication")
    
    # Create .gitignore
    create_gitignore()
    
    print("\n🎉 Setup completed!")
    print("📚 See README.md for next steps")

if __name__ == "__main__":
    main()
