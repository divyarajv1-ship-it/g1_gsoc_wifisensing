#!/usr/bin/env python3
"""
Packet-loss measurement for the GNU Radio OFDM TX/RX chain (GNU Radio Issue #6891).

Every transmitted packet carries a 16-bit sequence number in its first two
bytes, followed by random payload bytes. After reception we know exactly
which packets arrived, which were lost and which arrived with bit errors.

Two execution modes are compared:

  streaming : source -> ofdm_tx -> [channel] -> ofdm_rx -> sink
              (one flowgraph; the scheduler moves data in chunks)
  offline   : ofdm_tx runs to completion first, the complete baseband signal
              is stored, then ofdm_rx runs on the stored signal
              (removes scheduler chunking as an explanation)

If packets are lost in both modes, the loss is caused by the signal
processing (Schmidl & Cox plateau timing + Header/Payload Demux), not by the
scheduler.

Usage examples:
  python ofdm_packet_loss.py --rolloff 0 --n-packets 500 --seed 1
  python ofdm_packet_loss.py --sweep --out ../../Results/packet_loss.csv
"""

import argparse
import csv
import multiprocessing as mp
import os
import time

import numpy as np
import pmt
from gnuradio import blocks, channels, digital, gr
from gnuradio.digital.ofdm_txrx import ofdm_rx, ofdm_tx

LEN_KEY = "packet_len"
FRAME_KEY = "frame_len"
# The RX must use a different length-tag key than the TX (as the official
# ofdm_loopback example does). If the TX tag "packet_len" reaches an RX that
# also uses "packet_len", header_payload_demux fails with "Buffer too small
# for min_noutput_items" and the flowgraph freezes (see tag_leak_matrix.py).
RX_KEY = "rx_len"
N_FLUSH = 3


def make_packets(n_packets, packet_len, rng):
    """Return a list of packets; bytes 0-1 hold the sequence number."""
    packets = []
    for seq in range(n_packets):
        payload = rng.integers(0, 256, packet_len - 2, dtype=np.uint8)
        header = np.array([(seq >> 8) & 0xFF, seq & 0xFF], dtype=np.uint8)
        packets.append(np.concatenate([header, payload]))
    return packets


def make_channel(noise_voltage, freq_offset, seed=0):
    if noise_voltage is None:
        return None
    # epsilon=1.0 (no timing offset), single-tap channel
    return channels.channel_model(
        noise_voltage=noise_voltage,
        frequency_offset=freq_offset,
        epsilon=1.0,
        taps=[1.0 + 0.0j],
        noise_seed=seed,
        block_tags=True,
    )


def build_source(packets, packet_len):
    data = np.concatenate(packets).tolist()
    src = blocks.vector_source_b(data, False, 1, [])
    s2ts = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, packet_len, LEN_KEY)
    return src, s2ts


def split_rx(sink, packet_len):
    """Split the received byte stream into packets using the length tags."""
    data = np.array(sink.data(), dtype=np.uint8)
    tags = sorted(
        (t.offset, int(pmt.to_long(t.value)))
        for t in sink.tags()
        if pmt.symbol_to_string(t.key) == RX_KEY
    )
    rx_packets = []
    for offset, length in tags:
        rx_packets.append(data[offset:offset + length])
    if not tags and len(data):
        # fall back to fixed-length split
        rx_packets = [data[i:i + packet_len] for i in range(0, len(data), packet_len)]
    return rx_packets


def score(tx_packets, rx_packets):
    """Compare TX and RX packets by sequence number."""
    n_tx = len(tx_packets)
    received = {}
    bad_len = 0
    for p in rx_packets:
        if len(p) != len(tx_packets[0]):
            bad_len += 1
            continue
        seq = (int(p[0]) << 8) | int(p[1])
        if seq < n_tx and seq not in received:
            received[seq] = p
    bit_errors = 0
    corrupted = 0
    for seq, p in received.items():
        diff = np.unpackbits(np.bitwise_xor(p, tx_packets[seq]))
        e = int(diff.sum())
        bit_errors += e
        corrupted += e > 0
    n_rx = len(received)
    lost = n_tx - n_rx
    bits_checked = n_rx * len(tx_packets[0]) * 8
    lost_seq = sorted(set(range(n_tx)) - set(received))
    return {
        "n_tx": n_tx,
        "n_rx_valid": n_rx,
        "n_rx_bad_len": bad_len,
        "lost": lost,
        "pdr": n_rx / n_tx,
        "corrupted": corrupted,
        "ber_received": bit_errors / bits_checked if bits_checked else float("nan"),
        "lost_seq": lost_seq,
    }


def run_streaming(packets, packet_len, rolloff, noise_voltage, freq_offset, gap,
                  seed=0):
    tb = gr.top_block()
    src, s2ts = build_source(packets, packet_len)
    tx = ofdm_tx(packet_length_tag_key=LEN_KEY, rolloff=rolloff, scramble_bits=True)
    rx = ofdm_rx(frame_length_tag_key=FRAME_KEY, packet_length_tag_key=RX_KEY,
                 scramble_bits=True)
    sink = blocks.vector_sink_b()
    tb.connect(src, s2ts, tx)
    last = tx
    if gap:
        # zero padding between bursts (the "burst shaper" workaround)
        # ofdm_tx output carries the burst length tag under LEN_KEY
        shaper = digital.burst_shaper_cc([], gap, 0, False, LEN_KEY)
        tb.connect(last, shaper)
        last = shaper
    ch = make_channel(noise_voltage, freq_offset, seed)
    if ch is not None:
        tb.connect(last, ch, rx)
    else:
        tb.connect(last, rx)
    tb.connect(rx, sink)
    t0 = time.time()
    tb.run()
    return sink, time.time() - t0


def run_offline(packets, packet_len, rolloff, noise_voltage, freq_offset, gap,
                seed=0):
    # TX alone
    tb = gr.top_block()
    src, s2ts = build_source(packets, packet_len)
    tx = ofdm_tx(packet_length_tag_key=LEN_KEY, rolloff=rolloff, scramble_bits=True)
    tx_sink = blocks.vector_sink_c()
    tb.connect(src, s2ts, tx)
    if gap:
        shaper = digital.burst_shaper_cc([], gap, 0, False, LEN_KEY)
        tb.connect(tx, shaper, tx_sink)
    else:
        tb.connect(tx, tx_sink)
    tb.run()
    samples = list(tx_sink.data()) + [0j] * 2000
    # RX alone, on the stored signal
    tb = gr.top_block()
    vsrc = blocks.vector_source_c(samples, False)
    rx = ofdm_rx(frame_length_tag_key=FRAME_KEY, packet_length_tag_key=RX_KEY,
                 scramble_bits=True)
    sink = blocks.vector_sink_b()
    ch = make_channel(noise_voltage, freq_offset, seed)
    if ch is not None:
        tb.connect(vsrc, ch, rx, sink)
    else:
        tb.connect(vsrc, rx, sink)
    t0 = time.time()
    tb.run()
    return sink, time.time() - t0


def run_once(mode, n_packets, packet_len, rolloff, noise_voltage, freq_offset,
             gap, seed):
    rng = np.random.default_rng(seed)
    # N_FLUSH extra packets are sent after the measured ones so that the
    # receiver pipeline is flushed; they are not scored.
    packets = make_packets(n_packets + N_FLUSH, packet_len, rng)
    runner = run_streaming if mode == "streaming" else run_offline
    sink, elapsed = runner(packets, packet_len, rolloff, noise_voltage,
                           freq_offset, gap, seed)
    res = score(packets[:n_packets], split_rx(sink, packet_len))
    res.update(mode=mode, packet_len=packet_len, rolloff=rolloff,
               noise_voltage=noise_voltage if noise_voltage is not None else 0.0,
               freq_offset=freq_offset, gap=gap, seed=seed,
               runtime_s=round(elapsed, 3))
    return res


def _child(q, args):
    try:
        q.put(run_once(*args))
    except Exception as e:  # report instead of dying silently
        q.put({"error": repr(e)})


def run_guarded(args, timeout_s):
    """Run one trial in a child process. If the flowgraph stalls (a block
    thread died and the scheduler waits forever), record status=HANG."""
    q = mp.Queue()
    p = mp.Process(target=_child, args=(q, args))
    t0 = time.time()
    p.start()
    p.join(timeout_s)
    if p.is_alive():
        p.kill()
        p.join()
        mode, n, plen, ro, nv, fo, gap, seed = args
        return {"status": "HANG", "mode": mode, "packet_len": plen,
                "rolloff": ro, "gap": gap,
                "noise_voltage": nv if nv is not None else 0.0,
                "freq_offset": fo, "seed": seed, "n_tx": n,
                "runtime_s": round(time.time() - t0, 1)}
    res = q.get() if not q.empty() else {"error": "no result"}
    res.setdefault("status", "OK" if "error" not in res else "ERROR")
    return res


FIELDS = ["status", "mode", "packet_len", "rolloff", "gap", "noise_voltage",
          "freq_offset", "seed", "n_tx", "n_rx_valid", "n_rx_bad_len", "lost",
          "pdr", "corrupted", "ber_received", "runtime_s"]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["streaming", "offline"], default="streaming")
    ap.add_argument("--n-packets", type=int, default=500)
    ap.add_argument("--packet-len", type=int, default=50)
    ap.add_argument("--rolloff", type=int, default=0)
    ap.add_argument("--gap", type=int, default=0,
                    help="zero samples inserted after each burst")
    ap.add_argument("--noise", type=float, default=None,
                    help="channel noise voltage; omit for no channel block")
    ap.add_argument("--freq-offset", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--sweep", action="store_true",
                    help="run the full M2 experiment grid")
    ap.add_argument("--out", default=None, help="CSV output path")
    ap.add_argument("--timeout", type=float, default=60,
                    help="seconds before a trial is declared HANG")
    args = ap.parse_args()

    if not args.sweep:
        res = run_guarded((args.mode, args.n_packets, args.packet_len,
                           args.rolloff, args.noise, args.freq_offset,
                           args.gap, args.seed), args.timeout)
        for k in FIELDS:
            print(f"{k:>14}: {res.get(k)}")
        print(f"{'lost_seq':>14}: {res.get('lost_seq', [])[:30]}")
        return

    rows = []
    seeds = [1, 2, 3, 4, 5]
    grid = []
    # E1: baseline vs workarounds, ideal channel, both execution modes
    for mode in ["streaming", "offline"]:
        for rolloff, gap in [(0, 0), (1, 0), (2, 0), (4, 0), (0, 1), (0, 8)]:
            for seed in seeds:
                grid.append((mode, 50, rolloff, gap, None, 0.0, seed))
    # E2: packet length dependence (no workaround)
    for plen in [20, 50, 100, 200]:
        for seed in seeds:
            grid.append(("streaming", plen, 0, 0, None, 0.0, seed))
    # E3: noise sweep, with and without the rolloff fix
    for nv in [0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5]:
        for rolloff in [0, 4]:
            for seed in seeds:
                grid.append(("streaming", 50, rolloff, 0, nv, 0.0, seed))
    for i, (mode, plen, ro, gap, nv, fo, seed) in enumerate(grid):
        res = run_guarded((mode, args.n_packets, plen, ro, nv, fo, gap, seed),
                          args.timeout)
        rows.append(res)
        print(f"[{i + 1}/{len(grid)}] {mode:9s} len={plen:3d} rolloff={ro} gap={gap} "
              f"noise={res['noise_voltage']:.2f} seed={seed} -> {res['status']} "
              f"lost={res.get('lost')} PDR={res.get('pdr')}", flush=True)
    out = args.out or "packet_loss.csv"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
