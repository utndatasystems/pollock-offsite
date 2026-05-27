import logging

from include.constants import DOWNLOAD_PATH
from include.dataset_fetch import fetch_dataset_ids, download_dataset

log = logging.getLogger(__name__)

if __name__ == "__main__":
    DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(),
        ],
    )

    dataset_ids = fetch_dataset_ids(cached=True)
    log.info(f"Found {len(dataset_ids)} datasets")

    for id in dataset_ids:
        log.info(f"Fetching {id}")
        df = download_dataset(id)
        df.to_csv(path_or_buf=DOWNLOAD_PATH / f"{id.lower()}.csv", index=False)
        break
