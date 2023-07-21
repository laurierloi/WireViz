from dataclasses import dataclass, field

from wireviz.wv_utils import html_line_breaks


@dataclass
class MultilineHypertext:
    raw: str  # Hypertext possibly also including newlines to break lines in diagram output

    @staticmethod
    def to(value):
        if isinstance(value, MultilineHypertext):
            return value

        if isinstance(value, str):
            return MultilineHypertext(raw=value)

        if isinstance(value, list):
            return MultilineHypertext(raw="<br>".join(value))

        return MultilineHypertext("")

    @property
    def clean(self):
        return html_line_breaks(self.raw)

    def __repr__(self):
        return self.raw
