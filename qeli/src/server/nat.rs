//! Server-side NAT / masquerade for full-tunnel egress, programmed via the
//! **`iptables` CLI only** (never `nft` or `ufw`). When a profile sets
//! `routing.nat.enabled = true`, [`setup`] enables IPv4 forwarding and installs the
//! MASQUERADE + FORWARD + MSS-clamp rules so the client pool can reach the internet
//! through the server's WAN interface.
//!
//! Every rule carries a per-profile iptables comment (`qeli-nat:<profile>`), so
//! [`cleanup`] can find and delete EXACTLY our rules — even after an unclean exit.
//! `run_profile` calls [`cleanup`] on every start (clearing rules left behind, or a
//! now-disabled profile's rules) before [`setup`], and the worker tears them down
//! again on graceful shutdown.
//!
//! Rules are split into ESSENTIAL (MASQUERADE + MSS clamp — full-tunnel egress can't
//! work without them) and BEST-EFFORT (the explicit `FORWARD … ACCEPT` rules, only
//! needed when the host's FORWARD policy is DROP). Because the modern `iptables-nft`
//! wrapper can return success while silently no-op'ing on a chain backed by a legacy
//! table, we VERIFY each rule with `iptables -C` rather than trusting the exit code:
//! an essential rule that won't apply fails the setup; a best-effort one only logs a
//! warning (MASQUERADE alone still routes when the FORWARD policy is ACCEPT).

use std::process::Command;

/// iptables comment tag for the rules belonging to `profile`.
fn tag(profile: &str) -> String {
    format!("qeli-nat:{profile}")
}

/// Locate the `iptables` binary. `None` = not installed — the caller surfaces that
/// as an error + log + panel warning. Checks the usual sbin locations first (cheap,
/// no exec) then falls back to a PATH probe.
pub fn iptables_path() -> Option<String> {
    for p in [
        "/usr/sbin/iptables",
        "/sbin/iptables",
        "/usr/bin/iptables",
        "/bin/iptables",
    ] {
        if std::path::Path::new(p).exists() {
            return Some(p.to_string());
        }
    }
    if Command::new("iptables")
        .arg("--version")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
    {
        return Some("iptables".to_string());
    }
    None
}

/// Whether `iptables` is available on this host (used by the panel to warn).
pub fn available() -> bool {
    iptables_path().is_some()
}

fn ipt(path: &str, args: &[&str]) -> std::io::Result<std::process::Output> {
    Command::new(path).args(args).output()
}

/// Auto-detect the default-route (WAN) interface via `ip route get 1.1.1.1`.
fn detect_wan() -> Option<String> {
    let out = Command::new("ip")
        .args(["route", "get", "1.1.1.1"])
        .output()
        .ok()?;
    if !out.status.success() {
        return None;
    }
    // "1.1.1.1 via 10.0.0.1 dev eth0 src ..." — the token after "dev".
    let s = String::from_utf8_lossy(&out.stdout);
    let toks: Vec<&str> = s.split_whitespace().collect();
    toks.iter()
        .position(|&t| t == "dev")
        .and_then(|i| toks.get(i + 1))
        .map(|s| s.to_string())
}

/// Best-effort `net.ipv4.ip_forward = 1` (needs CAP_NET_ADMIN, which the worker has).
/// Left enabled on teardown — forwarding is a global host knob and flipping it off
/// could break other services on the box.
fn enable_ip_forward() {
    let path = "/proc/sys/net/ipv4/ip_forward";
    if matches!(std::fs::read_to_string(path), Ok(ref v) if v.trim() == "1") {
        return; // already on
    }
    match std::fs::write(path, "1\n") {
        Ok(()) => log::info!("NAT: enabled net.ipv4.ip_forward (left enabled on teardown)"),
        Err(e) => log::warn!(
            "NAT: could not enable net.ipv4.ip_forward ({e}); full-tunnel egress may not route"
        ),
    }
}

/// One iptables rule we manage. `essential = false` rules (FORWARD ACCEPT) are
/// best-effort: a host where they can't be applied still routes if its FORWARD
/// policy is ACCEPT.
struct Rule {
    table: &'static str,
    chain: &'static str,
    args: Vec<String>,
    essential: bool,
}

/// The iptables rules we install for one profile.
fn rules(profile: &str, wan: &str, tun: &str, pool_cidr: &str, mss: i32) -> Vec<Rule> {
    let mss = mss.to_string();
    let comment = tag(profile);
    let cm = |mut r: Vec<String>| -> Vec<String> {
        r.extend([
            "-m".into(),
            "comment".into(),
            "--comment".into(),
            comment.clone(),
        ]);
        r
    };
    vec![
        // ESSENTIAL — MASQUERADE the client pool out the WAN interface.
        Rule {
            table: "nat",
            chain: "POSTROUTING",
            args: cm(vec!["-s".into(), pool_cidr.into(), "-o".into(), wan.into()])
                .into_iter()
                .chain(["-j".into(), "MASQUERADE".into()])
                .collect(),
            essential: true,
        },
        // ESSENTIAL — clamp forwarded-TCP MSS to the tunnel MTU (both directions);
        // avoids the PMTU black hole that hangs downloads on TCP transports.
        Rule {
            table: "mangle",
            chain: "FORWARD",
            args: cm(vec![
                "-p".into(),
                "tcp".into(),
                "--tcp-flags".into(),
                "SYN,RST".into(),
                "SYN".into(),
                "-o".into(),
                tun.into(),
            ])
            .into_iter()
            .chain([
                "-j".into(),
                "TCPMSS".into(),
                "--set-mss".into(),
                mss.clone(),
            ])
            .collect(),
            essential: true,
        },
        Rule {
            table: "mangle",
            chain: "FORWARD",
            args: cm(vec![
                "-p".into(),
                "tcp".into(),
                "--tcp-flags".into(),
                "SYN,RST".into(),
                "SYN".into(),
                "-i".into(),
                tun.into(),
            ])
            .into_iter()
            .chain(["-j".into(), "TCPMSS".into(), "--set-mss".into(), mss])
            .collect(),
            essential: true,
        },
        // BEST-EFFORT — explicitly permit forwarding tun <-> wan (needed only when the
        // FORWARD policy is DROP).
        Rule {
            table: "filter",
            chain: "FORWARD",
            args: cm(vec!["-i".into(), tun.into(), "-o".into(), wan.into()])
                .into_iter()
                .chain(["-j".into(), "ACCEPT".into()])
                .collect(),
            essential: false,
        },
        Rule {
            table: "filter",
            chain: "FORWARD",
            args: cm(vec![
                "-i".into(),
                wan.into(),
                "-o".into(),
                tun.into(),
                "-m".into(),
                "state".into(),
                "--state".into(),
                "RELATED,ESTABLISHED".into(),
            ])
            .into_iter()
            .chain(["-j".into(), "ACCEPT".into()])
            .collect(),
            essential: false,
        },
    ]
}

/// Is this exact rule currently present? Verified with `iptables -C` (the only
/// reliable check across the legacy/nft backends — the exit code of `-A` lies on a
/// chain the nft wrapper considers incompatible).
fn rule_present(path: &str, table: &str, chain: &str, rule: &[String]) -> bool {
    let mut a: Vec<String> = vec!["-t".into(), table.into(), "-C".into(), chain.into()];
    a.extend_from_slice(rule);
    let argv: Vec<&str> = a.iter().map(String::as_str).collect();
    ipt(path, &argv)
        .map(|o| o.status.success())
        .unwrap_or(false)
}

/// Install NAT for `profile`. Returns the chosen WAN interface on success.
pub fn setup(
    profile: &str,
    configured_iface: &str,
    pool_cidr: &str,
    tun: &str,
    mtu: i32,
) -> anyhow::Result<String> {
    let path = iptables_path().ok_or_else(|| {
        anyhow::anyhow!(
            "`iptables` is not installed (apt install iptables) — required for routing.nat.enabled"
        )
    })?;
    // WAN: an explicit, non-default interface wins; otherwise auto-detect. The config
    // default "eth0" is treated as "auto" (it's just a placeholder).
    let iface = configured_iface.trim();
    let wan = if !iface.is_empty() && iface != "eth0" {
        iface.to_string()
    } else {
        detect_wan().ok_or_else(|| {
            anyhow::anyhow!(
                "could not auto-detect the WAN interface; set routing.nat.interface explicitly"
            )
        })?
    };

    enable_ip_forward();
    // Clear any stale copies first so a re-apply can't stack duplicates.
    cleanup_with(&path, profile);

    let mss = (mtu - 40).max(536);
    let mut forward_unapplied = false;
    for r in rules(profile, &wan, tun, pool_cidr, mss) {
        let mut args: Vec<String> = vec!["-t".into(), r.table.into(), "-A".into(), r.chain.into()];
        args.extend(r.args.clone());
        let argv: Vec<&str> = args.iter().map(String::as_str).collect();
        let _ = ipt(&path, &argv); // exit code is unreliable on nft-incompatible chains
        if !rule_present(&path, r.table, r.chain, &r.args) {
            if r.essential {
                cleanup_with(&path, profile); // roll back the partial set
                anyhow::bail!(
                    "iptables could not apply the {}/{} rule — check the host firewall backend \
                     (e.g. legacy/nft mix)",
                    r.table,
                    r.chain
                );
            }
            forward_unapplied = true;
        }
    }
    if forward_unapplied {
        log::warn!(
            "Profile '{profile}': FORWARD ACCEPT rules could not be applied (host has a mixed \
             legacy/nft filter table). NAT egress still works when the FORWARD policy is ACCEPT; \
             if it is DROP, permit forwarding {pool_cidr} <-> {wan} yourself."
        );
    }
    Ok(wan)
}

/// Pure L3 routing WITHOUT NAT (`routing.forward_private`): enable `net.ipv4.ip_forward`
/// and permit forwarding to/from the tunnel, so the server routes TRANSIT traffic between
/// the tunnel and its own networks with the real source IPs preserved (site-to-site) —
/// unlike [`setup`], which MASQUERADEs for internet egress. For a packet the server itself
/// originates to a client's `client_subnet` (#13) neither of these is needed (a route is
/// enough); this is only for third-party transit. Best-effort: a host whose FORWARD policy
/// is ACCEPT already routes. Rules carry the same `qeli-nat:<profile>` tag, so
/// [`cleanup`]/[`cleanup_all`] remove them too.
pub fn enable_routing(profile: &str, tun: &str, mtu: i32) {
    enable_ip_forward();
    let path = match iptables_path() {
        Some(p) => p,
        None => {
            log::info!(
                "Profile '{profile}': forward_private set but iptables is absent — relying on the host FORWARD policy for routing"
            );
            return;
        }
    };
    let mss = (mtu - 40).max(536).to_string();
    let comment = tag(profile);
    let cm = |mut r: Vec<String>| -> Vec<String> {
        r.extend([
            "-m".into(),
            "comment".into(),
            "--comment".into(),
            comment.clone(),
        ]);
        r
    };
    let mss_rule = |dir: &str| -> (&'static str, &'static str, Vec<String>) {
        (
            "mangle",
            "FORWARD",
            cm(vec![
                "-p".into(),
                "tcp".into(),
                "--tcp-flags".into(),
                "SYN,RST".into(),
                "SYN".into(),
                dir.into(),
                tun.into(),
            ])
            .into_iter()
            .chain([
                "-j".into(),
                "TCPMSS".into(),
                "--set-mss".into(),
                mss.clone(),
            ])
            .collect(),
        )
    };
    let accept = |dir: &str| -> (&'static str, &'static str, Vec<String>) {
        (
            "filter",
            "FORWARD",
            cm(vec![dir.into(), tun.into()])
                .into_iter()
                .chain(["-j".into(), "ACCEPT".into()])
                .collect(),
        )
    };
    // MSS-clamp forwarded TCP (PMTU black-hole guard), then permit tun<->anywhere routing.
    for (table, chain, args) in [mss_rule("-o"), mss_rule("-i"), accept("-i"), accept("-o")] {
        let mut argv = vec![
            "-t".to_string(),
            table.to_string(),
            "-A".to_string(),
            chain.to_string(),
        ];
        argv.extend(args);
        let refs: Vec<&str> = argv.iter().map(String::as_str).collect();
        let _ = ipt(&path, &refs); // best-effort; nft-mixed hosts already route on ACCEPT policy
    }
    log::info!(
        "Profile '{profile}': forward_private — ip_forward + FORWARD ACCEPT for {tun} (routing, no NAT)"
    );
}

/// Redirect in-tunnel DNS from the standard port 53 to where the proxy actually listens.
///
/// `dns.port` exists so the proxy can dodge a host service already holding 53 (dnsmasq,
/// Pi-hole and friends bind `0.0.0.0:53`, which covers the TUN address too). But the port was
/// then PUSHED to clients — and no client platform can use it: `VpnService.Builder` and
/// `NEDNSSettings` take an address and nothing else, Windows and macOS configure resolvers by
/// IP, and even the Rust client only manages it through `resolvectl`'s `IP#port` syntax, which
/// is lost the moment it falls back to writing `resolv.conf`. So a non-default `dns.port`
/// silently black-holed DNS for every client but one.
///
/// Splitting the two settings fixes it properly: the proxy keeps its odd port, clients are
/// told the only port they can express — 53 — and the kernel bridges the gap here. A no-op
/// when the proxy already listens on 53.
///
/// Tagged with the same per-profile comment as every other rule, so [`cleanup`] removes it
/// with the rest when the profile stops.
pub fn enable_dns_redirect(profile: &str, tun: &str, listen: &str, port: u16) -> bool {
    if port == 53 {
        return true; // nothing to bridge
    }
    let path = match iptables_path() {
        Some(p) => p,
        None => {
            log::error!(
                "Profile '{profile}': dns.port = {port} needs an iptables REDIRECT so clients                  can keep using port 53, but iptables is absent. Clients would be handed a                  resolver they cannot reach. Set dns.port = 53, or install iptables."
            );
            return false;
        }
    };
    let comment = tag(profile);
    // UDP only: the proxy binds a UDP socket and has no TCP listener, so a TCP rule would
    // point at nothing. Unchanged from the default-port behaviour, where 53/tcp is equally
    // unserved.
    let args: Vec<String> = vec![
        "-i".into(),
        tun.into(),
        "-p".into(),
        "udp".into(),
        "-d".into(),
        listen.into(),
        "--dport".into(),
        "53".into(),
        "-m".into(),
        "comment".into(),
        "--comment".into(),
        comment,
        "-j".into(),
        "REDIRECT".into(),
        "--to-ports".into(),
        port.to_string(),
    ];
    let mut argv = vec![
        "-t".to_string(),
        "nat".to_string(),
        "-A".to_string(),
        "PREROUTING".to_string(),
    ];
    argv.extend(args.clone());
    let refs: Vec<&str> = argv.iter().map(String::as_str).collect();
    let _ = ipt(&path, &refs);

    // VERIFY rather than trust the exit code — `iptables-nft` can report success for a rule it
    // did not install, which is why every other rule here is checked the same way.
    if rule_present(&path, "nat", "PREROUTING", &args) {
        log::info!(
            "Profile '{profile}': DNS redirect {listen}:53 -> :{port} on {tun}              (clients are told 53; the proxy listens on {port})"
        );
        true
    } else {
        log::error!(
            "Profile '{profile}': FAILED to install the DNS redirect {listen}:53 -> :{port} on              {tun}. Clients would be handed a resolver they cannot reach — set dns.port = 53,              or fix iptables."
        );
        false
    }
}

/// Remove every NAT rule tagged for `profile` (idempotent; a no-op if none exist or
/// iptables is absent).
pub fn cleanup(profile: &str) {
    if let Some(path) = iptables_path() {
        cleanup_with(&path, profile);
    }
}

/// Remove EVERY qeli-managed NAT rule (`qeli-nat:*`, any profile). Called once at
/// worker startup so rules left behind by a profile that has since been REMOVED
/// from the config — whose own [`cleanup`] is never called again — don't leak
/// forever. Active profiles re-install their rules immediately afterwards.
pub fn cleanup_all() {
    if let Some(path) = iptables_path() {
        cleanup_matching(&path, "qeli-nat:", false);
    }
}

fn cleanup_with(path: &str, profile: &str) {
    // EXACT tag match: the per-profile teardown must delete only THIS profile's rules.
    // A substring match (the old behaviour) made `qeli-nat:web` match `qeli-nat:web2`, so
    // starting/stopping profile `web` silently wiped profile `web2`'s MASQUERADE/FORWARD/
    // MSS rules and broke its egress until it restarted. Both names are valid idents. (M1)
    cleanup_matching(path, &tag(profile), true);
}

/// The iptables comment on a rule (the token right after `--comment`, dequoted). `None`
/// when the rule carries no comment.
fn rule_comment(line: &str) -> Option<String> {
    let toks: Vec<&str> = line.split_whitespace().collect();
    toks.windows(2)
        .find(|w| w[0] == "--comment")
        .map(|w| w[1].trim_matches('"').to_string())
}

/// Delete every managed rule whose iptables comment matches `needle`. With `exact`, the
/// comment must equal `needle` (a specific `qeli-nat:<profile>` tag); without it, the
/// comment must START WITH `needle` (the bare `qeli-nat:` prefix used by `cleanup_all`).
/// The comment is our own tag — no wire input — but we still match the parsed token, not a
/// raw substring, so one profile name can never be a prefix of another's rules. (M1)
fn cleanup_matching(path: &str, needle: &str, exact: bool) {
    for (table, chain) in [
        ("nat", "POSTROUTING"),
        ("filter", "FORWARD"),
        ("mangle", "FORWARD"),
    ] {
        // List the chain, find a tagged rule, delete it by replaying its own spec
        // with -D, and re-list (positions shift). Capped to avoid spinning.
        for _ in 0..64 {
            let out = match ipt(path, &["-t", table, "-S", chain]) {
                Ok(o) if o.status.success() => o,
                _ => break,
            };
            let listing = String::from_utf8_lossy(&out.stdout);
            let Some(line) = listing.lines().find(|l| {
                l.starts_with("-A ")
                    && rule_comment(l).is_some_and(|c| {
                        if exact {
                            c == needle
                        } else {
                            c.starts_with(needle)
                        }
                    })
            }) else {
                break;
            };
            // "-A CHAIN <spec...>" -> "iptables -t table -D CHAIN <spec...>".
            // Strip the quotes iptables-save puts around the comment value.
            let spec: Vec<String> = line
                .split_whitespace()
                .skip(2)
                .map(|t| t.trim_matches('"').to_string())
                .collect();
            let mut args: Vec<String> = vec!["-t".into(), table.into(), "-D".into(), chain.into()];
            args.extend(spec);
            let argv: Vec<&str> = args.iter().map(String::as_str).collect();
            if ipt(path, &argv)
                .map(|o| !o.status.success())
                .unwrap_or(true)
            {
                break; // delete failed — don't loop forever
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{rule_comment, tag};

    /// Reproduce the substring bug: `web`'s exact tag must NOT match `web2`'s rule, or
    /// tearing down `web` wipes `web2`'s NAT and breaks its egress. (M1)
    #[test]
    fn exact_tag_does_not_match_a_sibling_prefix() {
        let web = tag("web"); // "qeli-nat:web"
        let web2 = tag("web2"); // "qeli-nat:web2"
        let line_web2 =
            format!("-A POSTROUTING -o qeli0 -m comment --comment {web2} -j MASQUERADE");
        let c = rule_comment(&line_web2).unwrap();
        assert_eq!(c, web2);
        assert_ne!(c, web, "exact match must distinguish web from web2");
        assert!(
            c.starts_with(&web),
            "the substring bug: web2 DOES start with web"
        );
        // The prefix form (cleanup_all) intentionally matches both.
        assert!(c.starts_with("qeli-nat:"));
    }

    #[test]
    fn rule_comment_handles_quoted_and_bare() {
        let bare = "-A FORWARD -o t -m comment --comment qeli-nat:us -j ACCEPT";
        assert_eq!(rule_comment(bare).as_deref(), Some("qeli-nat:us"));
        let quoted = "-A FORWARD -o t -m comment --comment \"qeli-nat:us\" -j ACCEPT";
        assert_eq!(rule_comment(quoted).as_deref(), Some("qeli-nat:us"));
        let none = "-A FORWARD -o t -j ACCEPT";
        assert_eq!(rule_comment(none), None);
    }
}
