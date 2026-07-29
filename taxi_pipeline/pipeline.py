pf = pq.ParquetFile(path)                 # opens metadata only, ~instant
for batch in pf.iter_batches(batch_size=settings.chunk_size):
    chunk = batch.to_pandas()             # only 100k rows in memory at once
    ...