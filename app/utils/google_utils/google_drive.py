from app.utils.google_utils.google_auth import GoogleService


def list_files_in_folder(folder_id):
    service = GoogleService.get_instance().get_service('drive', 'v3')

    results = service.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'",
        fields="files(id, name)").execute()

    return results.get('files', [])
