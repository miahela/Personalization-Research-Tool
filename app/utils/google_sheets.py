from fontTools.subset.svg import ranges

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

def get_colored_cells(spreadsheet_id, sheet_name, range_name='A:ZZ'):
    EXCLUDED_VALUES = ['by the way', 'personalization date']
    service = GoogleService.get_instance().get_service('sheets', 'v4')

    # # Get the gridProperties to determine the number of rows and columns
    # sheet_metadata = service.spreadsheets().get(
    #     spreadsheetId=spreadsheet_id,
    #     fields='sheets.properties'
    # ).execute()
    #
    # sheet_id = None
    # num_rows = 0
    # num_cols = 0
    #
    # for sheet in sheet_metadata.get('sheets', ''):
    #     if sheet['properties']['title'] == sheet_name:
    #         sheet_id = sheet['properties']['sheetId']
    #         grid_props = sheet['properties'].get('gridProperties', {})
    #         num_rows = grid_props.get('rowCount', 1000)  # Default to 1000 if not specified
    #         num_cols = grid_props.get('columnCount', 26)  # Default to 26 if not specified
    #         break
    #
    # if not sheet_id:
    #     return []

    # Request cell data including formatting
    request = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        ranges=[f'{sheet_name}'],
        includeGridData=True,
        fields='sheets.data.rowData.values.userEnteredFormat.backgroundColor,sheets.data.rowData.values.formattedValue'
    )
    response = request.execute()

    colored_cells = []
    colored_cells_values = []

    for row_index, row in enumerate(response['sheets'][0]['data'][0]['rowData']):
        for col_index, cell in enumerate(row.get('values', [])):
            if 'userEnteredFormat' in cell and 'backgroundColor' in cell['userEnteredFormat']:
                bg_color = cell['userEnteredFormat']['backgroundColor']
                # Check if the background color is not white (1, 1, 1)
                if bg_color != {'red': 1, 'green': 1, 'blue': 1}:
                    value = cell.get('formattedValue', '')
                    if value.lower() in EXCLUDED_VALUES:
                        continue

                    colored_cells.append({
                        'row': row_index + 1,
                        'column': col_index + 1,
                        'value': value,
                        'color': bg_color
                    })
                    colored_cells_values.append(value)

    return colored_cells_values

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