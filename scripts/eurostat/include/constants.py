from pathlib import Path

DOWNLOAD_PATH = Path(__file__).parent.parent.parent.parent / "data" / "eurostat"
CSV_DOWNLOAD_PATH = DOWNLOAD_PATH / "csv"
OUTPUT_PATHS = [DOWNLOAD_PATH, CSV_DOWNLOAD_PATH]

MAX_PARALLEL_CONNECTIONS = 10
