//! Per-user lifetime traffic accounting + quota bookkeeping (Tier-2).
//!
//! Server-side only — no wire/protocol change, so every client keeps working
//! unchanged. Consumption is kept in a sidecar `usage.json` (NOT the users file,
//! which holds password hashes and is rewritten on every CRUD), so accounting
//! never risks that file.
//!
//! Accounting is driven by the worker's usage sweep (see `server::usage_sweep`):
//! once every few seconds it reads each live session's byte counters — which the
//! data plane already increments per packet — and folds the *delta since last
//! seen* into the per-user total. Folding is keyed by `session_id` and idempotent
//! (`committed` marker), so nothing is double-counted and the hot path is never
//! touched: zero added per-packet work.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

/// Sidecar file (qeli-owned, lives beside the config). Re-read by the panel.
pub const USAGE_PATH: &str = "/etc/qeli/usage.json";

pub fn now_unix() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

/// Migrate a pre-split sidecar in place: an old entry carries only `used_bytes`
/// (down/up default to 0). The historical total can't be split retroactively, so
/// attribute it to DOWNLOAD — the dominant VPN direction and the one the cap
/// limits, so enforcement stays equivalent. Idempotent: once down/up are populated
/// it only re-derives `used_bytes = down + up`, so it's safe to run on every read.
fn migrate_legacy(map: &mut HashMap<String, UserUsage>) {
    for e in map.values_mut() {
        if e.used_down == 0 && e.used_up == 0 && e.used_bytes > 0 {
            e.used_down = e.used_bytes;
        }
        e.used_bytes = e.used_down + e.used_up;
    }
}

#[derive(Serialize, Deserialize, Default, Clone)]
pub struct UserUsage {
    /// Download: bytes the server sent TO the client (`bytes_sent`). This is the
    /// direction the data cap limits.
    #[serde(default)]
    pub used_down: u64,
    /// Upload: bytes the server received FROM the client (`bytes_recv`).
    #[serde(default)]
    pub used_up: u64,
    /// Combined total (`used_down + used_up`). Kept in sync so pre-split readers and
    /// the legacy sidecar format keep working; the split fields are authoritative.
    pub used_bytes: u64,
    pub last_seen: i64,
    #[serde(default)]
    pub sessions: u64,
}

#[derive(Default)]
struct Inner {
    /// Persisted per-user totals.
    usage: HashMap<String, UserUsage>,
    /// In-memory: `(down, up)` already folded for a live `session_id` (idempotency).
    committed: HashMap<u64, (u64, u64)>,
}

pub struct UsageStore {
    path: String,
    inner: Mutex<Inner>,
    /// When set, this handle NEVER writes: `flush` is a no-op and `Drop` does nothing.
    ///
    /// The supervisor and the worker are separate processes (`qeli _worker`) that each
    /// open this same file. Only the worker accumulates — it folds live counters and
    /// flushes periodically, then flushes once more on SIGTERM before
    /// `std::process::exit(0)`, which deliberately skips destructors. The supervisor
    /// merely serves `/api/usage`, refreshing its copy with `reload()` when the panel
    /// asks. But it held a full read-write store, so its `Drop::flush` fired on a normal
    /// shutdown and wrote back the snapshot it had read at STARTUP — silently rolling the
    /// file back to that point. Every `systemctl restart qeli`, including the panel's
    /// "Apply & Restart" button, therefore discarded all accounting since the supervisor
    /// booted, and users past their quota passed the check again. Quotas effectively did
    /// not survive a restart. (Audit 2026-07-27, K3.)
    read_only: bool,
}

impl UsageStore {
    /// Load the sidecar read-write (the worker's handle).
    ///
    /// Absent → empty (normal first run). Present-but-unparsable → empty too, but LOUD:
    /// silently resetting the file wiped every user's lifetime total (and quota) with no
    /// trace, and the next `flush` would then overwrite the corrupt file with the empty
    /// set — so warn before that happens.
    pub fn load(path: &str) -> Self {
        Self::load_inner(path, false)
    }

    /// Load the sidecar for READING only — see the `read_only` field.
    ///
    /// Also skips moving a corrupt file aside: that is a write, and the worker owns this
    /// file. Two processes renaming it concurrently is exactly the race this avoids.
    pub fn load_read_only(path: &str) -> Self {
        Self::load_inner(path, true)
    }

    fn load_inner(path: &str, read_only: bool) -> Self {
        let usage = match std::fs::read_to_string(path) {
            Ok(s) => match serde_json::from_str::<HashMap<String, UserUsage>>(&s) {
                Ok(mut u) => {
                    migrate_legacy(&mut u);
                    u
                }
                Err(e) if read_only => {
                    log::warn!(
                        "usage: {path} is unparsable ({e}); this read-only handle reports \
                         EMPTY totals and leaves the file alone for the worker to handle."
                    );
                    HashMap::new()
                }
                Err(e) => {
                    // Preserve the corrupt file BEFORE returning empty: otherwise the next
                    // flush overwrites the only copy of the (recoverable) accounting data
                    // with the empty set. Move it aside so a fresh usage.json is written
                    // and the original stays for manual recovery.
                    let ts = std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .map(|d| d.as_secs())
                        .unwrap_or(0);
                    let aside = format!("{path}.corrupt-{ts}");
                    match std::fs::rename(path, &aside) {
                        Ok(()) => log::warn!(
                            "usage: {path} is unparsable ({e}) — moved aside to {aside} and \
                             starting from EMPTY totals; restore it if the data matters."
                        ),
                        Err(re) => log::error!(
                            "usage: {path} is unparsable ({e}) AND could not be moved aside \
                             ({re}) — starting EMPTY; the next flush WILL overwrite it."
                        ),
                    }
                    HashMap::new()
                }
            },
            Err(_) => HashMap::new(),
        };
        UsageStore {
            path: path.to_string(),
            inner: Mutex::new(Inner {
                usage,
                committed: HashMap::new(),
            }),
            read_only,
        }
    }

    fn lock(&self) -> std::sync::MutexGuard<'_, Inner> {
        self.inner.lock().unwrap_or_else(|p| p.into_inner())
    }

    /// Accrue a live session's running byte total. Idempotent per `session_id`:
    /// only the increase since the last fold is added, so calling it repeatedly
    /// (the sweep) never double-counts.
    pub fn fold(&self, session_id: u64, user: &str, cur_down: u64, cur_up: u64) {
        let mut g = self.lock();
        let (prev_down, prev_up) = g.committed.get(&session_id).copied().unwrap_or((0, 0));
        // Per-session counters are monotonic (fetch_add), so cur ≥ prev; saturating_sub
        // guards a wrap/reset anyway. Only fold when there is new traffic.
        if cur_down + cur_up > prev_down + prev_up {
            // A session_id absent from `committed` is new → count one connection. Markers
            // are pruned only for dead sessions, so a live session is counted exactly once.
            let first = !g.committed.contains_key(&session_id);
            g.committed.insert(session_id, (cur_down, cur_up));
            let e = g.usage.entry(user.to_string()).or_default();
            e.used_down += cur_down.saturating_sub(prev_down);
            e.used_up += cur_up.saturating_sub(prev_up);
            e.used_bytes = e.used_down + e.used_up;
            e.last_seen = now_unix();
            if first {
                e.sessions += 1;
            }
        }
    }

    /// Combined lifetime total (download + upload).
    pub fn used_bytes(&self, user: &str) -> u64 {
        self.lock()
            .usage
            .get(user)
            .map(|u| u.used_bytes)
            .unwrap_or(0)
    }

    /// Lifetime DOWNLOAD total (server→client). This is the direction the data cap
    /// limits, so quota enforcement reads this, not the combined total.
    pub fn used_down(&self, user: &str) -> u64 {
        self.lock()
            .usage
            .get(user)
            .map(|u| u.used_down)
            .unwrap_or(0)
    }

    /// Forget committed markers for sessions that are no longer live, so the map
    /// can't grow without bound.
    pub fn prune(&self, live: &HashSet<u64>) {
        self.lock().committed.retain(|id, _| live.contains(id));
    }

    /// Zero a user's counters (admin "reset usage") — download, upload and total.
    pub fn reset(&self, user: &str) {
        if let Some(u) = self.lock().usage.get_mut(user) {
            u.used_down = 0;
            u.used_up = 0;
            u.used_bytes = 0;
        }
    }

    pub fn snapshot(&self) -> HashMap<String, UserUsage> {
        self.lock().usage.clone()
    }

    /// Re-read the on-disk file — used by the supervisor/panel to observe the
    /// worker's flushes (the two run in separate processes).
    pub fn reload(&self) {
        if let Ok(s) = std::fs::read_to_string(&self.path) {
            if let Ok(mut u) = serde_json::from_str::<HashMap<String, UserUsage>>(&s) {
                // Present down/up correctly even if the worker hasn't yet flushed the
                // split format (first ~10 s after an upgrade): migrate on read too.
                migrate_legacy(&mut u);
                self.lock().usage = u;
            }
        }
    }

    /// Persist atomically (temp + rename) so a crash can't truncate the file.
    ///
    /// A read-only handle never writes — see the `read_only` field for why the
    /// supervisor must not.
    pub fn flush(&self) {
        if self.read_only {
            log::trace!("usage: flush skipped (read-only handle)");
            return;
        }
        let snap = self.snapshot();
        if let Ok(json) = serde_json::to_vec_pretty(&snap) {
            if let Err(e) = crate::util::write_atomic(&self.path, &json) {
                // Non-fatal: also runs from Drop, so never panic. Surface the
                // error (disk full / permission / rename race) so a persistently
                // failing flush -- silently dropping folded deltas -- is visible.
                log::warn!("usage: failed to persist {}: {e}", self.path);
            }
        }
    }
}

impl Drop for UsageStore {
    /// Best-effort final flush on a graceful teardown, so the deltas folded since
    /// the last sweep aren't lost when the store is dropped between sweeps. A hard
    /// `SIGKILL` still skips this (Drop can't run) — the periodic sweep bounds that
    /// loss to one interval.
    fn drop(&mut self) {
        self.flush();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A path for a store that must start EMPTY.
    ///
    /// These used to point at `/nonexistent/…`, on the assumption that the directory
    /// could never be written to. That assumption is environmental, not guaranteed —
    /// on a host where `/nonexistent` happens to exist (ours does), `Drop::flush`
    /// succeeds, the next `load()` reads the previous run's totals back, and the
    /// counts grow by one run every time (`sessions: 2` became 6 after three runs).
    /// Use a private temp path and clear it up front so the test states what it means.
    fn empty_store_path(tag: &str) -> String {
        let p = std::env::temp_dir().join(format!("qeli-usage-test-{tag}.json"));
        let _ = std::fs::remove_file(&p);
        p.to_string_lossy().into_owned()
    }
    /// A read-only handle must not write the file — not via `flush`, and not via `Drop`.
    ///
    /// Reproduces the supervisor/worker interaction that rolled accounting back on every
    /// restart: the supervisor loads at T0, the worker accumulates to T1, the supervisor
    /// exits and its destructor writes T0 over T1. (Audit 2026-07-27, K3.)
    #[test]
    fn read_only_handle_never_writes_the_file() {
        let path = empty_store_path("k3");

        // T0: the supervisor's view at startup — empty.
        let supervisor = UsageStore::load_read_only(&path);
        assert!(supervisor.snapshot().is_empty());

        // The worker accumulates and persists T1.
        {
            let worker = UsageStore::load(&path);
            worker.fold(1, "alice", 1_000, 100);
            worker.flush();
        }
        let after_worker = std::fs::read_to_string(&path).expect("worker must have written");
        assert!(after_worker.contains("alice"));

        // An explicit flush on the read-only handle must be a no-op...
        supervisor.flush();
        assert_eq!(
            std::fs::read_to_string(&path).unwrap(),
            after_worker,
            "read-only flush must not touch the file"
        );

        // ...and so must its Drop, which is what actually caused the regression.
        drop(supervisor);
        assert_eq!(
            std::fs::read_to_string(&path).unwrap(),
            after_worker,
            "read-only Drop must not roll the file back to the startup snapshot"
        );

        // Sanity: the writable handle still round-trips what the worker stored.
        let reread = UsageStore::load(&path);
        assert_eq!(reread.used_down("alice"), 1_000);

        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn fold_counts_each_session_once() {
        let s = UsageStore::load(&empty_store_path("a4"));
        s.fold(1, "alice", 80, 20); // down 80, up 20
        s.fold(1, "alice", 200, 50); // same session grows → still ONE connection
        s.fold(2, "alice", 40, 10); // a second session for alice
        s.fold(3, "bob", 10, 0);
        let snap = s.snapshot();
        assert_eq!(
            snap["alice"].sessions, 2,
            "two distinct session_ids = 2 connections"
        );
        assert_eq!(snap["alice"].used_down, 240, "200 + 40");
        assert_eq!(snap["alice"].used_up, 60, "50 + 10");
        assert_eq!(snap["alice"].used_bytes, 300, "down + up");
        assert_eq!(s.used_down("alice"), 240, "quota reads download only");
        assert_eq!(snap["bob"].sessions, 1);
    }

    #[test]
    fn fold_does_not_double_count_a_live_session() {
        let s = UsageStore::load(&empty_store_path("a4b"));
        for (d, u) in [(10u64, 1u64), (20, 3), (30, 6), (40, 10)] {
            s.fold(7, "carol", d, u);
        }
        let snap = s.snapshot();
        assert_eq!(
            snap["carol"].sessions, 1,
            "repeated folds of one session = 1"
        );
        assert_eq!(snap["carol"].used_down, 40, "latest download total");
        assert_eq!(snap["carol"].used_up, 10, "latest upload total");
    }

    #[test]
    fn migrate_attributes_legacy_total_to_download() {
        let mut m = HashMap::new();
        // Pre-split entry: only used_bytes set, down/up default 0.
        m.insert(
            "old".to_string(),
            UserUsage {
                used_bytes: 1500,
                last_seen: 1,
                sessions: 3,
                ..Default::default()
            },
        );
        // Already-split entry must be left alone (only used_bytes re-derived).
        m.insert(
            "new".to_string(),
            UserUsage {
                used_down: 200,
                used_up: 50,
                used_bytes: 0,
                last_seen: 1,
                sessions: 1,
            },
        );
        migrate_legacy(&mut m);
        assert_eq!(m["old"].used_down, 1500, "legacy total → download");
        assert_eq!(m["old"].used_up, 0);
        assert_eq!(m["old"].used_bytes, 1500);
        assert_eq!(m["new"].used_down, 200, "split entry untouched");
        assert_eq!(m["new"].used_up, 50);
        assert_eq!(m["new"].used_bytes, 250, "used_bytes re-derived");
    }

    #[test]
    fn reset_zeroes_both_directions() {
        let s = UsageStore::load(&empty_store_path("a4c"));
        s.fold(1, "dave", 500, 100);
        s.reset("dave");
        let snap = s.snapshot();
        assert_eq!(snap["dave"].used_down, 0);
        assert_eq!(snap["dave"].used_up, 0);
        assert_eq!(snap["dave"].used_bytes, 0);
    }
}
