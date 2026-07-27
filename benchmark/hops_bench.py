"""Hopsworks SDK-level online latency benchmark. Single-thread, warm.
Same sweep + format as feast_bench.py. Emits JSONL."""
import time, json
import numpy as np
import hopsworks

KEYSPACE = 10**4
WARMUP = 50
N = 300
KEY = open("/home/lex/.hw_bench_key").read().strip()
proj = hopsworks.login(host="10.113.154.130", port=443, project="feast_bench", api_key_value=KEY)
fs = proj.get_feature_store()
FVS = {f: fs.get_feature_view(f"fv_{f}", version=1) for f in [50,100,150,200,250]}
for fv in FVS.values():
    fv.init_serving()

def cell(batch, features):
    fv = FVS[features]
    if batch == 1:
        call = lambda: fv.get_feature_vector({"entity": int(np.random.randint(0, KEYSPACE))})
    else:
        call = lambda: fv.get_feature_vectors([{"entity": int(e)} for e in np.random.randint(0, KEYSPACE, batch)])
    for _ in range(WARMUP): call()
    lat = np.empty(N)
    for i in range(N):
        t = time.perf_counter(); call(); lat[i] = (time.perf_counter()-t)*1000
    p = lambda q: float(np.percentile(lat, q))
    return {"side":"hopsworks","batch":batch,"features":features,"n":N,
            "p50":p(50),"p90":p(90),"p99":p(99),"p999":p(99.9),
            "mean":float(lat.mean()),"max":float(lat.max()),
            "qps_1thread":1000.0/float(lat.mean())}

cells = [(b,50) for b in [1,10,25,50,100]] + \
        [(1,f) for f in [50,100,150,200,250]]
seen=set(); out=open("/home/lex/feast-bench/results_hops.jsonl","w")
for b,f in cells:
    if (b,f) in seen: continue
    seen.add((b,f))
    r=cell(b,f); print(json.dumps(r), flush=True); out.write(json.dumps(r)+"\n"); out.flush()
out.close()
print("HOPS BENCH DONE", flush=True)
