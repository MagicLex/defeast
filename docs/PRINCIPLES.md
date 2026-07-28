# Engineering Principles

Non-negotiable rules. If a PR violates one, it does not merge.

## Benchmarking

- **Same data, same model, same sweep on both sides.** One generator, one feature model, one query sweep. Differences in the result come from the stores, not the setup.
- **Give the opponent the home advantage.** Feast ran against localhost Redis with zero network; Hopsworks went over the wire. A win under that handicap is unimpeachable.
- **Concede where Feast wins.** State the axes where Feast is faster or simpler (small-scale offline, low-infra start). A benchmark that claims a clean sweep is not believed.
- **Discard contaminated runs.** A measurement taken under interference (a concurrent setup job, an attacked store) is thrown out and rerun in isolation, not published.
- **Measure at the same layer.** Compare SDK to SDK or HTTP server to HTTP server, never one against the other, and name the layer.

## The bridge

- **Read the Feast registry through the Feast SDK, never parse the repo's Python files.** `FeatureStore(repo_path)` plus the `list_*` APIs give concrete, inferred schemas.
- **Plan before execute.** The planner writes nothing. Every human-decision point (TTL, credentials, UDF translation, streaming) surfaces as a warning before anything is created.
- **The plan JSON is the interface.** Feast and hsfs have conflicting dependencies and run in separate environments. The reader produces a plan; the executor consumes it. Neither imports the other's heavy dependency.
- **No loss means content, not API.** The migrated store returns the same features, values, names, and point-in-time behavior. Verify it: `get_feature_vector` on the migrated store must equal the source Feast repo.

## General

- No mocks, no hardcoded results. Validate against the real broker, the real cluster, the real data.
- Reproducible harness in the repo, raw results committed as data.
- User-facing docs are reference, no em dashes, no vendor editorializing.
