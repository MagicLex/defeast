<h1 align="center">defeast</h1>

<p align="center">
  <b>Feast vs Hopsworks, measured where Feast claims to win.</b><br>
  And a one-shot bridge that replays a Feast repo into Hopsworks without loss.
</p>

<p align="center">
  <code>benchmark</code> &nbsp;·&nbsp; <code>import-feast</code> bridge &nbsp;·&nbsp; evidence-first, concessions included
</p>

---

Two things live here.

1. A reproducible **benchmark** that tests the claims people actually make for Feast (low-latency serving, fast offline retrieval, point-in-time correctness, reusability) against Hopsworks on the same hardware, conceding where Feast genuinely wins.
2. **`import-feast`**, a bridge that reads an existing Feast repo through the Feast SDK and recreates its feature groups and feature views in Hopsworks with the data backfilled, so a Feast user can move without rebuilding.

## Benchmark scorecard

Measured on a single 96-core host, Feast and Hopsworks side by side, 2026-07-27. Feast played at home: its Redis online store ran on localhost with zero network, while the Hopsworks client went over the wire to RonDB with TLS. Raw data and harness in [`benchmark/`](benchmark/).

![Online serving latency, Feast vs Hopsworks](benchmark/img/online_latency.png)

| Axis | Result | Winner |
|---|---|---|
| **Online serving latency** (SDK, p50) | 2.1x at 1 row / 50 feats, up to 27.9x at 100 rows. RonDB stays flat, Feast climbs with load. Confirmed at the HTTP median too. | **Hopsworks** |
| **Offline batch retrieval** | Feast's in-memory join wins below ~100k rows. Hopsworks 3.2x at 1M (109s vs 344s). Feast OOM-crashes at 10M, no distributed fallback. | **split** (Feast small, Hopsworks large) |
| **Point-in-time correctness** | Both leak-free, 0 future leakage on either. Table stakes, not a differentiator. | **tie** |
| **Reusability** | Read-level reuse is parity. Reverse lineage, model-to-feature provenance, cross-team sharing, RBAC are native in Hopsworks, absent from Feast's OSS default. | **Hopsworks** |

The honest read: Feast is faster for offline training sets under ~100k rows and simpler to start with no infrastructure. On online latency at any real load, on offline at production scale, and on governed reuse, Hopsworks wins. Charts, per-axis detail, and contaminated-run discards in [`benchmark/README.md`](benchmark/README.md) and [`docs/claims-teardown.md`](docs/claims-teardown.md).

## The bridge: `import-feast`

Replays a Feast feature repo into Hopsworks, self-hosted or the managed [Hopsworks Serverless](https://app.hopsworks.ai) SaaS. It reads the Feast registry through the Feast SDK (never parses the repo's Python), maps it to a Hopsworks migration plan, and runs that plan: storage connectors, then cached feature groups with their data backfilled, then feature views built from the Feast feature services.

Feast and hsfs have conflicting dependencies and never share an environment, so the flow is two steps with a plan JSON as the interface. Plan on the Feast side, execute on the Hopsworks side. You can also plan on one machine and execute on another.

```bash
# 1. read the Feast repo, print and save the plan   (Feast environment)
pip install -e '.[plan]'
import-feast plan path/to/feast_repo -o plan.json

# 2. run it against Hopsworks                        (Hopsworks environment)
pip install -e '.[execute]'
import-feast execute plan.json --host <host> --project <project> --api-key-file <key> [--no-statistics]
```

`plan` writes nothing to Hopsworks. It prints, in create order, the connectors, feature groups (mapped types and backfill), and feature views, with a warning at every point that needs a human decision (TTL semantics, on-demand UDF translation, stream aggregations, credentials, dedup, unsupported sources). Read it before you execute.

### What it covers, validated against a live Hopsworks cluster

- Batch feature views over `FileSource` become cached feature groups, backfilled from the source parquet.
- Feast feature services become Hopsworks feature views (the join over the underlying groups).
- **Type fidelity**: a Feast `Int32`/`Float32` feature migrates as `int`/`float`, not the `bigint`/`double` a naive parquet-inference would give. The backfill is coerced to the declared type.
- **Nullable features** are preserved (a null `Int32` stays a typed-int column with its nulls intact).
- **Point-in-time** behavior carries over (`event_time` is preserved); a migrated store returns `get_feature_vector` values identical to the source Feast repo.
- **Idempotent**: re-running `execute` upserts on the primary key, it does not duplicate rows.

### What it flags, not yet replayed

Surfaced as warnings in the plan, honest about the gap:

- Warehouse sources (BigQuery, Redshift, Snowflake, Spark) map to storage connectors and external feature groups. Credentials are recreated by hand and never travel in the plan.
- On-demand feature views (translate the UDF `body_text` to a Hopsworks `@udf`).
- Stream feature views (window aggregations become a regenerated Spark job).
- TTL: online expiry transfers, the historical-join lookback bound does not.

## Layout

- [`benchmark/`](benchmark/) : the benchmark harness and raw results, four axes.
- [`import_feast/`](import_feast/) : the bridge (`plan.py` model, `mapper.py` reader, `executor.py` writer, `cli.py`).
- [`docs/`](docs/) : [philosophy](docs/PHILOSOPHY.md), [glossary](docs/CONTEXT.md), [principles](docs/PRINCIPLES.md), [invariants](docs/INVARIANTS.md), [claims teardown](docs/claims-teardown.md), [bridge scoping](docs/import-feast-scoping.md).
- `feast/` : fork of [feast-dev/feast](https://github.com/feast-dev/feast), kept as reference. Tracked in its own repo, not vendored here.
