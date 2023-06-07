# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path

import click


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import wireviz.wireviz as wv
from wireviz import APP_NAME, __version__
from wireviz.wv_output import (
    generate_pdf_output,
    generate_html_output,
    generate_shared_bom,
    generate_titlepage,
)
from wireviz.parse_yaml import parse_merge_files
from wireviz.wv_dataclasses import AUTOGENERATED_PREFIX
from wireviz.metadata import Metadata
from wireviz.page_options import PageOptions

format_codes = {
    "c": "csv",
    "g": "gv",
    "h": "html",
    "p": "png",
    "P": "pdf",
    "s": "svg",
    "t": "tsv",
    "b": "shared_bom",
}

epilog = (
    "The -f or --formats option accepts a string containing one or more of the "
    "following characters to specify which file types to output:\n"
    + f", ".join([f"{key} ({value.upper()})" for key, value in format_codes.items()])
)


@click.command(epilog=epilog, no_args_is_help=True)
@click.argument(
    "files",
    type=click.Path(
        exists=True,
        readable=True,
        dir_okay=False,
        path_type=Path,
    ),
    nargs=-1,
    required=True,
)
@click.option(
    "-f",
    "--formats",
    default="hpst",
    type=str,
    show_default=True,
    help="Output formats (see below).",
)
@click.option(
    "-c",
    "--components",
    default=[],
    multiple=True,
    type=click.Path(
        exists=True,
        readable=True,
        file_okay=True,
        path_type=Path,
    ),
    help="YAML file containing component templates, prepended to each harness (optional).",
)
@click.option(
    "-d",
    "--metadata",
    default=[],
    multiple=True,
    type=click.Path(
        exists=True,
        readable=True,
        file_okay=True,
        path_type=Path,
    ),
    help="YAML file containing metadata/options, are merged to each harness content (optional).",
)
@click.option(
    "-o",
    "--output-dir",
    default=None,
    type=click.Path(
        exists=True,
        readable=True,
        file_okay=False,
        dir_okay=True,
        path_type=Path,
    ),
    help="Directory to use for output files, if different from input file directory.",
)
@click.option(
    "-O",
    "--output-name",
    default=None,
    type=str,
    help=(
        "File name (without extension) to use for output files, "
        "if different from input file name."
    ),
)
@click.option(
    "-V",
    "--version",
    is_flag=True,
    default=False,
    help=f"Output {APP_NAME} version and exit.",
)
@click.option(
    "-u",
    "--use-qty-multipliers",
    is_flag=True,
    type=bool,
    help="if set, the shared bom counts will be scaled with the qty-multipliers",
)
@click.option(
    "-m",
    "--multiplier-file-name",
    default="quantity_multipliers.txt",
    type=str,
    help="name of file used to fetch the qty_multipliers",
)
def cli(
    files,
    formats,
    components,
    metadata,
    output_dir,
    output_name,
    version,
    use_qty_multipliers,
    multiplier_file_name,
):
    """
    Parses the provided FILE and generates the specified outputs.
    """
    if version:
        print(f"{APP_NAME} {__version__}")
        return  # print version number only and exit


    # ensure files are sorted
    files_list = list(files)
    files_list.sort()
    files = tuple(files_list)
    _output_dir = files[0].parent if not output_dir else output_dir

    # determine output formats
    output_formats = {format_codes[f] for f in formats if f in format_codes}
    harness_output_formats = output_formats.copy()
    shared_bom = {}

    # TODO: all of this metadata should be defined within a dataclass
    extra_metadata = {}
    extra_metadata["output_dir"] = _output_dir
    extra_metadata["files"] = files
    extra_metadata["output_names"] = [_file.stem for _file in files]
    extra_metadata["sheet_total"] = len(files)
    extra_metadata["sheet_current"] = 1
    extra_metadata["use_qty_multipliers"] = use_qty_multipliers
    extra_metadata["multiplier_file_name"] = multiplier_file_name

    # Only generate the global pdf if there's multiple files
    create_titlepage = False
    if extra_metadata["sheet_total"] > 1:
        create_titlepage = True
        extra_metadata["titlepage"] = Path("titlepage")
        extra_metadata["output_names"].insert(0, "titlepage")
        extra_metadata["sheet_current"] += 1
        extra_metadata["sheet_total"] += 1

        if "pdf" in harness_output_formats:
            harness_output_formats.remove("pdf")
    else:
        extra_metadata["titlepage"] = None


    # run WireVIz on each input file
    for _file in files:
        _output_name = _file.stem

        print("Input file:  ", _file)
        print(
            "Output file: ",
            f"{_output_dir / _output_name}.[{'|'.join(output_formats)}]",
        )

        extra_metadata["sheet_name"] = _output_name.upper()

        file_dir = _file.parent

        ret = wv.parse(
            components + (_file,),
            metadata_files=metadata,
            return_types=("shared_bom"),
            output_formats=harness_output_formats,
            output_dir=_output_dir,
            extra_metadata=extra_metadata,
            shared_bom=shared_bom,
        )
        shared_bom = ret["shared_bom"]
        extra_metadata["sheet_current"] += 1

    shared_bom_base = None
    if "shared_bom" in output_formats:
        shared_bom_base = generate_shared_bom(
            _output_dir,
            shared_bom,
            use_qty_multipliers=use_qty_multipliers,
            files=files,
            multiplier_file_name=multiplier_file_name,
        )

    if ("html" in output_formats) and create_titlepage:
        yaml_data = parse_merge_files(metadata)

        generate_titlepage(yaml_data, extra_metadata, shared_bom)

        if "pdf" in output_formats:
            extra_metadata["titlepage"] = extra_metadata["titlepage"].with_stem(
                extra_metadata["titlepage"].stem + "_for_pdf"
            )

            generate_titlepage(yaml_data, extra_metadata, shared_bom, for_pdf=True)

    if "pdf" in output_formats:
        generate_pdf_output([_output_dir / p for p in extra_metadata["output_names"]])

    print()  # blank line after execution


if __name__ == "__main__":
    cli()
