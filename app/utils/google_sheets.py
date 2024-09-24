from app.utils.google_auth import GoogleService

def sheet_exists(spreadsheet_id, sheet_name):
    service = GoogleService.get_instance().get_service('sheets', 'v4')
    
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get('sheets', '')
    for sheet in sheets:
        if sheet['properties']['title'] == sheet_name:
            return True
    return False

def get_sheet_names(spreadsheet_id):
    service = GoogleService.get_instance().get_service('sheets', 'v4')

    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get('sheets', '')
    return [sheet['properties']['title'] for sheet in sheets]

def get_sheet_data(spreadsheet_id, sheet_name='New Connections', range_name='A:ZZ'):
    if not sheet_exists(spreadsheet_id, sheet_name):
        return None
    
    service = GoogleService.get_instance().get_service('sheets', 'v4')
    
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, 
                                range=f"'{sheet_name}'!{range_name}").execute()
    
    return result.get('values', [])

def update_sheet_data(sheet_id, range_name, values):
    service = GoogleService.get_instance().get_service('sheets', 'v4')
    
    body = {'values': values}
    result = service.spreadsheets().values().update(
        spreadsheetId=sheet_id, range=range_name,
        valueInputOption='USER_ENTERED', body=body).execute()
    
    return result

def read_sheet_data(sheet_id, range_name='A1:Z'):
    service = GoogleService.get_instance().get_service('sheets', 'v4')
    
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute()
    values = result.get('values', [])
    
    return values