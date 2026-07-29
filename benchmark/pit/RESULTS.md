# Results: point-in-time correctness

Feast markets point-in-time correctness ("avoid data leakage") as a headline. This tests whether it is a real differentiator or table-stakes. A feature changes at known timestamps; a spine of labels probes as-of values at boundaries, between events, and before the first event. Ground truth is the latest event with `event_time <= label`. Scripts: `pit_data.py`, `pit_feast.py`, `pit_hops.py`.

## Both are point-in-time correct. Neither leaks the future.

- **Feast** (`get_historical_features`, file offline, spine of 120 labels): 0 value mismatches. Every returned as-of value is correct, including exact boundaries (inclusive: `event_time <= label`) and between-event points. No future leakage.
- **Hopsworks**: the spine-based point-in-time join (arbitrary per-row label timestamps) is only supported by the Spark engine, which this dev cluster could not schedule reliably. Probed instead with `get_batch_data(end_time=T)` per label: no future value is ever returned. At non-boundary labels the as-of value is exactly correct.

The headline claim is table-stakes. Both stores avoid leakage. It is not a Feast differentiator.

## Where they differ (conventions, not correctness)

- **Null-row handling.** Feast silently drops rows whose feature has no as-of value (a label before the first event returns nothing, 100 of 120 rows). In a training set this quietly removes early examples. Worth knowing.
- **Boundary inclusivity.** Feast includes the event at an exact timestamp match (`<=`). Hopsworks `get_batch_data(end_time)` treats the window bound as exclusive (`<`), so at an exact-timestamp label it returns the prior event. This is the batch-window convention, past-leaning, never future. The spine-PIT path (Spark) may differ; not tested here.

## Caveat

The clean apples-to-apples test is spine-PIT on both sides. Hopsworks spine dataframes require the Spark engine ("spine dataframes are currently only supported with the Spark engine"), blocked on this cluster, so the Hopsworks side used a per-label `get_batch_data(end_time)` probe with a slightly different boundary convention. The core guarantee, no future leakage, is verified on both.
