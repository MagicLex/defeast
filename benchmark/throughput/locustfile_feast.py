"""Locust load for the Feast feature server (`feast serve`, gunicorn).

Open-loop arrival generator: each user fires at a fixed rate
(constant_throughput(RPS_PER_USER)), independent of response time as long as
latency stays under 1/RPS_PER_USER. The stepped shape in shape.py scales the
user count so aggregate target RPS = users * RPS_PER_USER. See shape.py for
the open-loop caveat at saturation.

Run:
  locust -f locustfile_feast.py,shape.py --headless \
      --host http://127.0.0.1:6566 --csv results/feast_b1_f50 --csv-full-history

Env:
  BATCH        entities per request (default 1)
  FEATURES     50|100|150|200|250, mapped to feature_service_0..4 (default 50)
  KEYSPACE     entity id range (default 10000, matches the seeded data)
  RPS_PER_USER per-user arrival rate, must match shape.py (default 1.0)

Request shape matches feast-benchmarks / gen_targets.py:
  POST /get-online-features
  {"feature_service": "feature_service_0",
   "entities": {"entity": [1, 2, 3]},
   "full_feature_names": false}
"""
import os
import random

from locust import constant_throughput, task
from locust.contrib.fasthttp import FastHttpUser

BATCH = int(os.getenv("BATCH", "1"))
FEATURES = int(os.getenv("FEATURES", "50"))
KEYSPACE = int(os.getenv("KEYSPACE", "10000"))
RPS_PER_USER = float(os.getenv("RPS_PER_USER", "1"))

# feature_service_N serves 50*(N+1) features: 50 -> _0 ... 250 -> _4.
SERVICE = f"feature_service_{FEATURES // 50 - 1}"


class FeastUser(FastHttpUser):
    # FastHttpUser (geventhttpclient) instead of HttpUser (requests): the
    # requests-based client caps out well below the RPS this sweep targets and
    # would make the load generator the bottleneck.
    wait_time = constant_throughput(RPS_PER_USER)

    @task
    def get_online_features(self):
        body = {
            "feature_service": SERVICE,
            "entities": {
                "entity": [random.randrange(KEYSPACE) for _ in range(BATCH)]
            },
            "full_feature_names": False,
        }
        # Non-2xx is auto-recorded as a failure; one stats bucket per cell.
        self.client.post(
            "/get-online-features",
            json=body,
            name=f"feast batch={BATCH} features={FEATURES}",
        )
