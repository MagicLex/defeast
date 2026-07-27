#!/bin/bash
# HTTP feature-server benchmark via Vegeta. Same sweep as the SDK bench.
# Usage: ./run_http.sh <side> <port>   (side=feast|hops)
SIDE=$1; PORT=$2
GEN=~/feast-bench/.venv/bin/python   # gen_targets uses numpy/click, in feast venv
VEG=~/.local/bin/vegeta
DUR=${DUR:-20s}; RATE=${RATE:-50}
OUT=~/feast-bench/http_${SIDE}.jsonl; : > $OUT
run(){ # batch features
  $GEN ~/gen_targets.py --url http://127.0.0.1:${PORT}/get-online-features --batch $1 --features $2 --requests 4000 --output /tmp/t.json
  R=$($VEG attack -format=json -targets=/tmp/t.json -rate=${RATE}/1s -duration=${DUR} -timeout=10s | $VEG report -type=json)
  echo "{\"side\":\"$SIDE\",\"batch\":$1,\"features\":$2,\"rate\":${RATE},\"vegeta\":$R}" >> $OUT
  echo "batch=$1 feats=$2 -> $(echo $R | ~/feast-bench/.venv/bin/python -c 'import sys,json; d=json.load(sys.stdin); l=d["latencies"]; print("p50=%.1fms p99=%.1fms p999=%.1fms success=%.1f%% rps=%.0f"%(l["50th"]/1e6,l["99th"]/1e6,l["999th"]/1e6,d["success"]*100,d["rate"]))')"
}
for b in 1 10 25 50 100; do run $b 50; done
for f in 100 150 200 250; do run 1 $f; done
echo "DONE $SIDE"
