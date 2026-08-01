package com.qeli

import com.qeli.model.VpnConfig
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

/**
 * Range checks on IMPORTED numeric config values. (Audit 2026-07-27, C6)
 *
 * The server-PUSHED mtu was already clamped at the handshake (QeliService.parseOk), but the
 * locally imported one was not: a hand-written `mtu = 40`, or a scanned
 * `qeli://…?mtu=99999`, went straight through to VpnService.Builder.setMtu, where establish()
 * fails and the retry loop reconnects forever behind an opaque error. Padding was the same
 * bug one layer down — an oversized `padding_max` makes every data record exceed
 * PacketCodec.MAX_RECORD_SIZE, so the peer drops all of them.
 *
 * The two entry points behave DIFFERENTLY on purpose, mirroring the Rust client
 * (qeli/src/config/client.rs) and the C# port: a config FILE is a thing the user wrote, so a
 * bad value is reported; a `qeli://` LINK is scanned or pasted and its import is infallible,
 * so a bad value degrades to auto. Getting these the same way round on every client is the
 * point — the divergence is what the conformance work keeps finding.
 */
class ConfigImportRangesTest {

    private fun ini(vararg extra: String) = buildString {
        append("[qeli]\n")
        append("server = vpn.example.com:443\n")
        append("user = alice\n")
        append("pass = secret\n")
        for (line in extra) append(line).append('\n')
    }

    private fun link(query: String) = "qeli://alice:secret@vpn.example.com:443?proto=tcp&$query"

    /**
     * `front` and `routing_mode` are compared against ONE literal at the use site, so an
     * unknown value silently takes the other branch instead of erroring. (Audit 2026-07-31, §3.)
     */
    @Test
    fun `unknown front and routing mode are refused`() {
        assertNotNull("front = webscoket must be refused",
            runCatching { VpnConfig.fromIni(ini("front = webscoket")).validate() }.exceptionOrNull())
        for (f in listOf("websocket", "none")) {
            VpnConfig.fromIni(ini("front = $f")).validate()
        }

        // routingMode has NO ini key — the flat INI derives it from `gateway`, so only the JSON
        // and qeli:// paths can carry a bad one. Exercise it where it can actually arrive.
        fun json(mode: String) = """{"server":{"address":"1.2.3.4","port":443},
            "auth":{"username":"u","password":"p"},"routing":{"mode":"$mode"}}"""
        assertNotNull("routing mode full-tunel must be refused",
            runCatching { VpnConfig.fromJson(json("full-tunel")).validate() }.exceptionOrNull())
        for (r in listOf("split-tunnel", "full-tunnel", "all")) {
            VpnConfig.fromJson(json(r)).validate()
        }
    }

    /**
     * A boolean nobody could parse must not read as `false`.
     *
     * Every unknown value used to be falsey, so `kill_switch = ture` silently disabled the kill
     * switch and `bind_static = ture` silently dropped the static-key binding — a security
     * downgrade with no message anywhere, and unrecoverable after parse because the original
     * string is gone. Parsing still succeeds (the editor must be able to open a bad profile to
     * fix it); validate() is what refuses. (Audit 2026-07-31.)
     */
    @Test
    fun `a typo in a boolean is refused, not read as false`() {
        for (key in listOf("gateway", "bind_static", "reconnect", "padding", "heartbeat", "quic")) {
            val cfg = VpnConfig.fromIni(ini("$key = ture"))
            assertTrue("$key: the typo must be recorded", cfg.unparsedBooleanKeys.contains(key))
            val e = runCatching { cfg.validate() }.exceptionOrNull()
            assertNotNull("$key: validate() must refuse the config", e)
            assertTrue("the message must name the key: ${e?.message}",
                e!!.message!!.contains(key))
        }

        // A typo must NOT be resolved to the falsey reading it used to get.
        assertTrue("gateway = ture must not silently become split-tunnel",
            VpnConfig.fromIni(ini("gateway = ture")).isFullTunnel)
        assertTrue("bind_static = ture must not silently disable key binding",
            VpnConfig.fromIni(ini("bind_static = ture")).bindStaticToSession)

        // Every spelling the Rust client accepts must still work, both ways, and leave the
        // config valid.
        for (yes in listOf("true", "1", "yes", "on", "TRUE", "On")) {
            val c = VpnConfig.fromIni(ini("quic = $yes"))
            assertTrue("$yes must be true", c.quicEnabled)
            assertTrue(c.unparsedBooleanKeys.isEmpty())
        }
        for (no in listOf("false", "0", "no", "off", "FALSE", "Off")) {
            val c = VpnConfig.fromIni(ini("quic = $no"))
            assertFalse("$no must be false", c.quicEnabled)
            assertTrue(c.unparsedBooleanKeys.isEmpty())
        }
    }

    @Test
    fun `an INI file with an out-of-range mtu is rejected`() {
        for (bad in listOf("99999", "40", "-1", "575", "16639")) {
            try {
                VpnConfig.fromIni(ini("mtu = $bad"))
                fail("mtu = $bad must be rejected, not imported")
            } catch (e: IllegalArgumentException) {
                assertEquals(true, e.message?.contains("mtu"))
            }
        }
    }

    @Test
    fun `an INI file with a valid mtu keeps it, and 0 stays auto`() {
        assertEquals(1380, VpnConfig.fromIni(ini("mtu = 1380")).mtu)
        assertEquals(576, VpnConfig.fromIni(ini("mtu = 576")).mtu)
        assertEquals(9000, VpnConfig.fromIni(ini("mtu = 9000")).mtu)
        // The real ceiling, derived in Rust from the record format. Pinned so this port cannot
        // silently keep an older, lower bound than the server accepts. (Audit 2026-08-01, §1.)
        assertEquals(16638, VpnConfig.MTU_MAX)
        assertEquals(16638, VpnConfig.fromIni(ini("mtu = 16638")).mtu)
        // 9001 used to be refused; it is inside the range now. Kept as a case so the old
        // ceiling cannot creep back in unnoticed.
        assertEquals(9001, VpnConfig.fromIni(ini("mtu = 9001")).mtu)
        assertEquals(0, VpnConfig.fromIni(ini("mtu = 0")).mtu)
        assertEquals(0, VpnConfig.fromIni(ini()).mtu)   // absent = auto
    }

    @Test
    fun `a JSON config with an out-of-range mtu is rejected`() {
        try {
            VpnConfig.fromJson("""{"server":{"address":"h","port":443},"tun":{"mtu":99999}}""")
            fail("JSON mtu 99999 must be rejected")
        } catch (e: IllegalArgumentException) {
            assertEquals(true, e.message?.contains("mtu"))
        }
        assertEquals(1400, VpnConfig.fromJson(
            """{"server":{"address":"h","port":443},"tun":{"mtu":1400}}"""
        ).mtu)
    }

    /** A link must stay importable: the mtu falls back to auto, everything else survives. */
    @Test
    fun `a qeli link with an out-of-range mtu falls back to auto`() {
        val cfg = VpnConfig.fromQeliUri(link("mode=fake-tls&mtu=99999"))
        assertEquals(0, cfg.mtu)
        assertEquals("vpn.example.com", cfg.serverAddress)
        assertEquals("alice", cfg.username)
        assertEquals(0, VpnConfig.fromQeliUri(link("mode=fake-tls&mtu=-5")).mtu)
        // In range → carried through untouched.
        assertEquals(1380, VpnConfig.fromQeliUri(link("mode=fake-tls&mtu=1380")).mtu)
    }

    /**
     * Padding is CLAMPED rather than rejected: unlike mtu these are pure obfuscation knobs,
     * so narrowing them costs the user nothing while an oversized max breaks every packet.
     */
    @Test
    fun `imported padding bounds are clamped to the wire ceiling`() {
        val c = VpnConfig.fromIni(ini("padding_min = -5", "padding_max = 60000"))
        assertEquals(0, c.paddingMin)
        assertEquals(1400, c.paddingMax)
        // min above max must not survive as an inverted range (nextInt would throw).
        val inverted = VpnConfig.fromIni(ini("padding_min = 900", "padding_max = 100"))
        assertEquals(900, inverted.paddingMin)
        assertEquals(900, inverted.paddingMax)
        val j = VpnConfig.fromJson(
            """{"server":{"address":"h","port":443},
                "obfuscation":{"padding":{"min_bytes":-1,"max_bytes":99999}}}"""
        )
        assertEquals(0, j.paddingMin)
        assertEquals(1400, j.paddingMax)
    }

    /** A clamped/accepted profile must still round-trip through the emit-side validator. */
    @Test
    fun `a clamped profile still passes validate on re-save`() {
        VpnConfig.fromIni(ini("padding_min = -5", "padding_max = 60000", "mtu = 1380")).validate()
    }

    /**
     * A number that is present but unreadable must be refused, not replaced by the default.
     *
     * `server`'s port has always thrown here, which is why the worst case never bit this port —
     * but every other numeric key fell back in silence, so `padding_min = abc` quietly became
     * 0. The C# port had it worse (`server = host:notnum` became `host:443`, a different
     * server), and all four must now agree. (Audit 2026-08-01, §P2.)
     */
    @Test
    fun `an unreadable number is refused, not replaced by the default`() {
        val cfg = VpnConfig.fromIni(ini("padding_min = abc"))
        assertTrue("the bad number must be recorded", cfg.unparsedNumericKeys.contains("padding_min"))
        val e = runCatching { cfg.validate() }.exceptionOrNull()
        assertNotNull("validate() must refuse it", e)
        assertTrue("the message must name the key: ${e?.message}",
            e!!.message!!.contains("padding_min"))

        // An ABSENT key keeps its default silently — that is what a default is for.
        assertTrue(VpnConfig.fromIni(ini()).unparsedNumericKeys.isEmpty())
        // ...and a readable one records nothing, so the check above cannot pass vacuously.
        val good = VpnConfig.fromIni(ini("padding_min = 10", "padding_max = 200"))
        assertTrue(good.unparsedNumericKeys.isEmpty())
        good.validate()

        // The port was already strict and must stay that way — an outright throw, not a record.
        assertNotNull("a non-numeric port must be rejected outright",
            runCatching { VpnConfig.fromIni("[qeli]\nserver = 1.2.3.4:notnum\n") }.exceptionOrNull())
    }

    /**
     * A key written twice must be refused, not silently resolved.
     *
     * The ports disagreed on which line wins: this parser folds entries into a map and keeps
     * the LAST, while the Rust client (config/format.rs `Section::get`) takes the FIRST. Two
     * `server` lines therefore sent the Rust client to one host and every GUI client to
     * another, out of one file, with nothing reported anywhere. Parsing still succeeds — the
     * editor must be able to open the file to fix it; validate() is what refuses.
     * (Audit 2026-08-01, §7.)
     */
    @Test
    fun `a key written twice is refused, not silently resolved`() {
        val cfg = VpnConfig.fromIni(ini("server = other.example.com:8443"))
        assertTrue("the duplicate must be recorded",
            cfg.duplicateKeys.contains("qeli.server"))
        val e = runCatching { cfg.validate() }.exceptionOrNull()
        assertNotNull("validate() must refuse an ambiguous config", e)
        assertTrue("the message must name the key: ${e?.message}",
            e!!.message!!.contains("qeli.server"))

        // Duplicates are found per SECTION — the same key name in two different sections is
        // not a duplicate, and a clean file must stay clean.
        val clean = VpnConfig.fromIni(ini("mtu = 1400") + "[logging]\nlevel = debug\n")
        assertTrue("a clean config must record nothing: ${clean.duplicateKeys}",
            clean.duplicateKeys.isEmpty())
        clean.validate()

        // Recorded ONCE however many times the key repeats, and the last value still wins, so
        // a file that already had a duplicate parses as it always did.
        val thrice = VpnConfig.fromIni(ini("mtu = 1400", "mtu = 1300", "mtu = 1200"))
        assertEquals(listOf("qeli.mtu"), thrice.duplicateKeys)
        assertEquals(1200, thrice.mtu)
    }
}

/**
 * A canonical JSON profile must survive import intact. (Audit 2026-07-29, #6)
 *
 * `fromJson` stopped filling fields at heartbeat, so shaping, an explicit
 * `tun.mtu_probe = false` and the whole `[logging]` block were dropped: the imported profile
 * silently came back with defaults, and re-exporting it wrote that loss back to disk. The
 * values below are all non-default on purpose — with the old importer every assertion here
 * fails, which is the point of the test.
 */
class ConfigJsonImportCompletenessTest {
    private val json = """
        {
          "server": {"address": "example.com", "port": 8443, "protocol": "tcp"},
          "auth": {"username": "u", "password": "p"},
          "tun": {"mtu": 1280, "mtu_probe": false},
          "logging": {"level": "debug", "time_format": "rfc3339"},
          "obfuscation": {
            "mode": "fake-tls",
            "traffic_shaping": {
              "enabled": true, "idle_gap_mean_ms": 800, "idle_gap_min_ms": 50,
              "idle_gap_max_ms": 7000, "budget_bytes_per_sec": 4096,
              "min_size": 128, "max_size": 900, "stealth": true, "stealth_rate_mbps": 5
            }
          }
        }
    """.trimIndent()

    @Test
    fun jsonImportKeepsShapingMtuProbeAndLogging() {
        val c = VpnConfig.fromJson(json)
        assertEquals(false, c.mtuProbe)
        assertEquals(true, c.shapingEnabled)
        assertEquals(800L, c.shapingGapMeanMs)
        assertEquals(50L, c.shapingGapMinMs)
        assertEquals(7000L, c.shapingGapMaxMs)
        assertEquals(4096, c.shapingBudgetBytesPerSec)
        assertEquals(128, c.shapingMinSize)
        assertEquals(900, c.shapingMaxSize)
        assertEquals(true, c.shapingStealth)
        assertEquals(5, c.shapingStealthRateMbps)
        assertEquals("debug", c.loggingLevel)
        assertEquals("rfc3339", c.loggingTimeFormat)
    }

    /** And the values must still be there after a save/load round-trip through INI. */
    @Test
    fun theValuesSurviveAnIniRoundTrip() {
        val back = VpnConfig.fromIni(VpnConfig.fromJson(json).toIni())
        assertEquals(false, back.mtuProbe)
        assertEquals(true, back.shapingEnabled)
        assertEquals(800L, back.shapingGapMeanMs)
        assertEquals(900, back.shapingMaxSize)
        assertEquals("debug", back.loggingLevel)
    }
}
