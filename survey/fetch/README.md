# survey/fetch

A reusable, dependency-light CLI that downloads CSV datasets from public open-data
catalogs and writes a sha256-deduplicated manifest. Part of the
[`pollock-survey`](https://github.com/HPI-Information-Systems/Pollock) pipeline,
but runnable on its own.

## Quickstart

```bash
pip install -r survey/fetch/requirements.txt
python -m survey.fetch data.gov --out-dir /tmp/pollock --max-files 100
```

Resulting `manifest.csv`:

```
origin,url,sha256,bytes,source,picked_reason,fetched_at,local_path
data.gov,https://example.org/x.csv,3c6e0b...,12345,data.gov,datagov:Some dataset,2026-06-03T12:34:56Z,/tmp/pollock/raw/data.gov/csv/x.csv
...
```

Re-running the same command is idempotent: rows whose sha256 is already in the
manifest are skipped (the staged file is unlinked).

License: TBD (will be added before public release).

## What this does

Open-data catalogs publish CSV files behind pagination, redirects, mixed
formats, and sometimes hostile sizes. `survey.fetch` walks each catalog's
search API, filters for CSV-shaped distributions, streams downloads to disk
under a per-file byte cap (with `O_EXCL` collision-safe naming), validates
each body via magic-byte sniffing, and appends a manifest row only when the
hash is novel. State (next-page cursor, bytes-used) lives in a single atomic
JSON file under the out-dir so killed runs resume cleanly.

## Installation

Requires **Python 3.10+** (PEP 604 `X | Y` syntax is used throughout).

```bash
pip install -r survey/fetch/requirements.txt
```

The only runtime dependency is `tqdm`. The wider survey pipeline has its own
`requirements.txt` at the repo root; this stage stands alone.

For running tests: `pip install pytest` (or `pip install pytest tqdm` on a
fresh venv).

## Manifest schema

One row per staged file. Columns (from
`survey.fetch.manifest.MANIFEST_FIELDS`):

| Column          | Description |
|-----------------|-------------|
| `origin`        | Catalog name (`data.gov`, `data.gov.uk`, `data.europa.eu`). |
| `url`           | Source URL the body was fetched from. |
| `sha256`        | Hex digest of the raw downloaded bytes. Dedup key. |
| `bytes`         | Size in bytes of the file on disk. |
| `source`        | Catalog sub-source / dataset id when the backend tracks one; otherwise the same as `origin`. |
| `picked_reason` | Free-form provenance note (e.g. `datagov:<dataset title>`). |
| `fetched_at`    | ISO-8601 UTC timestamp of the successful download. |
| `local_path`    | Absolute path to the staged file on disk. |

The manifest is append-only and atomic. `ManifestWriter` flushes every 25
rows by default and on `__exit__`.

## Per-backend caveats

### `data.gov` (US federal catalog)

The CKAN-3 action API at `catalog.data.gov/api/3/action/...` was
discontinued around **May 2026** and now returns 404. We use the htmx JSON
search endpoint that backs the public HTML UI:

```
GET https://catalog.data.gov/search?q=csv&per_page=20&sort=popularity[&after=<cursor>]
```

Pagination is opaque base-64 cursors in the `after` field. The cursor is
persisted to `.pollock_survey_state.json` under `datagov_cursors[<query>]`,
saved *before* the page's candidates are yielded so a cap-hit mid-page is
safe (sha-dedup keeps a re-run idempotent across the boundary).

The `--datagov-query` flag overrides the search term (default: `csv`).

### `data.gov.uk` (CKAN)

The public `data.gov.uk` portal is a static HTML site; the underlying CKAN
instance lives at `https://ckan.publishing.service.gov.uk`. Override either way:

- `--endpoint <URL>` flag (preferred)
- `CKAN_DATA_GOV_UK_URL` env var (legacy fallback when no `--endpoint`)

Resume offset (`start=`) is stored under `ckan_cursors[<source>]` in
`.pollock_survey_state.json`.

### `data.europa.eu` (EU Open Data Portal)

**Catalog size warning**: ~1.7M datasets. A single full crawl takes hours
and will saturate `--max-bytes` on default settings; use `--max-files` for
bounded test runs.

Distributions point at national publishers (data.gov.ua, opendata.gov.fr, ...)
rather than a unified EU CDN. **HEAD support is uneven** and `byte_size` is
frequently absent; the per-file streaming cap is the real safety net.

The page cursor is stored as `data_europa_eu_next_page` in
`.pollock_survey_state.json`.

### Stubbed backends (`inside_airbnb`, `hf`, `kaggle`)

Deferred past v1. The stubs are registered so they show up in `--help` and
exit `2` with a pointer to this README's roadmap.

## Roadmap

- `inside_airbnb`: walk `http://insideairbnb.com/get-the-data` and pull the
  per-city CSV bundles, screened against the size cap.
- `hf`: Hugging Face Hub via the `huggingface_hub` Python package; iterate
  CSV-shaped files in dataset repositories.
- `kaggle`: official `kaggle` Python package with API-token auth; one
  candidate per CSV file in selected datasets.

All three will plug into the same `Backend` protocol and `download_loop`,
so the manifest schema and dedup behaviour stay identical across backends.

## Configuration reference

### Environment variables

| Variable                       | Default | Effect |
|--------------------------------|---------|--------|
| `POLLOCK_SURVEY_LOG_LEVEL`     | `INFO`  | Root log level for `survey.fetch.*` loggers. |
| `POLLOCK_SURVEY_USER_AGENT`    | neutral | Override the outbound `User-Agent` header. |
| `CKAN_DATA_GOV_UK_URL`         | unset   | Fallback CKAN endpoint for `data.gov.uk`. |

The default User-Agent is
`pollock-survey/0.1 (+https://github.com/HPI-Information-Systems/Pollock)`.

### CLI flags

Shared across every backend (see `python -m survey.fetch <backend> --help`):

- `--out-dir PATH` (required): where the manifest, state, and staged files live.
- `--max-files N`: hard ceiling on manifest rows added this run.
- `--max-bytes SPEC`: total-bytes ceiling (`50G`, `500M`, `2K`, or raw int).
- `--per-file-cap-bytes SPEC`: abort downloads bigger than this (default `200M`).
- `--concurrency N`: worker threads (default `8`).
- `--dry-run`: list candidates without staging.
- `--user-agent STR`: override the User-Agent string.
- `--compress {none,gzip,zstd}`: currently parsed but no-op; uncompressed CSVs
  are stored verbatim.
- `-q` / `--quiet`, `-v` / `--verbose`: log-level shortcuts.

Backend-specific flags appear before the shared flags in `--help`:

- `data.gov`: `--datagov-query <str>` (default `csv`).
- `data.gov.uk`: `--endpoint <url>`.
- `data.europa.eu`: none.

## Contributing: registering a new backend

1. Create a module at `survey/fetch/<name>.py` exposing four module-level
   attributes:
   - `name: str`: registry key (e.g. `"my_catalog"`).
   - `add_subparser(sp)`: registers the argparse subparser; call
     `_backend.add_common_args(p)` to inherit the shared flags.
   - `options_from_args(args)`: return a typed options dataclass.
   - `run(opts) -> int`: drive the fetch; return a process exit code.
2. Add it to the `BACKENDS` registry in
   `survey/fetch/__init__.py:_build_registry`.
3. Add a smoke test under `survey/fetch/tests/test_backends_smoke.py` that
   mocks `_http._OPENER` and asserts the manifest+state shape.

The `Backend` Protocol in `survey/fetch/_backend.py` is the source of truth
for the four-callable contract. Use `Protocol` (not ABC) so each backend
stays a plain module.
