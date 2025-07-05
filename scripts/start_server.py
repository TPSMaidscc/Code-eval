#!/usr/bin/env python3
"""
Server startup script for the Bot Repetitions Analysis API
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_environment():
    """Check if the environment is properly set up."""
    print("🔍 Checking environment...")
    
    # Check if we're in the right directory
    if not Path("app/main.py").exists():
        print("❌ app/main.py not found. Make sure you're in the project root directory.")
        return False
    
    # Check for required directories
    required_dirs = ["app", "config", "data", "logs"]
    for directory in required_dirs:
        if not Path(directory).exists():
            print(f"❌ Directory '{directory}' not found")
            return False
    
    print("✅ Environment check passed")
    return True

def check_dependencies():
    """Check if required dependencies are installed."""
    print("📦 Checking dependencies...")

    required_packages = {
        'fastapi': 'FastAPI web framework',
        'uvicorn': 'ASGI server',
        'pandas': 'Data processing',
        'gspread': 'Google Sheets API',
        'google.auth': 'Google authentication',
        'requests': 'HTTP requests'
    }

    missing_packages = []

    for package, description in required_packages.items():
        try:
            # Handle packages with dots in the name
            if '.' in package:
                parts = package.split('.')
                module = __import__(parts[0])
                for part in parts[1:]:
                    module = getattr(module, part)
            else:
                __import__(package)
            print(f"   ✅ {package} ({description})")
        except (ImportError, AttributeError):
            missing_packages.append(package)
            print(f"   ❌ {package} ({description})")

    if missing_packages:
        print(f"\n❌ Missing {len(missing_packages)} required packages:")
        for package in missing_packages:
            print(f"   • {package}")
        print("\n📦 Install missing packages:")
        print("   pip install -r requirements.txt")
        return False

    print("✅ All dependencies check passed")
    return True

def main():
    """Main startup function."""
    print("🚀 Starting Bot Repetitions Analysis API Server")
    print("=" * 60)
    
    # Environment checks
    if not check_environment():
        sys.exit(1)
    
    if not check_dependencies():
        sys.exit(1)
    
    # Get configuration
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    reload = os.getenv("ENVIRONMENT", "development") == "development"
    
    print(f"🌐 Server configuration:")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Reload: {reload}")
    print(f"   Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    print(f"\n📍 API will be available at:")
    print(f"   • Local: http://localhost:{port}")
    print(f"   • Network: http://{host}:{port}")
    print(f"   • Interactive Docs: http://localhost:{port}/docs")
    print(f"   • ReDoc: http://localhost:{port}/redoc")
    
    print(f"\n🛑 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
