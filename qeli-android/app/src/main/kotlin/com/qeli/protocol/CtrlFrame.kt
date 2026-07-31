package com.qeli.protocol

/**
 * In-tunnel control frames — small typed messages carried as ordinary AEAD records alongside
 * the IP packets. Port of qeli/src/protocol/ctrl.rs.
 *
 * Why in-tunnel: the one thing that needs sending — the tunnel MTU this client settled on — is
 * only known AFTER the handshake (on UDP it comes out of the path-MTU probe), so no handshake
 * field can carry it. Riding inside the tunnel also means the frame inherits the session's AEAD
 * and replay protection, instead of being a bare datagram whose only identity is a source
 * address anyone could spoof.
 *
 * Wire: `[0xC1][0x9B][type(1)][len(1)][body(len)]`. The tunnel's plaintext is otherwise an IP
 * packet (or empty, for the heartbeat); 0xC1's high nibble is 0xC, which is neither 4 nor 6, so
 * a control frame can never be confused with IPv4/IPv6 in either direction.
 *
 * Additive: a server that predates this has no branch for the frame and discards it as a
 * malformed packet, keeping its profile MTU — exactly its old behaviour. Nothing waits for a
 * reply.
 */
object CtrlFrame {
    val MAGIC = byteArrayOf(0xC1.toByte(), 0x9B.toByte())
    const val HDR_LEN = 4                 // magic(2) + type(1) + len(1)
    const val TYPE_MTU_REPORT: Byte = 1   // body: [mtu(2 BE)]

    /**
     * Client→server: what this build is, so `list-clients` and the panel can answer "who still
     * needs to update?". Body: `[verLen(1)][version][platform]`.
     *
     * SELF-REPORTED, NOT ATTESTED. Any authenticated peer can claim any string, so this is
     * diagnostics only and must never gate anything.
     */
    const val TYPE_CLIENT_INFO: Byte = 2

    // Caps mirror ctrl.rs. Deliberately small: the value is peer-chosen and ends up in a CLI
    // table, the JSON API, the panel's DOM and the log.
    const val MAX_VERSION_LEN = 32
    const val MAX_PLATFORM_LEN = 16

    /** The platform tag this build reports. A closed set, like ctrl.rs. */
    const val PLATFORM = "android"

    /** Semver plus the punctuation real builds use. The server refuses anything else OUTRIGHT
     *  rather than scrubbing it, so a frame it would reject must not be built here either. */
    private fun validVersion(s: String) =
        s.isNotEmpty() && s.length <= MAX_VERSION_LEN &&
            s.all { it.code < 128 && (it.isLetterOrDigit() || it == '.' || it == '-' || it == '+' || it == '_') }

    /** A short lowercase identifier: linux, windows, macos, android, ios, … */
    private fun validPlatform(s: String) =
        s.isNotEmpty() && s.length <= MAX_PLATFORM_LEN &&
            s.all { it in 'a'..'z' || it in '0'..'9' || it == '-' }

    /**
     * Build the client-info frame, or null when either field breaks the caps or the charset —
     * the caller then sends nothing and the server shows the session as unknown, which is
     * exactly the pre-feature behaviour.
     */
    fun clientInfo(version: String, platform: String = PLATFORM): ByteArray? {
        if (!validVersion(version) || !validPlatform(platform)) return null
        val v = version.toByteArray(Charsets.US_ASCII)
        val p = platform.toByteArray(Charsets.US_ASCII)
        val bodyLen = 1 + v.size + p.size
        if (bodyLen > 0xFF) return null
        return byteArrayOf(MAGIC[0], MAGIC[1], TYPE_CLIENT_INFO, bodyLen.toByte(), v.size.toByte()) +
            v + p
    }

    /** Build the MTU report frame for [mtu]. */
    fun mtuReport(mtu: Int): ByteArray {
        val m = mtu.coerceIn(0, 0xFFFF)
        return byteArrayOf(
            MAGIC[0], MAGIC[1], TYPE_MTU_REPORT, 2,
            ((m shr 8) and 0xFF).toByte(), (m and 0xFF).toByte(),
        )
    }

    /** True if a decrypted tunnel plaintext is a control frame, not an IP packet. */
    fun isCtrl(p: ByteArray): Boolean =
        p.size >= HDR_LEN && p[0] == MAGIC[0] && p[1] == MAGIC[1]
}
