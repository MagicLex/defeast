# Throughput benchmark: open-loop load test

Measures requests/sec each feature server sustains under a p99 latency SLO, and where each one saturates. Open-loop stepped sweep (constant arrival rate per step), not closed-loop, so queueing delay is measured instead of hidden. Both servers get the identical harness.

## Prerequisites

- `pip install locust` (2.15+ for comma-separated `-f`)
- Servers and load generator on separate machines, or at minimum pinned to separate cores. A colocated generator steals CPU from the server under test.
- Same worker count on both sides. This is the fairness contract.

## Start the servers

Feast (its own product, gunicorn):

```
feast serve --host 127.0.0.1 --port 6566 --workers 4
```

Hopsworks (structural twin, gunicorn, sync workers):

```
export HOPSWORKS_HOST=<api-host>
export HOPSWORKS_API_KEY_FILE=~/.hw_bench_key
export FEATURE_VIEWS=fv_50   # only the view under test; init_serving is slow
gunicorn hops_server:app -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:6567 --timeout 120
```

`RDRS_HOST` (default 10.103.3.227) and `RDRS_PORT` (default 4406) point the hsfs REST client at the in-cluster RDRS endpoint. Wait for all workers to finish `init_serving` before loading (about 10 s for fv_50, about 40 s for fv_250). Bind to 127.0.0.1 or a cluster-internal address, never 0.0.0.0.

## Run the sweep

One cell = one (batch, features) pair, one server, one full RPS sweep.

```
export BATCH=1 FEATURES=50
locust -f locustfile_feast.py,shape.py --headless \
    --host http://127.0.0.1:6566 --csv results/feast_b1_f50 --csv-full-history

locust -f locustfile_hops.py,shape.py --headless \
    --host http://127.0.0.1:6567 --csv results/hops_b1_f50 --csv-full-history
```

Defaults: steps 50, 100, 200, 400, 800, 1600 RPS, 30 s each (3 min total). Override with `RPS_STEPS` and `STEP_SECONDS`. Above about 1000 users add `--processes 4` so the generator is not the bottleneck. `RPS_PER_USER` (default 1) is read by both the locustfiles and the shape; set it once in the environment if you change it.

## What to read

From `results/*_stats_history.csv` (per-window time series):

1. **Achieved RPS vs target per step.** While achieved tracks the step target, the run is open-loop and valid.
2. **Max sustained RPS under SLO.** Pick and state the SLO before the run (for example p99 < 100 ms). The result is the highest step where achieved RPS equals the target AND windowed p99 stays under the SLO AND failures are 0%.
3. **The knee.** The first step where achieved RPS falls below target, p99 blows up, or failures appear. Report the last good step and the first bad one for each server.

Discard the first few seconds of each step (spawn ramp).

## Honesty caveats

- Single-node servers on both sides. This measures one server process group, not a scaled deployment. The comparison is server-to-server at a matched worker model and matched hardware, nothing more.
- The Hopsworks server is our twin, not a shipped product. It mirrors the `feast serve` architecture (gunicorn, N sync workers, FastAPI) and its flaws from the previous single-async-worker version are fixed, but Feast is running its own code and Hopsworks is running ours.
- Above the knee, per-user arrival generators cannot maintain rate and the harness degrades toward closed-loop, so latency numbers past the knee understate true queueing delay. Report the knee, not the post-knee latencies.
- Store topology differs by design: Feast reads Redis, Hopsworks reads RonDB over the RDRS REST endpoint. Keep both stores same-node with their server to keep network hops comparable.
