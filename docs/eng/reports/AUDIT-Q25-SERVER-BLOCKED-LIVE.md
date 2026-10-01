# Q25-F158: saved versus active lockout policy

1 October 2026. Base: `7e4e5238`. D07 remains **IN_PROGRESS**.

The `POST /api/blocked/settings` path changed the panel login limiter directly after saving `[web] brute_force.*`, leaving `live_web.brute_force` stale. Other INI save paths use `reload_web_settings`, which updates both states together and retains the old policy on failure. The lockout tab read the saved INI without distinguishing it from the active policy after a failed reload. The new regression also exposed a false live-reload rejection for a startup-disabled panel without a password, despite there being no listener.

The lockout API now applies the panel policy through the shared live reload. Its save response includes `panel_applied` and reports when the INI was saved but the panel reload failed. `GET /api/blocked/settings` compares the saved and active policies in `panel_applied` and includes `live_panel` for diagnosis. The tab warns about a mismatch; unchanged thresholds preserve existing lockouts. Live reload now requires an admin password only when the panel was enabled at startup; the active-panel guard remains strict. VPN policy still signals the worker and reports a pending restart when the worker is unavailable. The persisted format remains INI; JSON is used only by the internal API.

On .11, the first run passed `cargo fmt --all --check`, two web-reload tests, one BF-candidate validation test, and strict Clippy. The new GET regression then reproduced the false reload rejection for a disabled panel. After the focused fix, repeat job `blockedlive4` was started, but .11 stopped returning an SSH banner. Its exit code and the final Rust build are **not claimed as PASS**. Local `node --check` passed for the template and dictionary, as did `git diff --check`. Compilation was not moved to .10 because it runs the lab server and has only 433 MB of free disk.

Both worker-only and full restart already repeat INI preflight before stopping the running worker; this review found no new defect there. The race with external editors that ignore the advisory lock and the remaining D07 runtime matrix stay open. Register: **5/15 DONE**.
