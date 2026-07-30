"""Command-line interface for the NYC TLC taxi batch pipeline."""
import logging
import os

import click

from taxi_pipeline.config import load_settings
from taxi_pipeline.pipeline import run_batch


def month_range(start: str, end: str):
    """Yield inclusive (year, month) tuples from two YYYY-MM values."""
    sy, sm = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    if not (1 <= sm <= 12 and 1 <= em <= 12):
        raise click.BadParameter("Dates must use valid months in YYYY-MM format.")
    if (sy, sm) > (ey, em):
        raise click.BadParameter("--start must not be later than --end.")
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
    load_settings()
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def execute_batches(taxi_types, batches, overwrite: bool) -> None:
    failures = []
    for taxi_type in taxi_types:
        for year, month in batches:
            try:
                result = run_batch(
                    taxi_type=taxi_type,
                    year=year,
                    month=month,
                    overwrite=overwrite,
                )
                click.echo(
                    f"[ok] {taxi_type} {year}-{month:02d} run={result.run_id} "
                    f"extracted={result.extracted_rows} "
                    f"loaded={result.loaded_rows} "
                    f"rejected={result.rejected_rows} "
                    f"promoted={result.promoted_rows}"
                )
            except Exception as error:
                click.echo(
                    f"[error] {taxi_type} {year}-{month:02d}: {error}",
                    err=True,
                )
                failures.append((taxi_type, year, month))
    if failures:
        raise click.ClickException(f"{len(failures)} failed batch(es): {failures}")


@cli.command()
@click.option(
    "--taxi-type",
    type=click.Choice(["yellow", "green", "both"]),
    required=True,
)
@click.option("--year", type=int, required=True)
@click.option("--month", type=click.IntRange(1, 12), required=True)
@click.option("--overwrite", is_flag=True, help="Download the Bronze file again.")
def ingest(taxi_type, year, month, overwrite):
    """Process one monthly batch for one or both taxi types."""
    execute_batches(
        resolve_taxi_types(taxi_type),
        [(year, month)],
        overwrite,
    )


@cli.command()
@click.option(
    "--taxi-type",
    type=click.Choice(["yellow", "green", "both"]),
    required=True,
)
@click.option("--start", required=True, help="YYYY-MM")
@click.option("--end", required=True, help="YYYY-MM")
@click.option("--overwrite", is_flag=True, help="Download Bronze files again.")
def backfill(taxi_type, start, end, overwrite):
    """Process an inclusive month range for one or both taxi types."""
    batches = list(month_range(start, end))
    execute_batches(resolve_taxi_types(taxi_type), batches, overwrite)


if __name__ == "__main__":
    cli()
