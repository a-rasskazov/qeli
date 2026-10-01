# Technical debt from started audits

<!-- normative-sync: audit-debt-v31 -->

Reconciled on 25 September 2026. At the user’s request, new full-audit sections
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
| D04 | 14/19/22/25 | DONE | Crash recovery | Persistent server firewall, DNS v2, kill-switch and physical routes verified; legacy global DNS, persistent TUN and lost sysctl witnesses have explicit safe manual boundaries. [Client mixed matrix](../reports/AUDIT-Q25-CLIENT-MIXED-FIREWALL.md): 152/152 cells, 136 crash/recovery; [server](../reports/AUDIT-Q14-MIXED-FIREWALL.md): 16/16, 476 checks rerun PASS. Arbitrary zones/policies and multiprofile remain D10; state accumulation remains D13. |
| D05 | 05/14/25 | IN_PROGRESS | Whole-operation deadlines and blocking | Panel preflight/health/backup, DNS/NSS, resolver files, startup INI/identity, TOFU/status writers and network workers checked. Batch A below closes command composition: 15 seconds for NetworkPlan and separate shared 15 seconds for cleanup through Drop and terminal firewall. Linux early-Drop/internal waits reconciled; hook/backup file preparation is closed by the continuation below; ordinary server startup/final cleanup and profile teardown now use joined workers; profile TUN/NAT and DNS firewall setup now also use joined workers; NDP bind now also runs on a worker, with AsyncFd registration in the original runtime; setup through readiness of every listener now has a shared 120-second budget; replacement admission after cancellation is closed by [Q25-F130](../reports/AUDIT-Q25-SERVER-FORCED-DROP-LEASE.md); async joining on forced Drop and the whole-shutdown deadline remain. [Server setup](../reports/AUDIT-Q25-SERVER-SETUP-WORKER.md), [DNS firewall](../reports/AUDIT-Q25-SERVER-DNS-SETUP-WORKER.md), [NDP bind](../reports/AUDIT-Q25-SERVER-NDP-BIND-WORKER.md), [readiness and budget](../reports/AUDIT-Q25-SERVER-SETUP-BUDGET.md). Arbitrary kernel/fs I/O and forced joins are not preempted. [Server cleanup](../reports/AUDIT-Q25-SERVER-CLEANUP-WORKER.md). [Worker ownership](../reports/AUDIT-Q25-IDENTITY-WORKER.md). |
| D06 | 15/21/22/23/25 | IN_PROGRESS | External network-resource context | Verify WAN identity, resolved/bus context, sysfs/procfs and attach/name contracts; process-global DNS/carrier state and dynamic IPv6. Document supported combinations. [Q15-F002](../reports/AUDIT-Q15-UDP-LOCAL-ADDRESS.md) closes multi-IP wildcard UDP: the local endpoint survives receive/reply/roaming/PMTU; [Q25-F131](../reports/AUDIT-Q25-SERVER-WAN-PRESENCE.md) rejects managed IPv4/IPv6 rule setup for an absent WAN; it does not bind active rules to device identity. [Q25-F132](../reports/AUDIT-Q25-SERVER-WAN-ECMP.md) shares the client default-route parser with the server and rejects ambiguous auto-WAN before forwarding/new rules. Explicit WAN and runtime route changes remain open. Other D06 criteria remain open. |
| D07 | 01/05/09/11 | IN_PROGRESS | Server configuration at runtime | Trace field → parse/validate/runtime/serialize; malformed/oversized input; check-config/startup/SIGHUP/HTTP save/Quick Start preserving active state on failure. [Q25-F137](../reports/AUDIT-Q25-SERVER-SIGHUP-AUTH.md) through [Q25-F149](../reports/AUDIT-Q25-SERVER-TLS-PATH-TRUST.md) cover targeted SIGHUP, size, live web state, private INI publication, admission parity, file-path trust, coordinated panel/CLI/restore writes, bounded TLS PEM intake, check-config TLS parity, explicit TLS path trust, and Let's Encrypt panel saves. [Q25-F150](../reports/AUDIT-Q25-SERVER-PANEL-SNAPSHOT-TRUST.md) closes panel identity/Share/users trust bypasses after manual INI edits. [Q25-F151](../reports/AUDIT-Q25-SERVER-PANEL-SAVE-TRUST.md) blocks trust promotion through panel saves, history, and archive commands. [Q25-F152](../reports/AUDIT-Q25-SERVER-FIELD-MATRIX-LOGGING.md) checks parse/serialize coverage of 150 fixed INI keys and requires a full restart for three active logging fields. [Q25-F153](../reports/AUDIT-Q25-SERVER-WEB-AUTH-SAVE.md) rejects an enabled panel without a password or explicit insecure_no_auth in both editors and history restore. The remaining field/path runtime matrix and the race with manual editors that do not take the advisory lock remain. |
| D08 | 02/24/27 | IN_PROGRESS | Shared client configuration | Verify the complete 81+3 field contract, INI/import/URI/QR/form/store/reconnect through real adapters; fuzz/budget and concurrent edits. |
| D09 | 14/15/25/32/33 | DONE | Linux lifecycle and system failures | [Closure evidence](../reports/AUDIT-Q25-LINUX-LIFECYCLE-CLOSURE.md): current SHA 2175 Linux unit, 8 control, 15 hook-process and 8/8 live worker lifecycle PASS, with exit/SHA and before/after network snapshots. Earlier 48 privileged and real DNS/route/firewall matrices still apply to unchanged paths. Full install/upgrade and network combinations remain D11/D10; whole shutdown remains D05. |
| D10 | 17/18/19/21/22/23 | IN_PROGRESS | Network integration matrix | Verify off/manual/route/nat66 × NDP, DNS UDP/TCP, multiple profiles, iptables/nft/firewalld, setup rollback/stop/restart and preservation of foreign resources. |
| D11 | 00/24/27/34 | IN_PROGRESS | Current native cores and provenance | Rebuild affected cores from a clean commit using pinned recipes, compare A/B outputs, update copies and genuine provenance; verify ABI/exports and packages. [Q25-F133](../reports/AUDIT-Q25-CLIENT-ONLY-BUILD.md) fixes two client-only compile errors in the Linux WAN monitor; client-only, server-only and router binary were checked, while overall D11 remains open. |
| D12 | 24/25/27/34 | IN_PROGRESS | Platform evidence | Android: 154 JVM + 6 API 34/x86_64 instrumentation tests PASS with fresh JNI; final snapshot remains required. Windows VM, Mac/Xcode/iOS and router runtime **SKIPPED by user decision on 24 September 2026**: those environments will not be provided. These platforms are not certified; this is a scope exclusion, not PASS. |
| D13 | 14/19/22/25 | IN_PROGRESS | Resource retention under load | Measure fd/tasks/threads/TUN/routes/firewall/journals/RSS before and after churn/reconnect/stop, including failures and multiple profiles; bounded duration and explicit growth criteria. |
| D14 | 00/34 | TODO | Current benchmark and certification | After correctness, run reproducible benchmarks for required modes with the current SHA, environment and metrics; build certification only from actual results. Historical 0.8.0 results do not certify 0.8.2. |
| D15 | All started sections | IN_PROGRESS | Evidence and documentation reconciliation | Map historical open items to later fixes; verify patch applicability, diff/commit and RU/EN links. Close each debt item with evidence, not a commit count. |

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
