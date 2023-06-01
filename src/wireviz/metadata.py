from datetime import datetime
import logging
from dataclasses import dataclass, field, asdict, fields
from typing import Union, Dict, List
from pathlib import Path
from enum import Enum

import wireviz  # for doing wireviz.__file__
from .wv_dataclasses import PlainText

# Metadata can contain whatever is needed by the HTML generation/template.
MetadataKeys = PlainText  # Literal['title', 'description', 'notes', ...]


@dataclass(frozen=True)
class DocumentInfo:
    title: str
    pn: str


@dataclass(frozen=True)
class CompanyInfo:
    company: str
    address: str


@dataclass(frozen=True)
class AuthorSignature:
    name: str = ''
    date: Union[datetime, str, None] = None

    def __post_init__(self):
        if isinstance(self.date, str):
            if self.date == None or self.date.lower() == 'n/a':
                newdate = 'n/a'
            elif self.date == 'TBD':
                newdate = "TBD"
            else:
                date_format = "%Y-%m-%d"
                try:
                    newdate = datetime.strptime(self.date, date_format)
                except:
                    raise ValueError(f'date ({self.date}) should be parsable with format ({date_format}) or set to "n/a" or "TBD"')
            object.__setattr__(self, 'date', newdate)


@dataclass(frozen=True)
class AuthorRole(AuthorSignature):
    role: str = ''


@dataclass(frozen=True)
class RevisionSignature(AuthorSignature):
    changelog: str = ''

    def __post_init__(self):
        super().__post_init__()


@dataclass(frozen=True)
class RevisionInfo(RevisionSignature):
    revision: str = ''


@dataclass(frozen=True)
class OutputMetadata():
    output_dir: Path
    output_name: str


@dataclass(frozen=True)
class SheetMetadata():
    sheet_total: int
    sheet_current: int
    sheet_name: str


@dataclass(frozen=True)
class PagesMetadata():
    titlepage: Path
    output_names: List[str]
    files: List[str]
    use_qty_multipliers: bool
    multiplier_file_name: str
    pages_notes: Dict[str, str] = field(default_factory=dict)

class PageTemplateTypes(str, Enum):
    simple = 'simple'
    din_6771 = 'din-6771'
    titlepage = 'titlepage'


class SheetSizes(str, Enum):
    A2 = 'A2'
    A3 = 'A3'
    A4 = 'A4'

class Orientations(str, Enum):
    landscape = 'landscape'
    portrait = 'portrait'

@dataclass(frozen=True)
class PageTemplateConfig():
    name: PageTemplateTypes = PageTemplateTypes.din_6771
    sheetsize: SheetSizes = SheetSizes.A3
    orientation: Union[Orientations] = None

    def __post_init__(self):
        if isinstance(self.name, str):
            object.__setattr__(self, 'name', PageTemplateTypes(self.name))
        if isinstance(self.sheetsize, str):
            object.__setattr__(self, 'sheetsize', SheetSizes(self.sheetsize))

        if self.orientation is None:
            if self.sheetsize == SheetSizes.A4:
                _orientation = Orientations.portrait
            else:
                _orientation = Orientations.landscape
            object.__setattr__(self, 'orientation', _orientation)


    def has_bom_reversed(self):
        if self.name == PageTemplateTypes.din_6771:
            return True
        return False


# TODO: Metadata is a 'fourre-tout' of metadata right now.
#       Is this the best way to keep it or we should have more segmentation?
#       Maybe we could avoid inheritance, and instead have everything as an arg
#       Then we create a 'from_dict' options, which fills the args even if they
#       are not at the proper depth (if there's no conflict in names)
@dataclass(frozen=True)
class Metadata(PagesMetadata, OutputMetadata, CompanyInfo, SheetMetadata, DocumentInfo):
    authors: Dict[str, AuthorSignature] = field(default_factory=dict)
    revisions: Dict[str, RevisionSignature] = field(default_factory=list)
    template: PageTemplateConfig = PageTemplateConfig()
    logo: str = None

    def __post_init__(self):
        _authors = {}
        for k, v in self.authors.items():
            _authors[k] = v
            if isinstance(v, dict):
                _authors[k] = AuthorSignature(**v)
            assert isinstance(_authors[k], AuthorSignature), f'{_authors[k]} should be an instance of AuthorSignature'
        object.__setattr__(self, 'authors', _authors)

        _revisions = {}
        for k, v in self.revisions.items():
            _revisions[k] = v
            if isinstance(v, dict):
                _revisions[k] = RevisionSignature(**v)
            assert isinstance(_revisions[k], RevisionSignature), f'{_revisions[k]} should be an instance of RevisionSignature'
        object.__setattr__(self, 'revisions', _revisions)

        if not isinstance(self.template, PageTemplateConfig):
            object.__setattr__(self, 'template', PageTemplateConfig(**self.template))

    @property
    def name(self):
        if self.pn and self.pn not in self.output_name:
            return f"{self.pn}-{self.output_name}"
        else:
            return self.output_name

    @property
    def generator(self):
        return f"{wireviz.APP_NAME} {wireviz.__version__} - {wireviz.APP_URL}"

    @property
    def authors_list(self):
        _authors_list = []
        for role, author in self.authors.items():
            _authors_list.append(AuthorRole(name=author.name, date=author.date, role=role))
        return _authors_list

    @property
    def revisions_list(self):
        _revisions_list = []
        for revision, sig in self.revisions.items():
            _revisions_list.append(RevisionInfo(revision=revision, name=sig.name, date=sig.date, changelog=sig.changelog))
        return _revisions_list

    @property
    def revision(self):
        return self.revisions_list[-1].revision

    @property
    def pages_metadata(self):
        return PagesMetadata(
            titlepage=self.titlepage,
            output_names=self.output_names,
        )


# TODO: standardize metadata to indicate which are supported...
#class Metadata(dict):
#    '''All data used to extend the informations on the pages'''
#
#    def __init__(self, **kwargs):
#        if 'options' in kwargs:
#            raise ValueError(f'Options should be defined externally to metadata!')
#
#        if 'notes' in kwargs:
#            raise ValueError(f'Notes should be defined externally to metadata!')
#
#        for k, v in kwargs.items():
#            self[k] = v
