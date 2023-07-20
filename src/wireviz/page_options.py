import logging
from dataclasses import dataclass, field, asdict, fields
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Tuple, Union

from .wv_dataclasses import PlainText
from wireviz.wv_colors import (
    ColorOutputMode,
    SingleColor,
)


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
class DiagramColorOpions:
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

# TODO: custom options for TitlePage, BOMPage, NotesPage, HarnessPage?
# TODO: have options tree instead of unwrapping?
@dataclass
class PageOptions(ComponentDimensions, PageFormatOptions, DiagramColorOpions):
    fontname: PlainText = "arial"
    mini_bom_mode: bool = True
    template_separator: str = "."
    for_pdf = False
    _pad: int = 0
    # TODO: resolve template and image paths during rendering, not during YAML parsing
    _template_paths: [List] = field(default_factory=list)
    _image_paths: [List] = field(default_factory=list)

    def __post_init(self):
        DiagramColorOptions.__post_init__(self)
        PageFormatOptions.__post_init__(self)


def get_page_options(parsed_data, page_name: str):
    '''Get the page options

    uses: the page\'s options   -> general options -> default options
        ('{page_name}_options') ->    ('options')  -> {}
    '''
    page_options_name = f'{page_name}_options'
    if page_options_name in parsed_data:
        return PageOptions(**parsed_data[page_options_name])
    return PageOptions(**parsed_data.get('options', {}))
