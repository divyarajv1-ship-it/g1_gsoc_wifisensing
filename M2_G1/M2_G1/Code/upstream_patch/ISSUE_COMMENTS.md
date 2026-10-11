# Draft comments for the GNU Radio issue tracker (NOT yet posted)

Post only after every team member who signs it can explain the numbers.

---
## Comment for #6891

Hi all, we are a student team (ECE 310, Ahmedabad University) who measured this
with GNU Radio 3.10.12.0. Each packet carried a sequence number, so we counted
exactly which packets were lost (500 packets × 5 seeds, 50-byte packets).

- Default TX (rolloff 0): ~4.1 % of packets lost with an ideal channel.
- The losses are **identical** whether TX and RX run in one flowgraph or the RX
  runs afterwards on the stored TX signal, which supports @ffu's explanation
  (plateau timing + Header/Payload Demux), not a scheduler effect.
- rolloff 1 has no effect, rolloff 2 → 99.8 %, rolloff 4 → 100 %;
  one zero sample between bursts → 100 %.
- With AWGN, the default setting gets *worse* with more SNR (99.6 % at 15 dB,
  94.4 % at 30 dB): noise randomises the plateau and partly hides the bug.

Since the existing QA only tests single packets, we would like to open a PR
adding a multi-packet regression test and setting rolloff=4 in the example.
Would that be welcome? Scripts and data: <link to our repo>

---
## Comment for #7997

Hi @Arian-Taheri-12 and @vamsip-cell, we don't want to duplicate your work, so
here is one observation that may help.

In GNU Radio 3.10 we can reproduce *the same symptom* (every block stops, no
error is raised from `run()`) in two ways with the stock OFDM blocks:

1. A packet/frame larger than a tagged-stream block's output buffer: the block
   logs `Buffer too small for min_noutput_items`, its thread exits, and all
   other blocks wait forever (≥300-byte packets with default buffers; fixed by
   raising the min output buffer).
2. A TX length tag reaching an RX that uses the same tag key: Header/Payload
   Demux fails with the same message (fixed by `block_tags=True` in the Channel
   Model or a different RX key).

Could you check whether your console shows `Buffer too small for
min_noutput_items` when it freezes, and share the .grc (or the custom
pilot_inserter's `forecast()`/`general_work()`)? Inserting the Channel Model
changes tag propagation and buffer allocation, so it could trigger case 1 or 2.
Our test scripts: <link to our repo>
