import logging
from dataclasses import dataclass, field, asdict, fields
from .wv_dataclasses import PlainText

# Metadata can contain whatever is needed by the HTML generation/template.
MetadataKeys = PlainText  # Literal['title', 'description', 'notes', ...]

# TODO: standardize metadata to indicate which are supported...
class Metadata(dict):
    '''All data used to extend the informations on the pages'''

    def __init__(self, **kwargs):
        if 'options' in kwargs:
            raise ValueError(f'Options should be defined externally to metadata!')

        if 'notes' in kwargs:
            raise ValueError(f'Notes should be defined externally to metadata!')

        for k, v in kwargs.items():
            self[k] = v
