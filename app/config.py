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

# Service Account credentials - JSON from GOOGLE_CREDENTIALS only
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS")

# Debug logging for environment variables
import logging
logger = logging.getLogger(__name__)

if GOOGLE_CREDENTIALS_JSON:
    # Use the JSON string from GOOGLE_CREDENTIALS
    logger.info("🔑 Found GOOGLE_CREDENTIALS environment variable")
    logger.info(f"📋 GOOGLE_CREDENTIALS (first 50 chars): {GOOGLE_CREDENTIALS_JSON[:50]}...")
    SERVICE_ACCOUNT_FILE = GOOGLE_CREDENTIALS_JSON
else:
    # Fallback to file path (for development)
    SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "cred.json")
    logger.info(f"📁 Using file path for Service Account: {SERVICE_ACCOUNT_FILE}")

logger.info(f"🎯 Final SERVICE_ACCOUNT_FILE (first 50 chars): {SERVICE_ACCOUNT_FILE[:50]}...")

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
        "skill_filter": ['gpt_filipina_outside', "GPT_MAIDSAT_FILIPINA_OUTSIDE","Filipina_Outside_Pending_Facephoto","Filipina_Outside_Pending_Passport","Filipina_Outside_Pending_Ticket","Filipina_Outside_Ticket_Booked"],
        "spreadsheet_id": os.getenv("APPLICANTS_SPREADSHEET_ID"),
        "output_file": "data/output/repetitions_applicants.csv",
        "cleaned_file": "data/temp/Applicants_cleaned_repetitions.csv",
        "raw_data_file": "data/temp/applicants_data.csv"
    },
    "doctors": {
        "view_name": "Doctors",
        "skill_filter": ['GPT_Doctors'],
        "spreadsheet_id": os.getenv("DOCTORS_SPREADSHEET_ID"),
        "output_file": "data/output/repetitions_doctors.csv",
        "cleaned_file": "data/temp/Doctors_cleaned_repetitions.csv",
        "raw_data_file": "data/temp/doctors_data.csv"
    },
    "mv_resolvers": {
        "view_name": "MV Department",  # MV Resolvers data is in the Applicants view
        "skill_filter": ['GPT_MV_RESOLVERS'],
        "spreadsheet_id": os.getenv("MV_RESOLVERS_SPREADSHEET_ID"),
        "output_file": "data/output/repetitions_mv_Raw.csv",
        "cleaned_file": "data/temp/MV_cleaned_repetitions.csv",
        "raw_data_file": "data/temp/mv_resolvers_data.csv"
    },
    "cc_sales": {
        "view_name": "Sales CC",
        "skill_filter": ['GPT_CC_PROSPECT'],
        "spreadsheet_id": os.getenv("CC_SALES_SPREADSHEET_ID"),
        "output_file": "data/output/repetitions_CC_Sale.csv",
        "cleaned_file": "data/temp/CC_Sale_cleaned_repetitions.csv",
        "raw_data_file": "data/temp/cc_sales_data.csv"
    },
     "cc_resolvers": {
        "view_name": "CC Department",
        "skill_filter": ['GPT_CC_RESOLVERS'],
        "spreadsheet_id": os.getenv("CC_RESOLVERS_SPREADSHEET_ID"),
        "output_file": "data/output/repetitions_CC_Resolvers.csv",
        "cleaned_file": "data/temp/CC_Resolvers_cleaned_repetitions.csv",
        "raw_data_file": "data/temp/CC_Resolvers_data.csv"
    },
      "delighters": {
        "view_name": "Delighters",
        "skill_filter": ['GPT_Delighters'],
        "spreadsheet_id": os.getenv("DELIGHTERS_SPREADSHEET_ID"),
        "output_file": "data/output/repetitions_Delighters.csv",
        "cleaned_file": "data/temp/Delighters_cleaned_repetitions.csv",
        "raw_data_file": "data/temp/Delighters_data.csv"
    },
        "mv_sales": {
        "view_name": "Sales MV",
        "skill_filter": ['GPT_MV_PROSPECT'],
        "spreadsheet_id": os.getenv("MV_SALES_SPREADSHEET_ID"),
        "output_file": "data/output/repetitions_MV_Sale.csv",
        "cleaned_file": "data/temp/MV_Sale_cleaned_repetitions.csv",
        "raw_data_file": "data/temp/MV_sales_data.csv"
    },
    
}

# Summary Spreadsheet IDs for combined analysis results
SUMMARY_SPREADSHEET_IDS = {
    "applicants": "1E5wHZKSDXQZlHIb3sV4ZWqIxvboLduzUEU0eupK7tys",
    "doctors": "1STHimb0IJ077iuBtTOwsa-GD8jStjU3SiBW7yBWom-E",
    "cc_sales": "1te1fbAXhURIUO0EzQ2Mrorv3a6GDtEVM_5np9TO775o",
    "mv_resolvers": "1XkVcHlkh8fEp7mmBD1Zkavdp2blBLwSABT1dE_sOf74",
    "cc_resolvers": "1QdmaTc5F2VUJ0Yu0kNF9d6ETnkMOlOgi18P7XlBSyHg",
    "delighters": "1PV0ZmobUYKHGZvHC7IfJ1t6HrJMTFi6YRbpISCouIfQ",
    "mv_sales": "1agrl9hlBhemXkiojuWKbqiMHKUzxGgos4JSkXxw7NAk"
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
        # Delays spreadsheet IDs are optional
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
