import logging
from dataclasses import dataclass, field, asdict, fields
from typing import Union, Dict, List, Tuple
from pathlib import Path
from enum import Enum

from wireviz.wv_templates import get_template
from wireviz.metadata import PagesMetadata

TABLE_COLUMNS = ["sheet", "page", "notes"]

@dataclass(frozen=True)
class IndexTableRow():
    sheet: int
    page: str
    notes: str = ''

    def get_items(self, for_pdf=False):
        return (self.sheet, self.get_formatted_page(for_pdf), self.notes)

    def get_formatted_page(self, for_pdf):
        if for_pdf:
            return self.page
        return f"<a href={Path(self.page).with_suffix('.html')}>{self.page}</a>"


def get_index_table_header():
    return (s.capitalize() for s in TABLE_COLUMNS)


@dataclass(frozen=True)
class IndexTable():
    rows: List[IndexTableRow]
    header: Tuple[str] = get_index_table_header()

    # TODO: how do we actually want to support this?
    @classmethod
    def from_pages_metadata(cls, metadata: PagesMetadata):
        rows = []
        rows.append(IndexTableRow(sheet=1, page=metadata.titlepage, notes=''))
        for index, row in enumerate(metadata.output_names):
            rows.append(IndexTableRow(
                sheet=index+2,
                page=row,
                notes=metadata.pages_notes.get(row, ''),
            ))
        return cls(rows=rows)

    def render(self, options):
        return get_template("index_table.html").render({
            "index_table": self,
            "options": options,
        })




