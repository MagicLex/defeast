# Philosophy

Prove where Hopsworks beats Feast on the points Feast is said to be good at, honestly, and build the one-shot bridge that replays a Feast repo into Hopsworks without loss.

## Why it exists

Feast is the popular open-source feature store, so two things are worth having. First, evidence: a reproducible benchmark that tests the claims people actually make for Feast (low-latency serving, fast offline retrieval, point-in-time correctness, reusability) against Hopsworks on the same hardware, conceding where Feast genuinely wins. Second, a migration path: a tool that takes an existing Feast repo and recreates its feature groups and feature views in Hopsworks with the data backfilled, so a Feast user can switch without rebuilding.

## Who it is for

The benchmark serves Hopsworks positioning and anyone comparing the two stores. The bridge serves Feast users evaluating or moving to Hopsworks.

## What it is not

- Not a Feast fork or replacement. The `feast/` directory is the upstream fork kept as reference.
- Not a marketing hit piece. The benchmark is evidence-first: contaminated numbers are discarded, Feast is given the home advantage, and the axes where Feast wins (small-scale offline, low-infra start) are stated plainly.
- Not a drop-in API shim. The bridge migrates the content of the store (features, values, definitions, point-in-time semantics). The application switches from the Feast client to the Hopsworks client.
