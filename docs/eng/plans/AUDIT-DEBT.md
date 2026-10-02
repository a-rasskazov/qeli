# Technical debt from started audits

<!-- normative-sync: audit-debt-v63 -->

Reconciled on 2 October 2026. At the user’s request, new full-audit sections
are paused until this register is closed. These are **15 groups of obligations**,
not 15 confirmed bugs or a completion percentage for all 37 sections. Sources: 57 baseline
`AUDIT-Q*.md` reports and `CLIENT-CONFIG-CORE.md`; repeated limitations are consolidated.

`DONE` requires a fix/justification and the required verification. `BLOCKED` denotes an
unavailable external prerequisite, never success. The user supplied Linux and an Android
emulator on 24 September; the historical “no Linux environment” limitation is obsolete.
Connections to both Linux VMs were verified; the running server and its files were not replaced.

[Full plan](FULL-SYSTEM-AUDIT.md) · [Shared configuration core](CLIENT-CONFIG-CORE.md)

| ID | Sections | Status | Debt | Closure criteria / current evidence |
|---|---|---|---|---|
| D01 | 14/17/18/25 | DONE | NAT and retired-generation failures | Retain exact rules before mutation; retry and final failure; prevent restart after incomplete cleanup; release IPv4 forwarding. Unit/cross, 18 native and 8 worker E2E PASS; baseline IPv4 leak reproduced. [Report](../reports/AUDIT-Q14-RETAINED-CLEANUP.md). |
| D02 | 14/25 | DONE | Internal sysctl boundaries | Lock/I/O/context, trusted directory, namespace fd pins, original per-interface fd/witness and v4 network_cookie verified. 1995 Linux + 32 privileged + 8 lifecycle and SIGKILL/mismatch worker E2E PASS. Lost interface witness stays for manual recovery; general persistent firewall/DNS/routes remains D04. [Report](../reports/AUDIT-Q25-NAMESPACE-GENERATION.md). |
| D03 | 22/25 | DONE | Standalone kill switch | Pinned namespace, retained exact-family owner, fail-closed reconnect and safe address rotation. 11 portable + 2 native regressions; actual IPv4/IPv6 filter counters and 2 baseline failures. [Report](../reports/AUDIT-Q25-KILL-SWITCH-IDENTITY.md). |
| D04 | 14/19/22/25 | DONE | Crash recovery | Persistent server firewall, DNS v2, kill-switch and physical routes verified; legacy global DNS, persistent TUN and lost sysctl witnesses have explicit safe manual boundaries. [Client mixed matrix](../reports/AUDIT-Q25-CLIENT-MIXED-FIREWALL.md): 152/152 cells, 136 crash/recovery; [server](../reports/AUDIT-Q14-MIXED-FIREWALL.md): 16/16, 476 checks rerun PASS. Additional multiprofile/public-policy reload is closed by D10/Q25-F213; state accumulation is covered by D13. Arbitrary policies/root rewrites are not certified. |
| D05 | 05/14/25 | DONE | Whole-operation deadlines and blocking | Panel preflight/health/backup, DNS/NSS, resolver files, startup INI/identity, TOFU/status writers and network workers checked. Batch A below closes command composition: 15 seconds for NetworkPlan and separate shared 15 seconds for cleanup through Drop and terminal firewall. Linux early-Drop/internal waits reconciled; hook/backup file preparation is closed by the continuation below; ordinary server startup/final cleanup and profile teardown now use joined workers; profile TUN/NAT and DNS firewall setup now also use joined workers; NDP bind now also runs on a worker, with AsyncFd registration in the original runtime; setup through readiness of every listener now has a shared 120-second budget; replacement admission after cancellation is closed by [Q25-F130](../reports/AUDIT-Q25-SERVER-FORCED-DROP-LEASE.md); async joining on forced Drop is closed by Q25-F206 below; Q25-F208 closes total CLI shutdown and concurrent notification drain: 45-second worker budget, forced exit 124, recovery, 136 unit and 8 lifecycle PASS. Library/kernel boundaries are justified. [Server setup](../reports/AUDIT-Q25-SERVER-SETUP-WORKER.md), [DNS firewall](../reports/AUDIT-Q25-SERVER-DNS-SETUP-WORKER.md), [NDP bind](../reports/AUDIT-Q25-SERVER-NDP-BIND-WORKER.md), [readiness and budget](../reports/AUDIT-Q25-SERVER-SETUP-BUDGET.md). Arbitrary kernel/fs I/O and forced joins are not preempted. [Server cleanup](../reports/AUDIT-Q25-SERVER-CLEANUP-WORKER.md). [Worker ownership](../reports/AUDIT-Q25-IDENTITY-WORKER.md). |
| D06 | 15/21/22/23/25 | IN_PROGRESS | External network-resource context | Verify WAN identity, resolved/bus context, sysfs/procfs and attach/name contracts; process-global DNS/carrier state and dynamic IPv6. Document supported combinations. [Q15-F002](../reports/AUDIT-Q15-UDP-LOCAL-ADDRESS.md) closes multi-IP wildcard UDP: the local endpoint survives receive/reply/roaming/PMTU; [Q25-F131](../reports/AUDIT-Q25-SERVER-WAN-PRESENCE.md) rejects managed IPv4/IPv6 rule setup for an absent WAN; it does not bind active rules to device identity. [Q25-F132](../reports/AUDIT-Q25-SERVER-WAN-ECMP.md) shares the client default-route parser with the server and rejects ambiguous auto-WAN before forwarding/new rules. Q25-F134/F135/F136 cover NAT66/NAT44 off-WAN guards and strict auto-WAN discovery; detailed remaining context is reconciled below. Q25-F214 below: 73 portable + 23 privileged PASS; mixed-backend late IPv4/IPv6 gap closed, DNS/sysfs/attach/process admission reconciled. Q25-F215 below closes documented server default/policy route and RFC1918/CGNAT/public-LAN composition: 4 mixed cells/204 packet checks PASS; continuous WAN identity/client WAN monitor reconciliation remain open. |
| D07 | 01/05/09/11 | DONE | Server configuration at runtime | Trace field → parse/validate/runtime/serialize; malformed/oversized input; check-config/startup/SIGHUP/HTTP save/Quick Start preserving active state on failure. [Q25-F137](../reports/AUDIT-Q25-SERVER-SIGHUP-AUTH.md) through [Q25-F149](../reports/AUDIT-Q25-SERVER-TLS-PATH-TRUST.md) cover targeted SIGHUP, size, live web state, private INI publication, admission parity, file-path trust, coordinated panel/CLI/restore writes, bounded TLS PEM intake, check-config TLS parity, explicit TLS path trust, and Let's Encrypt panel saves. [Q25-F150](../reports/AUDIT-Q25-SERVER-PANEL-SNAPSHOT-TRUST.md) closes panel identity/Share/users trust bypasses after manual INI edits. [Q25-F151](../reports/AUDIT-Q25-SERVER-PANEL-SAVE-TRUST.md) blocks trust promotion through panel saves, history, and archive commands. [Q25-F152](../reports/AUDIT-Q25-SERVER-FIELD-MATRIX-LOGGING.md) checks parse/serialize coverage of 150 fixed INI keys and requires a full restart for three active logging fields. [Q25-F153](../reports/AUDIT-Q25-SERVER-WEB-AUTH-SAVE.md) rejects an enabled panel without a password or explicit insecure_no_auth in both editors and history restore. [Q25-F154](../reports/AUDIT-Q25-SERVER-QUICKSTART-BF-SAVE.md) extends the guard to Quick Start and lockout-policy saves, validates the complete BF candidate before SIGHUP, and reports INI read failures or a pending worker reload. [Q25-F155](../reports/AUDIT-Q25-SERVER-SIGHUP-RESTART-HINTS.md) removes false warnings for disabled profiles and reports unapplied SIGHUP changes to live profiles, two auth flags, and three logging fields. [Q25-F156](../reports/AUDIT-Q25-SERVER-WEB-HASH-VALIDATION.md) validates a nonempty admin hash at check-config/startup and preserves working login after an invalid live reload. [Q25-F157](../reports/AUDIT-Q25-SERVER-WEB-RELOAD-RESULT.md) separates INI publication from successful panel application and prevents a partial lockout-policy swap when reload is cancelled. [Q25-F158](../reports/AUDIT-Q25-SERVER-BLOCKED-LIVE.md) applies the panel lockout policy through live web reload, exposes saved/active divergence, and avoids a false password rejection for a disabled panel. [Q25-F159](../reports/AUDIT-Q25-SERVER-INI-ORDER.md) stabilizes INI ordering of groups, IPv4/IPv6 reservations, and user metadata. The 2026-10-01 batch rejects empty profile sets through the shared validator and checks panel authentication and existing TLS PEM files before a full restart; 74 tests and strict Clippy passed on `.11` (2 namespace tests ignored). The second batch aligns `check-config` and startup with panel refusal when `web.enabled = true` has no password; 152 server/panel tests and strict Clippy passed on `.11` (2 namespace tests ignored). The next batch requires `expected_revision` for Quick Start, form, INI and history restore; older API scripts were updated, with 37 editor tests, formatting and strict Clippy passing on `.11`. The [global field matrix](../reports/AUDIT-Q25-SERVER-GLOBAL-FIELDS.md) traces parse/validate/runtime/apply for 34 auth/web/logging keys; the fixture generator confirms 163 names and three dynamic families. The [foundational profile matrix](../reports/AUDIT-Q25-SERVER-PROFILE-FOUNDATION.md) traces 63 non-obf.* entries and fixes the silent cap on explicit tun.queues above 256. The [obf.* matrix](../reports/AUDIT-Q25-SERVER-PROFILE-OBF.md) traces the other 59 keys and fixes REALITY share-link SNI. [Q25-F160](../reports/AUDIT-Q25-SERVER-BLOCKED-REVISION.md) also requires an INI revision for lockout-policy saves. [Q25-F161](../reports/AUDIT-Q25-SERVER-ARCHIVE-SCAN.md) stops silently skipping directory-entry errors during archive restore. [Q25-F162](../reports/AUDIT-Q25-SERVER-NOTIFY-INI.md) removes notification JSON migration and bounds notify.ini reads/writes. [Q25-F163](../reports/AUDIT-Q25-SERVER-NOTIFY-REVISION.md) guards notify.ini saves against stale tabs. Q25-F209 below closes mixed save/reload/import: 201 unit, 4 privileged executions and 44 runtime checks PASS; external writers ignoring the shared lock are explicitly unsupported, with rationale in the manual. [Q25-F190](../reports/AUDIT-Q25-SERVER-INI-HISTORY.md) makes INI history listing and rotation report I/O failures; Windows rustfmt and 1551 portable tests PASS, with targeted server tests and mixed Linux runtime rechecked in Q25-F209. |
| D08 | 02/24/27 | DONE | Shared client configuration | Verify the complete 81+3 field contract, INI/import/URI/QR/form/store/reconnect through real adapters; fuzz/budget and concurrent edits. [Q25-F164](../../ru/reports/AUDIT-Q25-CLIENT-PROFILE-REVISION.md) protects panel INI against stale tabs, manual edits and name collisions on import; [Q25-F165](../../ru/reports/AUDIT-Q25-CLIENT-PROFILE-BOUNDS.md) bounds autostart/status reads and serializes Connect/Delete with saves. [Q25-F166](../../ru/reports/AUDIT-Q25-CLIENT-DELETE-REVISION.md) requires a revision before Delete and reports when a saved running client needs reconnect. [Q25-F167](../../ru/reports/AUDIT-Q25-ANDROID-FILE-IMPORT.md) keeps Android file imports byte-faithful and rejects malformed UTF-8. [Q25-F168](../../ru/reports/AUDIT-Q25-DESKTOP-CONFIG-FILES.md) shares strict bounded INI file loading across Windows/macOS CLI. [Q25-F169](../../ru/reports/AUDIT-Q25-CLIENT-UI-INI-INPUT.md) passes untrimmed INI from Windows/macOS/Android/iOS UI to the shared parser. [Q25-F170](../../ru/reports/AUDIT-Q25-MOBILE-CONFIG-BUDGET.md) aligns early Android/iOS file and store budgets with the shared core’s 256 KiB limit. [Q25-F171](../../ru/reports/AUDIT-Q25-DESKTOP-STORE-UTF8.md) rejects malformed UTF-8 in Windows/macOS profile stores. [Q25-F172](../../ru/reports/AUDIT-Q25-DESKTOP-STORE-RECOVERY.md) prevents overwriting an unreadable store that could not be preserved and avoids misclassifying migration write failures. [Q25-F173](../../ru/reports/AUDIT-Q25-DESKTOP-PROFILE-TRANSACTIONS.md) persists proposed desktop profile changes before updating the visible list. [Q25-F174](../../ru/reports/AUDIT-Q25-ANDROID-PROFILE-TRANSACTIONS.md) commits Android profile changes and backup restore before UI updates, and verifies encrypted migration before erasing plaintext. [Q25-F175](../../ru/reports/AUDIT-Q25-MOBILE-STORE-LOAD-FAILURE.md) prevents ordinary Android/iOS writes after a store load failure while allowing explicit backup restore. [Q25-F176](../../ru/reports/AUDIT-Q25-ANDROID-STORE-DECODING.md) rejects malformed Android store structure and UTF-8 without changing credentials. [Q25-F177](../../ru/reports/AUDIT-Q25-CLIENT-PROFILE-UI-REVISION.md) rejects stale Android/desktop UI operations and reports when Android needs reconnect after editing the active INI. [Q25-F178](../../ru/reports/AUDIT-Q25-DESKTOP-STORE-CONCURRENCY.md) protects the desktop profile store from stale cross-process writes and quarantine. [Q25-F179](../../ru/reports/AUDIT-Q25-ANDROID-STORE-VERSION.md) rejects stale Android Activity and restore writes. [Q25-F180](../../ru/reports/AUDIT-Q25-IOS-EMPTY-ARCHIVE.md) rejects an empty iOS store before normalization. [Q25-F181](../../ru/reports/AUDIT-Q25-IOS-ACTIVE-PROFILE-RECONNECT.md) tells iOS users to reconnect after editing the active INI. [Q25-F182](../../ru/reports/AUDIT-Q25-IOS-PROFILE-SNAPSHOT.md) rejects stale iOS Edit/Delete actions within the app. [Q25-F183](../../ru/reports/AUDIT-Q25-DESKTOP-STORE-BOUNDS.md) bounds desktop store and macOS .bak I/O at 16 MiB. [Q25-F184](../../ru/reports/AUDIT-Q25-DESKTOP-STORE-LOCK-WAIT.md) allows bounded one-second waiting for brief desktop sidecar-lock contention. [Q25-F185](../../ru/reports/AUDIT-Q25-DESKTOP-STORE-STRUCTURE.md) rejects a null desktop store root or row while preserving a genuine empty array. [Q25-F186](../../ru/reports/AUDIT-Q25-ANDROID-ACTIVE-INDEX.md) rejects malformed Android active-profile indexes on all three paths and bounds direct service reads. [Q25-F187](../../ru/reports/AUDIT-Q25-IOS-ACTIVE-INDEX.md) rejects malformed iOS restore active indexes, pending XCTest on Mac/Xcode. [Q25-F188](../../ru/reports/AUDIT-Q25-MOBILE-STORE-BOUNDS.md) bounds Android encrypted store and backup before decoding/crypto, rejects malformed UTF-8, and documents distinct portable-backup and internal desktop-store budgets. [Q25-F189](../../ru/reports/AUDIT-Q25-DESKTOP-PROFILE-IDENTITY.md) migrates a missing Id in mixed desktop stores and rejects empty/duplicate explicit IDs on read and write. [Q25-F191](../reports/AUDIT-Q25-DESKTOP-STORE-NULL-FIELDS.md) rejects null in required desktop-profile fields and collections on read and write; conformance and both desktop builds PASS. [Q25-F192](../reports/AUDIT-Q25-DESKTOP-SETTINGS-STORE.md) shares Windows/macOS settings storage, bounds reads and writes to 1 MiB, and preserves corrupt originals before fallback; seven file conformance cases and both builds PASS. [Q25-F193](../reports/AUDIT-Q25-ANDROID-APPS-INI.md) keeps apps_mode/apps in the qeli section when editing a profile with a logging section; 167 JVM tests and a debug APK PASS. [Q25-F194](../reports/AUDIT-Q25-CLIENT-SHARE-PASSWORD.md) refuses share links without a portable inline password; 52 shared-editor integration tests PASS on Windows. [Q25-F195](../reports/AUDIT-Q25-CLIENT-SHARE-UI.md) shows the refusal in Windows/macOS/iOS UI; desktop builds PASS, iOS XCTest pending. [Q25-F196](../reports/AUDIT-Q25-CLIENT-SHARE-PARITY.md) aligns Android/.NET/iOS tests for passwordless-link import versus refused re-export; 167 Android JVM tests and .NET conformance PASS against fresh debug host DLL. [Q25-F197](../reports/AUDIT-Q25-CLIENT-INI-MATRIX.md) pins all 84 schema fields through runtime and 1000 deterministic INI export/reimport mutations; 54 editor tests PASS. Q25-F210 below closes the available remainder: arbitrary external writers are explicitly unsupported and the iOS provider is read-only; 511 .NET, 167 JVM and 12 Android instrumentation PASS. Preceding VPN/reconnect E2E is reconciled with D12; Apple runtime is SKIPPED by user decision, not PASS. [Q25-F198](../reports/AUDIT-Q25-CLIENT-URI-BUDGET.md) caps direct panel URI imports at 256 KiB before query parsing; 1552 portable and 54 integration tests PASS. |
| D09 | 14/15/25/32/33 | DONE | Linux lifecycle and system failures | [Closure evidence](../reports/AUDIT-Q25-LINUX-LIFECYCLE-CLOSURE.md): source `4eaf551a`: 2175 Linux unit, 8 control, 15 hook-process and 8/8 live worker lifecycle PASS, with exit/SHA and before/after network snapshots. Earlier 48 privileged and real DNS/route/firewall matrices still apply to unchanged paths. Full install/upgrade and network combinations remain D11/D10; whole shutdown remains D05. |
| D10 | 17/18/19/21/22/23 | DONE | Network integration matrix | Supported Linux contract closed by Q25-F211/F212/F213 below: 118 four-profile IPv6/DNS checks, 8 NDP packet cells/248 checks, 4 mixed IPv4/IPv6 backends with public firewalld zone/policy reload/restart/416 checks and 19 targeted tests PASS. Foreign resources restored; crash/recovery — D04, TCP/UDP multiprofile SIGKILL/churn — D13. Arbitrary root rewrites/automatic backend migration are not certified. [Evidence](../../../release/certification/evidence/firewalld-profiles-20261002.json). |
| D11 | 00/24/27/34 | DONE | Current native cores and provenance | [Q25-F202](../reports/AUDIT-Q25-NATIVE-REBUILD.md): clean source `27db1a22`, one digest, independent A/B release builds of Windows x64, macOS universal2 and Android arm64/x86_64 with matching SHA; ABI/exports, 14 manifest copies and provenance PASS. Windows selftest 143/0, Android APK embeds verified libraries. After Q25-F204, [the A/B refresh](../reports/AUDIT-Q25-NATIVE-REBUILD.md#refresh-after-q25-f204-1-october-2026) verified source digest `d39a3343`, four ABI 1.16 libraries, 14/14 SHA pairs and provenance; Windows selftest 143/143, Android JVM 167/167 and a new APK with exact `.so` files. Mac app/runtime are excluded under D12 by user decision. |
| D12 | 24/25/27/34 | DONE | Platform evidence within available scope | [Q25-F203](../reports/AUDIT-Q25-ANDROID-NETWORK-IDENTITY.md): Android 0.8.2 APK/JNI, 167 JVM, 11 instrumentation, bidirectional ICMP, WebView HTTP 200 from VPN address, reconnect and Wi-Fi toggle PASS. The physical inner source was localized to system Private DNS `netd`; server anti-spoofing held. Windows VM, Mac/Xcode/iOS and router runtime are **SKIPPED by user decision**, not PASS. After the new native A/B and APK, [instrumentation 11/11](../reports/AUDIT-Q25-NATIVE-REBUILD.md#refresh-after-q25-f204-1-october-2026) was repeated; full VPN traffic for this new APK was not. Physical Android/LTE/Doze/always-on and a release APK remain part of full audit section 29, not certified here. |
| D13 | 14/19/22/25 | DONE | Resource retention under load | [Q25-F204](../reports/AUDIT-Q25-WORKER-RESOURCE-CHURN.md): 8/8 worker TCP/UDP × IPv6-mode, 80 reloads, fd/socket/task delta zero; exact release SHA `a526c03b` completed 100 TCP handovers (16/16), 100 UDP QUIC handovers (17/17), and three UDP adapters ×20 (17/17 each), retaining session/processes/TUN and restoring sysctl leases. Concurrent TCP/UDP profiles: 14/14 stop/reload/SIGKILL/recovery, fd/socket/tasks 26/11/7→26/11/7, network/journal restored after stop. RSS peaks were sampled; unavailable platform runtime is not certified. |
| D14 | 00/34 | DONE | Current benchmark and certification | [Current candidate](../reports/BENCHMARK.md#current-release-candidate-checks--1-october-2026): exact SHA `a526c03b`, 12-mode benchmark/32 phases, 18 release cases/327 checks and 144 targeted checks after stopping the old lab restart loop; full host snapshot restored. Certification 20/20 automated gates, same-SHA 100 TCP + 100 QUIC soak and 2238 Linux unit reused with identical qeli tree. Initial parent differences attributed to exact vpn-nat scripts/journal; raw and partial manifest retained. No physical advisory is promoted to PASS; this is not full release preflight/CI/package audit. Source/artifact changes require certification refresh. |
| D15 | All started sections | IN_PROGRESS | Evidence and documentation reconciliation | Map historical open items to later fixes; verify patch applicability, diff/commit and RU/EN links. Close each debt item with evidence, not a commit count. [Q25-F200](../reports/AUDIT-Q25-DOC-PARITY.md): 32 index, 3 link and 26 language-parity findings resolved; 494 Markdown files and all 9 check_docs checks PASS. Older runtime evidence reconciliation remains. [Q25-F201](../reports/AUDIT-Q25-PATCH-RECONCILIATION.md): 625 archived patches classified without applying them; D09 evidence age corrected. All 22 received targeted review: no missing fix found among 20 code candidates; 2 touch the user-modified CHANGELOG. D15 remains open for final runtime/evidence reconciliation. |

Current status after D10: **13/15 DONE (86.7%), 2 IN_PROGRESS — D06/D15, 0 TODO**.
These are closed debt groups; current-HEAD certification still requires final D15.
Historical counts below belong to earlier snapshots and are not retroactively changed.

## Debt completion: workflow from 25 September

At the user's request, work proceeds in batches with tests selected by change risk.
The verified reference snapshot is `a8aba986`: 1584 host, 71 config, 2157 Linux,
48 privileged, 8 lifecycle, 38 native cases and 2 recoveries; see
[TOFU worker](../reports/AUDIT-Q25-IDENTITY-WORKER.md). These results belong to that
snapshot and do not automatically certify subsequent changes.

| Batch | Groups | Remaining work and completion condition |
|---|---|---|
| A. Startup, shutdown and system context | D05/D06/D09 | Review startup config_source::load/metadata/canonicalize, composed NetworkPlan/cleanup budgets and remaining early Drop paths in one pass; complete the WAN/resolved/attach/dynamic IPv6 table. Record each path as fixed and tested, already covered by referenced evidence, or a justified limitation. Finish with targeted Linux tests of affected boundaries. |
| B. Configuration and remaining network compatibility | D07/D08/D10 | Complete the server field → parse/validate/runtime/serialize table and the 81+3 client contract; cover save/reload/import, malformed input and concurrent edits. Run only uncovered IPv6/NDP, DNS, multiprofile and firewall combinations, grouping related fixes. |
| C. Builds, Android and resources | D11/D12/D13 | Rebuild affected cores at an agreed clean commit, verify A/B/ABI/provenance and Android. Run one bounded churn/reconnect/fault campaign with cycles and fd/tasks/threads/RSS/network-object growth criteria recorded before execution. Retain platform SKIPPED decisions. |
| D. Final regression and measurements | D14/D15 | Run one overall regression campaign on the final candidate, a current benchmark and package/documentation reconciliation. Give every obligation evidence or an explicit unresolved remainder; unverified work cannot be declared closed. |

Batches specify completion order, not a promise of four runs or a calendar deadline.
Fixes and short checks happen inside a batch; advancing does not require another
permission request.

### Test selection

- Each change gets its defect regression, affected module tests and necessary build.
  Docs-only changes get docs/link/diff checks, without Rust or lab runs.
- Related fixes share one test campaign. Run full Linux/host suites at batch boundaries;
  run the full feature/platform matrix on the final candidate, or earlier when
  cfg/features/ABI/dependencies change.
- New native fault/cancel/crash scenarios remain required for changes to ownership of
  networking, keys or persisted state. Unchanged transport and firewall matrices do
  not need to run after every local fix.
- Reproduce against the old binary once. Reuse that baseline with its SHA; repeat it
  only when its scenario, assumptions or an ambiguity changes.
- Reuse evidence only after checking affected code/dependencies and lab conditions,
  recording the original SHA and applicability reason. A newly built binary does not
  invalidate every independent check. The final candidate still gets overall validation.
- Run independent builds/tests concurrently; operations sharing mutable sources,
  target directories or network resources stay sequential. Do not repeat successful
  checks without a relevant subsequent change.

### Scope and reporting

Existing D01–D15 obligations remain. Record new noncritical improvements and unproven
hypotheses in the later full-audit queue without expanding this batch. Include confirmed
security, data/traffic loss or core functional defects with a specific reproducer.

Uninterruptible syscalls and forced Drop require a supported-boundary and ownership
explanation; they do not by themselves restart the audit cycle. Ordinary hangs, lost
errors and ownerless mutations remain mandatory defects. Relabelling a defect as a
limitation does not close it.

Use one batch result entry in this register; small fixes need no separate report.
Preserve logs, commands and hashes as machine artifacts. User-facing results state
behavior changes, closed criteria and a finite remainder. The 4/15 figure counts fully
closed groups; it is not a time or work-completion estimate. Rescheduling alone changes
no completion status.

Initial batch A reconciliation at `a8aba986`: config_source already rejects special
files with NONBLOCK + fstat and validates one opened snapshot. Do not re-audit those
properties unless they change. Remaining checks are synchronous loading before signal
registration, no overall size cap in the loader itself, and startup metadata/canonicalize.
These are concrete review targets. Individual DNS/route/gateway/kill-switch budgets and
joined workers already have evidence; inspect their composition and early exits instead
of repeating every previous scenario.

Privileged external mutation between a check and a write has no atomic protection
guarantee; this is an OS-interface limitation, not automatically a new feature defect.
However, identity loss, command errors and unknown outcomes must retain recovery evidence
and must not produce false success.


### Batch A — verified startup result, September 25

The startup part of D05/D09 is closed: stop handlers precede INI reads, the 256 KiB
client cap precedes content reads/allocation, and loading, capability probes and hook
canonicalization run on a joined worker. The permission warning uses the same opened
snapshot. Stop waits for admitted work; late failures remain errors, with no credential
command or connection started.

Targeted checks: 12 host + 32 Linux tests (15 config source, 8 lifecycle,
9 prepared worker), Linux Clippy and standalone client build. Frozen baseline
`a8aba986` reproduced runtime blocking, SIGTERM exit before handler registration, and
oversized-file reads. Three fixed startup cases and TCP/UDP startup → post_up → stop
passed in separate NET/mount/PID namespaces, preserving routes and operator firewall.
The first stop fixture incorrectly used `pass_cmd`: its strict-parser rejection was
retained and the corrected `password_command` fixture was rerun. Regression retained as
[scripts/audit_client_startup.py](../../../scripts/audit_client_startup.py) and
[test shim](../../../scripts/audit_client_startup_shim.c). Commands, manifests, SHA and logs:
`audit-debt-20260924/batch-a-startup/` under the `qeli` artifact directory.

The server at `a8aba986` (SHA256 `c53dec6b…83c97`) and unchanged teardown fixture are reused;
this change does not affect server behavior. Earlier broad matrices are not claimed as
new runs. D05/D06/D09 remain IN_PROGRESS: composed NetworkPlan/cleanup budget, system
context table and early Drop paths remain. Established boundary: arbitrary kernel/
filesystem I/O cannot safely be interrupted; forced Drop retains its join. This limit
does not close the remaining shared command-budget obligation.


**Shared command budget (batch A continuation).** TUN/gateway/routes/DNS setup shares
15 seconds. Rollback/cleanup receives a separate shared deadline, retained across pump
join, worker threads, fallback Drop and terminal firewall cleanup. Errors remain sticky;
a new attempt after previous owners finish receives a fresh budget. Ownership selectors,
namespace guards and kill-switch release prerequisites are not weakened.

Validated: 1594 host tests, 471 targeted Linux tests and 18 privileged; Linux Clippy,
client-only and server-only builds. Eight native baseline/fixed TCP/UDP cases inject
successive 9+9 second delays: old `efc9f949` takes 19–20 seconds. Fixed setup expires
commands at the shared deadline and finishes rollback about 15.9 seconds after the first
marker; cleanup takes about 14.8 seconds from its first mutation marker (its budget began
earlier). Setup leaves clean networking; failed cleanup retains both DROP families and
`failed`, preserving operator rules/routes. Four ordinary TCP/UDP clean/fault shutdown
cases and two explicit recovery runs also PASS. Fixture:
[audit_network_budget.py](../../../scripts/audit_network_budget.py). Evidence:
`audit-debt-20260924/batch-a-budget/`, 359-file source manifest, driver SHA256
`ef126a15…934a4f7`. Server `a8aba986` is reused; its runtime is not claimed as a new build.

A separate restart after **gateway timeout** confirmed the D02 boundary: a lost
per-interface sysctl witness prevents automatic cleanup completion. The initial automatic
recovery expectation produced 2 FAIL retained in `ab3`; this is not successful recovery.
Validation checks preservation of the original record, absence of TUN/routes and both
DROP families; follow [§6.64](../manuals/TROUBLESHOOTING.md) for manual recovery.
The two successful recovery cases above refer to the earlier route-fault scenario without
lost witnesses.

Command composition is closed within these limits; no hard arbitrary-kernel-I/O timeout
is promised. D05 remains IN_PROGRESS pending the final early-Drop/internal-wait inventory;
D06 remains open for the checks below. Group totals remain 4/15 DONE.

D06 reconciliation against current code (no new runtime PASS claim):

| Boundary | Existing evidence / remainder |
|---|---|
| resolved / system bus | GUID/unique owner/network/PID context already exercised in [resolver context](../reports/AUDIT-Q25-RESOLVER-CONTEXT.md); DNS v2 markers/crash are D04. |
| procfs / sysfs | Namespace pins, cookie and sysctl witnesses are D02/D04. IPv6 module-disabled evidence uses bounded strict reads; it does not guarantee absence of future IPv6. |
| TUN attach / names | [Attach](../reports/AUDIT-Q25-TUN-ATTACH.md), leases and route/TUN identity have dedicated checks. `dev_attach` reads `tun_flags` through `/sys/class/net`, which may belong to an inherited network namespace. The [kernel netlink snapshot](https://github.com/torvalds/linux/blob/master/drivers/net/tun.c) omits some `TUN_FEATURES`, and the first `TUNSETIFF` may rewrite them; a simple netlink substitution is unsafe. [Q25-F123](../reports/AUDIT-Q25-TUN-ATTACH-CONTEXT.md) adds a native same-name/different-netns test and rejects a proven `ifindex` mismatch before `TUNSETIFF`. Matching indexes do not prove namespace identity; this combination remains uncertified until full namespace-aware flag observation is available. |
| Physical WAN | `gateway/wan.rs` returns a route's device name; firewall records name selectors. [Q25-F120](../reports/AUDIT-Q25-GATEWAY-IPV6-ROAM.md) rechecks the IPv6 default route after the roaming COMMIT rule batch. [Q25-F124](../reports/AUDIT-Q25-EXIT-POLICY-ROUTING.md) reproduces un-NATed off-WAN egress under policy routing and adds a fail-closed DROP before MARK/NAT plus cleanup lockdown. [Q25-A125](../reports/AUDIT-Q25-WAN-NAME-REUSE.md) confirms that a distinct new name is blocked, but a new device reusing the old name inherits MARK/NAT without refresh. [Q25-F126](../reports/AUDIT-Q25-WAN-METRIC.md) selects the lowest-metric main-table default; a separate exit-WAN change without VPN COMMIT is now handled by the [Q25-F127](../reports/AUDIT-Q25-EXIT-WAN-MONITOR.md) monitor, verified on TCP/UDP through cleanup. Active-WAN rename/reuse is unsupported until an identity-bound backend exists; migration and mixed-backend packet/recovery remain D06/D10. [Q25-F128](../reports/AUDIT-Q25-EXIT-SELF-WAN.md) rejects the exit TUN itself as a WAN before installing rules. [Q25-F129](../reports/AUDIT-Q25-WAN-ECMP.md) rejects ECMP and equal-priority defaults on different WANs instead of selecting one destination hash bucket; the client IPv6 gateway also refuses before changing forwarding/RA. |
| DNS / carrier globals | DNS is per-link; process-global carrier/cycle state is protected by one run_client per process through terminal cleanup. Forced Drop closes readmission until process restart; verification below. |
| Dynamic IPv4 | [Q25-F122](../reports/AUDIT-Q25-KILL-SWITCH-DYNAMIC-IPV4.md) disallows admission without `iptables` based on a currently empty default-route list; a late route cannot bypass a missing firewall. Other WAN/route scenarios remain D06/D10. |
| Dynamic IPv6 | [Q25-F121](../reports/AUDIT-Q25-KILL-SWITCH-DYNAMIC-IPV6.md) disallows unprotected admission based on a currently empty address list; late IPv6 cannot bypass a missing firewall. The native address-arrival matrix and other dynamic paths remain D06/D10. |



**Linux runtime admission and early-exit reconciliation (batch A continuation).**
Concurrent `run_client` calls no longer overlap process-global carrier/cycle state:
the second call fails before config/signals, and admission lasts through cleanup and
final writer completion. A returned error permits another invocation with the usual
resource checks. Forced Drop of the whole future closes admission until process restart:
nested TaskGroups cannot guarantee async join in Drop. This is an explicit cancellation
boundary, not a claim of successful network cleanup.
[Contract](../manuals/OPERATIONS.md#one-linux-client-per-process).

Against the original `b307c913` entry point, the rejection-before-missing-INI check
produced the expected FAIL: the old invocation reached file open while the process gate
was occupied. The fixed entry point, simultaneous admission, terminal ownership,
cancellation with an in-flight child and panic passed: 7 host + 85 Linux tests, Linux
Clippy. Three privileged tests of unchanged namespace workers remain ignored in this
targeted run; no new privileged PASS is claimed. Final commands/exit codes/manifest: `audit-debt-20260925/batch-a-instance/`.

Linux client early-path reconciliation against current code and previous evidence:

| Path / wait | Outcome and boundary |
|---|---|
| Startup/NetworkPlan before adoption | `network_task::Job::Drop` rejects the result and joins the original thread; partial guards roll back there. [Network worker](../reports/AUDIT-Q25-NETWORK-TASK.md), startup and budget above. |
| Pump start / partial plan | Writer failure stops and joins the reader; rejected `(pump, guard)` drops in that order. [Pump start](../reports/AUDIT-Q25-PUMP-START.md). |
| Established TUN / ordinary error | `TunGuard::shutdown` awaits DNS → pump → routes/gateway; fallback Drop retains the TUN fd and shared cleanup deadline. [Teardown](../reports/AUDIT-Q25-TUN-TEARDOWN.md), budget above. |
| TCP/H2/UDP child tasks | Ordinary exits finish TaskGroups before terminal cleanup; Drop only closes admission/requests abort. Forced cancellation of the entire run_client now prohibits reuse in that process. [TCP](../reports/AUDIT-Q25-TCP-TASKS.md), [H2](../reports/AUDIT-Q25-H2-TASKS.md), [UDP](../reports/AUDIT-Q25-UDP-TASKS.md). |
| TOFU/status / file I/O | finish awaits the worker; fallback Drop joins synchronously. Sender/queue mutexes are not held during file operations. [TOFU](../reports/AUDIT-Q25-IDENTITY-WORKER.md), [status](../reports/AUDIT-Q25-STATUS-WRITER.md). |
| Internal locks / waits | Carrier/core/diagnostic state changes under short mutexes without await; writer queues release their mutex before external I/O. TunWorkers deliberately holds its join lock through all threads so cancellation cannot abandon fd ownership. [TUN workers](../reports/AUDIT-Q25-TUN-WORKERS.md). Non-preemptible kernel/fs I/O and forced join remain a documented boundary, not a 15-second process-exit guarantee. |

This closes reconciliation of the listed Linux early-Drop paths and process-global
admission. D05/D06/D09 were not closed at that stage: hook/backup file preparation
needed runtime reproduction. The following batch continuation closes that part;
server setup/cleanup still requires checking. WAN/dynamic IPv6 remain in D06. No new platform or network packet PASS is claimed.



**Hook and backup file I/O (batch A continuation).** Executor stalls during hook context
write/removal and active backup INI reading were reproduced and fixed. One joined thread
owns hook preparation, command runtime and cleanup; cancellation before spawn skips the
command, while cancellation of a running shell waits for termination/reaping before
context removal. Backup preflight uses the existing blocking worker with its config
lease; HTTP cancellation cannot release it before the operation ends. The shared loader
rejects FIFO and checks a stable source file. Hook authorization and INI/API formats
are unchanged.

Validation: **37 host + 77 Linux tests, 8 native scenarios PASS**, Linux Clippy and separate
client/server builds. The reproducer delays actual write/unlink/read by 2 seconds:
original `0645a8b0` handlers deliver 0/0/2 heartbeat ticks (3 expected FAIL), fixed handlers
178/178/179. Cancelled preparation leaves no command-start marker; cancellation of a live
hook verifies reaping/process absence and context removal. Cancelled backup retains the
config lease, preserves config and delivers 178 ticks. Backup → overlay/exact restore and
incomplete rollback-snapshot rejection ran in private NET/mount/PID namespaces and tmpfs
`/etc/qeli`, `/tmp`. Shim: [audit_hook_backup_io_shim.c](../../../scripts/audit_hook_backup_io_shim.c).
Logs/commands/362-file source manifest: `audit-debt-20260925/batch-a-file-io/`;
fixed test binary SHA256 `208e91b7…500bba`. Baseline combines the original handlers with
the new test harness; it is not an old released binary.

This hook/backup item is closed; D05 remains IN_PROGRESS. Server code review specifies
the next batch: `run_worker` invokes synchronous `nat::cleanup_all`;
`run_profile_generation` performs TUN/NAT setup, and ordinary `run_profile` calls
`drop(ProfileTeardown)` with NAT cleanup/worker joins on its async path. NAT component
budgets already have coverage; scheduler isolation and a composed profile deadline
still need checking. Non-preemptible kernel/fs calls and forced joins are not claimed
to have a hard timer bound. D06 WAN/dynamic IPv6 and other groups remain; **4/15 DONE**.

### Q25-F115 — server cleanup off the async executor

Synchronous `nat::cleanup_all`, ordinary `ProfileTeardown::drop`, final NAT
sweep/ownership checks and `usage.flush` run on joined workers. Cancelling an async
waiter joins its worker, so the network namespace lease and profile resources cannot
be released before accepted cleanup finishes. Child-task shutdown, registry removal,
NAT and TUN cleanup keep their order; a worker failure enters `Outcome`.
[Report](../reports/AUDIT-Q25-SERVER-CLEANUP-WORKER.md).

Host: 1602 tests PASS, 1 pre-existing ignored; Linux cross-check and all-targets
Clippy PASS. Lab `.11`: 10 targeted Linux tests and eight real TCP/UDP ×
`off`/`manual`/`route`/`nat66` lifecycle cases and 2 bind-failure/rollback/retry cases PASS in private NET/mount/PID
namespaces. Exact source manifest and logs:
`audit-debt-20260925/server-cleanup-phase/`. D05 remains IN_PROGRESS:
synchronous TUN/NAT setup, emergency Drop, a composed profile deadline and
non-preemptible system calls still need separate resolution. Register total:
**4/15 DONE**.

### Q25-F116 — server profile TUN/NAT setup off the executor

The first joined worker creates and configures TUN: until its result is adopted,
the non-persistent device belongs to its original fds. After adoption,
`ProfileTeardown` owns the queues; only then does a second worker install
NAT/IPv6 routing. Cancelling a waiter joins its running worker before dropping
the outer guard. [Report](../reports/AUDIT-Q25-SERVER-SETUP-WORKER.md).

1603 host tests PASS, 1 previously ignored; 11 targeted Linux tests, Linux
all-targets Clippy and 8 ordinary plus 2 bind-failure/retry cases in private
namespaces on `.11` PASS. Source/logs:
`audit-debt-20260925/server-setup-phase/`. D05 remains IN_PROGRESS: DNS INPUT
firewall, NDP bind, emergency Drop and the composed deadline for all operations
remain. Register: **4/15 DONE**.

### Q25-F117 — server profile DNS firewall setup off the executor

Both DNS INPUT/REDIRECT installs run on joined workers. Cancelling a waiter
closes adoption; an unadopted `DnsInputLease` is destroyed in its original
namespace before the outer guard drops. An adopted lease moves into
`ProfileTeardown`. [Report](../reports/AUDIT-Q25-SERVER-DNS-SETUP-WORKER.md).

1603 host tests PASS, 1 previously ignored; 11/11 targeted Linux tests,
22/22 recovery/ownership/SIGKILL checks, 4/4 TCP/UDP × IPv6 `manual`/`route`
DNS cases in private namespaces on `.11` PASS. Logs and manifest:
`audit-debt-20260925/server-dns-setup-phase/`. D05 stays IN_PROGRESS:
NDP bind, emergency Drop and whole-setup deadline remain. Register: **4/15 DONE**.

### Q25-F118 — NDP bind off the executor

`AF_PACKET` bind and socket-local multicast membership run on a joined
worker; the adopted `OwnedFd` is registered as `AsyncFd` on the original
Tokio runtime. Cancellation closes an unadopted fd before the outer guard
is destroyed. [Report](../reports/AUDIT-Q25-SERVER-NDP-BIND-WORKER.md).

On `.11`: 5 NDP unit, 1 privileged namespace, 8 lifecycle and 22 recovery
checks PASS; Linux Clippy for library/binary and rustfmt PASS. Source and logs:
`audit-debt-20260925/server-ndp-bind-phase/`. D05 stays IN_PROGRESS:
whole deadline, forced Drop and arbitrary kernel/fs I/O. Register:
**4/15 DONE**.

### Q25-F119 — shared server setup deadline and all-listener readiness

A 120-second budget runs from generation start until primary and every extra
listener confirms bind; after readiness, service has no such timer. UDP reports
readiness after its complete SO_REUSEPORT group. Bind errors belong to setup,
not cleanup. [Report](../reports/AUDIT-Q25-SERVER-SETUP-BUDGET.md).

On `.11`: 2 new + 11 worker tests, 8 lifecycle, 4 occupied-bind
rollback/retry/stop and 22 recovery checks PASS; Linux Clippy library/binary,
rustfmt and docs checks PASS. Failed first run and corrected rerun are in
`audit-debt-20260925/server-setup-budget-phase/`. D05 stays IN_PROGRESS:
forced Drop, whole-shutdown deadline and non-preemptible kernel/fs I/O.
Register: **4/15 DONE**.

### D09 — final Linux lifecycle reconciliation, 25 September

The [report](../reports/AUDIT-Q25-LINUX-LIFECYCLE-CLOSURE.md) ties the current
Linux suite (2175 PASS), 8 control and 15 hook-process tests to eight live
worker cases. Raw before/after firewall/routes/links/forwarding snapshots, binary
and harness SHA, stdout and exit codes are retained. An initial snapshot assertion
falsely flagged empty xtables-nft built-in tables; raw dumps remain and the comparison
was corrected. The first full suite hit EMFILE at nofile=1024 in a 512-connection
TCP test; unchanged code passed with nofile=4096. Prior privileged/DNS/route/crash
evidence was checked against the unchanged paths.
**D09 DONE; register: 5/15 DONE (33.3%), 8 IN_PROGRESS, 2 TODO.**
Install/upgrade and systemd runtime remain separate full-audit and D11 work;
D05/D06/D10 retain their status.

### Q25-F130 — server worker admission after cancellation

After the first network mutation, forced Drop or an unconfirmed terminal result
retains the network-namespace lease until process exit. Early rejection and
successful ordinary shutdown release it; a replacement worker cannot overlap
an unfinished generation. [Report and checks](../reports/AUDIT-Q25-SERVER-FORCED-DROP-LEASE.md).
This partially closes D05: async child joining on forced Drop and the whole
shutdown deadline remain open. Register: **5/15 DONE**.

### Q25-F131 — WAN presence during server setup

The selected IPv4 NAT or managed IPv6 uplink is now checked with an ioctl in the
worker network namespace before enabling forwarding or adding rules.
[Report and 1 unit + 8 ordinary + 2 negative Linux runs](../reports/AUDIT-Q25-SERVER-WAN-PRESENCE.md).
Active-WAN name reuse, atomic binding of rules to device identity and mixed-backend
recovery remain open. D06 stays IN_PROGRESS; register **5/15 DONE**.

### Q25-F132 — ambiguous server auto-WAN

The shared client/server default-route parser detects ECMP and equal best metrics
on different WANs. Server auto mode refuses before forwarding and new rules;
[report: 11 parser + 1 WAN unit, 8 ordinary and 2 negative Linux cases](../reports/AUDIT-Q25-SERVER-WAN-ECMP.md).
Explicit WAN, policy routes and runtime changes remain D06/D10;
register **5/15 DONE**.

### Q25-F133 — client core build without the roaming feature

The exit WAN monitor runs on Linux regardless of experimental-roaming, but TCP
and UDP declared the TUN name only under that feature. The client-only build
failed with two E0425 errors; the declaration is now Linux-scoped.
[Report, baseline FAIL and fixed feature builds](../reports/AUDIT-Q25-CLIENT-ONLY-BUILD.md).
The router client binary built and ran with --help; platform runtime and
provenance remain D11/D12. Register **5/15 DONE**.

## Sources

- [AUDIT-Q01-SERVER-INI](../reports/AUDIT-Q01-SERVER-INI.md)
- [AUDIT-Q02-CLIENT-PARSERS](../reports/AUDIT-Q02-CLIENT-PARSERS.md)
- [AUDIT-Q05-PREFLIGHT](../reports/AUDIT-Q05-PREFLIGHT.md)
- [AUDIT-Q14-CONTROL](../reports/AUDIT-Q14-CONTROL.md)
- [AUDIT-Q14-DNS-OWNERSHIP](../reports/AUDIT-Q14-DNS-OWNERSHIP.md)
- [AUDIT-Q14-H2-TASKS](../reports/AUDIT-Q14-H2-TASKS.md)
- [AUDIT-Q14-HOOKS](../reports/AUDIT-Q14-HOOKS.md)
- [AUDIT-Q14-IPV6-PARTIAL-ACQUIRE](../reports/AUDIT-Q14-IPV6-PARTIAL-ACQUIRE.md)
- [AUDIT-Q14-NAT-CLEANUP](../reports/AUDIT-Q14-NAT-CLEANUP.md)
- [AUDIT-Q14-NAT-COMMANDS](../reports/AUDIT-Q14-NAT-COMMANDS.md)
- [AUDIT-Q14-OWNED-SHUTDOWN](../reports/AUDIT-Q14-OWNED-SHUTDOWN.md)
- [AUDIT-Q14-PROFILE-SHUTDOWN](../reports/AUDIT-Q14-PROFILE-SHUTDOWN.md)
- [AUDIT-Q14-Q15-WORKER-USAGE](../reports/AUDIT-Q14-Q15-WORKER-USAGE.md)
- [AUDIT-Q14-Q19-LIFECYCLE](../reports/AUDIT-Q14-Q19-LIFECYCLE.md)
- [AUDIT-Q14-Q25-FIREWALL-CHECKS](../reports/AUDIT-Q14-Q25-FIREWALL-CHECKS.md)
- [AUDIT-Q14-Q32-NOTIFICATIONS](../reports/AUDIT-Q14-Q32-NOTIFICATIONS.md)
- [AUDIT-Q14-Q33-CONFIG-TRUST](../reports/AUDIT-Q14-Q33-CONFIG-TRUST.md)
- [AUDIT-Q14-SUPERVISOR](../reports/AUDIT-Q14-SUPERVISOR.md)
- [AUDIT-Q14-SYSCTL-RECOVERY](../reports/AUDIT-Q14-SYSCTL-RECOVERY.md)
- [AUDIT-Q19-DNS-CACHE](../reports/AUDIT-Q19-DNS-CACHE.md)
- [AUDIT-Q19-DNS-EDNS](../reports/AUDIT-Q19-DNS-EDNS.md)
- [AUDIT-Q19-DNS-PROXY](../reports/AUDIT-Q19-DNS-PROXY.md)
- [AUDIT-Q19-Q22-NETWORK-PLAN](../reports/AUDIT-Q19-Q22-NETWORK-PLAN.md)
- [AUDIT-Q25-CLIENT-COMMANDS](../reports/AUDIT-Q25-CLIENT-COMMANDS.md)
- [AUDIT-Q25-CLIENT-NAMESPACE](../reports/AUDIT-Q25-CLIENT-NAMESPACE.md)
- [AUDIT-Q25-CORE-LIFECYCLE](../reports/AUDIT-Q25-CORE-LIFECYCLE.md)
- [AUDIT-Q25-CREDENTIAL-COMMANDS](../reports/AUDIT-Q25-CREDENTIAL-COMMANDS.md)
- [AUDIT-Q25-DNS-LEASES](../reports/AUDIT-Q25-DNS-LEASES.md)
- [AUDIT-Q25-DNS-RECOVERY](../reports/AUDIT-Q25-DNS-RECOVERY.md)
- [AUDIT-Q25-EXIT-OWNERSHIP](../reports/AUDIT-Q25-EXIT-OWNERSHIP.md)
- [AUDIT-Q25-GATEWAY-IDENTITY](../reports/AUDIT-Q25-GATEWAY-IDENTITY.md)
- [AUDIT-Q25-GATEWAY-ROLLBACK](../reports/AUDIT-Q25-GATEWAY-ROLLBACK.md)
- [AUDIT-Q25-GATEWAY-WAN](../reports/AUDIT-Q25-GATEWAY-WAN.md)
- [AUDIT-Q25-H2-TASKS](../reports/AUDIT-Q25-H2-TASKS.md)
- [AUDIT-Q25-KILL-SWITCH-LIFETIME](../reports/AUDIT-Q25-KILL-SWITCH-LIFETIME.md)
- [AUDIT-Q25-NETWORK-CLEANUP](../reports/AUDIT-Q25-NETWORK-CLEANUP.md)
- [AUDIT-Q25-PASSWORD-FILES](../reports/AUDIT-Q25-PASSWORD-FILES.md)
- [AUDIT-Q25-PATH-MONITOR](../reports/AUDIT-Q25-PATH-MONITOR.md)
- [AUDIT-Q25-ROUTE-IDENTITY](../reports/AUDIT-Q25-ROUTE-IDENTITY.md)
- [AUDIT-Q25-ROUTE-OUTCOME](../reports/AUDIT-Q25-ROUTE-OUTCOME.md)
- [AUDIT-Q25-ROUTE-OWNERSHIP](../reports/AUDIT-Q25-ROUTE-OWNERSHIP.md)
- [AUDIT-Q25-ROUTE-PENDING](../reports/AUDIT-Q25-ROUTE-PENDING.md)
- [AUDIT-Q25-ROUTE-POSTCONDITIONS](../reports/AUDIT-Q25-ROUTE-POSTCONDITIONS.md)
- [AUDIT-Q25-ROUTE-SCOPE](../reports/AUDIT-Q25-ROUTE-SCOPE.md)
- [AUDIT-Q25-SETUP-FLUSH](../reports/AUDIT-Q25-SETUP-FLUSH.md)
- [AUDIT-Q25-SETUP-IDENTITY](../reports/AUDIT-Q25-SETUP-IDENTITY.md)
- [AUDIT-Q25-SYSCTL-NAMESPACE](../reports/AUDIT-Q25-SYSCTL-NAMESPACE.md)
- [AUDIT-Q25-SYSCTL-OWNER-EVIDENCE](../reports/AUDIT-Q25-SYSCTL-OWNER-EVIDENCE.md)
- [AUDIT-Q25-SYSTEM-COMMANDS](../reports/AUDIT-Q25-SYSTEM-COMMANDS.md)
- [AUDIT-Q25-TCP-TASKS](../reports/AUDIT-Q25-TCP-TASKS.md)
- [AUDIT-Q25-TUN-ADMISSION](../reports/AUDIT-Q25-TUN-ADMISSION.md)
- [AUDIT-Q25-TUN-ATTACH](../reports/AUDIT-Q25-TUN-ATTACH.md)
- [AUDIT-Q25-TUN-CLEANUP](../reports/AUDIT-Q25-TUN-CLEANUP.md)
- [AUDIT-Q25-TUN-LIFETIME](../reports/AUDIT-Q25-TUN-LIFETIME.md)
- [AUDIT-Q25-TUN-WORKERS](../reports/AUDIT-Q25-TUN-WORKERS.md)
- [AUDIT-Q25-TUNNEL-ROUTES](../reports/AUDIT-Q25-TUNNEL-ROUTES.md)
- [AUDIT-Q25-UDP-TASKS](../reports/AUDIT-Q25-UDP-TASKS.md)

D02/D05: [sysctl journal reads and lock waits](../reports/AUDIT-Q25-SYSCTL-JOURNAL-IO.md) are fixed within the stated scope; remaining row criteria are open.

D03: [kill-switch namespace / reconnect](../reports/AUDIT-Q25-KILL-SWITCH-IDENTITY.md).

D02/D06: [namespace-aware link observation](../reports/AUDIT-Q25-LINK-OBSERVATION.md).

D05: [async preflight and panel transaction lifetime](../reports/AUDIT-Q05-PANEL-TRANSACTIONS.md). The following phase closed the backup/restore budget; other network sequence budgets remain open.

D05/D09 update: [backup/restore budget and snapshot completeness](../reports/AUDIT-Q05-ARCHIVE-BUDGET.md). Other network sequences and filesystem fault E2E remain open.

D02: [internal sysctl boundary guard](../reports/AUDIT-Q25-SYSCTL-CONTEXT-IO.md); durable namespace identity and original-interface ownership remain open; a later phase closed parent trust.

D02/D05/D09: [atomic state publication](../reports/AUDIT-Q25-ATOMIC-STATE.md) cleans partial temporary files and syncs the directory on Unix; actual partial-write/fsync fault probes PASS. Other criteria of these groups remain open.

D02/D05/D09: [state-directory and lock identity](../reports/AUDIT-Q25-STATE-DIRECTORY.md). Parent trust is closed within the stated boundaries; durable namespace identity and original-interface generation remain D02. The groups are not yet fully closed.

D08/D11/D12: [Android JNI and emulator runtime](../reports/AUDIT-Q34-ANDROID-RUNTIME.md): fixed cargo-ndk cwd/API flag, removed the obsolete JSON-config harness; 154 JVM + 6 instrumentation tests PASS. The fresh dev x86_64 APK is SHA-verified. Release A/B, the full config/runtime contract and other platforms remain open.

D02: [namespace pins](../reports/AUDIT-Q25-NAMESPACE-PIN.md) retain open fds from admission through the end of the transaction; 1922 Linux + 29 privileged + 8 worker E2E PASS. Durable generation between transactions and after crashes remains open, as does original-interface generation.

D02: [Q25-F083 — original interface sysctl](../reports/AUDIT-Q25-SYSCTL-TARGET.md): journal v3 retains fds and refuses when evidence is lost; 3 baseline defects reproduced, 5 additional worker E2E PASS. Unsafe name-based restoration and loss of originals are closed. Durable namespace generation after crashes remains open for global journals; automatic per-interface crash recovery is not promised.

D05: [Q25-F084 — shared DNS deadline](../reports/AUDIT-Q25-DNS-BUDGET.md): dns/domain share 15 seconds from admission, retaining a partial lease for separate rollback. 3 new Linux regressions PASS. Kill-switch is addressed by the following phases below; NAT/routes and other lock waits remain open.

D05/D09: [Q05-F008 — async health probes](../reports/AUDIT-Q05-HEALTH-PROBES.md): Status/Transport health do not block the executor waiting for `--version`; four shared async slots and a deadline including queue time. 8 new ordinary + 1 privileged HTTP-router test PASS; 2 counterfactual old-behavior checks fail as expected. Whole network mutation budgets and full HTTP/systemd/fault coverage remain open.

D05/D09: [Q25-F085 — shared kill-switch cleanup deadline](../reports/AUDIT-Q25-KILL-SWITCH-BUDGET.md): 15 seconds include the operation mutex and both families; partial outcomes retain ownership for verified retry. 5 regressions PASS, 2 counterfactual old-behavior FAIL. Engage/refresh are addressed by the following phases below; NAT/routes/gateway and other lock waits remain open.

D05/D09: [Q25-F086/F087 — kill-switch refresh](../reports/AUDIT-Q25-KILL-SWITCH-REFRESH.md): shared admission/command deadline accounts for resolver time; unknown cannot authorize insertion. 6 new regressions and 5 cleanup reruns PASS; 3 counterfactual old-behavior FAIL. DNS/NSS remains synchronous; the following phase below addresses the engage command budget, while NAT/routes/gateway and other waits remain open.

D05/D09: [Q25-F088/F089 — kill-switch setup and rollback](../reports/AUDIT-Q25-KILL-SWITCH-SETUP.md): shared 15-second setup deadline plus a separate shared 15-second rollback deadline; leak overrides cannot accept incomplete rollback. 8 new regressions PASS; 2 counterfactual FAIL, then 8 setup + 6 refresh + 5 cleanup PASS. Full snapshot: 1962 Linux + 30 privileged + 8 worker E2E PASS. Engage/refresh/disengage command budgets are addressed within the stated limits; synchronous DNS/NSS, NAT/routes/gateway, other waits and full D04/D05/D09 remain open.

D05/D09: [Q14-F034 — shared NAT cleanup deadline](../reports/AUDIT-Q14-NAT-CLEANUP-BUDGET.md): profile/startup/final cleanup each share 15 seconds across admission, IPv4/IPv6, exact rules and retired DNS UDP/TCP. Late results cannot succeed; unverified records remain owned. 8 new Linux regressions PASS; 4 counterfactual FAIL, then 8 regressions + 1 privileged exact-rule PASS. Full snapshot: 1970 Linux + 30 privileged + 8 worker E2E PASS. NAT setup/rollback, DNS lease Drop/setup admission, routes/gateway, internal sysctl/I/O and full D04/D05/D09 remain open.

D05/D09: [Q14-F035 — DNS INPUT lease deadlines and retirement](../reports/AUDIT-Q14-DNS-INPUT-BUDGET.md): setup and cleanup each receive 15 seconds including queue/UDP/TCP; separate rollback after setup, retirement without lock admission and retained pending evidence. 4 new portable + 7 Linux + 1 privileged regressions PASS; 5 negative controls, then 20 domain + 7 DNS + 8 NAT + 2 native PASS. Full snapshot: 1981 Linux + 31 privileged + 8 worker E2E PASS. NAT setup/rollback, DNS REDIRECT, routes/gateway, internal sysctl/I/O and full D04/D05/D09 remain open.

D05/D09: [Q14-F036 — NAT/forwarding and DNS REDIRECT setup](../reports/AUDIT-Q14-NAT-SETUP-BUDGET.md): shared setup and exact rollback deadlines; 10 new regressions, 7 negative controls, 1991 Linux + 31 privileged + 8 E2E PASS. Client routes/gateway, scheduler isolation and full D05 remain open.

D02 closed: [Q25-F090 — namespace generation and journal v4](../reports/AUDIT-Q25-NAMESPACE-GENERATION.md). D04/D05 and other criteria remain. Windows VM, Mac/iOS and router tests are excluded from current scope by user decision, not declared PASS.

D09/D10: [17/17 Linux packet matrix PASS](../reports/AUDIT-Q34-LINUX-MATRIX.md). D13: 100 TCP handovers preserved session/fd but exceeded the RSS criterion; failure retained, debt open.

D05/D09: [Q25-F091 — shared gateway/exit-node deadline](../reports/AUDIT-Q25-GATEWAY-BUDGET.md): 6 regressions, 6 counterfactual failures, 107 restored gateway and full Linux 2001 + 32 privileged + 8 E2E PASS. Route sequences, internal locks/I/O and scheduler isolation remain open.

D13: [100 release TCP/UDP handovers each](../reports/AUDIT-Q34-RELEASE-SOAK.md): 30/30 assertions PASS, RSS growth within the unchanged 32 MiB limit; debug FAIL retained. Full resource/fault coverage and final-source measurements remain open.

D05/D09: [Q25-F092 — shared route transaction deadline](../reports/AUDIT-Q25-ROUTE-BUDGET.md): 8 regressions, 6 counterfactual FAILs, 196 restored route tests and full Linux 2009 + 32 privileged + 8 E2E PASS. Executor isolation and internal I/O remain open.

D06/D09: [Q25-F093 — strict resolver configuration check](../reports/AUDIT-Q25-RESOLVER-CONFIG.md): 3 new tests, 2 counterfactual FAILs, 18 restored DNS, full Linux 2012 + 32 privileged + 8 E2E PASS. A separate probe confirmed cross-netns mutation through a shared D-Bus; bus/service identity still needs a fix.

D06/D09/D10: [Q25-F094/F095 — resolved/D-Bus context and DNS ports](../reports/AUDIT-Q25-RESOLVER-CONTEXT.md): direct unique-owner calls with AUTH GUID, 2023 Linux + 33 privileged + 8 E2E, 17/17 packet matrix (301 assertions), 4 counterfactual FAILs and restored 29 DNS + 1 privileged PASS. Real resolved/custom ports/foreign netns and PID namespace checked. The previous open bus/service identity item is closed within these boundaries; other D06 and D10 criteria remain open.

D04/D06/D09: [Q14-F037 — worker network lease](../reports/AUDIT-Q14-WORKER-NETWORK-LEASE.md): different control/state paths can no longer bypass admission; baseline deleted 9 live-worker rules. 2027 Linux + 34 privileged + 8 lifecycle and 22 crash/admission/recovery checks PASS. D04 IN_PROGRESS: persistent exact firewall/routes and mixed nft remain open.

D04/D09/D10: [Q14-F038 — persistent server firewall](../reports/AUDIT-Q14-FIREWALL-JOURNAL.md): exact NAT/routing/DNS INPUT/REDIRECT specifications are written before mutation and recovered after SIGKILL/deleted profiles without listing. Backend/namespace/file errors abort startup and retain evidence. 2044 Linux + 35 privileged + 8 lifecycle; 27 recovery checks; 17/17 cases, 301 assertions PASS. D04 remains IN_PROGRESS: client route/DNS/kill-switch and the full mixed nft/firewalld matrix remain open.

D04/D06/D09: [Q25-F096/F097 — DNS state v2](../reports/AUDIT-Q25-DNS-MARKER-STORAGE.md): trusted held directory, validated files and SO_NETNS_COOKIE; v1 remains without automatic migration. Three file defects reproduced on baseline. 2055 Linux + 37 privileged + 8 lifecycle; 17/17 cases, 323 assertions PASS. Client route/kill-switch recovery, legacy global DNS, live persistent TUN, mixed nft/firewalld and sidecar accumulation remain open; D04 IN_PROGRESS.

D04/D09/D10: [Q25-F098 — kill-switch after crash](../reports/AUDIT-Q25-KILL-SWITCH-REBUILD.md): exact temporary DROP guards retain the prior barrier during setup/rollback and repeated SIGKILL. Real-client baseline passed 14 IPv4 + 13 IPv6 UDP probes; fixed passed 0. 2057 Linux + 39 privileged + 8 lifecycle; 14 runtime checks; 17/17 cases, 339 assertions PASS. D04 IN_PROGRESS: routes, legacy global DNS/persistent TUN and the full mixed firewall matrix remain open.

D04/D09: [Q25-F099 — route ownership attributes](../reports/AUDIT-Q25-ROUTE-ATTRIBUTES.md): usability is separate from delete/replace authority; implicit protocol/metric/source and extra attributes are checked. Baseline deleted 10 operator replacements on the kernel and a real client static bypass. 2068 Linux + 40 privileged + 8 lifecycle; 17/17 cases, 384 assertions PASS. At that stage persistent client route journaling was not implemented; see Q25-F100 below. D04 IN_PROGRESS.

D04/D09: [Q25-F100 — durable physical route journal](../reports/AUDIT-Q25-ROUTE-JOURNAL.md): intent/confirmed ownership, boot/cookie/TUN scope, shared lock and terminal roaming on I/O failure. Baseline left bypass/blackhole after SIGKILL → reconnect → stop (3 FAIL). 2087 Linux + 43 privileged + 8 lifecycle; 17/17 cases, 489 assertions PASS. Physical client route recovery is closed within the stated scope; legacy global DNS, live persistent TUN and mixed firewall keep D04 IN_PROGRESS.

D04/D05/D09: [Q25-F101 — legacy global DNS](../reports/AUDIT-Q25-LEGACY-DNS.md): unsafe automatic replay and PID refcount removed; snapshot/holders require manual recovery without reading contents or waiting on locks. Baseline changed the resolver in 4 cases; new contract 47/47 PASS. 2078 Linux + 43 privileged + 8 lifecycle; 17/17 cases, 489 assertions PASS. Legacy global recovery closed by safe refusal; live persistent TUN and mixed firewall keep D04 IN_PROGRESS.

D04/D09: [persistent TUN/TAP after SIGKILL](../reports/AUDIT-Q25-PERSISTENT-TUN.md): safe refusal preserves interface/routes/DNS/firewall; recovery succeeds after explicit removal of a verified orphan. 17/17 rows, 506 main assertions; 17 persistent scenarios with 199 detailed checks PASS. No new defect; Rust unchanged. This portion of D04 is closed within the stated boundary; D04 IN_PROGRESS for the full mixed firewall matrix.

D04/D09/D10: [server mixed nft/legacy/firewalld recovery](../reports/AUDIT-Q14-MIXED-FIREWALL.md): 16/16 scenarios, 476 checks PASS. Actual per-family backend switches, native nft parse errors, firewalld reload, partial cleanup and manual recovery verified. Unknown absence retains evidence; the lost WAN sysctl witness remains the D02 manual boundary. Rust unchanged. D04 IN_PROGRESS: mixed firewall client kill-switch/DNS/routes packet recovery is still required.

D04 closed: [Q25-F102 and client mixed firewall matrix](../reports/AUDIT-Q25-CLIENT-MIXED-FIREWALL.md): 152/152 network cells, 136 SIGKILL/recovery cases, 4880 main assertions and 3224 nested checks PASS. All 4352 direct UDP attempts under protection were blocked; 2624 allowed probes received replies. The shared classifier now handles exact legacy advice; server 16/16, 476 checks reran PASS. Persistent TUN/sysctl/legacy DNS manual boundaries remain. **Debt total: 4/15 DONE (26.7%), 9 IN_PROGRESS, 2 TODO.** This does not complete full-audit sections; D05/D06 and D09/D10/D13 remain open.

D05/D09: [Q25-F103 — shared DNS/NSS and shutdown](../reports/AUDIT-Q25-SYSTEM-RESOLVER.md): four unfinished calls, queue-inclusive deadline, retained capacity after cancellation and no blocking-pool shutdown wait. 4 baseline failures and 4 fixed PASS; 38/38 hostname cells, 34 crash/recovery, 1220 main and 806 nested checks PASS. 1537 host + 71 config; 2089 Linux + 44 privileged + 8 lifecycle PASS. D05 stays IN_PROGRESS: network-mutation scheduler isolation, internal locks/I/O and whole NetworkPlan/shutdown. **Debt: 4/15 DONE (26.7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F104 — resolver files before firewall](../reports/AUDIT-Q25-RESOLVER-FILES.md): one bounded snapshot, shared reader/parser with stub checks, exact keyword, comments and retained scope. 7 baseline/fixed pairs; 2 old hangs, all 7 fixed runs clean. 38/38 cells, 34 crash/recovery, 1220 main and 806 nested checks PASS. 1544 host + 71 config; 2098 Linux + 44 privileged + 8 lifecycle PASS. D05 stays IN_PROGRESS: network mutations, internal locks/I/O and whole NetworkPlan/shutdown. **Debt: 4/15 DONE (26.7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F105 — applying NetworkPlan outside the async executor](../reports/AUDIT-Q25-NETWORK-TASK.md): a fresh thread retains ownership and the original NET/mount context until adoption or completed rollback; native ACK uses async sleep. 7 new portable + 1 Linux + 1 privileged regressions; synchronous helper counterfactual FAIL, fixed PASS. Real TCP/UDP × TUN-create/ip-up: 4/4 PASS with a responsive current-thread runtime, joined rollback and exact network restoration. 38/38 cells, 34 crash/recovery, 1220 main and 806 nested checks; 1551 host + 71 config; 2106 Linux + 45 privileged + 8 lifecycle PASS. D05 remains IN_PROGRESS: established-tunnel teardown, kill-switch mutations, locks/I/O/diagnostics and whole NetworkPlan/shutdown deadlines. Forced Drop may block until join. **Debt: 4/15 DONE (26.7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F106 — graceful teardown of established tunnels](../reports/AUDIT-Q25-TUN-TEARDOWN.md): shared TCP/UDP TunGuard shutdown preserves DNS → pump join → routes/forwarding and runs network cleanup on one joined worker. Worker failures enter sticky Failures. 5 new portable + 1 privileged test; baseline TCP/UDP produced 0 heartbeat ticks during held cleanup, fixed produced 7–8. 4/4 fixed scenarios and 2/2 explicit restarts after faults PASS; kill-switch retained on failure. 38/38 cells, 34 crash/recovery, 1220 main and 806 nested checks; 1556 host + 71 config; 2111 Linux + 46 privileged + 8 lifecycle PASS. D05 remains IN_PROGRESS: early error/Drop paths, kill-switch mutations, locks/I/O/diagnostics and whole NetworkPlan/shutdown deadlines. **Debt: 4/15 DONE (26.7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F107/F108 — firewall workers and retained DROP](../reports/AUDIT-Q25-FIREWALL-TASK.md): setup/refresh and all six terminal cleanup paths await owned workers; unconfirmed unhook forbids chain flushing. 8 new regressions, 8 baseline + 12 fixed runtime scenarios; baseline passed 6 UDP probes after cleanup failure, fixed passed 0. 38/38 cells, 34 crash/recovery, 1220 main + 806 nested checks; 1564 host + 71 config; 2119 Linux + 46 privileged + 8 lifecycle PASS. Original wildcard UDP recovery FAIL retained: explicit-bind rerun passed; multi-IP wildcard remains D06/D10. D05 remains open for startup recovery, early Drop, locks/I/O/diagnostics and whole deadlines. **Debt: 4/15 DONE (26.7%), 9 IN_PROGRESS, 2 TODO.**

D06/D09/D10: [Q15-F002 — wildcard UDP reply address](../reports/AUDIT-Q15-UDP-LOCAL-ADDRESS.md): pktinfo survives receive through immutable reply/roaming/PMTU paths. Baseline secondary IPv4 connections fail with 96 wrong-source replies; fixed has 8/8 IPv4/IPv6 × plain/obfs connections, 256/256 inner UDP echoes and original refresh-fault recovery PASS. 6 new Linux + 1 privileged regression; 1564 host + 71 config; 2125 Linux + 47 privileged + 8 lifecycle; 38/38 cells, 34 crash/recovery, 1220 + 806 checks PASS. Wildcard defect closed within report boundaries; overall D06/D10 and D05 remain open. **Debt: 4/15 DONE (26.7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F111 — ordered diagnostics writer](../reports/AUDIT-Q25-STATUS-WRITER.md): one thread, one pending snapshot, joined final write; file I/O outside the async executor. 5 new portable + 1 privileged test; 2 baseline + 4 fixed fsync cases, 2 baseline + 4 fixed TCP/UDP teardown and 2 recoveries PASS. 1569 host + 71 config; 2133 Linux + 48 privileged + 8 lifecycle PASS. D05 remains open: other locks/I/O, early Drop and the overall deadline. **Debt: 4/15 DONE (26.7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F112/F113 — identity files](../reports/AUDIT-Q25-IDENTITY-FILES.md): ID loads once on a joined worker and temporary identity survives reconnect; TOFU is capped at 1 MiB, corrupt/conflicting pins reject new trust, writes are atomic. 15 new tests; 8 baseline + 8 fixed identity cases, 6 teardown cases and 2 recoveries PASS. 1575 host + 71 config; 2148 Linux + 48 privileged + 8 lifecycle PASS. D05 remains open: synchronous TOFU, other startup I/O/Drop and overall deadlines. **Debt: 4/15 DONE (26.7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F114 — TOFU worker](../reports/AUDIT-Q25-IDENTITY-WORKER.md): one joined thread owns trust-file I/O; stop and timeout retain admitted writes and late errors until terminal result. 9 portable regressions; 16 worker cases + 16 file cases + 6 teardown and 2 recoveries PASS. 1584 host + 71 config; 2157 Linux + 48 privileged + 8 lifecycle PASS. Overall deadlines and other startup I/O/Drop remain D05. **Debt: 4/15 DONE (26.7%), 9 IN_PROGRESS, 2 TODO.**


### Q25-F205 — panel client shutdown, 1 October 2026

A concrete D05 remainder is resolved: outbound-client shutdown no longer adds
five seconds per profile. Every manager-owned process receives SIGTERM concurrently
and shares the original five-second grace, including registry admission.
The first shutdown request closes Connect/autostart admission; repeated or cancelled
waiters do not reset the deadline. Forced kill, unsuccessful exit and signal/wait errors
reach the supervisor terminal result together with the main worker failure.

Disconnect retains the original Child until reaping even when its HTTP waiter is
cancelled. A per-profile lock prevents replacement while that process is still cleaning
up; status checks for other profiles do not wait for it. Shutdown creates no detached
handle owners, and observed failures survive waiter cancellation. Five new process
regressions plus existing autostart: **6/6**; related supervisor **19/19**, shutdown
**10/10**, profile tasks **19/19**, total **54 PASS**. Rustfmt PASS. Rust 1.97 Clippy
passed with `-D warnings -A clippy::useless_conversion`; without that exception it
failed on two unchanged portable UDP conversions. Both outcomes are retained.

[Machine evidence](../../../release/certification/evidence/client-shutdown-20261001.json)
contains hashes of all 287 tested Rust files, the test binary SHA, outputs and raw hashes.
The lab's working PID 845, listener 443 and release SHA `a526c03b` were preserved.
Tests use real child processes without network mutations; no new release VPN/E2E or
benchmark was run. The original sequence was established by production-source review;
the old release binary was not executed for this finding.

D05 remains IN_PROGRESS: async joining before resource destruction during forced Drop
and the total worker/supervisor shutdown wall-clock bound. Five seconds bounds only
outbound-client grace; kernel reaping/fs I/O is not promised to be interruptible.
D11/D14 evidence and **9/15** above describe tested candidate `62c84fc4`.
This server change modifies the native source digest and release tree; old provenance
and certification do not certify the new HEAD. Build evidence and certification refresh
belong to final D15 package assembly, rather than rerunning unchanged transport/firewall
matrices after every local fix.

### Q25-F206 — profile resources after forced cancellation, 2 October 2026

The D05 async-join/host-cleanup ordering item is closed. Previously Drop requested
task cancellation and immediately released TUN/DNS/NAT while a descendant could
still be running its destructor. ProfileScope now transfers both generation resources
and joinable task sets to the worker. The worker joins them before resource deletion,
the global NAT sweep and terminal hooks. Cancelling the drain requeues the entire
generation; no detached cleanup owner is created. Forced cancellation remains a
terminal failure even after successful cleanup. If the worker future itself is
destroyed, unfinished resources and its network lease remain retained until process
exit; a replacement in-process worker is rejected.

A regression with real TUN and DNS INPUT rules delays a descendant Drop. Its control
invokes the unchanged production ProfileTeardown destructor directly: **expected FAIL**,
resources disappear too early. This exercises the previous ordering with the same
test binary, rather than executing an old release. The fixed guard: **1/1 PASS**,
including cancelled initial drain, retained resources and repeated joining.
Ordinary teardown **13/13**, profile tasks **19/19**, shutdown **10/10**,
supervisor **19/19**, panel clients **6/6**, totaling **67 unit PASS**.
The current debug binary passes **8/8** live worker TCP/UDP × off/manual/route/nat66
with reload, second-worker rejection, SIGTERM and network-state restoration.
Full parent-host snapshots match; the working listener 443/PID 845 is preserved.

[Machine evidence](../../../release/certification/evidence/deferred-profile-20261001.json):
287 verified Rust source SHA pairs, test/debug binary SHA, commands, results,
raw hashes and host snapshots. Rustfmt PASS; Rust 1.97 Clippy PASS with the existing
exception for two portable UDP conversions: `-D warnings -A clippy::useless_conversion`.
The first compilation failed on mutability and the first build command on a driver
path; corrected runs succeeded and the initial logs are retained.

**D05 remains IN_PROGRESS for the overall shutdown budget within the stated limits**:
this fix adds no single wall-clock deadline and cannot interrupt kernel/fs I/O.
Historical **9/15 DONE (60%)** and D11/D14 apply to candidate `62c84fc4`;
the new HEAD requires final native/provenance/certification refresh under D15.

### Q25-F207 — concurrent worker and panel-client stop, 2 October 2026

Sequential supervisor shutdown composition is fixed. Previously outbound-client stop
began only after supervise returned, potentially 60 seconds after the signal.
Connect/autostart remained open until then, and the client grace was added after
worker waiting. Handling SIGTERM/SIGINT now synchronously closes client admission
before the worker's SIGTERM. One coordinator polls both supervisor-owned waits
concurrently and returns both results; it creates no detached tasks. Supervise
completion without a separate stop signal also starts client cleanup. Cancelling
the coordinator preserves existing guards and the manager's original deadline;
neither path's failure is discarded.

Targeted shutdown **13/13**, panel clients **7/7**, supervisor **19/19**,
notifications **8/8**: **47 PASS**, including four new regressions.
Live checks launch real supervisor/worker/client processes in separate NET/mount/PID
namespaces. The retained Q25-F206 debug binary reproduces sequential waiting:
with an eight-second post_down the client is still alive at 6.20 seconds,
and the total stop takes 13.24 seconds. The current debug binary reaps the client
at 5.02 seconds while the worker hook is still running; total stop takes 8.25 seconds.
Both supervisors return expected exit 1: the TCP peer deliberately leaves handshake
unanswered, forcing client kill and leaving its VPN cleanup unconfirmed.
This verifies delay/reaping and failure reporting, rather than a successful VPN handshake.

Both runs remove worker TUN/tagged NAT, restore the original forwarding value and
reap every child. Full parent-host snapshots match; listener 443/PID 845 and the
working release SHA are preserved. Rustfmt PASS; Rust 1.97 Clippy PASS with the existing
`-D warnings -A clippy::useless_conversion` exception. Evidence retains SHA for 287
sources, both debug binaries and the test binary, initial compile/fixture failures and
corrected runs. Full transport/benchmark matrices were not repeated.

Checks and exact SHA are recorded in
[machine evidence](../../../release/certification/evidence/stop-composition-20261002.json).
This fixes composition of existing grace periods rather than adding a single worker
shutdown deadline. Notification waiting, async joins, blocking host cleanup and kernel
reaping retain their documented limits. **D05 remains IN_PROGRESS**; final native
rebuild and release certification after server changes remain D15. Historical
**9/15 DONE (60%)** apply to the verified candidate `62c84fc4`.


### Q25-F208 — total CLI shutdown and notifications, 2 October 2026

The final D05 criterion is closed within its declared boundaries. CLI workers start
an OS-thread **45-second** clock, independent of Tokio, on the first observed stop/fatal
event before stop diagnostics. It remains armed through control handlers, services,
profile/deferred joins, NAT/sysctl, hooks, counter persistence, control-socket removal
and final logging. Repeated arm does not refresh it; cancelling the owning future does
not revoke an armed timer. Normal completion disarms and joins its thread. Late
completion cannot win merely because the monitor was scheduled late.

On expiry the worker closes command admission, kills tracked groups of owned commands
whose leaders remain unreaped, and calls `_exit(124)` without Rust Drop, logging or C
atexit. Spawn/reap/group signalling share one registry to prevent signalling a recycled
PGID. The supervisor classifies 124 as a deadline failure with cleanup unconfirmed.
Normally detached background services with closed pipes retain their existing contract.
Worker and supervisor notifications close admission and retain their original ten-second
grace from stop; draining runs concurrently with cleanup. The supervisor retains sixty
seconds for its worker and five for clients, polling all owned waits concurrently.

**136 targeted unit PASS**: process budget 6, notifications 9, supervisor 20,
shutdown 13, teardown 13, profile tasks 19, hook process 15, credential supplier 13,
system commands 21, panel clients 7. Eight new regressions include real child processes
with a stalled Tokio executor, timer-owner cancellation and exit 124. This is a targeted
set, not a new execution of all 2317 unit tests.

In isolated NET/mount/PID namespaces the retained Q25-F207 debug binary remains alive
48 seconds after stop when one post_down metadata call is delayed for sixty seconds.
Only the harness terminates it. The new worker exits itself after forty-five seconds
with code 124; another post_down starts a shell and sleep after thirty-five seconds of
preparation. The controller reaps the owned group leader and sleep with SIGKILL and
checks that every observed member has disappeared from `/proc`. TUN/tagged NAT are gone;
the unfinished sysctl journal remains. The next ordinary worker recovers forwarding and
exits normally with zero. Foreign INPUT rules, routes and other settings are preserved.
**8/8** ordinary TCP/UDP × off/manual/route/nat66 lifecycle cases with reload, refusal
of a second worker and stop PASS. Full outer-host snapshots match; the working listener,
PID and release SHA are preserved.

[Evidence](../../../release/certification/evidence/worker-budget-20261002.json) retains
288 verified Rust SHA values, test/debug SHA, commands, the initial Clippy failure and
correction, and the first fixture failure and corrected child-reaping assertion. The
outer shell could reap its script child before dying itself; requiring that child's
wait status again was a harness error. The corrected assertion requires SIGKILL for
the group leader and sleep and disappearance of every observed PID. Rustfmt, all nine
docs checks and diff PASS; Rust 1.97 Clippy PASS with the existing
`-D warnings -A clippy::useless_conversion` exception.

The limitation is justified: this is a CLI process boundary after an observed stop,
not an absolute guarantee from OS signal delivery. Preparation before shutdown, library
`run_worker`, arbitrary kernel exit/reaping and stalled spawn under the registry are not
safely preempted; library cancellation retains resources/namespace quarantine. Kernel
failure has no exact wall-clock guarantee. An application filesystem worker and an active
hook group are verified with real process exit and recovery. These limits are not reported
as PASS for arbitrary kernel failures. **D05 DONE; register: 10/15 DONE (66.7%),
5 IN_PROGRESS**. Final native/provenance/certification refresh remains D15; the historical
candidate `62c84fc4` certificate does not certify current HEAD.

### Q25-F209 — mixed configuration lifecycle, 2 October 2026

The remaining D07 scope is closed after the global and profile field matrices.
A new reproducible [harness](../../../scripts/audit_panel_config_lifecycle.py) exercises
the real HTTP panel, supervisor and TCP/UDP worker in private NET/mount/PID namespaces.
Rust code is unchanged: no new production defect was found in these scenarios.
The generator again confirms 163 parser names, three dynamic families and a current
165-entry fixture; this is parser coverage, not 165 separate network E2E cases.

**201 targeted unit tests PASS**: server 78, INI 22, config_source 16, panel config 38,
control 7, backup 32, status 4, preflight 4. All three privileged backup tests ignored
by the ordinary suite ran separately in isolation: exact/overlay roundtrip, rollback
refusal for an unreadable file, and ownership during slow backup I/O. The last also
ran with cancellation: **4 executions PASS**. Initial `server::web::api::*` filters
selected zero tests and are not counted; corrected `web::api::*` runs require a
nonempty selection for every group.

**44/44 HTTP/runtime checks PASS**: invalid INI/form/privileged-hook refusal;
mandatory revisions, stale tabs and exactly one concurrent-write winner; waiting
for an external process holding the shared lock and preserving its bytes on conflict;
live web versus saved profile versus startup-only web; refusing restart before
stopping a healthy worker; explicit restart applying a new TCP bind; Quick Start/
check-config/history rollback; malformed archive and exact restore preserving the
lock inode and identity; password rotation revoking the old cookie without restart;
normal stop restoring forwarding, TUN and foreign firewall rules. Identity survives
all operations. The first intermediate run had 43 checks; the final harness adds an
end-to-end identity comparison and reports PASS only after completing the scenario.

The [panel manual](../manuals/PANEL.md#server-config-writers-v1) defines the boundary:
every cooperative external writer must flock the canonical `<config>.lock` from
read through publication. Revision and the second check detect a completed manual
edit or changes during preparation. An arbitrary root writer ignoring that lock
between the final check and rename cannot be made atomically coordinated. This is
an explicitly unsupported writer protocol, not a PASS. Such editing requires stopping
Qeli, finishing competing panel/CLI writes, validating INI and starting again.

All 288 Rust inputs and debug/test SHA match the preceding exact-build evidence.
No new build, Clippy or full benchmark matrix ran in this batch. Full external `.11`
host snapshots match before/after both sets; the running release and listener
443/PID 845 are preserved; `.10` is untouched. Commands, SHA, results and raw manifest:
[machine evidence](../../../release/certification/evidence/config-mixed-20261002.json).
Network combinations remain D10 and final native/certificate refresh remains D15;
this is not certification of current HEAD or completion of the whole 37-step audit.
**D07 DONE; registry: 11/15 DONE (73.3%), 4 IN_PROGRESS — D06/D08/D10/D15.**

### Q25-F210 — client store ownership and D08 closure, 2 October 2026

D08 is closed within the available scope, retaining the agreed D12 exclusions.
Q25-F197 covers all 84 shared INI editor fields and 1000 deterministic mutations.
Its Rust code is unchanged; no new coverage-guided fuzzing is claimed. External
writers are bounded by the protocol below. Automatic reconnect and Wi-Fi transition
are covered by preceding Android VPN E2E Q25-F203, not by a new traffic run here.
Unavailable Mac/iOS/Windows VM/router checks remain **SKIPPED by user decision**,
not PASS; full mobile lifecycle and release delivery remain the full audit.

A second iOS writer was found and removed: when the archive was absent,
`ProfileStore.load()` saved a template in PacketTunnel as well as in the app.
During first publication the extension could overwrite the app's profiles with its
template. Only initial AppModel now explicitly allows missing-store initialization;
PacketTunnel and ordinary load are read-only and fail for an absent archive.
Reading existing ciphertext no longer creates a missing master key: it preserves
the encrypted original and requests backup recovery. Two XCTest regressions and
EN/RU messages were added. XCTest and iOS compilation **did not run** because the
Apple lab is excluded; call sites, guard ordering and absence of write/key-create
in the reader branch were reviewed. A single `@StateObject AppModel` serves the
WindowGroup on MainActor; PacketTunnel reads and widgets cannot access profiles
or keys. There is no second app-owned profile writer among these processes;
arbitrary external-process UserDefaults transactions are not promised atomic.

A new desktop conformance regression launches **two independent OS processes**:
both read one initial version, exactly one publishes, the other refuses; winner
bytes and `.bak` survive and a fresh reader writes after both exit. Full .NET
selftest: **511 PASS, 0 FAIL**, exact Windows DLL SHA `653522e6`. The first run placed
build artifacts outside the tree, could not find boundary corpus and reported one
FAIL. Corrected ordinary project output executes that corpus, including 19 additional
checks. The initial refusal is retained and not counted as PASS.

Android: **167 JVM, 0 failures/errors/skipped**; debug and androidTest APKs built.
**12/12 instrumentation PASS** on Android 14/API 34 x86_64 AVD, including real
INI → packaged JNI → AES-GCM/Keystore → re-read after a port edit → stale-write refusal.
This tests storage/adapters, not a new VPN handshake or UI editing during active VPN.
Both APK `.so` files equal committed A/B libraries. No native rebuild ran here;
final refresh remains D15. The read-only AVD exits without saving; userdata hashes
and the full external host snapshot match; working release/listener 443/PID 845
are preserved and `.10` is untouched.

Supported writing: desktop instances use shared ProfileStoreFile, sidecar and
observed revision; Android Activities share one process/SharedPreferences with an
encrypted version; iOS uses the single app writer. Edit/import INI through the app,
not by changing the encrypted store. Arbitrary external writers bypassing coordination
are unsupported: hash/revision does not close the final check-to-rename gap. Store
maintenance requires finishing all writers and using supported backup restoration.
Editing saved active INI does not rewrite an existing session; reconnect explicitly
when the app requests it. Previous reconnect E2E is not counted as a new execution.

[Checks and SHA](../../../release/certification/evidence/client-store-20261002.json).
**D08 DONE; registry: 12/15 DONE (80%), 3 IN_PROGRESS — D06/D10/D15.** This is not full
audit completion, iOS runtime PASS or certification of current HEAD.

### Q25-F211 — combined IPv6/DNS/NDP matrix, 2 October 2026

Added a reproducible [isolated runtime scenario](../../../scripts/audit_worker_ipv6_multiprofile.py):
four real dual-stack `off/manual/route/nat66` profiles, two TCP and two UDP, a shared
WAN, independent DNS listeners and required NDP responders on `manual`/`route`.
Real **iptables-nft and iptables-legacy: 59 checks each, 118 PASS total**.
Checks cover off DROP, no manual IPv6 rules, source-preserving route, nat66 MASQUERADE
and off-WAN guard, protective DROP ordering, shared forwarding/RA leases, invalid
SIGHUP refusal and unchanged network generation on valid reload.

Each backend executed **32 DNS queries** across four profiles: IPv4/IPv6 × UDP/TCP ×
A/AAAA. Upstream received only eight queries: cache is shared between frontend
transports within one profile and independent between profiles. Standalone `manual`
returned two additional IPv6 DNS answers with initial `forwarding=0` and unchanged
RA/IPv6 firewall. DNS originated on the server: this tests the real proxy/listeners,
not encrypted VPN traffic or TUN INPUT/port 53 redirection packet paths. Both NDP
responders actually bound; upstream NS/NA replies for active session leases are not
validated by this batch.

With a missing required `ndp_proxy_interface`, the profile admits no clients and
never runs post_up. The worker remains alive and retries the profile: required NDP
does not mean termination of other profiles. After SIGTERM the test compares exact
foreign rules/policies, routes, link flags (including ALLMULTI), sysctl values and
removal of the control socket/sysctl journal. Four-profile stop, manual-only stop
and stop following NDP refusal restore baseline on both backends.

Three intermediate fixture failures are retained and not counted as PASS: the first
two compared a baseline without yet-created empty nat/mangle tables; nft `-S` reads
do not instantiate them. The fixture now creates/removes an empty private chain
before taking baseline. The third incorrectly expected worker termination instead
of supported rejected-profile retry. No production Rust changes were required.
All 288 local/remote source SHA and debug SHA match previous exact build evidence;
no fresh build/Clippy/benchmark was run. External host snapshots match across all
four attempts, working release/listener is preserved, `.10` was untouched.
[Commands, SHA and raw manifest](../../../release/certification/evidence/ipv6-multiprofile-20261002.json).

**D10 stays IN_PROGRESS:** upstream NDP packet tests for active/inactive leases and
remaining mixed firewall/firewalld and lifecycle combinations are still required.
WAN changes/identity stay D06; final native/certificate refresh stays D15.
**Registry: 12/15 DONE (80%), 3 IN_PROGRESS — D06/D10/D15.** This fraction concerns
technical-debt groups, not the entire 37-step audit.

### Q25-F212 — NDP for active sessions and prefixes, 2 October 2026

Closed the D10 packet-level NDP component for `required` in `route` and `manual`:
**8/8 `route/manual × TCP/UDP × nft/legacy` cells, 31 checks each, 248 PASS total**.
The new [scenario](../../../scripts/audit_ndp_session_packet.py) launches a real worker
and authenticated CLI client in separate client/router/server namespaces. Upstream
considers the pool and delegated prefix on-link and sends NS to the server WAN;
no SessionMap injection or simulated firewall response is used.

Executed **128 packet probes, 384 Ethernet NS**. Each cell has a positive control:
kernel NDP on the WAN. Before connection, no NA covers the reserved `/128` or
`client_subnet`; after handshake, both addresses receive correct proxy NAs, while a
free pool address and unowned prefix receive none. Checks validate Ethernet MAC,
IPv6 source/destination, hop limit, ICMPv6 checksum, target/TLLA and Solicited/Override
flags. DAD receives all-nodes NA with both flags clear; wrong hop limit/checksum and
DAD with SLLA are rejected. Hex of every sent NS and received NA is retained.

The external router actually pings the assigned address and a client-side
`client_subnet` address through the encrypted VPN; no NAT66 is present. On normal
client stop the test waits for control registry removal (including UDP idle expiry/
maintenance), then fresh NS receives no NA for either lease or delegated prefix.
The prefix kernel route is retired. A new handshake restores ownership and both
addresses' NAs. Stopping the worker ends replies and restores exact foreign firewall
rules/policies, routes, link flags and IPv6 sysctl; control socket/sysctl journal are
removed. For `manual`, forwarding and permits are administrator-provided beforehand
and preserved; Qeli does not acquire their ownership.

Corrected the [IPv6 guide](../manuals/IPV6.md): stopping a client process does not
always mean immediate server session removal. While a UDP session remains until
idle/liveness timeout/cleanup, or a roaming grace period applies, NDP can still
reply for it. Test reply retirement after session removal/revoke; an old upstream
neighbor cache entry alone does not prove a fresh responder reply.

Two intermediate fixture failures are not counted as PASS: check-config correctly
rejected a 1000ms interval with default 5000ms jitter; the next initial snapshot
preceded WAN link-local DAD completion. Preparation now sets jitter=0 and waits for
the original link-local address; strict restoration comparison remains. Production
Rust is unchanged. All 288 local/remote source SHA and debug SHA match previous exact
build evidence; no fresh build/Clippy/benchmark. External host snapshots match across
all three attempts, working release/listener is preserved, `.10` was untouched.
[Results, commands, SHA and raw manifest](../../../release/certification/evidence/ndp-packets-20261002.json).

This is not a new packet test of `/0`, rate saturation, VLAN, admin revoke/active owner
replacement or SIGKILL NDP. Multiple-profile mixed firewall/firewalld reload/policy
combinations stay D10; WAN identity stays D06, final certification stays D15.
**Registry: 12/15 DONE (80%), D06/D10/D15 IN_PROGRESS.** NDP packet lifecycle is
validated; the entire D10 and full 37-step audit are not closed by this batch.

### Q25-F213 — multiprofile, mixed backends and firewalld policies, 2 October 2026

Closed the remaining D10 integration component: **4/4 IPv4/IPv6 pairs nft/nft,
nft/legacy, legacy/nft, legacy/legacy, 104 checks each — 416 PASS**.
The [four-profile scenario](../../../scripts/audit_worker_ipv6_multiprofile.py) now
uses an [isolated firewalld fixture](../../../scripts/audit_firewalld_profiles.py).
Real `off/manual/route/nat66` TCP/UDP profiles, manual/route required NDP and firewalld
2.3.1 public zone with a public → HOST priority -500 policy run together. Real copied
xtables multicall binaries are selected independently for IPv4/IPv6; command output
and rules are not mocked. SHA of all 17 original Debian packages was verified.

An external veth peer tests permitted UDP 49000 and policy-denied 49001: **96 packet
probes, 288 datagrams, 168 validated echo replies**; 120 denied sends receive no reply
within 250ms per packet. Removing the rich DROP actually opens 49001, restoring it
blocks IPv4 and IPv6 again. Firewalld reload with active profiles, after stop and after
restart preserves exact Qeli/foreign rules. A new generation may reorder independent
profiles while preserving each profile/table/chain order and mandatory DROP before
ACCEPT. Reload within one generation compares the full snapshot.

Each cell validates 42 DNS answers: initial 32 IPv4/IPv6 × UDP/TCP × A/AAAA, four after
policy changes, four after restart and two manual-only; **168 total**. Profile caches
are independent and policy changes retain cache. Invalid SIGHUP preserves active
state; valid SIGHUP retains the network generation. Manual-only preserves original
administrator forwarding/RA and IPv6 firewall; a missing required NDP interface
refuses admission/post_up while supported worker retry continues. All four stop
phases restore both backends, native nft, routes, sysctl/link flags, control socket
and journal to baseline.

Targeted suite: **18 portable PASS and one separately executed privileged PASS** on
the exact test-binary SHA. Coverage includes IPv6/NDP combinations, INI round-trip,
interface selection, lease/prefix/session ownership, malformed NS/DAD/NA, rate bound
and namespace bind; the `ndp` substring filter also selects several endpoint tests.
The initial wrong native module path was caught at listing before execution and is
not counted as PASS. Two early runtime failures were fixture defects: INPUT DROP
blocked IPv6 ND, then baseline contained synthetic iptables-save headers without six
empty native nft hooks. Preparation now permits ICMPv6 only on the control veth and
adds/deletes a temporary rule before baseline. Strict comparison remains; production
Rust is unchanged. All 288 local/remote source SHA and debug/test artifacts were
verified, so prior exact build evidence applies. No new build/Clippy/benchmark.
External host snapshots match for final and earlier attempts; working release/service
is preserved and `.10` was untouched.
[Commands, SHA, results, initial failures and raw manifest](../../../release/certification/evidence/firewalld-profiles-20261002.json).

D10 closure uses the following independent evidence:

| Criterion | Confirmation |
|---|---|
| off/manual/route/nat66, DNS/NDP, rollback/stop | Q25-F211: 118 checks; this batch repeats composition on four mixed backend pairs |
| Active/inactive NDP leases and delegated prefix, real VPN | Q25-F212: 8 packet cells/248 checks; this batch's targeted NDP tests |
| Foreign resources and mixed crash/recovery | D04: server 16-cell/476-check and client 152-cell matrices |
| Concurrent TCP/UDP, reload/stop/SIGKILL/recovery, churn | D13: 14 multiprofile lifecycle checks and prior same-SHA churn |
| Multiple IPv6 profiles with firewalld reload/policy | This batch: 4 mixed cells/416 checks, real positive and negative policy probes |

Validation boundaries remain: DNS originates on the server toward a real proxy port,
and control firewall traffic targets an independent echo listener. This is not a new
VPN forwarding packet test through every public zone/policy or TUN INPUT/port-53.
Arbitrary root rewrites, automatic backend migration and every possible firewall
policy are not certified; Qeli preserves foreign restrictions and the administrator
provides topology permissions. `/0` and rate bounds have unit coverage, but no new
packet saturation/VLAN/admin-revoke/SIGKILL NDP tests were run. Physical provider
networks and user-excluded platforms are not reported as PASS.

**D10 DONE within this Linux scope. Registry: 13/15 DONE (86.7%), 2 IN_PROGRESS —
D06 and D15.** WAN identity/runtime route changes and final native/certificate refresh
remain open. This fraction covers technical-debt groups, not the entire 37-step audit.
The next batch addresses D06's remaining external network context table.

### Q25-F214 — external network context and late addresses, 2 October 2026

Executed one targeted D06 batch on the exact current test binary:
**73 portable + 23 privileged executions PASS**. The new
[runner](../../../scripts/audit_external_context.py) uses existing Rust regressions
and real independently selected xtables backends for IPv4/IPv6. Production Rust is
unchanged; no new build, Clippy, full benchmark or native refresh. All 288 local/remote
source SHA and test/release SHA match the
[exact build evidence](../../../release/certification/evidence/config-mixed-20261002.json).

On **4/4 nft/nft, nft/legacy, legacy/nft, legacy/legacy pairs**, three native scenarios
run: late IPv4 default route, late global IPv6 plus default route, and refresh/cleanup/
restart after moving to a foreign network namespace. Total **12 native executions**,
eight covering dynamic addresses/routes. Protection is installed before the route/
address appears; real ICMP then increases the existing kill-switch DROP counter.
The namespace scenario preserves a foreign sentinel and refuses mutations in the
wrong context. This is packet counter proof, not an external receiver response test:
there is no external receiver on the dummy WAN.

The remaining suite runs once: 11 WAN-discovery, 23 exit-policy, 11 resolver-context,
18 attach-policy, 3 terminal-writer, 5 process-admission and 2 interface portable
tests; eight real TUN ioctl and three native context tests. Coverage includes missing/
borrowed/multiqueue TUN, fd cleanup after rename/replacement, foreign namespaces and
same-name/different-index sysfs rejection; interface MAC/index and TAP/hooks use the
calling namespace. Resolver refuses a foreign network before mutation. Admission
lasts through terminal completion, refuses overlap before reading configuration and
remains closed after forced Drop. Portable filters temporarily ignore three native
fixtures: two execute separately; the real-resolved child was not run or counted as
PASS here. Its previous packet/PID/bus checks retain separate evidence.

| D06 boundary | Reconciliation and current contract |
|---|---|
| DNS / D-Bus / procfs | Context guards rerun PASS; real resolved, AUTH GUID/unique owner, PID/network and marker recovery — prior Q25-F094/F095/F096/F097. Supported shared network/PID context and trusted resolver are required; no service fixture rerun here. |
| sysfs / link observation | Native interface/TAP/hooks PASS without sysfs remount; sysctl namespace pins/cookie/witness are closed by D02. Observation is not atomic protection against another root. |
| TUN attach / name / features | 18 policy + 8 native PASS. External manager holds device/format stable. `dev_attach` requires matching namespace sysfs; equal numeric ifindex in separate namespaces does not prove identity. This unsupported combination is not reported fixed. |
| DNS/carrier globals | 3 writer + 5 admission PASS; one Linux run_client per process through cleanup, forced Drop requires process restart. Independent clients use separate processes. |
| Late IPv4/IPv6 | 8/8 native executions on four mixed backend pairs PASS; prior missing-firewall refusals Q25-F121/F122 still apply. DHCP/RA daemon rollout and every dynamic route are not certified. |
| Client default WAN | 11 discovery + 23 exit-policy models PASS; real TCP/UDP monitor previously checked in Q25-F127. No new mixed monitor packet test here. |
| Server WAN / identity / policy routes | Q25-F131–F136 retain presence, ECMP/auto-failure and NAT44/NAT66 off-WAN guards. Same-name replacement lacks continuous identity protection; server runtime route/policy composition remains D06 work. |

All fixture changes occur in private NET/mount/PID namespaces; native Rust tests
also create disposable thread namespaces. Full outer snapshot of both backends/nft,
routes, addresses, listener, resolver and named namespaces matches before/after.
Working release/service is preserved; `.10` was untouched.
[Commands, exact selectors/counts, SHA and raw manifest](../../../release/certification/evidence/external-context-20261002.json).

**D06 stays IN_PROGRESS**, but the mixed-backend late-address/route coverage gap is
closed and DNS/sysfs/attach/process-global components need no repeated broad sweep.
Next: WAN identity, server runtime route changes and policy/RFC1918 contract with
packet checks. Unsupported privileged replacements are not relabelled as fixes.
**Registry: 13/15 DONE (86.7%), D06/D15 IN_PROGRESS**.

### Q25-F215 — server default/policy routes and LAN, 2 October 2026

Closed D06's documented server runtime-route/address-plan component: **4/4 pairs
nft/nft, nft/legacy, legacy/nft, legacy/legacy, 51 checks each, 204 PASS total**.
The new [packet runner](../../../scripts/audit_server_route_policy.py) launches a real
worker with concurrent dual-stack TCP NAT44/NAT66 and IPv6-only UDP route profiles,
two real authenticated clients, two WANs and a separate LAN. Qeli installs its rules;
no SessionMap injection or simulated network responses.

Receivers observe IPv4/IPv6 source after decryption, forwarding and NAT in each cell.
Executed **116 packet probes, 348 UDP datagrams, 252 validated echo replies**.
276 sends traverse real VPN; 72 are direct receiver positive controls. 96 sends
correctly receive no reply within 350ms each. For 84, the exact Qeli off-WAN DROP
counter increases (28 checks, delta=3 each); administrator `FORWARD DROP` blocks
the remaining 12.

| State | Observed behavior |
|---|---|
| Selected WAN A | NAT44/NAT66 use WAN A source; route preserves client IPv6 source |
| RFC1918 LAN off-WAN | 10/8, 172.16/12, 192.168/16 reached without NAT under administrator ACCEPT |
| CGNAT/public LAN off-WAN | NAT44 guard blocks 100.64.0.1 and 192.0.2.1; direct controls prove receivers healthy |
| IPv6 LAN off-WAN | NAT66 blocks; route reaches it with original source |
| Administrator FORWARD DROP | RFC1918 LAN closes; selected WAN remains reachable through Qeli's own permit |
| Default A → B | NAT44/NAT66 retain their rule generation and block off-WAN; route follows B without NAT |
| Source policy table100 → A with default B | NAT resumes through A; independent route client continues through B |
| Default restored A | NAT and route work through A without reconnect |
| Source policy → B with default A | NAT44/NAT66 guards block; peer B has positive controls |

After removing policy rules and restoring routes, the exact live snapshot matches:
both family/backend firewall saves/native nft, IPv4/IPv6 route tables and RPDB, link
flags and sysctl. Each of eight client-process logs has exactly one connection
attempt and one successful AUTH throughout the final scenario. Normal client/worker
stop restores initial state and removes the control socket/sysctl journal. Full
outer lab host snapshot matches before/after; working release/service is preserved,
`.10` was untouched.

The guide now explains that server auto-WAN selection occurs at profile installation
and does not automatically move NAT to a new default route. Select a new WAN by
restarting the profile, or provide administrator routing toward its original WAN.
The client exit-node monitor is separate. RFC1918 NAT44 exceptions exclude CGNAT/
public LAN. The initial fixture failure is retained: IPv6-only client mistakenly
received IPv4 includes and correctly refused them after AUTH; its route list was
corrected. Intermediate r2's 160 PASS remain separate: final r3 adds positive
controls, DROP counters and exact RPDB comparison; these are not added to the 204.
Production Rust is unchanged; 288 local/remote source SHA and debug/release SHA match
exact build evidence. No new build/Clippy/benchmark.
[Commands, results, SHA, initial failure and raw manifest](../../../release/certification/evidence/server-route-policy-20261002.json).

These are four selected topology/backend cells retaining devices, not every possible
policy table, obfuscation or physical network. Delegated client_subnet has separate
route/NDP evidence and does not traverse this NAT packet scenario. No new firewalld
daemon run: public-policy/multiprofile proof remains Q25-F213. IPv4 forward_private/
manual runtime paths were not rerun here.

**D06 IN_PROGRESS:** continuous selected-WAN identity across rename/delete/recreate
[Q25-A125](../reports/AUDIT-Q25-WAN-NAME-REUSE.md) is not fixed; the client WAN monitor
requires separate reconciliation of that remaining issue. This batch does not turn
name-based limitations into identity protection.
**Registry: 13/15 DONE (86.7%), D06/D15 IN_PROGRESS**.
