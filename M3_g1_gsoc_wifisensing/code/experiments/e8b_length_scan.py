#!/usr/bin/env python3
"""E8b: tests the M3 hypothesis for the unexplained M2 observation (no loss at
100-byte packets): loss happens only when the last OFDM payload symbol is
completely filled with data. Payload bits = (packet_len + 4 CRC bytes) * 8,
48 data carriers per symbol (BPSK) -> last symbol full iff bits % 48 == 0.
Also replays the Header/Payload Demux acceptance rule on the logged triggers:
a trigger is accepted only if it comes >= F-1 samples after the last accepted one
(see m3_harness.hpd_replay). The 'last symbol full' hypothesis is tested via last_symbol_full."""
import csv, sys
import numpy as np
import m3_harness as h

PRE = 100

def trial(plen, seed, rolloff=0, n=300):
    rng = np.random.default_rng(seed)
    pk = h.make_packets(n + h.N_FLUSH, plen, rng)
    iq, st, ln = h.transmit(pk, plen, rolloff=rolloff)
    r = h.receive(np.concatenate([np.zeros(PRE, np.complex64), iq]), instrument=True)
    s = h.score(pk[:n], r["rx_packets"])
    starts = np.array(st) + PRE
    trig = np.array(r["triggers"])
    idx = np.searchsorted(starts, trig, side="right") - 1
    off = trig - starts[idx]
    F = (int(ln[0]) // h.SYM_LEN) * h.SYM_LEN
    pred_lost = h.hpd_replay(trig, idx, F, n, slack=1)
    return {"lost": s["lost"], "pdr": s["pdr"], "jitter": int(off.max() - off.min()),
            "pred_lost": len(pred_lost), "pred_match": pred_lost == s["lost_seq"]}

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "../../Results/e8b_length_scan.csv"
    rows = []
    for plen in [20, 30, 40, 44, 45, 46, 50, 56, 60, 68, 70, 80, 86, 92, 100, 104, 110, 128, 140, 200]:
        bits = (plen + 4) * 8
        full = bits % 48 == 0
        for seed in [1, 2, 3]:
            r = h.run_guarded(trial, dict(plen=plen, seed=seed), 90)
            r.update(packet_len=plen, payload_bits=bits, n_symbols=-(-bits // 48),
                     last_symbol_full=full, seed=seed)
            rows.append(r)
            print(plen, bits, "full" if full else "part", seed, r.get("status"), "lost", r.get("lost"),
                  "jitter", r.get("jitter"), "pred", r.get("pred_lost"), r.get("pred_match"), flush=True)
    f = ["packet_len", "payload_bits", "n_symbols", "last_symbol_full", "seed", "status", "lost", "pdr",
         "jitter", "pred_lost", "pred_match"]
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=f, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    print("wrote", out)
