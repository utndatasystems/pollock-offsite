from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Literal

import pandas as pd

try:
    from .llm_utils import _extract_sections, _query_llm, _clean_fixed_csv
except ImportError:
    from llm_utils import _extract_sections, _query_llm, _clean_fixed_csv

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

#TODO: implement a fucntion to time the llm query. Also, is there a way to save the cost of the llm query?
#TODO: print statement to see if it is being executing with OpenAI or OLLAMA
def parse_csv(
    csv_path: str | Path,
    nrows: int | None = None,
    prompt_version: PromptVersion = "guided",
    encoding: str = "utf-8",
    verbose: bool = False,
) -> pd.DataFrame:
    """
    Parses and reconstructs a CSV file using a full-LLM parser.

    1) Source CSV is read and inserted into a prompt template.
    2) The prompt is sent to the LLM, which returns a fixed CSV and
       an error report in JSON format.
    3) The fixed CSV is validated by parsing it with pandas, and the error
       report is attached to the resulting DataFrame's attributes.

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
        verbose:
            Print the raw LLM response when True.

    Returns:
        A DataFrame parsed from the LLM-generated CSV for validation and
        inspection. Benchmark output should use df.attrs["llm_fixed_csv"]
        directly to avoid an additional pandas serialization step.

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

    # Builds the prompt messages for the LLM, including the source CSV content.
    messages = build_messages(
        csv_path=path,
        version=prompt_version,
        encoding=encoding,
    )

    # Queries the LLM with the prompt and retrieves the output.
    llm_output = _query_llm(messages, verbose=verbose)
    if verbose:
        print("\n--- RAW LLM OUTPUT START ---")
        print(llm_output)
        print("--- RAW LLM OUTPUT END ---\n")

    # Strip of Markdown for some models
    llm_output = _clean_fixed_csv(llm_output)

    # Extracts the fixed CSV and JSON error report from the LLM output.
    fixed_csv, error_report = _extract_sections(llm_output)

    fixed_csv = _validate_fixed_csv(fixed_csv)
    if fixed_csv:
        dataframe = _read_reconstructed_csv(fixed_csv, nrows=nrows)
    else:
        dataframe = pd.DataFrame()

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
                dtype=str,
                keep_default_na=False,
                na_filter=False,
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


def _real_test_solution() -> None:
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

        print("\nReconstructed DataFrame:")
        print(dataframe)

        print("\nPrompt version:")
        print(dataframe.attrs["llm_prompt_version"])

        print("\nLLM error report:")
        print(dataframe.attrs["llm_error_report"])


if __name__ == "__main__":
    _real_test_solution()