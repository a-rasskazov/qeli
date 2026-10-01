# Q25-F201 — archived patch applicability and evidence age

1 October 2026. Source snapshot: `003405fd` (`dev`). Product code was unchanged; the user's modifications to `CHANGELOG.md` and `qeli/src/web/templates/users.html` were left alone.

## Patch archive

A read-only scan of all 625 `*.patch` files under `C:/Users/litvi/OneDrive/Documents/qeli/` checked the working tree using `git apply --numstat`, `git apply --check` and `git apply --reverse --check`. It found 295 invalid or fragmentary files, 265 valid patches applying in neither direction, 39 exactly reverse-applicable patches (content already present), 22 forward-applicable patches and 4 ambiguous cases. Nothing was applied. This classifies syntax and context, not whether a fix is needed: code changed after a patch was drafted commonly rejects both directions.

Among 50 dated `audit-debt-20260924/25` patches, 47 have drifted with the code, 1 is exactly reverse-applicable and 2 have malformed patch syntax. For 21 of the 48 syntactically valid patches, an identical `git patch-id --stable` exists in a later commit. That is strong evidence that the exact diff was integrated, not a fresh runtime validation on `003405fd`. The two fragmentary drafts, `server-forced-drop-phase/proposed.patch` and `tun-attach-context-phase/attach-index.patch`, should not be applied: current `WorkerLease`/`mark_complete` and `verify_sysfs_index` implement the corresponding behavior, with evidence in [Q25-F130](AUDIT-Q25-SERVER-FORCED-DROP-LEASE.md) and [Q25-F123](AUDIT-Q25-TUN-ATTACH-CONTEXT.md).

All 22 forward-applicable patches belong to the older archive. Additive context accounts for much of this: lines already present can be inserted again. For example, `roaming-netns-rollout-gate.patch` proposes literal `roaming.enabled = true` and `roaming = required`, while today's `scripts/roaming_netns_e2e.sh` intentionally parameterizes and validates both settings. `roaming-packaged-configs.patch` proposes `roaming.enabled = false`, whereas shipped server profiles now explicitly set `true`, a contract checked by `qeli/tests/config_examples.rs`. Applying those patches would change the verified current behavior. Two older patches touch the user's modified `CHANGELOG.md`, which this review did not edit. The remaining older Android, Windows, telemetry and UDP candidates need contract-specific review under D08/D12/D13 rather than bulk `git apply`.

## Runtime evidence age

The D09 register row now identifies `4eaf551a` instead of saying “current SHA”: its report ran 2175 Linux tests and 8/8 lifecycle cases on that source on 25 September. Later targeted reports validate changed boundaries but do not turn that historical suite into a run on `003405fd`. D09 remains DONE within its evidenced historical scope; the final candidate's aggregate regression still belongs to D14/D15. This review neither closes D15 nor replaces Android, Windows, macOS/iOS or lab runtime validation.
