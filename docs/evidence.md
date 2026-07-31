# Verification evidence

This file records observed local verification results. Counts are a snapshot,
not a promise about future source revisions or later backfills.

## Automated tests

Command:

```powershell
python -m pytest tests -q -p no:cacheprovider
```

Observed result on July 30, 2026:

```text
7 passed
```

Coverage includes:

- Download URL and partitioned Bronze path construction
- Cross-year month ranges
- Invalid-month handling
- Yellow canonical normalization
- Deterministic trip keys
- Valid/rejected record splitting
- Required source-column detection

## Idempotency check

Green January 2025 was ingested twice:

```text
First run:  extracted=48,326 loaded=48,326 promoted=48,326
Second run: extracted=48,326 loaded=48,326 promoted=0
Gold count after both runs: 48,326
```

This demonstrates that an exact rerun does not duplicate Gold records.

## Transaction recovery observation

During Yellow February 2025, PostgreSQL received an administrator-triggered
fast shutdown. The active connection closed and the monthly transaction rolled
back. PostgreSQL logs showed crash recovery followed by a healthy restart.

The batch was rerun successfully:

```text
extracted=3,577,543
loaded=3,577,450
rejected=93
```

This incident motivated database connection waiting, interrupted-batch retries,
and the recovery guidance in `operations.md`.

## Large-month observation

Yellow March 2025 completed with:

```text
extracted=4,145,257
loaded=4,145,176
rejected=81
```

After chunk processing, Gold promotion remained quiet in Python logs while
PostgreSQL reported an active `INSERT INTO gold.yellow_trips`. Its wait events
changed from `WALWrite` to `DataFileWrite`, confirming disk activity rather
than a deadlock.

## Backfill snapshot

At the July 31, 2026 documentation checkpoint:

```text
Gold Yellow rows: 11,197,728
Gold Green rows:     396,577
Green February-August: successful
Green September: running
```

The Green backfill was still active, so later totals will be higher.

## Remaining verification gaps

- No automated disposable-PostgreSQL integration test
- No automated forced-disconnection/rollback test
- No performance benchmark across different chunk and COPY strategies
- No CI workflow
- No source checksum comparison against an upstream manifest
