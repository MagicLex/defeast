"""Render the benchmark charts embedded in README.md from the measured numbers.
Numbers come from RESULTS.md (online SDK) and RESULTS_BATCH.md (offline). Run:
    python plot.py   ->   img/online_latency.png, img/offline_scale.png
"""

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
os.makedirs("img", exist_ok=True)


def style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)


# Online latency, two panels (p50, ms). Source: RESULTS.md.
fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=150)
bx = [1, 10, 25, 50, 100]
a.plot(bx, [5.64, 28.97, 64.45, 126.70, 253.05], color=FEAST, label="Feast (Redis, localhost)", **MARK)
a.plot(bx, [2.68, 3.61, 4.68, 6.17, 9.08], color=HOPS, label="Hopsworks (RonDB, over network)", **MARK)
# Linear y on purpose: a log y-axis compresses the gap and flatters Feast. Linear
# shows the truth, Feast climbs to 253 ms while RonDB stays flat near the axis.
a.set_xscale("log"); a.set_xticks(bx)
a.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}"))
a.set_ylim(bottom=0)
a.set_title("Online latency vs batch size", fontweight="bold", fontsize=12, pad=10, loc="left")
a.set_xlabel("entity rows per request"); a.set_ylabel("p50 latency (ms)")
a.annotate("Feast 27.9x slower\nat batch 100", xy=(1.2, 232), ha="left", va="top", color=FEAST, fontweight="bold", fontsize=11)
style(a); a.legend(frameon=False, fontsize=9.5, loc="upper left")

fx = [50, 100, 150, 200, 250]
b.plot(fx, [5.64, 10.72, 16.23, 22.33, 27.47], color=FEAST, label="Feast", **MARK)
b.plot(fx, [2.68, 3.23, 3.75, 4.39, 4.95], color=HOPS, label="Hopsworks", **MARK)
b.set_title("Online latency vs feature count", fontweight="bold", fontsize=12, pad=10, loc="left")
b.set_xlabel("features requested (single row)"); b.set_ylabel("p50 latency (ms)"); b.set_xticks(fx)
style(b); b.legend(frameon=False, fontsize=9.5, loc="upper left")
fig.tight_layout(pad=1.4)
fig.savefig("img/online_latency.png", bbox_inches="tight")
plt.close(fig)

# Offline crossover (seconds vs rows, log-log). Source: RESULTS_BATCH.md.
# Hopsworks 10k is its distributed-query overhead floor (~45s), not a clean win.
fig, ax = plt.subplots(figsize=(7.5, 4.4), dpi=150)
rows = [1e4, 1e5, 1e6]
ax.plot(rows, [5.3, 35.6, 344], color=FEAST, label="Feast (file, pandas in-memory)", **MARK)
ax.plot(rows, [45, 53.8, 109], color=HOPS, label="Hopsworks (Hudi, Arrow Flight)", **MARK)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xticks(rows)
ax.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: {1e4: "10k", 1e5: "100k", 1e6: "1M"}.get(v, f"{v:g}")))
ax.get_yaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}"))
ax.axvspan(1e5, 1e6, color="#f4f4f0", zorder=0)
ax.set_title("Offline training data: the crossover", fontweight="bold", fontsize=12, pad=10, loc="left")
ax.set_xlabel("training set size (rows, log)"); ax.set_ylabel("time to build (seconds, log)")
ax.annotate("crossover", xy=(3.2e5, 70), color=MUT, fontsize=9.5, ha="center")
ax.annotate("Feast OOM-crashes at 10M\n(no distributed fallback)", xy=(1e6, 344),
            xytext=(1.05e6, 344), ha="left", va="center", color=FEAST, fontsize=9.5)
style(ax); ax.legend(frameon=False, fontsize=9.5, loc="upper left")
fig.tight_layout(pad=1.2)
fig.savefig("img/offline_scale.png", bbox_inches="tight")
plt.close(fig)
print("wrote img/online_latency.png, img/offline_scale.png")
