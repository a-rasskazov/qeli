# Q13: recordizer, padding and shaping — shaping fix batch

<!-- normative-sync: audit-q13-shaping-v1 -->

**4 October 2026. Batch: PASS. Q13: IN_PROGRESS.** Overall **12/37 DONE/PASS (32.4%)**.
This does not complete the entire audit. Source: `82c1ad770a6fa43302263babd67dab4e41043e9b`; Linux candidate: `d68bb6dab55234454821a22da1342469759a5d39aaa2c6915781acddddf4d10b`.
All compilation input hashes match this commit; original pre-build identity is retained.
Independent native builds use the clean source commit.

## Fixes

| ID | Problem and resulting behavior |
|---|---|
| Q13-S001 | P1: pacing discarded its final pause of up to 6 ms. One shared scheduler now waits for the entire deadline and counts slow cover writes towards it. Two active TCP writers and two currently disabled UDP branches use it. |
| Q13-S002 | P2: streams sampled time before locking; a stale timestamp moved the shared cover refill clock backwards and generated another refill. The clock now remains monotonic. |
| Q13-S003 | P2: local INI refused inactive `shaping_stealth_mbps = 0` while AuthOK preserved it. INI now retains the dormant value; active stealth still requires a positive rate. |
| Q13-S004 | P2: local INI accepted active 65535-byte cover, exceeding the common record ceiling. INI and AuthOK now share the active shaping validator and bounds. |
| Q13-S005 | P1: client data rate was per bonded TCP stream. All writers now reserve one aggregate direction budget; server rate accounting was already aggregate. |

A TCP cover write failure now terminates the writer rather than merely leaving its
inner pacing loop and trying to send data. Wire format and INI keys are unchanged.
Cover has a separate budget that meters padding bytes, not total interface traffic.

## Verification

- Five baseline assertions FAIL; **7 new tests**. **2359 Linux PASS / 60 ignored**,
  full/minimal Clippy and fmt PASS. Test-import and Send-wrapper compile failures
  are retained; corrected sources passed the complete fresh execution.
- Shipping release rlib campaign: **10000 roundtrips,40000 inner packets,40000 malformed
  records,622431 assertions PASS**, covering fragment/inflight/byte caps, duplicates,
  conflicts, budget recovery and expiry. Peak RSS **11128 KiB**. This is a bounded
  invariant campaign, not ASan/libFuzzer or exhaustive coverage.
- **10 network cases /102 assertions PASS**: TCP off/prefer/required, idle cover,
  stealth,three bonded TCP streams,and UDP recordizer/legacy. Identical post-load
  IPv4 pings have no loss; idle cover gaps vary in both directions.
- Fresh **18-case matrix /327 assertions**,aggregate IPv4/IPv6 leak and
  **100 TCP +100 QUIC path flips /33 soak checks PASS**;separate **24 REALITY-TLS/H2 checks**.
- Independent Windows x64,macOS universal,Android arm64/x64 A/B artifacts,consumer
  copies,exports and provenance PASS. This is not fresh installed application E2E;
  Mac/router/Windows VM runtime was excluded by the user.
- Full .10/.11 snapshots,active services and executables preserved;no replacement.

## Measurements on this lab

Identical directional iperf workload:6 seconds plus a separate warm-up second.
The three-bonded-stream case offers three parallel inner TCP flows.

| Mode | Upload,Mbps | Download,Mbps |
|---|---:|---:|
| TCP required,shaping off | 1041.93 | 1572.58 |
| TCP required,idle cover | 1480.05 | 1563.94 |
| TCP stealth 2Mbps,single stream | 1.89 | 1.92 |
| TCP stealth 2Mbps,three streams aggregate | 1.81 | 1.75 |

This is a local virtual topology,not a WAN benchmark. Uncapped measurements vary
with CPU/capture load;the idle-cover comparison does not demonstrate acceleration.
The rate result establishes that stream count does not multiply the cap;startup
credit may still permit a burst.

UDP **deliberately retains idle cover only**:both peers disable stealth. The first
fixture incorrectly expected a UDP cap and stopped. Eight PASS cases were retained;
only the two remaining cases reran against the documented TCP-only contract. This
was a fixture error,not a product regression or new UDP feature.

Header PCAP retains timestamps,original wire lengths and packet headers. The first
full captures retain source/derived transform hashes;only verified inactive remote
copies were reclaimed,local evidence remains. Ciphertext bodies are unnecessary
for this analysis. No vendor DPI resistance or universal absence of periodicity is claimed.

## Evidence and next work

Registry:`release/certification/evidence/q13-shaping-20261004.json`.
Raw:`../audit-debt-20260924/q13-shaping-20261004` relative to the audit worktree.

Next within Q13:recordizer/reassembly semantics,combined padding/normalization,
dormant UDP stealth branches and extreme timer review. This batch's five fixes
were verified immediately;the remaining section is not marked DONE.
