# Q31: LuCI control, INI publication and firewall failures

<!-- normative-sync: q31-openwrt-controls-v6 -->

6 October 2026. F307–F309 product fixes and F310 test reconciliation. Q31 moves
from TODO to IN_PROGRESS; no full checklist criterion or router runtime is closed.
Overall28/37(75.7%),9 remain. Q29 SIGKILL FAIL/auto-null ENONET, Q30 Apple runtime
exclusions and callback-drain OPEN, and D06 ACCEPTED_LIMITATION remain unchanged.

## F307: service commands ran before committed UCI intent

Connect/Disconnect staged `enabled` with `uci.save()`, issued service commands,
then invoked the modal apply helper. Session-local staged settings are not the
committed configuration read by the root init script. A disabled profile could
therefore ignore Connect; simultaneous controls could interleave an old start
with a new stop. The modal helper is not an awaitable commit barrier.

All three controls now share a promise queue. Connect/Disconnect save and await
`uci.apply()` commit/confirmation before enable/start or stop/disable. An apply/save
failure issues no later service commands; a failed operation does not poison the
queue. Restart waits its turn. This serializes controls in one loaded view only,
not independent tabs/RPC clients or unrelated form saves. Service failure after
commit does not roll back the saved autostart intent; the error is propagated.
Like the previous apply action, UCI apply can include other staged packages.
Unsaved form fields still require Save & Apply before the status controls.

The distinction and awaitable API were checked against primary LuCI sources:
[UCI save/apply](https://openwrt.github.io/luci/jsapi/uci.js.html) and
[modal changes.apply](https://openwrt.github.io/luci/jsapi/ui.js.html).
Seven Node fixtures execute the actual module with controlled UCI/RPC promises:
commit ordering, stop intent, save/apply failure, queue recovery, overlapping three
controls, failed enable and invalid action. They do not execute real rpcd/procd.

## F308: firewall synchronization reported success after failed mutation

The live init path discarded delete/add-list/set/commit/reload errors. Even after
adding error propagation, a retry can see already-staged UCI values and incorrectly
skip commit/reload. The root-only tmpfs `firewall-pending` marker is created before
mutation, retained on failure and cleared only after successful commit/reload.
A retry reconciles the current desired device and repeats pending commit/reload.
A clean no-op still performs neither commit nor reload. Init returns before procd
instance admission on a synchronization error. Persistent state-directory creation
failure is propagated as well. No existing firewall service was invoked by tests.

This is not a firewall transaction or rollback: partially staged changes can remain
for the retry, and other administrators/independent init invocations are not locked.
The one-shot install defaults and actual fw4 lifecycle require the next Q31 pass.

## F309: incomplete INI could replace the previous configuration

Rendering truncated the live file and ignored earlier I/O failures. Invalid UCI MTU
could disappear instead of failing (including malformed text), while out-of-range
values reached the core. Rendering now uses a0600 sibling tmpfs file, checks writes
and publishes by atomic rename; ordinary failure removes the temporary file and
preserves the previous INI. MTU must be decimal0(auto) or576..16602, matching the
core/LuCI range. Process kill during rendering may leave a0600 temporary file until
reboot; cleanup after SIGKILL and concurrent lifecycle ownership are not qualified.

Attacker-influenced values use printf with fixed formats. Literal backslash escapes
remain literal; raw C0/DEL controls are stripped from nonsecret INI values. CLI
secrets reject DEL too, matching rpcd validation. BusyBox baseline preserved literal
backslashes already; this is not a claim of a reproduced OpenWrt escape injection.
The printf change also closes echo interpretation on shells such as dash.
Passwords remain separate0600 tmpfs files; no JSON configuration format is added.

Ten Python fixtures source the actual init functions with mock UCI and a mock
firewall executable, each under a fresh temporary directory. Current BusyBox ash
and dash both PASS: render/DNS/router guard, safe value output, malformed/boundary
MTU, earlier write/publish failure, exact4096-byte secret and invalid secrets,
legacy migration no-op, firewall no-op, five mutation/reload failure-and-retry paths,
and reserved device namespace. Baseline BusyBox failures were retained separately.
Actual OpenWrt UCI parsing, RPC secret stdin and real firewall/network behavior are
not replaced by these fixtures. No /etc, running service, TUN or management route
was changed; tests ran only in an isolated `/var/tmp` directory on lab .11.

## F310: a stale Android source assertion broke the recipe gate

The37-test native recipe suite still expected the former nullable username chain.
At the packet base, Android already captures `activeConfig` once, checks stopping/
null/current core under the service monitor, then logs `logValue(config.username)`.
Both source and test matched the base before correction, proving this failure
predates the Q31 patch. The assertion now checks the current capture/sanitizer;
Android product code is unchanged. All37 recipe tests PASS. This source assertion
is not an Android runtime logging test or a new Android bug fix.

## Scope and remaining work

Reviewed initial source paths: init renderer/live firewall sync, LuCI controls,
package ACL/rpcd secret transport, package defaults and router build entrypoints.
The ACL remains scoped to qeli UCI and package-owned controls; service list is read
only. RPC secrets use stdin, not argv. No additional deletion was justified in
this packet. Broader source/dead-code review is still open.

Next: install/upgrade failure and rollback, cached UI status and unsaved form
ownership, cross-process secret/lifecycle races, build-helper failure/provenance
and available cross-build checks. Current artifacts were not rebuilt; Rust/native/
Android/Apple/Windows client implementation inputs are unchanged. Actual router
WAN renewal/reboot, memory/throughput and network runtime are USER_EXCLUDED;
cross-build results will not be presented as device qualification.

Documentation/bindings/diff checks accompany the fixture results. Prior automated
Linux case statuses/artifacts/execution dates/acceptance_basis stay intact; the
source digest is rebound with this scoped qualification supplement only.

Raw packet: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-openwrt-controls-20261006.
Evidence: release/certification/evidence/q31-openwrt-controls-20261006.json.

## F311: preparation errors and manifest recovery were outside cleanup

Router toolchain commands hid rustup failures behind tail/true; Zig exit status was
also ignored. Both helpers now check each command and the installed cargo-zigbuild
0.23.0 inventory. Only selected MIPS builds prepare nightly/rust-src; other selected
targets do not install an unused nightly. Cargo builds use --locked. Unknown arch,
extra argument and unknown flag are rejected before SSH rather than building all
targets after a typo. These fixes do not pin the rolling nightly/stable toolchain
or qualify reproducibility, ABI or current MIPS target support.

The entire connected lifetime now has a finally-close barrier. An interrupted
manifest backup is recovered before --sync, preventing a later restore from
replacing the newly uploaded Cargo.toml with the previous version. A successfully
restricted manifest is restored after build/transfer, and connection close still
runs when restoration fails. SFTP sync closes on put/inventory failure, propagates
cleanup/mkdir errors and requires Cargo.toml/Cargo.lock. This does not make source
sync atomic or exact: deleted remote modules and .cargo/config.toml reconciliation,
concurrent use of the shared checkout and full source provenance remain OPEN.

## F312: a failed download could still print KEENETIC_BUILD PASS

The Keenetic pull helper swallowed IOError and left build result zero. The original
main path was reproduced with a failed SFTP download: exit0 and PASS. Preparation
failure also left its SSH connection open; toolchain errors returned normally.
The corrected main returns1 on transfer failure, closes the connection and checks
setup failure. Both helpers reuse native_lab's verified atomic transfer: SHA256
is read over strict SSH, downloaded bytes must match before destination replacement,
and the empty digest is rejected before transfer/publication. Read failure, corrupt
payload and empty artifact preserve the previous local file. An architecture failure
is reported while the other selected architectures still run. This is transport
identity, not ELF/ABI/device/reproducibility attestation. No real binary was built
or published in this packet.

Fourteen executable Python tests load both real helpers with fake SSH/SFTP/toolchain
responses, exercising invalid CLI, toolchain/pin failures, non-MIPS admission,
manifest/sync order, cleanup failures, per-arch result propagation, verified artifact
publication and lockfile build commands. Current tests PASS; baseline reproduction
records are separate. Mock responses are not a successful real toolchain install.

## F313: repeated LuCI load read the same cached enabled flag

LuCI uci.load caches the package. Polling it again never refreshed external edits;
unloading it would discard staged form changes. A scoped read-only service_status
RPC now calls the package's status_enabled init command. That command reads the same
root UCI context used by service start, rather than the browser/session form cache.
Root CLI deltas may still be visible before commit; this is init-visible intent, not
a claim of a disk-only committed read. No form cache is loaded/unloaded by polling.
Exit0/1 mean enabled/disabled; load error, missing service or invalid RPC response
become unknown, displayed explicitly. The read ACL permits service_status only;
service actions and secret writes remain in the write ACL. Service process liveness
continues to come from procd and is not an authenticated connectivity measurement.

The9 LuCI caller fixtures plus one status/ACL adapter fixture PASS. The latter parses
the compatible adapter in JavaScript with mocked system/fs, not an ucode interpreter;
real ucode/rpcd and rc.common dispatch are NOT_RUN. The added init status case and
prior shell cases make11 tests per BusyBox ash/dash, both PASS in the isolated .11
directory. Official sources: [LuCI cache semantics](https://openwrt.github.io/luci/jsapi/uci.js.html),
[ucode system exit codes](https://ucode-lang.org/module-core.html).

Current packet, F311–F313: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-router-build-failures-20261006.
Evidence: release/certification/evidence/q31-router-build-failures-20261006.json.
The previous packet/seal is unchanged. Install defaults/upgrade rollback, broader
source review, secret/lifecycle races and real available cross-build qualification
remain OPEN. The next installation pass must exercise interrupted creation and
reload errors; the one-shot defaults have not been qualified by the live-sync tests.
Q31 remains IN_PROGRESS, overall28/37(75.7%),9 remain.


## F314: interrupted firewall defaults could report success

The first-install defaults ignored individual UCI and reload errors, then exited0.
If only the qeli zone name had been created, a later run saw that name and skipped
repair. Baseline fixtures reproduce exit0 after commit/reload/input failures;
commit failure leaves no persisted zone, reload is not retried, and an input failure
leaves an incomplete zone. These are shell/UCI-model reproductions, not libuci/fw4.

Defaults now check load, each mutation, commit and live-service reload. They create
named package-owned zone/forwarding sections and a0600 pending marker in a0700 tmpfs
runtime directory before mutation. Retry completes only those owned sections and
replaces the device list without duplicates. Existing administrator zones remain
unchanged; reserved-name collision, foreign pending ownership, multiple qeli zones
and invalid devices fail before mutation. Image preparation without a firewall
service remains supported. While firewall-install-pending exists, init refuses live
sync/start and tells the administrator to rerun /etc/uci-defaults/99-qeli-firewall.

This is recoverable installation, not automatic rollback or an interprocess
transaction. Root CLI staged deltas, concurrent changes, process death and reboot
are not qualified by the model. The temporary marker does not persist across boot;
normal failed mutations remain visible and must be corrected/retried. Nine new
installation cases plus12 init cases PASS in both BusyBox ash and dash on lab .11.
All test paths/services are redirected into temporary fixture directories; no live
/etc configuration, firewall or service is changed.

## F315: --sync retained deleted sources and omitted Cargo config

Both router helpers only removed src/bin and uploaded the remaining files additively.
A deleted module survived and the old .cargo/config.toml continued to influence the
build. Both baseline helper fixtures reproduce these stale inputs. A shared
router_source wrapper now delegates to the existing native_lab sync owner: replace
src and .cargo, upload current config/assets/sources/Cargo.toml/Cargo.lock, preserve
target cache. Mandatory local inputs are checked before remote mutation.

A0600 .router-sync-incomplete marker is written before replacement and removed only
after all uploads and SFTP close succeed. Both helpers check it before toolchain/
build admission, including a later invocation without --sync. Transfer/open/close/
remote-command failures retain it; successful --sync repairs the managed inputs.
Seven real-shell/filesystem adapter tests PASS in isolated Linux temporary roots,
14 router helper fault tests and12 unchanged shared native-lab tests PASS. Repeated
sync removes stale inputs and preserves target cache; missing local files cause no
remote commands. Baseline proof uses a bounded adapter for its historical hardcoded
cleanup, never the live /opt checkout.

This replacement is not atomic and has no cross-process lock. Without --sync, an
existing unmarked checkout is still intentionally reused. No claim is made for
concurrent users, mutable local snapshots, complete provenance, reproducibility,
ELF/ABI or a fresh real cross-build. Cargo config scope is the current single
.cargo/config.toml. A failed initial baseline attempt due to absent Paramiko in the
Linux fixture is retained; source-only imports were corrected with a connection-
forbidden lab stub before the successful reproduction, without installing packages.

Current packet F314–F315: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-install-source-sync-20261006.
Evidence: release/certification/evidence/q31-install-source-sync-20261006.json.
37 native recipe checks,10 Node caller/adapter cases and docs/bindings/diff checks
also PASS. Real libuci/fw4/procd/ucode/rpcd/package install and cross-build NOT_RUN;
router runtime USER_EXCLUDED. Earlier seals and runtime statuses/artifacts/dates/
acceptance_basis are retained. Full upgrade/rollback, cross-process lifecycle/secret
races, broader source review and actual build qualification remain OPEN.
Q31 IN_PROGRESS, overall28/37(75.7%),9 remain.

## F316–F318: deletion, migration and UCI admission failure

clear_secrets previously logged success after a failed rm. RPC clear_secret ignored
fs.unlink's null error return and always returned result=true. CLI deletion now
propagates failure, including all-secret partial failures; removing an absent file
remains idempotent. RPC validates the two literal names, delegates to the init
owner and returns result=false for nonzero or invalid command results. A compatible
Node fixture reproduces the original false success with the documented null return;
this is not actual ucode execution. [Primary fs.unlink contract](https://ucode-lang.org/module-fs.html#unlink).
Clearing a saved file does not stop a running VPN or erase copies already loaded
by the client/rendered obfs configuration; restart applies credential changes.

Legacy migration deleted staged UCI options before commit. After commit failure,
a retry saw no options and returned0 without retrying: old credentials remained on
persistent storage. A0600 secret-migration-pending marker is now created before
staged deletes and retained through failure. Retry commits even when no staged
legacy option remains; removal failure retains retry intent. Migration reads each
legacy value once, preserves an existing nonempty runtime credential, copies before
delete, and scrubs empty legacy values. Copy/marker/delete/commit/remove failures
are covered. The marker is tmpfs; no crash/reboot transaction or secure flash erase
is claimed. Rotate old credentials after migration as previously documented.

Both initial/reloaded qeli config_load calls, firewall load and restoration of the
qeli context now fail admission explicitly. Multiple qeli firewall zones are rejected
before mutation instead of silently selecting the last one. No-zone valid behavior
is retained. Baseline model probes reproduce false success on clear/load/ambiguous
zone and retained persistent secrets after migration retry in both interpreters.

## F319: rc.common hid callback errors from the service command

Review of the saved [upstream rc.common](https://raw.githubusercontent.com/openwrt/openwrt/master/package/base-files/files/etc/rc.common)
showed rc_procd invokes the callback, closes the service message, then start/stop
run optional hooks; the callback result is otherwise lost. A saved dispatcher
snapshot with fixture-only lib/functions/procd adapters reproduces direct callback
failure with CLI exit0. This uses an intermediate F316–F318 source before hooks,
recorded separately from the Git baseline, to isolate the dispatcher defect.

The init owner now retains preparation/cleanup status and returns it through the
standard service_started/service_stopped hooks. Failed stop cleanup still permits
procd_kill to be requested, but forbids subsequent start preparation in the same
restart/reload invocation. Valid disabled start succeeds. This covers callback
results, not ubus publication/delete failure, daemon acceptance, native process join
or authenticated connectivity. The real procd library's flock/admission behavior
is source-reviewed only; no custom locking mechanism was introduced.

Five saved-dispatcher cases plus23 init and9 installation cases make37 PASS per
BusyBox ash/dash on .11. The snapshot is byte/hash-pinned; tests require the explicit
QELI_OPENWRT_RC_COMMON_FIXTURE path and otherwise skip. All paths/adapters are in
temporary roots; actual /etc, firewall, rc.d and daemons are unchanged. Two result-
hook cases and the9 preceding init cases are new. Eleven Node fixtures PASS; one
new compatible RPC clear case. Native recipes37 and docs/bindings/diff PASS.

Current packet F316–F319: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-secrets-upgrade-20261006.
Evidence: release/certification/evidence/q31-secrets-upgrade-20261006.json.
Real libuci/fw4/procd/ucode/rpcd/opkg and cross-build NOT_RUN; router USER_EXCLUDED.
Full package upgrade/rollback, interprocess/daemon failure and lifecycle checks,
broader source review and build provenance remain OPEN. Previous seals/runtime
statuses/artifacts/dates/acceptance_basis and retained Q29/Q30/D06 observations stay
intact. Q31 IN_PROGRESS, overall28/37(75.7%),9 remain.

## F320: Keenetic installer consumed obsolete artifact names and hid dependencies

The build helper publishes qeli-client-keenetic-aarch64/mipsel, but the installer
looked only for qeli-client-aarch64/mipsel. A canonical-only bundle failed before
installation. It also ignored mandatory ip-full/iptables install failures with
||true and could publish a client and report completion with missing preparation.
Both behaviors are reproduced with the original Git source and isolated command
models. Documentation now lists canonical artifacts and --sync; old manually
prepared filenames remain a fallback, with canonical taking precedence.

The installer checks nonempty binary/init/new-config inputs before dependency
changes, propagates required update/install failures, checks ip/iptables command
availability and warns explicitly when optional ip6tables installation fails.
It prepares binary/init/config copies before publication, cleans ordinary temporary
files on exit and publishes each file by sibling rename. Existing INI content is
preserved; its mode becomes0600 and the credential directory0700. Copy/preparation
failure retains old installed binary/init. Publication failure can leave a partial
bundle, because multiple renames are not a transaction; correct the error and retry.
There is no forced service restart, concurrent-installer lock, fsync/power-loss or
actual architecture/ELF/package-manager qualification.

Eleven installer cases cover canonical and legacy names, both architecture choices,
existing config, required/optional dependency failures, missing command, incomplete
bundle/unsupported arch, copy failure and publication retry. Model artifacts are
small fixture files, not executed VPN binaries. Initial baseline reproduction used
ambient PATH and failed in the harness; that attempt is preserved. Final fixtures
restrict PATH for both sources; lab inventory confirms actual opkg is absent.

## F321: OpkgTun ignored ndm failures and mixed NetworkPlan reads

Each ndmc mutation previously continued after failure, then saved configuration and
logged interface up. Original-source model injection reproduces exit0/up/save after
failed ip global. The hook now checks every L3/configuration-save mutation, returns
failure, logs retry required and never logs up after failed apply. A0600 pending
checkpoint is created before mutations and removed only after successful save. A
failed apply bypasses the address-only no-op on retry, including when ndm already
shows matching connected addresses. Checkpoint create/remove errors reject apply
completion; no cross-process lock or durable/fsync transaction is implied. Earlier successful
ndm mutations are not rolled back; after fixing the error, rerun the hook or use the
manual registration sequence and check each command result. Deferred interface/
missing-plan behavior remains0 with a waiting diagnostic, rather than success-up.

The interface marker now requires opkgtun plus a nonempty all-decimal suffix and a
maximum15-character name. The prior glob accepted opkgtun0garbage; the model proves
it reached ndm. Rejected markers issue no ndm commands. This is a local marker grammar
fix, not a demonstrated server-to-ndm exploit. A plan is captured once per read and
IPv4/IPv6/MTU are extracted from that same snapshot. Forced replacement after the
first read reproduced old IPv4 from A with IPv6/MTU from B; corrected commands all
use A. This does not serialize a concurrent stop, mark a plan generation or validate
the whole NetworkPlan as a second client parser.

Nine hook cases cover dual-stack apply, all nine mutation failures and connected retry,
checkpoint creation/removal failures,
invalid marker, missing plan/interface, existing address no-op and forced plan
replacement. Existing optimistic address/status idempotence, MTU-only updates,
process ownership/join, legacy NAT/sysctl recovery and wan.d concurrency remain OPEN.
Current tests do not qualify real ndmc error/status output, event recursion, ndm
rollback or firmware compatibility. No router network/proc/sys/service was changed.

Current packet F320–F321: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-keenetic-install-hook-20261006.
Evidence: release/certification/evidence/q31-keenetic-install-hook-20261006.json.
20 cases per BusyBox ash/dash PASS in .11 temporary roots with substituted /opt,
PATH and opkg/ndmc commands. Native recipes37 and docs/bindings/diff PASS; native
implementation, OpenWrt adapters and build helpers are unchanged. Real opkg/ndm and
cross-build NOT_RUN; routers USER_EXCLUDED. Previous sealed evidence and runtime
statuses/artifacts/dates/acceptance_basis are retained; Q29/Q30/D06 observations
unchanged. Q31 IN_PROGRESS, overall28/37(75.7%),9 remain.

## F322: forwarding snapshots and failed restoration lost recovery state

Both Keenetic init templates wrote an unchecked snapshot directly to the final
file. A failed sysctl read could become an empty saved value; the original snapshot
function still returned success. Upstream route-query errors were also hidden by a
pipeline. Restoration ignored write errors and removed the checkpoint even when
recovery was incomplete. Isolated original/current comparisons reproduce these
cases; the failed read comparison calls the snapshot function, because the old
nat_up subsequently failed at its write after already creating the bad snapshot.

Both templates now check reads, allowed sysctl values and WAN query status, then
publish a0600 sibling checkpoint by rename. Only negotiated families are read/probed: an IPv4-only plan does not require IPv6
sysctl/WAN querying, and an IPv6-only plan does not require IPv4 sysctl/iptables. The version2 checkpoint records original values, TUN/LAN names and
families and RA journalled before mutation. Apply rejects a checkpoint for different rule
interfaces. Restoration validates saved fields, touches only journalled families
and checks reads/writes. A failed restore retains the checkpoint for retry; only
successful restoration removes it. Values changed away from the wrapper's1/2 are
preserved, but same-value administrator changes cannot be distinguished. This is
not a cross-process lock, fsync/power-loss transaction or ownership of kernel sysctls.

## F323: legacy rule cleanup could delete administrator rules and hide failures

Old rules had no owner tag: nat_up reused an administrator's matching rule, and
nat_down deleted it. Cleanup ignored firewall errors and could then discard the
saved state. Switching GATEWAY/OPKGTUN skipped recovery entirely. Original-source
models reproduce lost matching admin rules, false completion after failed delete/
check, retained stale state after mode change and restart reaching start after
incomplete legacy-state recovery.

New rules use comment qeli-keenetic-legacy. Checked add/delete helpers distinguish
model check status1 (absent) from higher errors; add/delete errors propagate. Only
tagged rules for journalled families and saved interfaces are cleaned. Recovery
runs from the checkpoint even after GATEWAY/OPKGTUN/TUN/LAN changes; without a
checkpoint no rules are deleted. Partial cleanup keeps retry state. Start rejects
failed stale recovery before clearing the plan or launching, and stop/restart
propagate cleanup failure. New legacy mode needs the iptables comment capability;
actual Entware/kernel behavior, including error-code differences, is NOT_RUN.

Versionless/unknown old checkpoints reject automatic cleanup and remain intact for
manual review. Before replacing an active legacy template, stop it with its old
script and inspect its rules/sysctls; if a checkpoint remains, keep its saved values
and identify old rule ownership before manual recovery. Do not discard that state
as an automatic migration. New code intentionally does not guess ownership of old
untagged firewall rules. No such migration was performed on a real router.

Twenty-two isolated state cases per template (44 new) cover capture/publication,
WAN failure, family/interface admission, journal failures, exact matching admin
rules, duplicate apply, check/add/delete/missing-command failures and retry,
restoration read/write failure, corrupt/old checkpoints, mode changes and start/
stop/actual dispatcher restart gating. Together with the20 prior installer/hook
cases,64 tests per BusyBox ash/dash PASS. Shared forwarding/firewall helper blocks are kept
identical by the scoped source review. Files replace proc/sys, all firewall/ip
commands are models and every potential signal is intercepted. No actual client
process, kernel forwarding, firewall or router service was operated. One initial
fixture TUN expectation FAIL and one reproduction-scope assertion FAIL are retained
and explained; final comparisons use corrected identical isolation for both sources.
Native recipes37/docs/bindings/diff PASS.

Packet F322–F323: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-keenetic-forwarding-state-20261006.
Evidence: release/certification/evidence/q31-keenetic-forwarding-state-20261006.json.
Actual router/iptables/comment module/sysctl runtime and cross-build NOT_RUN;
router USER_EXCLUDED. PID identity, TERM/join ordering, instant launch failure,
INI/core semantic parity, OpkgTun idempotence/concurrency and broader build/source
review remain OPEN. Earlier runtime statuses/artifacts/dates/acceptance_basis and
Q29/Q30/D06 observations are retained. Q31 IN_PROGRESS, overall28/37(75.7%),9 remain.
