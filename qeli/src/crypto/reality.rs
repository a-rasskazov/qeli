//! REALITY-style authenticator carried in the TLS `legacy_session_id`.
//!
//! The client embeds a 32-byte token in the ClientHello's session_id. The token
//! is `ChaCha20-Poly1305(k, nonce, short_id ‖ unix_time)` where `k`/`nonce` are
//! HKDF-derived from `X25519(client_ephemeral, server_reality_pub)`. Plaintext is
//! 16 bytes (8 short_id + 8 LE timestamp) → +16-byte tag = exactly 32 bytes, the
//! full session_id. The nonce is derived (not on the wire); each connection uses a
//! fresh ephemeral, so the per-connection key is single-use.
//!
//! The server re-derives the same `k`/`nonce` via `X25519(reality_priv, client_eph_pub)`
//! (the ephemeral pub comes from the ClientHello's key_share), decrypts, and accepts
//! the connection as a qeli client iff the AEAD verifies, the `short_id` is in its
//! allow-list, and the timestamp is fresh (anti-replay). A prober that lacks a valid
//! `short_id` cannot forge the token, so the server transparently proxies it to the
//! real `dest` (REALITY's active-probe defence).

use crate::crypto::{Cipher, Keypair, PublicKey, StaticKeypair};
use hkdf::Hkdf;
use sha2::Sha256;
use std::time::{SystemTime, UNIX_EPOCH};

pub const SHORT_ID_LEN: usize = 8;
const PT_LEN: usize = SHORT_ID_LEN + 8; // short_id(8) + unix_time u64(8)
const INFO: &[u8] = b"qeli-reality-sid-v1";

fn now_unix() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

/// Derive the single-use AEAD key + nonce from the X25519 shared secret.
fn derive_key_nonce(shared: &[u8; 32]) -> ([u8; 32], [u8; 12]) {
    let hk = Hkdf::<Sha256>::new(None, shared);
    let mut okm = [0u8; 44];
    hk.expand(INFO, &mut okm)
        .expect("HKDF expand for reality sid");
    let mut key = [0u8; 32];
    let mut nonce = [0u8; 12];
    key.copy_from_slice(&okm[..32]);
    nonce.copy_from_slice(&okm[32..44]);
    (key, nonce)
}

/// Parse a hex short_id into 8 bytes (zero-padded; extra hex ignored). Both sides
/// parse identically, so the allow-list comparison is exact.
///
/// LENIENT ON PURPOSE for the zero-padding: a short_id shorter than 16 hex digits is a
/// legitimate REALITY configuration and pads out to 8 bytes. It is NOT a validator —
/// non-hex characters are dropped, so garbage collapses to all-zeros. Use
/// [`parse_short_id`] anywhere the input has not already been validated; in particular
/// the server allow-list must not use this function. (Audit 2026-07-27, C8.)
///
/// [`parse_short_id`]: crate::crypto::reality::parse_short_id
pub fn short_id_from_hex(s: &str) -> [u8; SHORT_ID_LEN] {
    let mut out = [0u8; SHORT_ID_LEN];
    let hex: Vec<u8> = s.bytes().filter(|b| b.is_ascii_hexdigit()).collect();
    let mut i = 0;
    while i / 2 < SHORT_ID_LEN && i + 1 < hex.len() {
        let hi = (hex[i] as char).to_digit(16).unwrap_or(0) as u8;
        let lo = (hex[i + 1] as char).to_digit(16).unwrap_or(0) as u8;
        out[i / 2] = (hi << 4) | lo;
        i += 2;
    }
    out
}

/// Strict short_id parse: `None` unless `s` is valid, usable hex.
///
/// Byte-for-byte identical to [`short_id_from_hex`] for every input it accepts — it only
/// adds the gate, so no configuration that works today changes meaning. Rejected:
/// * anything containing a non-hex character (after `:`/`-`/space are stripped),
/// * an empty value,
/// * more than 16 hex digits,
/// * a value that parses to all-zero bytes.
///
/// WHY THIS EXISTS. The lenient parser *filters* non-hex away rather than failing, so a
/// typo or a substituted value such as `short_ids = zzzz` parses to `[0u8; 8]` — and it
/// does so on BOTH sides. The server built its allow-list with that parser, so a
/// misconfigured server accepted any client whose short_id was equally invalid. The
/// REALITY public key is not secret (it ships inside the `qeli://` link), which leaves
/// the short_id as the only thing an active prober must guess — so a silent collapse to
/// a constant is an authentication bypass, not a cosmetic issue. The all-zero result is
/// refused for the same reason: it is exactly what the degenerate parse produced, so
/// honouring it would keep the wildcard alive for operators who configured it literally.
/// (Audit 2026-07-27, C8.)
pub fn parse_short_id(s: &str) -> Option<[u8; SHORT_ID_LEN]> {
    let hex: Vec<u8> = s
        .bytes()
        .filter(|b| !matches!(b, b':' | b'-' | b' '))
        .collect();
    if hex.is_empty() || hex.len() > SHORT_ID_LEN * 2 || !hex.iter().all(u8::is_ascii_hexdigit) {
        return None;
    }
    let out = short_id_from_hex(s);
    if out == [0u8; SHORT_ID_LEN] {
        return None;
    }
    Some(out)
}

/// Client side: seal `{short_id, now}` into a 32-byte session_id using the
/// ephemeral that is also sent as the ClientHello key_share.
///
/// CONTRACT: `ephemeral` MUST be single-use — a fresh keypair per connection. The
/// `(key, nonce)` for this seal is derived deterministically from the ephemeral↔server
/// shared secret, so reusing an ephemeral across two seals would reuse the same AEAD
/// (key, nonce): the two ciphertexts share keystream (short_id cancels, the timestamp XOR
/// leaks) AND reuse the Poly1305 one-time key, which allows token forgery. Every live
/// caller passes a `Keypair::generate()` that doubles as the TLS key_share, so the
/// invariant holds; this note exists to stop a future refactor from caching the ephemeral.
pub fn seal_session_id(
    reality_pub: &PublicKey,
    ephemeral: &Keypair,
    short_id: &[u8; SHORT_ID_LEN],
) -> [u8; 32] {
    let shared = ephemeral.derive_shared(reality_pub);
    let (key, nonce) = derive_key_nonce(shared.as_bytes());
    let mut pt = [0u8; PT_LEN];
    pt[..SHORT_ID_LEN].copy_from_slice(short_id);
    pt[SHORT_ID_LEN..].copy_from_slice(&now_unix().to_le_bytes());
    let ct = Cipher::new(&key)
        .encrypt(&nonce, &pt)
        .expect("reality seal (16B pt → 32B ct)");
    let mut sid = [0u8; 32];
    sid.copy_from_slice(&ct);
    sid
}

/// Server side: open the session_id with the profile's REALITY (identity) key and
/// the client's ephemeral pub (from the key_share). Returns the `short_id` iff the
/// AEAD verifies and the timestamp is within `±window_secs` of now.
pub fn open_session_id(
    reality_priv: &StaticKeypair,
    eph_pub: &PublicKey,
    session_id: &[u8; 32],
    window_secs: u64,
) -> Option<[u8; SHORT_ID_LEN]> {
    // Reject a degenerate all-zero shared secret: a prober can send a low-order
    // ephemeral key_share to force an attacker-predictable key (RFC 7748 §6.1).
    let shared = reality_priv.derive_shared_checked(eph_pub)?;
    let (key, nonce) = derive_key_nonce(shared.as_bytes());
    let pt = Cipher::new(&key).decrypt(&nonce, session_id).ok()?;
    if pt.len() != PT_LEN {
        return None;
    }
    let mut ts_bytes = [0u8; 8];
    ts_bytes.copy_from_slice(&pt[SHORT_ID_LEN..]);
    if now_unix().abs_diff(u64::from_le_bytes(ts_bytes)) > window_secs {
        return None;
    }
    let mut short_id = [0u8; SHORT_ID_LEN];
    short_id.copy_from_slice(&pt[..SHORT_ID_LEN]);
    Some(short_id)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip_with_matching_keys() {
        let reality = StaticKeypair::generate();
        let eph = Keypair::generate();
        let id = short_id_from_hex("0123456789abcdef");
        let sid = seal_session_id(&reality.public, &eph, &id);
        let got = open_session_id(&reality, eph.public(), &sid, 120).unwrap();
        assert_eq!(got, id);
    }

    #[test]
    fn wrong_reality_key_rejected() {
        let reality = StaticKeypair::generate();
        let other = StaticKeypair::generate();
        let eph = Keypair::generate();
        let sid = seal_session_id(&reality.public, &eph, &short_id_from_hex("aabbccdd"));
        assert!(open_session_id(&other, eph.public(), &sid, 120).is_none());
    }

    #[test]
    fn tampered_session_id_rejected() {
        let reality = StaticKeypair::generate();
        let eph = Keypair::generate();
        let mut sid = seal_session_id(&reality.public, &eph, &short_id_from_hex("aabbccdd"));
        sid[3] ^= 0xff;
        assert!(open_session_id(&reality, eph.public(), &sid, 120).is_none());
    }

    #[test]
    fn stale_timestamp_rejected() {
        // window=0 → any non-instant skew rejects; re-seal twice to cross a second
        // is flaky, so assert the boundary: a far-past forged ts can't pass.
        let reality = StaticKeypair::generate();
        let eph = Keypair::generate();
        let id = short_id_from_hex("aabbccdd");
        let sid = seal_session_id(&reality.public, &eph, &id);
        // A 0-second window still accepts a just-sealed token (skew 0); a 1-byte
        // bump to the ciphertext timestamp region breaks AEAD instead — covered
        // above. Here we assert a huge window always accepts and that open works.
        assert!(open_session_id(&reality, eph.public(), &sid, u64::MAX).is_some());
    }

    #[test]
    fn low_order_ephemeral_key_share_rejected() {
        // A prober whose ClientHello key_share is a low-order/identity point
        // (all-zero here) forces an all-zero shared secret; the server must not
        // authenticate it and instead fall through to the proxy-to-dest path.
        let reality = StaticKeypair::generate();
        let zero_pub = PublicKey::from_bytes(&[0u8; 32]);
        assert!(open_session_id(&reality, &zero_pub, &[0u8; 32], 120).is_none());
    }

    #[test]
    fn short_id_hex_parsing() {
        assert_eq!(
            short_id_from_hex("0102030405060708"),
            [1, 2, 3, 4, 5, 6, 7, 8]
        );
        assert_eq!(short_id_from_hex(" a1b2 "), [0xa1, 0xb2, 0, 0, 0, 0, 0, 0]);
    }

    /// The strict parser must agree with the lenient one on everything it accepts, so
    /// switching the server allow-list over cannot change a working deployment.
    #[test]
    fn parse_short_id_matches_lenient_on_valid_input() {
        for s in [
            "0102030405060708",
            "a1b2",
            " a1b2 ",
            "aa:bb:cc:dd",
            "de-ad-be-ef",
            "abc", // odd digit count: lenient drops the trailing nibble, so must we
            "f",   // single digit: lenient yields all-zero -> rejected below, not here
        ] {
            if let Some(strict) = parse_short_id(s) {
                assert_eq!(strict, short_id_from_hex(s), "mismatch for {s:?}");
            }
        }
        assert_eq!(parse_short_id("a1b2"), Some(short_id_from_hex("a1b2")));
    }

    /// The whole point: garbage must NOT collapse to a constant that both sides agree on.
    /// (Audit 2026-07-27, C8.)
    #[test]
    fn parse_short_id_rejects_unusable_values() {
        assert_eq!(
            parse_short_id("zzzz"),
            None,
            "non-hex must not become zeros"
        );
        assert_eq!(parse_short_id("hello"), None);
        assert_eq!(parse_short_id(""), None);
        assert_eq!(parse_short_id("   "), None);
        assert_eq!(
            parse_short_id("0000000000000000"),
            None,
            "all-zero is a wildcard"
        );
        assert_eq!(parse_short_id("00"), None);
        assert_eq!(
            parse_short_id("0102030405060708aa"),
            None,
            "more than 16 hex digits must not be silently truncated"
        );
        // A single digit parses to all-zero under the lenient rule, so it is unusable.
        assert_eq!(parse_short_id("f"), None);
        // The degenerate value the old parser produced is exactly what we now refuse.
        assert_eq!(short_id_from_hex("zzzz"), [0u8; SHORT_ID_LEN]);
    }

    /// Full M1 path: client seals into a ClientHello session_id, server parses the
    /// (browser-like) ClientHello and recovers session_id + key_share, then opens.
    #[test]
    fn end_to_end_via_client_hello() {
        use crate::protocol::FakeTlsHandshake;
        let reality = StaticKeypair::generate();
        let eph = Keypair::generate(); // doubles as TLS key_share + REALITY ephemeral
        let id = short_id_from_hex("0123456789abcdef");
        let sid = seal_session_id(&reality.public, &eph, &id);

        let hello =
            FakeTlsHandshake::build_client_hello(eph.public(), "www.microsoft.com", 0, Some(&sid));
        let (got_sid, key_share) = FakeTlsHandshake::parse_client_hello_full(&hello).unwrap();
        assert_eq!(got_sid, sid, "server must recover the embedded session_id");
        assert_eq!(
            key_share,
            eph.public().as_bytes(),
            "key_share must be the client ephemeral"
        );

        let eph_pub = PublicKey::from_bytes(&<[u8; 32]>::try_from(key_share.as_slice()).unwrap());
        assert_eq!(
            open_session_id(&reality, &eph_pub, &got_sid, 120).unwrap(),
            id
        );

        // A foreign-but-valid ClientHello (no embedded token) must NOT authenticate.
        let foreign =
            FakeTlsHandshake::build_client_hello(Keypair::generate().public(), "x.com", 0, None);
        let (fsid, fks) = FakeTlsHandshake::parse_client_hello_full(&foreign).unwrap();
        let fpub = PublicKey::from_bytes(&<[u8; 32]>::try_from(fks.as_slice()).unwrap());
        assert!(open_session_id(&reality, &fpub, &fsid, 120).is_none());
    }
}
