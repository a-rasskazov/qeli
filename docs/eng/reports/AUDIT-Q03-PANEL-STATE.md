# Q03 — Panel state and load failures

Date: 3 October 2026. Status: **IN_PROGRESS**.

The first pass fixed configuration/policy load defects; the next pass covers
refresh behavior on logs, transport and blocked-journal pages.
Section 03 still needs the other pages, late responses, background refresh errors,
modals and additional keyboard/mobile paths.

## Q03-F001 — Unloaded policy looked available for saving

A delayed/failed GET `/api/blocked/settings` left fields and Save active and posted
initial defaults. The backend rejected the initial write without `expected_revision`;
no actual configuration overwrite was reproduced. The UI did not distinguish
loaded settings from its initial placeholder.

Fixed: fields and Save require successfully loaded settings and revision;
overlapping loads/saves are blocked. Errors remain visible and Reload retries.
A disabled fieldset also prevents keyboard editing. Mobile policies stack vertically.

## Q03-F002 — Canonical defaults failure enabled a duplicate JS schema

A failed GET `/api/config/defaults` still let Add profile instantiate a large
embedded object which could drift from Rust defaults. A failed later load could
also retain the previously fetched template.

Fixed: duplicate JS schema removed; common `apiFetch` handles loading and the old
template is cleared. Failure shows a localized message and disables Add.
Successfully loaded configuration remains editable; Reload restores creation only
after the canonical template becomes available.

## Checks

28 actual JS component groups PASS. Three new regressions cover loading, missing
revision, retry, overlapping Save and absence of fallback. The pre-fix regression
reproduced an extra POST; its original log is retained.

Real Edge: eight scenarios, RU/EN × desktop/mobile × two pages. Checked disable
while loading/failed, retry, Enter policy save, Enter canonical profile creation and
retention of its extra field. No JS/resource errors; eight screenshots retained,
RU mobile and RU desktop images visually inspected. APIs use local loopback
fixtures: UI integration, not real server auth/HTTP persistence/network qualification.

Static gate: 11 templates / 1154 RU strings. Native inputs unchanged; A/B provenance
passes without claiming fresh native builds. Linux checks and binary SHA are in
[evidence](../../../release/certification/evidence/q03-panel-load-20261003.json).

The first Linux build is not accepted: zero archive mtimes let Cargo reuse old
include objects. The repeat invalidates source timestamps, verifies the new message
inside the binary and requires a different SHA. Original evidence retained as
`FAILED_STALE_EMBEDDED_ARTIFACT`. This fixes the test setup; running services are preserved.

## Release checks for the fixes

2257 Linux unit PASS (60 normally ignored). Fresh release SHA `865b7e8ed589fbaca51bd4479d4a1524ae743e1e04e7231cfe30e16295e6e2b8`: 18 namespace cases / 327 checks, aggregate leak, 100 TCP + 100 QUIC / 33 checks and bounded shutdown/recovery passed. Host snapshots and the running .11 service were preserved. Desktop/Android native A/B refreshed with unchanged library hashes; this does not claim fresh platform UI/network tests.

The first Android native attempt refused insufficient disk space. Only the private debug cache was removed after saving unit logs; service files and release cache remained. The retry passed. A fresh Linux unit run found two assertions requiring the old fallback; they were corrected and all units passed. Later formatting of one server-only cfg(test) assertion was verified with rustfmt 1.97.0: canonical output identical. Actual input hashes and original A/B/source identities are retained; format reconciliation is not a new runtime execution.

[Certification](../../../release/certification/0.8.2.json) binds the new release; prior D15 candidate/benchmark records retain their original SHA. Overall Q03 remains IN_PROGRESS.

Desktop publishing initially refused a source-identity change during A/B; the original FAILED is retained. Composite qualification rechecked actual A/B hashes/exports and the sole formatter-equivalent server-only diff; no additional compilation is claimed by that reconciliation. The original build driver fmt_reused_from label is too broad: 286 Rust files are unchanged and the two changed test files were checked separately, as recorded by fmt_qualification.

## Q03-F003 — Late responses overwrote newer state

Logs, transport and blocked journals allowed a timer/manual request to overlap
another read. Old responses overwrote newer data and cleared a newer spinner.
The pre-fix regression reproduced a third background read over two pending reads.

Fixed: request sequence owns both data and spinner. Background polls skip pending
work; manual reload after a changed log limit or an unblock keeps priority. Late
responses after destroy cannot update journal/transport state. Timers are cleared.
This does not cancel an HTTP request already sent or guarantee a network timeout.

## Q03-F004 — Failures looked like empty journals or disappeared under filters

A blocked-journal GET returning `{ok:false}` cleared both tables and displayed
“No blocked IPs”. A logs error became a line without a severity, hidden by an ERROR
or search filter. A failed read does not establish that records are absent.

Fixed: independent role=alert errors, last successful snapshot preserved and empty
state gated on a successful load without a current error. Log errors are not log
entries. The blocked countdown never removes rows; only a successful GET confirms
removal. Countdown freezes on failure; retained data is the last received snapshot,
and remaining time is an estimate.

## Journal and transport refresh checks

37 JS groups PASS, including nine new groups: reverse response order, old failure
while a newer read is pending, spinner ownership, bounded background polling,
snapshot preservation, filter-independent errors, countdown and timer/destroy cleanup.
12 Edge scenarios PASS: RU/EN × desktop/mobile × logs/blocked/transport, actual
repository templates/assets and loopback fixture APIs. Initial failure, keyboard
Enter retry, background failure and reverse responses covered; no JS/resource errors.
Two RU mobile screenshots inspected. The first browser run required waiting for DOM
visibility after reactive state in the fixture; product code did not change for that
adjustment. A narrow mobile log search field remains a responsive-review candidate;
this does not declare the whole page complete.

Rust, native recipes and library bytes are unchanged. Prior 2257 units and native
A/B are explicitly reused, without a new-execution claim. Fresh release build/checks
for this UI pass are recorded separately in
[evidence](../../../release/certification/evidence/q03-refresh-20261003.json).
Dashboard, users, client and remaining page/modal scenarios still belong to Q03.

Q03-F003/F004 fresh release SHA `0d61d60402fdce03ddeafff87499691abafe25fb740eaed62cb7b13f6ae1229b`: 18 isolated cases / 327 checks, aggregate leak, 100 TCP + 100 QUIC / 33 checks and bounded shutdown/recovery PASS. Five pre-fix reproductions (two load errors and late responses on all three pages) are preserved separately. Complete snapshots, .11 service PID/start time and its working binary were preserved. Certification 20/20 is refreshed for this artifact; physical rows and older benchmark records are not requalified.

## Q03-F005 — An old write changed a newer modal

Dashboard/client/users completion for write A closed an already opened modal B.
Users could display A's sharing URI/new password in B's modal. Closing the modal
does not cancel an HTTP write already sent; the bug was response ownership.

Fixed: writes retain their original modal object, cannot close a new one or clear
its busy/error state, and duplicate Submit is blocked. Covers bandwidth, client
profile/import, create/edit/group, quota/reset and sharing. Client edit GET also
owns a sequence invalidated by a newer open/close. Later edits in users/dashboard
remain after a successful save. Client fields and Form/INI are disabled during
write: POST does not return a new revision, so UI cannot introduce later edits
with the old revision. A programmatically changed draft is also preserved.
The UI saving flag is omitted from API fields; explicit initial false works in CSP Alpine.

## Q03-F006 — Silent failures and overlapping background reads

Dashboard/client/users ignored API `{ok:false}`, showing initial empty datasets
as absence of clients/profiles/users. Polls and visibility callbacks overlapped;
dashboard/users did not clean them up. The shell started green before first response.

Fixed: separate errors/retry, success-gated empty state, last successful snapshot,
latest-response ownership and busy background skips. Metrics have their own sequence.
Users keeps independent freshness/errors for users/groups/profiles/usage. Current
usage/live failure clears unreliable active addresses; an obsolete failure cannot
clear fresh addresses. Malformed collection replies cannot corrupt the snapshot.
Timers, visibility listeners and delayed post-Connect reload are cleaned up on destroy.
Shell status starts Loading; failure shows Unavailable and an error.

## Q03-F007 — Narrow-screen logs search lost nearly all content width

Before: input outer width 46 px at a 390 px viewport (RU/EN), and 46–58.5 px at
768 px; padding left almost no room for text. Search/select now have a base width
and actions wrap. Eight RU/EN × 320/390/768/1440 checks: input 161–320 px and
select within viewport. CSS source and generated app.css were rebuilt by the locked
Tailwind pipeline. Dependencies installed offline with install scripts disabled;
lockfile unchanged.

## Consolidated checks

71 JS groups PASS (34 new beyond prior 37). Eight pre-fix reproductions are retained;
mobile CSS was measured before the fix too. 24 Edge scenarios PASS: 16 scenarios
on four pages RU/EN × desktop/mobile and eight logs widths. Actual repository
UI/assets and loopback API fixtures; not fresh backend auth/persistence evidence.
Error/retry, reverse reads, Enter Submit, modal ownership and single POST covered.
Initial fixture failures corrected selectors, visibility/focus waits and background
refresh versus manual load; FAILED records retained. Browser also caught a newly
undefined saving flag; initial false fixed before release.

Your uncommitted live-users refresh is separately archived. A merge with readSection,
cleanup and no-store retains its editor protection for live user rows. All 71 groups
also pass against merged WIP, plus four checks of editor/pending refresh/manual
priority/destroy. This extension remains uncommitted; certification covers committed tree.

Rust/manifests/native recipes are unchanged: prior 2257 units and native A/B are
explicitly reused, not executed again. Fresh Linux build/checks are recorded in
[evidence](../../../release/certification/evidence/q03-remaining-20261003.json).
Q03 remains IN_PROGRESS: notifications/quickstart/login and additional config
keyboard/secret/revision scenarios still need completion.

Q03-F005/F006/F007 fresh release SHA `dadbee830fb8e48279dbd83173dbc8db34b7e5bd4cc77df447a9c53885dc9b21`: 18 isolated cases / 327 checks, aggregate leak, 100 TCP + 100 QUIC / 33 checks and bounded shutdown/recovery PASS. Eight pre-fix UI reproductions are preserved separately. Four additional Edge scenarios passed against merged WIP; live-users changes remain uncommitted. Complete snapshots, .11 service PID/start time and its working binary were preserved. Certification 20/20 is refreshed for this artifact; physical rows and older benchmark records are not requalified.
