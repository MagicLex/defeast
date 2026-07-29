# Invariants

Architectural contracts. Verify before merging any significant change. Each item: PASS/FAIL evidence, not aspiration.

## Benchmark

- **Both sides share one dataset and one feature model.** PASS. `benchmark/gen_big.py` and the Feast/Hopsworks setup scripts read the same generated data; 25 groups of 10 features on both.
- **Latency is compared at a stated, matched layer.** PASS. `RESULTS.md` is SDK to SDK; `RESULTS_HTTP.md` is HTTP server to HTTP server, with the server-implementation caveats named.
- **No published number came from a contaminated run.** PASS. The first Feast SDK run (31 ms, overlapping the Hopsworks setup) was discarded and rerun in isolation (5.6 ms); documented in `RESULTS.md`.

## Bridge

- **`plan` writes nothing to Hopsworks.** PASS. `import_feast/cli.py` `_cmd_plan` only reads and prints; `execute` is a separate subcommand.
- **Feast and hsfs never load in one process.** PASS. `plan` imports feast, `execute` imports hsfs and reads the backfill parquet with pandas. The plan JSON is the only shared artifact.
- **The reader uses the Feast SDK registry, never parses `.py`.** PASS. `mapper.build_plan` calls `store.list_*`.
- **Migration is lossless at the feature level.** PASS. A migrated store returned `get_feature_vector(svc_ab, entity 3) = [370, 463, 223, 606, 285, 340]`, identical to the source parquet's `feat_0..5`.
- **Migrated FG schema carries Feast's declared types, not parquet inference.** PASS. The executor declares the FG schema from the plan's mapped types and coerces the backfill to them. On a `Feast Int32`/`Float32` feature over an int64/float64 parquet, the migrated FG is `int`/`float`; the old inference path gave `bigint`/`double`. The event-time column is carried in the schema as `timestamp`. Nullable features hold: a null `Int32` coerces to a pandas nullable dtype and stays a typed-`int` column with its nulls intact (4/20 preserved through insert and read-back).
- **`execute` is idempotent.** PASS. Re-running a plan upserts on the primary key. A repeat run of the same backfill kept the feature group at 500 rows (not 1000) and the migrated `get_feature_vector` unchanged.
- **The plan is self-contained: backfill paths are absolute.** PASS. The mapper resolves a FileSource path against the repo before writing the plan, so the executor (separate env, different CWD) reads the right parquet. Verified on a repo with a repo-relative `data/d.parquet` source.
- **Every human-decision point surfaces as a warning before execute.** PASS. TTL, credentials, dedup, UDF, stream, and unsupported sources emit warnings in the plan.

## Infrastructure

- **Services bind to localhost only.** PASS after an incident. The benchmark host is internet-facing with no host firewall; an early Redis on `0.0.0.0:6379` was hit by a scanner and moved to `127.0.0.1:6771`. Never bind `0.0.0.0` on a shared host.
- **The dev cluster is left as found.** PASS. Memory freed for Spark runs (scaled-down deployments, `hopsworks-instance` to 1) was restored to original replica counts; RSS requests reverted.
