"""
Entry point for serverless deployments (Vercel, etc.)
"""

from app.main import app

# For Vercel and other serverless platforms
handler = app
