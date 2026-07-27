import datetime
from feast import Entity, Field, FeatureView, FileSource, FeatureService
from feast.types import Int64
src = FileSource(path="/home/lex/feast-bench/generated_data.parquet", timestamp_field="event_timestamp")
entity = Entity(name="entity", join_keys=["entity"])
feature_views = [
    FeatureView(name=f"feature_view_{i}", entities=[entity],
        ttl=datetime.timedelta(days=3650),
        schema=[Field(name=f"feature_{10*i+j}", dtype=Int64) for j in range(10)],
        online=True, source=src)
    for i in range(25)]
feature_services = [FeatureService(name=f"feature_service_{i}", features=feature_views[:5*(i+1)]) for i in range(5)]
globals().update({fv.name: fv for fv in feature_views})
globals().update({fs.name: fs for fs in feature_services})
