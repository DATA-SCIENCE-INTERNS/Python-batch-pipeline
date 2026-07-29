"""
NYC TLC Taxi Data Pipeline — CLI entry point.

Usage:
    python -m taxi_pipeline ingest --taxi-type yellow --year 2025 --month 1
    python -m taxi_pipeline backfill --taxi-type both --start 2025-01 --end 2025-03
"""
import sys

import click

from taxi_pipeline.extract import download_trip_data


def month_range(start: str, end: str):
    """Yield (year, month) tuples from 'YYYY-MM' start to end, inclusive."""
    sy, sm = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    y, m = sy, sm
    while (y, m) <= (ey, em):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def resolve_taxi_types(taxi_type: str) -> list[str]:
    return ["yellow", "green"] if taxi_type == "both" else [taxi_type]


@click.group()
def cli():
    """NYC TLC Taxi Data Pipeline CLI."""
    pass


@cli.command()
@click.option(
    "--taxi-type",
    type=click.Choice(["yellow", "green", "both"]),
    required=True,
)
@click.option("--year", type=int, required=True)
@click.option("--month", type=int, required=True)
def ingest(taxi_type, year, month):
    """Ingest one monthly batch for one or both taxi types."""
    taxi_types = resolve_taxi_types(taxi_type)
    failures = []

    for t in taxi_types:
        try:
            path = download_trip_data(taxi_type=t, year=year, month=month)
            click.echo(f"[ok] {t} {year}-{month:02d} -> {path}")
        except FileNotFoundError as e:
            click.echo(f"[skipped] {e}")
            failures.append((t, year, month))
        except Exception as e:
            click.echo(f"[error] {t} {year}-{month:02d}: {e}")
            failures.append((t, year, month))

    if failures:
        click.echo(f"\n{len(failures)} failure(s): {failures}")
        sys.exit(1)


@cli.command()
@click.option(
    "--taxi-type",
    type=click.Choice(["yellow", "green", "both"]),
    required=True,
)
@click.option("--start", required=True, help="YYYY-MM")
@click.option("--end", required=True, help="YYYY-MM")
def backfill(taxi_type, start, end):
    """Backfill a range of months for one or both taxi types."""
    taxi_types = resolve_taxi_types(taxi_type)
    failures = []

    for t in taxi_types:
        for year, month in month_range(start, end):
            try:
                path = download_trip_data(taxi_type=t, year=year, month=month)
                click.echo(f"[ok] {t} {year}-{month:02d} -> {path}")
            except FileNotFoundError as e:
                click.echo(f"[skipped] {e}")
                failures.append((t, year, month))
            except Exception as e:
                click.echo(f"[error] {t} {year}-{month:02d}: {e}")
                failures.append((t, year, month))

    if failures:
        click.echo(f"\n{len(failures)} failure(s): {failures}")
        sys.exit(1)


if __name__ == "__main__":
    cli()

    