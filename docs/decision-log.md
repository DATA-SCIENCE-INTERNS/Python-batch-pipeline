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