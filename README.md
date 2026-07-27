# hopsworks-feast

Two things:

1. **Benchmark.** Feast vs Hopsworks on the points where Feast claims to be better.
2. **`import feast` bridge.** One-shot that replays a Feast repo's pipelines as Hopsworks feature groups and feature views, no loss.

## Layout

- `feast/`: fork of [feast-dev/feast](https://github.com/feast-dev/feast) (`MagicLex/feast`), kept as reference. Gitignored here, tracked in its own repo.

## Reference

The Feast model we map from lives in `feast/sdk/python/feast/`: `feature_store.py`, `feature_view.py`, `entity.py`, `infra/offline_stores`, `infra/online_stores`, `repo_config.py`.
