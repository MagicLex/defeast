# Results: HTTP feature-server latency

This reproduces Feast's own published methodology: the feature server behind an HTTP load generator (Vegeta), the layer where their advertised latency numbers live. Feast side is `feast serve` (their product, gunicorn). Hopsworks side is a structural twin (uvicorn calling `get_feature_vector`). Vegeta at 10 req/s, 15s per cell, single worker each side. Raw data in `results/http_*.jsonl`.

## What is clean, and what is not

Read this section before the numbers. Both servers show artifacts under load, and most of them are implementation, not store.

- The clean signal is **low-load p50 at batch 1**. It tracks the SDK result: Feast 7.2 ms, Hopsworks 4.5 ms at 50 features; Feast 28 ms, Hopsworks 6.9 ms at 250 features. Hopsworks stays 1.5x to 4x faster at the median through the HTTP hop too. That closes the "you only measured the slow SDK path" objection: `feast serve`, their own product, is slower than Hopsworks.
- Everything past the low-load median is noise from the server implementations, not a Feast-vs-Hopsworks signal:
  - Feast's single gunicorn worker saturates at 10 req/s for large batches (batch 100 times out at 28% success; batch 25 shows 1.8 s from queueing while batch 50 shows 77 ms, which is incoherent and means the run was unstable, not that batch 50 is faster than batch 25).
  - The Hopsworks twin is a naive `async def` calling a blocking `get_feature_vector`, which blocks the uvicorn event loop and resets connections under load. That is why batch-1 cells show 61 to 66% success and a ~214 ms tail. This is my wrapper, not RonDB. A sync-worker server (like Feast's gunicorn) would not do this.

## Takeaway

The HTTP layer confirms the SDK finding at the median: Hopsworks wins. Throughput and tail under load are not measured fairly here because both servers are single-worker and the Hopsworks twin is event-loop-blocking. Doing the HTTP throughput story properly needs sync-worker servers on both sides, per-cell rate calibrated below saturation, and longer runs. The SDK benchmark (`RESULTS.md`) stays the clean, primary latency result.

## One honest cost to Hopsworks

Serving init on the Hopsworks side is slow and scales with the number of joined feature groups: 9 s for a 5-group feature view, over 40 s for the 25-group one. This is a one-time per-view startup cost (prepared statements and the online connector), paid once when a server boots, not per request. Feast's server starts in seconds. Worth naming even though it does not affect steady-state latency.
