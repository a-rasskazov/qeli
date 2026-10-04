# Q14: current worker lifecycle checks

<!-- normative-sync: audit-q14-current-lifecycle-v1 -->

**Batch PASS; Q14 IN_PROGRESS.** 4 October 2026.
Source `711782d6d1cb6e41889c7c359f964e7242e314fc`, Linux artifact `5605f4b7867cefb0886f14c943c499693fb41a0d0f767f8675292115d5f27c55`.
Evidence: `release/certification/evidence/q14-lifecycle-current-20261004.json`.

Three existing isolated fixtures rerun on this release:

- **8/8 worker cases**: TCP/UDP × IPv6 off/manual/route/nat66; malformed INI,
  second-worker rejection, rejected SIGHUP, working control, once-only post_down,
  TUN/NAT/sysctl removal and before/after snapshots. **80 valid reloads** keep
  fd/socket/task and sampled RSS within established limits.
- **22/22 recovery checks**: different control/state paths and nested mount/PID
  cannot bypass namespace admission; SIGKILL, deleted profile, foreign rules preserved,
  post_down retains the lease; startup failure releases admission for a later launch.
- **14/14 multiprofile checks**: simultaneous TCP+UDP, invalid and 10 valid
  reloads, stop, SIGKILL and recovery after sibling removal; once-only hooks and
  final network/control/journal restoration.

Fresh ordinary Linux units: **2365 PASS / 60 ignored**. Evidence selects the passed
supervisor/tasks/control/hooks/shutdown module groups from that same run, not extra
test executions. Privileged ignored tests are not claimed PASS. Fixtures own fresh
NET/mount/PID namespaces and private /etc/qeli. Parent host snapshots match;
active service/executable unchanged.

Review covers Child/PID ownership, retry/Restart/Reload queue, cancel-safe join, deferred
profile resources, control path/IO/drain, loaded-INI trust, once-only post_down, hook process
groups/output bounds, and 45/60-second budgets. No new confirmed defect in this batch.
Earlier D09/D13 and related evidence retain their original SHA and limits.

Next Q14 batch: full supervisor crash/respawn/restart/stop, occupied bind/TUN with a
healthy sibling, control-client pressure and hook failure/cancellation at generation
boundaries. Supervisor panel/metrics/autostart ownership on stop and outer-future
cancellation also requires verification. Those remain open, so Q14 is not complete. Overall after Q13: **13/37 (35.1%)**.
