//! Guard for `qeli check-config`: every key present in a shipped example config
//! must be READ by `from_ini`. An unread key is exactly what check-config reports
//! as "a key that nothing reads — check the spelling", and what a web-panel save
//! silently drops on round-trip. A shipped example must therefore never contain
//! one. This exercises the REAL files the `.deb` installs (not a hand-kept fixture
//! that can drift from them) — the scenario an operator actually runs check-config
//! against — so a newly added config parameter that the parser forgets to read
//! (like the historical `update_check` regression) fails CI here.

use qeli::config::client::ClientConfig;
use qeli::config::format::IniDoc;
use qeli::config::server::ServerConfig;
use qeli::config::users::UsersDb;

#[test]
fn shipped_server_examples_have_no_unread_keys() {
    // The two server examples the .deb installs. `server.conf` is the exhaustive
    // single-profile reference (every server key); the multiprofile one exercises
    // repeated [profile:*] sections. Neither carries GUI-only or retired keys, so
    // the unread set must be exactly empty.
    for (name, text) in [
        ("server.conf", include_str!("../config/server.conf")),
        (
            "server-multiprofile.conf",
            include_str!("../config/server-multiprofile.conf"),
        ),
    ] {
        let doc = IniDoc::parse(text).unwrap_or_else(|e| panic!("{name}: parse error: {e}"));
        ServerConfig::from_ini(&doc).unwrap_or_else(|e| panic!("{name}: from_ini: {e}"));
        // Also consume any inline [user:*] / [group:*] the example might carry, so
        // their keys are not counted as unread.
        let _ = UsersDb::from_ini(&doc);
        let unread = doc.unread_keys();
        assert!(
            unread.is_empty(),
            "{name}: {} key(s) check-config would flag as typos (from_ini never reads them): {:?}",
            unread.len(),
            unread
        );
    }
}

#[test]
fn shipped_client_example_has_no_unexpected_unread_keys() {
    // The client example legitimately carries a few keys that only the Windows /
    // macOS GUI clients implement (this Rust client does not read them) —
    // check-config whitelists exactly these, so the test does too. Anything ELSE
    // left unread would be a real check-config false-positive on a shipped file.
    // Keep this list in sync with GUI_ONLY_CLIENT_KEYS in main.rs.
    const GUI_ONLY: &[&str] = &[
        "dev_node",
        "local",
        "lport",
        "metric",
        "persist_tun",
        "route_file",
    ];
    let text = include_str!("../config/client.conf");
    let doc = IniDoc::parse(text).expect("client.conf parse error");
    ClientConfig::from_ini(&doc).expect("client.conf from_ini");
    let unexpected: Vec<_> = doc
        .unread_keys()
        .into_iter()
        .filter(|(_, k)| !GUI_ONLY.contains(k))
        .collect();
    assert!(
        unexpected.is_empty(),
        "client.conf: {} key(s) check-config would flag as typos: {:?}",
        unexpected.len(),
        unexpected
    );
}
