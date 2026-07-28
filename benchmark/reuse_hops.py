"""Feature reusability on Hopsworks: define a feature group once, reuse its features across
multiple feature views with no recompute, then show lineage (which FVs consume the FG)."""
import time, pandas as pd, numpy as np, hopsworks
KEY=open("/home/lex/.hw_bench_key").read().strip()
proj=hopsworks.login(host="10.113.154.130",port=443,project="feast_bench",api_key_value=KEY)
fs=proj.get_feature_store(); japi=proj.get_job_api()
def njobs(): return len(japi.get_jobs())

df=pd.DataFrame({"entity":np.arange(1000),"event_timestamp":pd.Timestamp("2026-01-01",tz="UTC")})
for i in range(10): df[f"f{i}"]=np.random.randint(0,100,1000)
fg=fs.get_or_create_feature_group(name="reuse_shared",version=1,primary_key=["entity"],
    event_time="event_timestamp",online_enabled=False)
fg.insert(df, write_options={"wait_for_job": True})
print("shared FG created + inserted once.")

jobs_before=njobs()
fv_a=fs.get_or_create_feature_view(name="reuse_model_a",version=1,query=fg.select([f"f{i}" for i in range(5)]))
fv_b=fs.get_or_create_feature_view(name="reuse_model_b",version=1,query=fg.select([f"f{i}" for i in range(3,10)]))
jobs_after=njobs()
print(f"REUSE: created 2 feature views reusing the FG. New compute jobs triggered: {jobs_after-jobs_before}")

# lineage: which feature views consume this FG?
print("=== LINEAGE probe ===")
for m in ["get_feature_views","provenance","get_generated_feature_views"]:
    if hasattr(fg,m):
        try:
            r=getattr(fg,m)()
            print(f"fg.{m}() ->", [getattr(x,'name',x) for x in (r if isinstance(r,list) else getattr(r,'accessible',[r]))][:6])
        except Exception as e: print(f"fg.{m}() err:", str(e)[:100])
    else: print(f"fg.{m}: not available")
