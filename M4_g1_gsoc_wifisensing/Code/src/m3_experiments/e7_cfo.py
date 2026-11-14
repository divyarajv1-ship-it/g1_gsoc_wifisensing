#!/usr/bin/env python3
"""E7: PDR vs carrier frequency offset (CFO), in units of the subcarrier spacing,
flat and indoor channels, SNR 25 dB, rolloff 0 vs 4. 300 packets x 5 seeds."""
import csv, sys
import numpy as np
import m3_harness as h

def trial(profile, cfo_sc, rolloff, seed, n=300, plen=50, snr_db=25):
    rng = np.random.default_rng(seed)
    pk = h.make_packets(n + h.N_FLUSH, plen, rng)
    iq, _, _ = h.transmit(pk, plen, rolloff=rolloff)
    nt, dec = h.PROFILES[profile]
    taps = h.exp_pdp_taps(nt, dec, np.random.default_rng(1000 + seed))
    x = np.concatenate([np.zeros(100, np.complex64), iq])
    y = h.apply_channel(x, taps=taps, cfo=cfo_sc / h.FFT_LEN, snr_db=snr_db,
                        rng=np.random.default_rng(2000 + seed), p_sig=P_SIG)
    r = h.receive(y, instrument=False)
    s = h.score(pk[:n], r["rx_packets"])
    return {k: s[k] for k in ("n_tx", "n_rx_valid", "lost", "pdr", "bit_errors")}

P_SIG = h.tx_power()
if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "../../../Results/m3/e7_cfo.csv"
    rows = []
    for profile in ["flat", "indoor"]:
        for cfo in [0.0, 0.1, 0.25, 0.5, 1.0, 1.5, 2.5, 3.5]:
            for ro in [0, 4]:
                for seed in [1, 2, 3, 4, 5]:
                    r = h.run_guarded(trial, dict(profile=profile, cfo_sc=cfo, rolloff=ro, seed=seed), 60)
                    r.update(profile=profile, cfo_sc=cfo, rolloff=ro, seed=seed)
                    rows.append(r)
                    print(profile, cfo, ro, seed, r["status"], r.get("pdr"), flush=True)
    f = ["profile", "cfo_sc", "rolloff", "seed", "status", "n_tx", "n_rx_valid", "lost", "pdr", "bit_errors"]
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=f, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    print("wrote", out)
