# Q31: LuCI control, INI publication and firewall failures

<!-- normative-sync: q31-openwrt-controls-v1 -->

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
