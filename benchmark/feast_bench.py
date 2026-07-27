"""Feast SDK-level online latency benchmark. Single-thread, warm.
Mirrors feast-benchmarks sweep. Emits JSONL."""
import time, json, sys
import numpy as np
from feast import FeatureStore

KEYSPACE = 10**4
WARMUP = 50
N = 300
store = FeatureStore(repo_path="/home/lex/feast-bench/repo")

def svc(features):  # feature_service_{0..4} -> 50..250 features
    return store.get_feature_service(f"feature_service_{features//50 - 1}")

def cell(batch, features):
    fsvc = svc(features)
    def one():
        rows = [{"entity": int(e)} for e in np.random.randint(0, KEYSPACE, batch)]
        store.get_online_features(features=fsvc, entity_rows=rows).to_dict()
    for _ in range(WARMUP): one()
    lat = np.empty(N)
    for i in range(N):
        t = time.perf_counter(); one(); lat[i] = (time.perf_counter()-t)*1000
    p = lambda q: float(np.percentile(lat, q))
    return {"side":"feast","batch":batch,"features":features,"n":N,
            "p50":p(50),"p90":p(90),"p99":p(99),"p999":p(99.9),
            "mean":float(lat.mean()),"max":float(lat.max()),
            "qps_1thread":1000.0/float(lat.mean())}

cells = [(b,50) for b in [1,10,25,50,100]] + \
        [(1,f) for f in [50,100,150,200,250]]
seen=set(); out=open("/home/lex/feast-bench/results_feast.jsonl","w")
for b,f in cells:
    if (b,f) in seen: continue
    seen.add((b,f))
    r=cell(b,f); print(json.dumps(r)); out.write(json.dumps(r)+"\n"); out.flush()
out.close()
