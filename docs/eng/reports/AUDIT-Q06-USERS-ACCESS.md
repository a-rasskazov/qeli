# Q06: users and access revocation — batches 1–2

Date: 3 October 2026. **Batch status: PASS; overall Q06: IN_PROGRESS.**

The fixes were tested on isolated Linux release `c15280a7f83f185c10014b08ccf1dddbaf6660ef987d6de2799e4e85bf1d2b21`.
**Latest qualification is the second batch below: 199 Q06 checks.**
Configurations remain INI. JSON is only the service body of HTTP/control APIs.

## Confirmed defects and fixes

| ID | Defect | Result |
| --- | --- | --- |
| Q06-F001 | Scalar/array/null bodies cleared bandwidth/quota/expiry; wrong enabled/password/bandwidth types reported success. Wrong live bandwidth profile types selected all profiles. | Shared object check and strict field types before hashing, locks and writes. Malformed requests preserve exact previous users INI bytes. |
| Q06-F002 | Deleting a file override restored the inline user or previous group from server.conf. | Deletion of any entry also defined inline is rejected before mutation. Users can be disabled; inline definitions must be removed in server.conf. |
| Q06-F003 | Wrong route.gateway types silently removed the next hop. | Strict nullable string validation; missing/null/empty remain supported. |
| Q06-F004 | Delete, enabled=false through Edit and profile restrictions changed the database while existing TCP/UDP sessions kept working. | Successful SIGHUP applies current rights to open sessions through existing admission/kick/lease teardown. The sweep rechecks current rights, including sessions registered after the initial scan. |
| Q06-F005 | A second persist-command writer after panel bandwidth save replaced explicit burst_mbps with its CLI default. | The panel writes INI once; reload applies effective limit_mbps to existing sessions, including group inheritance. |

The baseline packet run reproduced six tunnels that kept working:
TCP and UDP × Edit disabled / Delete / profile restriction. Tests check both the
session list and ICMP through the client TUN. Private INPUT DROP prevents a false
success through the outer interface after TUN removal. The separate Disable endpoint
and quota/expiry have their own checks.

## Validation

- 119 real HTTP/API checks PASS: strict bodies/types, ACL arrays, u32 boundary, missing group,
  route/gateway families, inline/file precedence, fixed-address collisions,
  nullable clears, quota/expiry, password and limit preservation, share/QR.
- 57 checks PASS with real Linux TCP/UDP clients: 12 revocation scenarios,
  fixed IP, live group bandwidth 2 → 3 Mbps, expiry and seeded exhausted quota.
  Quota uses a private usage sidecar with a known counter, not a new gigabyte benchmark.
- 293 Q04 HTTP checks and 75 Q05 transaction checks PASS on the same new release.
- 2263 Linux unit tests PASS, 60 ignored; pinned full/minimal Clippy and rustfmt PASS;
  116 editor JS groups and panel checks PASS.
- Linux release matrix: 18 cases / 327 assertions PASS, host_restored=true.
  Fresh 100 TCP + 100 QUIC soak / 33 checks PASS; fresh desktop/Android native A/B,
  SHA256SUMS and provenance PASS. All four client libraries are byte-identical to Q04.

Users API confirms persistence and queued reload. It is not a synchronous receipt
of worker authentication readiness. The fixture waits for the user in read-only
worker control before initial authentication, keeping revoke tests separate from a
startup race and brute-force lockout. Historical fixture failures are retained separately
from canonical results.

## Boundaries after the first batch

Q06 remains open: UsersDb filesystem/lock/crash and concurrent writers,
current inline auth in worker control, live ACL/group restriction changes,
multiple devices and replacement of unsafe legacy fixtures. `test_user_reload.py`
and `test_l3_user_limits.py` were not run: they control shared services/fixed paths.
`burst_mbps` remains a legacy stored field; separate data-plane burst enforcement is unconfirmed.
No new benchmark or physical qualification is claimed. Mac, router and Windows VM were excluded by the user.

All new network tests use NET/mount/PID namespaces. Working qeli.service,
PID/start identity and binary were preserved; source and all compilation inputs are hashed.
[Plan](../plans/FULL-SYSTEM-AUDIT.md#06-users-groups-and-access-issuance).

Three legacy firewall/NAT rules appeared on desktop host `.10` during the native build;
raw evidence retains `host_restored=false`. Service PID/start and working executable
were unchanged. The origin is unattributed and no firewall restoration was performed.
This deviation is not reported as unchanged-network PASS; desktop proves A/B artifacts only.

[Final evidence](../../../release/certification/evidence/q06-users-access-20261003.json).

## Second batch: INI storage and inline auth after SIGHUP

**PASS; overall Q06 remains IN_PROGRESS.** New release `dda3c71f6c51e356d3a123f853f64073570ac17ac9c1a21b805f79141ef91e78`.

**Q06-F006:** SIGHUP installed the new user database, but four persistent control
commands merged users.conf with startup inline users/groups. The real baseline
resurrected a removed inline account through enable-user and failed to disable
an account introduced after reload. The fix retains the last accepted auth
configuration and holds its read lease through the INI transaction and live user
update. Reload replaces auth and users under the same lock order. enable-user,
disable-user, set-limit and set-bandwidth are covered by a regression test.

- New users-storage: 23 checks PASS. Eight concurrent creates lose no accounts;
  disjoint edits of one account preserve both fields. Corrupt INI (unknown key,
  invalid number, invalid UTF-8), read-only storage and rename refusal preserve
  exact bytes; normal saving recovers afterwards.
- API 119 and TCP/UDP live 57 reran successfully on this release: 199 Q06 checks.
- 2264 Linux units, 60 ignored; full/minimal Clippy and rustfmt PASS. Fresh 18/327
  release matrix and 100 TCP + 100 QUIC / 33 soak PASS.
- Fresh native A/B and ABI/provenance PASS; library bytes unchanged. .11 retained network and service. Desktop raw host_restored=false: the first
  default iptables-save dump differs from later ones, while explicit legacy/nft
  dumps and all other inventory fields agree. Read-only repetitions reproduce
  the inconsistent default dump; newly added rules are not established in this
  run. The earlier .10 deviation remains unattributed.

Storage coverage is still partial: ENOSPC/EACCES, lock timeout, crash/durability
and errors after published writes remain. Live ACL/groups, multiple devices and
legacy burst remain as well. These checks do not close Q06.
[Second batch evidence](../../../release/certification/evidence/q06-users-storage-20261003.json).
