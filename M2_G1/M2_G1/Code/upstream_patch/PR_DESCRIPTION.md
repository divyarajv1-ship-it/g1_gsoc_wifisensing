# Draft pull request to gnuradio/gnuradio (NOT yet submitted)

**Title:** digital: ofdm: add multi-packet loopback QA test, use rolloff in ofdm_loopback example

**Base branch:** `main` (request `backport-maint-3.10` label if maintainers agree)

## Description
Refs #6891.

`qa_ofdm_txrx.py` currently only tests single-packet transmission. The packet
drops reported in #6891 happen only between *consecutive* bursts, so no existing
test can catch them.

As @ffu explained in #6891, the Schmidl & Cox detector's plateau can put the
next packet's trigger a few samples early; if that lies inside the packet being
demultiplexed, Header/Payload Demux skips it. A TX rolloff separates the bursts.

This PR
1. adds `test_005_tx_multipacket_rolloff`: 100 back-to-back 50-byte packets,
   random payloads, `rolloff=4`, asserts every byte is received;
2. sets `rolloff: '4'` in `gr-digital/examples/ofdm/ofdm_loopback.grc`.

## Testing
- New test passes; the other 5 tests in `qa_ofdm_txrx.py` are unchanged and pass.
- Negative control: with `rolloff=0` the new test **fails** (`4850 != 5000`),
  so it really detects the drop.
- Measurements behind the choice of `rolloff=4` (500 packets × 5 seeds, ideal channel):

| TX setting | mean packet delivery |
|---|---|
| rolloff 0 (current example) | 95.9 % |
| rolloff 1 | 95.9 % (no effect) |
| rolloff 2 | 99.8 % |
| rolloff 4 | 100 % |
| 1 zero sample between bursts | 100 % |

  Identical losses occur when TX and RX run in one flowgraph and when the RX
  processes the stored TX signal afterwards, so the drops are not caused by
  scheduler chunking.
- Tested on: <OS>, GNU Radio built from `main` at <commit> (**fill in after building**).

## Checklist
- [ ] Built GNU Radio from source and ran `ctest -R qa_ofdm_txrx`
- [ ] Opened `ofdm_loopback.grc` in GRC, confirmed it runs
- [ ] Commits signed off (`git commit -s`)
- [ ] Python formatted (PEP8, `tools/check_pep8.sh`)
