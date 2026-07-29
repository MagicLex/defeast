"""Locust load for the Hopsworks feature server (hops_server.py, gunicorn).

Identical harness to locustfile_feast.py (same open-loop user model, same
batch/feature parameterization, same random entity draw) so the two sides are
load-tested identically. Only the endpoint and body shape differ.

Run:
  locust -f locustfile_hops.py,shape.py --headless \
      --host http://127.0.0.1:6567 --csv results/hops_b1_f50 --csv-full-history

Env:
  BATCH        entities per request (default 1)
  FEATURES     50|100|150|200|250, mapped to fv_50..fv_250 (default 50)
  KEYSPACE     entity id range (default 10000, matches the seeded data)
  RPS_PER_USER per-user arrival rate, must match shape.py (default 1.0)

Request shape (hops_server.py):
  POST /get-feature-vector
  {"feature_view": "fv_50", "entries": [{"entity": 1}, {"entity": 2}]}
"""
import os
import random

from locust import constant_throughput, task
from locust.contrib.fasthttp import FastHttpUser

BATCH = int(os.getenv("BATCH", "1"))
FEATURES = int(os.getenv("FEATURES", "50"))
KEYSPACE = int(os.getenv("KEYSPACE", "10000"))
RPS_PER_USER = float(os.getenv("RPS_PER_USER", "1"))

FEATURE_VIEW = f"fv_{FEATURES}"


class HopsUser(FastHttpUser):
    # Same client as the Feast side (FastHttpUser) so generator overhead is
    # identical on both sides.
    wait_time = constant_throughput(RPS_PER_USER)

    @task
    def get_feature_vector(self):
        body = {
            "feature_view": FEATURE_VIEW,
            "entries": [
                {"entity": random.randrange(KEYSPACE)} for _ in range(BATCH)
            ],
        }
        self.client.post(
            "/get-feature-vector",
            json=body,
            name=f"hops batch={BATCH} features={FEATURES}",
        )
