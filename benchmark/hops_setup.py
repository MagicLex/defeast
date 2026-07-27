"""Hopsworks side of the Feast-vs-Hopsworks benchmark.
Mirrors feast-benchmarks: 25 feature groups x 10 features, entity pk, 5 feature views (50..250 features).
Same generated_data.parquet as the Feast side."""
import time, sys
import pandas as pd
import hopsworks

KEY = open("/home/lex/.hw_bench_key").read().strip()
DATA = "/home/lex/feast-bench/generated_data.parquet"
NUM_FG = 25
FEATS_PER_FG = 10

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

df = pd.read_parquet(DATA)
log(f"data {df.shape}, entities unique={df.entity.nunique()}")

proj = hopsworks.login(host="10.113.154.130", port=443, project="feast_bench", api_key_value=KEY)
fs = proj.get_feature_store()
log(f"connected fs={fs.name}")

t0 = time.time()
for i in range(NUM_FG):
    cols = ["entity", "event_timestamp"] + [f"feature_{FEATS_PER_FG*i+j}" for j in range(FEATS_PER_FG)]
    sub = df[cols].copy()
    fg = fs.get_or_create_feature_group(
        name=f"fg_{i}", version=1,
        primary_key=["entity"], event_time="event_timestamp",
        online_enabled=True,
        description=f"bench fg {i}: features {FEATS_PER_FG*i}..{FEATS_PER_FG*i+FEATS_PER_FG-1}",
    )
    fg.insert(sub, write_options={"wait_for_job": True})
    log(f"fg_{i} inserted ({len(cols)-2} feats)")

# feature views: 50,100,150,200,250 features -> join first 5,10,15,20,25 FGs
for k, nfg in enumerate([5,10,15,20,25]):
    base = fs.get_feature_group(f"fg_0", version=1)
    q = base.select_all()
    for i in range(1, nfg):
        q = q.join(fs.get_feature_group(f"fg_{i}", version=1).select_all(), on=["entity"], prefix=f"g{i}_")
    fv = fs.get_or_create_feature_view(name=f"fv_{50*(k+1)}", version=1, query=q)
    log(f"fv_{50*(k+1)} created ({nfg} FGs -> {nfg*FEATS_PER_FG} feats)")

log(f"DONE in {time.time()-t0:.0f}s")
