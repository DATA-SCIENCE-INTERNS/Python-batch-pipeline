import pandas as pd

from taxi_pipeline.transform import (
    check_required_columns,
    normalize_chunk,
    validate_chunk,
)


def yellow_row(**overrides):
    row = {
        "VendorID": 1,
        "tpep_pickup_datetime": "2025-01-01 10:00:00",
        "tpep_dropoff_datetime": "2025-01-01 10:15:00",
        "passenger_count": 1,
        "trip_distance": 2.5,
        "RatecodeID": 1,
        "store_and_fwd_flag": "N",
        "PULocationID": 10,
        "DOLocationID": 20,
        "payment_type": 1,
        "fare_amount": 12.0,
        "extra": 0.0,
        "mta_tax": 0.5,
        "tip_amount": 2.0,
        "tolls_amount": 0.0,
        "improvement_surcharge": 1.0,
        "total_amount": 15.5,
        "congestion_surcharge": 0.0,
        "Airport_fee": 1.75,
    }
    row.update(overrides)
    return row


def normalize(rows):
    return normalize_chunk(
        pd.DataFrame(rows), "yellow", "yellow.parquet", 2025, 1
    )


def test_normalization_is_canonical_and_trip_key_is_deterministic():
    first = normalize([yellow_row()])
    second = normalize([yellow_row()])

    assert first.loc[0, "pickup_datetime"] == pd.Timestamp("2025-01-01 10:00:00")
    assert first.loc[0, "trip_key"] == second.loc[0, "trip_key"]
    assert first.loc[0, "taxi_type"] == "yellow"
    assert first.loc[0, "airport_fee"] == 1.75
    assert pd.isna(first.loc[0, "trip_type"])


def test_validation_splits_valid_and_invalid_rows():
    frame = normalize([
        yellow_row(),
        yellow_row(
            tpep_dropoff_datetime="2025-01-01 09:00:00",
            trip_distance=-1,
        ),
    ])
    valid, rejected = validate_chunk(frame)

    assert len(valid) == 1
    assert len(rejected) == 1
    assert "dropoff before pickup" in rejected.iloc[0]["reject_reason"]
    assert "negative trip distance" in rejected.iloc[0]["reject_reason"]


def test_required_column_check_reports_missing_fields():
    missing = check_required_columns(
        ["tpep_pickup_datetime", "tpep_dropoff_datetime"], "yellow"
    )
    assert "PULocationID" in missing
    assert "total_amount" in missing
