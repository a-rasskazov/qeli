package com.qeli.protocol

/**
 * The path-MTU probe ladder. Port of the Rust client's `mtu_probe_ladder`.
 *
 * Lives here, next to the other wire primitives, rather than inside `QeliService`: it is pure
 * arithmetic with no Android dependency, so a JVM unit test can reach it (a test cannot resolve
 * the `VpnService` subclass).
 */
object MtuLadder {
    /** IPv6 minimum PATH MTU (RFC 8200 §5) — the narrowest path we must serve. */
    const val PATH_FLOOR = 1280

    /**
     * Rungs in TUNNEL (inner) MTU units, highest first.
     *
     * [outerOverhead] is everything a probe for tunnel-MTU `m` adds on the wire: our record
     * overhead, the obfs seal, the QUIC header and the UDP + IP headers. The floor is the
     * largest tunnel MTU whose datagram still fits [PATH_FLOOR] — which is the whole point:
     * rungs are INNER MTUs while 1280 is an OUTER path MTU, and using it directly as the lowest
     * rung meant asking a 1280-byte path for 1280 + overhead bytes. Every rung then failed on
     * exactly the narrow paths probing exists for, the probe reported nothing, and the caller
     * fell back to the pushed MTU with fragmentation switched back on.
     * (Audit 2026-07-29, #12.)
     */
    fun rungs(ceiling: Int, outerOverhead: Int): List<Int> {
        val floor = (PATH_FLOOR - outerOverhead).coerceIn(576, maxOf(ceiling, 576))
        return listOf(ceiling, 1360, 1320, 1280, 1200, floor)
            .filter { it in floor..ceiling }
            .distinct()
            .sortedDescending()
    }
}
