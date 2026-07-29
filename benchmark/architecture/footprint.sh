#!/usr/bin/env bash
# Capture the serving-component footprint for the architecture table, in-cluster.
# The benchmark runs both stores on one node; this reads the serving pods with
# `kubectl top`. Requires KUBECONFIG set. Run while the store holds the benchmark
# data (materialized), ideally under load for the CPU columns.
set -euo pipefail

echo "== Hopsworks serving path =="
echo "-- RDRS (RonDB REST Data Service, the online read endpoint) --"
kubectl top pod -n hopsworks 2>/dev/null | grep -E 'NAME|rdrs' || true
echo "-- RonDB datanodes (the in-memory online store) --"
kubectl top pod -n hopsworks 2>/dev/null | grep -E 'datanode' || true
echo "rdrs pods:      $(kubectl -n hopsworks get pods 2>/dev/null | grep -c rdrs || true)"
echo "datanode pods:  $(kubectl -n hopsworks get pods 2>/dev/null | grep -c datanode || true)"

echo
echo "== Feast serving path (defeast-bench namespace) =="
echo "-- Redis (online store) --"
kubectl top pod -n defeast-bench 2>/dev/null | grep -E 'NAME|redis' || echo "redis not running (scale it up to measure)"
echo "-- feast serve (gunicorn) --"
echo "run 'feast serve' in the feast-client pod, then: kubectl top pod -n defeast-bench | grep feast-client"
echo "the pod runs only feast serve, so pod RSS is the server footprint."
