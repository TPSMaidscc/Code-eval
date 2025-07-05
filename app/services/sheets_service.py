"""
Google Sheets upload service
"""

import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
import pandas as pd
import os
import pickle
import logging
from typing import Optional

from app.config import GOOGLE_SCOPES, CREDENTIALS_FILE, SERVICE_ACCOUNT_FILE

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    """Service for uploading data to Google Sheets."""
    
    def __init__(self, credentials_file: str, use_service_account: bool = False):
        self.credentials_file = credentials_file
        self.use_service_account = use_service_account
        self.gc = self._get_gspread_client()
    
    def _get_gspread_client(self):
        """Get authenticated gspread client."""
        if self.use_service_account:
            return self._get_service_account_client()
        else:
            return self._get_oauth_client()
    
    def _get_service_account_client(self):
        """Get gspread client using Service Account authentication."""
        logger.info(f"Using Service Account authentication from {self.credentials_file}")
        
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(f"Service account key file not found: {self.credentials_file}")
        
        creds = ServiceAccountCredentials.from_service_account_file(
            self.credentials_file, scopes=GOOGLE_SCOPES
        )
        
        logger.info("Service Account authentication successful")
        return gspread.authorize(creds)
    
    def _get_oauth_client(self):
        """Get gspread client using OAuth authentication with automatic refresh."""
        creds = None
        token_pickle = self.credentials_file.replace('.json', '_token.pickle')

        # Try to load existing credentials
        if os.path.exists(token_pickle):
            logger.info(f"Loading stored OAuth credentials from {token_pickle}")
            try:
                with open(token_pickle, 'rb') as token:
                    creds = pickle.load(token)
                logger.info("Successfully loaded stored credentials")
            except Exception as e:
                logger.warning(f"Failed to load stored credentials: {e}")
                creds = None

        # Check if credentials are valid or can be refreshed
        if creds:
            if creds.valid:
                logger.info("Stored credentials are still valid")
            elif creds.expired and creds.refresh_token:
                logger.info("Credentials expired, attempting automatic refresh...")
                try:
                    creds.refresh(Request())
                    # Save refreshed credentials immediately
                    with open(token_pickle, 'wb') as token:
                        pickle.dump(creds, token)
                    logger.info("✅ OAuth credentials refreshed automatically - no manual login needed!")
                except Exception as e:
                    logger.warning(f"Failed to refresh credentials: {e}")
                    logger.info("Refresh token may be expired, starting new OAuth flow")
                    creds = None
            else:
                logger.warning("Credentials expired and no refresh token available")
                creds = None

        # If no valid credentials, start OAuth flow
        if not creds or not creds.valid:
            logger.info("Starting OAuth flow - browser will open for one-time authentication")
            creds = self._run_oauth_flow(token_pickle)

        logger.info("✅ OAuth authentication successful")
        return gspread.authorize(creds)
    
    def _run_oauth_flow(self, token_pickle: str):
        """Run OAuth flow and save credentials with refresh token."""
        logger.info("🔐 Starting OAuth authentication flow...")
        logger.info("📝 Please sign in with your COMPANY EMAIL when the browser opens")

        flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, GOOGLE_SCOPES)

        # Ensure we get a refresh token by forcing approval prompt
        flow.redirect_uri = flow._OOB_REDIRECT_URI if hasattr(flow, '_OOB_REDIRECT_URI') else 'urn:ietf:wg:oauth:2.0:oob'

        # Run the flow with access_type=offline to get refresh token
        creds = flow.run_local_server(
            port=0,
            access_type='offline',
            prompt='consent'  # Force consent to ensure refresh token
        )

        # Verify we got a refresh token
        if creds.refresh_token:
            logger.info("✅ Successfully obtained refresh token for automatic future authentication")
        else:
            logger.warning("⚠️ No refresh token received - you may need to authenticate again later")

        # Save credentials
        with open(token_pickle, 'wb') as token:
            pickle.dump(creds, token)
        logger.info(f"💾 Saved OAuth credentials to {token_pickle}")
        logger.info("🎉 One-time authentication complete! Future runs will be automatic.")

        return creds
    
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

def get_sheets_service(use_service_account: Optional[bool] = False) -> GoogleSheetsService:
    """
    Get Google Sheets service with automatic authentication method detection.

    Args:
        use_service_account: Force service account usage. If None, auto-detect.

    Returns:
        GoogleSheetsService instance
    """
    # Use OAuth with stored refresh tokens for company domain compliance
    if not use_service_account:
        logger.info("Using OAuth authentication with stored refresh tokens")
        if os.path.exists(CREDENTIALS_FILE):
            return GoogleSheetsService(CREDENTIALS_FILE, use_service_account=False)
        else:
            raise FileNotFoundError(f"OAuth credentials file not found: {CREDENTIALS_FILE}")
    else:
        # Service Account (only if explicitly requested)
        logger.info("Using Service Account authentication")
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            return GoogleSheetsService(SERVICE_ACCOUNT_FILE, use_service_account=True)
        else:
            raise FileNotFoundError(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")
