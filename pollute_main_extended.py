"""
Orchestrator for extended-pollution engines.

Each engine lives in `pollock/polluters_<engine>.py` and exposes a module-level
list `POLLUTIONS`. Each entry is one of:

    ("filename.csv", callable, kwargs_dict)

where `callable` is either:

  * a function (file: CSVFile, **kwargs) -> None
        — mutates the CSVFile in place; clean + parameters + polluted CSV are
          rendered by the standard XML pipeline.

  * a `RawBytePolluter` instance
        — produces clean + parameters via the standard pipeline, then runs
          a byte-level mutator on the rendered CSV.

Usage:

    python3 pollute_main_extended.py --engine unicode --output data/extended_unicode

If `--engine` is `all`, every available engine is run into the same output
directory (used by the smoke test, not the parallel attack run).
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys
from copy import deepcopy

from pollock.CSVFile import CSVFile
from pollock.polluters_extended import RawBytePolluter
from sut.utils import print as tprint


KNOWN_ENGINES = ["unicode", "quote", "typeinfer", "lineend", "struct", "dialect", "smoke"]


def _execute_xml(source_file: CSVFile, polluter, new_filename: str, kwargs: dict,
                 out_csv: str, out_clean: str, out_parameters: str) -> None:
    """Run an XML-mutating polluter and render via the standard pipeline."""
    f = deepcopy(source_file)
    polluter(f, **kwargs)
    f.filename = new_filename
    f.xml.getroot().attrib["filename"] = new_filename
    f.write_csv(out_csv)
    f.write_clean_csv(out_clean)
    f.write_parameters(out_parameters)


def _execute_raw(source_file: CSVFile, polluter: RawBytePolluter, new_filename: str,
                 out_csv: str, out_clean: str, out_parameters: str) -> None:
    polluter.apply(source_file, out_csv, out_clean, out_parameters, new_filename)


def _load_engine(engine_name: str):
    module_name = f"pollock.polluters_{engine_name}"
    return importlib.import_module(module_name)


def _engine_pollutions(engine_name: str):
    module = _load_engine(engine_name)
    pollutions = getattr(module, "POLLUTIONS", None)
    if pollutions is None:
        raise RuntimeError(
            f"Engine module '{module.__name__}' has no POLLUTIONS list. "
            f"Each engine must define POLLUTIONS = [(filename, callable, kwargs), ...]."
        )
    return pollutions


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="./results/source.csv",
                   help="Source CSV to pollute")
    p.add_argument("--engine", required=True,
                   help=f"Engine name. One of: {', '.join(KNOWN_ENGINES)}, or 'all'.")
    p.add_argument("--output", default=None,
                   help="Output dataset root. Defaults to data/extended_<engine>.")
    p.add_argument("--clean", action="store_true",
                   help="Wipe existing csv/ dir before generating")
    args = p.parse_args()

    out_root = args.output or f"./data/extended_{args.engine}"
    out_csv = os.path.join(out_root, "csv/")
    out_clean = os.path.join(out_root, "clean/")
    out_parameters = os.path.join(out_root, "parameters/")
    os.makedirs(out_csv, exist_ok=True)
    os.makedirs(out_clean, exist_ok=True)
    os.makedirs(out_parameters, exist_ok=True)
    if args.clean:
        os.system(f"cd {out_csv} && rm -f *.csv")
        os.system(f"cd {out_clean} && rm -f *.csv")
        os.system(f"cd {out_parameters} && rm -f *.json")

    engines = KNOWN_ENGINES if args.engine == "all" else [args.engine]
    if args.engine != "all" and args.engine not in KNOWN_ENGINES:
        # Allow ad-hoc engine names too — only require the module exists.
        engines = [args.engine]

    source_file = CSVFile(args.source, quote_all=True)

    total = 0
    for eng in engines:
        try:
            pollutions = _engine_pollutions(eng)
        except ModuleNotFoundError as e:
            tprint(f"Skipping engine '{eng}': {e}")
            continue
        tprint(f"Engine '{eng}': {len(pollutions)} pollutions")
        for entry in pollutions:
            if len(entry) == 3:
                name, callable_, kwargs = entry
            else:
                name, callable_ = entry
                kwargs = {}
            try:
                if isinstance(callable_, RawBytePolluter):
                    _execute_raw(source_file, callable_, name,
                                 out_csv, out_clean, out_parameters)
                else:
                    _execute_xml(source_file, callable_, name, kwargs,
                                 out_csv, out_clean, out_parameters)
                total += 1
            except Exception as e:
                tprint(f"  FAILED {name}: {e}")
    tprint(f"Generated {total} pollutions in {out_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
