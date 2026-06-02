"""Survey-wide configuration constants.

Keep this file dependency-free so every other module can import it cheaply.
Real defaults that need other modules (e.g. paths derived from the repo root)
live next to their consumers.
"""

from pathlib import Path

SCHEMA_VERSION = 2

REPO_ROOT = Path(__file__).resolve().parent.parent
SURVEY_ROOT = REPO_ROOT / "survey"
DEFAULT_OUT_DIR = SURVEY_ROOT / "out"

# Reuse the seed used by the rest of the project so survey-wide sampling
# (Tier 3 random sample, manifest shuffle) lines up with pollock/constants.py.
RAND_SEED = 27

# Budgets — overridable on the CLI.
DEFAULT_BUDGET_USD = 450.0  # 10% headroom under the user-stated $500 cap.
DEFAULT_MAX_BYTES = 50 * 1024 * 1024 * 1024  # 50 GB.
DEFAULT_AMBIGUITY_THRESHOLD = 0.30
DEFAULT_DISCOVER_SAMPLE = 250

# Per-source corpus targets used by the fetcher when no overrides are passed.
PER_SOURCE_FILE_TARGETS = {
    "data.gov": 2500,
    "data.gov.uk": 2500,
    "github": 2000,
    "hf": 1000,
    "kaggle": 500,
}

# Big-file oversample bucket: targets ~5% of total corpus by count from
# files >10 MB, split as 50% wide-rows / 30% wide-fields / 20% many-rows.
BIG_FILE_THRESHOLD_BYTES = 10 * 1024 * 1024
BIG_FILE_BUCKET_PCT = 0.05
BIG_FILE_BUCKET_SPLIT = {"wide_rows": 0.50, "wide_fields": 0.30, "many_rows": 0.20}

# Sampling caps for big-file annotation (Tier 1).
SAMPLE_HEAD_LINES = 200
SAMPLE_TAIL_LINES = 50
SAMPLE_BYTES_THRESHOLD = 5 * 1024 * 1024

# Default LLM models.
DEFAULT_TRIAGE_MODEL = "claude-haiku-4-5"
DEFAULT_TRIAGE_ESCALATION_MODEL = "claude-sonnet-4-6"
DEFAULT_DISCOVERY_MODEL = "claude-haiku-4-5"

# Pollution-flag taxonomy. Tier 1 detectors emit one entry per name. Names
# match the Pollock paper's survey annotations 1:1 where applicable; the
# "new" group is research-backed (Pytheas, Hypoparsr, CleverCSV, Muppets,
# SchemaPile, SemTab) and may be promoted to "stable" once Tier 4 P/R/F1
# meets the gate.
POLLOCK_ORIGINAL_FLAGS = (
    "file_name_nonalnum",
    "file_name_nonalnum_nounderscore",
    "table_multiple_tables",
    "table_no_header",
    "table_multirow_header",
    "table_preamble_rows",
    "table_footnote_rows",
    "table_columns_less_than_2",
    "table_columns_more_256",
    "table_lines_less_2",
    "table_lines_more_65k",
    "table_not_crlf_delimiter",
    "table_not_comma_delimiter",
    "table_not_double_quote",
    "table_not_escape_quote",
    "row_inconsistent_n_delimiter",
    "row_inconsistent_record_delimiter",
    "row_inconsistent_field_delimiter",
    "row_inconsistent_quotation",
    "row_inconsistent_escape",
    "column_header_unique",
    "column_header_non_alnum",
    "column_header_empty",
    "column_header_long",
    "column_formats_heterogeneous",
    "column_string_boundary",
    "column_int_boundary",
    "column_date_boundary",
)

NEW_CANDIDATE_FLAGS = (
    "bom_present",
    "has_comment_lines",
    "line_art_row_present",
    "locale_european_numbers",
    "multiline_cell_present",
    "missing_value_qualifier_diverse",
    "aggregated_row_present",
    "units_in_values",
    "ambiguous_delimiter",
    "sniffer_low_confidence",
    "leading_trailing_whitespace_in_header",
    "mixed_quote_styles",
    "dialect_unparseable",
)

# Non-boolean annotation values.
SCALAR_ANNOTATION_FIELDS = ("dimension", "encoding_flag", "jagged_rows_count")

ALL_ANNOTATION_FIELDS = (
    POLLOCK_ORIGINAL_FLAGS + NEW_CANDIDATE_FLAGS + SCALAR_ANNOTATION_FIELDS
)
