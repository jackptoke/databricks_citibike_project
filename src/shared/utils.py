"""Helpers for landing raw Citibike trip archives into a Unity Catalog Volume.

The pure functions here (`build_target_dir`, `select_single_csv`) are unit-tested
in `tests/unit/test_utils.py` without any network or Spark dependency.
"""

import os
import shutil
import tempfile
import zipfile

import requests


def build_target_dir(catalog: str, schema: str, volume: str, folder: str, year: int, month: int) -> str:
    """Return the UC Volume path a given year/month archive should land in.

    Example: build_target_dir("cat", "00_landing", "source_data", "citibike_trips", 2025, 9)
             -> "/Volumes/cat/00_landing/source_data/citibike_trips/2025-09"
    """
    folder_name = f"{folder}/{year:04d}-{month:02d}"
    return f"/Volumes/{catalog}/{schema}/{volume}/{folder_name}"


def select_single_csv(namelist: list[str]) -> str:
    """Pick the single real CSV member from a zip archive's name list.

    Ignores macOS resource forks (``__MACOSX/``) and dot-files. Raises
    ``ValueError`` unless exactly one CSV remains — Citibike archives are
    expected to contain precisely one data file.
    """
    csv_members = [
        m
        for m in namelist
        if m.lower().endswith(".csv") and not m.startswith("__MACOSX/") and not os.path.basename(m).startswith(".")
    ]
    if len(csv_members) != 1:
        raise ValueError(f"Expected exactly 1 CSV, found {len(csv_members)}: {csv_members}")
    return csv_members[0]


def download_and_extract(
    url: str,
    catalog: str,
    schema: str,
    volume: str,
    folder: str,
    year: int,
    month: int,
    overwrite: bool = True,
) -> tuple[str, bool]:
    """
    Download a zip from `url` and extract its single CSV into a UC Volume under
    a folder named by year/month, e.g. /Volumes/<catalog>/<schema>/<volume>/2025-09/

    Returns (target_dir, downloaded) where `downloaded` is True if the file was
    fetched and extracted, False if it was skipped because the folder already
    existed and overwrite=False. The volume itself must already exist.
    Raises ValueError if the zip does not contain exactly one CSV.
    """
    target_dir = build_target_dir(catalog, schema, volume, folder, year, month)

    already_present = os.path.isdir(target_dir) and len(os.listdir(target_dir)) > 0
    if already_present and not overwrite:
        print(f"Skipping - {target_dir} already populated (overwrite=False)")
        return target_dir, False

    # (Re)create a clean target folder
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)

    # Stream to local disk first - avoids per-chunk FUSE writes to the Volume
    tmp_zip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False).name
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(tmp_zip, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):  # 1 MB
                    f.write(chunk)

        with zipfile.ZipFile(tmp_zip) as z:
            member = select_single_csv(z.namelist())
            dest = os.path.join(target_dir, os.path.basename(member))
            with z.open(member) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)  # streamed copy, safe for large CSVs
    finally:
        os.remove(tmp_zip)

    print(f"Extracted {os.path.basename(dest)} into {target_dir}")
    return target_dir, True
