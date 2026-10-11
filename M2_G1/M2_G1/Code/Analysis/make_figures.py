#!/usr/bin/env python3
"""Build the M2 figures from Results/*.csv. Run from this folder."""
import collections
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Results")
FIG = os.path.join(RES, "figures")
os.makedirs(FIG, exist_ok=True)
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False,
    "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF,
    "savefig.facecolor": SURF, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True,
})


def load(name):
    return list(csv.DictReader(open(os.path.join(RES, name))))


# ---------- Figure 1: PDR per configuration, streaming vs offline ----------
rows = load("packet_loss_sweep.csv")
cfgs = [("0", "0", "rolloff 0\n(default)"), ("1", "0", "rolloff 1"),
        ("2", "0", "rolloff 2"), ("4", "0", "rolloff 4"),
        ("0", "1", "1-sample\ngap"), ("0", "8", "8-sample\ngap")]
fig, ax = plt.subplots(figsize=(7.2, 3.4))
w = 0.38
summary = []
for i, mode in enumerate(["streaming", "offline"]):
    means, lo, hi = [], [], []
    for ro, gap, _ in cfgs:
        v = [100 * float(r["pdr"]) for r in rows if r["mode"] == mode and r["packet_len"] == "50"
             and r["rolloff"] == ro and r["gap"] == gap and float(r["noise_voltage"]) == 0]
        means.append(np.mean(v)); lo.append(np.mean(v) - min(v)); hi.append(max(v) - np.mean(v))
        summary.append((mode, ro, gap, np.mean(v), min(v), max(v), len(v)))
    x = np.arange(len(cfgs)) + (i - 0.5) * (w + 0.02)
    ax.bar(x, means, w, color=[BLUE, AQUA][i], label=f"{mode} (TX→RX in {'one flowgraph' if mode == 'streaming' else 'two runs'})",
           yerr=[lo, hi], error_kw=dict(ecolor=INK2, lw=1, capsize=2))
ax.set_xticks(np.arange(len(cfgs)), [c[2] for c in cfgs])
ax.set_ylim(90, 100.8)
ax.set_ylabel("Packet delivery ratio (%)")
ax.set_title("Ideal channel, 50-byte packets, 500 packets × 5 seeds (bars: mean, whiskers: min–max)",
             fontsize=9, color=INK2, loc="left")
ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig1_pdr_by_config.png"), dpi=200); plt.close(fig)

# ---------- Figure 2: packet length dependence ----------
fig, ax = plt.subplots(figsize=(5, 3))
lens = ["20", "50", "100", "200"]
m = []
for L in lens:
    v = [100 * float(r["pdr"]) for r in rows if r["mode"] == "streaming" and r["packet_len"] == L
         and r["rolloff"] == "0" and r["gap"] == "0" and float(r["noise_voltage"]) == 0]
    m.append(np.mean(v))
ax.bar(lens, m, 0.6, color=ORANGE)
for i, v in enumerate(m):
    ax.text(i, v + 0.15, f"{v:.1f}%", ha="center", fontsize=8, color=INK)
ax.set_ylim(90, 101); ax.set_xlabel("Packet length (bytes)"); ax.set_ylabel("PDR (%)")
ax.set_title("rolloff 0, ideal channel", fontsize=9, color=INK2, loc="left")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig2_pdr_vs_packet_len.png"), dpi=200); plt.close(fig)

# ---------- Figure 3: PDR vs SNR ----------
srows = load("snr_sweep.csv")
fig, ax = plt.subplots(figsize=(6.4, 3.6))
snr_table = []
for ro, col, lab in [("0", ORANGE, "rolloff 0 (default)"), ("4", BLUE, "rolloff 4 (fix)")]:
    by = collections.defaultdict(list)
    for r in srows:
        if r["rolloff"] == ro and r["status"] == "OK":
            by[int(r["snr_db"])].append(100 * float(r["pdr"]))
    xs = sorted(by)
    mean = [np.mean(by[s]) for s in xs]
    ax.fill_between(xs, [min(by[s]) for s in xs], [max(by[s]) for s in xs], color=col, alpha=0.15, lw=0)
    ax.plot(xs, mean, color=col, lw=2, marker="o", ms=4, label=lab)
    ax.annotate(lab, (xs[-1], mean[-1]), xytext=(4, -10 if ro == "0" else 4),
                textcoords="offset points", fontsize=8, color=INK)
    snr_table.append((ro, {s: (np.mean(by[s]), min(by[s]), max(by[s])) for s in xs}))
ax.set_xlabel("SNR (dB)  [mean TX sample power / noise power]")
ax.set_ylabel("Packet delivery ratio (%)")
ax.set_xlim(5.5, 34)
ax.legend(frameon=False, fontsize=8, loc="center right")
ax.set_title("AWGN channel, 300 packets × 5 seeds (line: mean, band: min–max)", fontsize=9, color=INK2, loc="left")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig3_pdr_vs_snr.png"), dpi=200); plt.close(fig)

# inset-style zoom of the high-SNR floor
fig, ax = plt.subplots(figsize=(6.4, 3))
for ro, col, lab in [("0", ORANGE, "rolloff 0 (default)"), ("4", BLUE, "rolloff 4 (fix)")]:
    d = dict(snr_table)[ro]
    xs = [s for s in sorted(d) if s >= 14]
    ax.plot(xs, [d[s][0] for s in xs], color=col, lw=2, marker="o", ms=4, label=lab)
ax.set_ylim(90, 100.5); ax.set_xlabel("SNR (dB)"); ax.set_ylabel("PDR (%)")
ax.legend(frameon=False, fontsize=8, loc="lower left")
ax.set_title("Zoom on high SNR: the #6891 loss floor does not disappear with more SNR", fontsize=9, color=INK2, loc="left")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig4_high_snr_floor.png"), dpi=200); plt.close(fig)

with open(os.path.join(RES, "summary.md"), "w") as f:
    f.write("# M2 results summary (auto-generated by Code/analysis/make_figures.py)\n\n")
    f.write("## E1 ideal channel, 50-byte packets, 500 packets x 5 seeds\n\n")
    f.write("| mode | rolloff | gap | mean PDR % | min | max | runs |\n|---|---|---|---|---|---|---|\n")
    for s in summary:
        f.write(f"| {s[0]} | {s[1]} | {s[2]} | {s[3]:.2f} | {s[4]:.2f} | {s[5]:.2f} | {s[6]} |\n")
    f.write("\n## E3 PDR vs SNR (300 packets x 5 seeds)\n\n| SNR dB | rolloff 0 mean PDR % | rolloff 4 mean PDR % |\n|---|---|---|\n")
    d0, d4 = dict(snr_table)["0"], dict(snr_table)["4"]
    for s in sorted(d0):
        f.write(f"| {s} | {d0[s][0]:.1f} | {d4[s][0]:.1f} |\n")
print(open(os.path.join(RES, "summary.md")).read())
