# SQL showcase

These read-only PostgreSQL scripts demonstrate the pipeline from four angles:

1. `01_pipeline_health.sql` - batch execution, coverage, and file lineage
2. `02_data_quality.sql` - acceptance rates and rejected-record evidence
3. `03_business_insights.sql` - useful taxi and revenue analysis
4. `04_engineering_checks.sql` - idempotency, reconciliation, and integrity

## Run in pgAdmin

Connect with:

```text
Host: 127.0.0.1
Port: 5433
Database: nyc_taxi
Username: taxi_user
```

Open **Query Tool** under the `nyc_taxi` database, open one script, and execute
each numbered query separately while explaining the heading above it.

The scripts do not create, update, or delete data.

## Suggested presentation order

Start with pipeline health to establish that the monthly batches ran. Show the
file checksum query as lineage evidence. Continue to data quality to explain
that invalid records are quarantined instead of silently discarded. Then show
two or three business queries. Finish with the engineering checks proving that
Gold has no duplicate keys and that loaded/rejected counts reconcile.

Some business queries scan millions of Gold rows and can take longer than the
metadata queries. They deliberately restrict detailed analysis to one month
where practical.
