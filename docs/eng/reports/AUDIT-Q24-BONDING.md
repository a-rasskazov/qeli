# Q24: multipath, bonding and shared budgets

<!-- normative-sync: audit-q24-bonding-v2 -->

**IN_PROGRESS. Overall plan: 23/37 (62.2%).** 4 October 2026.
[Evidence](../../../release/certification/evidence/q24-bonding-20261004.json).

## Q24-F001: one stalled carrier stopped healthy flows (P2)

The isolated Linux baseline delivered 480/480 UDP echoes across 16 inner flows.
After blackholing one secondary TCP carrier and starting a bounded UDP flood,
only 11 echoes arrived; the last five seconds received zero. Removing the rule
restored traffic without replacing the process or TUN.

The client's 4096-entry queue retained TunPacket values from the small shared pool.
A stalled writer could exhaust it, stopping TUN reads for the other carriers.
The server queue could likewise retain its entire shared 4 MiB wire pool.

The common core now snapshots bonded uplink into one fixed 4 MiB pool. Queues
retain PooledBuffer, immediately releasing native TUN packets, including FIFO
Wintun reservations. Each queue receives a share of the budget, leaving room
for other streams and a temporary resume candidate. There is no fallback allocation;
overload drops the packet. Server queues use the same share calculation.
Single-stream TCP keeps its former path. No new INI option, wire format or public ABI.

## Layer review

Reviewed primary AUTH/server push, bearer and authenticated JOIN proofs, fresh
transcript/epoch, stream caps, atomic admission/revocation, fixed/adaptive actors,
logical-slot scheduling, IPv4/IPv6 fragment affinity, independent directional rate
buckets, shared cover/stealth budgets, quota counters and task/socket release.
Bearer JOIN remains necessary for compatibility; no confirmed dead production
code was found in this pass.

The manual now describes the 1–16 range, fixed targets with retries, adaptive
three-second ramp with no downscaling, negotiated stable slots versus legacy
modulo scheduling, and the fact that one inner flow is not striped across carriers.

## Qualification and remaining work

The production fix is qualified: 2407 full-feature Linux units PASS/60 ignored,
strict Clippy and release PASS. Twelve fresh isolated current-binary Linux
scenarios pass 283 checks. The old baseline has zero last-half echo replies in
both directions; fixed receives450 each. Shared8Mbps cap yields6.466312–7.777372Mbps.
This is not a peak-throughput benchmark.

Four fresh independent native A/B pairs PASS, canonical/consumer copies match;
22 actual Windows ABI/runner and C11/C++11 header checks PASS. Actual Android
JNI calls on the new x86_64 library pass23/23. First private AVD initialization
adds two base userdata files while preserving the original seed exactly; raw
whole-fixture rc1/userdata_preserved=false is retained. Repeated cold boot on
the initialized AVD times out at240/480seconds before JNI. It is not counted PASS;
Q24 remains open, overall23/37(62.2%).

The .10 fallback has2GiB RAM/2GiB swap. Emulator37.2.12 forces2560MiB guest RAM
and6GiB userdata. Missing libraries were extracted privately; inactive compiler
caches cleared with all mapped files and working executable preserved. The
private SDK was archived/restored for build capacity. .11 provides no SSH banner;
its final host state is unverified. Mac/iOS/router/Windows VM network runtime
remain user exclusions. No installed-app/physical E2E, deployment or push.

The width fixture and bounded18-second impairment/phase logs were corrected.
Only exact three accepted ambient legacy rules may differ; raw host_restored
values remain. Profiles are INI-only; service/API JSON remains allowed.
