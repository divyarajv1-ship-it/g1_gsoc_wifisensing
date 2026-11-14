# G1 GSoC Wi-Fi Sensing

A hardware-independent Wi-Fi sensing project focused on robust OFDM
channel modeling and signal-processing reliability using GNU Radio.

## Project Scope

This project investigates GNU Radio Issue #7997, where inserting the
Channel Model into an OFDM flowgraph causes the flowgraph to freeze.

The proposed work will focus on:

- reproducing and understanding the reported OFDM flowgraph issue,
- investigating the interaction between the GNU Radio scheduler,
  block processing, buffering, and the Channel Model,
- developing and validating a robust solution,
- evaluating OFDM reliability under controlled channel conditions, and
- studying the relevance of reliable OFDM/channel modeling to Wi-Fi
  CSI sensing.

GNU Radio Issue #6891 will be considered as a related OFDM reliability
issue.

## Domain

Wi-Fi Sensing

## Mode

GSoC

## Primary Issue

GNU Radio #7997

## Related Issue

GNU Radio #6891

## Benchmark / Dataset

WiFi-CSI-Sensing-Benchmark (SenseFi)

## Hardware

Hardware-independent. The core project will use GNU Radio simulation
and publicly available CSI datasets. Physical hardware is not required
for the proposed scope.

## Project Status

## Milestones

| Milestone | What we did | Folder |
|---|---|---|
| M1 | Chose the problem: silent packet loss (#6891) and flowgraph freezes (#7997) in GNU Radio's OFDM chain; reviewed CSI sensing, IEEE 802.11bf and Wi-Fi sensing work. | [`M1_g1_gsoc_wifisensing/`](M1_g1_gsoc_wifisensing/) |
| M2 | Reproduced #6891: the stock OFDM loopback delivers only 95.9 % of packets with zero noise, the same with and without the scheduler. Reproduced the freeze mechanism behind #7997 (output buffer too small). Prepared an upstream fix: a multi-packet regression test plus `rolloff=4` in the example. | [`M2_g1_gsoc_wifisensing/`](M2_G1/) |
| M3 | Six experiments (E6–E10): Schmidl & Cox trigger jitter of 69–73 samples explains every lost packet (100/100 runs); the fix is never worse over 20 multipath/SNR conditions; CFO up to 3.5 subcarriers has no effect; the bug silently removes 7–9 % of CSI samples; packets ≥ 1020 B are never transmitted. GSoC 2027 proposal draft. | [`M3_g1_gsoc_wifisensing/`](M3_g1_gsoc_wifisensing/) |
| M4 | Final: consolidated evaluation (E1–E10); our one pull request, #8271 (11 Nov 2026), and the maintainer's question on it; revision prepared, not pushed yet; SOTA positioning; refined GSoC 2027 proposal; 20-min video. | [`M4_g1_gsoc_wifisensing/`](M4_g1_gsoc_wifisensing/) |


## Current status (14 Nov 2026)

| Item | Status |
|---|---|
| Upstream pull request | One pull request: [gnuradio/gnuradio#8271](https://github.com/gnuradio/gnuradio/pull/8271), open, label "Needs Action". Revision prepared after the maintainer's question; not pushed yet. |
| What the PR adds | `test_005_tx_multipacket_rolloff` in `gr-digital/python/digital/qa_ofdm_txrx.py` (100 back-to-back packets; fails with rolloff 0, passes with rolloff 4) and `rolloff: '4'` in `gr-digital/examples/ofdm/ofdm_loopback.grc`. |
| Issue comment #6891 | Posted: https://github.com/gnuradio/gnuradio/issues/6891#issuecomment-6787055390 |
| Issue comment #7997 | not yet posted |
| Maintainer feedback | marcusmueller (12 Nov 2026): "are you proposing to abuse the rolloff factor to hide a bug?" We agree and have prepared a test-only revision of the same PR (default rolloff, `@unittest.expectedFailure`), not pushed yet; see the M4 report, Section 8. |

