#!/usr/bin/env python3
"""
Production startup script for Bot Repetitions Analysis API
"""

import os
import sys
import uvicorn
from pathlib import Path

def main():
    """Start the application."""
    # Set environment
    os.environ.setdefault("ENVIRONMENT", "production")
    
    # Get port from environment (for cloud platforms)
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"🚀 Starting Bot Repetitions Analysis API")
    print(f"   Environment: {os.environ.get('ENVIRONMENT', 'development')}")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()
