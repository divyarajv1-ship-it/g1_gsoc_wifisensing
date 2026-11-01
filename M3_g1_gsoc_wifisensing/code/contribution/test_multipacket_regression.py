#!/usr/bin/env python3
"""M3 re-validation of the M2 upstream contribution on a *second* GNU Radio build
(Ubuntu 24.04 package 3.10.9.2; M2 used conda-forge 3.10.12.0).

Contains the exact helper + test_005 proposed for gr-digital/python/digital/qa_ofdm_txrx.py
plus a negative control (rolloff=0) that must FAIL, proving the test detects #6891,
and a parametrised version over several packet lengths and seeds."""
import random
import unittest

from gnuradio import blocks, gr
from gnuradio.digital.ofdm_txrx import ofdm_rx, ofdm_tx
from gnuradio.digital.utils import tagged_streams


def txrx_multipacket(n_packets, n_bytes, rolloff, seed=0):
    random.seed(seed)
    len_tag_key = 'packet_len'
    packets = [[random.randint(0, 255) for _ in range(n_bytes)] for _ in range(n_packets)]
    data, tags = tagged_streams.packets_to_vectors(packets, len_tag_key)
    tx_tb = gr.top_block()
    src = blocks.vector_source_b(data, False, 1, tags)
    tx = ofdm_tx(packet_length_tag_key=len_tag_key, rolloff=rolloff, scramble_bits=True)
    tx_sink = blocks.vector_sink_c()
    tx_tb.connect(src, tx, tx_sink)
    tx_tb.run()
    rx_tb = gr.top_block()
    samples = [0j] * 100 + list(tx_sink.data()) + [0j] * 1000
    rx_src = blocks.vector_source_c(samples)
    rx = ofdm_rx(frame_length_tag_key='frame_len', scramble_bits=True)
    rx_sink = blocks.vector_sink_b()
    rx_tb.connect(rx_src, rx, rx_sink)
    rx_tb.run()
    return list(data), list(rx_sink.data())


class TestMultipacket(unittest.TestCase):
    def test_005_tx_multipacket_rolloff(self):
        """The proposed upstream test (100 x 50 B, rolloff 4)."""
        tx, rx = txrx_multipacket(100, 50, 4)
        self.assertEqual(len(rx), len(tx))
        self.assertEqual(tx, rx)

    def test_negative_control_rolloff0_detects_bug(self):
        """Same test with the stock setting must lose data (it is #6891)."""
        tx, rx = txrx_multipacket(100, 50, 0)
        self.assertLess(len(rx), len(tx))

    def test_rolloff4_many_lengths_and_seeds(self):
        """Robustness of the fix beyond the single case used upstream."""
        for n_bytes in (20, 50, 100, 200):
            for seed in range(3):
                with self.subTest(n_bytes=n_bytes, seed=seed):
                    tx, rx = txrx_multipacket(100, n_bytes, 4, seed)
                    self.assertEqual(tx, rx)


if __name__ == '__main__':
    print("GNU Radio", gr.version())
    unittest.main(verbosity=2)
