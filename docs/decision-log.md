# Architecture Decision Log

## ADR-001: Use Medallion Architecture

**Date:** July 2026

**Status:** Accepted

### Decision

The pipeline will use Bronze, Silver and Gold layers.

### Reason

The architecture separates raw ingestion, validation and final trusted data. It improves traceability, troubleshooting and safe reprocessing.

### Implementation

- Bronze: raw Parquet files in the file system.
- Silver: validated PostgreSQL staging tables.
- Gold: final deduplicated PostgreSQL tables.

---

## ADR-002: Use PostgreSQL for Silver and Gold

**Date:** July 2026

**Status:** Accepted

### Decision

PostgreSQL will store the Silver and Gold layers.

### Reason

PostgreSQL supports transactions, constraints, unique keys, SQL validation and persistent storage.

---

## ADR-003: Use Python for the complete pipeline

**Date:** July 2026

**Status:** Accepted

### Decision

Python will control extraction, transformation, validation and loading.

### Reason

The assignment requires a Python batch ingestion system and the team has experience using Python.

---

## ADR-004: Use Docker Compose

**Date:** July 2026

**Status:** Accepted

### Decision

Docker Compose will manage the Python pipeline and PostgreSQL services.

### Reason

It provides a reproducible local environment that can be started from a clean checkout.

---

## ADR-005: Use one transaction per monthly batch

**Date:** July 2026

**Status:** Accepted for the current project; revisit before production scale

### Decision

Silver replacement, rejected-row loading, Gold promotion, summary refresh, and
success metadata commit atomically for one taxi type and month.

### Reason

The database never exposes a partially published month, and rerunning a failed
batch is straightforward.

### Tradeoff

The transaction can contain millions of rows. A PostgreSQL restart rolls back
the complete month, and Gold promotion generates significant WAL and disk I/O.
Durable chunk staging is the preferred future design.

---

## ADR-006: Derive a deterministic trip key

**Date:** July 2026

**Status:** Accepted with limitations

### Decision

Hash taxi type, timestamps, locations, distance, fares, and vendor into a
stable key used by Gold primary keys.

### Reason

The source data does not provide a universal unique trip identifier. The
derived key makes exact reruns idempotent.

### Tradeoff

The selected attributes are an approximation of identity. Legitimate trips
with identical attributes may be merged, while corrected source values may
produce a new key.
