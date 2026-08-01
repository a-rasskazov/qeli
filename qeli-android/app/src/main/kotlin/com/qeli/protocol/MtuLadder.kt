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
    /**
     * Stop refining once the bracket is this narrow — chasing the last few dozen bytes is not
     * worth a round trip, and the threshold also bounds the loop for a wide gap. Same value in
     * Rust, C# and Swift.
     */
    const val REFINE_STEP = 256

    /** Hard cap on refinement probes, so a pathological bracket cannot stretch the handshake. */
    const val REFINE_MAX_PROBES = 5

    /**
     * Next size to try between a rung known to WORK ([lo]) and one known to FAIL ([hi]), or
     * `null` when the bracket is narrow enough to stop.
     *
     * The coarse ladder certifies the best rung that FITS, not the path's maximum: with rungs
     * at 9000 and 6000 an 8999-byte path was pinned to 6000 and threw away a third of every
     * frame. A ladder can only ever land on its own numbers, so adding rungs moves the loss
     * around instead of removing it — the bracket has to be searched.
     * (Audit 2026-08-01, §8.)
     */
    fun refineStep(lo: Int, hi: Int): Int? = if (hi - lo <= REFINE_STEP) null else lo + (hi - lo) / 2

    fun rungs(ceiling: Int, outerOverhead: Int): List<Int> {
        val floor = (PATH_FLOOR - outerOverhead).coerceIn(576, maxOf(ceiling, 576))
        // The jumbo rungs (12000..1500) exist because the ceiling stopped being an Ethernet
        // number. While it was 1500 the next rung down was 1360 and the gap was 140 bytes; once
        // the ceiling became 16638 the same ladder went straight from 16638 to 1360, so a path
        // that carries 9000 — an ordinary jumbo LAN, which is exactly who configures a large
        // MTU — was certified at 1360 and lost ~85% of its frame. These cost nothing on a
        // normal path: they are all above a 1500 ceiling and the filter drops them.
        //
        // The set is a COMPROMISE, not an exact answer: probing fixed rungs certifies the
        // best rung that FITS, not the path's real maximum, so a 7000-byte path lands on 6000.
        // Closing that needs a binary search between the highest failing rung and the best
        // passing one — worth doing, and deliberately not smuggled in here, since it changes
        // the probe's control flow in all four ports.
        // (Audit 2026-08-01, §8.)
        return listOf(ceiling, 12000, 9000, 6000, 4000, 2500, 2000, 1500, 1360, 1320, 1280, 1200, floor)
            .filter { it in floor..ceiling }
            .distinct()
            .sortedDescending()
    }
}
