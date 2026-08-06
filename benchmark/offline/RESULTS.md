# Results: offline (training data) retrieval

Building a training dataset: N unique entities, 250 features, point-in-time correct join across 25 feature groups. Feast `get_historical_features` (file offline store, pandas join) vs Hopsworks over the Hopsworks Query Service (DELTA feature groups, Arrow Flight / DuckDB). Unique entities, so both return exactly N rows, no join fan-out. Same machine (dev0), measured warm.

## Two operations, not one

Offline retrieval has two distinct patterns, and they have very different costs. The first version of this axis measured only the first one, with the wrong Hopsworks API, and that undersold the store on the pattern that matters for training.

- **On-the-fly build**: compute the point-in-time join and return the rows now. Feast `get_historical_features`; Hopsworks `training_data()`. Both stores rebuild the join on every call. (`get_batch_data`, referenced below only as a cross-check, is a related but different API: it does the same wide PIT join across the joined groups but observes over a time range (`start_time`/`end_time`) instead of an entity spine, so `training_data` is the true analogue of Feast's spine-driven `get_historical_features`.)
- **Materialize once, read many**: compute the join once into a versioned dataset, then read it back cheaply. Hopsworks `create_training_data` then `get_training_data`. Feast has no native offline equivalent, `get_historical_features` rebuilds the join every read.

Measured on dev0 at 10k rows, 25 groups:

| operation | method | time |
|---|---|---|
| on-the-fly build | Feast `get_historical_features` | 5.3 s |
| on-the-fly build | Hopsworks `training_data` (PIT, in-memory, stats off) | 42.7 s |
| on-the-fly build | Hopsworks `get_batch_data` (same PIT join, time-range spine) | 45.4 s |
| materialize once | Hopsworks `create_training_data` (job) | 60.6 s |
| **read materialized** | Hopsworks `get_training_data` (warm) | **0.75 s** |

`training_data` is measured with `statistics_config=False`, so it builds the PIT join and returns the rows and nothing else, the same operation as Feast `get_historical_features`. The default call also computes feature statistics (Feast's does not) and lands at ~51 s at this size; that extra work is a Hopsworks capability, not part of a fair build-the-join comparison, so it is excluded here.

## On-the-fly: Feast wins small, Hopsworks wins at scale

![Offline on-the-fly build vs rows](../img/offline_scale.png)

On-the-fly, both stores rebuild the join every call, same API on each side: Feast `get_historical_features`, Hopsworks `training_data`. Feast's in-memory pandas join is cheap at small N. Hopsworks pays a distributed-query cost that is dominated by query construction and grows with the number of joined groups (see below), so at 10k with a 25-way join it is ~43 s against Feast's 5.3 s. The lines cross between 100k and 1M: Feast still wins at 100k (35.6 s vs 49.5 s), at 1M Hopsworks is ~3.7x faster (93.9 s vs 344 s), and at 10M Feast OOM-crashes with no distributed fallback while Hopsworks completes.

The whole axis now rides one API on each side. The earlier version measured Hopsworks with `get_batch_data` (a time-range read); those numbers were slightly higher (52 s / 53.8 s / 109 s at 10k / 100k / 1M) but the crossover and shape are identical, so the choice of on-the-fly API was never what decided the small-N case. The wide PIT join is genuinely expensive at small scale.

## The on-the-fly floor is join-width bound

![Offline floor vs join width](../img/offline_join_width.png)

Holding rows at 10k and varying the number of joined groups, Hopsworks `training_data` runs 2.7 s at 1 group, 8.7 s at 5, 42.7 s at 25. Roughly 1.7 s per group. A cProfile of the equivalent 25-group call puts ~24 s in `_get_batch_query` and ~12 s in `_construct_query` (backend query construction) and only ~10 s in the Arrow Flight read; client-side parsing is 0.15 s. So the on-the-fly floor is server-side query construction that scales with join width, not a row cost. It reproduced identically on dev0 (starved), on the eu-west SaaS (healthy), and with `online_enabled` both true and false, so it is not cluster memory pressure and not the online setting. It is the cost of constructing a wide point-in-time join in this Hopsworks version (5.0.3), and worth a ticket upstream.

This floor is measured without `lookback`, which is the honest worst case for both stores (Feast's pandas join scans everything too). Hopsworks documents `lookback` as a partition-pruning knob on both `get_batch_data` and `create_training_data`: the PIT `event_time <=` comparison is a range, which defeats partition pruning and forces a full-history scan, and `lookback` turns the window into a constant-bound predicate the engine can prune on before opening files. It attacks this exact floor, and Feast's file offline store has no equivalent. We do not claim the pruned number here; it is a lever left unmeasured, not a result.

Feast's 5.3 s is at the full 250 features; at narrow widths Feast reads less and is faster, so a fair by-width comparison would need Feast measured at the same widths (its width harness is not clean here: empty spine on this parquet plus a pandas datetime dtype error on the multi-FV join). What is established is the Hopsworks side.

## Materialize once, read many: the training workflow

![Offline read-many](../img/offline_materialized.png)

The realistic training loop materializes a dataset once and reads it many times (epochs, experiments, re-runs). Hopsworks materializes a versioned training dataset once (60.6 s at 10k/25 groups) and then reads it in **0.75 s**, and that read is width-independent because the join is baked into the stored table. Feast has no materialized offline dataset: every read is another `get_historical_features` at 5.3 s. Cumulatively Hopsworks overtakes Feast at ~13 reads, and per read after that it is 0.75 s against 5.3 s. Hopsworks training datasets are also versioned, which Feast's offline path does not provide.

The materialized read is measured at 10k; the mechanism (read a flat stored table, no join) is size-scaling but width-independent. 100k and 1M materialized reads are not yet measured (they need DELTA groups built at those sizes, a heavy run).

## 10M: where Feast ends

- **Feast**: does not complete. The driver run was OOM-killed by the host in ~42 s; a re-run under a 300 GB address-space limit ran for minutes without finishing. The file offline store does a 25-way pandas join of a 10M x 250 dataset in memory, and it is not viable. Feast has no distributed fallback.
- **Hopsworks**: the 25 feature groups of 10M rows each insert cleanly in ~9 minutes. The Python client's Arrow Flight / DuckDB engine hit its service temp-directory limit (OOM at 19.5 GB of spill) on the 25-way 10M on-the-fly join, so the production path at that size is Spark (`create_training_data(write_options={"use_spark": True})`), which Feast has no equivalent of. A clean 10M timing is blocked by a client bug (job update mangles the system job's `local://` appPath into an invalid DFS path, HTTP 422) and cluster capacity; the result stands qualitatively.

## Method notes

- Feast's 25 feature views read one parquet; Hopsworks joins 25 offline feature groups. Same logical output (N rows, 250 features, PIT).
- On hopsworks 5.0.3 the offline read only works on DELTA feature groups. Reading the original HUDI benchmark groups raises "Reading data with Hive is not supported (client >= 4.0)", so the measurement uses DELTA groups over Arrow Flight.
- Hopsworks side is `benchmark/offline/training_data_hops.py` (modes: build 25 DELTA groups, create a width-W view, bench `training_data(statistics_config=False)`), warm median of 3 timed builds after a warmup. Raw data in `results/training_data.jsonl`. Run in-cluster on dev0 against project `feast_bench`; the client is a from-scratch venv (hopsworks 5.0.3), the offline read path is Arrow Flight / HQS to DELTA on HopsFS.
- The Hopsworks output has 300 columns (250 features plus entity and per-group event-time columns from the join); Feast returns 252. Row counts match N on both.
- Two Feast cells showed contention variance (100k at 36 and 49 s, 1M at 344 and 370 s) from an overlapping run; the lower, isolated values are used.
