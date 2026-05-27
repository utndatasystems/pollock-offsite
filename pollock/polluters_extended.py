"""
Shared infrastructure for the "extended pollutions" attack engines.

The standard polluters in `polluters_stdlib.py` mutate the XML representation
of a CSV in `CSVFile`, which then renders the polluted file via XSLT in the
file's declared encoding. That works well for delimiter / quote / structural
attacks, but is awkward for byte-level attacks (BOMs, mixed encodings, NUL
bytes, invalid UTF-8 sequences, Unicode line separators that don't survive
the XSL pipeline...).

`RawBytePolluter` provides a second pollution mechanism that runs alongside
the XML pipeline:

  1. Caller passes a `CSVFile` already initialized from `source.csv` and a
     callable `byte_mutator(raw_bytes: bytes, file: CSVFile) -> bytes`.
  2. We render the (un-mutated) CSV via the standard XML pipeline to produce
     the canonical clean CSV and parameters JSON, exactly as the standard
     polluters do.
  3. The polluted CSV bytes are produced by:
       a. rendering the in-memory XML to a string,
       b. encoding it with the file's declared encoding,
       c. handing the resulting bytes to `byte_mutator`,
       d. writing the returned bytes to disk verbatim.

The `clean/` and `parameters/` outputs are intentionally identical to what
the XML pipeline would have produced — the *parser* sees the mutated bytes,
but the *evaluator* compares against an honest clean rendering.

Engines that prefer to work in XML space can ignore this module entirely
and just import `polluters_base` like the standard polluters do.
"""
from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Callable

from lxml import etree

from .CSVFile import CSV_XSL, CSVFile


def _render_csv_text(file: CSVFile) -> str:
    xslt = etree.XML(CSV_XSL)
    transform = etree.XSLT(xslt)
    return str(transform(file.xml))


class RawBytePolluter:
    """Run a byte-level mutation on the rendered CSV, leaving clean+parameters honest.

    Use this when your attack needs to manipulate bytes the XML pipeline can't
    represent (BOMs, embedded NULs, invalid UTF-8, mixed encodings).
    """

    def __init__(self, name: str, mutator: Callable[[bytes, CSVFile], bytes],
                 description: str = ""):
        self.name = name
        self.mutator = mutator
        self.description = description

    def apply(self, source_file: CSVFile, out_csv_dir: str, out_clean_dir: str,
              out_parameters_dir: str, new_filename: str) -> None:
        f = deepcopy(source_file)
        f.filename = new_filename
        f.xml.getroot().attrib["filename"] = new_filename

        # Honest clean + parameters via the standard pipeline.
        Path(out_clean_dir).mkdir(parents=True, exist_ok=True)
        Path(out_parameters_dir).mkdir(parents=True, exist_ok=True)
        f.write_clean_csv(out_clean_dir)
        f.write_parameters(out_parameters_dir)

        # Render base bytes, then mutate, then write polluted output.
        text = _render_csv_text(f)
        try:
            base_bytes = text.encode(f.encoding)
        except (LookupError, UnicodeEncodeError):
            base_bytes = text.encode("utf-8")
        polluted = self.mutator(base_bytes, f)

        Path(out_csv_dir).mkdir(parents=True, exist_ok=True)
        with open(os.path.join(out_csv_dir, new_filename), "wb") as out:
            out.write(polluted)


def execute_raw(source_file: CSVFile, polluter: RawBytePolluter, new_filename: str,
                out_csv_dir: str, out_clean_dir: str, out_parameters_dir: str) -> None:
    polluter.apply(source_file, out_csv_dir, out_clean_dir, out_parameters_dir,
                   new_filename)
