"""Stepped open-loop load shape: hold a constant target arrival rate for a
fixed window, step up, repeat. Sweeps RPS to expose the saturation knee.

How RPS maps to users:
  Every user in the locustfiles has wait_time = constant_throughput(RPS_PER_USER),
  i.e. each user is a fixed-rate arrival generator firing RPS_PER_USER req/s
  regardless of how long responses take (it sleeps only the remainder of its
  1/RPS_PER_USER budget). So:

      target RPS = users * RPS_PER_USER  =>  users = ceil(target / RPS_PER_USER)

  This is open-loop as long as per-request latency < 1/RPS_PER_USER (1 s at the
  default). Past that point a user cannot maintain its rate and the harness
  degrades toward closed-loop: measured RPS falls below the step target. That
  divergence IS the signal: the first step where achieved RPS < target (or p99
  blows through the SLO) is the saturation knee. Keep RPS_PER_USER low (1) so
  the open-loop guarantee holds far beyond any sane SLO.

Usage: pass this file alongside a locustfile, Locust picks up any
LoadTestShape subclass it finds:

  locust -f locustfile_feast.py,shape.py --headless

Env:
  RPS_STEPS    comma list of target RPS steps (default 50,100,200,400,800,1600)
  STEP_SECONDS hold time per step (default 30)
  RPS_PER_USER MUST match the value the locustfile uses (default 1.0)

Note: user count equals target RPS at the default RPS_PER_USER, so the 1600
step needs 1600 users. FastHttpUser handles that in one process, but above
~1000 users give Locust more cores with --processes N (workers are forked and
the shape drives the aggregate). Total run at defaults: 6 steps * 30 s = 3 min.
"""
import math
import os

from locust import LoadTestShape

RPS_STEPS = [int(s) for s in os.getenv("RPS_STEPS", "50,100,200,400,800,1600").split(",")]
STEP_SECONDS = int(os.getenv("STEP_SECONDS", "30"))
RPS_PER_USER = float(os.getenv("RPS_PER_USER", "1"))


class SteppedArrivalRateShape(LoadTestShape):
    def tick(self):
        run_time = self.get_run_time()
        step = int(run_time // STEP_SECONDS)
        if step >= len(RPS_STEPS):
            return None  # sweep done, stop the run
        users = math.ceil(RPS_STEPS[step] / RPS_PER_USER)
        # Spawn rate = users: the whole step comes up in about a second, so
        # nearly the full window measures the target rate steady-state.
        return (users, users)
