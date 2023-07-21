from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from wireviz.wv_utils import awg_equiv, mm2_equiv, remove_links


# TODO: use frozen dataclass
@dataclass
class PartNumberInfo:
    pn: str = ""
    manufacturer: str = ""
    mpn: str = ""
    supplier: str = ""
    spn: str = ""
    is_list: bool = False

    BOM_KEY_TO_COLUMNS = {
        "pn": "P/N",
        "manufacturer": "Manufacturer",
        "mpn": "MPN",
        "supplier": "Supplier",
        "spn": "SPN",
    }

    def __bool__(self):
        return bool(
            self.pn or self.manufacturer or self.mpn or self.supplier or self.spn
        )

    def __hash__(self):
        return hash((self.pn, self.manufacturer, self.mpn, self.supplier, self.spn))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __post_init__(self):
        if isinstance(self.pn, list):
            raise ValueError(f"pn ({self.pn}) should not be a list")

        def clean_arg(arg):
            return remove_links("" if arg is None else str(arg))

        self.pn = clean_arg(self.pn)
        self.manufacturer = clean_arg(self.manufacturer)
        self.mpn = clean_arg(self.mpn)
        self.supplier = clean_arg(self.supplier)
        self.spn = clean_arg(self.spn)

    @property
    def bom_keys(self):
        return list(self.BOM_KEY_TO_COLUMNS.keys())

    @property
    def bom_dict(self):
        return {k: self[k] for k in self.bom_keys}

    @property
    def str_list(self):
        l = ["", "", ""]
        if self.pn:
            l[0] = f"P/N: {self.pn}"
        l[1] = self.manufacturer
        if self.mpn:
            if not l[1]:
                l[1] = "MPN"
            l[1] += ": "
            l[1] += self.mpn
        l[2] = self.supplier
        if self.spn:
            if not l[2]:
                l[2] = "SPN"
            l[2] += ": "
            l[2] += self.spn
        return [i for i in l if i]

    def copy(self):
        return PartNumberInfo(
            pn=self.pn,
            manufacturer=self.manufacturer,
            mpn=self.mpn,
            supplier=self.supplier,
            spn=self.spn,
        )

    def clear_per_field(self, op, other):
        part = self.copy()

        if other is None:
            if op == "==":
                return part
            elif op == "!=":
                return None
            else:
                raise NotImplementedError(f"op {op} not supported")

        if other.is_list:
            for item in other.pn_list:
                part = part.clear_per_field(op, item)
        else:
            for k in ["pn", "manufacturer", "mpn", "supplier", "spn"]:
                if op == "==":
                    if part[k] == other[k]:
                        part[k] = ""
                elif op == "!=":
                    if part[k] != other[k]:
                        part[k] = ""
                else:
                    raise NotImplementedError(f"op {op} not supported")
        return part

    def keep_only_eq(self, other):
        return self.clear_per_field("!=", other)

    def remove_eq(self, other):
        return self.clear_per_field("==", other)

    @staticmethod
    def list_keep_only_eq(partnumbers):
        pn = partnumbers[0]
        for p in partnumbers:
            pn = pn.keep_only_eq(p)
        return pn

    def as_list(self, parent_partnumbers=None):
        return partnumbers2list(self, parent_partnumbers)


@dataclass
class PartnumberInfoList:
    pn_list: List[PartNumberInfo] = field(default_factory=list())
    is_list: bool = True

    def keep_only_eq(self, other):
        for pn in self.pn_list:
            yield pn.keep_only_eq(other)

    def remove_eq(self, other):
        for pn in self.pn_list:
            yield pn.remove_eq(other)

    def as_list(self, parent_partnumbers=None):
        for pn in self.pn_list:
            yield pn.as_list()


def partnumbers2list(
    partnumbers: PartNumberInfo, parent_partnumbers: PartNumberInfo = None
) -> List[str]:
    if not isinstance(partnumbers, list):
        partnumbers = [partnumbers]

    # if there's no parent, fold
    if parent_partnumbers is None:
        return PartNumberInfo.list_keep_only_eq(partnumbers).str_list

    if isinstance(parent_partnumbers, list):
        parent_partnumbers = PartNumberInfo.list_keep_only_eq(parent_partnumbers)

    partnumbers = [p.remove_eq(parent_partnumbers) for p in partnumbers]

    return [p.str_list for p in partnumbers if p]
