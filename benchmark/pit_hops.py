"""Hopsworks PIT correctness without Spark spine: probe get_batch_data(end_time=T) per label,
verify latest-as-of-T value per entity vs ground truth, and check the before-first null behavior."""
import json
import pandas as pd, hopsworks
KEY=open("/home/lex/.hw_bench_key").read().strip()
proj=hopsworks.login(host="10.113.154.130",port=443,project="feast_bench",api_key_value=KEY)
fs=proj.get_feature_store()
hist=pd.read_parquet("/tmp/pit_hist.parquet")
fg=fs.get_or_create_feature_group(name="pit_hist2",version=1,primary_key=["entity"],
    event_time="event_timestamp", online_enabled=False)
fg.insert(hist, write_options={"wait_for_job": True})
fv=fs.get_or_create_feature_view(name="pit2", version=1, query=fg.select_all())
gt=json.load(open("/tmp/pit_gt.json"))
LABELS=["2025-12-15","2026-01-01","2026-01-15","2026-02-01","2026-03-20","2026-05-01"]
ENTS=list(range(1,21))
mism=[]; dropped=[]
for L in LABELS:
    df=fv.get_batch_data(end_time=L)
    got={int(r["entity"]): (None if pd.isna(r["val"]) else int(r["val"])) for _,r in df.iterrows()}
    for e in ENTS:
        exp=gt[f"{e}|{L}"]; g=got.get(e,"DROPPED")
        if g=="DROPPED": dropped.append((e,L,exp))
        elif g!=exp: mism.append((e,L,exp,g))
print(f"HOPS PIT: {len(mism)} value-mismatches, {len(dropped)} dropped of {len(gt)}")
for m in mism[:8]: print("  MISMATCH", m)
from collections import Counter
print("dropped by label:", Counter(d[1] for d in dropped))
print("all dropped expected null?", all(d[2] is None for d in dropped) if dropped else "none dropped")
print("VERDICT:", "CORRECT+COMPLETE" if not mism and not dropped else ("CORRECT-but-drops" if not mism else "LEAKAGE/ERROR"))
