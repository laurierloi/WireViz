from dataclasses import dataclass, field, asdict, fields
from .wv_dataclasses import PlainText

# Metadata can contain whatever is needed by the HTML generation/template.
MetadataKeys = PlainText  # Literal['title', 'description', 'notes', ...]

# TODO: standardize metadata to indicate which are supported...
class Metadata(dict):
    '''All data used to extend the informations on the pages'''
    pass
