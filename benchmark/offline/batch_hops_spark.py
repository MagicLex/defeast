import os
"""Hopsworks 10M training-data generation via Spark (production path for large scale).
create_training_data submits a Spark job on the cluster (not the client Python/ArrowFlight
engine that OOMs at this scale). Times the job. Feast has no equivalent (file offline = pandas)."""
import sys, time, json
import hopsworks
N = int(sys.argv[1])
KEY = open(os.environ.get("HOPSWORKS_API_KEY_FILE", os.path.expanduser("~/.hw_bench_key"))).read().strip()
proj = hopsworks.login(host=os.environ["HOPSWORKS_HOST"], port=443, project="feast_bench", api_key_value=KEY)
fs = proj.get_feature_store()
fv = fs.get_feature_view(f"fvb_{N}", version=1)
print(f"[{time.strftime('%H:%M:%S')}] create_training_data via Spark, N={N}", flush=True)
t = time.time()
version, job = fv.create_training_data(write_options={"wait_for_job": True, "use_spark": True})
dt = time.time() - t
r = {"side":"hopsworks_spark","rows":N,"features":250,"td_version":version,"seconds":round(dt,2)}
print(json.dumps(r))
open("/home/lex/feast-bench/batch_hops.jsonl","a").write(json.dumps(r)+"\n")
