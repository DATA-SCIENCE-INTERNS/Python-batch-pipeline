import pytest

from taxi_pipeline.__main__ import month_range
from taxi_pipeline.extract import build_bronze_path, build_download_url


def test_build_download_url_uses_requested_base_url():
    assert build_download_url("yellow", 2025, 1, "https://example.test/") == (
        "https://example.test/yellow_tripdata_2025-01.parquet"
    )


def test_build_bronze_path_is_partitioned():
    path = build_bronze_path("green", 2025, 12, "bronze")
    assert path.as_posix() == (
        "bronze/green/2025/12/green_tripdata_2025-12.parquet"
    )


def test_month_range_crosses_year_boundary():
    assert list(month_range("2025-11", "2026-02")) == [
        (2025, 11), (2025, 12), (2026, 1), (2026, 2)
    ]


def test_invalid_month_is_rejected():
    with pytest.raises(ValueError):
        build_download_url("yellow", 2025, 13)
