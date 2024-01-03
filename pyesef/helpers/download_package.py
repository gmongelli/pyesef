"""Helper function to download a XBRL-package."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
from  urllib import request
from urllib.parse import quote, unquote
from urllib.error import HTTPError

import requests

from ..const import PATH_ARCHIVES, Country

BASE_URL = "https://filings.xbrl.org/"


@dataclass
class Filing:
    """Represent a filing."""

    country: str
    file_name: str
    path: str


IdentifierType = dict[str, list[Filing]]


def _parse_file_ending(path: str) -> str:
    """Parse the file ending."""
    path = path.lower()
    splitted_path = path.split("/")
    country_iso = splitted_path[-2]
    return country_iso


def _cleanup_package_dict(identifier_map: IdentifierType) -> list[Filing]:
    """
    Cleanup package dict and return only one filing.

    Will return the English version if available.
    """
    data_list: list[Filing] = []
    for key, _ in identifier_map.items():
        filing_list = identifier_map[key]

        for filing in filing_list:
            data_list.append(filing)

    return data_list


def download_packages() -> None:
    """
    Download XBRL-packages from XBRL.org.

    Prefer the English version of there are multiple languages available.
    """
    identifier_map: IdentifierType = {}
    idx: int = 0

    with request.urlopen(f"{BASE_URL}api/filings?page[number]=0&page[size]=999999") as url:
        data = json.loads(url.read().decode())
        for _, item in enumerate(data["data"]):
            try:
                if True:
                    package_url = item["attributes"]["package_url"]
                    if package_url is None:
                        continue
                    else:
                        package_url = unquote(package_url)
                    lei = os.path.basename(unquote(item["relationships"]["entity"]["links"]["related"]))
                    filing = Filing(
                        country=item["attributes"]["country"],
                        file_name=os.path.basename(package_url),
                        path=os.path.dirname(package_url),
                    )

                    if lei not in identifier_map:
                        identifier_map[lei] = [filing]
                    else:
                        identifier_map[lei].append(filing)
            except KeyError as e:
                print(f"KeyError: {e} for entry {item['id']}, it will be ignored")

    data_list = _cleanup_package_dict(identifier_map=identifier_map)

    print(f"{len(data_list)} items found")  # noqa: T201

    for idx, item in enumerate(data_list):
        if idx % 10 == 0:
            print(f"Parsing {idx}/{len(data_list)}")  # noqa: T201

        _download_package(item)


def _download_package(filing: Filing) -> None:
    """Download a package and store it the archive-folder."""
    url = f"{BASE_URL}{filing.path}/{quote(filing.file_name)}"

    download_path = os.path.join(PATH_ARCHIVES, filing.path[1:])

    # Create download path if it does not exist
    Path(download_path).mkdir(parents=True, exist_ok=True)

    print(f"Downloading {url}")  # noqa: T201


    write_location = os.path.join(download_path, filing.file_name)
    if not os.path.exists(write_location):
        try:
            request.urlretrieve(url, write_location)
        except HTTPError as e:
            if e.code == 404:
                print(f"Skipping download of {url}")
