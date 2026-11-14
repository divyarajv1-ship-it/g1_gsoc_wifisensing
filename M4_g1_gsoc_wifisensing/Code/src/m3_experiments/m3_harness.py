#!/usr/bin/env python3
"""
M3 measurement harness for the GNU Radio OFDM TX/RX chain (G1, #6891 / #7997).

It extends the M2 harness (M2_g1_gsoc_wifisensing/Code/experiments/ofdm_packet_loss.py)
with three things M3 needs:

  1. multipath + carrier-frequency-offset (CFO) channels,
  2. direct logging of the Schmidl & Cox trigger positions inside ofdm_rx,
  3. per-packet channel estimates (CSI) taken from ofdm_chanest_vcvc.

Signal chain (offline mode, as in M2: M2 showed streaming and offline lose the
same packets, so offline is used where we need sample-exact bookkeeping):

  packets (seq no. + random) -> ofdm_tx(rolloff) -> [burst gap] -> stored IQ
  -> channel (numpy: per-burst FIR taps, CFO, AWGN)  -> ofdm_rx(debug_log=True)
  -> bytes  + sync-detect.dat (trigger stream) + channel-estimate.dat (CSI)

Every trial runs in a child process with a timeout so a frozen flowgraph is
recorded as HANG instead of blocking the sweep.
"""

import contextlib
import multiprocessing as mp
import os
import tempfile
import time

import numpy as np
import pmt
from gnuradio import blocks, digital, gr
from gnuradio.digital.ofdm_txrx import ofdm_rx, ofdm_tx

LEN_KEY = "packet_len"
FRAME_KEY = "frame_len"
RX_KEY = "rx_len"          # different from the TX key, see M2 E5 (tag leak freeze)
N_FLUSH = 3
FFT_LEN = 64
CP_LEN = 16
SYM_LEN = FFT_LEN + CP_LEN
# default ofdm_tx occupied carriers (48 data + 4 pilots), FFT-shifted indexing
OCCUPIED = sorted(list(range(-26, -21)) + list(range(-20, -7)) + list(range(-6, 0))
                  + list(range(1, 7)) + list(range(8, 21)) + list(range(22, 27))
                  + [-21, -7, 7, 21])


# ----------------------------------------------------------------- packets / TX
def make_packets(n_packets, packet_len, rng):
    packets = []
    for seq in range(n_packets):
        payload = rng.integers(0, 256, packet_len - 2, dtype=np.uint8)
        header = np.array([(seq >> 8) & 0xFF, seq & 0xFF], dtype=np.uint8)
        packets.append(np.concatenate([header, payload]))
    return packets


def transmit(packets, packet_len, rolloff=0, gap=0, big_buffers=False):
    """Run ofdm_tx alone. Returns (iq samples, list of burst start offsets, list of burst lengths)."""
    tb = gr.top_block()
    data = np.concatenate(packets).tolist()
    src = blocks.vector_source_b(data, False, 1, [])
    s2ts = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, packet_len, LEN_KEY)
    tx = ofdm_tx(packet_length_tag_key=LEN_KEY, rolloff=rolloff, scramble_bits=True)
    if big_buffers:
        for b in (s2ts, tx):
            b.set_min_output_buffer(1 << 16)
    sink = blocks.vector_sink_c()
    tb.connect(src, s2ts, tx)
    last = tx
    if gap:
        shaper = digital.burst_shaper_cc([], gap, 0, False, LEN_KEY)
        tb.connect(last, shaper)
        last = shaper
    tb.connect(last, sink)
    tb.run()
    iq = np.array(sink.data(), dtype=np.complex64)
    tags = sorted((t.offset, int(pmt.to_long(t.value))) for t in sink.tags()
                  if pmt.symbol_to_string(t.key) == LEN_KEY)
    starts = [o for o, _ in tags]
    lens = [n for _, n in tags]
    return iq, starts, lens


# ----------------------------------------------------------------- channel
def exp_pdp_taps(n_taps, decay_samples, rng):
    """Static random multipath taps with an exponential power-delay profile,
    normalised to unit energy. decay_samples = 0 -> single tap (flat)."""
    if n_taps <= 1:
        return np.array([1.0 + 0j])
    k = np.arange(n_taps)
    p = np.exp(-k / decay_samples)
    p /= p.sum()
    h = (rng.standard_normal(n_taps) + 1j * rng.standard_normal(n_taps)) / np.sqrt(2)
    h *= np.sqrt(p)
    h[0] = np.sqrt(p[0]) * np.exp(1j * rng.uniform(0, 2 * np.pi))  # strong first path
    return h / np.sqrt(np.sum(np.abs(h) ** 2))


PROFILES = {
    # name: (n_taps, decay in samples). 1 sample = 50 ns at 20 MHz; CP = 16 samples = 800 ns
    "flat": (1, 0),
    "mild": (3, 0.7),        # rms delay ~ 35 ns  (small room, LOS)
    "indoor": (8, 2.0),      # rms delay ~ 100 ns (office, IEEE 802.11 TGn model B/C range)
    "harsh": (14, 4.0),      # rms delay ~ 200 ns (large hall), still inside the CP
}


def apply_channel(iq, taps=None, cfo=0.0, snr_db=None, rng=None, p_sig=None,
                  burst_starts=None, burst_taps=None):
    """FIR multipath (static, or one tap vector per burst), CFO in cycles/sample, AWGN.
    SNR = mean TX sample power / noise power, as in M2."""
    x = iq.astype(np.complex128)
    if burst_taps is not None:
        y = np.zeros(len(x) + 64, dtype=np.complex128)
        bounds = list(burst_starts) + [len(x)]
        for i, h in enumerate(burst_taps):
            seg = x[bounds[i]:bounds[i + 1]]
            out = np.convolve(seg, h)
            y[bounds[i]:bounds[i] + len(out)] += out
        x = y[:len(x)]
    elif taps is not None and len(taps) > 1:
        x = np.convolve(x, taps)[:len(x)]
    if cfo:
        x = x * np.exp(2j * np.pi * cfo * np.arange(len(x)))
    if snr_db is not None:
        if p_sig is None:
            p_sig = np.mean(np.abs(iq) ** 2)
        nv = np.sqrt(p_sig / 10 ** (snr_db / 10))
        x = x + nv * (rng.standard_normal(len(x)) + 1j * rng.standard_normal(len(x))) / np.sqrt(2)
    return x.astype(np.complex64)


# ----------------------------------------------------------------- RX
@contextlib.contextmanager
def _quiet_cwd(path):
    """ofdm_rx(debug_log=True) writes .dat files to the cwd and prints tag_debug
    output; run it in a temp dir with stdout silenced."""
    old = os.getcwd()
    os.chdir(path)
    devnull = os.open(os.devnull, os.O_WRONLY)
    saved = os.dup(1)
    os.dup2(devnull, 1)
    try:
        yield
    finally:
        os.dup2(saved, 1)
        os.close(devnull)
        os.chdir(old)


def receive(samples, instrument=True, big_buffers=False):
    """Run ofdm_rx on stored samples. Returns dict with rx packets, trigger
    positions and per-frame channel estimates (one 64-vector per detected frame)."""
    samples = list(samples) + [0j] * 2000
    with tempfile.TemporaryDirectory() as d:
        ctx = _quiet_cwd(d) if instrument else contextlib.nullcontext()
        with ctx:
            tb = gr.top_block()
            src = blocks.vector_source_c(samples, False)
            rx = ofdm_rx(frame_length_tag_key=FRAME_KEY, packet_length_tag_key=RX_KEY,
                         scramble_bits=True, debug_log=instrument)
            if big_buffers:
                rx.set_min_output_buffer(1 << 16)
            sink = blocks.vector_sink_b()
            tb.connect(src, rx, sink)
            t0 = time.time()
            tb.run()
            elapsed = time.time() - t0
            trig = csi = None
            if instrument:
                det = np.fromfile("sync-detect.dat", dtype=np.uint8)
                trig = np.flatnonzero(det).tolist()
                csi = np.fromfile("channel-estimate.dat", dtype=np.complex64)
                csi = csi.reshape(-1, FFT_LEN)
    data = np.array(sink.data(), dtype=np.uint8)
    tags = sorted((t.offset, int(pmt.to_long(t.value))) for t in sink.tags()
                  if pmt.symbol_to_string(t.key) == RX_KEY)
    rx_packets = [data[o:o + n] for o, n in tags]
    return {"rx_packets": rx_packets, "triggers": trig, "csi": csi, "runtime_s": elapsed}


def score(tx_packets, rx_packets):
    n_tx = len(tx_packets)
    received = {}
    order = []
    for p in rx_packets:
        if len(p) != len(tx_packets[0]):
            continue
        seq = (int(p[0]) << 8) | int(p[1])
        if seq < n_tx and seq not in received:
            received[seq] = p
            order.append(seq)
    bit_err = sum(int(np.unpackbits(np.bitwise_xor(p, tx_packets[s])).sum())
                  for s, p in received.items())
    lost_seq = sorted(set(range(n_tx)) - set(received))
    return {"n_tx": n_tx, "n_rx_valid": len(received), "lost": len(lost_seq),
            "pdr": len(received) / n_tx, "bit_errors": bit_err,
            "lost_seq": lost_seq, "rx_order": order}


# ----------------------------------------------------------------- guarded trial
def _child(q, fn, kwargs):
    try:
        q.put(fn(**kwargs))
    except Exception as e:  # report instead of dying silently
        q.put({"status": "ERROR", "error": repr(e)})


def run_guarded(fn, kwargs, timeout_s=60):
    ctx = mp.get_context("fork")
    q = ctx.Queue()
    p = ctx.Process(target=_child, args=(q, fn, kwargs))
    t0 = time.time()
    p.start()
    res = None
    deadline = t0 + timeout_s
    while time.time() < deadline:
        try:
            res = q.get(timeout=0.5)
            break
        except Exception:
            if not p.is_alive() and q.empty():
                break
    if res is None:
        if p.is_alive():
            p.kill()
        p.join()
        return {"status": "HANG", "runtime_s": round(time.time() - t0, 1), **kwargs}
    p.join()
    res.setdefault("status", "OK")
    return res


def tx_power(rolloff=4):
    rng = np.random.default_rng(0)
    iq, _, _ = transmit(make_packets(50, 50, rng), 50, rolloff=rolloff)
    return float(np.mean(np.abs(iq) ** 2))


def hpd_replay(triggers, burst_idx, frame_samples, n_scored, slack=1):
    """Replay Header/Payload Demux's trigger handling on logged triggers.
    Empirical rule found in M3 (E8): a trigger is used only if it arrives at
    least (frame_samples - slack) samples after the last used trigger; earlier
    triggers fall inside the frame being demultiplexed and are skipped, so that
    packet is lost. With slack=1 this predicts the lost packets exactly."""
    acc, rej = [], []
    for t, b in zip(triggers, burst_idx):
        if not acc or t >= acc[-1] + frame_samples - slack:
            acc.append(t)
        else:
            rej.append(int(b))
    return sorted(b for b in rej if b < n_scored)
