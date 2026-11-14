#!/usr/bin/env python3
"""E6: PDR of stock (rolloff 0) vs fixed (rolloff 4) OFDM TX over static multipath
channels (flat / mild / indoor / harsh exponential power-delay profiles, all
inside the 16-sample CP) and AWGN at 15-30 dB SNR. 300 packets x 5 seeds per point."""
import csv, sys
import numpy as np
import m3_harness as h

def trial(profile, snr_db, rolloff, seed, n=300, plen=50):
    rng = np.random.default_rng(seed)
    pk = h.make_packets(n + h.N_FLUSH, plen, rng)
    iq, st, _ = h.transmit(pk, plen, rolloff=rolloff)
    nt, dec = h.PROFILES[profile]
    taps = h.exp_pdp_taps(nt, dec, np.random.default_rng(1000 + seed))
    x = np.concatenate([np.zeros(100, np.complex64), iq])
    y = h.apply_channel(x, taps=taps, snr_db=snr_db, rng=np.random.default_rng(2000 + seed),
                        p_sig=P_SIG)
    r = h.receive(y, instrument=False)
    s = h.score(pk[:n], r["rx_packets"])
    return {k: s[k] for k in ("n_tx", "n_rx_valid", "lost", "pdr", "bit_errors")}

P_SIG = h.tx_power()
if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "../../../Results/m3/e6_multipath_snr.csv"
    rows = []
    for profile in ["flat", "mild", "indoor", "harsh"]:
        for snr in [15, 20, 25, 30, None]:
            for ro in [0, 4]:
                for seed in [1, 2, 3, 4, 5]:
                    r = h.run_guarded(trial, dict(profile=profile, snr_db=snr, rolloff=ro, seed=seed), 60)
                    r.update(profile=profile, snr_db="inf" if snr is None else snr, rolloff=ro, seed=seed)
                    rows.append(r)
                    print(profile, snr, ro, seed, r["status"], r.get("pdr"), flush=True)
    f = ["profile", "snr_db", "rolloff", "seed", "status", "n_tx", "n_rx_valid", "lost", "pdr", "bit_errors"]
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=f, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    print("wrote", out)
