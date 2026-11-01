# Milestone 3 — G1 GSoC Wi-Fi Sensing

**Project:** Robust OFDM Channel Modelling for Wi-Fi CSI Sensing in GNU Radio
**Mode:** GSoC / open source (GNU Radio) **Issues:** [#6891](https://github.com/gnuradio/gnuradio/issues/6891), [#7997](https://github.com/gnuradio/gnuradio/issues/7997)
**Team:** Hirva Vekariya, Tirth Pathar, Divyaraj Vaghela, Jahnavi Patel, Jinay Shah

M1 chose the problem. M2 reproduced it, found the causes and prepared a tested upstream contribution.
**M3 validates that contribution under realistic channels, explains it at sample level, measures what
the bug means for Wi-Fi sensing, and states the contribution status and next steps (GSoC 2027 draft).**

Report: [`Report/M3_g1_gsoc_wifisensing_Report.pdf`](Report/M3_g1_gsoc_wifisensing_Report.pdf)

## What M3 found (all numbers from the scripts in `Code/`, tables in `Results/summary_m3.md`)

| # | Finding | Evidence |
|---|---|---|
| F7 | With the stock TX the Schmidl & Cox trigger jitters over 69–73 samples; with `rolloff=4` it is fixed at one sample (73), with one zero sample at 74. | E8, Fig. 5 |
| F8 | Rule "Header/Payload Demux uses a trigger only if it arrives ≥ frame_len − 1 samples after the last used trigger" predicts **every lost packet exactly** in 100/100 logged runs. | E8, E8b |
| F9 | M2's "100-byte packets lose nothing" = those lengths have ≤ 1 sample trigger jitter. "Last OFDM symbol full" hypothesis tested and **rejected**. | E8b, Fig. 6 |
| F10 | Over 4 multipath profiles × 5 SNRs the fix is never worse (20/20). Multipath makes the bug worse: noise-free loss 3.9 % (flat) → 11.5 % (harsh); fix → 0 %. | E6, Fig. 7 |
| F11 | CFO up to 3.5 subcarriers changes nothing; fix stays at 100 % (flat, 25 dB). | E7, Fig. 8 |
| F12 | GNU Radio's channel estimator gives accurate CSI (NMSE −19 dB at 15 dB → −34 dB at 30 dB) but `ofdm_rx` does not output it. The bug silently removes 7–9 % of CSI samples; a 0.5 Hz motion is then estimated 7–8 % too high if timestamps come from packet order (< 0.1 % with the fix). | E9, Fig. 9 |
| F13 | Freeze reproduced on a second GR build (≥ 300 B, default buffers). Bigger buffers fix ≤ 1019 B; **≥ 1020 B are silently never transmitted** (`tagged_stream_mux`: max 8191 items available). | E10 |
| F14 | The proposed upstream test passes on GR 3.10.9.2, its negative control (rolloff 0) fails, and it passes for 20/50/100/200 B × 3 seeds. | `Results/contribution_test_3.10.9.txt` |

## Folder layout

```
M3_g1_gsoc_wifisensing/
├── README.md
├── Report/
│   ├── M3_g1_gsoc_wifisensing_Report.pdf      final PDF (submit this)
│   └── M3_g1_gsoc_wifisensing_Report.md       editable source
├── Code/
│   ├── environment.yml                        conda/micromamba env (or apt install gnuradio)
│   ├── run_all.sh                             re-runs every experiment + figures (~25 min)
│   ├── experiments/
│   │   ├── m3_harness.py                      TX/RX, numpy channel, trigger + CSI logging, HPD replay
│   │   ├── e6_multipath_snr.py                PDR vs SNR over 4 multipath profiles
│   │   ├── e7_cfo.py                          PDR vs carrier frequency offset
│   │   ├── e8_trigger_timing.py               trigger jitter + exact loss prediction
│   │   ├── e8b_length_scan.py                 20 packet lengths (100-byte mystery)
│   │   ├── e9_csi_sensing.py                  CSI accuracy, CSI gaps, sensing bias
│   │   └── e10_large_packets.py               freeze / silent refusal up to 1500 B
│   ├── contribution/test_multipacket_regression.py   upstream test re-validation
│   └── analysis/make_m3_figures.py            builds Results/figures + summary_m3.md
├── Results/  CSVs, logs/, figures/, summary_m3.md, contribution_test_3.10.9.txt
├── Proposal/GSoC2027_Proposal_Draft_G1.md     initial GSoC 2027 proposal draft
└── Docs/     00_WHAT_IS_M3.md (explainer), 01_M3_STEP_BY_STEP_GUIDE.md (team guide)
```

## Reproduce

```bash
# Ubuntu 24.04 / WSL:  sudo apt install gnuradio python3-numpy python3-matplotlib python3-pandas
# or, no sudo:          micromamba create -f Code/environment.yml && micromamba activate g1-gr310
cd Code && ./run_all.sh
# quick check: E8 rolloff 0, seed 1 loses 26 of 500 packets (same as M2)
```
Every trial runs in a child process with a timeout, so a frozen flowgraph is recorded as `HANG`.
M3 numbers were produced with GNU Radio 3.10.9.2 (Python 3.12); M2's numbers reproduce exactly on it.

## Metrics
* **PDR** = packets with valid CRC and correct sequence number / packets sent.
* **Trigger offset / spacing** = position of each Schmidl & Cox trigger relative to the true burst start / previous trigger (from `ofdm_rx(debug_log=True)`'s `sync-detect.dat`).
* **CSI NMSE** = Σ(s·|Ĥ|−|H|)² / Σ|H|² over the 52 occupied subcarriers (one global scale s).
* **SNR** = mean TX sample power / noise power. **Freeze** = no progress within the timeout (`HANG`).

## Contribution status
| Item | Status |
|---|---|
| Multi-packet QA test + example fix (`rolloff=4`) | written (M2), re-validated on a second GR build (M3) |
| Issue comments #6891 / #7997 | **[TEAM: posted on … / link]** |
| Pull request to gnuradio/gnuradio | **[TEAM: link + state, or "not yet opened"]** |
| Maintainer feedback | **[TEAM]** |

## Limitations
Simulation only; synthetic channels; #7997's own flowgraph unavailable; the jitter-free packet lengths
are observed but not explained; uncoded BPSK limits low-SNR multipath performance; ≥ 1020 B packets fail.

Video: **[TEAM: link, if required]**
