//! In-tunnel control frames: small typed messages that travel as ordinary AEAD records
//! alongside the IP packets, for state neither side can express in the handshake.
//!
//! Why in-tunnel and not another handshake field: the one thing we need to send —
//! the client's *discovered* path MTU — is only known AFTER the handshake. The client
//! probes the path once AuthOK has landed and the socket is idle (see
//! `client::probe_udp_mtu`), so there is no earlier message to carry it.
//!
//! Why not a bare datagram on the UDP socket next to the MTU probes: those are keyed by
//! source address and are not authenticated, so anyone who can guess a session's
//! `IP:port` could shrink that session's MTU. Riding inside the tunnel means the frame
//! inherits the session's AEAD and replay protection, and it works identically on the
//! TCP and UDP transports.
//!
//! # Wire
//!
//! ```text
//! [0xC1][0x9B][type(1)][len(1)][body(len)]
//! ```
//!
//! The tunnel's plaintext is otherwise an IP packet, or empty for the heartbeat. The
//! magic's first byte has high nibble `0xC`, which is neither 4 nor 6, so a control
//! frame can never be mistaken for IPv4/IPv6 and vice versa. `len` makes the frame
//! skippable, so a peer can ignore a type it does not know instead of guessing its size.
//!
//! # Compatibility
//!
//! Additive in both directions. A peer that predates this module has no branch for the
//! frame: it fails that peer's `version == 4` test and is discarded (the server's
//! forwarder drops it, the client's TUN writer never sees a routable packet). So a new
//! client may send the report to an old server, which simply keeps using its profile
//! MTU — the exact behaviour it had before. Nothing depends on a reply.

/// Frame magic. `0xC1 >> 4 == 0xC`, so it collides with neither IP version.
pub const CTRL_MAGIC: [u8; 2] = [0xC1, 0x9B];
/// magic(2) + type(1) + len(1).
pub const CTRL_HDR_LEN: usize = 4;

/// Client→server: the tunnel MTU the client actually settled on, after probing.
/// Body: `[mtu(2 BE)]`.
pub const CTRL_MTU_REPORT: u8 = 1;

/// Client→server: what the client is, so `list-clients` and the panel can show which
/// build each session runs — the operator's answer to "who still needs to update?".
/// Body: `[ver_len(1)][version][platform]`.
///
/// SELF-REPORTED, NOT ATTESTED. Any authenticated peer can claim any string; this is
/// diagnostics, never a policy input. Nothing may gate access on it.
pub const CTRL_CLIENT_INFO: u8 = 2;

/// Caps for the self-reported identity. Deliberately small: the value is peer-chosen and
/// ends up in the CLI table, the JSON API, the panel and the log, so a long one is either
/// a bug or an attempt to bloat per-session state. `version` fits semver plus a build
/// suffix; `platform` fits a short identifier (`linux`, `android`, `windows`, …).
pub const MAX_CLIENT_VERSION_LEN: usize = 32;
pub const MAX_CLIENT_PLATFORM_LEN: usize = 16;

/// Semver plus the punctuation real builds use. Anything else is refused outright rather
/// than scrubbed: the strings reach a log (where a newline forges a line), a terminal
/// table, and the panel's DOM, and "reject" is the only policy with no clever edge case.
fn valid_version(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= MAX_CLIENT_VERSION_LEN
        && s.bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'-' | b'+' | b'_'))
}

/// A short lowercase identifier — `linux`, `windows`, `macos`, `android`, `ios`, `router`.
fn valid_platform(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= MAX_CLIENT_PLATFORM_LEN
        && s.bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
}

/// Build the client-info frame. `None` when either field would violate the caps or the
/// charset — the caller then simply sends nothing, and the peer shows "unknown", which is
/// exactly the pre-feature behaviour.
pub fn client_info(version: &str, platform: &str) -> Option<Vec<u8>> {
    if !valid_version(version) || !valid_platform(platform) {
        return None;
    }
    let body_len = 1 + version.len() + platform.len();
    if body_len > u8::MAX as usize {
        return None;
    }
    let mut f = Vec::with_capacity(CTRL_HDR_LEN + body_len);
    f.extend_from_slice(&CTRL_MAGIC);
    f.push(CTRL_CLIENT_INFO);
    f.push(body_len as u8);
    f.push(version.len() as u8);
    f.extend_from_slice(version.as_bytes());
    f.extend_from_slice(platform.as_bytes());
    Some(f)
}

/// Read a client-info frame as `(version, platform)`. `None` when this is not one, or the
/// body is malformed, or either field fails the charset/length rules — a peer that lies
/// about itself gets nothing shown, not a mangled string in the operator's table.
pub fn parse_client_info(p: &[u8]) -> Option<(String, String)> {
    let (ty, body) = parse(p)?;
    if ty != CTRL_CLIENT_INFO || body.is_empty() {
        return None;
    }
    let vlen = body[0] as usize;
    let version = std::str::from_utf8(body.get(1..1 + vlen)?).ok()?;
    let platform = std::str::from_utf8(body.get(1 + vlen..)?).ok()?;
    if !valid_version(version) || !valid_platform(platform) {
        return None;
    }
    Some((version.to_string(), platform.to_string()))
}

/// The platform tag this build reports. Deliberately a closed set of short identifiers
/// rather than `std::env::consts::OS` passed through: the panel groups by this value, and
/// an unrecognised target should read as `other` instead of putting an arbitrary target
/// triple in front of the operator.
pub fn platform_tag() -> &'static str {
    match std::env::consts::OS {
        "linux" => "linux",
        "windows" => "windows",
        "macos" => "macos",
        "android" => "android",
        "ios" => "ios",
        "freebsd" => "freebsd",
        _ => "other",
    }
}

/// This build's own client-info frame — the single project version and [`platform_tag`].
/// `None` only if the crate version ever stops matching the charset, in which case the
/// client sends nothing and the server shows it as unknown.
pub fn this_build() -> Option<Vec<u8>> {
    client_info(env!("CARGO_PKG_VERSION"), platform_tag())
}

/// Lowest MTU we will believe from a peer.
///
/// 576 is the IPv4 minimum reassembly buffer (RFC 791) — NOT the IPv6 minimum, which is 1280;
/// the comment here used to say the latter. Below this there is no plausible path, and taking
/// e.g. 68 on faith would let one malformed report shrink a session to uselessness. Reports
/// below it are clamped up, not honoured.
pub const MIN_REPORTED_MTU: u16 = 576;
/// Highest MTU we will believe. Anything larger than a jumbo-less Ethernet path is
/// either a bug or an attempt to push the server into emitting oversized packets.
pub const MAX_REPORTED_MTU: u16 = 9000;

/// True if `p` (a decrypted tunnel plaintext) is a control frame rather than an IP packet.
#[inline]
pub fn is_ctrl(p: &[u8]) -> bool {
    p.len() >= CTRL_HDR_LEN && p[0] == CTRL_MAGIC[0] && p[1] == CTRL_MAGIC[1]
}

/// Build the MTU report frame for `mtu`.
pub fn mtu_report(mtu: u16) -> Vec<u8> {
    let mut f = Vec::with_capacity(CTRL_HDR_LEN + 2);
    f.extend_from_slice(&CTRL_MAGIC);
    f.push(CTRL_MTU_REPORT);
    f.push(2);
    f.extend_from_slice(&mtu.to_be_bytes());
    f
}

/// Parse a control frame into `(type, body)`, or `None` when it is malformed. A frame
/// whose declared `len` does not fit the buffer is rejected rather than truncated —
/// there is no reason for a legitimate peer to emit one, and guessing invites confusion
/// between a short read and a lie.
pub fn parse(p: &[u8]) -> Option<(u8, &[u8])> {
    if !is_ctrl(p) {
        return None;
    }
    let ty = p[2];
    let len = p[3] as usize;
    let body = p.get(CTRL_HDR_LEN..CTRL_HDR_LEN + len)?;
    Some((ty, body))
}

/// Read an MTU report's value, clamped into the believable range. `None` when this is
/// not an MTU report or the body is the wrong size.
pub fn parse_mtu_report(p: &[u8]) -> Option<u16> {
    let (ty, body) = parse(p)?;
    if ty != CTRL_MTU_REPORT || body.len() != 2 {
        return None;
    }
    let mtu = u16::from_be_bytes([body[0], body[1]]);
    Some(mtu.clamp(MIN_REPORTED_MTU, MAX_REPORTED_MTU))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The exact bytes, pinned identically in the C#, Kotlin and Swift ports. A port that
    /// drifts on byte order or the magic would make the server read a nonsense MTU.
    #[test]
    fn mtu_report_matches_the_shared_vector() {
        // 1280 = 0x0500, big-endian.
        assert_eq!(mtu_report(1280), vec![0xC1, 0x9B, 0x01, 0x02, 0x05, 0x00]);
        assert_eq!(
            mtu_report(u16::MAX),
            vec![0xC1, 0x9B, 0x01, 0x02, 0xFF, 0xFF]
        );
        assert_eq!(mtu_report(0), vec![0xC1, 0x9B, 0x01, 0x02, 0x00, 0x00]);
    }

    #[test]
    fn mtu_report_roundtrips() {
        let f = mtu_report(1280);
        assert!(is_ctrl(&f));
        assert_eq!(f.len(), CTRL_HDR_LEN + 2);
        assert_eq!(parse_mtu_report(&f), Some(1280));
        assert_eq!(
            parse(&f).map(|(t, b)| (t, b.len())),
            Some((CTRL_MTU_REPORT, 2))
        );
    }

    /// The discriminator that keeps control frames and IP packets apart. If this ever
    /// fails, a control frame could be routed as a packet (or a packet parsed as a frame).
    #[test]
    fn magic_cannot_collide_with_an_ip_packet() {
        assert_ne!(CTRL_MAGIC[0] >> 4, 4);
        assert_ne!(CTRL_MAGIC[0] >> 4, 6);
        // A real IPv4 header and a real IPv6 header are both rejected as control frames.
        let ipv4 = [
            0x45u8, 0, 0, 40, 0, 0, 0, 0, 64, 6, 0, 0, 10, 8, 0, 2, 1, 1, 1, 1,
        ];
        assert!(!is_ctrl(&ipv4));
        let mut ipv6 = [0u8; 40];
        ipv6[0] = 0x60;
        assert!(!is_ctrl(&ipv6));
        // …and the heartbeat (an empty plaintext) is not one either.
        assert!(!is_ctrl(&[]));
    }

    #[test]
    fn malformed_frames_are_rejected_not_guessed() {
        // Truncated header: the length byte never arrived.
        assert_eq!(parse(&[0xC1, 0x9B, CTRL_MTU_REPORT]), None);
        // Declared length runs past the buffer.
        assert_eq!(parse(&[0xC1, 0x9B, CTRL_MTU_REPORT, 8, 0, 0]), None);
        // Right type, wrong body size.
        assert_eq!(parse_mtu_report(&[0xC1, 0x9B, CTRL_MTU_REPORT, 1, 5]), None);
        // Unknown type is parsed (so it can be skipped) but is not an MTU report.
        let unknown = [0xC1, 0x9B, 0xEE, 1, 7];
        assert_eq!(parse(&unknown), Some((0xEE, &[7u8][..])));
        assert_eq!(parse_mtu_report(&unknown), None);
    }

    /// The exact bytes, to be pinned identically in the C#, Kotlin and Swift ports.
    #[test]
    fn client_info_matches_the_shared_vector() {
        assert_eq!(
            client_info("0.7.13", "linux").unwrap(),
            vec![
                0xC1, 0x9B, 0x02, 0x0C, // magic, type=2, len=12
                0x06, // ver_len=6
                b'0', b'.', b'7', b'.', b'1', b'3', //
                b'l', b'i', b'n', b'u', b'x',
            ]
        );
        assert_eq!(
            parse_client_info(&client_info("0.7.13", "linux").unwrap()),
            Some(("0.7.13".into(), "linux".into()))
        );
    }

    /// This build must be able to describe itself: a crate version that stopped matching
    /// the charset would silently disable the feature for every client at once.
    #[test]
    fn this_build_can_describe_itself() {
        let f = this_build().expect("own version/platform must pass validation");
        let (v, p) = parse_client_info(&f).unwrap();
        assert_eq!(v, env!("CARGO_PKG_VERSION"));
        assert_eq!(p, platform_tag());
    }

    #[test]
    fn client_info_roundtrips_every_platform_we_ship() {
        for p in ["linux", "windows", "macos", "android", "ios", "router"] {
            let f = client_info("1.0.0-rc1+build.7", p).unwrap();
            assert!(is_ctrl(&f));
            assert_eq!(
                parse_client_info(&f),
                Some(("1.0.0-rc1+build.7".into(), p.to_string()))
            );
            // The MTU reader must not mistake it for its own frame, and vice versa.
            assert_eq!(parse_mtu_report(&f), None);
        }
        assert_eq!(parse_client_info(&mtu_report(1400)), None);
    }

    /// The string is peer-chosen and lands in a log line, a terminal table and the panel's
    /// DOM. Every one of these would be a real injection if it were merely scrubbed.
    #[test]
    fn hostile_client_info_is_refused_outright() {
        // Log-line forgery, terminal escapes, HTML, and a NUL.
        for bad in [
            "1.0\nJul 30 12:00:00 qeli: root logged in",
            "1.0\u{1b}[2J",
            "<script>alert(1)</script>",
            "1.0\0",
            "1.0 beta",  // space
            "1.0/../..", // path-ish
            "",          // empty
        ] {
            assert!(client_info(bad, "linux").is_none(), "built: {bad:?}");
            assert!(
                parse_client_info(&forge(bad, "linux")).is_none(),
                "parsed: {bad:?}"
            );
        }
        // Platform is stricter still: no uppercase, no punctuation beyond '-'.
        for bad in ["Linux", "linux_x86", "linux!", ""] {
            assert!(client_info("1.0", bad).is_none(), "built: {bad:?}");
            assert!(
                parse_client_info(&forge("1.0", bad)).is_none(),
                "parsed: {bad:?}"
            );
        }
        // Over the caps.
        let long_v = "1".repeat(MAX_CLIENT_VERSION_LEN + 1);
        let long_p = "a".repeat(MAX_CLIENT_PLATFORM_LEN + 1);
        assert!(client_info(&long_v, "linux").is_none());
        assert!(client_info("1.0", &long_p).is_none());
        assert!(parse_client_info(&forge(&long_v, "linux")).is_none());
        assert!(parse_client_info(&forge("1.0", &long_p)).is_none());
    }

    /// Build a frame WITHOUT the builder's validation, to prove the parser stands on its
    /// own — the bytes on the wire come from a peer, not from our builder.
    fn forge(version: &str, platform: &str) -> Vec<u8> {
        let body_len = 1 + version.len() + platform.len();
        let mut f = vec![CTRL_MAGIC[0], CTRL_MAGIC[1], CTRL_CLIENT_INFO];
        f.push(body_len.min(255) as u8);
        f.push(version.len().min(255) as u8);
        f.extend_from_slice(version.as_bytes());
        f.extend_from_slice(platform.as_bytes());
        f
    }

    /// A declared `ver_len` that runs past the body must not panic or read neighbouring
    /// bytes — it is a peer-supplied index into a peer-supplied buffer.
    #[test]
    fn client_info_length_field_cannot_over_read() {
        // ver_len declares 200 bytes of version inside a 9-byte body.
        let mut f = vec![CTRL_MAGIC[0], CTRL_MAGIC[1], CTRL_CLIENT_INFO, 9, 200];
        f.extend_from_slice(b"1.0linux");
        assert_eq!(parse_client_info(&f), None);
        // Empty body.
        assert_eq!(parse_client_info(&[0xC1, 0x9B, CTRL_CLIENT_INFO, 0]), None);
        // ver_len == body length leaves an empty platform.
        assert_eq!(parse_client_info(&forge("1.0", "")), None);
    }

    #[test]
    fn absurd_reports_are_clamped_into_range() {
        assert_eq!(parse_mtu_report(&mtu_report(0)), Some(MIN_REPORTED_MTU));
        assert_eq!(parse_mtu_report(&mtu_report(68)), Some(MIN_REPORTED_MTU));
        assert_eq!(parse_mtu_report(&mtu_report(65535)), Some(MAX_REPORTED_MTU));
        // A believable value passes through untouched.
        assert_eq!(parse_mtu_report(&mtu_report(1400)), Some(1400));
    }
}
