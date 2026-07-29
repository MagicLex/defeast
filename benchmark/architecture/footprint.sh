#!/usr/bin/env bash
# footprint.sh - capture the serving-component footprint numbers for
# benchmark/architecture/README.md ("Serving-component footprint" table).
#
# Run on the benchmark host, ideally while the latency sweep is generating load,
# so "CPU under load" means what it says.
#
# Prerequisites (nothing is hardcoded here):
#   - podman running the Redis container as "bench-redis"
#   - "feast serve" running as a host process
#   - KUBECONFIG already exported by the caller, pointing at the Hopsworks cluster
#
# Output maps 1:1 onto the README table rows. Copy the numbers by hand.

set -u

echo "=============================================================="
echo " Serving-component footprint capture"
echo " ($(date -u +%FT%TZ))"
echo "=============================================================="

# --- Row: Feast: Redis (bench-redis) ---------------------------------------
echo
echo "--- Feast: Redis (container bench-redis) ---"
echo "    -> README row 'Feast: Redis': MEM USAGE = RSS, CPU % = CPU under load"
if command -v podman >/dev/null 2>&1; then
    podman stats --no-stream bench-redis || echo "    [warn] bench-redis not running?"
    echo "    container count:"
    podman ps --filter name=bench-redis --format '{{.Names}}' | wc -l
else
    echo "    [warn] podman not found on this host"
fi

# --- Row: Feast: feast serve (gunicorn) ------------------------------------
echo
echo "--- Feast: feast serve (host process) ---"
echo "    -> README row 'Feast: feast serve': RSS in KiB (sum), %CPU per process"
FEAST_PIDS=$(pgrep -f "feast serve" || true)
if [ -n "${FEAST_PIDS}" ]; then
    # Per-process detail: pid, RSS (KiB), %CPU, command.
    # gunicorn forks workers, so expect one master + N workers; the table
    # wants the sum of RSS and the process count.
    ps -o pid,rss,pcpu,etime,comm -p ${FEAST_PIDS}
    echo "    process count:"
    echo "${FEAST_PIDS}" | wc -w
    echo "    total RSS (KiB):"
    ps -o rss= -p ${FEAST_PIDS} | awk '{sum+=$1} END {print sum}'
else
    echo "    [warn] no 'feast serve' process found (pgrep -f \"feast serve\")"
fi

# --- Rows: Hopsworks RDRS pod and RonDB datanode pod ------------------------
# These run on the cluster, not this host. The commands below are printed AND
# executed if kubectl is available; if this host has no cluster access, run
# them wherever KUBECONFIG works.
echo
echo "--- Hopsworks: RDRS and RonDB datanode pods (namespace: hopsworks) ---"
echo "    -> README rows 'Hopsworks: RDRS pod' and 'Hopsworks: RonDB datanode pod'"
echo "    Commands (run where KUBECONFIG is set):"
echo "      kubectl -n hopsworks top pod | grep -Ei 'rdrs'"
echo "      kubectl -n hopsworks top pod | grep -Ei 'rondb|datanode|ndbmtd'"
echo "      kubectl -n hopsworks get pod | grep -Eic 'rdrs'"
echo "      kubectl -n hopsworks get pod | grep -Eic 'rondb|datanode|ndbmtd'"
if command -v kubectl >/dev/null 2>&1 && [ -n "${KUBECONFIG:-}" ]; then
    echo
    echo "    RDRS pod usage (MEMORY = RSS proxy, CPU = CPU under load):"
    kubectl -n hopsworks top pod 2>/dev/null | grep -Ei 'rdrs' \
        || echo "    [warn] no rdrs pod in 'kubectl top' output (metrics-server up?)"
    echo "    RDRS pod count:"
    kubectl -n hopsworks get pod --no-headers 2>/dev/null | grep -Eic 'rdrs'
    echo
    echo "    RonDB datanode pod usage:"
    kubectl -n hopsworks top pod 2>/dev/null | grep -Ei 'rondb|datanode|ndbmtd' \
        || echo "    [warn] no rondb/datanode pod in 'kubectl top' output"
    echo "    RonDB datanode pod count:"
    kubectl -n hopsworks get pod --no-headers 2>/dev/null | grep -Eic 'rondb|datanode|ndbmtd'
else
    echo
    echo "    [info] kubectl not available or KUBECONFIG unset here; run the"
    echo "    printed commands from a host with cluster access."
fi

echo
echo "=============================================================="
echo " Done. Fill the four '<TBD>' rows in architecture/README.md."
echo " Note: kubectl top reports working-set memory, a close RSS proxy."
echo "=============================================================="
