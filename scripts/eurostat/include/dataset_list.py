import logging
import xml.etree.ElementTree as ET
import gzip

from .constants import DOWNLOAD_PATH, SESSION

DATAFLOW_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/dataflow/ESTAT/all/latest"
)
XML_NAMESPACES = {
    "message": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message",
    "structure": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
    "common": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
}


def _decode_response_content(response):
    """Decode gziped response"""
    content = response.content

    # gzip magic bytes
    if content[:2] == b"\x1f\x8b":
        content = gzip.decompress(content)

    return content


def _fetch_datasets(log: logging.Logger, cached: bool) -> ET.Element:
    """Download the eurostat dataset catalog in .xml"""
    OUTPATH = DOWNLOAD_PATH / "dataset_list.xml"

    if cached and OUTPATH.exists():
        log.info(f"Using cached dataset list '{OUTPATH}'")
        with OUTPATH.open("rb") as f:
            return ET.fromstring(f.read())

    log.info(f"Fetching dataset list '{OUTPATH}'")
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


def fetch_dataset_ids(log: logging.Logger = logging.getLogger(__name__)) -> set[str]:
    """
    Fetch available Eurostat dataset IDs.
    """
    datasets_xml = _fetch_datasets(log=log, cached=True)

    dataset_ids = set(
        elem.attrib.get("id")
        for elem in datasets_xml.findall(".//structure:Dataflow", XML_NAMESPACES)
    )
    return dataset_ids
