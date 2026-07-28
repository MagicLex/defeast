# import feast: scoping

One-shot bridge that replays a Feast feature repo into Hopsworks feature groups and feature views without loss. This document scopes the mapping, the architecture, the loss points, and the build slices. It is a plan, not code.

Sources: the Feast object model was inventoried from the fork (`feast/sdk/python/feast/`), the Hopsworks target from hsfs 5.0.3 on the dev cluster. Two facts shape everything:

- Read the Feast **registry via the Feast SDK**, never parse the repo's Python files. `FeatureStore(repo_path)` plus `list_entities / list_batch_feature_views / list_on_demand_feature_views / list_stream_feature_views / list_feature_services / list_data_sources` gives every object with concrete, inferred schemas. Use `skip_udf=True` for cross-Python-version safety.
- This fork has diverged from upstream Feast (fork-only fields: lifecycle `state`, versioning, derived `source_views`, ODFV `aggregations`, `Set`/`Struct`/`Json`/`Uuid` types, `LabelView`, tiling, Permissions). The bridge must degrade gracefully and also handle vanilla Feast.

## What "no loss" means

Three layers, in priority order:

1. **Definitions**: every entity, feature, dtype, source, projection, join, and TTL is carried or explicitly flagged.
2. **Data**: feature values are replayed so the Hopsworks store is populated, not just defined. FileSources backfill into cached FGs; warehouse sources become external FGs (lazy) or backfill, a per-FV choice.
3. **Semantics**: point-in-time correctness is preserved (event_time carries over). Where semantics cannot transfer exactly (TTL lookback, created-timestamp dedup), the bridge warns per object rather than silently changing behavior.

## Architecture

```
feast_store (SDK reader)  ->  mapper  ->  hsfs writer (Hopsworks)
   list_* + registry          matrix       connectors -> FGs (+backfill) -> FVs
```

- **Reader**: instantiate `FeatureStore` against the repo `feature_store.yaml`; enumerate objects; pull `offline_store` config from RepoConfig (credentials live there, not on the DataSources).
- **Mapper**: apply the matrix below, emit a migration plan with per-object warnings.
- **Writer**: create in dependency order. Storage connectors first, then feature groups (cached FGs also get a backfill `insert()`), then feature views built from the feature-service projections.
- **Interface**: a CLI, `import-feast <feast_repo> --project <hopsworks_project> [--dry-run]`. Dry-run prints the plan and warnings without writing.

## Mapping matrix (condensed)

| Feast | Hopsworks | Rating |
|---|---|---|
| Entity (name, join_key, value_type) | FG `primary_key` column, surfaces as a FeatureView serving key | clean |
| FeatureView (batch, over a source) | cached FeatureGroup (+ backfill) + a serving FeatureView; or ExternalFeatureGroup to stay lazy | clean structure, per-FV data decision |
| FeatureService (projections over FVs) | FeatureView with `query = fg.select([...]).join(..., prefix=)` | clean, honor `name_alias` + `join_key_map` as prefix/join-on |
| FileSource | read file, `fg.insert(df)`; `timestamp_field` to `event_time` | clean |
| BigQuery / Redshift / Snowflake source | matching storage connector + ExternalFeatureGroup(`data_source=query`) | clean, credentials re-provisioned by hand |
| SparkSource / Trino / Postgres / custom | connector if dialect fits, else materialize | lossy |
| KafkaSource (stream) | KafkaConnector + `stream=True` FG + user Spark ingestion job | lossy |
| PushSource | `stream=True` FG + `insert()` (push semantics match) | clean |
| RequestSource | `request_parameters` on serving + on-demand UDF inputs | clean, typing becomes documentation |
| dtypes (Int/Float/String/Bytes/Bool/UnixTimestamp/Array) | int/bigint/float/double/string/binary/boolean/timestamp/array | clean, Decimal loses precision, Set degrades to array |
| TTL | FG `ttl` (native in 5.0.3) | lossy: online expiry transfers, historical-join lookback bound does not |
| OnDemandFeatureView (dill UDF + source text) | `@udf` on-demand tf on FG, or model-dependent tf on FV | lossy: translate `body_text`, flag closures/imports, choose placement |
| StreamFeatureView (Kafka + Spark aggs) | `stream=True` FG + regenerated Spark Structured Streaming job | lossy: aggregations are user Spark code, no declarative slot |
| `created_timestamp_column` (dedup tiebreak) | `hudi_precombine_key` (HUDI only, not the DELTA default) | lossy |
| feature logging config | Hopsworks serving/monitoring logging | no clean 1:1 |
| fork-only: state, versioning, source_views, LabelView, tiling, Permissions | no target | skip with a note |

## Loss points that need a human decision

The bridge surfaces these in the plan; it never guesses silently.

1. **Cached vs external per FV** (data laziness vs online sync). Default: FileSource to cached+backfill, warehouse sources to external.
2. **TTL semantics split**: online expiry carries, historical-join lookback does not. Per-FV warning.
3. **ODFV UDF translation**: replay `body_text` as a Hopsworks `@udf`; auto for simple pandas-mode UDFs, flag closures, imports, substrait, multi-output.
4. **Stream transformations**: regenerate as Spark jobs, not replayable declaratively.
5. **created_timestamp_column**: only under HUDI; otherwise dedup tiebreak changes.
6. **Credentials**: warehouse connectors recreated by hand (secrets never migrate).
7. **RequestSource typing**: request parameters are untyped at call time.
8. **Entity name normalization**: if two FVs use different join-key names for one entity, normalize or set explicit `join_on`.

## Build slices

- **Slice 0, dry-run planner** (safe, no writes). Read a repo, print the ordered hsfs call plan with the eight warnings inline. Proves the mapping end to end and surfaces every decision before touching Hopsworks. Ship this first.
- **Slice 1, MVP replay**: entities + batch FeatureViews over FileSource + dtypes + FeatureServices to cached FGs (backfilled) + FVs. Covers the common repo. No transforms, no streaming.
- **Slice 2, warehouse sources**: BigQuery / Redshift / Snowflake / Spark to storage connectors + external FGs, credentials as a prompted step.
- **Slice 3, on-demand transforms**: ODFV `body_text` to Hopsworks on-demand / model-dependent `@udf`.
- **Slice 4, streaming + push**: StreamFeatureView + Kafka / Push to stream FGs + regenerated Spark jobs.

Each slice is independently useful and testable against a real Feast repo (the benchmark repos in `benchmark/feast_repo` and the fork's `examples/` are ready fixtures).

## Open questions for Lex

1. Bridge home: a standalone CLI in this repo, or folded into the `hops` CLI as `hops import-feast`?
2. "No loss" default: definitions + data backfill (my assumption), or definitions only with a separate backfill step?
3. Build order: Slice 0 + 1 first (dry-run planner then MVP replay), or straight to MVP?
4. Fork vs vanilla: target upstream Feast semantics and degrade the fork-only fields, or support the fork's extra types (`Struct`/`Set`/vector) too?
