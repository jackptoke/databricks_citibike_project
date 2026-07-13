"""Unit tests for landing-zone helpers (no network, no Spark)."""

import io
import zipfile

import pytest

from shared.utils import build_target_dir, select_single_csv


def test_build_target_dir_zero_pads_year_and_month():
    path = build_target_dir("cat", "00_landing", "source_data", "citibike_trips", 2025, 9)
    assert path == "/Volumes/cat/00_landing/source_data/citibike_trips/2025-09"


def test_build_target_dir_double_digit_month():
    path = build_target_dir("cat", "00_landing", "source_data", "citibike_trips", 2016, 12)
    assert path.endswith("/citibike_trips/2016-12")


def _zip_with(names: list[str]) -> zipfile.ZipFile:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n in names:
            z.writestr(n, "col_a,col_b\n1,2\n")
    buf.seek(0)
    return zipfile.ZipFile(buf)


def test_select_single_csv_picks_the_one_data_file():
    z = _zip_with(["JC-202509-citibike-tripdata.csv"])
    assert select_single_csv(z.namelist()) == "JC-202509-citibike-tripdata.csv"


def test_select_single_csv_ignores_macosx_and_dotfiles():
    z = _zip_with(
        [
            "__MACOSX/._JC-202509-citibike-tripdata.csv",
            ".DS_Store",
            "JC-202509-citibike-tripdata.csv",
        ]
    )
    assert select_single_csv(z.namelist()) == "JC-202509-citibike-tripdata.csv"


def test_select_single_csv_raises_when_none():
    z = _zip_with(["readme.txt"])
    with pytest.raises(ValueError, match="Expected exactly 1 CSV"):
        select_single_csv(z.namelist())


def test_select_single_csv_raises_when_multiple():
    z = _zip_with(["a.csv", "b.csv"])
    with pytest.raises(ValueError, match="found 2"):
        select_single_csv(z.namelist())
