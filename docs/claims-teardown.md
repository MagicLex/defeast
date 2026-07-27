# Feast claims teardown

Goal: kill the claims people make in Feast's favor, precisely, on the points where Feast is said to be good. Honest first. We do not attack what is actually true, we reframe it. We benchmark what is measurable, using Feast's own methodology so they cannot cry foul.

Every claim below is sourced. Feast-self sources are file paths in the `feast/` fork. Community sources are URLs with the author's affiliation noted.

## Tier A. KILL. Measurable head-to-head, Feast loses.

### A1. Online serving latency (flagship)
- Claim in the wild: "p99 latency of 4.2ms and 100K+ QPS" with Redis (dasroot.net, independent). Feast's own blog: Go server p99 ~3.9ms.
- The crack: Feast's own docs list "need very low latency feature retrieval (p99 << 10ms)" under **when NOT to use Feast** (https://docs.feast.dev/). The fast numbers are the **Go feature server**, alpha, Redis-only (`feast/docs/blog/go-feature-server-benchmarks.md`). The `pip install feast` default serves through the **Python feature server, 3 to 5x slower** by their own measurement. Extra hop: Python server to external DB, no native store.
- Hopsworks: RonDB online store, vendor benchmark claims ~15ms vs Feast ~50ms p99 (250 features, batch 1) (https://www.hopsworks.ai/post/feature-store-benchmark-comparison-hopsworks-and-feast). Vendor source, so we re-measure ourselves.
- Proof to produce: latency benchmark, our hardware, using the Feast team's own harness (feast-dev/feast-benchmarks) so the method is theirs. Default Feast (Python server + Redis) vs Hopsworks. Report p50/p99/p999 and max QPS at fixed p99, varied by batch size, feature count, concurrency. Include the Go server too, to stay honest.

### A2. "It is a feature store" but does not compute features
- Most-cited limitation across neutral sources: "Feast does not compute features. It stores and serves precomputed features that you generate through external data pipelines" (Tacnode, https://tacnode.io/post/how-to-evaluate-a-feature-store). Featureform on HN: "it exclusively stores features, it does not manage the transformations" (https://news.ycombinator.com/item?id=31932513).
- Honest caveat: the Feast maintainer partially rebuts it. On-demand and streaming transformations exist, batch is nascent (`feast/docs/README.md` "What Feast is not"). So it is "limited feature engineering", not literally zero.
- Hopsworks: computes features in-platform (Spark, Flink, pandas) and serves them. No external pipeline required.
- Proof to produce: build the same feature (a streaming aggregation + an on-demand transform) end to end in both. Show Feast requires an external compute pipeline you own and operate, Hopsworks does it in-platform.

### A3. Registry scale and governance
- Claim: "centralized catalog, single source of truth" (`feast/docs/getting-started/components/registry.md`).
- The crack: the default registry is a **single protobuf file** on local FS or S3 (`registry.md:5`), no concurrency control, no RBAC. Their own text: "can be turned into a more scalable SQL-backed registry", the admission that the default does not scale.
- Hopsworks: transactional registry with RBAC, project isolation, and a UI.
- Proof to produce: concurrent `feast apply` against the file registry to show the race, plus a feature matrix (RBAC, UI, project isolation) that Feast's default lacks.

## Tier B. EGALIZE. Table-stakes, not a Feast differentiator.

### B1. Point-in-time correctness / no data leakage
- Claim: `feast/README.md`, `feast/docs/README.md`. Real capability, but self-sourced and matched by every serious store (Tecton, Hopsworks). The web sonde flagged it as table-stakes, not an edge.
- Move: show equivalent ASOF/point-in-time joins in Hopsworks. Neutralize, do not oversell.

## Tier C. CONCEDE then reframe. Actually true, do NOT pretend to beat.

These are Feast's strongest, most independently-sourced claims. Attacking them head-on loses credibility. The reframe: each is true at toy scale and inverts into cost or gap at production scale.

### C1. Lightweight, pip install, reuse existing infra
- True and most-repeated (Reintech, Feast homepage "START SERVING IN SECONDS", maintainer on HN).
- Reframe, all sourced: the low-infra story inverts into operational burden. "You are responsible for deploying, monitoring, and scaling the infrastructure" (Reintech). To reach production you assemble and run Spark, Postgres, Kafka, Redis yourself (featurestorecomparison.com). The "lightweight" is a first-run illusion; the second run is a distributed system you operate.

### C2. Open-source, vendor-neutral, no lock-in
- True (universal across sources).
- Reframe: Hopsworks is also open-source and self-hostable, and additionally offers managed. Feast's "no lock-in" still locks you into operating the substrate. And note Hopsworks is the mid-ground independent reviewers already name: "more capable than Feast, significantly cheaper than Tecton" (Uplatz, MLOps Platforms, Taylor Amarel).

### C3. Broad storage-backend catalog (10+ offline, 15+ online)
- True and concrete (Feast homepage, Tacnode). A genuine differentiator: reuse rather than replace.
- Reframe: breadth of connectors you wire together vs depth of an integrated store. You assemble, they integrate. Depth wins on latency (A1) and governance (A3).

### C4. Low cost, no license fees
- True (no licensing beyond infra).
- Reframe: TCO includes the engineering time to run it, the "hidden cost" every neutral source appends to this claim (Reintech).

## What we do NOT do
Do not fabricate Reddit quotes (the sonde could not confirm any, so none are cited). Do not benchmark C1 to C4 to "win"; they are conceded and reframed, not measured. Do not present the Hopsworks vendor benchmark as our evidence; we re-measure A1 ourselves with Feast's own harness.

## Sources index
- Feast self: `feast/README.md`, `feast/docs/README.md`, `feast/docs/getting-started/components/registry.md`, `feast/docs/blog/go-feature-server-benchmarks.md`, `feast/docs/blog/performance-test-for-python-based-feast-feature-server.md`, https://docs.feast.dev/, https://feast.dev/
- Neutral-ish: Reintech, Tacnode, dasroot.net, Uplatz, MLOps Platforms, Taylor Amarel (URLs inline above)
- Maintainer intent: Danny Chiao (adchia) on HN, https://news.ycombinator.com/item?id=31932513
- Vendor (discounted): hopsworks.ai benchmark post, featurestorecomparison.com, Schmitt/Medium (Feast-leaning)
- Feast benchmark harness to reuse: https://github.com/feast-dev/feast-benchmarks
