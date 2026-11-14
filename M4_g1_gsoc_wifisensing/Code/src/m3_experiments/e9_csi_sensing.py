#!/usr/bin/env python3
"""E9: Wi-Fi sensing bridge. Extract per-packet CSI from GNU Radio's own OFDM
receiver (ofdm_chanest_vcvc output, via ofdm_rx debug_log) under a
time-varying indoor channel with a moving reflector ("person"), then:

 (a) CSI accuracy: NMSE of the estimated |H(f)| vs the true |H(f)| on the 52
     occupied carriers, SNR 15-30 dB, rolloff 0 vs 4;
 (b) CSI continuity: how many CSI samples are missing and how long the gaps are;
 (c) a toy sensing task: estimate the reflector's motion frequency (0.5 Hz)
     from the CSI amplitude time series, with timestamps either recovered from
     the packet sequence numbers ("seq") or assumed from packet order ("naive",
     as with tools that do not report drops).

Packet rate is assumed to be 50 packets/s (a common CSI sampling rate)."""
import csv, json, sys
import numpy as np
import m3_harness as h

PRE = 100
PKT_RATE = 50.0
F_MOTION = 0.5
OCC_IDX = np.array(h.OCCUPIED) + h.FFT_LEN // 2   # fft-shifted vector index


def channel_sequence(n_bursts, seed):
    """Static indoor taps + one reflector path (delay 4 samples) whose gain
    varies with time like a person moving back and forth."""
    rng = np.random.default_rng(1000 + seed)
    base = h.exp_pdp_taps(*h.PROFILES["indoor"], rng)
    t = np.arange(n_bursts) / PKT_RATE
    taps = []
    for ti in t:
        hh = base.copy()
        g = 0.45 * (1 + 0.8 * np.sin(2 * np.pi * F_MOTION * ti))
        phase = 2 * np.pi * 0.3 * np.sin(2 * np.pi * F_MOTION * ti)   # path-length change
        hh[4] += g * np.exp(1j * phase)
        taps.append(hh / np.sqrt(np.sum(np.abs(base) ** 2) + 0.45 ** 2))
    return taps


def true_csi(taps):
    H = np.fft.fftshift(np.fft.fft(taps, h.FFT_LEN))
    return H[OCC_IDX]


def est_freq(times, values):
    """Peak of the (zero-padded) periodogram of the mean-removed series,
    after linear interpolation onto a uniform 50 Hz grid."""
    grid = np.arange(times[0], times[-1], 1 / PKT_RATE)
    v = np.interp(grid, times, values)
    v = v - v.mean()
    nfft = 1 << 16
    S = np.abs(np.fft.rfft(v * np.hanning(len(v)), nfft))
    f = np.fft.rfftfreq(nfft, 1 / PKT_RATE)
    band = (f > 0.1) & (f < 5)
    return float(f[band][np.argmax(S[band])])


def trial(rolloff, snr_db, seed, n=500, plen=50):
    rng = np.random.default_rng(seed)
    pk = h.make_packets(n + h.N_FLUSH, plen, rng)
    iq, st, ln = h.transmit(pk, plen, rolloff=rolloff)
    taps = channel_sequence(len(st), seed)
    x = np.concatenate([np.zeros(PRE, np.complex64), iq])
    starts = np.array(st) + PRE
    y = h.apply_channel(x, snr_db=snr_db, rng=np.random.default_rng(2000 + seed), p_sig=P_SIG,
                        burst_starts=[0] + list(starts[1:]), burst_taps=taps)
    r = h.receive(y, instrument=True)
    s = h.score(pk[:n], r["rx_packets"])
    csi = r["csi"]
    order = s["rx_order"]
    # map CSI rows to packets
    if len(csi) == len(order):
        seqs = order
    else:
        trig = np.array(r["triggers"])
        idx = np.searchsorted(starts, trig, side="right") - 1
        F = (int(ln[0]) // h.SYM_LEN) * h.SYM_LEN
        seqs = None
        for slack in (1, 0, 2, 3):   # replay HPD (E8 rule); noise can shift a marginal trigger
            acc, last = [], None
            for t, b in zip(trig, idx):
                if last is None or t >= last + F - slack:
                    acc.append(int(b)); last = t
            if len(acc) == len(csi):
                seqs = acc
                break
    out = {"n_tx": n, "lost": s["lost"], "pdr": s["pdr"], "n_csi": int(len(csi)), "mapped": seqs is not None}
    if seqs is None:
        return out
    keep = [(i, q) for i, q in enumerate(seqs) if q < n]
    est = np.array([np.abs(csi[i][OCC_IDX]) for i, _ in keep])
    tru = np.array([np.abs(true_csi(taps[q])) for _, q in keep])
    scale = np.sum(est * tru) / np.sum(est * est)        # one global real scale factor
    nmse = np.sum((scale * est - tru) ** 2) / np.sum(tru ** 2)
    out["nmse_db"] = float(10 * np.log10(nmse))
    rx_seq = np.array([q for _, q in keep])
    gaps = np.diff(np.concatenate([[-1], np.sort(rx_seq), [n]])) - 1
    out["max_gap"] = int(gaps.max())
    out["n_gaps"] = int(np.sum(gaps > 0))
    amp = (scale * est).mean(axis=1)
    t_seq = rx_seq / PKT_RATE
    t_naive = np.arange(len(rx_seq)) / PKT_RATE
    out["f_seq"] = est_freq(t_seq, amp)
    out["f_naive"] = est_freq(t_naive, amp)
    out["f_true_amp"] = est_freq(np.arange(n) / PKT_RATE,
                                 np.array([np.abs(true_csi(taps[q])).mean() for q in range(n)]))
    return out


P_SIG = h.tx_power()
if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "../../../Results/m3/e9_csi_sensing.csv"
    rows = []
    for snr in [15, 20, 25, 30, None]:
        for ro in [0, 4]:
            for seed in [1, 2, 3, 4, 5]:
                r = h.run_guarded(trial, dict(rolloff=ro, snr_db=snr, seed=seed), 120)
                r.update(rolloff=ro, snr_db="inf" if snr is None else snr, seed=seed)
                rows.append(r)
                print(snr, ro, seed, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()
                                      if k not in ("rolloff", "seed", "snr_db")}, flush=True)
    f = ["snr_db", "rolloff", "seed", "status", "n_tx", "lost", "pdr", "n_csi", "mapped", "nmse_db",
         "n_gaps", "max_gap", "f_true_amp", "f_seq", "f_naive"]
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=f, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    print("wrote", out)
