"""Render the benchmark charts embedded in README.md from the measured numbers.
Latency charts (online_latency, tail_latency) read the raw per-cell percentiles from
latency/results/*_incluster.jsonl. Throughput reads the Locust ramp from
throughput/results/*_history.csv. Offline reads the transcribed crossover (no raw
file, numbers sourced from offline/RESULTS.md). Run:
    python plot.py   ->   img/{online_latency,tail_latency,throughput,offline_scale}.png
"""

import csv
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

FEAST, HOPS, TXT, MUT, GRID = "#eb6834", "#2a78d6", "#2b2b2b", "#8a8a8a", "#e6e6e3"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "text.color": TXT,
    "axes.edgecolor": "#cfcfca", "axes.labelcolor": TXT, "axes.titlecolor": TXT,
    "xtick.color": MUT, "ytick.color": MUT, "axes.linewidth": 0.8,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
})
MARK = dict(marker="o", ms=5, lw=2.4, zorder=3)
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, "img"), exist_ok=True)


def style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)


def save(fig, name):
    fig.tight_layout(pad=1.4)
    fig.savefig(os.path.join(HERE, "img", name), bbox_inches="tight")
    plt.close(fig)


def load_cells(fname):
    """(batch, features) -> row, from a latency results jsonl."""
    out = {}
    with open(os.path.join(HERE, "latency", "results", fname)) as f:
        for line in f:
            r = json.loads(line)
            out[(r["batch"], r["features"])] = r
    return out


def load_history(fname):
    """Aggregated Locust history: elapsed seconds, achieved rps, p99 (ms)."""
    t0, t, rps, p99 = None, [], [], []
    with open(os.path.join(HERE, "throughput", "results", fname)) as f:
        for row in csv.DictReader(f):
            if row["Name"] != "Aggregated" or row["99%"] in ("", "N/A"):
                continue
            ts = int(row["Timestamp"])
            t0 = ts if t0 is None else t0
            t.append(ts - t0)
            rps.append(float(row["Requests/s"]))
            p99.append(float(row["99%"]))
    return t, rps, p99


feast, hops = load_cells("feast_incluster.jsonl"), load_cells("hops_incluster.jsonl")
BATCH = [1, 10, 25, 50, 100]
FEATS = [50, 100, 150, 200, 250]


def by_batch(cells, pct):
    return [cells[(b, 50)][pct] for b in BATCH]


def by_feats(cells, pct):
    return [cells[(1, n)][pct] for n in FEATS]


# --- Online latency, p50, two panels (batch, feature count). Source jsonl. ---
fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=150)
a.plot(BATCH, by_batch(feast, "p50"), color=FEAST, label="Feast (Redis, same node)", **MARK)
a.plot(BATCH, by_batch(hops, "p50"), color=HOPS, label="Hopsworks (RonDB via RDRS, same node)", **MARK)
# Linear y on purpose: a log y-axis compresses the gap and flatters Feast. Linear
# shows the truth, Feast climbs to 313 ms while RonDB stays flat near the axis.
a.set_xscale("log"); a.set_xticks(BATCH)
a.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}"))
a.set_ylim(bottom=0)
a.set_title("Online latency vs batch size", fontweight="bold", fontsize=12, pad=10, loc="left")
a.set_xlabel("entity rows per request"); a.set_ylabel("p50 latency (ms)")
a.annotate("Feast 21.8x slower\nat batch 100", xy=(1.2, 288), ha="left", va="top", color=FEAST, fontweight="bold", fontsize=11)
style(a); a.legend(frameon=False, fontsize=9.5, loc="upper left")

b.plot(FEATS, by_feats(feast, "p50"), color=FEAST, label="Feast", **MARK)
b.plot(FEATS, by_feats(hops, "p50"), color=HOPS, label="Hopsworks", **MARK)
b.set_title("Online latency vs feature count", fontweight="bold", fontsize=12, pad=10, loc="left")
b.set_xlabel("features requested (single row)"); b.set_ylabel("p50 latency (ms)"); b.set_xticks(FEATS)
style(b); b.legend(frameon=False, fontsize=9.5, loc="upper left")
save(fig, "online_latency.png")

# --- Tail latency: p50 vs p99, the spread that an online SLA is written against. ---
fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=150)
for cells, color, name in ((feast, FEAST, "Feast"), (hops, HOPS, "Hopsworks")):
    p50, p99 = by_batch(cells, "p50"), by_batch(cells, "p99")
    a.fill_between(BATCH, p50, p99, color=color, alpha=0.12, zorder=1)
    a.plot(BATCH, p99, color=color, label=f"{name} p99", **MARK)
    a.plot(BATCH, p50, color=color, lw=1.4, ls="--", alpha=0.7, zorder=2)
a.set_xscale("log"); a.set_xticks(BATCH)
a.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}"))
a.set_ylim(bottom=0)
a.set_title("Tail latency (p50 dashed, p99 solid) vs batch", fontweight="bold", fontsize=12, pad=10, loc="left")
a.set_xlabel("entity rows per request"); a.set_ylabel("latency (ms)")
a.annotate(f"Feast p99 {feast[(100, 50)]['p99']:.0f} ms", xy=(100, feast[(100, 50)]["p99"]),
           xytext=(58, feast[(100, 50)]["p99"]), ha="right", va="center", color=FEAST, fontweight="bold", fontsize=10)
style(a); a.legend(frameon=False, fontsize=9.5, loc="upper left")

for cells, color, name in ((feast, FEAST, "Feast"), (hops, HOPS, "Hopsworks")):
    p50, p99 = by_feats(cells, "p50"), by_feats(cells, "p99")
    b.fill_between(FEATS, p50, p99, color=color, alpha=0.12, zorder=1)
    b.plot(FEATS, p99, color=color, label=f"{name} p99", **MARK)
    b.plot(FEATS, p50, color=color, lw=1.4, ls="--", alpha=0.7, zorder=2)
b.set_ylim(bottom=0)
b.set_title("Tail latency vs feature count (single row)", fontweight="bold", fontsize=12, pad=10, loc="left")
b.set_xlabel("features requested"); b.set_ylabel("latency (ms)"); b.set_xticks(FEATS)
style(b); b.legend(frameon=False, fontsize=9.5, loc="upper left")
save(fig, "tail_latency.png")

# --- Throughput under load: the open-loop ramp. Source Locust history CSVs. ---
ft, frps, fp99 = load_history("feast_history.csv")
ht, hrps, hp99 = load_history("hops_history.csv")
fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=150)
a.plot(ft, frps, color=FEAST, label="Feast (feast serve, 4 workers)", **MARK)
a.plot(ht, hrps, color=HOPS, label="Hopsworks (RDRS twin, 4 workers)", **MARK)
a.set_ylim(bottom=0)
# Instantaneous per-10s achieved rps. The reported sustained figures (456 vs 116)
# are the whole-run Locust averages, diluted by the low early ramp steps.
a.set_title("Achieved throughput under a rising ramp", fontweight="bold", fontsize=12, pad=10, loc="left")
a.set_xlabel("elapsed (s)"); a.set_ylabel("requests / s served (per 10s)")
a.annotate("Hopsworks follows\nthe ramp up", xy=(150, 900), ha="center", va="center", color=HOPS, fontweight="bold", fontsize=10)
a.annotate("Feast flatlines", xy=(150, 130), xytext=(150, 300), ha="center", va="bottom", color=FEAST, fontweight="bold", fontsize=10)
style(a); a.legend(frameon=False, fontsize=9.5, loc="upper left")

b.plot(ft, [v / 1000 for v in fp99], color=FEAST, label="Feast p99", **MARK)
b.plot(ht, [v / 1000 for v in hp99], color=HOPS, label="Hopsworks p99", **MARK)
b.set_ylim(bottom=0)
b.set_title("Tail latency under the same ramp", fontweight="bold", fontsize=12, pad=10, loc="left")
b.set_xlabel("elapsed (s)"); b.set_ylabel("p99 latency (s)")
b.annotate(f"Feast p99 collapses to {max(fp99) / 1000:.0f} s", xy=(60, max(fp99) / 1000 * 0.8),
           ha="left", va="center", color=FEAST, fontweight="bold", fontsize=10)
style(b); b.legend(frameon=False, fontsize=9.5, loc="upper left")
save(fig, "throughput.png")

# --- Offline join-width floor (get_batch_data at 10k vs groups joined). Source
# offline/results/join_width_10k.jsonl. The offline floor is fan-out-bound: each
# joined group adds backend query-construction, not row cost. ---
fig, ax = plt.subplots(figsize=(7.5, 4.4), dpi=150)
groups = [1, 5, 25]
hops = [2.99, 10.01, 52.04]
ax.plot(groups, hops, color=HOPS, label="Hopsworks get_batch_data (DELTA/HQS)", **MARK)
# Feast is only measured at the full 250 features (25 FVs), so it is one point at 25
# groups, not a line: at narrow widths Feast reads less and is faster, unmeasured here.
ax.plot([25], [5.3], color=FEAST, marker="D", ms=8, ls="none", zorder=4, label="Feast get_historical_features (250 features)")
ax.set_xticks(groups); ax.set_ylim(bottom=0)
ax.set_title("Hopsworks offline floor scales with join width (10k rows)", fontweight="bold", fontsize=12, pad=10, loc="left")
ax.set_xlabel("feature groups joined (point-in-time)"); ax.set_ylabel("time to build (seconds)")
ax.annotate("~2s per group added\n(query construction)", xy=(25, 52.04), xytext=(23.5, 52.04), ha="right", va="center", color=HOPS, fontweight="bold", fontsize=9.5)
ax.annotate("Feast at 250 feats: 5.3s\n(narrow widths not measured)", xy=(25, 5.3), xytext=(24, 13), ha="right", va="bottom", color=FEAST, fontsize=9)
ax.annotate("25 groups =\nfeast-benchmarks design", xy=(25, 52.04), xytext=(15, 43), ha="center", va="top", color=MUT, fontsize=9)
style(ax); ax.legend(frameon=False, fontsize=9.5, loc="upper left")
save(fig, "offline_join_width.png")

# --- Offline materialize-once, read-many (10k, 25 groups). Source
# offline/results/methods_10k.jsonl. Hopsworks materializes a versioned training
# dataset once, then reads it in 0.75s (join baked in, width-independent). Feast has
# no materialized offline read: get_historical_features rebuilds the join every read. ---
fig, ax = plt.subplots(figsize=(7.5, 4.4), dpi=150)
reads = list(range(0, 26))
hops_mat, hops_read, feast_read = 60.62, 0.75, 5.3
hops_cum = [hops_mat + hops_read * n for n in reads]
feast_cum = [feast_read * n for n in reads]
ax.plot(reads, hops_cum, color=HOPS, label="Hopsworks: materialize once (61s) + 0.75s/read", **MARK)
ax.plot(reads, feast_cum, color=FEAST, label="Feast: rebuild join every read (5.3s/read)", **MARK)
cross = hops_mat / (feast_read - hops_read)
ax.axvline(cross, color=MUT, lw=1, ls=":", zorder=1)
ax.set_ylim(bottom=0); ax.set_xlim(left=0)
ax.set_title("Offline read-many: materialized dataset vs rebuilding (10k, 25 groups)", fontweight="bold", fontsize=12, pad=10, loc="left")
ax.set_xlabel("number of reads of the same training set"); ax.set_ylabel("cumulative time (seconds)")
ax.annotate(f"crossover ~{cross:.0f} reads", xy=(cross, feast_read * cross), xytext=(cross + 0.6, feast_read * cross - 22), ha="left", color=MUT, fontsize=9.5)
ax.annotate("0.75s/read,\nwidth-independent", xy=(25, hops_cum[-1]), xytext=(24.5, hops_cum[-1] + 12), ha="right", va="bottom", color=HOPS, fontweight="bold", fontsize=9.5)
style(ax); ax.legend(frameon=False, fontsize=9, loc="upper left")
save(fig, "offline_materialized.png")

# --- Offline crossover (on-the-fly build, seconds vs rows, log-log). Source
# offline/RESULTS.md. Both stores rebuild the join on the fly here. ---
# Hopsworks 10k is its distributed-query overhead floor (~45s), not a clean win.
fig, ax = plt.subplots(figsize=(7.5, 4.4), dpi=150)
rows = [1e4, 1e5, 1e6]
ax.plot(rows, [5.3, 35.6, 344], color=FEAST, label="Feast get_historical_features (pandas in-memory)", **MARK)
ax.plot(rows, [45, 53.8, 109], color=HOPS, label="Hopsworks on-the-fly (rebuild join per read)", **MARK)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xticks(rows)
ax.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: {1e4: "10k", 1e5: "100k", 1e6: "1M"}.get(v, f"{v:g}")))
ax.get_yaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}"))
ax.axvspan(1e5, 1e6, color="#f4f4f0", zorder=0)
ax.set_title("Offline on-the-fly build vs rows (25 groups)", fontweight="bold", fontsize=12, pad=10, loc="left")
ax.set_xlabel("training set size (rows, log)"); ax.set_ylabel("time to build (seconds, log)")
ax.annotate("crossover", xy=(3.2e5, 70), color=MUT, fontsize=9.5, ha="center")
ax.annotate("Feast OOM-crashes at 10M\n(no distributed fallback)", xy=(1e6, 344),
            xytext=(1.05e6, 344), ha="left", va="center", color=FEAST, fontsize=9.5)
style(ax); ax.legend(frameon=False, fontsize=9.5, loc="upper left")
save(fig, "offline_scale.png")

print("wrote img/{online_latency,tail_latency,throughput,offline_join_width,offline_materialized,offline_scale}.png")
