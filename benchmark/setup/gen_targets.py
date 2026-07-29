"""Vegeta target generator, same request shape as feast-benchmarks request_generator.py
but parameterized by host:port so it can hit either server. Writes vegeta JSON targets."""
import click, json, base64
import numpy as np

@click.command()
@click.option('--url', required=True)          # e.g. http://127.0.0.1:6566/get-online-features
@click.option('--features', default=50)
@click.option('--batch', default=1)
@click.option('--keyspace', default=10**4)
@click.option('--requests', default=2000)
@click.option('--output', default='targets.json')
def gen(url, features, batch, keyspace, requests, output):
    fs = f"feature_service_{features//50 - 1}"
    lines = []
    for _ in range(requests):
        body = {"feature_service": fs, "entities": {"entity": np.random.randint(0, keyspace, batch).tolist()}}
        lines.append(json.dumps({"method":"POST","url":url,
            "header":{"Content-Type":["application/json"]},
            "body": base64.b64encode(json.dumps(body).encode()).decode()}))
    open(output,'w').write("\n".join(lines))

if __name__ == '__main__':
    gen()
