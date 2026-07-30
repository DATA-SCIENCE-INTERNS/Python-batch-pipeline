"""End-to-end orchestration for one NYC taxi monthly batch."""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq

from .config import Settings, load_settings
from .database import (
    create_batch_run,
    create_file_ingestion,
    finish_batch,
    get_connection,
    insert_rejected_rows,
    insert_silver_rows,
    promote_to_gold,
    replace_silver_batch,
)
from .extract import TaxiType, build_download_url, download_trip_data
from .transform import check_required_columns, normalize_chunk, validate_chunk

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchResult:
    run_id: int
    taxi_type: str
    year: int
    month: int
    source_file: Path
    extracted_rows: int
    loaded_rows: int
    rejected_rows: int
    promoted_rows: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_batch(taxi_type: TaxiType, year: int, month: int, *,
              settings: Settings | None = None,
              overwrite: bool = False) -> BatchResult:
    """Run download, validation, Silver load and Gold promotion for one month."""
    settings = settings or load_settings()
    source_url = build_download_url(taxi_type, year, month, settings.base_url)
    conn = get_connection(settings)
    run_id = create_batch_run(conn, taxi_type, year, month, source_url)
    file_id = None
    extracted = loaded = rejected = 0

    try:
        path = download_trip_data(
            taxi_type,
            year,
            month,
            bronze_directory=settings.data_dir,
            overwrite=overwrite,
            base_url=settings.base_url,
        )
        checksum = sha256_file(path)
        parquet = pq.ParquetFile(path)
        missing = check_required_columns(parquet.schema.names, taxi_type)
        if missing:
            raise ValueError(
                "Source file is missing required columns: "
                + ", ".join(sorted(missing))
            )

        file_id = create_file_ingestion(
            conn, run_id, taxi_type, year, month, str(path), checksum
        )
        with conn.cursor() as cur:
            replace_silver_batch(cur, taxi_type, year, month)
            for batch in parquet.iter_batches(batch_size=settings.chunk_size):
                raw = batch.to_pandas()
                extracted += len(raw)
                normalized = normalize_chunk(
                    raw, taxi_type, path.name, year, month
                )
                valid, invalid = validate_chunk(normalized)
                loaded += insert_silver_rows(cur, valid)
                rejected += insert_rejected_rows(cur, run_id, invalid)
                log.info(
                    "Processed batch run_id=%s extracted=%s loaded=%s rejected=%s",
                    run_id, extracted, loaded, rejected,
                )

            promoted = promote_to_gold(cur, taxi_type, year, month)
            cur.execute("REFRESH MATERIALIZED VIEW gold.monthly_summary")
            finish_batch(
                cur, run_id, file_id, "success", extracted, loaded, rejected
            )
        conn.commit()
        return BatchResult(
            run_id, taxi_type, year, month, path, extracted, loaded,
            rejected, promoted,
        )
    except Exception as exc:
        conn.rollback()
        error = str(exc)[:4_000]
        with conn.cursor() as cur:
            if file_id is None:
                cur.execute(
                    """
                    UPDATE pipeline.batch_runs
                    SET status = 'failed', finished_at = now(),
                        error_message = %s
                    WHERE run_id = %s
                    """,
                    (error, run_id),
                )
            else:
                finish_batch(
                    cur, run_id, file_id, "failed",
                    extracted, loaded, rejected, error,
                )
        conn.commit()
        raise
    finally:
        conn.close()
