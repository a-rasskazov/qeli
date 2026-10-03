# Q12: transports and wire camouflage

<!-- normative-sync: audit-q12-ws-read-v2 -->

Date: **4 October 2026**. **Q12 IN_PROGRESS**. WS write and HTTP/WS read batches passed; the section remains open. Current code: `19fed832`. Evidence: `release/certification/evidence/q12-ws-read-20261004.json`.

## HTTP Upgrade and inbound frames: 4 October

Batch **PASS**, code `19fed832`, evidence `release/certification/evidence/q12-ws-read-20261004.json`.
Changes live in shared protocol/obfs and apply to the server and all clients.

- **Q12-R001, P2:** the server accepted incomplete or malformed upgrades. The shared bounded parser now requires the exact GET/HTTP/1.1 request line, a nonempty singleton Host, version 13, valid field names/values and a singleton 16-byte base64 key. Critical duplicates, obs-fold, control bytes and ambiguous bodies are rejected. Content-Length may be absent or decimal zero; Transfer-Encoding is forbidden.
- **Q12-R002, P2:** the client accepted ambiguous 101 responses. It now validates the complete head and status line and rejects duplicate Upgrade/Accept and unoffered extensions/subprotocols. Accept remains challenge-bound. Multiple Connection fields remain supported; unused values may contain obs-text.
- **Q12-R003, P2:** a 4097-byte head passed when its last byte completed CRLFCRLF. The **4096-byte cap includes the terminator** and is checked before completion; direct head parsing uses the same cap.
- **Q12-R004, P2:** inbound frames accepted nonminimal length encodings. u16 starts at 126 bytes, u64 at 65536; the existing **16384-byte payload cap** remains. Thus u64 frames cannot pass this binary carrier's cap.
- **Q12-R005, P1:** a later malformed frame could hide bytes from earlier complete frames. Earlier payloads now drain before a latched failure, after which parsing cannot resume. This is delivery ordering, not an authentication bypass: inner PacketCodec still verifies each packet's AEAD.
- **Q12-R006, P2:** frame-boundary EOF was treated as clean while a fragmented message remained unfinished. It now yields latched UnexpectedEof. Completed fragmentation with an interleaved Ping remains compatible.

**9 baseline groups: 0 PASS / 9 FAIL** before fixes; **11 tests** added.
Fresh checks: **2335 Linux PASS / 60 ignored**, full/minimal Clippy and fmt;
**40 live Upgrade/frame probes** in two isolated WS fixtures, **39 WS** and
**24 REALITY-TLS/H2** assertions; **18-case matrix + aggregate IPv4/IPv6 leak**;
**100 TCP + 100 QUIC / 33 soak checks**; four independent native A/B builds,
consumer copies, exports and provenance. Working services and binaries preserved.

Bounded **ASan/libFuzzer, 60 seconds**, arbitrary requests and mutations of valid
upgrades: **1148461 runs**, no crash. Exact input hashes match qualified code;
original pre-commit identity retained separately. This is request-head fuzz, not
response/frame parser ASan coverage or a claim of exhaustive testing.
On .10 raw snapshot false is retained only for the previously documented three
legacy rules; every other field/service/executable matches. Full .11 snapshots match.

## Shared transport fixes

WS write batch,3–4 October:code `10849261`,evidence `release/certification/evidence/q12-ws-write-20261003.json`. The following fixes and checks refer to that batch.

- **Q12-W001, P1:** the writer advanced its cipher, owned the entire input and could emit a frame prefix before returning Pending. After cancellation and a changed input slice it emitted the old frame and returned its old length without accepting the new input. Accepted bytes are now owned and reported once through Ready; a later Pending operation accepts no new input. Whole and split streams use one writer state. A failure after partial emission is latched: subsequent write/flush/shutdown cannot continue the corrupted stream.
- **Q12-W002, P2:** the complete write slice was copied, encrypted and framed before socket transmission, without an ownership bound. Each poll now accepts at most16384 data bytes, plus the existing bounded queue of at most eight owed control replies.
- **Q12-W003, P1:** flush and shutdown only polled the underlying socket. Buffered frames and owed Pong/Close could remain unsent. Both stream forms now drain owned bytes and control replies before socket flush/shutdown. Daemon and shared client core use one write-all-and-flush helper at handshake, ACK and data/cover record boundaries before waiting for a response, publishing delivery or sleeping.
- **Q12-W004, P2:** an empty read polled the network and could stall. It now returns immediately without changing cipher or parser state.

Five baseline scenarios reproduced: **0 PASS / 5 FAIL**. Seven new tests cover
short writes, a cancelled Pending with a changed slice, bounded memory, control
flush/shutdown, empty reads, terminal socket failure and bidirectional exchange
through a **seven-byte** duplex buffer. Record boundaries matter: AsyncWrite
acceptance does not mean that the socket has transmitted the complete frame.

## Verification

- **2324 Linux tests PASS**, 60 ignored; full/minimal Clippy and fmt PASS. Intermediate failed builds with import/Clippy and Windows cfg diagnostics are retained;the helper was moved from Linux-only transport into portable protocol; the final fresh run uses corrected sources.
- First Linux r4 artifact: **10 private live cases / 199 assertions PASS**, TCP plain/fake-tls/obfs-none/obfs-ws/obfs-awg,WS resume and UDP QUIC/fake-tls/obfs/obfs-awg. After moving the byte-identical helper into portable protocol,the final r5 artifact passed **3 fresh WS success/resume + REALITY-TLS/H2 cases / 63 assertions**. Earlier results retain their original SHA and are not presented as a new run.
- Fresh **18-case** functional matrix and aggregate IPv4/IPv6 leak PASS; **100 TCP +100QUIC** path flips /33soak checks PASS.
- Four native libraries independently rebuilt A/B; A/B hashes,consumer copies,exports and provenance PASS. This does not establish new app E2E; physical Mac/router/Windows VM excluded by the user.
- Working services and binaries were not replaced. Full .11 snapshots match. On .10 only the previously recorded three legacy firewall rules may differ, retaining raw false; all other fields,service and executable must match. Their cause remains unattributed.

No fresh ASan campaign,PCAP,throughput benchmark or DPI resistance is claimed for
this batch. Functional exchange does not establish wire indistinguishability.
WebSocket requirements use [RFC 6455](https://www.rfc-editor.org/rfc/rfc6455).

## Remaining Q12 work

Remaining: Close lifecycle/control-response guarantees, structured inbound-frame fuzz,
parameter/wire-mode matrix review and remaining QUIC/AWG contracts.
HTTP Upgrade/head caps, minimal frame lengths, fragment EOF and prior payload delivery
before failure passed the 4 October batch. Overall: **11/37 DONE/PASS (29.7%)**.
