#!/usr/bin/env python3
"""
Does a TX length tag leaking into ofdm_rx freeze the flowgraph?

Streaming TX->RX, ideal channel, rolloff=4 (no packet loss expected).
Cases vary (a) whether a channel_model with block_tags=True sits between
TX and RX and (b) whether the RX uses the same length-tag key as the TX.
Each case runs in a child process with a timeout; a stall is a HANG.
"""
import multiprocessing as mp
import sys
import time

import numpy as np
from gnuradio import blocks, channels, gr
from gnuradio.digital.ofdm_txrx import ofdm_rx, ofdm_tx

N_PACKETS, PACKET_LEN = 300, 50


def case(q, channel, block_tags, rx_key):
    rng = np.random.default_rng(1)
    data = rng.integers(0, 256, N_PACKETS * PACKET_LEN, dtype=np.uint8).tolist()
    tb = gr.top_block()
    src = blocks.vector_source_b(data, False)
    s2ts = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, PACKET_LEN, "packet_len")
    tx = ofdm_tx(packet_length_tag_key="packet_len", rolloff=4, scramble_bits=True)
    rx = ofdm_rx(frame_length_tag_key="frame_len", packet_length_tag_key=rx_key,
                 scramble_bits=True)
    sink = blocks.vector_sink_b()
    tb.connect(src, s2ts, tx)
    if channel:
        ch = channels.channel_model(0.0, 0.0, 1.0, [1.0], 0, block_tags)
        tb.connect(tx, ch, rx)
    else:
        tb.connect(tx, rx)
    tb.connect(rx, sink)
    tb.run()
    q.put(len(sink.data()) // PACKET_LEN)


if __name__ == "__main__":
    cases = [
        ("no channel, RX key = TX key", False, False, "packet_len"),
        ("no channel, RX key = 'rx_len'", False, False, "rx_len"),
        ("channel block_tags=False, same key", True, False, "packet_len"),
        ("channel block_tags=True,  same key", True, True, "packet_len"),
        ("channel block_tags=False, 'rx_len'", True, False, "rx_len"),
    ]
    for name, chan, bt, key in cases:
        q = mp.Queue()
        p = mp.Process(target=case, args=(q, chan, bt, key))
        t0 = time.time()
        p.start()
        p.join(40)
        if p.is_alive():
            p.kill()
            p.join()
            print(f"{name:40s} -> HANG (no progress after 40 s)", flush=True)
        else:
            n = q.get() if not q.empty() else "?"
            print(f"{name:40s} -> finished in {time.time() - t0:4.1f} s, "
                  f"{n}/{N_PACKETS} packets out", flush=True)
