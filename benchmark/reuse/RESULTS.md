# Results: feature reusability

Can you define a feature once and reuse it across many models, teams and projects? Tested concretely (define once, reuse in multiple views, check for recompute and lineage), plus a governance matrix. Scripts: `reuse_hops.py`, `reuse_feast.py`.

## Read-level reuse: parity

Both stores let you define a feature once and reuse it across consumers with no recompute.

- **Hopsworks**: one feature group, two feature views selecting overlapping subsets. Creating the views triggered **0 new compute jobs**. Views are logical (a query over the group).
- **Feast**: one feature view, two feature services selecting overlapping subsets. `feast apply` is metadata only, no materialization triggered.

So the basic "compute once, read many" story is the same on both. It is not a differentiator.

## Lineage: Hopsworks has it, Feast does not

- **Hopsworks**: `fg.get_generated_feature_views()` returns `['reuse_model_a', 'reuse_model_b']` directly. The store knows which views (and downstream models) consume a feature group. Native provenance.
- **Feast**: no reverse-lineage API. To find which services consume a feature view you scan every feature service by hand. The registry records no model-to-feature link at all.

This matters at team scale: "who depends on this feature, can I change it" is a native query in Hopsworks and a manual audit in Feast.

## Governance matrix

Reusing a feature across teams needs more than a shared read. The rest is where Feast's open-source default is thin (sourced in `docs/claims-teardown.md`, confirmed by Feast's own docs).

| Capability | Feast (OSS default) | Hopsworks |
|---|---|---|
| Compute once, reuse in many views | yes | yes |
| Reverse lineage (feature to consumers) | no (manual scan) | yes (provenance API) |
| Model to feature lineage | no | yes |
| Cross-project / team sharing | no (single flat registry) | yes (shared feature store, per-project) |
| RBAC / access control | no | yes (project-based) |
| Discovery UI / search | no | yes |
| Feature statistics / monitoring | no | yes |
| Registry backing | file protobuf (default) | transactional, per-project |

## Takeaway

Reuse at the read level is table-stakes, both do it. The reusability that matters for an organization, sharing a governed feature across teams with lineage and access control, is native in Hopsworks and absent from Feast's open-source default. This lines up with the most-cited Feast limitation from the community research: it stores and serves features but does not carry the governance around them.
