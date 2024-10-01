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
        if row_index != 0:
            break

        for col_index, cell in enumerate(row.get('values', [])):
            if 'userEnteredFormat' in cell and 'backgroundColor' in cell['userEnteredFormat']:
                bg_color = cell['userEnteredFormat']['backgroundColor']
                # Check if the background color is not white (1, 1, 1)
                if bg_color != {'red': 1, 'green': 1, 'blue': 1}:
                    value = cell.get('formattedValue', '')
                    if value.lower() in EXCLUDED_VALUES or value == '':
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

    values = result.get('values', [])

    # Add row numbers to the data
    numbered_values = [['row_number'] + values[0]]  # Add 'row_number' to headers
    numbered_values.extend([[i + 1] + row for i, row in enumerate(values[1:])])

    return numbered_values


def column_number_to_letter(column_number):
    """
    Convert a column number to a column letter (A, B, C, ..., Z, AA, AB, ...).

    :param column_number: The column number (1-indexed)
    :return: The corresponding column letter(s)
    """
    column_letter = ''
    while column_number > 0:
        column_number, remainder = divmod(column_number - 1, 26)
        column_letter = chr(65 + remainder) + column_letter
    return column_letter


def update_specific_cells(spreadsheet_id, sheet_name, row_number, updates):
    """
    Update specific cells in a given row of a Google Spreadsheet.

    :param spreadsheet_id: ID of the Google Spreadsheet
    :param sheet_name: Name of the sheet within the spreadsheet
    :param row_number: The row number to update (1-indexed)
    :param updates: A dictionary where keys are column names and values are the new cell values
    """
    service = GoogleService.get_instance().get_service('sheets', 'v4')

    # First, get the header row to map column names to column letters
    header_range = f"'{sheet_name}'!1:1"
    header_result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=header_range).execute()
    header = header_result.get('values', [[]])[0]

    # Create a list of updates
    batch_updates = []
    for column_name, new_value in updates.items():
        if column_name in header:
            column_index = header.index(column_name)
            column_letter = column_number_to_letter(column_index + 1)
            cell_range = f"'{sheet_name}'!{column_letter}{row_number}"

            batch_updates.append({
                'range': cell_range,
                'values': [[new_value]]
            })

    # Execute the batch update
    if batch_updates:
        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': batch_updates
        }
        result = service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body).execute()
        return result
    else:
        return None


def read_sheet_data(sheet_id, range_name='A1:Z'):
    service = GoogleService.get_instance().get_service('sheets', 'v4')

    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute()
    values = result.get('values', [])

    return values
