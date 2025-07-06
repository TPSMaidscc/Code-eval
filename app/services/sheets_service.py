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
        logger.info("Using Service Account authentication")
        logger.info(f"Credentials source (first 50 chars): {self.credentials_file[:50]}...")
        logger.info(f"Credentials type check - starts with '{{': {self.credentials_file.strip().startswith('{') if self.credentials_file else False}")

        # Check if credentials_file is a JSON string or file path
        if self.credentials_file and self.credentials_file.strip().startswith('{'):
            # It's a JSON string from environment variable
            logger.info("Detected JSON string - Loading Service Account from environment variable")
            try:
                # Clean up any potential JSON formatting issues
                cleaned_json = self.credentials_file.strip()
                # Fix common JSON syntax errors (semicolons instead of colons)
                cleaned_json = cleaned_json.replace('";:', '":').replace("';:", "':")

                logger.info(f"Cleaned JSON (first 100 chars): {cleaned_json[:100]}...")
                service_account_info = json.loads(cleaned_json)
                logger.info(f"JSON parsed successfully - Project ID: {service_account_info.get('project_id', 'unknown')}")
                logger.info(f"Service Account Email: {service_account_info.get('client_email', 'unknown')}")

                creds = ServiceAccountCredentials.from_service_account_info(
                    service_account_info, scopes=GOOGLE_SCOPES
                )
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in credentials: {e}")
                logger.error(f"JSON content (first 200 chars): {self.credentials_file[:200]}...")
                raise ValueError(f"Invalid JSON in Service Account credentials: {e}")
            except Exception as e:
                logger.error(f"Error creating credentials from JSON: {e}")
                raise
        else:
            # It's a file path
            logger.info(f"Detected file path - Loading Service Account from file: {self.credentials_file}")
            if not os.path.exists(self.credentials_file):
                logger.error(f"Service account file not found: {self.credentials_file}")
                raise FileNotFoundError(f"Service account key file not found: {self.credentials_file}")

            creds = ServiceAccountCredentials.from_service_account_file(
                self.credentials_file, scopes=GOOGLE_SCOPES
            )

        logger.info("Service Account authentication successful")
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

    def create_summary_sheet(self, spreadsheet_id: str, sheet_name: str, summary_data: dict) -> bool:
        """
        Create and populate a summary sheet with analysis results.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the worksheet to create/update (format: YYYY-MM-DD)
            summary_data: Dictionary containing analysis results

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Creating summary sheet '{sheet_name}' with analysis data")

            # Open spreadsheet
            sh = self.gc.open_by_key(spreadsheet_id)

            # Try to find existing worksheet or create new one
            try:
                ws = sh.worksheet(sheet_name)
                logger.info(f"Worksheet '{sheet_name}' found, clearing contents")
                ws.clear()
            except gspread.exceptions.WorksheetNotFound:
                logger.info(f"Worksheet '{sheet_name}' not found, creating new worksheet")
                try:
                    ws = sh.add_worksheet(title=sheet_name, rows=25, cols=2)  # 25 rows for all metrics
                    logger.info(f"New worksheet '{sheet_name}' created successfully")
                except gspread.exceptions.APIError as e:
                    if e.response.status_code == 403:
                        logger.warning(f"Permission denied creating worksheet. Using first available worksheet.")
                        ws = sh.get_worksheet(0)
                        ws.clear()
                        logger.info(f"Using existing worksheet: '{ws.title}'")
                    else:
                        raise e

            # Define the metrics headers in Column A
            metrics_headers = [
                ["Metric Name", "Values"],  # Header row
                ["META Quality", ""],
                ["LLM Model used", ""],
                ["Cost", ""],
                ["7-day CVR %", ""],
                ["Total Number of Chats", summary_data.get('total_conversations', '')],
                ["Handling %", ""],
                ["Agent intervention %", ""],
                ["Repetition %", summary_data.get('repetition_percentage', '')],
                ["Avg Delay - Initial msg", summary_data.get('avg_delay_initial', '')],
                ["Avg Delay - non-initial msg", summary_data.get('avg_delay_subsequent', '')],
                ["% Engagement for closing & filler", ""],
                ["Loss of interest", ""],
                ["Rule Breaking", ""],
                ["Sentiment Analysis", ""],
                ["Transfers due to escalations", ""],
                ["Transfers due to known flows", ""],
                ["Wrong tool called", ""],
                ["Missed to be called", ""],
                ["Missing policy", ""],
                ["Unclear policy", ""],
                ["% chats shadowed", ""],
                ["Reported issue", ""]
            ]

            # Upload the data to the worksheet
            ws.update('A1:B23', metrics_headers)
            logger.info(f"Summary data uploaded successfully to '{sheet_name}'")

            return True

        except Exception as e:
            logger.error(f"Failed to create summary sheet: {e}")
            return False

def get_sheets_service() -> GoogleSheetsService:
    """
    Get Google Sheets service using Service Account authentication.

    Returns:
        GoogleSheetsService instance
    """
    logger.info("Getting Google Sheets service")
    logger.info(f"SERVICE_ACCOUNT_FILE (first 50 chars): {SERVICE_ACCOUNT_FILE[:50]}...")

    # SERVICE_ACCOUNT_FILE can be either a JSON string or file path
    if SERVICE_ACCOUNT_FILE:
        return GoogleSheetsService(SERVICE_ACCOUNT_FILE)
    else:
        raise ValueError("No Service Account credentials found. Set GOOGLE_CREDENTIALS environment variable.")
