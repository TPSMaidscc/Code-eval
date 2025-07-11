"""
Tableau data fetching service
"""

import requests
import urllib.parse
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta

from app.config import TABLEAU_CONFIG

logger = logging.getLogger(__name__)

class TableauService:
    """Service for fetching data from Tableau Server."""
    
    def __init__(self):
        self.server_url = TABLEAU_CONFIG["server_url"]
        self.api_version = TABLEAU_CONFIG["api_version"]
        self.token_name = TABLEAU_CONFIG["token_name"]
        self.token_value = TABLEAU_CONFIG["token_value"]
        self.site_content_url = TABLEAU_CONFIG["site_content_url"]
        self.workbook_name = TABLEAU_CONFIG["workbook_name"]
    
    def sign_in(self) -> Tuple[str, str]:
        """Authenticate via PAT and return token and site LUID."""
        logger.info("Authenticating with Tableau Server")
        
        url = f"{self.server_url}/api/{self.api_version}/auth/signin"
        payload = {
            "credentials": {
                "personalAccessTokenName": self.token_name,
                "personalAccessTokenSecret": self.token_value,
                "site": {"contentUrl": self.site_content_url}
            }
        }
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        resp = requests.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Sign-in failed (HTTP {resp.status_code}): {resp.text}")
        
        if 'application/json' not in resp.headers.get('Content-Type', ''):
            raise RuntimeError(f"Expected JSON sign-in response but got:\n{resp.headers.get('Content-Type')}\n{resp.text}")
        
        creds = resp.json()['credentials']
        logger.info("Successfully authenticated with Tableau Server")
        return creds['token'], creds['site']['id']
    
    def get_workbook_id(self, token: str, site_luid: str) -> str:
        """Retrieve the workbook LUID matching WORKBOOK_NAME."""
        logger.info(f"Searching for workbook: {self.workbook_name}")
        
        page_number = 1
        headers = {
            'X-Tableau-Auth': token,
            'Accept': 'application/json'
        }
        
        while True:
            logger.debug(f"Searching workbook page {page_number}")
            url = (
                f"{self.server_url}/api/{self.api_version}/sites/{site_luid}/workbooks"
                f"?pageSize=100&pageNumber={page_number}"
            )
            
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            
            data = resp.json()['workbooks']
            workbooks = data.get('workbook', [])
            
            for wb in workbooks:
                if wb['name'] == self.workbook_name:
                    logger.info(f"Found workbook: {self.workbook_name} (ID: {wb['id']})")
                    return wb['id']
            
            # Check if there are more pages
            if len(workbooks) < 100:
                break
            page_number += 1
        
        raise RuntimeError(f"Workbook '{self.workbook_name}' not found")
    
    def get_view_id(self, token: str, site_luid: str, workbook_id: str, view_name: str) -> str:
        """Retrieve the view LUID matching view_name."""
        logger.info(f"Searching for view: {view_name}")
        
        page_number = 1
        headers = {
            'X-Tableau-Auth': token,
            'Accept': 'application/json'
        }
        
        while True:
            logger.debug(f"Searching view page {page_number}")
            url = (
                f"{self.server_url}/api/{self.api_version}/sites/{site_luid}"
                f"/workbooks/{workbook_id}/views?pageSize=100&pageNumber={page_number}"
            )
            
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            
            data = resp.json()['views']
            views = data.get('view', [])
            
            for view in views:
                if view['name'] == view_name:
                    logger.info(f"Found view: {view_name} (ID: {view['id']})")
                    return view['id']
            
            # Check if there are more pages
            if len(views) < 100:
                break
            page_number += 1
        
        raise RuntimeError(f"View '{view_name}' not found in workbook")
    
    def download_csv(self, token: str, site_luid: str, view_id: str, 
                    start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
        """Download CSV text for the given view with optional date range filters."""
        logger.info("Downloading CSV data from Tableau view")
        
        url = f"{self.server_url}/api/{self.api_version}/sites/{site_luid}/views/{view_id}/data"
        headers = {
            'X-Tableau-Auth': token,
            'Accept': '*/*'
        }
        
        # Calculate previous day's date if not provided
        if not start_date or not end_date:
            yesterday = datetime.now() - timedelta(days=1)
            from_date = yesterday.strftime("%Y-%m-%d")
            to_date = yesterday.strftime("%Y-%m-%d")
        else:
            from_date = start_date
            to_date = end_date
        
        logger.info(f"Fetching data for date range: {from_date} to {to_date}")
        
        # Add filter parameters
        params = {
            'vf_From': urllib.parse.quote(from_date),
            'vf_To': urllib.parse.quote(to_date),
            'vf_ActionDate': urllib.parse.quote(from_date + ':' + to_date),
        }
        
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        
        logger.info("Successfully downloaded CSV data")
        return resp.text
    
    def sign_out(self, token: str) -> None:
        """Invalidate the auth token."""
        logger.debug("Signing out from Tableau Server")
        
        url = f"{self.server_url}/api/{self.api_version}/auth/signout"
        headers = {
            'X-Tableau-Auth': token,
            'Accept': 'application/json'
        }
        
        try:
            requests.post(url, headers=headers)
            logger.debug("Successfully signed out from Tableau Server")
        except Exception as e:
            logger.warning(f"Failed to sign out from Tableau Server: {e}")
    
    def fetch_data(self, view_name: str, csv_output_path: str, 
                  start_date: Optional[str] = None, end_date: Optional[str] = None) -> bool:
        """
        Fetch data from Tableau and save to CSV.
        
        Args:
            view_name: Name of the Tableau view to fetch
            csv_output_path: Path where to save the CSV file
            start_date: Start date for data filter (YYYY-MM-DD)
            end_date: End date for data filter (YYYY-MM-DD)
        
        Returns:
            True if successful, False otherwise
        """
        token = None
        try:
            logger.info(f"Starting data fetch for view: {view_name}")
            
            # Authenticate
            token, site_luid = self.sign_in()
            
            # Get workbook and view IDs
            workbook_id = self.get_workbook_id(token, site_luid)
            view_id = self.get_view_id(token, site_luid, workbook_id, view_name)
            
            # Download CSV data
            csv_data = self.download_csv(token, site_luid, view_id, start_date, end_date)
            
            # Clean up the data by replacing any problematic characters
            csv_data = csv_data.replace('â\x80¯', ' ')
            
            # Save to file
            with open(csv_output_path, 'w', encoding='utf-8-sig', newline='') as f:
                f.write(csv_data)
            
            logger.info(f"CSV successfully saved to {csv_output_path}")
            return True

        except Exception as e:
            logger.error(f"Error fetching data for view {view_name}: {e}")
            return False
        finally:
            if token:
                self.sign_out(token)

    def fetch_quality_data(self, output_file: str) -> bool:
        """
        Fetch quality rating data from the Quality view.

        Args:
            output_file: Path to save the CSV file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Fetching quality data from Tableau")

            # Sign in to get token and site LUID
            token, site_luid = self.sign_in()

            # Get workbook LUID
            workbook_luid = self.get_workbook_luid(token, site_luid)
            if not workbook_luid:
                logger.error("Failed to get workbook LUID for quality data")
                return False

            # Get view LUID for Quality view
            view_luid = self.get_view_luid(token, site_luid, workbook_luid, "Quality")
            if not view_luid:
                logger.error("Failed to get view LUID for Quality view")
                return False

            # Download the view data as CSV
            success = self.download_view_csv(token, site_luid, view_luid, output_file)

            if success:
                logger.info(f"Successfully downloaded quality data to {output_file}")
            else:
                logger.error("Failed to download quality data")

            return success

        except Exception as e:
            logger.error(f"Error fetching quality data: {e}")
            return False

    def fetch_quality_data(self, output_file: str) -> bool:
        """
        Fetch quality rating data from the Quality view.

        Args:
            output_file: Path to save the CSV file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Fetching quality data from Tableau")

            # Sign in to get token and site LUID
            token, site_luid = self.sign_in()

            # Get workbook LUID
            workbook_luid = self.get_workbook_luid(token, site_luid)
            if not workbook_luid:
                logger.error("Failed to get workbook LUID for quality data")
                return False

            # Get view LUID for Quality view
            view_luid = self.get_view_luid(token, site_luid, workbook_luid, "Quality")
            if not view_luid:
                logger.error("Failed to get view LUID for Quality view")
                return False

            # Download the view data as CSV
            success = self.download_view_csv(token, site_luid, view_luid, output_file)

            if success:
                logger.info(f"Successfully downloaded quality data to {output_file}")
            else:
                logger.error("Failed to download quality data")

            return success

        except Exception as e:
            logger.error(f"Error fetching quality data: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to fetch data for view {view_name}: {e}")
            return False
        finally:
            if token:
                self.sign_out(token)
