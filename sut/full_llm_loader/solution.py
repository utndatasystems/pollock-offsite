from io import StringIO
from itertools import islice
import pandas as pd

try:
    from .llm_utils import _build_prompt, _extract_sections, _query_llm
except ImportError:
    from llm_utils import _build_prompt, _extract_sections, _query_llm

def parse_csv(csv_path: str, nrows: int | None = None) -> pd.DataFrame:
    """
    Parses CSV file and returns a repaired pandas DataFrame.

    This function reads the raw CSV text from the provided file path, sends the
    corrupted content to an LLM for repair, and then loads the fixed CSV output
    with pandas.

    The returned DataFrame contains two extra attributes:
    - df.attrs["llm_error_report"]: structured JSON describing the repairs.
    - df.attrs["llm_prompt"]: the exact prompt that was sent to the LLM.

    Args:
        csv_path: Filesystem path to the corrupted CSV file.
        nrows: Optional number of data rows to parse from the start of the CSV.

    Returns:
        A pandas DataFrame built from the repaired CSV text and:
            df.attrs["llm_error_report"] contains a structured JSON report of the repairs.
            df.attrs["llm_prompt"] contains the prompt sent to the LLM for debugging and


    Raises:
        EnvironmentError: if OPENAI_API_KEY is not set in the environment.
        ValueError: if the LLM output cannot be parsed or is malformed.
        requests.HTTPError: if the OpenAI/LLM request fails.
    """

    with open(csv_path, "r", encoding="utf-8", errors="replace") as handle:
        if nrows is None:
            corrupted_csv = handle.read()
        else:
            if nrows < 0:
                raise ValueError("nrows must be non-negative")
            corrupted_csv = "".join(islice(handle, nrows + 1))

    prompt = _build_prompt(corrupted_csv)
    llm_output = _query_llm(prompt)
    fixed_csv, error_report = _extract_sections(llm_output)

    try:
        df = pd.read_csv(StringIO(fixed_csv), nrows=nrows)
    except pd.errors.ParserError:
        first_line = fixed_csv.splitlines()[0] if fixed_csv else ""
        if ";" in first_line and first_line.count(";") >= first_line.count(","):
            sep = ";"
        elif "\t" in first_line and first_line.count("\t") >= first_line.count(","):
            sep = "\t"
        else:
            sep = ","
        df = pd.read_csv(StringIO(fixed_csv), sep=sep, engine="python", nrows=nrows)

    df.attrs["llm_error_report"] = error_report
    df.attrs["llm_prompt"] = prompt
    return df
