"""
Configuration settings for the Bot Repetitions Analysis API
"""

import os
import json
from typing import Dict, Any

# API Configuration
API_TITLE = "Bot Repetitions Analysis API"
API_DESCRIPTION = "API for analyzing chatbot message repetitions across different departments"
API_VERSION = "1.0.0"
API_HOST = "0.0.0.0"
API_PORT = 8000

# File paths - Service Account only
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "cred.json")  # Service account credentials

# Check if we have JSON credentials in environment variable
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS")
if GOOGLE_CREDENTIALS_JSON:
    # Use the JSON string directly
    SERVICE_ACCOUNT_FILE = GOOGLE_CREDENTIALS_JSON

# Tableau Configuration - All sensitive values moved to environment variables
TABLEAU_CONFIG = {
    "server_url": os.getenv("TABLEAU_SERVER_URL", "https://prod-uk-a.online.tableau.com"),
    "api_version": os.getenv("TABLEAU_API_VERSION", "3.16"),
    "token_name": os.getenv("TABLEAU_TOKEN_NAME"),
    "token_value": os.getenv("TABLEAU_TOKEN_VALUE"),
    "site_content_url": os.getenv("TABLEAU_SITE_CONTENT_URL"),
    "workbook_name": os.getenv("TABLEAU_WORKBOOK_NAME", "8 Department wise tables for chats & calls")
}

# Department Configuration - Spreadsheet IDs moved to environment variables
DEPARTMENT_CONFIG: Dict[str, Dict[str, Any]] = {
    "applicants": {
        "view_name": "Applicants",
        "skill_filter": "FILIPINA_OUTSIDE",
        "spreadsheet_id": os.getenv("APPLICANTS_SPREADSHEET_ID"),
        "output_file": "data/output/repetitions_applicants.csv",
        "cleaned_file": "data/temp/Applicants_cleaned_repetitions.csv",
        "raw_data_file": "data/temp/applicants_data.csv"
    },
    "doctors": {
        "view_name": "Doctors",
        "skill_filter": "GPT_Doctors",
        "spreadsheet_id": os.getenv("DOCTORS_SPREADSHEET_ID"),
        "output_file": "data/output/repetitions_doctors.csv",
        "cleaned_file": "data/temp/Doctors_cleaned_repetitions.csv",
        "raw_data_file": "data/temp/doctors_data.csv"
    },
    "mv_resolvers": {
        "view_name": "MV Resolvers",
        "skill_filter": "gpt_mv_resolvers",
        "spreadsheet_id": os.getenv("MV_RESOLVERS_SPREADSHEET_ID"),
        "output_file": "data/output/repetitions_mv_Raw.csv",
        "cleaned_file": "data/temp/MV_cleaned_repetitions.csv",
        "raw_data_file": "data/temp/mv_resolvers_data.csv"
    },
    "cc_sales": {
        "view_name": "Sales CC",
        "skill_filter": "GPT_CC_PROSPECT",
        "spreadsheet_id": os.getenv("CC_SALES_SPREADSHEET_ID"),
        "output_file": "data/output/repetitions_CC_Sale.csv",
        "cleaned_file": "data/temp/CC_Sale_cleaned_repetitions.csv",
        "raw_data_file": "data/temp/cc_sales_data.csv"
    }
}

# Google Sheets Configuration
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "formatter": "default",
            "class": "logging.FileHandler",
            "filename": "logs/api.log",
            "mode": "a",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["default", "file"],
    },
}

# Environment-specific settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    # Production settings
    API_HOST = "0.0.0.0"
    API_PORT = int(os.getenv("PORT", 8000))
    LOGGING_CONFIG["root"]["level"] = "INFO"

    # Service Account credentials are already handled above
elif ENVIRONMENT == "development":
    # Development settings
    API_HOST = "localhost"
    LOGGING_CONFIG["root"]["level"] = "DEBUG"

# Validation for required environment variables
def validate_required_env_vars():
    """Validate that all required environment variables are set"""
    required_vars = [
        "TABLEAU_TOKEN_NAME",
        "TABLEAU_TOKEN_VALUE",
        "TABLEAU_SITE_CONTENT_URL",
        "APPLICANTS_SPREADSHEET_ID",
        "DOCTORS_SPREADSHEET_ID",
        "MV_RESOLVERS_SPREADSHEET_ID",
        "CC_SALES_SPREADSHEET_ID"
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            f"Please set these environment variables before running the application."
        )

# Validate environment variables on import (only in production)
if ENVIRONMENT == "production":
    validate_required_env_vars()

# Create necessary directories
REQUIRED_DIRECTORIES = [
    "data/temp",
    "data/output",
    "data/archive",
    "logs",
    "config"
]
