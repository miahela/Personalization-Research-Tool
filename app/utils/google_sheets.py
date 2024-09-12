from googleapiclient.discovery import build
from app.utils.google_auth import get_credentials

def get_sheet_data(sheet_id, range_name):
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)
    
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute()
    
    return result.get('values', [])

def update_sheet_data(sheet_id, range_name, values):
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)
    
    body = {'values': values}
    result = service.spreadsheets().values().update(
        spreadsheetId=sheet_id, range=range_name,
        valueInputOption='USER_ENTERED', body=body).execute()
    
    return result