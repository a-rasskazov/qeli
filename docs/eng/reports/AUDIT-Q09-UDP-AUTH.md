# Q09: UDP AUTH ownership and pre-authentication PMTU

<!-- normative-sync: audit-q09-udp-auth-v1 -->

Date: **3 October 2026**. Code: `616cb54b`. This fix batch is qualified;
Q09 overall remains **IN_PROGRESS**. [Evidence](../../../release/certification/evidence/q09-udp-auth-20261003.json).

## Findings and fixes

| ID | Priority | Before | Fix and verification |
|---|---|---|---|
| Q09-F001 | P2 | Both carrier PMTU branches checked address-entry existence although comments promised an authenticated peer. AwaitingAuth, unsent AuthOK and revoked entries could receive ACKs before the shared state checks | Shared `pmtu_reply` requires Authenticated, AuthOK and non-revoked state before sending or consuming a QUIC packet number. Real UDP/QUIC sockets compare baseline and fixed releases |
| Q09-F002 | P1 | An off-loop AUTH task retained a source address while reaping or pending-cap eviction could remove its handshake during tarpit/Argon2. The delayed verifier could then remove or configure a replacement at that address | `UdpAuthLease` reserves the specific handshake under the directory lock before spawn. Reaping, capacity eviction and receive-side revoked removal preserve the reservation; duplicate AUTH cannot start another task. Drop releases it on completion, cancellation or rejected spawn |

This is a confirmed state-ownership defect; a successful remote password bypass is
not claimed. If all 1024 half-open slots are reserved, new handshakes are dropped for
retry without exceeding the cap.

UDP AUTH verification, Argon2-gate waiting and tarpit now consume the remaining
`perf.connection.handshake_timeout_secs` measured from handshake creation. Retries
receive no fresh budget. The reservation remains through admission/AuthOK sending;
no timeout was added around the entire transaction after resource allocation.
An already-running blocking Argon2 job finishes with its concurrency permit:
cancelling its waiter does not prematurely admit another blocking job.

## Final-batch verification

- **2283 Linux units PASS**, 0 failed, 60 explicitly ignored. Four new regressions cover PMTU state/order/revocation, ownership/cancellation, rejected spawn and original deadline.
- Pinned full/minimal Clippy and rustfmt PASS. Linux jemalloc release: `406cbb794521d8cbbf4bcd3929b4258c34e59bfee3dbe00a785331ac864aff48`.
- **16 real UDP/QUIC checks**: a proxy forwards an actual Qeli ClientHello, withholds all ServerHello fragments and prevents AUTH. Both PMTU formats receive baseline Q08 ACKs and no fixed-release ACKs.
- **35 admission E2E checks PASS**: TCP/UDP same-device, fixed IPv4, session cap, profile scope, teardown and actual tunnel packets. No forced live reaper race is claimed; ownership is qualified by review and deterministic ownership/cancellation tests.
- Fresh **18 release cases / 327 assertions**, aggregate leak and **100 TCP + 100 QUIC / 33 soak checks PASS** on the same SHA.
- Four native core A/B pairs, ABI, consumed copies and provenance PASS. These server changes are excluded from native targets; all four binaries remained byte-identical while metadata was updated to current sources.
- Complete lab snapshots, PID/start and working executables preserved. No service replacement, push, deployment or new benchmark.

Raw logs, source/fixture hashes and retained artifacts:
`audit-debt-20260924/q09-handshake-20261003` beside the worktree. Fixtures contain no secrets.

## Remaining Q09

The next batch covers TCP pre-authentication deadlines/admission saturation, UDP
anti-amplification coverage, truncation/replay/reordering/slow peers, incorrect
PQ/proof/password, capabilities/downgrade and handshake parser/fuzz coverage. Two fixes
do not close the entire section; required verification for **this** batch is complete.
Physical-platform status and earlier Q08 limitations are unchanged.
