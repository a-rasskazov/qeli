# Q07: backup, restore and history — batches 1–2

<!-- normative-sync: audit-q07-backup-restore-v2 -->

Date: 3 October 2026. **Batch: PASS; overall Q07: IN_PROGRESS.**
Configurations remain INI; JSON serves API responses and audit evidence.

## Confirmed defects

| ID | Defect | Fix |
| --- | --- | --- |
| Q07-F001, P2 | Portable archives exclude locks, but exact shape validation demanded nested `server.ini.lock`; a valid native backup could not restore. | Nested validation preserves `.lock`, matching publisher/pruner. Active sidecar inode remains unchanged. |
| Q07-F002, P1 | Restore accepted missing overlay identity and malformed keys; startup could generate a new pin or fail a profile. | Active profiles require regular 32-byte identity files. Managed paths come from staging even in overlay; external dependencies must already exist. Validation never generates identities. |
| Q07-F003, P1 | HTTPS restore accepted missing or invalid PEM material. | Remap managed paths into staging and invoke existing TLS checker for a complete matching pair without generation; check external paths against existing files. |
| Q07-F004, P2 | GNU tar retained uploaded UID/GID; a root server then rejected custom-path INI as untrusted. | Extraction uses `--no-same-owner`, assigning the server user. Existing 0600/0700 mode normalization remains. |

Six checks failed on the previous release: exact nested locks, missing overlay
identity, malformed identity, missing/invalid TLS pairs and foreign UID.
Old exact-mode missing identity was refused by the nested-lock check; it is not
independent identity-validation evidence. All six failing cases now pass with
normal roundtrips.

## Runtime validation

Final release: `d502a58df16f6d86062edaf17d3ee55bc3bb786ae4909bfe9e6d63e56612e7b3`.
38 real HTTP/system checks PASS in private NET/mount/PID namespaces:

- Download with `/etc/qeli/nested/server.ini`, custom users INI and exact identity.
- Overlay retains extras; exact deletes a top-level extra while retaining nested locks.
- Rollback snapshots exclude previous snapshots/uploads/staging; no temporary leftovers.
- Pre-publication refusal for traversal, absolute paths, symlink/hardlink/FIFO,
  executables, malformed/missing INI/users/identity/TLS; SHA comparison of the
  previous data tree excludes operational snapshots and sidecars.
- Expanded size >64 MiB and >5000 entries; successful restore after refusals.
- A second restore immediately returns 409 while the first waits on an external
  config FileLock; status responds, first restore succeeds after unlocking.
- Foreign UID/GID becomes server UID/GID. A custom matching TLS pair restores;
  a fresh HTTPS process starts and authenticates the administrator.
- A fresh ordinary worker starts with the unchanged identity after roundtrip.

Another 75 HTTP history/config transaction checks PASS on the same release:
exact bytes/revisions/snapshots, eight writers, ENOSPC, read-only, target rename
failure, FileLock budget and recovery. Linux: 2265 units PASS / 60 ignored,
full/minimal Clippy and rustfmt PASS. Native/release qualification is retained
in the evidence below. No performance benchmark or physical qualification claimed.

## Remaining Q07

Q07 remains open. After the second batch, fresh restoration with mixed
inline/external users and the panel-secret lifecycle remain to be tested.
Archive-restore preparation faults (actual ENOSPC/read-only and HTTP cancellation)
still need direct coverage; passing Q05 history tests do not substitute for them.
Multi-file publication is not an atomic transaction and has no automatic rollback.
Power loss and uncoordinated root writes are not certified.
[Budget report](AUDIT-Q05-ARCHIVE-BUDGET.md).

Shared services and deployed binaries were not replaced. Full .11 snapshots match.
Desktop .10 SDK A/B passes; default/explicit legacy IPv4 dumps differ, while nft,
other host fields, PID/start and binary match. Historical unattributed .10 dump
variability remains an evidence limitation; full .10 network-preservation PASS
is not claimed. Rules were not removed/restored. Completed historical debug
artifacts were losslessly gzipped with SHA verification; completed lint cache
removed with sources/test logs retained.

[First batch evidence](../../../release/certification/evidence/q07-backup-restore-20261003.json).

Release qualification: fresh 18/327 matrix, aggregate leak and 100 TCP + 100 QUIC / 33 soak checks PASS. All four native cores passed A/B and match Q06 byte-for-byte; canonical/client copies, ABI and provenance agree.

## Second batch: publication, recovery and local state

Final release: `771d3a40b11867ce09b7fda0b212bec02a74b8d746e2f7c0b782974c216a13ef`.

| ID | Problem | Fix |
| --- | --- | --- |
| Q07-F005, P2 | Unknown or empty `exact` silently selected overlay. | Strict parsing returns HTTP 400 before restore starts. |
| Q07-F006, P1 | New client `.ini` bypassed the file-only password_command check applied only to `.conf`. | Both extensions use the common trust checker; notify.ini retains its dedicated parser. |
| Q07-F007, P1 | Uploaded archives could overwrite local rollback/history snapshots. | Operational paths are rejected at every staging level. |
| Q07-F008, P2 | Invalid content created a snapshot and rotated previous recovery files before validation. | Snapshot follows vet/preflight/locks; rotation follows complete success. |
| Q07-F009, P2 | Timestamp/PID/sequence filename sorting removed newer snapshots across 9→10. | Sort by mtime with path tie-break; never delete the current snapshot. |
| Q07-F010, P1 | Restore ignored external users/identity FileLocks. | Deterministic locks for old/new config dependencies within the managed root; deduplicate canonical aliases. |
| Q07-F011, P1 | Exact removed a held nested lock with its absent directory, allowing a second writer to acquire another inode. | Recursive cleanup removes ordinary files while preserving sidecars and their directories. |
| Q07-F012, P2 | Partial-rename failures omitted recovery snapshot and publication state. | HTTP 500 / ok=false, publication_started=true, rollback_snapshot and recovery-before-restart instruction. |
| Q07-F013, P2 | Exact cleanup errors reported success with warnings despite incomplete rollback. | Failure with the same recovery metadata; retain the snapshot. |

Previous exact release: policy **11 FAIL of 14**, publication **6 FAIL of 49**.
The six publication failures cover missing recovery metadata for EIO/ENOSPC/EACCES,
false prune success and two checks proving destroyed lock inode/split flock.
Baseline continues independent probes but fails overall; successful manual recovery
on the old release is not claimed as a new fix.

New release: **14 policy + 49 publication + 38 archive + 75 history = 176 checks PASS**.
Second-rename EIO/ENOSPC/EACCES and prune EACCES use process-scoped LD_PRELOAD
only in the owned supervisor inside verified private namespaces. These are injected
errors, not actual disk exhaustion or host syscall/library replacement. Manual tar
recovery restores exact config/users/identity bytes. SIGKILL before/after the first
rename never reports false HTTP success; a fresh recovered worker authenticates
the administrator with the old identity. Both killed PIDs are verified as fixture-owned.

The 49-check fixture also covers canonical-alias self-deadlock avoidance, continued
flock exclusion after exact and responsive status following failures. Snapshot/prepare
errors are not treated as publication start. Power loss and whole-tree atomicity are
not claimed. [Second batch evidence](../../../release/certification/evidence/q07-publication-20261003.json).

Second-batch qualification: 2265 units / 60 ignored, full/minimal Clippy and rustfmt PASS; fresh 18/327 matrix, aggregate leak and 100 TCP + 100 QUIC / 33 soak PASS. All four native cores passed A/B and match first Q07 byte-for-byte; ABI, copies and provenance PASS. .11 snapshots match; historical .10 legacy IPv4 dump limitations are retained although the current pair matches.
