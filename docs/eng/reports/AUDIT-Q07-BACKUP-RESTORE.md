# Q07: backup, restore and history — first batch

<!-- normative-sync: audit-q07-backup-restore-v1 -->

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

Q07 remains open. Next batch: multi-file publication/prune failures and crashes,
manual recovery proof from rollback snapshot, external users/identity writers,
mixed inline/external users and panel-secret, retention/protection of operational
snapshots, other INI trust boundaries and strict exact-query parsing. Existing
history positive/fault tests passed; archive publication is not a whole-tree
atomic transaction and has no automatic rollback, as retained in the earlier
[budget report](AUDIT-Q05-ARCHIVE-BUDGET.md).

Shared services and deployed binaries were not replaced. Full .11 snapshots match.
Desktop .10 SDK A/B passes; default/explicit legacy IPv4 dumps differ, while nft,
other host fields, PID/start and binary match. Historical unattributed .10 dump
variability remains an evidence limitation; full .10 network-preservation PASS
is not claimed. Rules were not removed/restored. Completed historical debug
artifacts were losslessly gzipped with SHA verification; completed lint cache
removed with sources/test logs retained.

[First batch evidence](../../../release/certification/evidence/q07-backup-restore-20261003.json).

Release qualification: fresh 18/327 matrix, aggregate leak and 100 TCP + 100 QUIC / 33 soak checks PASS. All four native cores passed A/B and match Q06 byte-for-byte; canonical/client copies, ABI and provenance agree.
