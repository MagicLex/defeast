# Results: online serving latency (same-machine)

SDK path, single-thread, warm. 300 measured calls per cell after 50 warmup, random entities over a 10k keyspace. Both stores and both clients run on one node, `lex-worker-2`, so neither side crosses an external network. Feast reads Redis on the same node, Hopsworks reads RonDB through RDRS (the RonDB REST Data Service) on the same node via the in-cluster service address. This replaces an earlier run where the Hopsworks client sat on a separate host and reached RonDB over the load balancer, a handicap Feast did not have. Raw data in `results/feast_incluster.jsonl` and `results/hops_incluster.jsonl`.

## Headline

Hopsworks retrieves online features 4.9x to 21.8x faster at the median, and the gap grows with load. Feast climbs almost linearly with batch size; RonDB stays nearly flat.

| Query | Feast p50 | Feast p99 | Hops p50 | Hops p99 | Ratio p50 |
|---|---|---|---|---|---|
| 1 row, 50 feats | 6.4 | 10.9 | 1.3 | 2.6 | 4.9x |
| 10 rows, 50 feats | 34.2 | 57.5 | 2.6 | 4.0 | 13.2x |
| 25 rows, 50 feats | 80.3 | 136.4 | 4.4 | 5.5 | 18.2x |
| 50 rows, 50 feats | 161.0 | 269.6 | 7.6 | 9.1 | 21.2x |
| 100 rows, 50 feats | 312.9 | 523.9 | 14.3 | 17.0 | 21.8x |
| 1 row, 100 feats | 12.2 | 21.5 | 1.4 | 2.1 | 8.5x |
| 1 row, 150 feats | 18.4 | 31.4 | 1.6 | 3.3 | 11.7x |
| 1 row, 200 feats | 24.6 | 42.4 | 1.8 | 2.7 | 13.8x |
| 1 row, 250 feats | 30.9 | 53.3 | 2.0 | 3.2 | 15.4x |

All values in milliseconds.

## Reading it honestly

- Same machine, same node, no external network on either side. Both clients run in-cluster on `lex-worker-2` and reach their store through the cluster service network. The node is idle in practice (about 2% CPU, 61% memory), so the measurement is not fighting contention.
- Removing the network widened the gap, because Hopsworks was the side that used to pay for it. At a single row the ratio went from 2.1x (client over the load balancer) to 4.9x (same node). At 250 features it went from 5.6x to 15.4x.
- Hopsworks here uses the REST path (client to RDRS over HTTP). That path carries a per-request HTTP cost that shows at large batch: at batch 100 it is 14.3 ms, where the direct SQL client to RonDB was 9 ms. So the batch-100 ratio (21.8x) understates Hopsworks; the SQL path would widen it. Single-row and feature-count reads, where most online serving lives, are the clean win.
- Both numbers are the Python SDK returning a materialized object, the default `pip install feast` path, not the alpha Go feature server Feast benchmarks advertise.
- Feast's own slowdown from batch 1 to batch 100 is 49x. This is the per-entity Python processing that a purpose-built store avoids.

## Method

- Feast: 25 feature views, 5 feature services, online store Redis 7 on the same node, `feast materialize`. Repo generated in-cluster, mirroring `setup/feast_repo`. Read with `get_online_features`.
- Hopsworks: 25 feature groups, 5 feature views, online store RonDB. Read with `get_feature_vector(s)`, REST client pinned to the in-cluster RDRS endpoint.
- The in-cluster harness is reproducible from `setup/k8s/` (namespace, client pods pinned to the RonDB node, Redis). Runs are sequential, never concurrent, so the two do not contend.

## Not yet measured here

Throughput under concurrency (the HTTP feature-server path with a load generator). That is the `throughput/` slice, run with Locust in open-loop against both servers on the same node.
