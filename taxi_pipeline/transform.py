"""Silver-layer transformation: one canonical trip structure.

Yellow and Green files do NOT share an identical schema (requirement 11):
- Yellow uses tpep_pickup_datetime / tpep_dropoff_datetime
- Green uses  lpep_pickup_datetime / lpep_dropoff_datetime
- Green has trip_type and ehail_fee; Yellow has airport_fee
This module maps both into one canonical column set, casts every column
explicitly (never trusting Pandas inference), adds lineage metadata, and
computes a deterministic trip_key used for deduplication.
"""
import hashlib
import logging

import pandas as pd

log = logging.getLogger(__name__)

# ---- source -> canonical column renames --------------------------------
YELLOW_RENAMES = {
    "tpep_pickup_datetime": "pickup_datetime",
    "tpep_dropoff_datetime": "dropoff_datetime",
    "VendorID": "vendor_id",
    "RatecodeID": "ratecode_id",
    "PULocationID": "pu_location_id",
    "DOLocationID": "do_location_id",
}
GREEN_RENAMES = {
    "lpep_pickup_datetime": "pickup_datetime",
    "lpep_dropoff_datetime": "dropoff_datetime",
    "VendorID": "vendor_id",
    "RatecodeID": "ratecode_id",
    "PULocationID": "pu_location_id",
    "DOLocationID": "do_location_id",
}

# Columns that MUST exist in the source file for the run to proceed
# (data-quality check 19).
REQUIRED_SOURCE_COLUMNS = {
    "yellow": {"tpep_pickup_datetime", "tpep_dropoff_datetime",
               "PULocationID", "DOLocationID", "trip_distance",
               "fare_amount", "total_amount"},
    "green": {"lpep_pickup_datetime", "lpep_dropoff_datetime",
              "PULocationID", "DOLocationID", "trip_distance",
              "fare_amount", "total_amount"},
}

# Canonical schema: name -> pandas dtype
CANONICAL_DTYPES = {
    "vendor_id": "Int64",
    "pickup_datetime": "datetime64[us]",
    "dropoff_datetime": "datetime64[us]",
    "passenger_count": "Int64",
    "trip_distance": "float64",
    "ratecode_id": "Int64",
    "store_and_fwd_flag": "string",
    "pu_location_id": "Int64",
    "do_location_id": "Int64",
    "payment_type": "Int64",
    "fare_amount": "float64",
    "extra": "float64",
    "mta_tax": "float64",
    "tip_amount": "float64",
    "tolls_amount": "float64",
    "improvement_surcharge": "float64",
    "total_amount": "float64",
    "congestion_surcharge": "float64",
    "airport_fee": "float64",     # yellow only -> NULL for green
    "trip_type": "Int64",         # green only  -> NULL for yellow
}

# Fields that define trip identity for the trip_key hash.
KEY_FIELDS = [
    "pickup_datetime", "dropoff_datetime", "pu_location_id",
    "do_location_id", "trip_distance", "fare_amount",
    "total_amount", "vendor_id",
]


def check_required_columns(columns, taxi_type: str) -> set:
    """Return the set of missing required columns (empty set = OK)."""
    return REQUIRED_SOURCE_COLUMNS[taxi_type] - set(columns)


def _compute_trip_key(df: pd.DataFrame, taxi_type: str) -> pd.Series:
    """Deterministic MD5 over taxi_type + identity fields.

    Documented business key (requirement 14): two rows with the same
    taxi type, timestamps, locations, distance, fares and vendor are
    considered the same physical trip. The hash is stable across reruns,
    which makes ON CONFLICT DO NOTHING in the gold layer idempotent.
    """
    key_src = df[KEY_FIELDS].astype("string").fillna("~")
    joined = taxi_type + "|" + key_src.agg("|".join, axis=1)
    return joined.map(lambda s: hashlib.md5(s.encode()).hexdigest())


def normalize_chunk(df: pd.DataFrame, taxi_type: str, source_file: str,
                    year: int, month: int) -> pd.DataFrame:
    """Map one raw chunk to the canonical silver structure."""
    renames = YELLOW_RENAMES if taxi_type == "yellow" else GREEN_RENAMES
    df = df.rename(columns=renames)
    # Green files sometimes ship an ehail_fee column that is entirely
    # null and absent from Yellow; it carries no analytical value, so we
    # drop it (decision-log entry).
    df = df.drop(columns=["ehail_fee"], errors="ignore")

    # Ensure every canonical column exists, then cast explicitly.
    for col, dtype in CANONICAL_DTYPES.items():
        if col not in df.columns:
            df[col] = pd.NA
        if dtype.startswith("datetime"):
            df[col] = pd.to_datetime(df[col], errors="coerce")
        else:
            df[col] = df[col].astype(dtype, errors="ignore")

    df = df[list(CANONICAL_DTYPES)]  # drop extras, fix column order

    # Lineage / metadata columns
    df["taxi_type"] = taxi_type
    df["source_file"] = source_file
    df["source_year"] = year
    df["source_month"] = month
    df["ingested_at"] = pd.Timestamp.now("UTC")

    df["trip_key"] = _compute_trip_key(df, taxi_type)
    return df
