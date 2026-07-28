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

## In progress

Nothing active.

## Next

- Bridge slice 2: warehouse sources to storage connectors and external feature groups.
- Bridge slice 3: on-demand feature views, translate UDF `body_text` to Hopsworks `@udf`.
- Bridge slice 4: stream feature views to streaming feature groups plus regenerated Spark jobs.
- Bridge: explicit feature-type schema on FG creation instead of relying on parquet inference.
- Clean up test artifacts left in the `feast_bench` project (fg_*, fvb_*, pit_*, reuse_*, fv_0/1/2, svc_ab/ac).
- The 10M Spark batch number: blocked by cluster capacity and a hsfs job-update bug (see OPS). Needs a small memory bump on the cluster.
- The one-click "import feast" UI wrapping plan and execute (the original vision).
