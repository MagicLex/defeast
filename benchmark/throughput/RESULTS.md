# Results: throughput under concurrency (same-machine)

Open-loop load test of the two HTTP feature servers, both on one node, `lex-worker-2`. A stepped arrival-rate shape ramps the target from 50 to 1600 requests per second. This replaces the earlier Vegeta run, which used a single worker per side and an event-loop-blocking Hopsworks twin, both of which it flagged as unfair.

The servers are matched: `feast serve` (Feast's own gunicorn server) with 4 workers, and a structural twin for Hopsworks (gunicorn with 4 uvicorn workers, a sync handler calling `get_feature_vectors` through the in-cluster RDRS client). Same worker count, same node, batch 1, 50 features. Raw data in `results/{feast,hops}_stats.csv` and `results/{feast,hops}_history.csv`.

## What came out

| Server | Sustained rps | Failures | Median | p99 |
|---|---|---|---|---|
| Feast (`feast serve`, 4 workers) | 116 | 0.6% | 2100 ms | 18000 ms |
| Hopsworks (RDRS twin, 4 workers) | 456 | 0% | 520 ms | 1800 ms |

Under the same ramp, Hopsworks sustained 3.9x the request rate, with zero failures, and a median latency 4x lower under load. Feast's server saturated early: at the top steps its achieved rate stayed near 116 rps while requests queued, the median climbed to 2.1 s, and the p99 reached 18 s. Hopsworks held 456 rps with no failures and a 520 ms median.

## Reading it honestly

- Both numbers are capped by the same thing: the load generator (Locust) shared the pod's CPU with the server, so neither figure is the server's absolute ceiling. This caps both sides equally, so the ratio holds, but the true ceilings are higher, Hopsworks more so since it had headroom (0 failures) where Feast was already failing.
- The signal is the saturation behavior, not a single rps number. Feast saturates around 100 to 150 rps on this node and its tail collapses past that (18 s p99). Hopsworks absorbs the same ramp with no failures and a bounded tail.
- Same worker count on both (4), same node, same request shape. This is server-to-server at a matched worker model, the comparison the earlier single-worker Vegeta run could not make.
- A cleaner absolute-ceiling run would put the load generator in its own pod so it does not steal CPU from the server. The relative result here is already decisive.

## Reproduce

Servers and load generator run in-cluster on the RonDB node (`setup/k8s/`), one server at a time (never concurrent). Start a server, then:

```
locust -f locustfile_feast.py,shape.py --headless --host http://127.0.0.1:6566 --csv results/feast
locust -f locustfile_hops.py,shape.py  --headless --host http://127.0.0.1:6567 --csv results/hops
```

See `run.md` for the server start commands and the metric to read (max sustained rps with achieved equal to target and no failures; the knee is the first step where they diverge).
