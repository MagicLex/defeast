"""Minimal Hopsworks online feature HTTP server: the structural twin of Feast's
`feast serve` (gunicorn+FastAPI calling the online store). One process per port.
Endpoint matches feast-benchmarks request_generator.py so the SAME Vegeta targets hit both.
Run: PORT=6566 uvicorn hops_server:app --host 0.0.0.0 --port $PORT"""
import os
from fastapi import FastAPI, Request
import hopsworks

KEY = open("/home/lex/.hw_bench_key").read().strip()
proj = hopsworks.login(host="10.113.154.130", port=443, project="feast_bench", api_key_value=KEY)
fs = proj.get_feature_store()
# feature_service_N (Feast) -> fv_{50*(N+1)} (Hopsworks): N=0->50 .. N=4->250
FVS = {n: fs.get_feature_view(f"fv_{50*(n+1)}", version=1) for n in range(5)}
for fv in FVS.values():
    fv.init_serving()

app = FastAPI()

@app.post("/get-online-features")
async def get_online_features(req: Request):
    body = await req.json()
    n = int(body["feature_service"].split("_")[-1])
    ents = body["entities"]["entity"]
    fv = FVS[n]
    if len(ents) == 1:
        vec = fv.get_feature_vector({"entity": int(ents[0])})
    else:
        vec = fv.get_feature_vectors([{"entity": int(e)} for e in ents])
    return {"n": len(vec)}
