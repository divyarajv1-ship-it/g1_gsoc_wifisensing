#!/usr/bin/env python3
"""E8: sample-level explanation of #6891. Logs every Schmidl & Cox trigger inside
ofdm_rx (sync-detect.dat) on an ideal channel and relates it to the true burst
starts and to the lost packets.

For each trigger we record: offset from its burst start, and spacing to the
previous trigger. Model tested (m3_harness.hpd_replay): a packet is lost exactly when its trigger
arrives earlier than (frame length - 1) samples after the last *used* trigger,
because Header/Payload Demux is still consuming the previous frame."""
import csv, json, sys
import numpy as np
import m3_harness as h

PRE = 100

def trial(rolloff, gap, plen, seed, n=500):
    rng = np.random.default_rng(seed)
    pk = h.make_packets(n + h.N_FLUSH, plen, rng)
    iq, st, ln = h.transmit(pk, plen, rolloff=rolloff, gap=gap)
    x = np.concatenate([np.zeros(PRE, np.complex64), iq])
    r = h.receive(x, instrument=True)
    s = h.score(pk[:n], r["rx_packets"])
    starts = np.array(st) + PRE
    trig = np.array(r["triggers"])
    # assign each trigger to the burst it falls in
    idx = np.searchsorted(starts, trig, side="right") - 1
    off = trig - starts[idx]
    spacing = np.diff(trig)
    sym_frame = (int(ln[0]) // h.SYM_LEN) * h.SYM_LEN
    early = h.hpd_replay(trig, idx, sym_frame, n, slack=1)
    lost = s["lost_seq"]
    return {"n_tx": n, "lost": s["lost"], "pdr": s["pdr"], "n_trig": int(len(trig)),
            "burst_len": int(ln[0]), "frame_samples": sym_frame,
            "off_min": int(off.min()), "off_max": int(off.max()),
            "off_values": sorted(set(off.tolist())),
            "spacing_min": int(spacing.min()), "spacing_max": int(spacing.max()),
            "n_short_spacing": len(early),
            "short_spacing_bursts_lt_n": early,
            "lost_seq": lost}

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "../../../Results/m3/e8_trigger_timing.csv"
    rows = []
    cfgs = [(0, 0, 50), (1, 0, 50), (2, 0, 50), (4, 0, 50), (0, 1, 50),
            (0, 0, 20), (0, 0, 100), (0, 0, 200)]
    for ro, gap, plen in cfgs:
        for seed in [1, 2, 3, 4, 5]:
            r = h.run_guarded(trial, dict(rolloff=ro, gap=gap, plen=plen, seed=seed), 90)
            match = (r.get("short_spacing_bursts_lt_n") == r.get("lost_seq"))
            r.update(rolloff=ro, gap=gap, packet_len=plen, seed=seed, lost_equals_short_spacing=match)
            rows.append(r)
            print(ro, gap, plen, seed, r["status"], "lost", r.get("lost"), "short", r.get("n_short_spacing"),
                  "match", match, "off", r.get("off_values"), "sp", r.get("spacing_min"), r.get("spacing_max"),
                  "frame", r.get("frame_samples"), "burst", r.get("burst_len"), flush=True)
    f = ["rolloff", "gap", "packet_len", "seed", "status", "n_tx", "lost", "pdr", "n_trig", "burst_len",
         "frame_samples", "off_min", "off_max", "off_values", "spacing_min", "spacing_max",
         "n_short_spacing", "lost_equals_short_spacing"]
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=f, extrasaction="ignore"); w.writeheader()
        for r in rows:
            r = dict(r); r["off_values"] = json.dumps(r.get("off_values")); w.writerow(r)
    print("wrote", out)
