import logging

from include.constants import DOWNLOAD_PATH
from include.dataset_list import fetch_dataset_ids

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

    dataset_ids = fetch_dataset_ids()
    log.info(f"Found {len(dataset_ids)} datasets: {dataset_ids}")
