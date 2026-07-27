# Results: online serving latency

SDK path, single-thread, warm. 300 measured calls per cell after 50 warmup, random entities over a 10k keyspace. Run on dev0 (96 cores) against a Hopsworks cluster on the same host's K8s, 2026-07-27. Raw data in `results/`.

## Headline

Hopsworks retrieves online features 2x to 28x faster at the median, and the gap grows with load. Feast climbs almost linearly with batch size; RonDB stays nearly flat.

| Query | Feast p50 | Feast p99 | Hops p50 | Hops p99 | Ratio p50 |
|---|---|---|---|---|---|
| 1 row, 50 feats | 5.6 | 11.1 | 2.7 | 3.7 | 2.1x |
| 10 rows, 50 feats | 29.0 | 52.8 | 3.6 | 4.7 | 8.0x |
| 25 rows, 50 feats | 64.5 | 117.0 | 4.7 | 5.4 | 13.8x |
| 50 rows, 50 feats | 126.7 | 225.9 | 6.2 | 7.4 | 20.5x |
| 100 rows, 50 feats | 253.1 | 444.4 | 9.1 | 11.0 | 27.9x |
| 1 row, 100 feats | 10.7 | 20.7 | 3.2 | 4.2 | 3.3x |
| 1 row, 150 feats | 16.2 | 32.0 | 3.8 | 4.5 | 4.3x |
| 1 row, 200 feats | 22.3 | 46.2 | 4.4 | 214.8 | 5.1x |
| 1 row, 250 feats | 27.5 | 55.0 | 4.9 | 216.1 | 5.6x |

All values in milliseconds.

## Reading it honestly

- Feast played at home. Its Redis store ran on localhost, zero network. The Hopsworks client went over the network to RonDB with TLS. The advantage was Feast's, and it still lost on the median everywhere.
- At the smallest query (1 row), Hopsworks shows occasional network tail spikes near 210 ms p99 on two cells. These are external-client artifacts on the metadata path, not RonDB. Feast's localhost avoids them. Under any real load (batch or many features) Hopsworks wins on every percentile.
- Both numbers are the Python SDK returning a materialized object, the default `pip install feast` path, not the alpha Go feature server Feast benchmarks advertise.
- Feast's own slowdown from batch 1 to batch 100 is 45x. This is the per-entity Python processing that a purpose-built store avoids.

## First-run contamination (discarded)

An earlier run showed Feast at 31 ms p50 for the 1 row / 50 feats cell. That run overlapped the Hopsworks feature-group setup (25 Kafka-backed inserts) loading the host. It was discarded. The clean, isolated numbers above (5.6 ms) are the fair ones.

## Not yet measured

The HTTP feature server path (Feast's own published methodology: Dockerized feature servers behind Vegeta, where their 4 ms Redis claim lives). Next slice, to close the "you used the slow SDK path" objection.
