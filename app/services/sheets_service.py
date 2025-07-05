"""
Google Sheets upload service - Service Account only
"""

import gspread
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
import pandas as pd
import os
import json
import logging

from app.config import GOOGLE_SCOPES, SERVICE_ACCOUNT_FILE

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    """Service for uploading data to Google Sheets using Service Account authentication."""

    def __init__(self, credentials_file: str):
        self.credentials_file = credentials_file
        self.gc = self._get_gspread_client()

    def _get_gspread_client(self):
        """Get authenticated gspread client using Service Account."""
        logger.info(f"Using Service Account authentication")

        # Check if credentials_file is a JSON string or file path
        if self.credentials_file.strip().startswith('{'):
            # It's a JSON string from environment variable
            logger.info("Loading Service Account from environment variable JSON")
            try:
                service_account_info = json.loads(self.credentials_file)
                creds = ServiceAccountCredentials.from_service_account_info(
                    service_account_info, scopes=GOOGLE_SCOPES
                )
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in GOOGLE_CREDENTIALS environment variable: {e}")
        else:
            # It's a file path
            logger.info(f"Loading Service Account from file: {self.credentials_file}")
            if not os.path.exists(self.credentials_file):
                raise FileNotFoundError(f"Service account key file not found: {self.credentials_file}")

            creds = ServiceAccountCredentials.from_service_account_file(
                self.credentials_file, scopes=GOOGLE_SCOPES
            )

        logger.info("✅ Service Account authentication successful")
        return gspread.authorize(creds)

    
    def upload_csv_to_sheet(self, spreadsheet_id: str, csv_path: str, sheet_name: str) -> bool:
        """
        Upload CSV data to Google Sheets.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            csv_path: Path to CSV file to upload
            sheet_name: Name of the worksheet to create/update
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Uploading {csv_path} to sheet '{sheet_name}'")
            
            # Open spreadsheet
            sh = self.gc.open_by_key(spreadsheet_id)
            
            # Read CSV data
            df = pd.read_csv(csv_path)
            df = df.fillna("")  # Replace NaN with empty string
            
            # Try to find existing worksheet
            try:
                ws = sh.worksheet(sheet_name)
                logger.info(f"Worksheet '{sheet_name}' found, clearing contents")
                ws.clear()
            except gspread.exceptions.WorksheetNotFound:
                logger.info(f"Worksheet '{sheet_name}' not found, trying to create new worksheet")
                try:
                    ws = sh.add_worksheet(title=sheet_name, rows=str(len(df)+1), cols=str(len(df.columns)))
                    logger.info(f"New worksheet '{sheet_name}' created successfully")
                except gspread.exceptions.APIError as e:
                    if e.response.status_code == 403:
                        logger.warning(f"Permission denied creating worksheet. Using first available worksheet.")
                        # Use the first worksheet if we can't create a new one
                        ws = sh.get_worksheet(0)
                        ws.clear()
                        logger.info(f"Using existing worksheet: '{ws.title}'")
                    else:
                        raise e
            
            # Prepare data for upload
            data = [df.columns.tolist()] + df.values.tolist()
            
            # Upload data
            ws.update(data)
            logger.info(f"Data uploaded successfully to '{sheet_name}'")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload data to Google Sheets: {e}")
            return False

def get_sheets_service() -> GoogleSheetsService:
    """
    Get Google Sheets service using Service Account authentication.

    Returns:
        GoogleSheetsService instance
    """
    logger.info("Using Service Account authentication")
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        return GoogleSheetsService(SERVICE_ACCOUNT_FILE)
    else:
        raise FileNotFoundError(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")
