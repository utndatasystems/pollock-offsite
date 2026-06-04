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

DEFAULT_MAX_BYTES = 50 * 1024 * 1024 * 1024  # 50 GB.

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
