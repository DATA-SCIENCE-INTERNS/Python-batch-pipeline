from pathlib import Path
from typing import Literal

import requests


TaxiType = Literal["yellow", "green"]

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"


def build_download_url(
    taxi_type: TaxiType,
    year: int,
    month: int,
) -> str:
    """Create the official NYC TLC download URL."""

    if taxi_type not in {"yellow", "green"}:
        raise ValueError("Taxi type must be yellow or green.")

    if month < 1 or month > 12:
        raise ValueError("Month must be between 1 and 12.")

    filename = f"{taxi_type}_tripdata_{year}-{month:02d}.parquet"

    return f"{BASE_URL}/{filename}"


def build_bronze_path(
    taxi_type: TaxiType,
    year: int,
    month: int,
    bronze_directory: str | Path = "data/bronze",
) -> Path:
    """Create the Bronze-layer file path."""

    filename = f"{taxi_type}_tripdata_{year}-{month:02d}.parquet"

    return (
        Path(bronze_directory)
        / taxi_type
        / str(year)
        / f"{month:02d}"
        / filename
    )


def download_trip_data(
    taxi_type: TaxiType,
    year: int,
    month: int,
    bronze_directory: str | Path = "data/bronze",
    overwrite: bool = False,
) -> Path:
    """Download one monthly taxi dataset."""

    url = build_download_url(
        taxi_type=taxi_type,
        year=year,
        month=month,
    )

    destination = build_bronze_path(
        taxi_type=taxi_type,
        year=year,
        month=month,
        bronze_directory=bronze_directory,
    )

    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and not overwrite:
        print(f"Skipping existing file: {destination}")
        return destination

    temporary_file = destination.with_suffix(".parquet.part")

    print(f"Downloading {taxi_type} data for {year}-{month:02d}")

    try:
        with requests.get(
            url,
            stream=True,
            timeout=(10, 300),
        ) as response:

            if response.status_code == 404:
                raise FileNotFoundError(
                    f"Dataset unavailable: {taxi_type} "
                    f"{year}-{month:02d}"
                )

            response.raise_for_status()

            with temporary_file.open("wb") as output_file:
                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if chunk:
                        output_file.write(chunk)

        if temporary_file.stat().st_size == 0:
            raise ValueError("The downloaded file is empty.")

        temporary_file.replace(destination)

        print(f"Completed: {destination}")

        return destination

    except Exception:
        if temporary_file.exists():
            temporary_file.unlink()

        raise

def ingest_year(
    year: int,
    taxi_types: list[TaxiType],
    bronze_directory: str | Path = "data/bronze",
) -> dict:
    """
    Download all available monthly files for the selected year.

    Example:
        ingest_year(
            year=2025,
            taxi_types=["yellow", "green"],
        )
    """

    successful_files: list[Path] = []
    failed_downloads: list[str] = []

    print("=" * 60)
    print(f"Starting ingestion for {year}")
    print(f"Taxi types: {', '.join(taxi_types)}")
    print("=" * 60)

    for taxi_type in taxi_types:
        for month in range(1, 13):

            try:
                downloaded_file = download_trip_data(
                    taxi_type=taxi_type,
                    year=year,
                    month=month,
                    bronze_directory=bronze_directory,
                )

                successful_files.append(downloaded_file)

            except FileNotFoundError as error:
                print(f"Skipped: {error}")
                failed_downloads.append(str(error))

            except requests.RequestException as error:
                message = (
                    f"Network error for {taxi_type} "
                    f"{year}-{month:02d}: {error}"
                )

                print(message)
                failed_downloads.append(message)

            except Exception as error:
                message = (
                    f"Unexpected error for {taxi_type} "
                    f"{year}-{month:02d}: {error}"
                )

                print(message)
                failed_downloads.append(message)

    results = {
        "year": year,
        "successful_count": len(successful_files),
        "failed_count": len(failed_downloads),
        "successful_files": successful_files,
        "failed_downloads": failed_downloads,
    }

    print("=" * 60)
    print("Ingestion completed")
    print(f"Successful files: {results['successful_count']}")
    print(f"Failed or unavailable files: {results['failed_count']}")
    print("=" * 60)

    return results