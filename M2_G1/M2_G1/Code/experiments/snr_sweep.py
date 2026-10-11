#!/usr/bin/env python3
"""
Packet delivery ratio (PDR) of the GNU Radio OFDM chain versus SNR,
with (rolloff=4) and without (rolloff=0) the #6891 workaround.

SNR is defined as mean TX sample power / noise power. The TX power of
ofdm_tx with default settings is measured once (~51, the IFFT is not
normalised), and the channel noise voltage is set from it.
Each trial runs with a watchdog, so a frozen flowgraph is recorded as HANG.
"""
import csv
import sys

import numpy as np
from gnuradio import blocks, gr
from gnuradio.digital.ofdm_txrx import ofdm_tx

import ofdm_packet_loss as opl


def tx_power():
    d = np.random.default_rng(0).integers(0, 256, 50 * 50).tolist()
    tb = gr.top_block()
    src = blocks.vector_source_b(d)
    s2ts = blocks.stream_to_tagged_stream(1, 1, 50, "packet_len")
    tx = ofdm_tx(packet_length_tag_key="packet_len", rolloff=4, scramble_bits=True)
    sink = blocks.vector_sink_c()
    tb.connect(src, s2ts, tx, sink)
    tb.run()
    x = np.array(sink.data())
    return float(np.mean(np.abs(x) ** 2))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "snr_sweep.csv"
    p_sig = tx_power()
    print(f"TX power = {p_sig:.2f}")
    rows = []
    for snr_db in [6, 8, 9, 10, 11, 12, 13, 14, 15, 17, 20, 25, 30]:
        nv = float(np.sqrt(p_sig / 10 ** (snr_db / 10)))
        for rolloff in [0, 4]:
            for seed in [1, 2, 3, 4, 5]:
                r = opl.run_guarded(("streaming", 300, 50, rolloff, nv, 0.0, 0, seed), 60)
                r["snr_db"] = snr_db
                rows.append(r)
                print(f"SNR={snr_db:2d} dB nv={nv:.3f} rolloff={rolloff} seed={seed} "
                      f"-> {r['status']} PDR={r.get('pdr')}", flush=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["snr_db"] + opl.FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print("wrote", out)
