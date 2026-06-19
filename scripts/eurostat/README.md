# Quickstart
Install requirements as described in root repo README. Download data using
`python scripts/eurostat/download.py`. Files are stored in `data/eurostat/`:
* download.log - script log output (errors!)
* dataset_list.xml - catalog of data + some meta information (description etc). Used to fetch IDs
* csv/ - raw, zstd compressed .csv files

Examine results using, e.g., `zstdcat data/eurostat/csv/edat_aes_l25.csv.zstd`
