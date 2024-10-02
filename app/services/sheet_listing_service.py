from flask import current_app

from app.services.data_processor import filter_data
from app.utils.google_utils.google_drive import list_files_in_folder

from app.utils.google_utils.google_sheets import get_sheet_data


def list_sheets():
    sheets = list_files_in_folder(current_app.config['GOOGLE_DRIVE_FOLDER_ID'])
    return [{
        'id': sheet['id'],
        'name': sheet['name'],
        'empty_by_the_way_count': _count_unprocessed_rows(sheet['id'])
    } for sheet in sheets]


def _count_unprocessed_rows(spreadsheet_id):
    new_connections_data = get_sheet_data(spreadsheet_id, 'New Connections', 'A:ZZ')

    if new_connections_data is None or len(new_connections_data) < 2:
        return 0

    headers = new_connections_data[0]
    processed_data = [dict(zip(headers, row + [''] * (len(headers) - len(row)))) for row in new_connections_data[1:]]
    filtered_data = filter_data(processed_data)

    return len(filtered_data)
