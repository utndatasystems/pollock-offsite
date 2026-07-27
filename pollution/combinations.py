"""Utilities for applying multiple compatible pollutions to one CSV artifact."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

from .CSVFile import CSVFile
from .ground_truth import GroundTruthBundle
from .polluters_utils import _set_polluted_filename

PollutionStep = tuple[Callable[..., None], Mapping[str, Any]]


def apply_pollution_combination(
    file: CSVFile,
    steps: Sequence[PollutionStep],
    *,
    filename: str | None = None,
) -> CSVFile:
    """Apply two or more compatible pollutions to one shared copy.

    Combination steps must be reversible pollutions for which the unpolluted
    source table is a valid reconstruction. The returned artifact records the
    ordered operators and arguments in ``pollution_combination`` so
    ``CSVFile.write_parameters`` can persist the provenance.
    """
    if len(steps) < 2:
        raise ValueError("A combination must contain at least two pollutions")

    if filename is not None:
        output_name = Path(filename)
        if output_name.name != filename or output_name.suffix.lower() != ".csv":
            raise ValueError("filename must be a plain .csv filename")

    combined = deepcopy(file)
    source_rows = CSVFile.clean_rows(file)
    provenance = []
    filename_components = []

    for polluter, kwargs in steps:
        if not callable(polluter):
            raise TypeError("Every combination polluter must be callable")
        if not isinstance(kwargs, Mapping):
            raise TypeError("Every combination argument set must be a mapping")

        copied_kwargs = deepcopy(dict(kwargs))
        polluter(combined, **copied_kwargs)
        component = Path(combined.filename).stem
        if component.startswith("file_"):
            component = component.removeprefix("file_")
        filename_components.append(component)
        provenance.append(
            {
                "function": polluter.__name__,
                "name": getattr(polluter, "pollution_name", None),
                "category": getattr(polluter, "pollution_category", None),
                "arguments": copied_kwargs,
            }
        )

    combined.ground_truth_bundle = GroundTruthBundle.single(
        source_rows,
        accept_origin=True,
    )
    combined.clean_rows_override = source_rows
    combined.pollution_combination = {"pollutions": provenance}
    if filename is None:
        filename = f"combo__{'__'.join(filename_components)}.csv"
    _set_polluted_filename(combined, filename)
    return combined
