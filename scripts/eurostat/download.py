import logging
import zstandard as zstd

from tqdm import tqdm
from multiprocessing import Pool

from include.constants import (
    DOWNLOAD_PATH,
    CSV_DOWNLOAD_PATH,
    OUTPUT_PATHS,
    MAX_PARALLEL_CONNECTIONS,
)
from include.dataset_fetch import fetch_dataset_ids, download_dataset

log = logging.getLogger(__name__)


def download_and_save(dataset_id: str) -> tuple[str, str]:
    output_path = CSV_DOWNLOAD_PATH / f"{dataset_id.lower()}.csv.zstd"
    try:
        if not output_path.exists():
            dataset_str = download_dataset(dataset_id)
            with output_path.open("wb") as f:
                cctx = zstd.ZstdCompressor(level=10)
                with cctx.stream_writer(f) as compr:
                    compr.write(dataset_str.encode("utf-8"))
        return (dataset_id, output_path, None)
    except Exception as e:
        return (dataset_id, output_path, str(e))


if __name__ == "__main__":
    for path in OUTPUT_PATHS:
        path.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(filename=DOWNLOAD_PATH / "download.log"),
        ],
    )

    dataset_ids = fetch_dataset_ids(cached=True)
    log.info(f"Found {len(dataset_ids)} datasets")

    with Pool(MAX_PARALLEL_CONNECTIONS) as pool:
        results = pool.imap_unordered(
            download_and_save,
            dataset_ids,
        )

        for dataset_id, output_path, error in tqdm(results, total=len(dataset_ids)):
            if error is None:
                continue

            log.error(f"Failed to download {dataset_id} to '{output_path}': {error}")
