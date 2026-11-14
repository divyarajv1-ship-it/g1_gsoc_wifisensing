# Results

All files are produced by `Code/run_all.sh` (fixed seeds). Numbers in the report come from these files.

| Folder / file | Content | Produced by |
|---|---|---|
| `m4/fig10_consolidated_pdr.png`, `m4/consolidated_results.md` | Headline comparison: stock vs workarounds (ideal channel) and per multipath profile | `Code/src/analysis/make_m4_summary.py` |
| `m4/` (after a re-run) | `smoke_test.txt`, `environment_used.txt`, `contribution_test_submitted_rerun.txt`, `contribution_test_revision_expectedfailure.txt` | `Code/run_all.sh` |
| `m2/packet_loss_sweep.csv`, `.log` | E1–E3: PDR per TX setting, mode, packet length, noise | `ofdm_packet_loss.py --sweep` |
| `m2/snr_sweep.csv`, `.log` | Fine SNR sweep | `snr_sweep.py` |
| `m2/freeze_buffer_test.txt`, `m2/tag_leak_matrix.txt` | E4, E5 freeze results | M2 scripts |
| `m2/summary.md`, `m2/figures/fig1–fig4` | M2 tables and figures | `make_m2_figures.py` |
| `m3/e8_trigger_timing.csv`, `e8b_length_scan.csv` | Trigger offsets/spacing, losses, replay-model match | E8, E8b |
| `m3/e6_multipath_snr.csv`, `e7_cfo.csv` | PDR over multipath × SNR, CFO | E6, E7 |
| `m3/e9_csi_sensing.csv` | CSI NMSE, missing CSI frames, motion-frequency error | E9 |
| `m3/e10_large_packets.csv` | Large-packet freeze / refusal | E10 |
| `m3/contribution_test_3.10.9.txt` | Upstream test re-validation on GNU Radio 3.10.9.2 | `test_multipacket_regression.py` |
| `m3/summary_m3.md`, `m3/figures/fig5–fig9`, `m3/logs/` | M3 tables, figures, raw logs | `make_m3_figures.py` |

## Headline numbers

| Result | Value | File |
|---|---|---|
| Stock PDR, ideal channel, 50 B | 95.88 % (103 of 2500 lost) | `m3/summary_m3.md` |
| Streaming vs offline lost per seed | 26, 21, 19, 18, 19 in both | `m2/packet_loss_sweep.csv` |
| Trigger offset stock / rolloff 4 | 69–73 / 73 only | `m3/e8_trigger_timing.csv` |
| Replay model predicts every loss | 100/100 runs | `m3/summary_m3.md` |
| Harsh multipath, noise-free | 88.5 % → 100 % | `m3/e6_multipath_snr.csv` |
| CSI samples missing (stock) | 7.5–7.9 % at ≥ 25 dB | `m3/e9_csi_sensing.csv` |
| Motion-frequency bias (stock, packet-order timestamps) | 7.4–8.3 % | `m3/e9_csi_sensing.csv` |
| Largest packet that can be sent | 1019 B | `m3/e10_large_packets.csv`, `m3/logs/e10.log` |
