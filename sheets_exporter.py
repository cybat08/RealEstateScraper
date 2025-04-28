"""
Google Sheets Exporter Module

This module provides functions to export data to Google Sheets.
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import os
import tempfile
import time
from datetime import datetime

def create_credentials_file(credentials_json):
    """
    Create a temporary credentials file from JSON string
    
    Args:
        credentials_json (str): JSON string containing Google API credentials
        
    Returns:
        str: Path to the temporary credentials file
    """
    # Create a temporary file
    fd, path = tempfile.mkstemp(suffix='.json')
    
    # Write the credentials JSON to the file
    with os.fdopen(fd, 'w') as tmp:
        tmp.write(credentials_json)
    
    return path

def connect_to_sheets(credentials_path=None, credentials_json=None):
    """
    Connect to Google Sheets API
    
    Args:
        credentials_path (str, optional): Path to credentials JSON file
        credentials_json (str, optional): JSON string containing credentials
        
    Returns:
        gspread.Client: Authorized gspread client or None if failed
    """
    # Define the scope
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Handle temp file creation if JSON string provided
    temp_file_path = None
    if credentials_json and not credentials_path:
        try:
            temp_file_path = create_credentials_file(credentials_json)
            credentials_path = temp_file_path
        except Exception as e:
            print(f"Error creating credentials file: {e}")
            return None
    
    try:
        # Authorize with credentials
        credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        client = gspread.authorize(credentials)
        
        # Clean up temp file if created
        if temp_file_path:
            os.unlink(temp_file_path)
            
        return client
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        
        # Clean up temp file if created
        if temp_file_path:
            os.unlink(temp_file_path)
            
        return None

def export_dataframe_to_sheet(df, credentials_path=None, credentials_json=None, 
                              spreadsheet_name=None, spreadsheet_id=None, 
                              worksheet_name=None, append=False):
    """
    Export a pandas DataFrame to Google Sheets
    
    Args:
        df (pandas.DataFrame): DataFrame to export
        credentials_path (str, optional): Path to credentials JSON file
        credentials_json (str, optional): JSON string containing credentials
        spreadsheet_name (str, optional): Name for a new spreadsheet
        spreadsheet_id (str, optional): ID of existing spreadsheet
        worksheet_name (str, optional): Name of worksheet
        append (bool): Whether to append to existing data
        
    Returns:
        dict: Result information including urls and status
    """
    # Validate inputs
    if not credentials_path and not credentials_json:
        return {"success": False, "error": "No credentials provided"}
    
    if not spreadsheet_name and not spreadsheet_id:
        return {"success": False, "error": "Spreadsheet name or ID required"}
    
    # Connect to Google Sheets
    client = connect_to_sheets(credentials_path, credentials_json)
    if not client:
        return {"success": False, "error": "Failed to connect to Google Sheets"}
    
    try:
        # Get or create spreadsheet
        if spreadsheet_id:
            spreadsheet = client.open_by_key(spreadsheet_id)
        else:
            spreadsheet = client.create(spreadsheet_name or f"Data Export {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get or create worksheet
        if worksheet_name:
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=df.shape[0]+10, cols=df.shape[1]+5)
        else:
            # Use the first sheet
            worksheet = spreadsheet.sheet1
            
        # Get the values as a list of lists (2D array)
        values = [df.columns.tolist()] + df.values.tolist()
        
        if append and worksheet.get_all_values():
            # If appending, get all existing values, and add new ones
            existing_values = worksheet.get_all_values()
            headers = existing_values[0]
            
            # Check if headers match
            if headers != df.columns.tolist():
                # If headers don't match, just add to a new sheet
                worksheet = spreadsheet.add_worksheet(
                    title=f"{worksheet_name or 'Sheet'} {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    rows=df.shape[0]+10,
                    cols=df.shape[1]+5
                )
                worksheet.update('A1', values)
            else:
                # Add new rows (skipping headers)
                new_values = df.values.tolist()
                row_count = len(existing_values)
                worksheet.update(f'A{row_count+1}', new_values)
        else:
            # Replace all data
            worksheet.clear()
            worksheet.update('A1', values)
            
        # Format header row
        worksheet.format('1:1', {'textFormat': {'bold': True}})
        
        return {
            "success": True,
            "spreadsheet_id": spreadsheet.id,
            "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}",
            "spreadsheet_name": spreadsheet.title,
            "worksheet_name": worksheet.title
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_available_spreadsheets(credentials_path=None, credentials_json=None, max_results=10):
    """
    List available spreadsheets in Google Drive
    
    Args:
        credentials_path (str, optional): Path to credentials JSON file
        credentials_json (str, optional): JSON string containing credentials
        max_results (int): Maximum number of spreadsheets to return
        
    Returns:
        list: List of spreadsheet information dictionaries
    """
    client = connect_to_sheets(credentials_path, credentials_json)
    if not client:
        return []
    
    try:
        # Get all spreadsheets
        spreadsheets = client.openall()
        
        # Limit results
        spreadsheets = spreadsheets[:max_results]
        
        # Create list of spreadsheet info
        result = []
        for sheet in spreadsheets:
            result.append({
                "id": sheet.id,
                "title": sheet.title,
                "url": f"https://docs.google.com/spreadsheets/d/{sheet.id}",
                "worksheets": [ws.title for ws in sheet.worksheets()]
            })
            
        return result
    except Exception as e:
        print(f"Error listing spreadsheets: {e}")
        return []