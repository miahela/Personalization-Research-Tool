from googleapiclient.discovery import build
from app.utils.google_auth import get_credentials

def list_files_in_folder(folder_id):
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)
    
    results = service.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'",
        fields="files(id, name)").execute()
    
    return results.get('files', []) 