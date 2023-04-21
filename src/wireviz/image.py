from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union


from wireviz.hypertext import MultilineHypertext
from wireviz.wv_colors import SingleColor

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
            self.fixedsize = (self.width or self.height) and self.scale is None

        if self.scale is None or self.scale is "":
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
