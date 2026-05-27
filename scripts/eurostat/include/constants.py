import requests

from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DOWNLOAD_PATH = Path(__file__).parent.parent.parent.parent / "data" / "eurostat"


def _create_session() -> requests.Session:
    session = requests.Session()

    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    return session


SESSION = _create_session()
