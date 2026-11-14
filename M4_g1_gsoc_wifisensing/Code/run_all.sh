#!/usr/bin/env bash
# Re-runs every experiment of the project (M2 + M3), the contribution tests and the figures.
# Usage (from anywhere):   bash Code/run_all.sh            # full run, about 35 min on a laptop
#                          QUICK=1 bash Code/run_all.sh    # only the 2-minute smoke test
# Choose the interpreter with PY=python3.12 etc. Needs GNU Radio 3.10 (see Code/README.md).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
RES="$HERE/../Results"
PY=${PY:-python3}
mkdir -p "$RES/m2" "$RES/m3/logs" "$RES/m4"

echo "GNU Radio $($PY -c 'from gnuradio import gr; print(gr.version())')" | tee "$RES/m4/environment_used.txt"
$PY --version >> "$RES/m4/environment_used.txt"

# --- smoke test: one stock run must lose 26 of 500 packets (seed 1), the fix must lose 0
cd "$HERE/src/m2_experiments"
$PY ofdm_packet_loss.py --mode offline --rolloff 0 --seed 1 | tee "$RES/m4/smoke_test.txt"
$PY ofdm_packet_loss.py --mode offline --rolloff 4 --seed 1 | tee -a "$RES/m4/smoke_test.txt"
[ -n "$QUICK" ] && exit 0

# --- M2 experiments (E1-E5)
$PY ofdm_packet_loss.py --sweep --out "$RES/m2/packet_loss_sweep.csv" > "$RES/m2/packet_loss_sweep.log" 2>&1
$PY snr_sweep.py "$RES/m2/snr_sweep.csv"                               > "$RES/m2/snr_sweep.log" 2>&1
$PY freeze_buffer_test.py > "$RES/m2/freeze_buffer_test.txt" 2>&1 || true
$PY tag_leak_matrix.py    > "$RES/m2/tag_leak_matrix.txt"    2>&1 || true

# --- M3 experiments (E6-E10)
cd "$HERE/src/m3_experiments"
$PY e8_trigger_timing.py > "$RES/m3/logs/e8.log"  2>&1
$PY e8b_length_scan.py   > "$RES/m3/logs/e8b.log" 2>&1
$PY e6_multipath_snr.py  > "$RES/m3/logs/e6.log"  2>&1
$PY e7_cfo.py            > "$RES/m3/logs/e7.log"  2>&1
$PY e9_csi_sensing.py    > "$RES/m3/logs/e9.log"  2>&1
$PY e10_large_packets.py > "$RES/m3/logs/e10.log" 2>&1

# --- contribution tests
cd "$HERE/src/contribution"
$PY test_multipacket_regression.py 2>&1 | tee "$RES/m4/contribution_test_submitted_rerun.txt"
$PY pr8271_revision_prepared_not_pushed/qa_ofdm_txrx.py 2>&1 | tail -4 | tee "$RES/m4/contribution_test_revision_expectedfailure.txt"

# --- figures and summaries
cd "$HERE/src/analysis"
$PY make_m2_figures.py
$PY make_m3_figures.py
echo "Done. Compare Results/m3/summary_m3.md with the numbers in the report."
