# Q25-F204 — Linux worker resource churn

<!-- normative-sync: audit-q25-worker-resource-churn-v1 -->

Date: 1 October 2026. Current Rust source previously synchronized to
lab .11; `cargo build --offline --locked --bin qeli` with
`CARGO_INCREMENTAL=0`, `CARGO_BUILD_JOBS=1` passed.
Tested debug binary SHA-256:
`ae59962eebe483ad4d312bda34cb5634bf66bcd2ca372869b17b15e8c95e66d9`.
Complete `qeli/src`: 308 files with the same digest
`64be415e454438fe2b90129168069e0be9a9caf4a7a467bca24398fd4a6250aa`
in the checkout and on .11.

The existing `scripts/audit_worker_lifecycle.py` gained bounded
`--resource-reloads 10`. Every case runs in fresh network, mount,
and PID namespaces with a private bind mount for `/etc/qeli`.
After worker readiness, a second owner is rejected and malformed
SIGHUP is rejected; ten valid SIGHUPs follow, with a control request
between them. Snapshots of `/proc/<pid>/fd`, socket fds, `task`,
and `VmRSS` are saved before and after every reload. Predetermined
criteria: final fd/socket fd/task growth no more than two, sampled
peak RSS no more than +32 MiB. After SIGTERM, TUN, routes, firewall,
sysctl, control socket, and journal are checked.

| Modes | Result | Δ fd/socket/tasks | Largest Δ RSS |
|---|---:|---:|---:|
| TCP: off/manual/route/nat66 | 4/4 PASS | 0/0/0 in each | 15,520 KiB |
| UDP: off/manual/route/nat66 | 4/4 PASS | 0/0/0 in each | 15,472 KiB |

Overall **8/8 cases and 80 valid reloads PASS**. All eight second-worker
rejections and eight malformed reloads preserved the live worker.
After every stop, the control socket, TUN, Qeli rules, and
`sysctls.state` are gone; full before/after network snapshots match
under the documented checks. The RSS limit is a sampled peak, not
a continuous maximum between samples. `py_compile` and
`git diff --check` passed.

Raw evidence: `C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/d13-resource-20261001/`
(`results.json`, eight `resource-samples.json` files,
network-before/after, active firewall dumps, and worker logs).
Identity keys were not copied from the isolated lab.

D13 remains **IN_PROGRESS**: current-source same-session reconnect
soak and multi-profile stop/fault cases remain. Earlier 100 release
handovers at `ea87fd49` are separate evidence and are not counted
as verification of this binary.

[Debt register](../plans/AUDIT-DEBT.md) ·
[Earlier release soak](AUDIT-Q34-RELEASE-SOAK.md)
