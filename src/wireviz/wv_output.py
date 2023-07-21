# -*- coding: utf-8 -*-

import base64
import logging
import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Dict, List, Union

from weasyprint import HTML

import wireviz  # for doing wireviz.__file__
from wireviz.index_table import IndexTable
from wireviz.metadata import Metadata
from wireviz.notes import Notes, get_page_notes
from wireviz.page_options import PageOptions, get_page_options
from wireviz.wv_bom import BomContent, BomRenderOptions
from wireviz.wv_harness_quantity import HarnessQuantity
from wireviz.wv_templates import get_template

mime_subtype_replacements = {"jpg": "jpeg", "tif": "tiff"}


def embed_svg_images(svg_in: str, base_path: Union[str, Path] = Path.cwd()) -> str:
    images_b64 = {}  # cache of base64-encoded images

    def image_tag(pre: str, url: str, post: str) -> str:
        return f'<image{pre} xlink:href="{url}"{post}>'

    def replace(match: re.Match) -> str:
        imgurl = match["URL"]
        if not imgurl in images_b64:  # only encode/cache every unique URL once
            imgurl_abs = (Path(base_path) / imgurl).resolve()
            image = imgurl_abs.read_bytes()
            images_b64[imgurl] = base64.b64encode(image).decode("utf-8")
        return image_tag(
            match["PRE"] or "",
            f"data:image/{get_mime_subtype(imgurl)};base64, {images_b64[imgurl]}",
            match["POST"] or "",
        )

    pattern = re.compile(
        image_tag(r"(?P<PRE> [^>]*?)?", r'(?P<URL>[^"]*?)', r"(?P<POST> [^>]*?)?"),
        re.IGNORECASE,
    )
    return pattern.sub(replace, svg_in)


def get_mime_subtype(filename: Union[str, Path]) -> str:
    mime_subtype = Path(filename).suffix.lstrip(".").lower()
    if mime_subtype in mime_subtype_replacements:
        mime_subtype = mime_subtype_replacements[mime_subtype]
    return mime_subtype


def embed_svg_images_file(
    filename_in: Union[str, Path], overwrite: bool = True
) -> None:
    filename_in = Path(filename_in).resolve()
    filename_out = filename_in.with_suffix(".b64.svg")
    filename_out.write_text(
        embed_svg_images(filename_in.read_text(), filename_in.parent)
    )
    if overwrite:
        filename_out.replace(filename_in)


def generate_pdf_output(
    filename_list: List[Path],
):
    """Generate a pdf output"""
    if isinstance(filename_list, Path):
        filename_list = [filename_list]
        output_path = filename_list[0].with_suffix(".pdf")
    else:
        output_dir = filename_list[0].parent
        output_path = (output_dir / output_dir.name).with_suffix(".pdf")

    filepath_list = [f.with_suffix(".html") for f in filename_list]

    print(f"Generating pdf output: {output_path}")
    files_html = [HTML(path) for path in filepath_list]
    documents = [f.render() for f in files_html]
    all_pages = [p for doc in documents for p in doc.pages]
    documents[0].copy(all_pages).write_pdf(output_path)


def generate_shared_bom(
    output_dir,
    shared_bom,
    use_qty_multipliers=False,
    files=None,
    multiplier_file_name=None,
):
    shared_bom_base = output_dir / "shared_bom"
    shared_bom_file = shared_bom_base.with_suffix(".tsv")
    print(f"Generating shared bom at {shared_bom_base}")

    if use_qty_multipliers:
        harnesses = HarnessQuantity(files, multiplier_file_name, output_dir=output_dir)
        harnesses.fetch_qty_multipliers_from_file()
        print(f"Using quantity multipliers: {harnesses.multipliers}")
        for bom_item in shared_bom.values():
            bom_item.scale_per_harness(harnesses.multipliers)

    bom_render = BomContent(shared_bom).get_bom_render(
        options=BomRenderOptions(
            restrict_printed_lengths=False,
            filter_entries=True,
            no_per_harness=False,
            reverse=False,
        )
    )

    shared_bom_file.open("w").write(bom_render.as_tsv())

    return shared_bom_base


# TODO: should define the dataclass needed to avoid doing any dict shuffling in here
def generate_html_output(
    filename: Path,
    bom: List[List[str]],
    metadata: Metadata,
    options: PageOptions,
    notes: Notes,
    rendered: Dict[str, str] = None,
    bom_render_options: BomRenderOptions = None,
):
    print("Generating html output")
    assert metadata and isinstance(metadata, Metadata), "metadata should be defiend"
    template_name = metadata.template.name

    if rendered is None:
        rendered = {}

    if bom_render_options is None:
        bom_render_options = BomRenderOptions(
            restrict_printed_lengths=True,
            filter_entries=True,
            no_per_harness=True,
            reverse=metadata.template.has_bom_reversed(),
        )

    bom_render = BomContent(bom).get_bom_render(options=bom_render_options)
    options.bom_rows = bom_render.rows
    rendered["bom"] = bom_render.render(options=options)

    # TODO: instead provide a PageOption to generate or not the svg
    svgdata = None
    if template_name != "titlepage":
        # embed SVG diagram for all but the titlepage
        with filename.with_suffix(".svg").open("r") as f:
            svgdata = re.sub(
                "^<[?]xml [^?>]*[?]>[^<]*<!DOCTYPE [^>]*>",
                "<!-- XML and DOCTYPE declarations from SVG file removed -->",
                f.read(),
                1,
            )

    replacements = {
        "options": options,
        "diagram": svgdata,
        "metadata": metadata,
        "notes": notes,
    }

    # TODO: all rendering should be done within their respective classes

    # prepare titleblock
    rendered["titleblock"] = get_template("titleblock.html").render(replacements)

    # preparate Notes
    if "notes" in replacements and replacements["notes"].notes:
        rendered["notes"] = get_template("notes.html").render(replacements)

    # generate page template
    page_rendered = get_template(template_name, ".html").render(
        {
            **replacements,
            **rendered,
        }
    )

    # save generated file
    filename.with_suffix(".html").open("w").write(page_rendered)


def generate_titlepage(yaml_data, extra_metadata, shared_bom, for_pdf=False):
    print("Generating titlepage")

    titlepage_metadata = {
        **yaml_data.get("metadata", {}),
        **extra_metadata,
        "sheet_current": 1,
        "sheet_name": "titlepage",
        "output_name": "titlepage",
    }
    titlepage_metadata["template"]["name"] = "titlepage"
    metadata = Metadata(**titlepage_metadata)
    index_table = IndexTable.from_pages_metadata(metadata)

    bom_render_options = BomRenderOptions(
        restrict_printed_lengths=False,
        filter_entries=True,
        no_per_harness=True,
        reverse=False,
    )

    # todo: index table options as a dataclass
    options = get_page_options(yaml_data, "titlepage")
    options.bom_updated_position = "top: 20mm; left: 10mm"
    options.for_pdf = for_pdf

    generate_html_output(
        extra_metadata["output_dir"] / extra_metadata["titlepage"],
        bom=shared_bom,
        metadata=metadata,
        options=options,
        notes=get_page_notes(yaml_data, "titlepage"),
        rendered={"index_table": index_table.render(options)},
        bom_render_options=bom_render_options,
    )
