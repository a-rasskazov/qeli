//! A4 — JNI bridge over the sans-IO realtls core for the Android client.
//!
//! Java can't call the plain C ABI ([`super::ffi`]) directly, so these
//! `Java_com_qeli_RealTls_*` functions (JNI calling convention) wrap the same
//! [`SansIoClient`]. The Kotlin side is `com.qeli.RealTls` with matching
//! `external fun` declarations and `System.loadLibrary("qeli")`.
//!
//! Convention: a `long` handle holds a `Box<SansIoClient>`; byte arrays cross as
//! `jbyteArray`. `nativeRecv` returns the bytes to send when the handshake
//! completes, an empty array while more input is needed, or `null` on error.

#![cfg(target_os = "android")]

use super::registry::Registry;
use super::sansio::{Progress, SansIoClient};
use crate::crypto::reality::SHORT_ID_LEN;
use crate::crypto::PublicKey;
use jni::objects::{JByteArray, JClass, JString};
use jni::sys::{jboolean, jbyteArray, jint, jlong, JNI_FALSE, JNI_TRUE};
use jni::JNIEnv;

// C-1: opaque handles are generation-checked registry tokens, not raw `Box`
// pointers — a stale/double handle is rejected, never dereferenced. The token is
// still a `jlong`, so the Kotlin side (`com.qeli.RealTls` / `MlKem`) is unchanged.
static REALTLS: Registry<SansIoClient> = Registry::new();
static MLKEM: Registry<MlKemKeypair> = Registry::new();

fn to_array(env: &mut JNIEnv, data: &[u8]) -> jbyteArray {
    env.byte_array_from_slice(data)
        .map(|a| a.into_raw())
        .unwrap_or(std::ptr::null_mut())
}

/// Run `f`, converting a panic into `fallback` instead of letting it unwind.
///
/// EVERY `Java_com_qeli_*` entry point below must go through this. The Android
/// `libqeli.so` is built with `CARGO_PROFILE_RELEASE_PANIC=unwind`
/// (`scripts/build_android_so_11.py`, `scripts/build_so_aes.py`) precisely so the
/// `catch_unwind` guards in the sibling C-ABI module are effective — but this module had
/// none, on any of its twelve functions. Unwinding across a JNI boundary is undefined
/// behaviour; in practice ART aborts, killing the whole VPN service, where returning
/// `0` / `null` / `JNI_FALSE` is something the Kotlin side already handles on every one
/// of these calls. `Registry::with` only catches panics raised INSIDE its closure, so
/// everything around it — `SansIoClient::new`, `mlkem768_keypair`, array conversion,
/// `to_array` — was unprotected. The note in `qeli/Cargo.toml` that explains the unwind
/// override lists only `ffi.rs`; that omission is what this fixes.
/// (Audit 2026-07-27, K4.)
fn guard<T>(fallback: T, f: impl FnOnce() -> T) -> T {
    std::panic::catch_unwind(std::panic::AssertUnwindSafe(f)).unwrap_or(fallback)
}

/// `TlsHandshake.nativeFakeClientHello(x25519Pub, mlKemEk, sni, padToMin) -> byte[]`
/// — the shared Rust-built fake-tls ClientHello (null on error). Lets the Android
/// client emit the identical hello to the Rust/C# clients (same GREASE/shuffle/ALPN)
/// instead of rebuilding it in Kotlin.
#[no_mangle]
pub extern "system" fn Java_com_qeli_protocol_TlsHandshake_nativeFakeClientHello<'local>(
    mut env: JNIEnv<'local>,
    _class: JClass<'local>,
    x25519_pub: JByteArray<'local>,
    ml_ek: JByteArray<'local>,
    sni: JString<'local>,
    pad_to_min: jint,
) -> jbyteArray {
    guard(std::ptr::null_mut(), || {
        let pk_bytes = match env.convert_byte_array(&x25519_pub) {
            Ok(b) if b.len() == 32 => b,
            _ => return std::ptr::null_mut(),
        };
        let ek = match env.convert_byte_array(&ml_ek) {
            Ok(b) if !b.is_empty() => b,
            _ => return std::ptr::null_mut(),
        };
        let sni_str: String = match env.get_string(&sni) {
            Ok(s) => s.into(),
            Err(_) => return std::ptr::null_mut(),
        };
        let mut pk = [0u8; 32];
        pk.copy_from_slice(&pk_bytes);
        let hello = crate::protocol::FakeTlsHandshake::build_client_hello_with_ek(
            &PublicKey::from_bytes(&pk),
            &sni_str,
            pad_to_min.max(0) as usize,
            &ek,
        );
        to_array(&mut env, &hello)
    })
}

/// `RealTls.nativeNew(realityPub, shortId, sni) -> long` (0 on error).
#[no_mangle]
pub extern "system" fn Java_com_qeli_RealTls_nativeNew<'local>(
    mut env: JNIEnv<'local>,
    _class: JClass<'local>,
    reality_pub: JByteArray<'local>,
    short_id: JByteArray<'local>,
    sni: JString<'local>,
) -> jlong {
    guard(0, || {
        let pub_bytes = match env.convert_byte_array(&reality_pub) {
            Ok(b) if b.len() == 32 => b,
            _ => return 0,
        };
        let sid_bytes = match env.convert_byte_array(&short_id) {
            Ok(b) if b.len() >= SHORT_ID_LEN => b,
            _ => return 0,
        };
        let sni_str: String = match env.get_string(&sni) {
            Ok(s) => s.into(),
            Err(_) => return 0,
        };
        let mut pk = [0u8; 32];
        pk.copy_from_slice(&pub_bytes);
        let mut sid = [0u8; SHORT_ID_LEN];
        sid.copy_from_slice(&sid_bytes[..SHORT_ID_LEN]);
        let (client, _hello) = SansIoClient::new(&PublicKey::from_bytes(&pk), &sid, &sni_str);
        REALTLS.insert(client) as jlong
    })
}

/// `RealTls.nativeClientHello(handle) -> byte[]` — the ClientHello to send first.
#[no_mangle]
pub extern "system" fn Java_com_qeli_RealTls_nativeClientHello<'local>(
    mut env: JNIEnv<'local>,
    _class: JClass<'local>,
    handle: jlong,
) -> jbyteArray {
    guard(std::ptr::null_mut(), || {
        match REALTLS.with(handle as u64, |client| client.client_hello().to_vec()) {
            Some(hello) => to_array(&mut env, &hello),
            None => std::ptr::null_mut(),
        }
    })
}

/// `RealTls.nativeRecv(handle, data) -> byte[]` — bytes to send (handshake done),
/// empty (need more), or null (error).
#[no_mangle]
pub extern "system" fn Java_com_qeli_RealTls_nativeRecv<'local>(
    mut env: JNIEnv<'local>,
    _class: JClass<'local>,
    handle: jlong,
    data: JByteArray<'local>,
) -> jbyteArray {
    guard(std::ptr::null_mut(), || {
        let bytes = env.convert_byte_array(&data).unwrap_or_default();
        match REALTLS.with(handle as u64, |client| client.recv(&bytes)) {
            Some(Ok(Progress::NeedMore)) => to_array(&mut env, &[]),
            Some(Ok(Progress::Done(to_send))) => to_array(&mut env, &to_send),
            Some(Err(_)) | None => std::ptr::null_mut(), // None = stale/invalid handle
        }
    })
}

/// `RealTls.nativeSeal(handle, plaintext) -> byte[]` — one application_data record.
#[no_mangle]
pub extern "system" fn Java_com_qeli_RealTls_nativeSeal<'local>(
    mut env: JNIEnv<'local>,
    _class: JClass<'local>,
    handle: jlong,
    data: JByteArray<'local>,
) -> jbyteArray {
    guard(std::ptr::null_mut(), || {
        let bytes = env.convert_byte_array(&data).unwrap_or_default();
        match REALTLS.with(handle as u64, |client| client.seal(&bytes)) {
            Some(Ok(rec)) => to_array(&mut env, &rec),
            Some(Err(_)) | None => std::ptr::null_mut(), // None = stale/invalid handle
        }
    })
}

/// `RealTls.nativeOpen(handle, data) -> byte[]` — concatenated decrypted plaintext.
#[no_mangle]
pub extern "system" fn Java_com_qeli_RealTls_nativeOpen<'local>(
    mut env: JNIEnv<'local>,
    _class: JClass<'local>,
    handle: jlong,
    data: JByteArray<'local>,
) -> jbyteArray {
    guard(std::ptr::null_mut(), || {
        let bytes = env.convert_byte_array(&data).unwrap_or_default();
        let result = REALTLS.with(handle as u64, |client| {
            client.open_push(&bytes).map(|msgs| {
                let mut cat = Vec::new();
                for m in msgs {
                    cat.extend_from_slice(&m);
                }
                cat
            })
        });
        match result {
            Some(Ok(cat)) => to_array(&mut env, &cat),
            Some(Err(_)) | None => std::ptr::null_mut(), // None = stale/invalid handle
        }
    })
}

/// `RealTls.nativeEstablished(handle) -> boolean`.
#[no_mangle]
pub extern "system" fn Java_com_qeli_RealTls_nativeEstablished<'local>(
    _env: JNIEnv<'local>,
    _class: JClass<'local>,
    handle: jlong,
) -> jboolean {
    guard(JNI_FALSE, || {
        match REALTLS.with(handle as u64, |client| client.established()) {
            Some(true) => JNI_TRUE,
            _ => JNI_FALSE, // false, or a stale/invalid handle
        }
    })
}

/// `RealTls.nativeFree(handle)`.
#[no_mangle]
pub extern "system" fn Java_com_qeli_RealTls_nativeFree<'local>(
    _env: JNIEnv<'local>,
    _class: JClass<'local>,
    handle: jlong,
) {
    guard((), || {
        // A double free or a free of a never-issued handle is a safe no-op (C-1).
        REALTLS.remove(handle as u64);
    })
}

// --- ML-KEM-768 bridge (`com.qeli.MlKem`) ---------------------------------
//
// Kotlin has no vetted ML-KEM, so the Android client drives the hybrid qeli
// handshake's post-quantum half through the same `ml-kem` crate the server
// uses. A `long` handle holds a `Box<MlKemKeypair>`: the retained decapsulation
// key plus the public encapsulation key the caller embeds in its ClientHello.
// Lifecycle mirrors the `RealTls` handle — `nativeKeygen` allocates,
// `nativeFree` releases, and the bytes returned by `nativeEncapKey` /
// `nativeDecapsulate` are owned by the JVM once handed back.

struct MlKemKeypair {
    dk: crate::crypto::mlkem::DecapKey,
    ek: Vec<u8>,
}

/// `MlKem.nativeKeygen() -> long` — a fresh ML-KEM-768 keypair handle (0 on error).
#[no_mangle]
pub extern "system" fn Java_com_qeli_MlKem_nativeKeygen<'local>(
    _env: JNIEnv<'local>,
    _class: JClass<'local>,
) -> jlong {
    guard(0, || {
        let (dk, ek) = crate::crypto::mlkem::mlkem768_keypair();
        MLKEM.insert(MlKemKeypair { dk, ek }) as jlong
    })
}

/// `MlKem.nativeEncapKey(handle) -> byte[]` — the 1184-byte encapsulation key to
/// carry in the ClientHello key_share (null on a bad handle).
#[no_mangle]
pub extern "system" fn Java_com_qeli_MlKem_nativeEncapKey<'local>(
    mut env: JNIEnv<'local>,
    _class: JClass<'local>,
    handle: jlong,
) -> jbyteArray {
    guard(std::ptr::null_mut(), || {
        match MLKEM.with(handle as u64, |kp| kp.ek.clone()) {
            Some(ek) => to_array(&mut env, &ek),
            None => std::ptr::null_mut(),
        }
    })
}

/// `MlKem.nativeDecapsulate(handle, ct) -> byte[]` — the 32-byte shared secret
/// from the server's ciphertext, or null on a malformed ciphertext / bad handle.
#[no_mangle]
pub extern "system" fn Java_com_qeli_MlKem_nativeDecapsulate<'local>(
    mut env: JNIEnv<'local>,
    _class: JClass<'local>,
    handle: jlong,
    ct: JByteArray<'local>,
) -> jbyteArray {
    guard(std::ptr::null_mut(), || {
        let ct_bytes = env.convert_byte_array(&ct).unwrap_or_default();
        let result = MLKEM.with(handle as u64, |kp| {
            crate::crypto::mlkem::mlkem768_decapsulate(&kp.dk, &ct_bytes)
        });
        match result {
            Some(Some(ss)) => to_array(&mut env, &ss),
            // inner None = bad ciphertext; outer None = stale/invalid handle
            Some(None) | None => std::ptr::null_mut(),
        }
    })
}

/// `MlKem.nativeFree(handle)`.
#[no_mangle]
pub extern "system" fn Java_com_qeli_MlKem_nativeFree<'local>(
    _env: JNIEnv<'local>,
    _class: JClass<'local>,
    handle: jlong,
) {
    guard((), || {
        // A double free or a free of a never-issued handle is a safe no-op (C-1).
        MLKEM.remove(handle as u64);
    })
}

// --- X25519 bridge (`com.qeli.crypto.KeyExchange`) -------------------------
//
// Android's platform X25519 (JCA "XDH"/"X25519") only exists from API 33
// (Android 13). Below that every provider lookup fails, so the classic half of
// the hybrid handshake could not run at all and the client retried forever
// (reported on Android 9 / API 28). The fix mirrors the ML-KEM bridge above:
// drive it through the same Rust the server uses, so one implementation serves
// every Android version and cannot drift from the peer.
//
// Deliberately STATELESS (no registry handle, unlike RealTls/MlKem): the secret
// scalar crosses back to Kotlin as bytes and returns for each DH. That removes
// the handle lifecycle entirely — no leak on the many mid-handshake error paths
// (retransmit timeouts, auth failures), and no call-site changes to free it.
// The trade-off is the scalar living in a JVM array for the length of a
// handshake; acceptable because it never leaves the process and the alternative
// costs a free() on every failure path. Kotlin wraps it in an opaque
// `java.security.PrivateKey` whose getEncoded() is null — the same shape Android
// Keystore uses for keys whose material is not in the JVM.

/// `KeyExchange.nativeKeypair() -> byte[]` — a fresh X25519 keypair as
/// `secret(32) || public(32)`, or null on error.
#[no_mangle]
pub extern "system" fn Java_com_qeli_crypto_KeyExchange_nativeKeypair<'local>(
    mut env: JNIEnv<'local>,
    _class: JClass<'local>,
) -> jbyteArray {
    guard(std::ptr::null_mut(), || {
        use zeroize::Zeroize;
        let kp = crate::crypto::Keypair::generate();
        let mut out = [0u8; 64];
        out[..32].copy_from_slice(&kp.secret_bytes());
        out[32..].copy_from_slice(kp.public().as_bytes());
        let arr = to_array(&mut env, &out);
        out.zeroize(); // the JVM copy is the only one that outlives this call
        arr
    })
}

/// `KeyExchange.nativeDh(secret32, peer32) -> byte[]` — the 32-byte X25519 shared
/// secret, or null on a malformed input OR a degenerate all-zero result (a peer
/// low-order/identity key, RFC 7748 §6.1 — the same contributory-behaviour check
/// the Rust client and server enforce, which the old managed path never did).
#[no_mangle]
pub extern "system" fn Java_com_qeli_crypto_KeyExchange_nativeDh<'local>(
    mut env: JNIEnv<'local>,
    _class: JClass<'local>,
    secret: JByteArray<'local>,
    peer: JByteArray<'local>,
) -> jbyteArray {
    guard(std::ptr::null_mut(), || {
        use zeroize::Zeroize;
        let s = env.convert_byte_array(&secret).unwrap_or_default();
        let p = env.convert_byte_array(&peer).unwrap_or_default();
        if s.len() != 32 || p.len() != 32 {
            return std::ptr::null_mut();
        }
        let mut sb = [0u8; 32];
        sb.copy_from_slice(&s);
        let mut pb = [0u8; 32];
        pb.copy_from_slice(&p);
        let kp = crate::crypto::Keypair::from_secret_bytes(&sb);
        sb.zeroize();
        let out = match kp.derive_shared_checked(&PublicKey::from_bytes(&pb)) {
            Some(ss) => to_array(&mut env, ss.as_bytes()),
            None => std::ptr::null_mut(),
        };
        out
    })
}
