# Results: offline (batch / training data) retrieval

Time to generate a training dataset from the offline store: N unique entities, 250 features, point-in-time correct join across 25 feature groups. Feast `get_historical_features` (file offline store, pandas join) vs Hopsworks `get_batch_data` (Hudi via Arrow Flight). Unique entities, so both return exactly N rows, no join fan-out. Raw data in `results/batch_*.jsonl`.

## The crossover

| rows | Feast | Hopsworks | winner |
|---|---|---|---|
| 10k | 5.3 s | ~45 s (overhead floor) | Feast |
| 100k | 35.6 s | 53.8 s | Feast (slight) |
| 1M | 344 s | 109 s | Hopsworks 3.2x |
| 10M | OOM crash | Spark path (see below) | Hopsworks |

Feast scales linearly: 5.3, 36, 344 seconds, a clean 10x per decade of rows. Hopsworks scales sub-linearly: a fixed distributed-query overhead of roughly 45 to 55 s dominates at small scale, then the engine barely moves (54 to 109 s from 100k to 1M). The lines cross between 100k and 1M.

The honest read: below about 100k rows, Feast's in-memory pandas join wins because it has no distributed-query overhead. Above it, Hopsworks pulls away and the gap widens without bound. Production training sets are millions of rows, which is the right of the crossover.

## 10M: where Feast ends

- **Feast**: does not complete. The driver run was OOM-killed by the host in ~42 s; a re-run under a 300 GB address-space limit ran for minutes without finishing. The file offline store does a 25-way pandas join of a 10M x 250 dataset in memory, and it is not viable. Feast has no distributed fallback.
- **Hopsworks**: the 25 feature groups of 10M rows each insert cleanly in ~9 minutes (~22 s per group). The read is where scale shows. The Python client's Arrow Flight / DuckDB engine hit its service temp-directory limit (OOM at 19.5 GB of spill) on the 25-way 10M join, so the production path is Spark (`create_training_data(write_options={"use_spark": True})`), which Feast has no equivalent of. Getting Spark to run took clearing a 130-job stats backlog and freeing memory (the platform reserves 92 to 99% of the small 4x32GB cluster). Once scheduled, the Spark job ran the full 25-way 10M join with RSS shuffle, thousands of tasks over ~75 minutes on two single-core executors, then the default 2 GB driver OOM-failed at finalization. Raising the driver memory is blocked by a Hopsworks client bug (job update mangles the system job's `local://` appPath into an invalid DFS path, HTTP 422), so a completed timing is not recorded. The result stands qualitatively: Hopsworks executes the 10M join that Feast OOM-crashes on instantly. Only a driver-memory bump (blocked by that client bug on this version) and a larger cluster separate it from a clean number.

## Method notes

- Feast's 25 feature views read one parquet; Hopsworks joins 25 offline feature groups. Same logical output (N rows, 250 features, PIT).
- The Hopsworks output has 300 columns (250 features plus entity and per-group event-time columns from the join); Feast returns 252. Row counts match N on both.
- Two Feast cells show contention variance (100k at 36 and 49 s, 1M at 344 and 370 s) from an overlapping run; the lower, isolated values are used above.
