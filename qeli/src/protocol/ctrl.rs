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

/// Lowest MTU we will believe from a peer. Below the IPv6 minimum there is no plausible
/// path, and accepting e.g. 68 would let one malformed report shrink a session to
/// uselessness. Reports below this are clamped up, not honoured.
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

    #[test]
    fn absurd_reports_are_clamped_into_range() {
        assert_eq!(parse_mtu_report(&mtu_report(0)), Some(MIN_REPORTED_MTU));
        assert_eq!(parse_mtu_report(&mtu_report(68)), Some(MIN_REPORTED_MTU));
        assert_eq!(parse_mtu_report(&mtu_report(65535)), Some(MAX_REPORTED_MTU));
        // A believable value passes through untouched.
        assert_eq!(parse_mtu_report(&mtu_report(1400)), Some(1400));
    }
}
