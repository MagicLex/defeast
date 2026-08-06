"""Hopsworks offline on-the-fly build, measured with the CORRECT API: training_data().

This is the spine-driven PIT training build, the true analogue of Feast
get_historical_features. It replaces the get_batch_data (time-range) numbers used in
the earlier width sweep and 100k/1M scale points, so the whole offline axis rides one
API. Groups are DELTA (the only offline-readable format on 5.0.x via Arrow Flight).

25 DELTA feature groups (10 int64 features each) of N unique-entity rows are built once
per N; a width-W view joins the first W of them, so W groups = 10*W features. Bench times
fv.training_data() warm: one untimed warmup, then REPEAT timed builds, reporting warm
median and min.

Modes:
  groups         build the 25 DELTA groups for this N (idempotent: skips ones already present)
  view <W>       create/reuse the width-W feature view over the first W groups
  bench <W>      time training_data() on the width-W view

Usage: python training_data_hops.py <N> <parquet> groups
       python training_data_hops.py <N> <parquet> view <W>
       python training_data_hops.py <N> <parquet> bench <W>
"""
import sys, time, json, statistics
import pandas as pd, hopsworks

N = int(sys.argv[1]); PARQUET = sys.argv[2]; MODE = sys.argv[3]
W = int(sys.argv[4]) if len(sys.argv) > 4 else 25
REPEAT = 3
NGROUPS = 25
OUT = "/home/lex/offbench/training_data_hops.jsonl"

KEY = open("/home/lex/.hw_bench_key").read().strip()
proj = hopsworks.login(host="10.113.154.130", port=443, project="feast_bench", api_key_value=KEY)
fs = proj.get_feature_store()

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

gname = lambda i: f"d{N}g{i}"
fvname = lambda w: f"fvtd_{N}_{w}"

def existing(name):
    try:
        return fs.get_feature_group(name=name, version=1)
    except Exception:
        return None

if MODE == "groups":
    for i in range(NGROUPS):
        if existing(gname(i)) is not None:
            log(f"{gname(i)} exists, skip")
            continue
        cols = ["entity", "event_timestamp"] + [f"feature_{10*i+j}" for j in range(10)]
        sub = pd.read_parquet(PARQUET, columns=cols)
        fg = fs.create_feature_group(
            name=gname(i), version=1, primary_key=["entity"],
            event_time="event_timestamp", online_enabled=False,
            time_travel_format="DELTA")
        fg.insert(sub, write_options={"wait_for_job": True})
        log(f"{gname(i)} inserted ({N} rows, DELTA)")
    log("groups ready")

elif MODE == "view":
    q = fs.get_feature_group(gname(0), version=1).select_all()
    for i in range(1, W):
        q = q.join(fs.get_feature_group(gname(i), version=1).select_all(),
                   on=["entity"], prefix=f"g{i}_")
    fs.get_or_create_feature_view(name=fvname(W), version=1, query=q)
    log(f"{fvname(W)} created (W={W}, {10*W} features)")

elif MODE == "bench":
    fv = fs.get_feature_view(fvname(W), version=1)

    # statistics_config=False: build the PIT join and return rows, nothing more, so it
    # is the same operation as Feast get_historical_features. Default training_data also
    # computes feature statistics (Feast's call does not), which would add Hopsworks-only
    # work to the timing and make the head-to-head unfair.
    def build():
        td = fv.training_data(statistics_config=False)
        return td[0] if isinstance(td, tuple) else td

    shape = list(build().shape)  # warmup + capture out shape
    times = []
    for _ in range(REPEAT):
        t = time.time(); build(); times.append(time.time() - t)
    r = {"cluster": "dev0", "side": "hopsworks", "method": "training_data",
         "rows": N, "groups": W, "features": 10 * W, "engine": "delta/HQS",
         "out_shape": shape, "warm_median_s": round(statistics.median(times), 2),
         "warm_min_s": round(min(times), 2), "all_s": [round(x, 2) for x in times]}
    print(json.dumps(r))
    open(OUT, "a").write(json.dumps(r) + "\n")
