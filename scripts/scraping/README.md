# CSV Scraping Helpers

These scripts collect public CSV files into the Pollock benchmark layout:

```text
data/<dataset>/csv/         raw files for SUTs
data/<dataset>/clean/       expected files, mirrored from raw downloads
data/<dataset>/parameters/  dialect metadata used by dialect-aware SUTs
data/<dataset>/metadata/    scraper manifest
```

## Proof of Concept

```bash
python3 scripts/scraping/poc_download.py
DATASET=web_csv_poc python3 ./sut/pandas/panda.py
python3 evaluate.py --sut pandas --dataset web_csv_poc
```

## Scrape Eurostat and Data.gov

```bash
python3 scripts/scraping/scrape_csvs.py \
  --dataset web_csv_dump \
  --sources eurostat,datagov \
  --max-files 20 \
  --max-mb 25 \
  --eurostat-prefixes TPS,TEI \
  --data-gov-query "transportation csv"
```

Then run a benchmark target against that dataset:

```bash
DATASET=web_csv_dump python3 ./sut/pandas/panda.py
python3 evaluate.py --sut pandas --dataset web_csv_dump
```

Data.gov uses the GSA CKAN API. Set `DATA_GOV_API_KEY` for a real key; otherwise the script uses `DEMO_KEY`.

Eurostat discovery uses the official inventory endpoint and downloads the `Data download url (csv)` field. Keep a prefix filter and a file-size cap, otherwise it is easy to ask for much more data than intended.
