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
