from app.services.sheet_listing_service import update_sheet_data
from app.utils.google_utils.google_sheets import update_specific_cells
from app.utils.file_manager import get_file_manager
from flask import Flask


def save_entry(data):
    sheet_id = data.get('sheet_id')
    row_number = data.get('row_number')
    entry_data = data.get('entry_data')
    username = data.get('username')

    result = update_specific_cells(sheet_id, 'New Connections', row_number, entry_data)

    file_manager = get_file_manager()
    file_manager.delete_all_files_by_user(username)

    # Update the unprocessed rows count in Redis cache
    new_count = update_sheet_data(sheet_id, row_number, entry_data)

    return {'success': True, 'updated_cells': result.get('updatedCells')}
