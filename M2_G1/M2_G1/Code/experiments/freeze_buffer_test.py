#!/usr/bin/env python3
"""
Silent-freeze test: packet size vs. block output-buffer size.

GNU Radio's tagged-stream blocks (tagged_stream_mux, ofdm_carrier_allocator,
ofdm_cyclic_prefixer) and header_payload_demux need one complete packet/frame
to fit into their output buffer. They request this with
set_min_noutput_items(). If it does not fit, the block thread stops with
"Buffer too small for min_noutput_items", the other threads keep waiting,
and tb.run() never returns: the flowgraph freezes without an exception.

This script sends 20 packets of each length through ofdm_tx -> ofdm_rx
(offline mode, rolloff 4) twice: with default buffers and with all internal
output buffers raised to 65536 items via hier_block2.set_min_output_buffer().
"""
import ofdm_packet_loss as opl

orig_tx, orig_rx = opl.ofdm_tx, opl.ofdm_rx


def enlarged(cls):
    def make(*a, **k):
        blk = cls(*a, **k)
        blk.set_min_output_buffer(1 << 16)
        return blk
    return make


if __name__ == "__main__":
    print(f"{'packet bytes':>12} | {'default buffers':<28} | {'buffers = 65536 items':<28}")
    for length in (50, 100, 200, 250, 300, 400, 600, 800):
        out = []
        for big in (False, True):
            opl.ofdm_tx = enlarged(orig_tx) if big else orig_tx
            opl.ofdm_rx = enlarged(orig_rx) if big else orig_rx
            r = opl.run_guarded(("offline", 20, length, 4, None, 0.0, 0, 1), 30)
            out.append(f"{r['status']:<5} {str(r.get('n_rx_valid', '-')):>3}/20 received")
        print(f"{length:>12} | {out[0]:<28} | {out[1]:<28}", flush=True)
