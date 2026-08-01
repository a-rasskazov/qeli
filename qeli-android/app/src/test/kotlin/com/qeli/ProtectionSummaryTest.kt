package com.qeli

import com.qeli.model.ProtectionScope
import com.qeli.model.ProtectionSummary
import com.qeli.model.ProtectionWarning
import com.qeli.model.VpnConfig
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The protection card makes security claims, so these tests exist to keep it from
 * overstating. Every case here is a way the tunnel carries LESS than everything; each must
 * flip [ProtectionSummary.carriesEverything] to false, because that flag is the only thing
 * allowed to render "all traffic is protected".
 */
class ProtectionSummaryTest {

    private fun cfg(
        mode: String = "fake-tls",
        key: String? = "aa".repeat(32),
        gateway: Boolean = true,
        lan: Boolean = false,
        ipv6: Boolean = false,
        exclude: List<String> = emptyList(),
        dns: List<String> = emptyList(),
        appsMode: String = "all",
        apps: List<String> = emptyList(),
    ) = VpnConfig(
        serverAddress = "vpn.example.com",
        port = 443,
        username = "alice",
        password = "s3cret",
        wireMode = mode,
        serverPublicKeyHex = key,
        addDefaultGateway = gateway,
        routingMode = if (gateway) "full-tunnel" else "split-tunnel",
        allowLan = lan,
        allowIpv6Leak = ipv6,
        excludeRoutes = exclude,
        dnsServers = dns,
        appsMode = appsMode,
        apps = apps,
    )

    @Test
    fun `a plain full tunnel with a pinned key carries everything`() {
        val s = ProtectionSummary.of(cfg())
        assertTrue(s.carriesEverything)
        assertEquals(ProtectionScope.ALL, s.scope)
        assertTrue(s.warnings.isEmpty())
    }

    @Test
    fun `LAN bypass stops it claiming everything`() {
        val s = ProtectionSummary.of(cfg(lan = true))
        assertFalse(s.carriesEverything)
        assertTrue(s.warnings.contains(ProtectionWarning.LAN_OUTSIDE))
    }

    @Test
    fun `IPv6 left outside stops it claiming everything`() {
        val s = ProtectionSummary.of(cfg(ipv6 = true))
        assertFalse(s.carriesEverything)
        assertTrue(s.warnings.contains(ProtectionWarning.IPV6_OUTSIDE))
    }

    @Test
    fun `excluded routes stop it claiming everything`() {
        val s = ProtectionSummary.of(cfg(exclude = listOf("192.168.0.0/16", "10.0.0.0/8")))
        assertFalse(s.carriesEverything)
        assertEquals(2, s.excludedRouteCount)
        assertTrue(s.warnings.contains(ProtectionWarning.EXCLUDED_ROUTES))
    }

    @Test
    fun `split tunnel is reported as routes, not as everything`() {
        val s = ProtectionSummary.of(cfg(gateway = false))
        assertFalse(s.carriesEverything)
        assertEquals(ProtectionScope.SPLIT_ROUTES, s.scope)
    }

    @Test
    fun `per-app modes are reported with their count`() {
        val only = ProtectionSummary.of(cfg(appsMode = "include", apps = listOf("a", "b")))
        assertEquals(ProtectionScope.ONLY_SELECTED, only.scope)
        assertEquals(2, only.appCount)
        assertFalse(only.carriesEverything)

        val except = ProtectionSummary.of(cfg(appsMode = "exclude", apps = listOf("a")))
        assertEquals(ProtectionScope.ALL_EXCEPT, except.scope)
        assertFalse(except.carriesEverything)
    }

    /**
     * Pinning decides WHO the client talks to, not HOW MUCH it carries — so it warns
     * without contradicting a truthful "all traffic" headline.
     */
    @Test
    fun `a missing pinned key warns but does not narrow the scope`() {
        val s = ProtectionSummary.of(cfg(key = null))
        assertTrue(s.carriesEverything)
        assertFalse(s.keyPinned)
        assertTrue(s.warnings.contains(ProtectionWarning.NO_PINNED_KEY))
    }

    /**
     * `plain` is the only mode without the hybrid handshake; obfs and reality-tls are
     * transport wrappers around the SAME PQ ClientHello, so claiming post-quantum for them
     * is correct — and claiming it for `plain` would not be.
     */
    @Test
    fun `post-quantum is claimed for every mode except plain`() {
        for (mode in listOf("fake-tls", "obfs", "reality-tls")) {
            assertTrue("$mode must count as post-quantum", ProtectionSummary.of(cfg(mode = mode)).postQuantum)
        }
        assertFalse(ProtectionSummary.of(cfg(mode = "plain")).postQuantum)
    }

    @Test
    fun `DNS is only claimed to be tunnelled when the config guarantees it`() {
        assertTrue(ProtectionSummary.of(cfg()).dnsThroughTunnel)
        assertTrue(ProtectionSummary.of(cfg(gateway = false, dns = listOf("1.1.1.1"))).dnsThroughTunnel)
        assertFalse(ProtectionSummary.of(cfg(gateway = false)).dnsThroughTunnel)
    }
}
