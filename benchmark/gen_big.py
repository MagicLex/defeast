"""Large-data generator for the batch/offline slice. Unique entities (no fan-out),
250 int64 features, one parquet per size. Feast reads it directly; Hopsworks inserts it."""
import sys, time, datetime
import numpy as np, pandas as pd
N = int(sys.argv[1]); NF = 250
t = time.time()
ts = pd.Timestamp("2026-01-01", tz="UTC")
df = pd.DataFrame({"entity": np.arange(N, dtype=np.int64),
                   "event_timestamp": ts})
# features: random small ints, chunked to limit peak memory
for i in range(NF):
    df[f"feature_{i}"] = np.random.randint(0, 10**6, N).astype(np.int64)
path = f"/tmp/big_{N}.parquet"
df.to_parquet(path)
import os
print(f"N={N} shape={df.shape} parquet={os.path.getsize(path)/1e6:.0f}MB gen={time.time()-t:.1f}s")
