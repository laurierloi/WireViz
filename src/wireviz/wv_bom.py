# -*- coding: utf-8 -*-
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Union, Set, Tuple

import tabulate as tabulate_module

from wireviz.numbers import NumberAndUnit
from wireviz.partnumber import PartNumberInfo
from wireviz.wv_utils import remove_links
from wireviz.wv_templates import get_template

# TODO: different BOM modes
# BomMode
# "normal"  # no bubbles, full PN info in GV node
# "bubbles"  # = "full" -> maximum info in GV node
# "hide PN info"
# "PN crossref" = "PN bubbles" + "hide PN info"
# "additionally: BOM table in GV graph label (#227)"
# "title block in GV graph label"



@dataclass
class BomEntry:
    qty: NumberAndUnit
    partnumbers: PartNumberInfo
    id: str
    amount: Union[NumberAndUnit, None] = None
    qty_multiplier: Union[int, float] = 1
    description: str = ""
    category: str = ""
    ignore_in_bom: bool = False

    # Used to add all occurence of a BomEntry
    designators: [List] = field(default_factory=list)
    per_harness: [Dict] = field(default_factory=dict)

    # Used to restrict printed lengths
    MAX_PRINTED_DESCRIPTION: int = 40
    MAX_PRINTED_DESIGNATORS: int = 2
    restrict_printed_lengths: bool = True

    scaled_per_harness = False

    # Map a bom key to the header
    BOM_KEY_TO_COLUMNS = {
        "id": "#",
        "qty": "Qty",
        "unit": "Unit",
        "description": "Description",
        "designators": "Designators",
        "per_harness": "Per Harness",
    }

    def __repr__(self):
        return f"{id}: {self.partnumbers}, {self.qty}"

    def __hash__(self):
        return hash((self.partnumbers, self.description))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __add__(self, other):
        # TODO: add update designators and per_harness
        return BomEntry(
            qty=self.qty + other.qty,
            partnumbers=self.partnumbers,
            id=self.id,
            amount=None,  # amount already included
            qty_multiplier=None,  # qty_multiplier already included
            description=self.description,
            category=self.category,
            ignore_in_bom=self.ignore_in_bom,
            designators=self.designators,
            per_harness=self.per_harness,
        )

    def __getitem__(self, key):
        if key in self.partnumbers.BOM_KEY_TO_COLUMNS:
            return self.partnumbers[key]
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __post_init__(self):
        assert isinstance(self.qty, NumberAndUnit), f"Unexpected qty type {self.qty}"
        assert isinstance(
            self.partnumbers, PartNumberInfo
        ), f"Unexpected partnumbers type {self.partnumbers}"
        assert self.id is None or isinstance(
            self.id, str
        ), f"Unexpected id type {self.id}"

        if self.amount is not None:
            assert isinstance(
                self.amount, NumberAndUnit
            ), f"Unexpected id type {self.amount}"
            self.qty *= self.amount
        if self.qty_multiplier is not None:
            if not isinstance(self.qty_multiplier, str):
                self.qty *= float(self.qty_multiplier)

    @property
    def description_str(self):
        description = self.description
        if (
            not self.restrict_printed_lengths or
            'href' in description or
            len(description) < self.MAX_PRINTED_DESCRIPTION
        ):
            return description
        return f"{description[:self.MAX_PRINTED_DESCRIPTION]} (...)"

    @property
    def designators_str(self):
        if not self.designators:
            return ""

        all_designators = sorted(self.designators)
        if (
            self.restrict_printed_lengths
            and len(all_designators) > self.MAX_PRINTED_DESIGNATORS
        ):
            all_designators = all_designators[: self.MAX_PRINTED_DESIGNATORS] + ["..."]
        return ", ".join(all_designators)

    @property
    def bom_keys(self):
        return list(self.BOM_KEY_TO_COLUMNS.keys()) + self.partnumbers.bom_keys

    @property
    def bom_dict(self):
        d = {}
        for k in self.bom_keys:
            # Some keys require custom handling, others use default value
            if k == "id":
                d[k] = str(self.id)
            elif k == "qty":
                d[k] = self.qty.number_str
            elif k == "unit":
                d[k] = self.qty.unit_str
            elif k == "description":
                d[k] = self.description_str
            elif k == "designators":
                d[k] = self.designators_str
            elif k == "per_harness":
                content = [
                    f'{name}: {info["qty"]}' for name, info in self.per_harness.items()
                ]
                if len(content) > 0:
                    d[k] = ", ".join(content)
            else:
                d[k] = self[k]
        return d

    @property
    def bom_defined(self):
        d = self.bom_dict
        return {k for k, v in d.items() if v != ""}

    def bom_column(self, key):
        if key in self.BOM_KEY_TO_COLUMNS:
            return self.BOM_KEY_TO_COLUMNS[key]
        if key in self.partnumbers.BOM_KEY_TO_COLUMNS:
            return self.partnumbers.BOM_KEY_TO_COLUMNS[key]
        raise ValueError(f"key '{key}' not found in bom keys")

    @property
    def bom_dict_pretty_column(self):
        return {self.bom_column(k): v for k, v in self.bom_dict.items()}

    def scale_per_harness(self, qty_multipliers):
        if self.scaled_per_harness:
            logging.warn("{self}: Already scaled")

        qty = NumberAndUnit(0, self.qty.unit_str)
        for name, info in self.per_harness.items():
            multiplier_name = [k for k in qty_multipliers.keys() if name.endswith(k)]
            if len(multiplier_name) == 0:
                raise ValueError(
                    f"No multiplier found for harness {name} in {qty_multipliers}"
                )
            if len(multiplier_name) > 1:
                raise ValueError(
                    f"Conflicting multipliers found ({multiplier_name}) for harness {name} in {qty_multipliers}"
                )

            info["qty"] *= qty_multipliers[multiplier_name[0]]
            qty += info["qty"]
        self.qty = qty
        self.scaled_per_harness = True

@dataclass(frozen=True)
class BomRenderOptions:
    restrict_printed_lengths: bool = True
    filter_entries: bool = False
    no_per_harness: bool = True
    reverse: bool = False


@dataclass(frozen=True)
class BomRender:
    entries: List[Dict[str, str]]
    columns: List[str]
    has_content: Set[str] = field(default_factory=set())
    options: BomRenderOptions = field(default_factory=BomRenderOptions())

    private_content: List[Tuple[str]] = field(default_factory=list)

    @property
    def headers(self):
        headers = self.columns
        if self.options.filter_entries:
            headers = [k for k in self.columns if k in self.has_content]

        if self.options.no_per_harness:
            if 'Per Harness' in headers:
                headers.remove('Per Harness')
        return headers

    @property
    def content(self):
        if not self.private_content:
            headers = self.headers
            entries_as_list = []
            for entry in self.entries:
                entries_as_list.append(tuple([entry.get(k, "") for k in headers]))

            # sanity check
            expected_length = len(entries_as_list[0])
            for e in entries_as_list:
                assert len(e) == expected_length, f'entries {e} length is not {expected_length}'

            if self.options.reverse:
                entries_as_list.reverse()

            object.__setattr__(self, 'private_content', entries_as_list)

        return self.private_content

    @property
    def columns_class(self):
        return ["bom_col_{}".format("id" if c == "#" else c.lower()) for c in self.headers]

    @property
    def rows(self):
        return len(self.entries)

    def as_list(self):
        return [self.headers] + self.content

    def as_table(self):
        return tabulate_module.tabulate(self.as_list(), headers="firstrow")

    def as_tsv(self):
        output = ""
        for row in self.as_list():
            row = [item if item is not None else "" for item in row]
            output = output + "\t".join(str(remove_links(item)) for item in row) + "\n"
        return output

    def print_bom_table(self):
        print('\n', self.as_table(), '\n')

    def render(self, options):
        return get_template("bom.html").render({"bom": self, "options": options})


@dataclass
class BomContent:
    '''Used to represent the bom'''
    entries: Dict[str, BomEntry]

    def get_bom_render(self, options: Union[BomRenderOptions, None] = None):
        if options is None:
            options = BomRenderOptions()

        entries_as_dict = []
        bom_columns = []
        has_content = set()
        for entry in self.entries.values():
            entry.restrict_printed_lengths = options.restrict_printed_lengths
            entry_as_dict = entry.bom_dict_pretty_column
            entries_as_dict.append(entry_as_dict)
            for k in entry_as_dict:
                if k not in bom_columns:
                    bom_columns.append(k)
                if entry_as_dict[k] is not None and entry_as_dict[k] != "":
                    has_content.add(k)
        return BomRender(
            entries=entries_as_dict,
            columns=bom_columns,
            has_content=has_content,
            options=options,
        )
