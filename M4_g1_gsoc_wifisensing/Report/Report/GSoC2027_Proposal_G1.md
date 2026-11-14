**GSoC 2027 Proposal: Reliable, CSI Producing OFDM Receiver for GNU Radio** 

Refined proposal (ECE 310 Milestone 4, Team G1). Organisation: GNU Radio 

| Skills  | Python, C++, DSP (OFDM, synchronisation, channel estimation), GNU Radio blocks, unit testing |
| :---- | :---- |
| Applicant  | One applicant per proposal (GSoC is individual). Each member who applies copies this proposal and fills in Section 10\. |
| Potential  mentors | Ask on the GNU Radio Matrix chat / Discourse before naming anyone. Candidates: gr-digital reviewers and the maintainers active on \#6891 and \#8271. |
| Before  submitting | Check the official GNU Radio GSoC 2027 ideas list; align with a listed idea or get a mentor's OK for this one. |

**1\. Synopsis** 

GNU Radio's generic OFDM transmitter/receiver ( gr-digital ) is where students, researchers and many Wi-Fi-sensing experiments start. Our measurements show that it fails **silently** in three ways: (1) about 4 % of back-to-back packets are dropped on a perfect channel and up to 11.5 % on multipath (\#6891); (2) flowgraphs freeze without an exception when a frame does not fit a block's buffer (the symptom in \#7997); (3) packets of 1020 bytes or more are never transmitted, and the flowgraph ends normally with zero output. The receiver also computes an accurate per packet channel estimate (CSI) but does not expose it. 

This project will: **(a)** fix the multi-packet drop **in the receiver**; **(b)** turn the silent failures into clear errors or graceful drops, with tests; and **(c)** add a supported per-packet CSI output (with packet number and timestamp) plus an example that writes a CSI dataset from a configurable multipath channel. Together, these make GNU Radio a reliable, open CSI source for Wi-Fi-sensing 

research. 

**2\. What changed since the M3 draft (and why)**

| M3 draft  | Refined (M4)  | Reason |
| ----- | :---- | :---- |
| Three receiver  options, TX rolloff as a fallback  "documented  default" | **Receiver fix only.** The TX-rolloff fallback is removed | Maintainer review of PR \#8271: changing the rolloff "hides a bug". A TX default does not help users whose bursts come from other transmitters |
| Test PR in weeks 1–2  | The multi-packet test is already submitted in our one pull request, PR \#8271 (open). A revision with expectedFailure is prepared and will be pushed to the same PR after the maintainer confirms. Weeks 1–2 build the full benchmark matrix | Gives the fix a ready acceptance test. Removing the  expectedFailure decorator  becomes the measurable goal at midterm |

| M3 draft  | Refined (M4)  | Reason |
| :---- | :---- | :---- |
| Prior-work links  missing | Filled in (Section 4\)  | Our issue comment on \#6891 and our one pull request (\#8271) now exist |
| Generic risks  | Risks tied to the actual review feedback  | Section 8 |

**3\. Benefits to the community** 

Every user of ofdm\_loopback.grc and ofdm\_tx / ofdm\_rx gets a receiver that does not silently lose packets, whatever the transmitter does. 

Clear errors replace hangs that currently cost users hours (\#7997). 

Regression tests for multi-packet operation, large frames and buffer limits protect future changes, including the GNU Radio 4.0 port. 

A per-packet CSI output opens GNU Radio to the Wi-Fi-sensing community, which today depends on closed chip-specific CSI tools. 

**4\. Evidence of prior work (ECE 310 project, 2026\)**

| Item  | Link / location |
| :---- | :---- |
| Measurements on \#6891  | https\://github.com/gnuradio/gnuradio/issues/6891\#issuecomment 6787055390 |
| Our only pull request so far: first multi-packet OFDM QA test | https\://github.com/gnuradio/gnuradio/pull/8271 (submitted 11 Nov 2026; open; maintainer asked a question on 12 Nov; revision prepared, not pushed yet) |
| Scheduler ruled out (streaming \= offline, 5/5 seeds) | M2 report, team repository |
| Sample-level model: packet lost iff its trigger is \< frame\_len − 1 samples after the last used trigger; predicts every loss in 100/100 runs | M3/M4 report, e8\_trigger\_timing.py , e8b\_length\_scan.py |
| TX workaround evaluated over 4 multipath profiles × 5 SNRs, CFO ≤ 3.5 subcarriers, 2 GNU Radio builds | M3/M4 report Section 6.4 |
| CSI from ofdm\_chanest\_vcvc : −19 dB NMSE at 15 dB SNR, −34 dB at 30 dB; 7–9 % CSI samples missing; 7–8 % sensing bias | M3/M4 report Section 6.5 |
| Freeze and ≥ 1020 B refusal reproduced | M3/M4 report Section 6.6 |
| Team repository  | https\://github.com/divyarajv1-ship-it/g1\_gsoc\_wifisensing |

**5\. Technical plan** 

**5.1 Receiver-side fix for multi-packet drops (core)** 

**Current behaviour.** header\_payload\_demux ignores a trigger that falls inside the frame it is consuming. With touching bursts, the Schmidl & Cox plateau trigger lands 69–73 samples after the true burst start, so a trigger 1–4 samples early loses the packet. 

**Options to prototype and compare (decision with mentors by week 4):** 

1\. **Early-trigger tolerance** in header\_payload\_demux : accept a trigger that falls in the last k samples of the current frame and re-align the next frame start. Smallest change; must not break users who rely on the current behaviour (default k to be agreed). 

2\. **Fine timing refinement** after detection: cross-correlate with the known second sync word to place the trigger consistently, before the demux. Keeps the demux unchanged; costs CPU. 

**Acceptance criteria.** With rolloff=0 at the TX: PDR \= 100 % on the test matrix (lengths 20– 1000 B; flat, mild, indoor and harsh multipath; CFO ≤ 3.5 subcarriers; SNR ≥ 25 dB); the expectedFailure decorator on the \#8271 test can be removed; no regression in existing QA tests; CPU cost measured and reported. 

**5.2 Loud failures instead of silent ones** 

header\_payload\_demux : a maximum-payload-length check (the source notes "There is currently no 'max payload len' param"). Drop the frame and log a warning instead of killing the thread. 

> Tagged-stream blocks: when a packet cannot fit the buffer, raise a clear error naming the block, the requested and available sizes and the fix ( set\_min\_output\_buffer ), and stop the flowgraph instead of hanging. 

> ≥ 1020 B TX refusal ( tagged\_stream\_mux , max 8191 items available): fix the buffer sizing or document a hard limit with an explicit error. Report as a new issue first, with our reproducer. Tests that assert an error or warning instead of a hang, with a watchdog so CI never blocks. 

**5.3 Per-packet CSI output** 

Optional message port on ofdm\_rx that emits, for every detected frame, a PMT dict: {packet\_num, sample\_offset, carrier\_offset, csi (c32vector over occupied carriers), header\_ok, crc\_ok} . 

Example ofdm\_csi\_dataset.py / .grc : TX → configurable multipath \+ Doppler channel → RX → CSI file in a documented NumPy/HDF5 layout compatible with SenseFi-style pipelines. Validation: CSI vs ground-truth \|H(f)\| NMSE vs SNR (as in our E9). Lost packets are reported explicitly, so sensing pipelines can use correct timestamps. 

**5.4 Documentation** 

A tutorial page, "OFDM packet reliability and CSI in GNU Radio", covering the measurement method (sequence-numbered packets, watchdog, trigger logging, replay model) and the new CSI output.  
**6\. Timeline and milestones (12 weeks \+ community bonding)** 

Everything in this table is **planned work for GSoC 2027**. None of it has been done or submitted yet. So far the team has submitted one pull request (\#8271) and one issue comment (\#6891). 

| Period  | Work  | Deliverable / milestone |
| :---- | :---- | :---- |
| Community  bonding | Agree design options with mentors; source build of main ; finish the review of our existing PR \#8271 | Design note |
| Weeks 1–2  | Port our harness to the test-matrix benchmark (lengths × channels × CFO × SNR) | Benchmark scripts and QA tests |
| Weeks 3–5  | Prototype options 1 and 2; measure PDR and CPU on the matrix | Comparison report; mentor decision (week 4\) |
| Week 6  | Implement the chosen fix in C++ with QA tests; remove expectedFailure | Receiver fix with tests  (midterm goal) |
| Weeks 7–8  | Loud failures (5.2); new issue \+ fix/limit for ≥ 1020 B  | Clear errors instead of  freezes, with tests |
| Weeks 9–10  | CSI message port \+ dataset example (5.3)  | CSI output and dataset  example |
| Week 11  | CSI validation; tutorial page  | Tutorial page; blog post |
| Week 12  | Review changes; final report  | Final evaluation |

**7\. Expected deliverables (planned for GSoC 2027\)** 

1\. The multi-packet regression test from our existing PR \#8271, finished with the maintainer, and a benchmark/test matrix. 

2\. A receiver-side fix for \#6891 with tests and measurements; ofdm\_loopback.grc works with the default rolloff. 

3\. Errors or graceful drops instead of silent freezes; resolution of the ≥ 1020 B refusal. 4\. Per-packet CSI output on ofdm\_rx and a CSI dataset example. 

5\. Tutorial documentation and a final report. 

**8\. Risks and mitigation**

| Risk  | Mitigation |
| :---- | :---- |
| Maintainers do not want a behaviour change in header\_payload\_demux | Option 2 (timing refinement) leaves the demux unchanged; decide by week 4 |
| C++ changes are slow to review  | Small, separate changes, each with tests and numbers; tests first |
| CSI output API debate  | Start as an example or out-of-tree block; propose in tree only after feedback |
| GNU Radio 4.0 priorities  | Keep tests runtime-agnostic; note which results transfer to GR4 |
| No hardware  | All acceptance criteria are simulation-based; hardware is a stretch goal |

**9\. Stretch goals** 

Repeat the reliability matrix on SDR hardware (PlutoSDR/USRP) or in GNU Radio's hardware in-the-loop CI. 

Port the multi-packet test and CSI example to GNU Radio 4.0. 

Apply the trigger-logging method to gr-ieee802-11. 

**10\. About the applicant (each applicant fills this in)** 

Name, Ahmedabad University, B.Tech programme and year, time zone IST (UTC+5:30) Availability: hours per week, exam dates, other commitments 

Relevant courses: ECE 310 Wireless Communications, Signals and Systems, … Programming experience (Python, C++), GitHub profile, open-source activity (link PR \#8271 if you were involved) 

Why GNU Radio, and why this project 

**11\. Communication plan** 

Weekly mentor call; progress on the GNU Radio Matrix chat and Discourse; a public development blog; all work done in public on GitHub.