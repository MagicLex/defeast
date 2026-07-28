"""Feature reusability on Feast: define a feature view once, reuse it across feature services
with no recompute, then probe for lineage (which services consume a feature view)."""
import datetime, os
import pandas as pd, numpy as np
from feast import FeatureStore, Entity, Field, FeatureView, FileSource, FeatureService
from feast.types import Int64

# small data
df=pd.DataFrame({"entity":np.arange(1000),"event_timestamp":pd.Timestamp("2026-01-01",tz="UTC")})
for i in range(10): df[f"f{i}"]=np.random.randint(0,100,1000)
df.to_parquet("/tmp/reuse.parquet")
repo="/tmp/feast_reuse"; os.makedirs(repo+"/data",exist_ok=True)
open(repo+"/feature_store.yaml","w").write("project: reuse\nprovider: local\nregistry: data/registry.db\nonline_store:\n  type: sqlite\noffline_store:\n  type: file\nentity_key_serialization_version: 3\n")
src=FileSource(path="/tmp/reuse.parquet",timestamp_field="event_timestamp")
ent=Entity(name="entity",join_keys=["entity"])
shared=FeatureView(name="shared",entities=[ent],ttl=datetime.timedelta(days=3650),
    schema=[Field(name=f"f{i}",dtype=Int64) for i in range(10)],online=False,source=src)
svc_a=FeatureService(name="model_a",features=[shared[[f"f{i}" for i in range(5)]]])
svc_b=FeatureService(name="model_b",features=[shared[[f"f{i}" for i in range(3,10)]]])
store=FeatureStore(repo_path=repo)
store.apply([ent,shared,svc_a,svc_b])
print("REUSE: 1 feature view reused by 2 feature services via feast apply. No materialization/recompute triggered (apply is metadata only).")

print("=== LINEAGE probe: which services consume feature view 'shared'? ===")
# Feast has no reverse-lineage API. You must scan every feature service manually.
consumers=[]
for svc in store.list_feature_services():
    for proj in svc.feature_view_projections:
        if proj.name=="shared": consumers.append(svc.name)
print("native fg/fv -> consumers API:", "none (Feast registry has no reverse lineage)")
print("manual scan of all feature services finds:", consumers)
print("Feast also has no model<-feature lineage: the registry does not record which models use which features.")
