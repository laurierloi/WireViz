# -*- coding: utf-8 -*-
import logging
from dataclasses import asdict, dataclass, field, fields
from enum import Enum, IntEnum
from itertools import zip_longest
from typing import Any, Dict, List, Optional, Tuple, Union

from wireviz.hypertext import MultilineHypertext
from wireviz.image import Image
from wireviz.numbers import NumberAndUnit
from wireviz.partnumber import PartNumberInfo, PartnumberInfoList
from wireviz.wv_bom import BomEntry
from wireviz.wv_colors import (
    COLOR_CODES,
    ColorOutputMode,
    MultiColor,
    SingleColor,
    get_color_by_colorcode_index,
)
from wireviz.wv_utils import awg_equiv, mm2_equiv, remove_links

# Each type alias have their legal values described in comments
# - validation might be implemented in the future
PlainText = str  # Text not containing HTML tags nor newlines

Designator = PlainText  # Case insensitive unique name of connector or cable

# Type combinations
Pin = Union[int, PlainText]  # Pin identifier
PinIndex = int  # Zero-based pin index
Wire = Union[int, PlainText]  # Wire number or Literal['s'] for shield
NoneOrMorePins = Union[
    Pin, Tuple[Pin, ...], None
]  # None, one, or a tuple of pin identifiers
NoneOrMorePinIndices = Union[
    PinIndex, Tuple[PinIndex, ...], None
]  # None, one, or a tuple of zero-based pin indices
OneOrMoreWires = Union[Wire, Tuple[Wire, ...]]  # One or a tuple of wires


Side = Enum("Side", "LEFT RIGHT")

AUTOGENERATED_PREFIX = "AUTOGENERATED_"

BomCategory = IntEnum(  # to enforce ordering in BOM
    "BomEntry", "CONNECTOR CABLE WIRE PIN ADDITIONAL BUNDLE"
)
QtyMultiplierConnector = Enum(
    "QtyMultiplierConnector", "PINCOUNT POPULATED CONNECTIONS"
)
QtyMultiplierCable = Enum(
    "QtyMultiplierCable", "WIRECOUNT TERMINATION LENGTH TOTAL_LENGTH"
)


@dataclass
class PinClass:
    index: int
    id: str
    label: str
    color: MultiColor
    parent: str  # designator of parent connector
    _num_connections = 0  # incremented in Connector.connect()
    _anonymous: bool = False  # true for pins on autogenerated connectors
    _simple: bool = False  # true for simple connector

    # TODO: support a "crimp" defined by parent

    def __post_init__(self):
        if self.label and "__" in self.label:
            self.label, pin = self.label.split("__")
            self.index = int(pin) - 1

    def __str__(self):
        snippets = [  # use str() for each in case they are int or other non-str
            str(self.parent) if not self._anonymous else "",
            str(self.id) if not self._anonymous and not self._simple else "",
            str(self.label) if self.label else "",
        ]
        return ":".join([snip for snip in snippets if snip != ""])

    @property
    def category(self):
        return BomCategory.PIN


@dataclass
class Component:
    category: Optional[str] = None  # currently only used by cables, to define bundles
    type: Union[MultilineHypertext, List[MultilineHypertext]] = None
    subtype: Union[MultilineHypertext, List[MultilineHypertext]] = None

    # the following are provided for user convenience and should not be accessed later.
    # their contents are loaded into partnumbers during the child class __post_init__()
    pn: str = None
    manufacturer: str = None
    mpn: str = None
    supplier: str = None
    spn: str = None

    # BOM info
    qty: NumberAndUnit = NumberAndUnit(1, None)
    amount: Optional[NumberAndUnit] = None
    ignore_in_bom: bool = False
    id: Optional[str] = None  # to be filled after harness is built
    designators: [List] = field(
        default_factory=list
    )  # Used only for additional components

    # Utility
    parent: Optional = None
    additional_components: Optional[List] = field(default_factory=list)
    qty_multiplier: Union[QtyMultiplierConnector, QtyMultiplierCable, int] = 1
    _qty_multiplier_computed: Union[int, float] = 1

    # style
    bgcolor: SingleColor = None

    def __hash__(self):
        """Provide a hash for this component dataclass.

        Any component using same part should have the same hash
        """
        return hash(self.partnumbers)

    def __str__(self) -> str:
        return f"{self.type}{', ' + self.subtype.raw if self.subtype.raw else ''}"

    def __post_init__(self):
        self.qty = NumberAndUnit.to_number_and_unit(self.qty)
        self.amount = NumberAndUnit.to_number_and_unit(self.amount)

        self.type = MultilineHypertext.to(self.type)
        self.subtype = MultilineHypertext.to(self.subtype)

        if isinstance(self.pn, list):
            raise RuntimeError(f"PN ({self.pn}) should not be a list")

        for i, item in enumerate(self.additional_components):
            if isinstance(item, Component):
                continue
            elif isinstance(item, dict):
                self.additional_components[i] = Component(
                    **item, category=BomCategory.ADDITIONAL, parent=self
                )
            else:
                raise ValueError(
                    f"additional component {item} should be a Component or a dict, is {type(item)}"
                )

        if self.category is None:
            raise RuntimeError(f"category should be defined for {self}")

    def compute_qty_multipliers(self):
        pass

    @property
    def bom_entry(self):
        self.compute_qty_multipliers()
        return BomEntry(
            qty=self.qty,
            partnumbers=self.partnumbers,
            id=self.id,
            amount=self.amount,
            qty_multiplier=self._qty_multiplier_computed,
            description=str(self),
            category=self.category,
            designators=self.designators,
            ignore_in_bom=self.ignore_in_bom,
        )

    @property
    def partnumbers(self):
        return PartNumberInfo(
            pn=self.pn,
            manufacturer=self.manufacturer,
            mpn=self.mpn,
            supplier=self.supplier,
            spn=self.spn,
        )


@dataclass
class GraphicalComponent(Component):  # abstract class
    # component properties
    designator: Designator = ""
    color: Optional[MultiColor] = None
    image: Optional[Image] = None
    additional_components: List[Component] = field(default_factory=list)
    notes: Optional[MultilineHypertext] = None
    # BOM options
    add_up_in_bom: Optional[bool] = None
    # rendering options
    bgcolor: Optional[SingleColor] = None
    bgcolor_title: Optional[SingleColor] = None
    show_name: Optional[bool] = None

    def __hash__(self):
        return hash(super())

    def __post_init__(self):
        super().__post_init__()
        self.notes = MultilineHypertext.to(self.notes)

        self.designator = remove_links(self.designator)


@dataclass
class Connector(GraphicalComponent):
    # connector-specific properties
    style: Optional[str] = None
    loops: List[List[Pin]] = field(default_factory=list)
    # pin information in particular
    pincount: Optional[int] = None
    pins: List[Pin] = field(default_factory=list)  # legacy
    pinlabels: List[Pin] = field(default_factory=list)  # legacy
    pincolors: List[str] = field(default_factory=list)  # legacy
    pin_objects: Dict[Any, PinClass] = field(default_factory=dict)  # new
    # rendering option
    show_pincount: Optional[bool] = None
    hide_disconnected_pins: bool = False

    ports_left: bool = True
    ports_right: bool = False

    def __hash__(self):
        return hash(super())

    def __str__(self) -> str:
        substrs = [
            "Connector",
            self.type,
            self.subtype,
            f"{self.pincount} pins" if self.show_pincount else None,
            str(self.color) if self.color else None,
        ]
        return ", ".join([str(s) for s in substrs if s is not None and s != ""])

    @property
    def is_autogenerated(self):
        return self.designator.startswith(AUTOGENERATED_PREFIX)

    @property
    def has_pincolors(self):
        return any(_pin.color for _pin in self.pin_objects.values())

    def should_show_pin(self, pin_id):
        return (
            not self.hide_disconnected_pins
            or self.pin_objects[pin_id]._num_connections > 0
        )

    def pins_to_show(self):
        return [p for k, p in self.pin_objects.items() if self.should_show_pin(k)]

    def __post_init__(self) -> None:
        self.category = BomCategory.CONNECTOR
        super().__post_init__()

        self.bgcolor = SingleColor(self.bgcolor)
        self.bgcolor_title = SingleColor(self.bgcolor_title)
        self.color = MultiColor(self.color)

        if isinstance(self.image, dict):
            self.image = Image(**self.image)

        self._ports_left_set = False
        self._ports_right_set = False

        if self.style == "simple":
            if self.pincount and self.pincount > 1:
                raise Exception(
                    "Connectors with style set to simple may only have one pin"
                )
            self.pincount = 1

        if not self.pincount:
            self.pincount = max(
                len(self.pins), len(self.pinlabels), len(self.pincolors)
            )
            if not self.pincount:
                raise Exception(
                    "You need to specify at least one: "
                    "pincount, pins, pinlabels, or pincolors"
                )

        # create default list for pins (sequential) if not specified
        if not self.pins:
            self.pins = list(range(1, self.pincount + 1))

        if len(self.pins) != len(set(self.pins)):
            raise Exception("Pins are not unique")

        # all checks have passed
        pin_tuples = zip_longest(
            self.pins,
            self.pinlabels,
            self.pincolors,
        )
        for pin_index, (pin_id, pin_label, pin_color) in enumerate(pin_tuples):
            self.pin_objects[pin_id] = PinClass(
                index=pin_index,
                id=pin_id,
                label=pin_label,
                color=MultiColor(pin_color),
                parent=self.designator,
                _anonymous=self.is_autogenerated,
                _simple=self.style == "simple",
            )

        if self.show_name is None:
            self.show_name = self.style != "simple" and not self.is_autogenerated

        if self.show_pincount is None:
            # hide pincount for simple (1 pin) connectors by default
            self.show_pincount = self.style != "simple"

        for loop in self.loops:
            # TODO: check that pins to connect actually exist
            # TODO: allow using pin labels in addition to pin numbers,
            #       just like when defining regular connections
            # TODO: include properties of wire used to create the loop
            if len(loop) != 2:
                raise Exception("Loops must be between exactly two pins!")
            # side=None, determine side to show loops during rendering
            self.activate_pin(loop[0], side=None, is_connection=True)
            self.activate_pin(loop[1], side=None, is_connection=True)

    def activate_pin(self, pin_id, side: Side = None, is_connection=True) -> None:
        if is_connection:
            self.pin_objects[pin_id]._num_connections += 1
        if side == Side.LEFT:
            self._ports_left_set = True
            self.ports_left = True
            if not self._ports_right_set:
                self.ports_right = False
        elif side == Side.RIGHT:
            self._ports_right_set = True
            self.ports_right = True
            if not self._ports_left_set:
                self.ports_left = False

    def compute_qty_multipliers(self):
        # do not run before all connections in harness have been made!
        num_populated_pins = len(
            [pin for pin in self.pin_objects.values() if pin._num_connections > 0]
        )
        num_connections = sum(
            [pin._num_connections for pin in self.pin_objects.values()]
        )
        qty_multipliers_computed = {
            "PINCOUNT": self.pincount,
            "POPULATED": num_populated_pins,
            "CONNECTIONS": num_connections,
        }
        for subitem in self.additional_components:
            if isinstance(subitem.qty_multiplier, str):
                computed_factor = qty_multipliers_computed[
                    subitem.qty_multiplier.upper()
                ]
            # if isinstance(subitem.qty_multiplier, QtyMultiplierConnector):
            #    computed_factor = qty_multipliers_computed[subitem.qty_multiplier.name.upper()]
            # elif isinstance(subitem.qty_multiplier, QtyMultiplierCable):
            #    raise Exception("Used a cable multiplier in a connector!")
            elif isinstance(subitem.qty_multiplier, int) or isinstance(
                subitem.qty_multiplier, float
            ):
                computed_factor = subitem.qty_multiplier
            else:
                raise ValueError(
                    f'Unexpected qty multiplier "{subitem.qty_multiplier}"'
                )
            subitem._qty_multiplier_computed = computed_factor


@dataclass
class WireClass(GraphicalComponent):
    parent: str = None  # designator of parent cable/bundle
    # wire-specific properties
    index: int = None
    label: str = ""
    color: MultiColor = None
    # inheritable from parent cable
    gauge: Optional[NumberAndUnit] = None
    length: Optional[NumberAndUnit] = None
    ignore_in_bom: Optional[bool] = False

    is_shield = False

    def __hash__(self):
        return hash((self.partnumbers, self.gauge_str, str(self.color)))

    def __str__(self) -> str:
        substrs = [
            "Wire",
            self.type.raw,
            self.subtype.raw,
            self.gauge_str,
            str(self.color) if self.color else None,
        ]
        desc = ", ".join([s for s in substrs if s is not None and s != ""])
        return desc

    def __post_init__(self):
        self.category = BomCategory.WIRE
        super().__post_init__()

    def wireinfo(self, parent_is_bundle=False):
        wireinfo = []
        if not parent_is_bundle and not self.is_shield:
            wireinfo.append(self.id)
        if self.color:
            wireinfo.append(str(self.color))
        if self.label:
            wireinfo.append(self.label)
        return ":".join(wireinfo)

    @property
    def port(self):
        return f"w{self.index+1}"

    @property
    def partnumbers(self):
        _partnumbers = super().partnumbers
        if not _partnumbers.mpn and self.color is not None:
            _partnumbers.mpn = self.get_mpn_if_belden()
        return _partnumbers

    @property
    def bom_entry(self):
        self.compute_qty_multipliers()
        return BomEntry(
            qty=self.length,
            partnumbers=self.partnumbers,
            id=self.id,
            description=str(self),
            category=self.category,
            ignore_in_bom=self.ignore_in_bom,
        )

    @property
    def gauge_str(self):
        if not self.gauge:
            return None
        number = (
            int(self.gauge.number) if self.gauge.unit == "AWG" else self.gauge.number
        )
        actual_gauge = f"{number} {self.gauge.unit}"
        actual_gauge = actual_gauge.replace("mm2", "mm\u00B2")
        return actual_gauge

    @property
    def gauge_str_with_equiv(self):
        if not self.gauge:
            return None
        actual_gauge = self.gauge_str
        equivalent_gauge = ""
        if self.show_equiv:
            # convert unit if known
            if self.gauge.unit == "mm2":
                equivalent_gauge = f" ({awg_equiv(self.gauge.number)} AWG)"
            elif self.gauge.unit.upper() == "AWG":
                equivalent_gauge = f" ({mm2_equiv(self.gauge.number)} mm2)"
        out = f"{actual_gauge}{equivalent_gauge}"
        out = out.replace("mm2", "mm\u00B2")
        return out

    @property
    def length_str(self):
        if not self.length:
            return None
        return str(self.length)

    belden_color = {
        "BN": "001",
        "RD": "002",
        "OG": "003",
        "YE": "004",
        "GN": "005",
        "TQ": "006",  # (For Belden: light blue. For WireViz: turquoise)
        "VT": "007",
        "GY": "008",
        "WH": "009",
        "BK": "010",
        "BG": "011",
        "PK": "012",
        "BU": "013",
        "BKRD": "015",  # (for Belden: white/red)
        "BKGN": "016",  # (for Belden: white/green)
        "BKYE": "017",  # (for Belden: white/yellow)
        "BKBU": "018",  # (for Belden: white/blue)
        "BKBN": "019",  # (for Belden: white/brown)
        "BKOG": "020",  # (for Belden: white/orange)
        "BKGY": "021",  # (for Belden: white/gray)
        "BKVT": "022",  # (for Belden: white/purple)
        # (1) Why use BKRD instead of WHRD, since Belden only sells white/red?
        #    - WHRD is impractical to use in Wireviz (white wire sides on white background does not help with identification)
        #    - BKRD is clearly distinguishable, and comes handy to use in Wireviz, as the representation of a GND rail associated (even twisted, if applicable) with a specific RD signal wire.
        # (2) For all wire colors see:
        # https://www.belden.com/dfsmedia/f1e38517e0cd4caa8b1acb6619890f5e/7806-source/options/view/cabling-solutions-for-industrial-applications-catalog-belden-09-2020#page=153
    }
    belden_tfe_base_mpn = {
        # Leftmost in list is the prefered MPN
        # NOTE (lal 2022-12-20):  this prefered MPN is arbitrary ATM
        "16 AWG": ["83030", "83010"],
        "18 AWG": ["83029", "83009"],
        "20 AWG": ["83028", "83027", "83007", "83008"],
        "22 AWG": ["83049", "83050", "83025", "83026", "83005", "83006"],
        "24 AWG": ["83003", "83004", "83023", "83047", "83048"],
        "26 AWG": ["83002", "83046"],
        "28 AWG": ["83001", "83045"],
        "30 AWG": ["83000", "83043"],
        "32 AWG": ["83041"],
        # see: https://www.belden.com/dfsmedia/f1e38517e0cd4caa8b1acb6619890f5e/7806-source/options/view/cabling-solutions-for-industrial-applications-catalog-belden-09-2020#page=136
    }

    @property
    def is_belden(self):
        if "belden" in self.manufacturer.lower():
            return True
        return False

    def get_belden_color(self, color):
        if color not in self.belden_color:
            logging.warn(
                f"{self}: Color '{self.color}' not found in belden colors {list(self.belden_color.keys())}, defaulting to BK"
            )
            return self.belden_color["BK"]
        return self.belden_color[color]

    def gen_belden_cable_with_alternate(self):
        # Gauge and mpn base
        try:
            parts = self.belden_tfe_base_mpn[self.gauge_str]
        except KeyError:
            raise ValueError(
                f"Couldn't find a belden TFE wire for wire of {self.gauge_str}"
            )

        color = self.get_belden_color(str(self.color))

        if not color:
            raise ValueError(f"Failed to find a color for property: {self}")

        # Create the list of mpn
        roll_length = 100
        mpn_list = [f"{mpn} {color}{roll_length}" for mpn in parts]

        main_part = mpn_list[0]
        alternates = mpn_list[1:] if len(mpn_list) > 1 else []
        return (main_part, alternates)

    # TODO: clean me up
    def get_mpn_if_belden(self):
        if self.manufacturer and not self.mpn:
            if self.is_belden:
                main_part, alternates = self.gen_belden_cable_with_alternate()
                return main_part
                if alternates:
                    logging.info(
                        f'Alternate part{"s" if len(alternates) > 1 else ""} available for {self.gauge_str}, color {self.color}: {alternates}'
                    )
            else:
                logging.info(
                    f'Not updating part for manufacturer {self.manufacturer}, only "belden" supported'
                )
        else:
            logging.info(f"Not updating part, no manufacturer provided")
        return self.mpn if self.mpn else ""


@dataclass
class ShieldClass(WireClass):
    is_shield = True
    pass  # TODO, for wires with multiple shields more shield details, ...

    def __hash__(self):
        return hash(self.partnumbers)


@dataclass
class Connection:
    from_: PinClass = None
    via: Union[WireClass, ShieldClass] = None
    to: PinClass = None


@dataclass
class Cable(WireClass):
    # cable-specific properties
    gauge: Optional[NumberAndUnit] = None
    length: Optional[NumberAndUnit] = None
    color_code: Optional[str] = None
    # wire information in particular
    wirecount: Optional[int] = None
    shield: Union[bool, MultiColor] = False
    colors: List[str] = field(default_factory=list)  # legacy
    wirelabels: List[Wire] = field(default_factory=list)  # legacy
    wire_objects: Dict[Any, WireClass] = field(default_factory=dict)  # new
    # internal
    _connections: List[Connection] = field(default_factory=list)
    # rendering options
    show_name: Optional[bool] = None
    show_equiv: bool = False
    show_wirecount: bool = True

    def __hash__(self):
        if self.is_bundle:
            return hash(tuple([hash(w) for w in self.wire_objects.values()]))
        else:
            return hash(super())

    def __str__(self) -> str:
        substrs = [
            ("", "Cable"),
            (", ", self.type),
            (", ", self.subtype),
            (", ", self.wirecount),
            (" ", f"x {self.gauge_str}" if self.gauge else "wires"),
            (" ", "shielded" if self.shield else None),
            (", ", str(self.color) if self.color else None),
        ]
        if self.is_bundle:
            substrs += [
                (f"\n\t{i}: ", w) for i, w in enumerate(self.wire_objects.values())
            ]
        desc = "".join(
            [f"{s[0]}{s[1]}" for s in substrs if s[1] is not None and s[1] != ""]
        )
        return desc

    @property
    def partnumbers(self):
        if self.is_bundle:
            return PartnumberInfoList(
                pn_list=[w.partnumbers for w in self.wire_objects.values()]
            )
        else:
            return super().partnumbers

    @property
    def bom_entry(self):
        self.compute_qty_multipliers()
        if self.is_bundle:
            return [w.bom_entry for w in self.wire_objects.values()]
        else:
            return BomEntry(
                qty=self.qty,
                partnumbers=self.partnumbers,
                id=self.id,
                amount=self.amount,
                qty_multiplier=self._qty_multiplier_computed,
                description=str(self),
                category=self.category,
                designators=self.designators,
                ignore_in_bom=self.ignore_in_bom,
            )

    @property
    def is_bundle(self):
        return self.category == BomCategory.BUNDLE

    @property
    def is_autogenerated(self):
        return self.designator.startswith(AUTOGENERATED_PREFIX)

    def __post_init__(self) -> None:
        if isinstance(self.category, str) and self.category.lower() == "bundle":
            self.category = BomCategory.BUNDLE
        else:
            self.category = BomCategory.CABLE
        self.notes = MultilineHypertext.to(self.notes)

        # TODO: style management should be separated from this logic...
        self.bgcolor = SingleColor(self.bgcolor)
        self.bgcolor_title = SingleColor(self.bgcolor_title)
        self.color = MultiColor(self.color)

        if isinstance(self.image, dict):
            self.image = Image(**self.image)

        # TODO:
        # allow gauge, length, and other fields to be lists too (like part numbers),
        # and assign them the same way to bundles.

        self.gauge = NumberAndUnit.to_number_and_unit(self.gauge, "mm2")
        self.length = NumberAndUnit.to_number_and_unit(self.length, "m")
        self.amount = self.length  # for BOM

        if self.wirecount:  # number of wires explicitly defined
            if self.colors:  # use custom color palette (partly or looped if needed)
                self.colors = [
                    self.colors[i % len(self.colors)] for i in range(self.wirecount)
                ]
            elif self.color_code:
                # use standard color palette (partly or looped if needed)
                if self.color_code not in COLOR_CODES:
                    raise Exception("Unknown color code")
                self.colors = [
                    get_color_by_colorcode_index(self.color_code, i)
                    for i in range(self.wirecount)
                ]
            elif self.color:
                self.colors = [self.color[w] for w in range(self.wirecount)]
            else:  # no colors defined, add dummy colors
                self.colors = [""] * self.wirecount

        else:  # wirecount implicit in length of color list
            if not self.colors:
                raise Exception(
                    "Unknown number of wires. "
                    "Must specify wirecount or colors (implicit length)"
                )
            self.wirecount = len(self.colors)

        if self.wirelabels:
            if self.shield and "s" in self.wirelabels:
                raise Exception(
                    '"s" may not be used as a wire label for a shielded cable.'
                )

        # if lists of part numbers are provided,
        # check this is a bundle and that it matches the wirecount.
        for idfield in [self.manufacturer, self.mpn, self.supplier, self.spn, self.pn]:
            if isinstance(idfield, list):
                if self.is_bundle:
                    # check the length
                    if len(idfield) != self.wirecount:
                        raise Exception("lists of part data must match wirecount")
                else:
                    raise Exception("lists of part data are only supported for bundles")

        # all checks have passed
        wire_tuples = zip_longest(
            # TODO: self.wire_ids
            self.colors,
            self.wirelabels,
        )
        for wire_index, (wire_color, wire_label) in enumerate(wire_tuples):
            id = wire_index + 1
            color = MultiColor(wire_color)[wire_index]
            by_idx = lambda x: x[wire_index] if isinstance(x, list) else x
            pn = by_idx(self.pn)
            manufacturer = by_idx(self.manufacturer)
            mpn = by_idx(self.mpn)
            supplier = by_idx(self.supplier)
            spn = by_idx(self.spn)

            self.wire_objects[id] = WireClass(
                pn=pn,
                manufacturer=manufacturer,
                mpn=mpn,
                supplier=supplier,
                spn=spn,
                parent=self.designator,
                # wire-specific properties
                index=wire_index,  # TODO: wire_id
                id=str(id),  # TODO: wire_id
                label=wire_label,
                color=color,
                # inheritable from parent cable
                type=self.type,
                subtype=self.subtype,
                gauge=self.gauge,
                length=self.length,
                ignore_in_bom=self.ignore_in_bom,
            )

        if self.shield:
            index_offset = len(self.wire_objects)
            # TODO: add support for multiple shields
            id = "s"
            self.wire_objects[id] = ShieldClass(
                index=index_offset,
                id=id,
                label="Shield",
                color=MultiColor(self.shield)
                if isinstance(self.shield, str)
                else MultiColor(None),
                parent=self.designator,
            )

        if self.show_name is None:
            self.show_name = not self.is_autogenerated

        for i, item in enumerate(self.additional_components):
            if isinstance(item, dict):
                self.additional_components[i] = Component(
                    **item, category=BomCategory.ADDITIONAL, parent=self.designator
                )

    def _connect(
        self,
        from_pin_obj: [PinClass],
        via_wire_id: str,
        to_pin_obj: [PinClass],
    ) -> None:
        via_wire_obj = self.wire_objects[via_wire_id]
        self._connections.append(Connection(from_pin_obj, via_wire_obj, to_pin_obj))

    def wire_ins(self, wire_id):
        return [
            str(c.from_)
            for c in self._connections
            if c.via.id == wire_id and c.from_ is not None
        ]

    def wire_ins_str(self, wire_id):
        return ", ".join(self.wire_ins(wire_id))

    def wire_outs(self, wire_id):
        return [
            str(c.to)
            for c in self._connections
            if c.via.id == wire_id and c.to is not None
        ]

    def wire_outs_str(self, wire_id):
        return ", ".join(self.wire_outs(wire_id))

    def compute_qty_multipliers(self):
        # do not run before all connections in harness have been made!
        total_length = sum(
            [
                wire.length.number if wire.length else 0
                for wire in self.wire_objects.values()
            ]
        )
        qty_multipliers_computed = {
            "WIRECOUNT": len(self.wire_objects),
            "TERMINATIONS": 999,  # TODO
            "LENGTH": self.length.number if self.length else 0,
            "TOTAL_LENGTH": total_length,
        }
        for subitem in self.additional_components:
            if isinstance(subitem.qty_multiplier, QtyMultiplierCable):
                computed_factor = qty_multipliers_computed[subitem.qty_multiplier.name]
                # inherit component's length unit if appropriate
                if subitem.qty_multiplier.name.upper() in ["LENGTH", "TOTAL_LENGTH"]:
                    if subitem.qty.unit is not None:
                        raise Exception(
                            f"No unit may be specified when using"
                            f"{subitem.qty_multiplier} as a multiplier"
                        )
                    subitem.qty = NumberAndUnit(subitem.qty.number, self.length.unit)

            elif isinstance(subitem.qty_multiplier, QtyMultiplierConnector):
                raise Exception("Used a connector multiplier in a cable!")
            else:  # int or float
                computed_factor = subitem.qty_multiplier
            subitem._qty_multiplier_computed = computed_factor
