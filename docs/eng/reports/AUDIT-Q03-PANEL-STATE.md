# Q03 — Panel state and load failures

Date: 3 October 2026. Status: **IN_PROGRESS**.

This pass fixes two defects on configuration and blocked-address pages.
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
