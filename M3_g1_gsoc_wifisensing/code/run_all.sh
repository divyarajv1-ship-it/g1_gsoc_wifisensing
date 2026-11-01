#!/usr/bin/env bash
# Usage: bash run_all.sh   (set PY=python3.12 etc. to choose the interpreter)
# Re-runs every M3 experiment and rebuilds figures + Results/summary_m3.md (~25 min on a laptop).
set -e
cd "$(dirname "$0")/experiments"
mkdir -p ../../Results/logs
${PY:-python3} e8_trigger_timing.py   > ../../Results/logs/e8.log  2>&1
${PY:-python3} e8b_length_scan.py     > ../../Results/logs/e8b.log 2>&1
${PY:-python3} e6_multipath_snr.py    > ../../Results/logs/e6.log  2>&1
${PY:-python3} e7_cfo.py              > ../../Results/logs/e7.log  2>&1
${PY:-python3} e9_csi_sensing.py      > ../../Results/logs/e9.log  2>&1
${PY:-python3} e10_large_packets.py   > ../../Results/logs/e10.log 2>&1
${PY:-python3} ../contribution/test_multipacket_regression.py 2>&1 | tee ../../Results/contribution_test.txt
${PY:-python3} ../analysis/make_m3_figures.py
