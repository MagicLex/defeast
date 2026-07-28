"""Point-in-time correctness test data with known ground truth.
Each entity has a feature that changes at known timestamps. The correct as-of value for a
label at time T is the latest feature whose event_time <= T. Also tests: exact-boundary,
before-first-event (expect null), and between-events."""
import pandas as pd, numpy as np, itertools, json

# feature history: entity -> list of (event_time, value)
ENTS = list(range(1, 21))          # 20 entities
EVENTS = ["2026-01-01","2026-02-01","2026-03-01","2026-04-01"]
rows = []
for e in ENTS:
    for k, d in enumerate(EVENTS):
        rows.append({"entity": e, "event_timestamp": pd.Timestamp(d, tz="UTC"),
                     "val": e*100 + (k+1)})   # deterministic, unique per (entity,event)
hist = pd.DataFrame(rows)
hist.to_parquet("/tmp/pit_hist.parquet")

# spine: label timestamps to probe, including boundaries and before-first
LABELS = ["2025-12-15",   # before first event -> null
          "2026-01-01",   # exact boundary -> event 0
          "2026-01-15",   # between 0 and 1 -> event 0
          "2026-02-01",   # exact boundary -> event 1
          "2026-03-20",   # between 2 and 3 -> event 2
          "2026-05-01"]   # after last -> event 3
spine = pd.DataFrame([{"entity": e, "event_timestamp": pd.Timestamp(l, tz="UTC")}
                      for e in ENTS for l in LABELS])
spine.to_parquet("/tmp/pit_spine.parquet")

# ground truth: for each (entity,label) the expected val (or None)
def expected(e, label):
    ts = pd.Timestamp(label, tz="UTC")
    valid = [(pd.Timestamp(d, tz="UTC"), e*100+(k+1)) for k,d in enumerate(EVENTS)
             if pd.Timestamp(d, tz="UTC") <= ts]
    return valid[-1][1] if valid else None
gt = {f"{e}|{l}": expected(e, l) for e in ENTS for l in LABELS}
json.dump(gt, open("/tmp/pit_gt.json","w"))
print(f"hist {hist.shape}, spine {spine.shape}, gt {len(gt)} entries")
print("sample gt:", {k:gt[k] for k in list(gt)[:6]})
