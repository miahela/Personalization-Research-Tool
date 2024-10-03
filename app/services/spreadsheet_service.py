from typing import List, Optional
from datetime import timedelta

from flask import current_app

from app.models import SpreadsheetData, SheetData, PqKeywords, SheetRow
from app.utils.google_utils.google_drive import list_files_in_folder
from app.utils.google_utils.google_sheets import fetch_sheet_names_from_google, fetch_sheet_data_from_google, \
    fetch_colored_cells_from_google, update_sheet_rows
from app.utils.redis_cache import RedisCache


class SpreadsheetService:
    _instance = None
    CACHE_EXPIRY = timedelta(hours=1)  # Set cache expiry to 1 hour

    def __init__(self):
        self.cache = RedisCache.get_instance()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_spreadsheet(self, spreadsheet_id: str, name='') -> Optional[SpreadsheetData]:
        # Try to get the entire spreadsheet data from cache
        cache_key = f"spreadsheet:{spreadsheet_id}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return SpreadsheetData.model_validate(cached_data)

        # If not in cache, fetch from Google Sheets
        new_connections_data = self.get_sheet_data(spreadsheet_id, 'New Connections', 'A:ZZ')
        all_pq_sheets = self.get_all_sheets_that_match_name(spreadsheet_id, 'pq')
        pq_data = SheetData(headers=all_pq_sheets[0].headers,
                            rows=[row for sheet in all_pq_sheets for row in sheet.rows]) if all_pq_sheets else None
        keywords = self._load_keywords(spreadsheet_id, pq_data)

        if new_connections_data:
            spreadsheet_data = SpreadsheetData(
                id=spreadsheet_id,
                name=name,
                new_connections=new_connections_data,
                pq_data=pq_data,
                keywords=keywords,
            )
            self._cache_spreadsheet_data(spreadsheet_data)
            return spreadsheet_data

        return None

    def get_sheet_data(self, spreadsheet_id: str, sheet_name: str, sheet_range: str) -> Optional[SheetData]:
        cache_key = f"sheet_data:{spreadsheet_id}:{sheet_name}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return SheetData.model_validate(cached_data)

        sheet_data = fetch_sheet_data_from_google(spreadsheet_id, sheet_name, sheet_range)
        if sheet_data:
            sheet_data_model = SheetData.from_list(sheet_data)
            if sheet_name == 'New Connections':
                colored_cells = fetch_colored_cells_from_google(spreadsheet_id, sheet_name)
                sheet_data_model.colored_cells = colored_cells
            self.cache.set(cache_key, sheet_data_model.model_dump(), expire=self.CACHE_EXPIRY)
            return sheet_data_model

        return None

    def get_all_sheets_that_match_name(self, spreadsheet_id: str, sheet_name: str) -> List[SheetData]:
        cache_key = f"spreadsheet_sheets:{spreadsheet_id}"

        # Try to get the list of sheet names from cache
        all_sheets = self.cache.get(cache_key)

        if not all_sheets:
            # If not in cache, fetch from Google Sheets
            all_sheets = fetch_sheet_names_from_google(spreadsheet_id)
            # Cache the list of sheet names
            self.cache.set(cache_key, all_sheets, expire=self.CACHE_EXPIRY)

        matching_sheets = [name for name in all_sheets if sheet_name.lower().strip() in name.lower().strip()]
        result = []
        for name in matching_sheets:
            sheet_data = self.get_sheet_data(spreadsheet_id, name, 'A:ZZ')
            if sheet_data:
                result.append(sheet_data)

        return result

    def update_row(self, spreadsheet_id: str, sheet_name: str, row_number: int, new_data: dict):
        update_sheet_rows(spreadsheet_id, sheet_name, row_number, new_data)
        self._update_sheet_row_cache(spreadsheet_id, sheet_name, row_number, new_data)

    def get_all_spreadsheets_in_drive(self) -> List[SpreadsheetData]:
        all_files = list_files_in_folder(current_app.config['GOOGLE_DRIVE_FOLDER_ID'])
        return [self.get_spreadsheet(file['id'], file['name']) for file in all_files if
                self.get_spreadsheet(file['id'], file['name'])]

    def _load_keywords(self, spreadsheet_id: str, pq_data: Optional[SheetData]) -> PqKeywords:
        cache_key = f"keywords:{spreadsheet_id}"
        cached_keywords = self.cache.get(cache_key)
        if cached_keywords:
            return PqKeywords.model_validate(cached_keywords)

        if not pq_data:
            return PqKeywords(titles=[], seniority=[], negative_keywords=[])

        titles = []
        seniorities = []
        negative_keywords = []
        for row in pq_data.rows:
            title = row.get('Titles', '')
            seniority = row.get('Seniority', '')
            negative = row.get('Negative', '')

            if title and title not in titles:
                titles.append(title)
            if seniority and seniority not in seniorities:
                seniorities.append(seniority)
            if negative and negative not in negative_keywords:
                negative_keywords.append(negative)

        keywords = PqKeywords(titles=titles, seniority=seniorities, negative_keywords=negative_keywords)
        self.cache.set(cache_key, keywords.model_dump(), expire=self.CACHE_EXPIRY)
        return keywords

    def _cache_spreadsheet_data(self, spreadsheet_data: SpreadsheetData):
        cache_key = f"spreadsheet:{spreadsheet_data.id}"
        self.cache.set(cache_key, spreadsheet_data.model_dump(), expire=self.CACHE_EXPIRY)

    def _update_sheet_row_cache(self, spreadsheet_id: str, sheet_name: str, row_number: int, new_data: dict):
        cache_key = f"sheet_data:{spreadsheet_id}:{sheet_name}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            sheet_data = SheetData.model_validate(cached_data)
            for row in sheet_data.rows:
                if row.row_number == row_number:
                    row.update(new_data)
                    break
            self.cache.set(cache_key, sheet_data.model_dump(), expire=self.CACHE_EXPIRY)

    @staticmethod
    def calculate_unprocessed_rows_in_sheet(sheet: SheetData) -> List[SheetRow]:
        return [
            row for row in sheet.rows
            if not row.get('by the way', '').strip() and not row.get('approved', '').strip()
        ]
