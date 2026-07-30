package com.qeli.crypto

import android.util.Log
import java.security.KeyFactory
import java.security.KeyPairGenerator
import java.security.PrivateKey
import java.security.PublicKey
import java.security.spec.X509EncodedKeySpec
import javax.crypto.KeyAgreement

/**
 * X25519 for the classic half of the hybrid handshake.
 *
 * Two backends, native FIRST:
 *  * **native** — the same Rust `x25519-dalek` the server and the Rust client use, through
 *    `libqeli.so` (already a hard dependency here: ML-KEM and the fake-tls ClientHello go
 *    the same way, since Android ships neither).
 *  * **managed** — the platform JCA provider, kept as a fallback.
 *
 * Why native is primary and not merely a fallback for old devices: Android's JCA X25519
 * ("XDH") only exists from **API 33 (Android 13)**. Before that every provider lookup fails,
 * so the handshake could not run at all — an Android 9 device just reconnect-looped with
 * "All X25519 key generation methods failed" (the old code tried four variants of the *same*
 * missing provider, which only looked like a fallback chain). Making native the primary path
 * means the code an Android 9 user runs is the code every test run exercises; a path taken
 * only below API 33 could never be covered by our devices and would rot.
 *
 * The managed path stays as a safety net for a build/device where the native library is
 * absent — [com.qeli.protocol.TlsHandshake] already tolerates that for the ClientHello, and
 * the `plain` wire mode does not otherwise need the library at all.
 */
class KeyExchange {

    /**
     * Private key whose scalar was produced by the native backend. Opaque on purpose:
     * `getFormat`/`getEncoded` return null, exactly how Android Keystore presents keys whose
     * material the JVM does not own — so it can never be accidentally serialised, and any
     * JCA operation on it fails loudly instead of silently using half a keypair. Only
     * [computeSharedSecret] knows how to use it.
     */
    private class NativePrivateKey(val secret: ByteArray) : PrivateKey {
        override fun getAlgorithm(): String = "X25519"
        override fun getFormat(): String? = null
        override fun getEncoded(): ByteArray? = null
    }

    /** [publicKey] is null on the native path — nothing outside this class uses the JCA
     *  object; callers need [publicKeyBytes] (the 32 raw bytes that go on the wire). */
    data class KeyPair(
        val privateKey: PrivateKey,
        val publicKey: PublicKey?,
        val publicKeyBytes: ByteArray
    )

    fun generateKeyPair(): KeyPair {
        // ── native ────────────────────────────────────────────────────────────
        if (nativeAvailable) {
            runCatching {
                val both = nativeKeypair()
                if (both != null && both.size == 64) {
                    val secret = both.copyOfRange(0, 32)
                    val pub = both.copyOfRange(32, 64)
                    java.util.Arrays.fill(both, 0)
                    if (!isWeakKey(pub)) {
                        backend = "native"
                        return KeyPair(NativePrivateKey(secret), null, pub)
                    }
                }
            }.onFailure { Log.w(TAG, "native keygen unavailable: ${it.message}") }
        }

        // ── managed (JCA) ─────────────────────────────────────────────────────
        val kp = jcaGenerateKeyPair()
        val encoded: ByteArray = kp.public.encoded
        val rawBytes: ByteArray = when {
            encoded.size == 44 -> encoded.copyOfRange(12, 44)
            encoded.size > 32 -> encoded.copyOfRange(encoded.size - 32, encoded.size)
            else -> throw IllegalStateException("Unexpected SPKI size: ${encoded.size}")
        }
        if (isWeakKey(rawBytes)) {
            throw IllegalStateException("Generated weak X25519 key (all zeros or order-8 point)")
        }
        backend = "managed"
        return KeyPair(kp.private, kp.public, rawBytes)
    }

    fun computeSharedSecret(privateKey: PrivateKey, peerPublicKeyRaw: ByteArray): ByteArray {
        if (isWeakKey(peerPublicKeyRaw)) {
            throw IllegalArgumentException("Peer public key is weak (all zeros or order-8 point)")
        }

        // A native-generated key can only be used natively — there is no JCA object behind it.
        if (privateKey is NativePrivateKey) {
            val ss = nativeDh(privateKey.secret, peerPublicKeyRaw)
                ?: throw IllegalStateException(
                    "X25519 shared secret rejected (malformed input or a degenerate all-zero " +
                        "result from a low-order peer key)"
                )
            return ss
        }

        val spki = buildX25519Spki(peerPublicKeyRaw)
        val kf = KeyFactory.getInstance("XDH")
        val peerPub: PublicKey = kf.generatePublic(X509EncodedKeySpec(spki))

        val ka = KeyAgreement.getInstance("XDH")
        ka.init(privateKey)
        ka.doPhase(peerPub, true)
        return ka.generateSecret()
    }

    /**
     * Platform X25519. Present only from API 33; on older Android every variant below fails
     * (they are all the same absent provider), which is what the native path above exists for.
     */
    private fun jcaGenerateKeyPair(): java.security.KeyPair {
        runCatching {
            val kpg = KeyPairGenerator.getInstance("XDH")
            val spec = Class.forName("java.security.spec.NamedParameterSpec")
                .getConstructor(String::class.java)
                .newInstance("X25519") as java.security.spec.AlgorithmParameterSpec
            kpg.initialize(spec)
            return kpg.genKeyPair()
        }
        runCatching {
            val kpg = KeyPairGenerator.getInstance("X25519")
            return kpg.genKeyPair()
        }
        runCatching {
            val kpg = KeyPairGenerator.getInstance("XDH")
            return kpg.genKeyPair()
        }
        throw RuntimeException(
            "X25519 unavailable: the native core did not load AND this Android has no " +
                "platform provider (added in API 33; this device is API " +
                "${android.os.Build.VERSION.SDK_INT}). Supported ABIs: " +
                android.os.Build.SUPPORTED_ABIS.joinToString(",")
        )
    }

    private fun isWeakKey(rawKey: ByteArray): Boolean {
        if (rawKey.size != 32) return true
        val allZeros = rawKey.all { it == 0x00.toByte() }
        if (allZeros) return true
        val allOnes = rawKey.all { it == 0xFF.toByte() }
        if (allOnes) return true
        val order8Points = listOf(
            "0100000000000000000000000000000000000000000000000000000000000000",
            "e0eb7a7c3b41b8ae1656e3faf19fc46ada098deb9c32b1fd866205165f49b800",
            "5f9c95bca3508c24b1d0b1559c83ef5b04445cc4581c8e86d8224edda094e000",
            "ecffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f",
            "1d00000000000000000000000000000000000000000000000000000000000000",
            "5f19672fdf76ce51ba69c6076a0f77eaddb3a93be6f89688de17d813620a0002",
            "6f9c95bca3508c24b1d0b1559c83ef5b04445cc4581c8e86d8224edda094e000",
            "0000000000000000000000000000000000000000000000000000000000000080"
        )
        val hex = rawKey.joinToString("") { "%02x".format(it) }
        return hex in order8Points
    }

    private fun buildX25519Spki(rawKey: ByteArray): ByteArray {
        require(rawKey.size == 32) { "X25519 raw key must be 32 bytes, got ${rawKey.size}" }
        return ByteArray(44).apply {
            this[0] = 0x30; this[1] = 42
            this[2] = 0x30; this[3] = 5
            this[4] = 0x06; this[5] = 3
            this[6] = 0x2b; this[7] = 0x65; this[8] = 0x6e
            this[9] = 0x03; this[10] = 33; this[11] = 0
            System.arraycopy(rawKey, 0, this, 12, 32)
        }
    }

    private external fun nativeKeypair(): ByteArray?
    private external fun nativeDh(secret: ByteArray, peer: ByteArray): ByteArray?

    companion object {
        private const val TAG = "KeyExchange"

        /** Whether `libqeli.so` loaded. False on a build/device without a matching ABI. */
        @JvmStatic
        val nativeAvailable: Boolean = runCatching { System.loadLibrary("qeli") }.isSuccess

        /** Which backend the last keypair came from ("native" / "managed" / "-"), for the
         *  connection log — the reporter's log then says outright which path ran. */
        @Volatile
        @JvmStatic
        var backend: String = "-"
            private set

        /** One-line diagnostic for the connection log. */
        @JvmStatic
        fun describe(): String =
            "x25519=$backend (native lib ${if (nativeAvailable) "loaded" else "MISSING"}, " +
                "API ${android.os.Build.VERSION.SDK_INT}, " +
                "abi ${android.os.Build.SUPPORTED_ABIS.joinToString("/")})"
    }
}
