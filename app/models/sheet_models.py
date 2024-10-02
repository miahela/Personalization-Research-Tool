from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class SheetRow(BaseModel):
    row_number: int
    data: Dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def update(self, new_data: Dict[str, Any]):
        self.data.update(new_data)


class SheetData(BaseModel):
    headers: List[str]
    rows: List[SheetRow]
    colored_cells: List[str] = Field(default_factory=list)

    def get_row(self, row_number: int) -> Optional[SheetRow]:
        return next((row for row in self.rows if row.row_number == row_number), None)

    def update_row(self, row_number: int, new_data: Dict[str, Any]):
        row = self.get_row(row_number)
        if row:
            row.update(new_data)

    @classmethod
    def from_list(cls, data: List[List[Any]], colored_cells: List[str] = None) -> 'SheetData':
        if not data or len(data) < 2:
            return cls(headers=[], rows=[], colored_cells=colored_cells or [])

        headers = data[0]
        rows = [
            SheetRow(row_number=i, data=dict(zip(headers, row)))
            for i, row in enumerate(data[1:], start=1)
        ]
        return cls(headers=headers, rows=rows, colored_cells=colored_cells or [])


class SpreadsheetData(BaseModel):
    id: str
    new_connections: SheetData
    pq_data: SheetData
