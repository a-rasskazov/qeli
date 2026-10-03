# Q08: cryptography and keys — first batch

<!-- normative-sync: audit-q08-crypto-keys-v1 -->

Date: 3 October 2026. **Batch: PASS; overall Q08: IN_PROGRESS.**
Configuration remains INI. The 32-byte key format, algorithms and wire protocol are unchanged.

## Findings

| ID | Problem | Fix |
| --- | --- | --- |
| Q08-F001, P2 | Three identity/panel/session-key loaders read unbounded files and could block on FIFOs; a dangling identity link was treated as missing and replaced with a new identity. | Shared crypto/key_file.rs validates the opened regular-file inode and size, reads at most 33 bytes, opens Unix FIFOs nonblocking, and refuses dangling links without generation. Temporary secret buffers use Zeroizing. |
| Q08-F002, P2 | Legacy panel-secret migration preceded the modern FileLock. Corrupt legacy material could silently cause generation of a key incompatible with existing password_enc. | Modern load, migration and generation share one lock and recheck; modern keys take precedence, corrupt/inaccessible legacy files never trigger replacement generation. |
| Q08-F003, P2 | Both client verifiers used unchecked X25519 DH for static identity; low-order keys allow computing proofs with an attacker-known zero shared secret. | Checked DH rejects those identities before proof acceptance and credential transmission in the shared transport core. No bypass of a valid nondegenerate pin was confirmed. |

Read/generation handling is shared across three loaders and their unbounded reads are removed. Publication retains the existing atomic-private writer. Operator links to existing regular files remain supported; reading preserves existing owner/mode, generated files are 0600. Damaged identities never rotate automatically. Session-key errors retain the existing per-process fallback and warning, so those cookies do not survive restart. CLI reversible password storage remains best-effort; Argon2 hashes are a separate authentication mechanism.

## Reproduction and validation

Previous exact release `ba7d93afc47c71592e2d1d20e18d2c7c6a6cb0eb4248b674cf713e756aa1c712`: **6 FAIL of 19** storage checks — identity FIFO, dangling link, unlocked migration, corrupt-legacy replacement, panel FIFO and session FIFO. Independent probes continued while the baseline failed overall. The corrected baseline fixture releases only its own FIFO and gracefully stops its supervisor; private network and external host/service snapshots are restored. The initial forced-supervisor-kill fixture is not accepted as the baseline because it failed orphan-worker cleanup.

Final release `0fdcb1a4ed45e850b9d7e6cd1b3bc3965f3775c6682ac59bcc0348a028e1a749`: **19 storage + 25 restore/state = 44 HTTP/system checks PASS** in verified private NET/mount/PID namespaces. Coverage includes eight identity readers, lengths 0/31/33/4 MiB, FIFO/dangling-link inode preservation, regular operator links, held modern FileLock and modern-key precedence, byte-identical 0600 migration, corrupt-legacy refusal, storage recovery and cookies across fresh supervisors. Q07 regression covers reissue, legacy migration, mixed users/groups and actual restored VPN clients with tunnel ping, including a new host without panel-secret.

The unit negative vector constructs computable proofs for public points 0 and 1 with DH=0; both verifiers now refuse them and subsequently accept a legitimate proof. Previous unchecked acceptance is established by source and proof construction; no live hostile-peer baseline or valid explicit-pin bypass is claimed. The shared verifier call was reviewed before credential construction/transmission in the transport core.

An independent Python HMAC-SHA256 implementation checks **5 HKDF wire vectors / 18 checks** across all four schemes, directions, IKM order and input changes. It never calls the Rust generator/helper. This is an independent consistency implementation, not an external crypto audit or independent primitive certification.

Linux: **2270 units PASS / 60 ignored**, full/minimal Clippy and rustfmt PASS. Fresh **18/327 matrix**, aggregate leak and **100 TCP + 100 QUIC / 33 soak checks PASS**. All four native cores pass independent A/B builds; ABI/canonical-client copies/provenance PASS. .11 snapshots/service/binary remain unchanged. The current .10 pair and fields are recorded; historical unattributed legacy IPv4 dump variability remains a limitation, with no general .10 host-preservation PASS. No working-service replacement, push or new performance benchmark. Physical advisory rows remain unchanged.

## Remaining overall Q08

Independent X25519/ML-KEM/AEAD vectors, further static binding/proof-before-credentials review, TOFU/RNG/nonce exhaustion/rotation/zeroization and owner/mode/link policies remain. Current fixes are fully checked; these are the remaining section scope rather than deferred mandatory verification of this batch. Bounded reads do not promise hard regular-filesystem IO deadlines. Sidecar locks coordinate current writers; power loss, uncoordinated root writes and old binaries are not certified. The previously accepted AES expanded-schedule zeroization limitation remains.

[Batch evidence](../../../release/certification/evidence/q08-keys-20261003.json).
