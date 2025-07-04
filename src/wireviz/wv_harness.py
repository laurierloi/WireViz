# -*- coding: utf-8 -*-

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from graphviz import Graph

import wireviz.wv_colors
from wireviz import APP_NAME, APP_URL, __version__
from wireviz.metadata import Metadata
from wireviz.notes import Notes
from wireviz.page_options import PageOptions
from wireviz.wv_bom import BomContent, BomRenderOptions
from wireviz.wv_dataclasses import BomCategory, Cable, Component, Connector, Side
from wireviz.wv_graphviz import (
    gv_connector_loops,
    gv_edge_wire,
    gv_node_cable,
    gv_node_connector,
    set_dot_basics,
)
from wireviz.wv_output import (
    embed_svg_images_file,
    generate_html_output,
    generate_pdf_output,
)
from wireviz.wv_templates import get_template


@dataclass
class Harness:
    metadata: Metadata
    options: PageOptions
    notes: Notes
    additional_bom_items: List[Component] = field(default_factory=list)
    shared_bom: Dict = field(default_factory=dict)

    def __post_init__(self):
        self.connectors = {}
        self.cables = {}
        self.bom = {}
        self.additional_bom_items = []

    @property
    def name(self) -> str:
        return self.metadata.name

    def add_connector(self, designator: str, *args, **kwargs) -> None:
        conn = Connector(designator=designator, *args, **kwargs)
        self.connectors[designator] = conn

    def add_cable(self, designator: str, *args, **kwargs) -> None:
        cbl = Cable(designator=designator, *args, **kwargs)
        self.cables[designator] = cbl

    def add_additional_bom_item(self, item: dict) -> None:
        new_item = Component(**item, category=BomCategory.ADDITIONAL)
        self.additional_bom_items.append(new_item)

    def populate_bom(self):
        # helper lists
        all_toplevel_items = (
            list(self.connectors.values())
            + list(self.cables.values())
            + self.additional_bom_items
        )
        all_subitems = [
            subitem
            for item in all_toplevel_items
            for subitem in item.additional_components
        ]
        all_bom_relevant_items = (
            list(self.connectors.values())
            + [cable for cable in self.cables.values() if cable.category != "bundle"]
            + [
                wire
                for cable in self.cables.values()
                if cable.category == "bundle"
                for wire in cable.wire_objects.values()
            ]
            + self.additional_bom_items
            + all_subitems
        )

        def add_to_bom(entry):
            if isinstance(entry, list):
                for e in entry:
                    add_to_bom(e)
                return

            if hash(entry) in self.bom:
                self.bom[hash(entry)] += entry
            else:
                self.bom[hash(entry)] = entry

            try:
                self.bom[hash(entry)]
            except KeyError:
                raise RuntimeError(
                    f"BomEntry's hash is not persitent: h1:{hash(entry)} h2:{hash(entry)}\n\tentry: {entry}\n\titem:{item}"
                )

        # add items to BOM
        for item in all_bom_relevant_items:
            if item.ignore_in_bom:
                continue
            add_to_bom(item.bom_entry)

        # sort BOM by category first, then alphabetically by description within category
        self.bom = dict(
            sorted(
                self.bom.items(),
                key=lambda x: (
                    x[1].category,
                    x[1].description,
                ),  # x[0] = key, x[1] = value
            )
        )

        next_id = len(self.shared_bom) + 1
        # TODO: for each harness, track a (harness_name, qty) pair
        def get_per_harness(v):
            d = {
                "qty": v["qty"],
            }
            return (self.name, d)

        for key, values in self.bom.items():
            if key in self.shared_bom:
                self.shared_bom[key]["qty"] += values["qty"]
                values["id"] = self.shared_bom[key]["id"]
            else:
                self.shared_bom[key] = values
                self.shared_bom[key]["id"] = next_id
                values["id"] = next_id
                next_id += 1

            k, v = get_per_harness(values)
            self.shared_bom[key].per_harness[k] = v

        # print(f'bom length: {len(self.bom)}, shared_bom length: {len(self.shared_bom)}') # for debugging

        # set BOM IDs within components (for BOM bubbles)
        for item in all_bom_relevant_items:
            if item.ignore_in_bom:
                continue
            if hash(item) not in self.bom:
                continue
            item.id = self.bom[hash(item)].id

        self.bom = dict(
            sorted(
                self.bom.items(),
                key=lambda x: (x[1].id,),
            )
        )
        # from wireviz.wv_bom import print_bom_table ; print_bom_table(self.bom)  # for debugging

    def connect(
        self,
        from_name: str,
        from_pin: (int, str),
        via_name: str,
        via_wire: (int, str),
        to_name: str,
        to_pin: (int, str),
    ) -> None:
        def clean_pin(pin):
            """Allow for a pin of the form "PINLABEL__PINNUMBER"

            This is a bit treacherous, because we actually allow PINNUMBER which are not int.
            When this happens, the pinnumber will be considered as a pinlabel.
            The logic below should handle that case

            """
            pinlabel = None
            pinnumber = None
            if isinstance(pin, str):
                if "__" in pin:
                    pinlabel, pinnumber = pin.split("__")
                    pinnumber = int(pinnumber)
                else:
                    try:
                        pinnumber = int(pin)
                    except ValueError:
                        pinlabel = pin
            if isinstance(pin, int):
                pinnumber = pin
            return pinlabel, pinnumber

        # check from and to connectors
        for (name, (pinlabel, pinnumber)) in zip(
            [from_name, to_name], [clean_pin(from_pin), clean_pin(to_pin)]
        ):
            if name is None or name not in self.connectors:
                continue

            connector = self.connectors[name]

            pinlabel_indexes = None
            pinnumber_index = None

            if pinlabel is not None:
                pinlabel_indexes = [
                    i for i, x in enumerate(connector.pinlabels) if x == pinlabel
                ]
                if len(pinlabel_indexes) == 0:
                    pinlabel_indexes = None
                    if pinlabel in connector.pins:
                        pinnumber = pinlabel
                    else:
                        raise ValueError(
                            f"Pinlabel {pinlabel} is not in pinlabels of connector {name}"
                        )

            if pinnumber is not None:
                pinnumber_indexes = [
                    i for i, x in enumerate(connector.pins) if x == pinnumber
                ]
                if len(pinnumber_indexes) > 1:
                    raise ValueError(
                        f"Pinnumber {pinnumber} is not unique in pins of connector {name}"
                    )
                pinnumber_index = pinnumber_indexes[0]
                if pinlabel_indexes is not None:
                    if pinnumber_index not in pinlabel_indexes:
                        raise ValueError(
                            f"No pinnumber {pinnumber} matches pinlabel {pinlabel} in connector {name}, pinlabel for that pinnumber is {connector.pinlabels[pinnumber_index]}"
                        )
            elif pinlabel_indexes is not None:
                if len(pinlabel_indexes) > 1:
                    pinnumber_indexes = [connector.pins[i] for i in pinlabel_indexes]
                    raise ValueError(
                        f"Pinlabel {pinlabel} is not unique in pinlabels of connector {name} (available pins are: {pinnumber_indexes}), and no pinnumber defined to disambiguate\nThe user can define a pinnumber by using the form PINLABEL__PINNUMBER, where the double underscore is the separator"
                    )
                pinnumber_index = pinlabel_indexes[0]

            if pinnumber_index is None:
                raise ValueError(
                    f"Neither pinlabel ({pinlabel}) or pinnumber ({pinnumber}) where found on connector {name}, pinlabels: {connector.pinlabels}, pinnumbers: {connector.pins})"
                )

            pin = connector.pins[pinnumber_index]
            if name == from_name:
                from_pin = pin
            if name == to_name:
                to_pin = pin

        # check via cable
        if via_name in self.cables:
            cable = self.cables[via_name]
            # check if provided name is ambiguous
            if via_wire in cable.colors and via_wire in cable.wirelabels:
                if cable.colors.index(via_wire) != cable.wirelabels.index(via_wire):
                    raise Exception(
                        f"{via_name}:{via_wire} is defined both in colors and wirelabels, "
                        "for different wires."
                    )
                # TODO: Maybe issue a warning if present in both lists
                # but referencing the same wire?
            if via_wire in cable.colors:
                if cable.colors.count(via_wire) > 1:
                    raise Exception(
                        f"{via_name}:{via_wire} is used for more than one wire."
                    )
                # list index starts at 0, wire IDs start at 1
                via_wire = cable.colors.index(via_wire) + 1
            elif via_wire in cable.wirelabels:
                if cable.wirelabels.count(via_wire) > 1:
                    raise Exception(
                        f"{via_name}:{via_wire} is used for more than one wire."
                    )
                via_wire = (
                    cable.wirelabels.index(via_wire) + 1
                )  # list index starts at 0, wire IDs start at 1

        # perform the actual connection
        if from_name is not None:
            from_con = self.connectors[from_name]
            from_pin_obj = from_con.pin_objects[from_pin]
        else:
            from_pin_obj = None
        if to_name is not None:
            to_con = self.connectors[to_name]
            to_pin_obj = to_con.pin_objects[to_pin]
        else:
            to_pin_obj = None

        try:
            self.cables[via_name]._connect(from_pin_obj, via_wire, to_pin_obj)
        except Exception as e:
            logging.warning(
                f"fail to connect cable {via_name}, from_pin: {from_pin}, via_wire: {via_wire}, to_pin: {to_pin}\n\texception:{e}"
            )
            raise
        if from_name in self.connectors:
            self.connectors[from_name].activate_pin(from_pin, Side.RIGHT)
        if to_name in self.connectors:
            self.connectors[to_name].activate_pin(to_pin, Side.LEFT)

    def create_graph(self) -> Graph:
        dot = Graph()
        set_dot_basics(dot, self.options)

        for connector in self.connectors.values():
            # generate connector node
            template_html = gv_node_connector(connector)
            dot.node(
                connector.designator,
                label=f"<\n{template_html}\n>",
                shape="box",
                style="filled",
            )
            # generate edges for connector loops
            if len(connector.loops) > 0:
                dot.attr("edge", color="#000000")
                loops = gv_connector_loops(connector)
                for loop, head, tail in loops:
                    dot.edge(head, tail, xlabel=loop.label)

        # determine if there are double- or triple-colored wires in the harness;
        # if so, pad single-color wires to make all wires of equal thickness
        wire_is_multicolor = [
            len(wire.color) > 1
            for cable in self.cables.values()
            for wire in cable.wire_objects.values()
        ]
        if any(wire_is_multicolor):
            wireviz.wv_colors.padding_amount = 3
        else:
            wireviz.wv_colors.padding_amount = 1

        for cable in self.cables.values():
            # generate cable node
            template_html = gv_node_cable(cable)
            # For debugging:
            # print('\n'.join([f'l. {idx:03}: {line}' for idx, line in enumerate(template_html.split('\n'))]))
            style = "filled,dashed" if cable.category == "bundle" else "filled"
            dot.node(
                cable.designator,
                label=f"<\n{template_html}\n>",
                shape="box",
                style=style,
            )

            # generate wire edges between component nodes and cable nodes
            for connection in cable._connections:
                color, l1, l2, r1, r2 = gv_edge_wire(self, cable, connection)
                dot.attr("edge", color=color)
                if not (l1, l2) == (None, None):
                    dot.edge(l1, l2)
                if not (r1, r2) == (None, None):
                    dot.edge(r1, r2)

        return dot

    # cache for the GraphViz Graph object
    # do not access directly, use self.graph instead
    _graph = None

    @property
    def graph(self):
        if not self._graph:  # no cached graph exists, generate one
            self._graph = self.create_graph()
        return self._graph  # return cached graph

    @property
    def png(self):
        from io import BytesIO

        graph = self.graph
        data = BytesIO()
        data.write(graph.pipe(format="png"))
        data.seek(0)
        return data.read()

    @property
    def svg(self):
        graph = self.graph
        return embed_svg_images(graph.pipe(format="svg").decode("utf-8"), Path.cwd())

    def output(
        self,
        filename: (str, Path),
        view: bool = False,
        cleanup: bool = True,
        fmt: tuple = ("html", "png", "svg", "tsv"),
    ) -> None:
        # graphical output
        graph = self.graph

        rendered = set()
        for f in fmt:
            if f in ("png", "svg", "html"):
                if f == "html":  # if HTML format is specified,
                    f = "svg"  # generate SVG for embedding into HTML
                # SVG file will be renamed/deleted later
                if f in rendered:
                    continue
                graph.format = f
                graph.render(filename=filename, view=view, cleanup=cleanup)
                rendered.add(f)
        # embed images into SVG output
        if "svg" in fmt or "html" in fmt:
            embed_svg_images_file(filename.with_suffix(".svg"))
        # GraphViz output
        if "gv" in fmt:
            graph.save(filename=filename.with_suffix(".gv"))
        # BOM output
        if "tsv" in fmt:
            bom_render = BomContent(self.bom).get_bom_render(
                options=BomRenderOptions(
                    restrict_printed_lengths=False,
                )
            )
            filename.with_suffix(".tsv").open("w").write(bom_render.as_tsv())
        if "csv" in fmt:
            # TODO: implement CSV output (preferrably using CSV library)
            print("CSV output is not yet supported")
        # HTML output
        if "html" in fmt:
            generate_html_output(
                filename, self.bom, self.metadata, self.options, self.notes
            )
        # PDF output
        if "pdf" in fmt:
            generate_pdf_output(filename)
        # delete SVG if not needed
        if "html" in fmt and not "svg" in fmt:
            # SVG file was just needed to generate HTML
            filename.with_suffix(".svg").unlink()
