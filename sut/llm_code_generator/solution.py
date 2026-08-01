import hashlib
import json
import os
import tempfile
import time
import urllib.request
from collections import Counter, OrderedDict
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
from llm_utils import _LLM_RESPONSE_CACHE, _LLM_CALL_STATS, _LLM_CACHE_PATH, _LLM_CACHE_ENABLED, _LLM_CACHE_LOADED, _LLM_DRY_RUN, _save_cache_to_disk, _ensure_cache_loaded, TraceWriter, call_llm, _extract_json_object, _read_sample_lines, _read_scoring_lines, _decode_token, _valid_delimiter, _valid_char, _valid_newline, _safe_nonnegative_int, sniff_with_clevercsv, _dialect_from_mapping, infer_dialect_with_llm, parse_record, _score_dialect, reconcile_dialects, _header_lines, combine_header_rows, infer_expected_columns, _unique_duckdb_columns, _sql_string, _sql_bool, _sql_columns, _records_from_df, load_with_duckdb, _coerce_cell, finalize_dataframe, rejects_to_malformed, find_width_rejects, merge_rejects, _good_examples, _dedupe_rejects_for_prompt, infer_repairs_with_llm


DEFAULT_OPENAI_ENDPOINT = "http://dep-eng-data-s-heimgarten.hosts.utn.de:4000/v1/chat/completions"
DEFAULT_OPENAI_MODEL = "gpt-5.4" #"gpt-5.4-mini"
TRACE_VERSION = 1

_LLM_RESPONSE_CACHE: Dict[str, str] = {}
_LLM_DRY_RUN_ESTIMATED_OUTPUT: Dict[str, int] = {}  # prompt_sha -> estimated chars for dry-run dedup
_LLM_CACHE_PATH: Optional[str] = None
_LLM_CACHE_ENABLED: bool = True
_LLM_CACHE_LOADED: bool = False
_LLM_CALL_STATS: Dict[str, int] = {
    "total": 0, "cached": 0,
    "input_chars_total": 0, "input_chars_cached": 0,
    "output_chars_fresh": 0, "output_chars_cached": 0,
}
_LLM_DRY_RUN: bool = False


# Step 1 - prepare setup for llm call including loading the prompt from prompt.txt


# Step 2 - call the model and convert the output into a Python object


# Step 3 - execute the gegenerated python codecontaining the function parse_csv_test(text:str, delimiter: str = ",")on the input data and return the result



text = Path("data.csv").read_text(encoding="utf-8-sig")
records = parse_csv_to_dicts(text)