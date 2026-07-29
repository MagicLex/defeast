"""Fair Hopsworks online-feature HTTP server for the throughput benchmark.

Structural twin of `feast serve` (Feast's feature server: a FastAPI app run
under gunicorn with uvicorn workers, sync `def` handlers).

Worker model choice (why this shape):
  - Feast's server is a gunicorn master + N worker processes; its handlers are
    sync, so blocking store I/O never stalls an event loop, and parallelism
    comes from processes.
  - The previous version of this file was a SINGLE async uvicorn worker whose
    `async def` handler called the blocking hsfs client. That blocked the event
    loop and reset connections under load (see RESULTS.md). Known flaw, fixed here.
  - This version: sync (`def`) endpoint, so the blocking hsfs call runs in the
    worker's threadpool, run under gunicorn with N uvicorn workers. Run both
    sides with the SAME worker count (feast serve --workers N <=> WORKERS=N here)
    or the comparison is meaningless.

Run (gunicorn preferred, mirrors feast serve exactly; do NOT use --preload,
each worker must own its hsfs connections post-fork):

  gunicorn hops_server:app -k uvicorn.workers.UvicornWorker \
      -w ${WORKERS:-4} -b 127.0.0.1:6567 --timeout 120

  # equivalent: uvicorn hops_server:app --workers ${WORKERS:-4} --host 127.0.0.1 --port 6567

Bind to 127.0.0.1 or a cluster-internal address, never 0.0.0.0 (dev0 is
internet-facing with no host firewall).

Env:
  HOPSWORKS_HOST          Hopsworks API host (required)
  HOPSWORKS_API_KEY_FILE  path to API key file (default ~/.hw_bench_key)
  RDRS_HOST               in-cluster RDRS REST host (default 10.103.3.227)
  RDRS_PORT               RDRS REST port (default 4406)
  FEATURE_VIEWS           comma list of feature views to serve
                          (default fv_50,fv_100,fv_150,fv_200,fv_250)

Startup cost: login + init_serving run at import time in EVERY worker (this is
the correct per-process behavior, same as Feast workers each opening their own
store connections). init_serving on the 25-group view takes ~40 s, so restrict
FEATURE_VIEWS to the view under test when iterating.

ASSUMPTIONS to validate against the live hsfs version:
  - config_rest_client key names ("host", "port", "verify_certs", "use_ssl",
    "api_key") match the installed hsfs; check
    hsfs.core.online_store_rest_client if init fails.
  - get_feature_vectors returns JSON-serializable values for this dataset
    (numeric features). If not, the response encoder needs a default handler.
"""
import os

from fastapi import FastAPI
import hopsworks

KEY = open(
    os.environ.get("HOPSWORKS_API_KEY_FILE", os.path.expanduser("~/.hw_bench_key"))
).read().strip()
RDRS_HOST = os.environ.get("RDRS_HOST", "10.103.3.227")
RDRS_PORT = int(os.environ.get("RDRS_PORT", "4406"))
FEATURE_VIEWS = os.environ.get(
    "FEATURE_VIEWS", "fv_50,fv_100,fv_150,fv_200,fv_250"
).split(",")

proj = hopsworks.login(
    host=os.environ["HOPSWORKS_HOST"],
    port=443,
    project="feast_bench",
    api_key_value=KEY,
)
fs = proj.get_feature_store()

FVS = {}
for name in FEATURE_VIEWS:
    fv = fs.get_feature_view(name, version=1)
    # REST online client pinned to the in-cluster RDRS endpoint so reads stay
    # same-node; no cert verification (internal IP, self-signed), ssl on.
    fv.init_serving(
        init_rest_client=True,
        config_rest_client={
            "host": RDRS_HOST,
            "port": RDRS_PORT,
            "verify_certs": False,
            "use_ssl": True,
            "api_key": KEY,
        },
        default_client="rest",
    )
    FVS[name] = fv

app = FastAPI()


@app.post("/get-feature-vector")
def get_feature_vector(body: dict):
    # Sync handler on purpose: runs in the worker threadpool, blocking hsfs I/O
    # never touches the event loop. Batch 1 goes through get_feature_vectors
    # too, matching the Feast server which always takes a list of entity rows.
    fv = FVS[body["feature_view"]]
    entries = [{"entity": int(e["entity"])} for e in body["entries"]]
    vecs = fv.get_feature_vectors(entries, force_rest_client=True)
    # Return the full vectors, not a count: Feast's server serializes every
    # feature value into the response, so skipping serialization here would
    # unfairly favor Hopsworks.
    return {"results": vecs}
