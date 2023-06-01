import logging
from dataclasses import dataclass, field, asdict, fields
from typing import Union, Dict, List, Tuple
from pathlib import Path
from enum import Enum

from wireviz.wv_templates import get_template
from wireviz.metadata import PagesMetadata
from wireviz.wv_harness_quantity import HarnessQuantity

TABLE_COLUMNS = ["sheet", "page", "quantity", "notes"]

@dataclass(frozen=True)
class IndexTableRow():
    sheet: int
    page: str
    quantity: Union[int, str] = 1
    notes: str = ''
    use_quantity: bool= True

    def get_items(self, for_pdf=False):
        if self.use_quantity:
            return (self.sheet, self.get_formatted_page(for_pdf), self.quantity, self.notes)
        else:
            return (self.sheet, self.get_formatted_page(for_pdf), self.notes)

    def get_formatted_page(self, for_pdf):
        if for_pdf:
            return self.page
        return f"<a href={Path(self.page).with_suffix('.html')}>{self.page}</a>"


@dataclass(frozen=True)
class IndexTable():
    rows: List[IndexTableRow]
    header: Tuple[str]

    @staticmethod
    def get_index_table_header(metadata: PagesMetadata = None):
        skip = []
        if metadata is not None and not metadata.use_qty_multipliers:
            skip.append('quantity')
        return (s.capitalize() for s in TABLE_COLUMNS if s not in skip)

    # TODO: how do we actually want to support this?
    @classmethod
    def from_pages_metadata(cls, metadata: PagesMetadata):
        header = cls.get_index_table_header(metadata)
        rows = []
        qty_multipliers = None
        if metadata.use_qty_multipliers:
            harnesses = HarnessQuantity(
                metadata.files,
                metadata.multiplier_file_name,
                output_dir=metadata.output_dir
            )
            harnesses.fetch_qty_multipliers_from_file()
            qty_multipliers = harnesses.multipliers

        for index, row in enumerate(metadata.output_names):
            if str(row) == 'titlepage':
                rows.append(IndexTableRow(sheet=1, page=metadata.titlepage, quantity='', notes=''))
                continue
            quantity = qty_multipliers[row] if qty_multipliers is not None else 1
            rows.append(IndexTableRow(
                sheet=index+2,
                page=row,
                quantity=quantity,
                notes=metadata.pages_notes.get(row, ''),
                use_quantity=metadata.use_qty_multipliers,
            ))
        return cls(rows=rows, header=header)


    def render(self, options):
        return get_template("index_table.html").render({
            "index_table": self,
            "options": options,
        })




