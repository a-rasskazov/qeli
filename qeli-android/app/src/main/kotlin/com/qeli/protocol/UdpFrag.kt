package com.qeli.protocol

/**
 * App-layer fragmentation for the large UDP handshake messages. Port of
 * qeli/src/protocol/udp_frag.rs.
 *
 * The post-quantum UDP handshake is big (ML-KEM-768: ek 1184 B in the ClientHello,
 * ct 1088 B + cert in the ServerHello -> CH ~1440 B, SH ~1959 B). A single ~2 KB
 * datagram is IP-fragmented, and mobile / CGNAT networks routinely DROP IP fragments,
 * so the UDP handshake silently hangs (works on Wi-Fi, fails on LTE). We split the
 * ClientHello (and reassemble the ServerHello) into <=MAX_CHUNK-byte fragments that
 * never need IP fragmentation.
 *
 * Wire: [MAGIC(3)][msgId(1)][idx(1)][count(1)][chunk...]. Sits below the QUIC-mask /
 * obfs-XOR transforms (each fragment is wrapped independently). The magic cannot open a
 * TLS record (0x16 0x03), so a fragment is distinguishable from a legacy single datagram.
 */
object UdpFrag {
    val MAGIC = byteArrayOf(0xF0.toByte(), 0x9B.toByte(), 0x71.toByte())
    const val HDR_LEN = 6            // magic(3) + msgId(1) + idx(1) + count(1)

    /** IPv6 minimum link MTU (RFC 8200 §5) — the narrowest path the handshake must survive. */
    const val IPV6_MIN_MTU = 1280
    // Worst-case outer headers around one fragment, inside out. Emitted sizes, not protocol
    // minimums: an IPv6 + obfs + QUIC-masked fragment really carries all of them at once.
    private const val OUTER_QUIC = 1 + 4 + 1 + 4 + 1 + 1 + 2 + 4  // QUIC long header (Quic.wrapLong)
    private const val OUTER_OBFS_SEAL = 1 + 12                    // obfs flag byte + nonce
    private const val OUTER_UDP = 8
    private const val OUTER_IPV6 = 40
    // Headroom so adding one more outer layer cannot silently push the handshake back over
    // IPV6_MIN_MTU — the exact regression the old hard-coded 1200 was.
    private const val OUTER_RESERVE = 32

    /**
     * Max payload bytes per fragment. **Derived**, not chosen: chunk + header + QUIC long
     * header + obfs seal + UDP + IPv6 must fit [IPV6_MIN_MTU].
     *
     * This was 1200 — QUIC's initial-packet floor, which budgets a whole datagram, not the
     * payload inside four more layers. The handshake wraps each fragment in a QUIC **long**
     * header (18 B; the data plane's short header is only 9 B), so the real worst case was
     * 1200 + 6 + 18 + 13 + 8 + 40 = 1285 — five bytes over the IPv6 minimum, i.e. the PQ
     * handshake could not complete on a 1280-MTU IPv6 path with obfs + QUIC masking on.
     *
     * This bounds only what we **emit**; [MAX_CHUNK_ACCEPT] bounds what we accept. Keeping the
     * two separate is what makes the change compatible in both directions — see there.
     * (Audit 2026-07-30, #14.)
     */
    const val MAX_CHUNK =
        IPV6_MIN_MTU - OUTER_IPV6 - OUTER_UDP - OUTER_OBFS_SEAL - OUTER_QUIC - OUTER_RESERVE - HDR_LEN

    /**
     * Largest chunk we **accept**, pinned to the historical 1200 that every build before the
     * #14 fix emitted.
     *
     * Reassembly is size-agnostic — fragments are placed by idx, with no offset or per-fragment
     * length field — so the only thing a receiver does with a chunk size is bound it from above
     * for anti-DoS. Shrinking [MAX_CHUNK] keeps our fragments readable by any peer; but
     * shrinking the accept bound with it would have rejected every fragment from a pre-fix
     * peer, breaking the handshake in the other direction. Must never drop below 1200.
     */
    const val MAX_CHUNK_ACCEPT = 1200
    const val MAX_FRAGS = 24         // anti-DoS cap on the reassembly buffer
    const val MSG_CLIENT_HELLO: Byte = 1
    const val MSG_SERVER_HELLO: Byte = 2
    // A throwaway pre-handshake junk decoy (AmneziaWG-style Jc on UDP): carries no real
    // data; the server drops it cheaply before its rate limiter. The client may emit `jc`
    // of these before its ClientHello to blur the first datagrams' size/count.
    const val MSG_JUNK: Byte = 3
    // Path-MTU probe (client->server): a single-fragment datagram padded so the whole
    // outer datagram is exactly the size being tested (sent with DF, so an oversized one
    // is dropped, not IP-fragmented -> no ACK). Body: [id(2 LE)][outerSize(2 LE)] + pad.
    // The server echoes a tiny MSG_MTU_PROBE_ACK. Recognized before the reassembler.
    const val MSG_MTU_PROBE: Byte = 4
    const val MSG_MTU_PROBE_ACK: Byte = 5

    /**
     * The **AuthOK** (server->client), fragmented for the same reason as the ServerHello.
     *
     * Unlike the two handshake messages this one has no fixed size: it carries the pushed
     * route list, so a profile pushing enough routes puts it past what a fragment-dropping
     * path (mobile, CGNAT) will carry — which is exactly the network this client runs on.
     * The failure was indistinguishable from a dead server: the client retransmits AUTH, the
     * network eats the reply every time, and it times out at the AUTHENTICATION step with
     * nothing in either log to say why. (Audit 2026-08-02, §4.)
     *
     * The server fragments ONLY above [MAX_CHUNK]; at or below it the AuthOK is still the
     * single datagram it always was, byte for byte. So this changes nothing in any case that
     * works today — the only case where fragments appear is the one where the reply was
     * already being destroyed.
     *
     * The payload is the finished AEAD record, not plaintext: reassemble first, decrypt
     * after. Nothing about the session cipher, the transcript or the replay window moves.
     *
     * There is no ambiguity against a real record, in either framing: TLS framing opens
     * 0x17 0x03 0x03, and raw framing opens with a u16 payload length bounded by
     * MAX_RECORD_SIZE (0x4124), so its high byte is at most 0x41 — 0xF0 is unreachable both
     * ways. That is the same property [isFragment] already relies on to tell a fragmented
     * ClientHello from a legacy single-datagram one, which is why `fill()` can classify every
     * datagram it receives without risking a data record.
     */
    const val MSG_AUTH_OK: Byte = 6
    const val PROBE_BODY_LEN = 4     // id(2) + outerSize(2)

    fun isFragment(d: ByteArray): Boolean =
        d.size >= HDR_LEN && d[0] == MAGIC[0] && d[1] == MAGIC[1] && d[2] == MAGIC[2]

    /** True if [d] (after obfs/QUIC unwrap) is an AWG junk decoy datagram. */
    fun isJunk(d: ByteArray): Boolean = isFragment(d) && d[3] == MSG_JUNK

    /** True if [d] (after obfs/QUIC unwrap) is a fragment of the AuthOK. */
    fun isAuthOkFragment(d: ByteArray): Boolean = isFragment(d) && d[3] == MSG_AUTH_OK

    /** True if [d] (after unwrap) is a path-MTU probe. */
    fun isMtuProbe(d: ByteArray): Boolean =
        isFragment(d) && d[3] == MSG_MTU_PROBE && d.size >= HDR_LEN + PROBE_BODY_LEN

    /** True if [d] (after unwrap) is a path-MTU probe ACK. */
    fun isMtuProbeAck(d: ByteArray): Boolean =
        isFragment(d) && d[3] == MSG_MTU_PROBE_ACK && d.size >= HDR_LEN + PROBE_BODY_LEN

    /** Read (id, outerSize) from a probe or probe-ACK datagram, or null if too short. */
    fun parseMtuProbe(d: ByteArray): Pair<Int, Int>? {
        if (d.size < HDR_LEN + PROBE_BODY_LEN) return null
        val id = (d[HDR_LEN].toInt() and 0xFF) or ((d[HDR_LEN + 1].toInt() and 0xFF) shl 8)
        val size = (d[HDR_LEN + 2].toInt() and 0xFF) or ((d[HDR_LEN + 3].toInt() and 0xFF) shl 8)
        return Pair(id, size)
    }

    /** Build a probe datagram padded so the total outer datagram is [outerSize] bytes,
     *  or null if it can't hold the header+body. */
    fun mtuProbeDatagram(id: Int, outerSize: Int): ByteArray? {
        val min = HDR_LEN + PROBE_BODY_LEN
        if (outerSize < min || outerSize > 0xFFFF) return null
        val d = ByteArray(outerSize)
        d[0] = MAGIC[0]; d[1] = MAGIC[1]; d[2] = MAGIC[2]
        d[3] = MSG_MTU_PROBE; d[4] = 0; d[5] = 1
        d[HDR_LEN] = (id and 0xFF).toByte(); d[HDR_LEN + 1] = ((id shr 8) and 0xFF).toByte()
        d[HDR_LEN + 2] = (outerSize and 0xFF).toByte(); d[HDR_LEN + 3] = ((outerSize shr 8) and 0xFF).toByte()
        val pad = ByteArray(outerSize - min)
        java.security.SecureRandom().nextBytes(pad)
        System.arraycopy(pad, 0, d, min, pad.size)
        return d
    }

    /** Build the tiny ACK for a received probe (echoes its id + outerSize). */
    fun mtuProbeAckDatagram(id: Int, outerSize: Int): ByteArray {
        val d = ByteArray(HDR_LEN + PROBE_BODY_LEN)
        d[0] = MAGIC[0]; d[1] = MAGIC[1]; d[2] = MAGIC[2]
        d[3] = MSG_MTU_PROBE_ACK; d[4] = 0; d[5] = 1
        d[HDR_LEN] = (id and 0xFF).toByte(); d[HDR_LEN + 1] = ((id shr 8) and 0xFF).toByte()
        d[HDR_LEN + 2] = (outerSize and 0xFF).toByte(); d[HDR_LEN + 3] = ((outerSize shr 8) and 0xFF).toByte()
        return d
    }

    /** Build ONE junk decoy datagram: a single-fragment [MSG_JUNK] message with [len]
     *  random body bytes. Same on-wire envelope as a real fragment, so it rides the
     *  identical obfs-XOR / QUIC mask and the peer's [isJunk] recognizes it after unwrap. */
    fun junkDatagram(len: Int): ByteArray {
        val body = ByteArray(len)
        java.security.SecureRandom().nextBytes(body)
        val d = ByteArray(HDR_LEN + len)
        d[0] = MAGIC[0]; d[1] = MAGIC[1]; d[2] = MAGIC[2]
        d[3] = MSG_JUNK; d[4] = 0; d[5] = 1
        System.arraycopy(body, 0, d, HDR_LEN, len)
        return d
    }

    /** Split a handshake message into fragment datagrams (always >= 1). */
    fun fragment(msgId: Byte, msg: ByteArray): List<ByteArray> {
        val count = maxOf(1, (msg.size + MAX_CHUNK - 1) / MAX_CHUNK)
        // The receiver rejects count > MAX_FRAGS and the on-wire idx/count are single bytes,
        // so an oversize message would pack "successfully" here and then fail at the peer as a
        // mysterious handshake hang (or, past 255 fragments, silently misassemble). Fail loudly
        // at the source instead — parity with the Rust sender.
        require(count <= MAX_FRAGS) {
            "handshake message too large to fragment ($count > $MAX_FRAGS fragments)"
        }
        return (0 until count).map { i ->
            val start = i * MAX_CHUNK
            val len = minOf(MAX_CHUNK, msg.size - start)
            val f = ByteArray(HDR_LEN + len)
            f[0] = MAGIC[0]; f[1] = MAGIC[1]; f[2] = MAGIC[2]
            f[3] = msgId; f[4] = i.toByte(); f[5] = count.toByte()
            System.arraycopy(msg, start, f, HDR_LEN, len)
            f
        }
    }

    /** Reassembles the fragments of ONE message. Tolerates out-of-order arrival and
     *  duplicates; throws on a malformed/inconsistent fragment. */
    class Reassembler {
        private var msgId: Byte = 0
        private var count = 0
        private var have = 0
        private var parts: Array<ByteArray?> = arrayOf()

        /** Feed one fragment datagram. Returns the full message once every fragment has
         *  arrived, else null. */
        fun push(d: ByteArray): ByteArray? {
            require(isFragment(d)) { "not a fragment" }
            val mId = d[3]
            val idx = d[4].toInt() and 0xFF
            val cnt = d[5].toInt() and 0xFF
            require(cnt in 1..MAX_FRAGS) { "bad fragment count" }
            require(idx < cnt) { "fragment index out of range" }
            // Cap the per-fragment chunk (parity with the Rust reassembler), bounding a
            // reassembly buffer at MAX_FRAGS*MAX_CHUNK_ACCEPT instead of MAX_FRAGS*65535.
            // Deliberately the ACCEPT bound, not the send budget: a peer built before the
            // #14 fix emits 1200-byte chunks, and bounding by our smaller MAX_CHUNK would
            // reject every one of its handshakes.
            require(d.size - HDR_LEN <= MAX_CHUNK_ACCEPT) { "fragment chunk too large" }
            if (count == 0) {
                msgId = mId; count = cnt; parts = arrayOfNulls(cnt); have = 0
            } else require(mId == msgId && cnt == count) { "inconsistent fragment" }
            if (parts[idx] == null) { parts[idx] = d.copyOfRange(HDR_LEN, d.size); have++ }
            if (have != count) return null
            val total = parts.sumOf { it!!.size }
            val out = ByteArray(total)
            var o = 0
            for (p in parts) { System.arraycopy(p!!, 0, out, o, p.size); o += p.size }
            return out
        }
    }
}
