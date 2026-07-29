import os
"""Hopsworks offline (batch/training data) benchmark. Setup: 25 offline-only FGs +
1 FV joining them, unique entities from big_N.parquet. Bench: time get_batch_data (N rows,
250 feats, 25-FG PIT join). Reuses FGs if present. Appends JSONL.
Usage: python batch_hops.py <N> <parquet> [setup|bench]"""
import sys, time, json
import pandas as pd, hopsworks

N = int(sys.argv[1]); PARQUET = sys.argv[2]; MODE = sys.argv[3] if len(sys.argv) > 3 else "both"
KEY = open(os.environ.get("HOPSWORKS_API_KEY_FILE", os.path.expanduser("~/.hw_bench_key"))).read().strip()
proj = hopsworks.login(host=os.environ["HOPSWORKS_HOST"], port=443, project="feast_bench", api_key_value=KEY)
fs = proj.get_feature_store()
tag = f"b{N}"

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

if MODE in ("setup", "both"):
    for i in range(25):
        cols = ["entity","event_timestamp"] + [f"feature_{10*i+j}" for j in range(10)]
        sub = pd.read_parquet(PARQUET, columns=cols)
        fg = fs.get_or_create_feature_group(name=f"fg{tag}_{i}", version=1,
            primary_key=["entity"], event_time="event_timestamp", online_enabled=False)
        fg.insert(sub, write_options={"wait_for_job": True})
        log(f"fg{tag}_{i} inserted ({N} rows)")
    q = fs.get_feature_group(f"fg{tag}_0", version=1).select_all()
    for i in range(1, 25):
        q = q.join(fs.get_feature_group(f"fg{tag}_{i}", version=1).select_all(), on=["entity"], prefix=f"g{i}_")
    fs.get_or_create_feature_view(name=f"fvb_{N}", version=1, query=q)
    log(f"fvb_{N} created")

if MODE in ("bench", "both"):
    fv = fs.get_feature_view(f"fvb_{N}", version=1)
    t = time.time(); df = fv.get_batch_data(); dt = time.time() - t
    r = {"side":"hopsworks","rows":N,"features":250,"out_shape":list(df.shape),"seconds":round(dt,2)}
    print(json.dumps(r))
    open("/home/lex/feast-bench/batch_hops.jsonl","a").write(json.dumps(r)+"\n")
