from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from typing import Literal, cast

import pandas as pd

try:
    from .llm_utils import _extract_sections, _query_llm
except ImportError:
    from llm_utils import _extract_sections, _query_llm

try:
    from .build_prompt_utils import (
        PromptVersion,
        build_messages,
    )
except ImportError:
    from build_prompt_utils import (
        PromptVersion,
        build_messages,
    )

OutputFormat = Literal["fixed_csv", "reconstruction_json"]


def parse_csv(
    csv_path: str | Path,
    nrows: int | None = None,
    prompt_version: PromptVersion = "guided",
    encoding: str = "utf-8",) -> pd.DataFrame:
    """
    Parse and reconstruct a CSV file using a full-LLM parser.

    The source CSV is inserted into the selected prompt template. The LLM
    reconstructs the file, and the repaired CSV is loaded into pandas.

    Args:
        csv_path:
            Path to the CSV artifact.
        nrows:
            Optional number of reconstructed rows to return. The complete
            source file is still sent to the model.
        prompt_version:
            Prompt version to use: "naive" or "guided".
        encoding:
            Encoding used to read the source CSV.

    Returns:
        A DataFrame reconstructed from the LLM-generated CSV.

        Additional metadata is available through:

        - df.attrs["llm_error_report"]
        - df.attrs["llm_messages"]
        - df.attrs["llm_raw_output"]
        - df.attrs["llm_fixed_csv"]
        - df.attrs["llm_prompt_version"]
        - df.attrs["source_csv_path"]
    """
    path = Path(csv_path).expanduser().resolve()

    if not path.is_file():
        raise FileNotFoundError(f"CSV file does not exist: {path}")

    if nrows is not None and nrows < 0:
        raise ValueError("nrows must be non-negative or None")

    messages = build_messages(
        csv_path=path,
        version=prompt_version,
        encoding=encoding,
    )

    llm_output = _query_llm(messages)

    fixed_csv, error_report = _extract_sections(llm_output)

    if not fixed_csv.strip():
        raise ValueError("The LLM returned an empty fixed-CSV section")

    try:
        dataframe = pd.read_csv(
            StringIO(fixed_csv),
            nrows=nrows,
        )
    except pd.errors.ParserError:
        separator = _infer_separator(fixed_csv)

        try:
            dataframe = pd.read_csv(
                StringIO(fixed_csv),
                sep=separator,
                engine="python",
                nrows=nrows,
            )
        except (pd.errors.ParserError, ValueError) as exc:
            raise ValueError(
                "The LLM returned a fixed-CSV section, but pandas "
                "could not parse it."
            ) from exc

    dataframe.attrs["llm_error_report"] = error_report
    dataframe.attrs["llm_messages"] = messages
    dataframe.attrs["llm_raw_output"] = llm_output
    dataframe.attrs["llm_fixed_csv"] = fixed_csv
    dataframe.attrs["llm_prompt_version"] = prompt_version
    dataframe.attrs["source_csv_path"] = str(path)

    return dataframe


def _validate_fixed_csv(fixed_csv: str) -> str:
    """Perform basic validation on reconstructed CSV text."""
    if not isinstance(fixed_csv, str):
        raise ValueError(
            "The extracted fixed CSV must be a string, "
            f"received {type(fixed_csv).__name__}"
        )

    # Preserve internal and trailing newlines, but remove accidental whitespace
    # before the first CSV character.
    fixed_csv = fixed_csv.lstrip("\ufeff \t\r\n")

    if not fixed_csv:
        raise ValueError("The LLM returned an empty reconstructed CSV")

    if "\x00" in fixed_csv:
        raise ValueError("The reconstructed CSV contains null bytes")

    return fixed_csv


def _read_reconstructed_csv(
    fixed_csv: str,
    *,
    nrows: int | None,
) -> pd.DataFrame:
    """
    Parse reconstructed CSV text.

    The prompts should require comma-separated output, so comma is attempted
    first. Dialect fallback exists mainly to produce a usable result when the
    model violates the requested format.
    """
    parse_attempts: list[tuple[str, dict[str, object]]] = [
        (
            "standard comma-separated CSV",
            {
                "sep": ",",
                "engine": "c",
            },
        ),
        (
            "comma-separated CSV with Python engine",
            {
                "sep": ",",
                "engine": "python",
            },
        ),
    ]

    inferred_separator = _infer_separator(fixed_csv)

    if inferred_separator != ",":
        parse_attempts.append(
            (
                f"fallback separator {inferred_separator!r}",
                {
                    "sep": inferred_separator,
                    "engine": "python",
                },
            )
        )

    errors: list[str] = []

    for description, options in parse_attempts:
        try:
            return pd.read_csv(
                StringIO(fixed_csv),
                nrows=nrows,
                **options,
            )
        except (pd.errors.ParserError, UnicodeError, ValueError) as exc:
            errors.append(f"{description}: {exc}")

    formatted_errors = "\n".join(f"- {error}" for error in errors)

    raise RuntimeError(
        "The LLM response contained a fixed-CSV section, but pandas could "
        f"not parse it.\n\nAttempts:\n{formatted_errors}"
    )


def _infer_separator(csv_text: str) -> str:
    """
    Infer a likely separator from the first non-empty output line.

    This is only a fallback because the prompts should request comma-separated
    output explicitly.
    """
    first_line = next(
        (
            line
            for line in csv_text.splitlines()
            if line.strip()
        ),
        "",
    )

    candidates = [",", ";", "\t", "|"]

    return max(
        candidates,
        key=first_line.count,
        default=",",
    )


def _test_solution() -> None:
    csv_path = Path(
        "/home/neubauer/src/pollock-offsite/results/source.csv"
    )

    for version in ("naive", "guided"):
        print(f"\nRunning full-LLM parser with {version} prompt...")

        dataframe = parse_csv(
            csv_path=csv_path,
            prompt_version=version,
            nrows=5,
        )

        print(dataframe)

        print("\nPrompt version:")
        print(dataframe.attrs["llm_prompt_version"])

        print("\nLLM error report:")
        print(dataframe.attrs["llm_error_report"])


if __name__ == "__main__":
    _test_solution()