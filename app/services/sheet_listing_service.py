import logging
from turtledemo.penrose import start

from flask import current_app
from app.services.data_processor import filter_unprocessed_rows
from app.utils.google_utils.google_drive import list_files_in_folder
from app.utils.google_utils.google_sheets import fetch_sheet_data_from_google, fetch_colored_cells_from_google
from app.utils.redis_cache import get_redis_cache
from app.models.sheet_models import SheetData
import time


def get_all_spreadsheets_in_drive():
    start_time = time.time()
    sheets = list_files_in_folder(current_app.config['GOOGLE_DRIVE_FOLDER_ID'])
    print("--- List Files in %s seconds ---" % (time.time() - start_time))
    all_sheets = []
    new_time = time.time()
    for sheet in sheets:
        new_sheet = {
            'id': sheet['id'],
            'name': sheet['name'],
            'empty_by_the_way_count': _get_unprocessed_rows_count(sheet['id'])
        }
        all_sheets.append(new_sheet)
    print("--- Get Unprocessed Rows Count in %s seconds ---" % (time.time() - new_time))
    return all_sheets


def _get_unprocessed_rows_count(spreadsheet_id: str) -> int:
    sheet_data = get_or_fetch_sheet_data(spreadsheet_id)
    if not sheet_data or len(sheet_data.rows) == 0:
        return 0

    filtered_data = filter_unprocessed_rows([row for row in sheet_data.rows])
    return len(filtered_data)


def get_or_fetch_sheet_data(spreadsheet_id: str, sheet_name: str = 'New Connections',
                            sheet_range: str = 'A:ZZ') -> SheetData | None:
    redis_cache = get_redis_cache()
    cache_key = f"sheet_data:{spreadsheet_id}+{sheet_name}"

    # Try to get the data from cache
    cached_data = redis_cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    # If not in cache, fetch the data
    sheet_data = fetch_sheet_data_from_google(spreadsheet_id, sheet_name, sheet_range)

    # Store the data in cache
    if sheet_data:
        sheet_data_model = SheetData.from_list(sheet_data)
        if sheet_name == 'New Connections':
            colored_cells = fetch_colored_cells_from_google(spreadsheet_id, sheet_name)
            sheet_data_model.colored_cells = colored_cells
        redis_cache.set(cache_key, sheet_data_model)
        return sheet_data_model

    return None


def update_sheet_data(spreadsheet_id: str, row_number: int, entry_data: dict,
                      sheet_name: str = 'New Connections') -> int:
    redis_cache = get_redis_cache()
    cache_key = f"sheet_data:{spreadsheet_id}+{sheet_name}"

    sheet_data = redis_cache.get(cache_key)

    if sheet_data:
        # Update the specific row in the cached data
        sheet_data.update_row(row_number, entry_data)

        success = redis_cache.set(cache_key, sheet_data)
        if not success:
            logging.error(f"Failed to update Redis cache for key: {cache_key}")

    # Recalculate the unprocessed rows count
    new_count = _get_unprocessed_rows_count(spreadsheet_id)

    return new_count
