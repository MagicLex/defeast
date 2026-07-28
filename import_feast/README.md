# import-feast

One-shot bridge that replays a Feast feature repo into Hopsworks feature groups and feature views. Design and mapping in `../docs/import-feast-scoping.md`.

## Status

- **Slice 0, dry-run planner (done)**: reads a Feast repo through the Feast SDK registry, maps it to a Hopsworks plan, and prints it. Writes nothing.
- Slice 1 (next): executor that runs the plan (create feature groups, backfill data, create feature views).

## Use

```
pip install -e .              # exposes the import-feast command
import-feast <feast_repo>     # a directory with feature_store.yaml
# or without installing:
python -m import_feast <feast_repo>
```

It prints, in create order: storage connectors, feature groups (with the backfill it would run and the mapped feature types), feature views (built from Feast feature services as queries over the groups), and a warnings list for every point that needs a human decision (TTL semantics, on-demand UDF translation, stream aggregations, credentials, dedup, unsupported sources).

## Layout

- `plan.py`: the migration plan model (connectors, feature groups, feature views, warnings).
- `mapper.py`: reads the Feast registry (`list_*` APIs) and builds the plan. Reused by the executor.
- `cli.py`: argument parsing and plan printing.
