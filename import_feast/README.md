# import-feast

One-shot bridge that replays a Feast feature repo into Hopsworks feature groups and feature views. Design and mapping in `../docs/import-feast-scoping.md`.

## Status

- **Slice 0, planner (done)**: reads a Feast repo through the Feast SDK registry, maps it to a Hopsworks plan, prints it, and can save it as JSON. Writes nothing to Hopsworks.
- **Slice 1, executor (done)**: runs a saved plan against Hopsworks. Creates cached feature groups, backfills their data from the FileSource parquet, and creates the feature views. Validated end to end: a migrated store returns `get_feature_vector` values identical to the source Feast repo.
- Next: warehouse sources (connectors + external FGs), on-demand transforms, streaming.

## Why two commands

Feast and hsfs have conflicting dependencies and cannot share one environment. The plan JSON is the interface: `plan` reads Feast (needs the feast package), `execute` writes Hopsworks (needs hsfs, reads the backfill parquet with pandas, no feast). You can also plan on one machine and execute on another.

## Use

```
pip install -e .              # exposes the import-feast command

# 1. read the Feast repo, print and save the plan (feast environment)
import-feast plan <feast_repo> -o plan.json

# 2. run it against Hopsworks (hsfs environment)
import-feast execute plan.json --host <host> --project <project> --api-key-file <file> [--no-statistics]
```

`plan` prints, in create order: storage connectors, feature groups (backfill + mapped types), feature views (Feast feature services as queries over the groups), and a warning per human-decision point (TTL semantics, on-demand UDF translation, stream aggregations, credentials, dedup, unsupported sources).

## Layout

- `plan.py`: the migration plan model + JSON serialization (the reader/executor interface).
- `mapper.py`: reads the Feast registry (`list_*` APIs) and builds the plan.
- `executor.py`: runs a plan via hsfs (create FGs, backfill, create FVs).
- `cli.py`: the `plan` and `execute` subcommands.

## Current scope

Vanilla Feast, batch feature views over FileSources, backfilled into cached feature groups, with feature services becoming feature views. Warehouse sources map to external feature groups (metadata, credentials wired by hand). On-demand and stream feature views are flagged, not yet replayed.
