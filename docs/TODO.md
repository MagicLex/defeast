# TODO

Last updated: 2026-07-28.

## Shipped

- Forked `feast-dev/feast` and `feast-dev/feast-benchmarks` under MagicLex, kept as reference.
- `docs/claims-teardown.md`: sourced Feast claims sorted KILL / EGALIZE / CONCEDE.
- Benchmark, four axes, harness and raw results in `benchmark/`:
  - Online latency SDK: Hopsworks 2x to 28x faster at p50 (`RESULTS.md`).
  - Online latency HTTP: low-load p50 confirms the SDK finding (`RESULTS_HTTP.md`).
  - Offline batch: in-memory vs distributed crossover, Feast wins below ~100k, Hopsworks 3.2x at 1M, Feast OOM at 10M (`RESULTS_BATCH.md`).
  - Point-in-time: both leak-free, table-stakes (`RESULTS_PIT.md`).
  - Reusability: read-level parity, lineage and governance native in Hopsworks only (`RESULTS_REUSE.md`).
- Shareable artifact (report.html) with the four-claims scorecard.
- `docs/import-feast-scoping.md`: bridge mapping matrix, architecture, slices, locked decisions.
- Bridge slice 0 (planner) and slice 1 (executor), validated lossless. `import_feast/`.
- Bridge: explicit feature-type schema on FG creation. The executor declares the FG schema from the plan's mapped types and coerces the backfill dataframe to them, instead of letting parquet inference decide. Proven on a divergent case (Feast `Int32`/`Float32` over an int64/float64 parquet): inference gave `bigint`/`double`, the fix gives `int`/`float`. Also fixed a relative-backfill-path bug (the plan stores an absolute FileSource path, self-contained for the executor's separate CWD).
- Bridge hardening, full end-to-end validation against dev0/`feast_bench`:
  - nullable features handled: a null `Int32` coerces to a pandas nullable dtype, stays a typed-`int` column with its nulls (4/20 nulls preserved on insert + read-back).
  - version threading: the executor reads each FG's version from the plan for feature-view joins instead of the hardcoded `1`.
  - idempotency verified: re-running `execute` upserts on the primary key (500 rows stayed 500), no duplication, lossless stable.
  - error paths return exit 2 with a clear message (bad repo, missing key, no subcommand).
  - `pyproject.toml` extras `[plan]` (feast) and `[execute]` (hopsworks, pandas) match the two-environment split; base install stays feast-free.
  - Root `README.md` rewritten for users (benchmark scorecard + bridge quickstart); `import_feast/README.md` refreshed.

## In progress

Nothing active.

## Next

- Bridge slice 2: warehouse sources to storage connectors and external feature groups.
- Bridge slice 3: on-demand feature views, translate UDF `body_text` to Hopsworks `@udf`.
- Bridge slice 4: stream feature views to streaming feature groups plus regenerated Spark jobs.
- Bridge: explicit `feature_view` versioning (still created at v1; the fork's Feast has FV versions, vanilla does not).
- Clean up test artifacts left in the `feast_bench` project (fg_*, fvb_*, pit_*, reuse_*, fv_0/1/2, svc_ab/ac).
- The 10M Spark batch number: blocked by cluster capacity and a hsfs job-update bug (see OPS). Needs a small memory bump on the cluster.
- The one-click "import feast" UI wrapping plan and execute (the original vision).
