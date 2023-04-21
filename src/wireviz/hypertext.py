from dataclasses import dataclass, field
from wireviz.wv_utils import html_line_breaks

@dataclass
class MultilineHypertext:
    raw: str    # Hypertext possibly also including newlines to break lines in diagram output

    def clean(self):
        return html_line_breaks(self.raw)
