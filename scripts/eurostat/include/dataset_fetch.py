import xml.etree.ElementTree as ET
import gzip
import requests


from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .constants import DOWNLOAD_PATH

DATAFLOW_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/dataflow/ESTAT/all/latest"
)
DATASET_URL_BASE = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1"


def _create_session() -> requests.Session:
    session = requests.Session()

    retries = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    return session


SESSION = _create_session()


def _decode_response_content(response):
    """Decode gziped response"""
    content = response.content

    # gzip magic bytes
    if content[:2] == b"\x1f\x8b":
        content = gzip.decompress(content)

    return content


def _fetch_raw_datasets_xml(cached: bool) -> ET.Element:
    """Download the eurostat dataset catalog in .xml"""
    OUTPATH = DOWNLOAD_PATH / "dataset_list.xml"

    if cached and OUTPATH.exists():
        with OUTPATH.open("rb") as f:
            return ET.fromstring(f.read())

    response = SESSION.get(DATAFLOW_URL, timeout=60)
    response.raise_for_status()

    content = _decode_response_content(response)
    root = ET.fromstring(content)

    # Add cached representation
    if cached:
        ET.indent(root, space="  ", level=0)
        tree = ET.ElementTree(root)
        with OUTPATH.open("wb") as file:
            tree.write(file, encoding="utf-8", xml_declaration=True)

    return root


def fetch_dataset_ids(cached: bool) -> set[str]:
    """
    Fetch available Eurostat dataset IDs.
    """
    XML_NAMESPACES = {
        "message": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message",
        "structure": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
        "common": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
    }
    datasets_xml = _fetch_raw_datasets_xml(cached=True)

    dataset_ids = set(
        elem.attrib.get("id")
        for elem in datasets_xml.findall(".//structure:Dataflow", XML_NAMESPACES)
    )
    return dataset_ids


def download_dataset(dataset_id: str) -> str:
    """
    Download SDMX structure definition XML.
    """
    url = f"{DATASET_URL_BASE}/data/{dataset_id}?format=SDMX-CSV"

    response = SESSION.get(
        url,
        timeout=120,
        headers={"Accept": "application/vnd.sdmx.data+csv"},
    )
    response.raise_for_status()

    return response.text
