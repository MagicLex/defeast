# import-feast

One-shot bridge that replays a Feast feature repo into Hopsworks feature groups and feature views. Design and mapping in `../docs/import-feast-scoping.md`.

## Status

- **Planner (done)**: reads a Feast repo through the Feast SDK registry, maps it to a Hopsworks plan, prints it, and can save it as JSON. Writes nothing to Hopsworks.
- **Executor (done)**: runs a saved plan against Hopsworks. Creates cached feature groups with an explicit schema, backfills their data from the FileSource parquet, and creates the feature views. Validated end to end against a live **self-hosted** cluster:
  - lossless: a migrated store returns `get_feature_vector` values identical to the source Feast repo.
  - type fidelity: a Feast `Int32`/`Float32` migrates as `int`/`float`, not the `bigint`/`double` parquet inference would give. The backfill is coerced to the declared type.
  - nullable features are preserved (a null `Int32` stays a typed-int column with its nulls).
  - idempotent: re-running `execute` upserts on the primary key, no row duplication.
- **SaaS**: the executor logs in with the standard `hopsworks` client (`--host` + project-scoped API key), so the [Hopsworks SaaS](https://app.hopsworks.ai) deployment uses the same path and should behave the same. Not yet run end to end there; supported-not-yet-verified until a SaaS run is posted.
- Next: warehouse sources (connectors + external FGs), on-demand transforms, streaming.

## Why two commands

Feast and the Hopsworks client have conflicting dependencies and cannot share one environment. The plan JSON is the interface: `plan` reads Feast (needs the `feast` package), `execute` writes Hopsworks (needs the `hopsworks` client, reads the backfill parquet with pandas, no feast). You can also plan on one machine and execute on another.

## Use

```
# 1. read the Feast repo, print and save the plan   (Feast environment)
pip install -e '.[plan]'
import-feast plan <feast_repo> -o plan.json

# 2. run it against Hopsworks                        (Hopsworks environment, needs the hopsworks client)
pip install -e '.[execute]'
import-feast execute plan.json --host <host> --project <project> --api-key-file <file> [--no-statistics]
```

`plan` prints, in create order: storage connectors, feature groups (backfill + mapped types), feature views (Feast feature services as queries over the groups), and a warning per human-decision point (TTL semantics, on-demand UDF translation, stream aggregations, credentials, dedup, unsupported sources).

## Layout

- `plan.py`: the migration plan model + JSON serialization (the reader/executor interface).
- `mapper.py`: reads the Feast registry (`list_*` APIs) and builds the plan.
- `executor.py`: runs a plan via the hopsworks client (create FGs, backfill, create FVs).
- `cli.py`: the `plan` and `execute` subcommands.

## Current scope

Vanilla Feast, batch feature views over FileSources, backfilled into cached feature groups, with feature services becoming feature views. Warehouse sources map to external feature groups (metadata, credentials wired by hand). On-demand and stream feature views are flagged, not yet replayed.
