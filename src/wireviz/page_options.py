import logging
from dataclasses import dataclass, field, asdict, fields
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Tuple, Union

from .wv_dataclasses import PlainText
from wireviz.wv_colors import (
    ColorOutputMode,
    MultiColor,
    SingleColor,
    get_color_by_colorcode_index,
)

@dataclass
class PageFormatOptions:
    show_bom: bool = True
    show_index_table: bool = False
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

# TODO: have options tree instead of unwrapping?
@dataclass
class PageOptions(PageFormatOptions, DiagramColorOpions):
    fontname: PlainText = "arial"
    mini_bom_mode: bool = True
    template_separator: str = "."
    _pad: int = 0
    # TODO: resolve template and image paths during rendering, not during YAML parsing
    _template_paths: [List] = field(default_factory=list)
    _image_paths: [List] = field(default_factory=list)

    def __post_init(self):
        DiagramColorOpions.__post_init__(self)
        PageFormatOpions.__post_init__(self)


def get_page_options(parsed_data, page_name: str):
    '''Get the page options

    uses: the page\'s options   -> general options -> default options
        ('{page_name}_options') ->    ('options')  -> {}
    '''
    page_options_name = f'{page_name}_options'
    if page_options_name in parsed_data:
        return PageOptions(**parsed_data[page_options_name])
    return PageOptions(**parsed_data.get('options', {}))


