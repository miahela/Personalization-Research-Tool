from app.utils.google_auth import GoogleService
from app.utils.google_sheets import read_sheet_data


def list_files_in_folder(folder_id):
    service = GoogleService.get_instance().get_service('drive', 'v3')

    results = service.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'",
        fields="files(id, name)").execute()

    return results.get('files', [])


def list_sheets_in_folder(folder_id):
    service = GoogleService.get_instance().get_service('drive', 'v3')

    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'"
    results = service.files().list(q=query,
                                   fields="nextPageToken, files(id, name)").execute()
    sheets = results.get('files', [])

    return sheets


def process_sheets_in_folder(folder_id):
    sheets = list_sheets_in_folder(folder_id)
    all_data = {}

    for sheet in sheets:
        sheet_id = sheet['id']
        sheet_name = sheet['name']
        data = read_sheet_data(sheet_id)
        all_data[sheet_name] = data

    return all_data
