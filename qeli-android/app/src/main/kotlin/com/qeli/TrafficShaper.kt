package com.qeli

import java.security.SecureRandom
import kotlin.math.ln
import kotlin.math.max

/**
 * Idle cover-traffic scheduler — the Kotlin mirror of the Rust `protocol::shaper`
 * (DPI-AUDIT 6.1/6.2). When enabled, an idle tunnel emits cover packets at gaps
 * sampled from an exponential (Poisson-process) distribution rather than a fixed
 * heartbeat, with a browsing-ish size distribution, capped by a byte budget.
 * Cover packets are empty-payload encrypted records the peer drops, so this is
 * not a wire-format change. Sampling is timing/size only (not secret).
 */
class TrafficShaper(
    enabledIn: Boolean,
    private val gapMeanMs: Long,
    private val gapMinMs: Long,
    gapMaxMs: Long,
    private val budgetBytesPerSec: Int,
    private val minSize: Int,
    maxSize: Int,
    stealthIn: Boolean = false,
    stealthRateMbps: Int = 2,
) {
    val enabled: Boolean = enabledIn && budgetBytesPerSec > 0

    /** Stealth: rate-cap the data plane + cover under load. Implies [enabled].
     * TCP-only (the caller gates UDP off, mirroring the Rust core). */
    val stealth: Boolean = enabled && stealthIn

    /**
     * Cover-traffic sampler. MUST be a CSPRNG. (Audit 2026-07-27, E6)
     *
     * This used to be `kotlin.random.Random.Default` — an XorWow PRNG whose internal state
     * is reconstructible from a handful of outputs. Cover gaps and sizes ARE outputs: an
     * observer who watches enough of them recovers the state, predicts every following cover
     * packet, and subtracts the cover from the flow — which leaves exactly the real traffic
     * pattern the shaping exists to hide, so the feature actively cost battery for nothing.
     * Seeding a fast PRNG (the C# fix) removes only the "guess it from process state" half;
     * the sequence stays predictable once recovered. Rust uses `rand::rng()` (a ChaCha
     * CSPRNG) for the same reason, so match that: SecureRandom is forward- and
     * backward-secure, and at a few samples per second the cost is irrelevant.
     */
    private val rng: SecureRandom = SecureRandom()

    private val gapMax: Long = max(gapMinMs, gapMaxMs)
    private val sizeMax: Int = max(minSize, maxSize)
    private val stealthRateBps: Double = max(1, stealthRateMbps) * 1_000_000.0
    private var tokens: Double = budgetBytesPerSec.toDouble()
    private var lastRefillNanos: Long = System.nanoTime()
    // Separate token bucket (bits) for the stealth data-plane rate cap.
    private var rateTokens: Double = 0.0
    private var rateLastNanos: Long = System.nanoTime()

    /** Stealth data-plane pacing: account [bytes] against the rate cap and return how
     * long (ms) to sleep before the next send (0 if under budget or stealth is off).
     * Carries a deficit so bursts average to the cap. */
    fun stealthPaceMs(bytes: Int): Long {
        if (!stealth) return 0
        val now = System.nanoTime()
        val elapsed = (now - rateLastNanos) / 1_000_000_000.0
        rateLastNanos = now
        rateTokens = minOf(rateTokens + elapsed * stealthRateBps, stealthRateBps)
        rateTokens -= bytes * 8.0
        return if (rateTokens >= 0) 0 else minOf(1000.0, -rateTokens / stealthRateBps * 1000.0).toLong()
    }

    /** Next inter-cover gap (ms): exponential (inverse-CDF), clamped to [min,max]. */
    fun nextGapMs(): Long {
        val u = rng.nextDouble()
        val sampled = -max(1L, gapMeanMs).toDouble() * ln(max(1e-12, 1.0 - u))
        return sampled.toLong().coerceIn(gapMinMs, gapMax)
    }

    /** Sample a cover packet size in [minSize, maxSize]. */
    // nextInt(origin, bound) is Java 17 / API 36 on java.util.Random, so build the range
    // from the single-argument form to stay on minSdk 28.
    fun nextSize(): Int =
        if (minSize >= sizeMax) minSize else minSize + rng.nextInt(sizeMax - minSize + 1)

    /** Token-bucket check+spend; true (and deducts) if the budget allows [bytes]. */
    fun trySpend(bytes: Int): Boolean {
        if (budgetBytesPerSec <= 0) return false
        val now = System.nanoTime()
        val elapsed = (now - lastRefillNanos) / 1_000_000_000.0
        lastRefillNanos = now
        tokens = minOf(tokens + elapsed * budgetBytesPerSec, budgetBytesPerSec.toDouble())
        return if (tokens >= bytes) { tokens -= bytes; true } else false
    }
}
