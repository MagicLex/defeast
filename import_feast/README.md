# import-feast

One-shot bridge that replays a Feast feature repo into Hopsworks feature groups and feature views. Design and mapping in `../docs/import-feast-scoping.md`.

## Status

- **Planner (done)**: reads a Feast repo through the Feast SDK registry, maps it to a Hopsworks plan, prints it, and can save it as JSON. Writes nothing to Hopsworks.
- **Executor (done)**: runs a saved plan against Hopsworks. Creates cached feature groups with an explicit schema, backfills their data from the FileSource parquet, and creates the feature views. Validated end to end against a live **self-hosted** cluster:
  - lossless: a migrated store returns `get_feature_vector` values identical to the source Feast repo.
  - type fidelity: a Feast `Int32`/`Float32` migrates as `int`/`float`, not the `bigint`/`double` parquet inference would give. The backfill is coerced to the declared type.
  - nullable features are preserved (a null `Int32` stays a typed-int column with its nulls).
  - idempotent: re-running `execute` upserts on the primary key, no row duplication.
- **SaaS**: validated end to end against a Hopsworks SaaS deployment (`eu-west.cloud.hopsworks.ai`), same FileSource repo, same fidelity checks. The executor creates feature groups with `time_travel_format="HUDI"` so the offline write runs as a server-side materialization job (client produces to Kafka, the cluster writes the table). The 5.x default `DELTA` makes the python client write the offline table directly to the object store, which only works where the client can reach it (S3-backed serverless), not an HDFS-backed cluster reached from outside. The `[execute]` extra installs `hopsworks[python]` (fastavro + confluent-kafka), which the HUDI insert needs.
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
import-feast execute plan.json --host <host> --project <project> --api-key-file <file> [--no-statistics] [--verbose]

# inside Hopsworks (terminal, job, notebook) the client logs in from its environment
import-feast execute plan.json
```

`execute` prints only its own progress lines; `--verbose` adds the hopsworks client output (job links, upload progress, logs).

`plan` prints, in create order: storage connectors, feature groups (backfill + mapped types), feature views (Feast feature services as queries over the groups), and a warning per human-decision point (TTL semantics, on-demand UDF translation, stream aggregations, credentials, dedup, unsupported sources, label views).

`Map`, `Json` and `Struct` features are planned as `string`; `execute` writes their values as JSON.

## Layout

- `plan.py`: the migration plan model + JSON serialization (the reader/executor interface).
- `mapper.py`: reads the Feast registry (`list_*` APIs) and builds the plan.
- `executor.py`: runs a plan via the hopsworks client (create FGs, backfill, create FVs).
- `cli.py`: the `plan` and `execute` subcommands.

## Current scope

Vanilla Feast, batch feature views over FileSources, backfilled into cached feature groups, with feature services becoming feature views. Warehouse sources map to external feature groups (metadata, credentials wired by hand). On-demand and stream feature views are flagged, not yet replayed.
