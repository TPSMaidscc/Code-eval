#!/usr/bin/env python3
"""
Configuration validation script
Run this script to validate your environment configuration before deployment
"""

import os
import sys
from pathlib import Path

# Add the app directory to the path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

def validate_config():
    """Validate configuration and environment variables"""
    print("🔍 Validating configuration...")
    
    # Check if .env file exists (for development)
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file found")
        # Load .env file if python-dotenv is available
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("✅ .env file loaded")
        except ImportError:
            print("⚠️  python-dotenv not installed, .env file not loaded automatically")
    else:
        print("ℹ️  No .env file found (OK for production)")
    
    # Import config to trigger validation
    try:
        from app.config import TABLEAU_CONFIG, DEPARTMENT_CONFIG, validate_required_env_vars
        print("✅ Configuration imported successfully")
    except ValueError as e:
        print(f"❌ Configuration validation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error importing configuration: {e}")
        return False
    
    # Check individual components
    print("\n📋 Configuration Summary:")
    print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"Port: {os.getenv('PORT', '8000')}")
    
    # Check Tableau config (without exposing sensitive values)
    tableau_configured = all([
        TABLEAU_CONFIG.get('token_name'),
        TABLEAU_CONFIG.get('token_value'),
        TABLEAU_CONFIG.get('site_content_url')
    ])
    print(f"Tableau configured: {'✅' if tableau_configured else '❌'}")
    
    # Check department spreadsheet IDs
    dept_configured = all([
        dept_config.get('spreadsheet_id') 
        for dept_config in DEPARTMENT_CONFIG.values()
    ])
    print(f"Department spreadsheets configured: {'✅' if dept_configured else '❌'}")
    
    # Check Service Account credentials
    service_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "cred.json")
    google_creds_env = os.getenv("GOOGLE_CREDENTIALS")

    creds_available = (
        Path(service_file).exists() or
        google_creds_env is not None
    )
    print(f"Service Account credentials available: {'✅' if creds_available else '❌'}")

    if Path(service_file).exists():
        print(f"  📄 Service Account file: {service_file}")
    elif google_creds_env:
        print(f"  🔐 Service Account from environment variable")
    else:
        print(f"  ❌ No Service Account credentials found")
    
    if tableau_configured and dept_configured and creds_available:
        print("\n🎉 Configuration validation passed! Ready for deployment.")
        return True
    else:
        print("\n❌ Configuration validation failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = validate_config()
    sys.exit(0 if success else 1)
