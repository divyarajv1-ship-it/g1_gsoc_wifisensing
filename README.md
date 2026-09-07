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

Initial scoping / M1
