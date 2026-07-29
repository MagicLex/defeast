#!/bin/bash
PY=~/feast-bench/.venv/bin/python
VEG=~/.local/bin/vegeta
DUR=15s; RATE=10
cell(){ # side port batch features
  $PY ~/gen_targets.py --url http://127.0.0.1:$2/get-online-features --batch $3 --features $4 --requests 500 --output /tmp/t_$1.json
  R=$($VEG attack -format=json -targets=/tmp/t_$1.json -rate=${RATE}/1s -duration=${DUR} -timeout=10s | $VEG report -type=json)
  echo "$R" | $PY -c "import sys,json; d=json.load(sys.stdin); l=d['latencies']; print('$1 batch=$3 feats=$4 -> p50=%.2f p90=%.2f p99=%.2f max=%.2f ms | success=%.1f%%'%(l['50th']/1e6,l['90th']/1e6,l['99th']/1e6,l['max']/1e6,d['success']*100))"
  echo "{\"side\":\"$1\",\"batch\":$3,\"features\":$4,\"rate\":$RATE,\"latencies_ms\":{\"p50\":$(echo $R|$PY -c 'import sys,json;print(json.load(sys.stdin)["latencies"]["50th"]/1e6)'),\"p90\":$(echo $R|$PY -c 'import sys,json;print(json.load(sys.stdin)["latencies"]["90th"]/1e6)'),\"p99\":$(echo $R|$PY -c 'import sys,json;print(json.load(sys.stdin)["latencies"]["99th"]/1e6)'),\"max\":$(echo $R|$PY -c 'import sys,json;print(json.load(sys.stdin)["latencies"]["max"]/1e6)')},\"success\":$(echo $R|$PY -c 'import sys,json;print(json.load(sys.stdin)["success"])')}" >> ~/feast-bench/http_$1.jsonl
}
side=$1; port=$2
: > ~/feast-bench/http_$side.jsonl
for b in 1 10 25 50 100; do cell $side $port $b 50; done
for f in 100 150 200 250; do cell $side $port 1 $f; done
echo "DONE $side"
