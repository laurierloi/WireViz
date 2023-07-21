from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from wireviz.hypertext import MultilineHypertext
from wireviz.wv_colors import SingleColor


def aspect_ratio(image_src):
    try:
        from PIL import Image

        image = Image.open(image_src)
        if image.width > 0 and image.height > 0:
            return image.width / image.height
        print(f"aspect_ratio(): Invalid image size {image.width} x {image.height}")
    # ModuleNotFoundError and FileNotFoundError are the most expected, but all are handled equally.
    except Exception as error:
        print(f"aspect_ratio(): {type(error).__name__}: {error}")
    return 1  # Assume 1:1 when unable to read actual image size


@dataclass
class Image:
    # Attributes of the image object <img>:
    src: str
    scale: str = ""
    # Attributes of the image cell <td> containing the image:
    width: int = 0
    height: int = 0
    fixedsize: bool = False
    bgcolor: SingleColor = None
    # Contents of the text cell <td> just below the image cell:
    caption: Optional[MultilineHypertext] = None
    # See also HTML doc at https://graphviz.org/doc/info/shapes.html#html

    def __post_init__(self):

        self.bgcolor = SingleColor(self.bgcolor)

        if not self.fixedsize:
            # Default True if any dimension specified unless self.scale also is specified.
            self.fixedsize = (self.width or self.height) and self.scale in ["", None]

        if self.scale in [None, ""]:
            if not self.width and not self.height:
                self.scale = "false"
            elif self.width and self.height:
                self.scale = "both"
            else:
                self.scale = "true"  # When only one dimension is specified.

        if self.fixedsize:
            # If only one dimension is specified, compute the other
            # because Graphviz requires both when fixedsize=True.
            if self.height:
                if not self.width:
                    self.width = self.height * aspect_ratio(self.src)
            else:
                if self.width:
                    self.height = self.width / aspect_ratio(self.src)
