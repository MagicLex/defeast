"""Feast point-in-time correctness: get_historical over the spine, compare each returned
value to ground truth (as-of latest event_time <= label). Reports mismatches."""
import json, datetime, os
import pandas as pd
from feast import FeatureStore, Entity, Field, FeatureView, FileSource
from feast.types import Int64

repo = "/tmp/feast_pit"; os.makedirs(repo+"/data", exist_ok=True)
open(repo+"/feature_store.yaml","w").write(
    "project: pit\nprovider: local\nregistry: data/registry.db\n"
    "online_store:\n  type: sqlite\noffline_store:\n  type: file\nentity_key_serialization_version: 3\n")
src = FileSource(path="/tmp/pit_hist.parquet", timestamp_field="event_timestamp")
ent = Entity(name="entity", join_keys=["entity"])
fv = FeatureView(name="hist", entities=[ent], ttl=datetime.timedelta(days=36500),
                 schema=[Field(name="val", dtype=Int64)], online=False, source=src)
store = FeatureStore(repo_path=repo); store.apply([ent, fv])

spine = pd.read_parquet("/tmp/pit_spine.parquet")
out = store.get_historical_features(entity_df=spine, features=["hist:val"]).to_df()
gt = json.load(open("/tmp/pit_gt.json"))

mism = []
for _, r in out.iterrows():
    key = f"{int(r['entity'])}|{pd.Timestamp(r['event_timestamp']).strftime('%Y-%m-%d')}"
    exp = gt[key]
    got = None if pd.isna(r['val']) else int(r['val'])
    if got != exp: mism.append((key, exp, got))
print(f"FEAST PIT: {len(out)} rows, {len(mism)} mismatches of {len(gt)}")
for m in mism[:10]: print("  MISMATCH", m)
print("VERDICT:", "CORRECT" if not mism else "LEAKAGE/ERROR")

# coverage: which spine rows are missing entirely (dropped vs returned-null)?
returned = set(f"{int(r['entity'])}|{pd.Timestamp(r['event_timestamp']).strftime('%Y-%m-%d')}" for _,r in out.iterrows())
missing = [k for k in gt if k not in returned]
print(f"COVERAGE: {len(returned)}/{len(gt)} spine rows returned; {len(missing)} dropped")
from collections import Counter
print("dropped by label:", Counter(k.split('|')[1] for k in missing))
print("all dropped are before-first (expected null)?", all(gt[k] is None for k in missing))
