#!/usr/bin/env python3
"""E10: silent freeze (#7997 mechanism) vs packet size up to the Wi-Fi MTU
(1500 B), for three buffer configurations:
  default        - GNU Radio default buffers everywhere
  rx_tx_big      - ofdm_tx and ofdm_rx hier blocks: set_min_output_buffer(65536)
  all_big        - additionally the source-side stream_to_tagged_stream block
20 packets, rolloff 4, ideal channel; a trial that does not finish in 30 s = HANG."""
import csv, sys
import numpy as np
import m3_harness as h

def trial(plen, cfg, n=20):
    rng = np.random.default_rng(1)
    pk = h.make_packets(n + h.N_FLUSH, plen, rng)
    big_tx = cfg in ("rx_tx_big", "all_big")
    if cfg == "rx_tx_big":
        # enlarge only the ofdm_tx hier block, not the source-side block
        import gnuradio.blocks as gb
        from gnuradio import gr
        from gnuradio.digital.ofdm_txrx import ofdm_tx
        tb = gr.top_block()
        src = gb.vector_source_b(np.concatenate(pk).tolist(), False, 1, [])
        s2ts = gb.stream_to_tagged_stream(gr.sizeof_char, 1, plen, h.LEN_KEY)
        tx = ofdm_tx(packet_length_tag_key=h.LEN_KEY, rolloff=4, scramble_bits=True)
        tx.set_min_output_buffer(1 << 16)
        sink = gb.vector_sink_c()
        tb.connect(src, s2ts, tx, sink)
        tb.run()
        iq = np.array(sink.data(), dtype=np.complex64)
    else:
        iq, _, _ = h.transmit(pk, plen, rolloff=4, big_buffers=big_tx)
    r = h.receive(np.concatenate([np.zeros(100, np.complex64), iq]), instrument=False,
                  big_buffers=big_tx)
    s = h.score(pk[:n], r["rx_packets"])
    return {"n_tx": n, "n_rx_valid": s["n_rx_valid"], "pdr": s["pdr"]}

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "../../Results/e10_large_packets.csv"
    rows = []
    for plen in [100, 250, 300, 600, 1000, 1500]:
        for cfg in ["default", "rx_tx_big", "all_big"]:
            r = h.run_guarded(trial, dict(plen=plen, cfg=cfg), 30)
            r.update(packet_len=plen, buffers=cfg)
            rows.append(r)
            print(plen, cfg, r["status"], r.get("n_rx_valid"), flush=True)
    f = ["packet_len", "buffers", "status", "n_tx", "n_rx_valid", "pdr"]
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=f, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    print("wrote", out)
