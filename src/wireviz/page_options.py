import logging
from dataclasses import asdict, dataclass, field, fields
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Tuple, Union

from wireviz.wv_colors import ColorOutputMode, SingleColor

from .wv_dataclasses import PlainText


@dataclass
class PageFormatOptions:
    show_bom: bool = True
    bom_updated_position: str = ""
    show_index_table: bool = True
    index_table_on_right: bool = True
    index_table_updated_position: str = ""
    show_notes: bool = True
    notes_on_right: bool = True
    notes_width: str = "100mm"


@dataclass
class DiagramColorOptions:
    bgcolor: SingleColor = "WH"  # will be converted to SingleColor in __post_init__
    bgcolor_node: SingleColor = "WH"
    bgcolor_connector: SingleColor = None
    bgcolor_cable: SingleColor = None
    bgcolor_bundle: SingleColor = None
    color_output_mode: ColorOutputMode = ColorOutputMode.EN_UPPER

    def __post_init__(self):
        self.bgcolor = SingleColor(self.bgcolor)
        self.bgcolor_node = SingleColor(self.bgcolor_node) or self.bgcolor
        self.bgcolor_connector = (
            SingleColor(self.bgcolor_connector) or self.bgcolor_node
        )
        self.bgcolor_cable = SingleColor(self.bgcolor_cable) or self.bgcolor_node
        self.bgcolor_bundle = SingleColor(self.bgcolor_bundle) or self.bgcolor_cable


@dataclass
class ComponentDimensions:
    bom_rows: int = 0
    titleblock_rows: int = 9
    bom_row_height: float = 4.25
    titleblock_row_height: float = 4.25
    index_table_row_height: float = 4.25

    def __post_init__(self):
        self.bom_rows = int(self.bom_rows)
        self.titleblock_rows = int(self.titleblock_rows)
        self.bom_row_height = float(self.bom_row_height)
        self.titleblock_row_height = float(self.titleblock_row_height)
        self.index_table_row_height = float(self.index_table_row_height)


# TODO: custom options for TitlePage, BOMPage, NotesPage, HarnessPage?
# TODO: have options tree instead of unwrapping?
@dataclass
class PageOptions(ComponentDimensions, PageFormatOptions, DiagramColorOptions):
    fontname: PlainText = "arial"
    mini_bom_mode: bool = True
    template_separator: str = "."
    for_pdf = False
    _pad: int = 0
    # TODO: resolve template and image paths during rendering, not during YAML parsing
    _template_paths: [List] = field(default_factory=list)
    _image_paths: [List] = field(default_factory=list)

    def __post_init__(self):
        DiagramColorOptions.__post_init__(self)
        ComponentDimensions.__post_init__(self)


def get_page_options(parsed_data, page_name: str):
    """Get the page options

    uses: the page\'s options   -> general options -> default options
        ('{page_name}_options') ->    ('options')  -> {}
    """
    page_options_name = f"{page_name}_options"
    if page_options_name in parsed_data:
        return PageOptions(**parsed_data[page_options_name])
    return PageOptions(**parsed_data.get("options", {}))
