# Code

Everything that produced the numbers in the M2, M3 and M4 reports, and the upstream contribution.

## Requirements
* GNU Radio 3.10 with Python bindings (tested: 3.10.12.0 conda-forge / Python 3.11; 3.10.9.2 Ubuntu 24.04 / Python 3.12)
* numpy, pandas, matplotlib
* No SDR hardware, no external dataset

```bash
sudo apt install gnuradio python3-numpy python3-matplotlib python3-pandas      # Ubuntu 24.04 / WSL
# or
micromamba create -f environment.yml && micromamba activate g1-gr310            # no admin rights
python3 -c "from gnuradio import gr; print(gr.version())"                      # check
```

## Run
```bash
QUICK=1 bash run_all.sh   # smoke test (2 min) -> Results/m4/smoke_test.txt
bash run_all.sh           # everything (~35 min) -> Results/m2, Results/m3, Results/m4
```
Choose the interpreter with `PY=python3.12 bash run_all.sh`. Every trial runs in a child process with a timeout, so a frozen flowgraph is recorded as `HANG` and the run continues.

## `src/` contents

| Path | What it does | Report section |
|---|---|---|
| `m2_experiments/ofdm_packet_loss.py` | Sequence-numbered packet-loss harness; streaming vs offline; `--sweep` runs E1–E3 | Section 6.1, Section 6.2 |
| `m2_experiments/snr_sweep.py` | Fine SNR sweep (Fig. 3) | Section 6.2 |
| `m2_experiments/freeze_buffer_test.py` | E4: packet size vs buffer size → HANG/OK | Section 6.6 |
| `m2_experiments/tag_leak_matrix.py` | E5: leaked length tags freeze the RX | Section 6.6 |
| `m3_experiments/m3_harness.py` | TX/RX, numpy channel (multipath, CFO, AWGN), trigger + CSI logging, Header/Payload Demux replay model | Section 3.1 |
| `m3_experiments/e8_trigger_timing.py`, `e8b_length_scan.py` | Sample-level mechanism, length scan | Section 6.3 |
| `m3_experiments/e6_multipath_snr.py`, `e7_cfo.py` | Multipath × SNR, CFO | Section 6.4 |
| `m3_experiments/e9_csi_sensing.py` | CSI accuracy, CSI gaps, motion-frequency bias | Section 6.5 |
| `m3_experiments/e10_large_packets.py` | Freeze / silent refusal up to 1500 B | Section 6.6 |
| `analysis/make_m2_figures.py`, `make_m3_figures.py`, `make_m4_summary.py` | Figures and summary tables | Section 6 |
| `contribution/pr8271_as_submitted/` | Our one pull request, #8271, as submitted on 11 Nov 2026: patched `qa_ofdm_txrx.py`, patches, PR description, commit message | Report Section 4.2 |
| `contribution/pr8271_revision_prepared_not_pushed/` | Revision of the same PR prepared after the maintainer's question (default rolloff, `@unittest.expectedFailure`) and its diff against the submitted version. Not pushed yet | Report Section 4.3 |
| `contribution/test_multipacket_regression.py` | Stand-alone re-validation: submitted test, negative control, 4 lengths × 3 seeds | Section 6.6 |

## Testing the upstream test on your own GNU Radio
```bash
python3 src/contribution/test_multipacket_regression.py      # expect: Ran 3 tests ... OK
python3 src/contribution/pr8271_revision_prepared_not_pushed/qa_ofdm_txrx.py   # expect: OK (expected failures=1)
```
