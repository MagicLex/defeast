"""Feast offline (training data) benchmark: time get_historical_features for a spine
of all N unique entities, 250 features (25 FVs over one parquet). Appends JSONL."""
import sys, time, json, datetime, shutil, os
import pandas as pd
from feast import FeatureStore, Entity, Field, FeatureView, FileSource
from feast.types import Int64

N = int(sys.argv[1]); PARQUET = sys.argv[2]
repo = f"/tmp/feast_batch_{N}"
os.makedirs(repo+"/data", exist_ok=True)
open(repo+"/feature_store.yaml","w").write(
    f"project: batch_{N}\nprovider: local\nregistry: data/registry.db\n"
    "online_store:\n  type: sqlite\noffline_store:\n  type: file\nentity_key_serialization_version: 3\n")
src = FileSource(path=PARQUET, timestamp_field="event_timestamp")
ent = Entity(name="entity", join_keys=["entity"])
fvs = [FeatureView(name=f"fv_{i}", entities=[ent], ttl=datetime.timedelta(days=3650),
        schema=[Field(name=f"feature_{10*i+j}", dtype=Int64) for j in range(10)],
        online=False, source=src) for i in range(25)]
store = FeatureStore(repo_path=repo)
store.apply([ent, *fvs])
spine = pd.DataFrame({"entity": pd.read_parquet(PARQUET, columns=["entity"])["entity"].values,
                      "event_timestamp": pd.Timestamp("2026-06-01", tz="UTC")})
feats = [f"fv_{i}:feature_{10*i+j}" for i in range(25) for j in range(10)]
t = time.time()
out = store.get_historical_features(entity_df=spine, features=feats).to_df()
dt = time.time() - t
r = {"side":"feast","rows":N,"features":250,"out_shape":list(out.shape),"seconds":round(dt,2)}
print(json.dumps(r))
open("/home/lex/feast-bench/batch_feast.jsonl","a").write(json.dumps(r)+"\n")
shutil.rmtree(repo, ignore_errors=True)
