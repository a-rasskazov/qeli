package com.qeli.model

import org.json.JSONObject
import java.io.Serializable

/**
 * Full qeli client configuration. Mirrors the relevant fields of the Rust
 * ClientConfig (qeli/src/config/client.rs). Built either from the simple
 * UI fields or by importing a JSON config via [fromJson].
 */
data class VpnConfig(
    // ── server ──
    val serverAddress: String,
    val port: Int,
    val protocol: String = "tcp",              // "tcp" | "udp"
    val connectionTimeoutSecs: Long = 30,
    // ── reconnect ──
    val reconnectEnabled: Boolean = true,
    val reconnectMaxRetries: Int = -1,
    val reconnectBaseDelaySecs: Long = 1,
    val reconnectMaxDelaySecs: Long = 60,
    // ── auth ──
    val username: String,
    val password: String,
    val serverPublicKeyHex: String? = null,    // pinned static key (hex), null = TOFU
    // H-1: bind data keys to the server static identity (must match server's
    // auth.bind_static_to_session + requires a pinned key). Default TRUE
    // (secure-by-default since 0.7.1); set false for a legacy 0.7.0 / TOFU server.
    val bindStaticToSession: Boolean = true,
    // ── tun ──
    // 0 = auto: adopt the MTU the server pushes at auth (falls back to 1400 if the
    // server is too old to push one). A value > 0 is an explicit override.
    val mtu: Int = 0,
    // Active UDP path-MTU probing when mtu == 0 (default on; kill switch = false). No
    // effect on TCP transports (the kernel does PMTUD) or when mtu > 0 (explicit).
    val mtuProbe: Boolean = true,
    // ── routing ──
    // Default to full-tunnel: a VPN should carry ALL traffic so nothing leaks
    // outside the encrypted path. Split-tunnel stays available via an imported
    // JSON config (routing.mode = "split-tunnel").
    val routingMode: String = "full-tunnel",   // "full-tunnel" | "split-tunnel"
    val addDefaultGateway: Boolean = true,
    val includeRoutes: List<String> = emptyList(),
    val excludeRoutes: List<String> = emptyList(),
    // Route private/local networks (RFC1918) through the VPN. When true, the
    // client adds the private ranges AND applies any networks the server pushed,
    // so LAN resources behind the server work through the tunnel. When false
    // (default), local networks are not tunnelled and pushed networks are ignored.
    val routeLocalNetworks: Boolean = false,
    // Full-tunnel captures IPv6 into the (IPv4-only) tunnel to close the classic dual-stack
    // leak; set true to OPT OUT and keep native IPv6 (it bypasses the tunnel). Default off;
    // mirrors the Rust/desktop `allow_ipv6_leak`.
    val allowIpv6Leak: Boolean = false,
    // Allow direct access to the local/LAN network while on a full tunnel: carve the
    // RFC1918 private ranges OUT of the tunnel so Wi-Fi/LAN devices (printers, NAS,
    // Chromecast, the router UI) stay reachable without disconnecting the VPN. Off by
    // default (a full tunnel normally carries everything). Distinct from — and the
    // inverse of — route_local_networks. Android extra; the desktop/CLI client ignores it.
    val allowLan: Boolean = false,
    // ── dns ──
    // Public resolvers reachable through the tunnel (the server NATs them out).
    // Without this, full-tunnel would point DNS at the server's tun IP, which
    // only resolves if the server runs a DNS proxy.
    // Empty by default so a config without DNS round-trips clean and the server-pushed
    // resolver is honoured; the 1.1.1.1/8.8.8.8 fallback moved to connect time (QeliService).
    val dnsServers: List<String> = emptyList(),
    // ── obfuscation ──
    val wireMode: String = "fake-tls",         // "fake-tls" | "obfs"
    val obfsKey: String = "",
    // obfs anti-FET fronting: "websocket" (default) wraps the nonce exchange in a
    // WebSocket Upgrade handshake; "none" is the legacy raw nonce. Must match the
    // server. Mirrors ClientObfuscationConfig::fronting in the Rust client.
    val obfsFronting: String = "websocket",
    // F2: AmneziaWG-style pre-handshake junk (obfs mode only). OFF by default so
    // the wire is byte-identical to today. When awgEnabled && awgJc>0, the sender
    // emits awgJc junk records (each uniform length in [awgJmin,awgJmax]) right
    // after the front/TCP handshake and before the nonce exchange; the peer reads
    // and discards awgJc records. Both ends MUST share awgJc; jmin/jmax are
    // sender-only. Mirrors obf.awg.* in the Rust/C# clients.
    val awgEnabled: Boolean = false,
    val awgJc: Int = 0,      // junk record count, cap 128
    val awgJmin: Int = 40,   // min junk length
    val awgJmax: Int = 300,  // max junk length (require jmin<=jmax<=1400)
    val quicEnabled: Boolean = false,
    val sni: String? = null,
    // REALITY short_id (hex) — pairs with serverPublicKeyHex to seal the auth
    // token into the realtls ClientHello (wireMode = "reality-tls").
    val realityShortId: String? = null,
    // padding
    val paddingEnabled: Boolean = true,
    val paddingMin: Int = 0,
    val paddingMax: Int = 255,
    // heartbeat
    val heartbeatEnabled: Boolean = true,
    val heartbeatIntervalMs: Long = 15000,
    val heartbeatDataSize: Int = 16,
    val heartbeatJitterMs: Long = 2000,
    // flow shaping (idle cover traffic; DPI-AUDIT 6.1/6.2). Normally pushed from
    // the server. Defaults mirror the Rust TrafficShapingConfig.
    val shapingEnabled: Boolean = false,
    val shapingGapMeanMs: Long = 700,
    val shapingGapMinMs: Long = 40,
    val shapingGapMaxMs: Long = 6000,
    val shapingBudgetBytesPerSec: Int = 16384,
    val shapingMinSize: Int = 64,
    val shapingMaxSize: Int = 1024,
    // Stealth (Phase 2): rate-cap the data plane + cover under load. TCP-only.
    val shapingStealth: Boolean = false,
    val shapingStealthRateMbps: Int = 2,
    // ── per-app split tunnel (Android-only extra; the Rust/desktop clients ignore these) ──
    // "all" = every app uses the VPN (default). "include" = ONLY [apps] are tunnelled.
    // "exclude" = every app EXCEPT [apps]. [apps] holds Android package names.
    val appsMode: String = "all",             // "all" | "include" | "exclude"
    val apps: List<String> = emptyList(),
    // ── [logging] passthrough ──
    // Not used by the app (its own log settings live in SharedPreferences); carried so a
    // desktop/router client.conf opened and re-saved here keeps its logging section instead
    // of silently losing it. Mirrors qeli/src/config/client.rs, which parses AND re-emits it.
    val loggingLevel: String? = null,
    val loggingFile: String? = null,
    val loggingTimeFormat: String? = null,
    /**
     * Keys whose boolean value was neither true-ish nor false-ish — `gateway = ture`.
     *
     * Carried instead of being resolved at parse time because the ORIGINAL STRING IS LOST once
     * a bool is produced, so nothing downstream could ever tell a typo from a deliberate
     * `false`. That mattered: every unknown value used to read as `false`, so `kill_switch =
     * ture` silently disabled the kill switch and `bind_static = ture` silently dropped the
     * static-key binding — a security downgrade with no message anywhere.
     *
     * Parsing still SUCCEEDS (the editor must be able to open a bad profile in order to fix
     * it); [validate] is what refuses to connect. Same split as the enum checks.
     * (Audit 2026-07-31.)
     */
    val unparsedBooleanKeys: List<String> = emptyList()
) : Serializable {

    /** True when the protocol is UDP (DatagramChannel transport, QUIC masking). */
    val isUdp: Boolean get() = protocol.equals("udp", ignoreCase = true)

    /**
     * `all` counts too. The validator accepts `split-tunnel | full-tunnel | all` (the Rust
     * client's set, see `client/route.rs`), but this only compared against `full-tunnel` — so a
     * perfectly valid `routing.mode = "all"` profile validated and then ran as a SPLIT tunnel,
     * quietly sending everything outside the VPN past it. (Audit 2026-07-31, §2.)
     */
    val isFullTunnel: Boolean
        get() = addDefaultGateway ||
            routingMode.equals("full-tunnel", ignoreCase = true) ||
            routingMode.equals("all", ignoreCase = true)

    /**
     * Reject configs that cannot be represented as flat-INI, and range-check the numeric
     * fields. Mirrors the iOS `VPNConfig.validate()` so both mobile clients accept and
     * refuse exactly the same profiles.
     *
     * The control-character scan is a SECURITY guard, not cosmetics. [toIni] writes
     * `key = value` verbatim, so a password / SNI / route carrying a newline lets an
     * imported `qeli://` link forge additional INI keys — e.g. appending
     * `\nbind_static = false` turns off binding the session to the pinned server key, and
     * the forged line comes back as trusted config on the next save. Checked on emit (the
     * moment the forgery would be written) and on link import (untrusted input entering).
     *
     * Parsing stays lenient about the STRING fields for the same reason (an odd sni already
     * on disk must not lock the user out of their own profile), but NOT about the numeric
     * ranges: `mtu` and the padding bounds are checked at import too, because an
     * out-of-range value there is not a cosmetic problem — it produces a tunnel that cannot
     * establish, or records the peer rejects, with no hint of why. See [checkedMtu] /
     * [checkedPadding]. (Audit 2026-07-27, C6)
     */
    fun validate() {
        // A boolean nobody could parse is a typo, and every one of them used to read as
        // `false` — so `kill_switch = ture` disabled the kill switch and `bind_static = ture`
        // dropped the static-key binding, silently. Refuse to connect rather than run with a
        // setting the user plainly did not choose. (Audit 2026-07-31.)
        require(unparsedBooleanKeys.isEmpty()) {
            "unrecognised boolean value for ${unparsedBooleanKeys.joinToString(", ")} — " +
                "expected true/false, yes/no, on/off or 1/0"
        }
        fun scalar(name: String, v: String?) {
            val bad = v?.firstOrNull { it == '\r' || it == '\n' || it == '\u0000' } ?: return
            throw IllegalArgumentException(
                "'$name' contains a control character (0x%02X); refusing to write it".format(bad.code)
            )
        }
        scalar("server", serverAddress); scalar("proto", protocol)
        scalar("user", username); scalar("pass", password)
        scalar("key", serverPublicKeyHex); scalar("mode", wireMode)
        scalar("sni", sni); scalar("reality_sid", realityShortId)
        scalar("obfs_key", obfsKey); scalar("front", obfsFronting)
        for (v in includeRoutes) scalar("include", v)
        for (v in excludeRoutes) scalar("exclude", v)
        for (v in dnsServers) scalar("dns", v)
        for (v in apps) scalar("apps", v)
        scalar("logging.level", loggingLevel); scalar("logging.file", loggingFile)
        scalar("logging.time_format", loggingTimeFormat)

        require(serverAddress.isNotEmpty()) { "'server' has empty host" }
        require(port in 1..65535) { "'server' port out of range: $port" }
        require(protocol == "tcp" || protocol == "udp") { "'proto' must be tcp or udp, got '$protocol'" }
        require(connectionTimeoutSecs in 1..300) { "'timeout' must be 1..300, got $connectionTimeoutSecs" }
        require(wireMode in WIRE_MODES) { "'mode' must be one of $WIRE_MODES, got '$wireMode'" }
        // Same class as `mode`, and left unchecked: both are compared against ONE literal at
        // the use site, so an unknown value does not error — it silently takes the other
        // branch. `front = webscoket` drops the WebSocket framing the profile asked for and the
        // peer then disagrees about the wire; `routing_mode = full-tunel` with
        // add_default_gateway = false quietly becomes a split tunnel. (Audit 2026-07-31, §3.)
        require(obfsFronting in FRONTING_MODES) {
            "'front' must be one of $FRONTING_MODES, got '$obfsFronting'"
        }
        require(routingMode in ROUTING_MODES) {
            "'routing_mode' must be one of $ROUTING_MODES, got '$routingMode'"
        }
        // 0 = auto. Matches the Rust client, which rejects anything outside MTU_MIN..MTU_MAX.
        // Same predicate the import paths use, so emit and import can never disagree. (C6)
        require(mtuInRange(mtu)) { "'mtu' must be 0 (auto) or $MTU_MIN..$MTU_MAX, got $mtu" }
        require(paddingMin >= 0 && paddingMax >= paddingMin && paddingMax <= PADDING_CEILING) {
            "padding range invalid: $paddingMin..$paddingMax (expected 0..$PADDING_CEILING)"
        }
    }

    /**
     * Build a compact `qeli://` share link (inverse of [fromQeliUri]); mirrors the C#
     * VpnConfig.ToQeliUri and the Rust ClientLink::to_uri, so the link imports on every
     * client + the server's /api/share. [name] becomes the `#label` fragment.
     */
    fun toQeliUri(name: String? = null): String {
        validate()
        val sb = StringBuilder("qeli://")
        // Always `user:pass@`, even when the password is empty — that is what the Rust
        // ClientLink::to_uri and the iOS client emit, so the same profile now produces a
        // byte-identical link (and QR) on every platform.
        sb.append(pctEncode(username)).append(':').append(pctEncode(password))
        // Bracket an IPv6 literal so its colons aren't read as the :port separator.
        val host = if (serverAddress.contains(':') && !serverAddress.startsWith('[')) "[$serverAddress]" else serverAddress
        sb.append('@').append(host).append(':').append(port)
        val q = mutableListOf("proto=$protocol", "mode=$wireMode")
        if (!serverPublicKeyHex.isNullOrEmpty()) q.add("key=$serverPublicKeyHex")
        if (!sni.isNullOrEmpty()) q.add("sni=${pctEncode(sni!!)}")
        if (!realityShortId.isNullOrEmpty()) q.add("rsid=${pctEncode(realityShortId!!)}")
        if (obfsKey.isNotEmpty()) q.add("obfs=${pctEncode(obfsKey)}")
        if (awgEnabled) { q.add("awg=1"); q.add("jc=$awgJc"); q.add("jmin=$awgJmin"); q.add("jmax=$awgJmax") }
        if (quicEnabled) q.add("quic=1")
        if (mtu > 0) q.add("mtu=$mtu")   // 0 = auto, omit
        // `front` affects the wire: omitting it does not mean "default" to the importer,
        // it means the import silently re-defaults to websocket — a different framing, so
        // the tunnel never handshakes. Carried by every implementation. (C-12)
        if (obfsFronting != "websocket") q.add("front=${pctEncode(obfsFronting)}")
        // `bind_static` and `mtu_probe` are deliberately NOT emitted. They are local device
        // policy, not a property of the server, and the link is defined as carrying only
        // what the client cannot learn any other way. Android was the only implementation
        // that put them in: Rust, C# and Swift dropped them as unknown params, so a link
        // shared from here arrived elsewhere with bind_static silently back ON — demanding
        // a pinned key the link never carried. Emitting `bind_static=0` was also the worse
        // half of the divergence: it hands a security downgrade to anyone the QR is
        // forwarded to. Set both in the profile itself instead. Parsing them stays below,
        // as tolerance for links this app issued before 0.7.13.
        sb.append('?').append(q.joinToString("&"))
        if (!name.isNullOrBlank()) sb.append('#').append(pctEncode(name))
        return sb.toString()
    }

    // `toConfigJson` lived here — DELETED (Audit 2026-07-27, X4). It had no callers: the app
    // stores profiles as flat-INI via [toIni], and an imported qeli:// link goes through that
    // same path. It also hardcoded `routing.mode = "full-tunnel"` + `add_default_gateway =
    // true` regardless of the config it was serialising, so anyone who wired it up would have
    // silently overridden a split-tunnel profile — dead code that was wrong on the one field
    // a VPN cannot afford to get wrong.

    /**
     * Render the connection essentials to the flat-INI `[qeli]` format — the
     * SAME schema the Rust client reads (qeli/src/config/client.rs::from_ini),
     * so a profile exported here is loadable by the desktop/CLI client too.
     * `dns` and `mtu` are app extras the Rust client simply ignores.
     */
    fun toIni(label: String? = null): String = buildString {
        // Emit-time gate: refuses control characters (INI forgery) and out-of-range values.
        validate()
        // A label carrying a newline would forge INI lines just like a scalar would.
        if (!label.isNullOrBlank()) append("# ").append(label.replace(Regex("[\\r\\n\\u0000]"), " ")).append('\n')
        append("[qeli]\n")
        append("server = ").append(serverAddress).append(':').append(port).append('\n')
        append("proto = ").append(protocol).append('\n')
        append("user = ").append(username).append('\n')
        append("pass = ").append(password).append('\n')
        if (!serverPublicKeyHex.isNullOrEmpty()) append("key = ").append(serverPublicKeyHex).append('\n')
        if (!bindStaticToSession) append("bind_static = false\n")  // on by default; emit only when off
        append("mode = ").append(wireMode).append('\n')
        if (!sni.isNullOrBlank()) append("sni = ").append(sni).append('\n')
        if (!realityShortId.isNullOrEmpty()) append("reality_sid = ").append(realityShortId).append('\n')
        if (obfsKey.isNotEmpty()) append("obfs_key = ").append(obfsKey).append('\n')
        if (obfsFronting != "websocket") append("front = ").append(obfsFronting).append('\n')
        // F2: AmneziaWG junk. Emit only when enabled (default OFF → byte-identical
        // round-trip). Mirrors the Rust client's awg/jc/jmin/jmax INI keys.
        if (awgEnabled) {
            append("awg = true\n")
            append("jc = ").append(awgJc).append('\n')
            append("jmin = ").append(awgJmin).append('\n')
            append("jmax = ").append(awgJmax).append('\n')
        }
        if (quicEnabled) append("quic = true\n")  // udp+quic profiles: lost on round-trip without this
        // Routing: full-tunnel is the default; emit `gateway = false` only for an
        // explicit split-tunnel so the choice survives a save round-trip (the editor
        // re-serializes to INI). Mirrors the Rust client's `gateway` key.
        if (!isFullTunnel) append("gateway = false\n")
        if (routeLocalNetworks) append("route_local = true\n")
        if (allowIpv6Leak) append("allow_ipv6_leak = true\n")
        if (allowLan) append("allow_lan = true\n")  // LAN bypass (exclude RFC1918 from tunnel)
        if (includeRoutes.isNotEmpty()) append("include = ").append(includeRoutes.joinToString(", ")).append('\n')
        if (excludeRoutes.isNotEmpty()) append("exclude = ").append(excludeRoutes.joinToString(", ")).append('\n')
        if (dnsServers.isNotEmpty()) append("dns = ").append(dnsServers.joinToString(", ")).append('\n')
        if (mtu > 0) append("mtu = ").append(mtu).append('\n')  // 0 = auto, omit
        if (!mtuProbe) append("mtu_probe = false\n")  // default true, emit only when off
        // Per-app split tunnel (Android extra). Emit only when active so default
        // profiles stay byte-identical and the desktop/CLI client (which ignores
        // these keys) round-trips them harmlessly.
        // Emitted independently (matching iOS): coupling them dropped `apps_mode = include`
        // with an empty list, silently reverting the profile to "all apps tunnelled".
        if (appsMode != "all") append("apps_mode = ").append(appsMode).append('\n')
        if (apps.isNotEmpty()) append("apps = ").append(apps.joinToString(", ")).append('\n')
        // Reconnect / timeout tuning (Android extras; the Rust client ignores them).
        // Emitted only when diverging from the defaults.
        if (!reconnectEnabled) append("reconnect = false\n")
        if (reconnectMaxRetries != -1) append("reconnect_retries = ").append(reconnectMaxRetries).append('\n')
        if (reconnectBaseDelaySecs != 1L) append("reconnect_base_delay = ").append(reconnectBaseDelaySecs).append('\n')
        if (reconnectMaxDelaySecs != 60L) append("reconnect_max_delay = ").append(reconnectMaxDelaySecs).append('\n')
        if (connectionTimeoutSecs != 30L) append("timeout = ").append(connectionTimeoutSecs).append('\n')
        // Padding / heartbeat / shaping. Normally server-pushed, so these are local
        // OVERRIDES and stay out of the file at their defaults. The key names match the
        // iOS client exactly — it already read and wrote them, so without these an
        // iOS-exported profile silently lost its shaping/heartbeat tuning here.
        if (!paddingEnabled) append("padding = false\n")
        if (paddingMin != 0) append("padding_min = ").append(paddingMin).append('\n')
        if (paddingMax != 255) append("padding_max = ").append(paddingMax).append('\n')
        if (!heartbeatEnabled) append("heartbeat = false\n")
        if (heartbeatIntervalMs != 15000L) append("heartbeat_interval = ").append(heartbeatIntervalMs).append('\n')
        if (heartbeatDataSize != 16) append("heartbeat_size = ").append(heartbeatDataSize).append('\n')
        if (heartbeatJitterMs != 2000L) append("heartbeat_jitter = ").append(heartbeatJitterMs).append('\n')
        if (shapingEnabled) append("shaping = true\n")
        if (shapingGapMeanMs != 700L) append("shaping_gap_mean = ").append(shapingGapMeanMs).append('\n')
        if (shapingGapMinMs != 40L) append("shaping_gap_min = ").append(shapingGapMinMs).append('\n')
        if (shapingGapMaxMs != 6000L) append("shaping_gap_max = ").append(shapingGapMaxMs).append('\n')
        if (shapingBudgetBytesPerSec != 16384) append("shaping_budget = ").append(shapingBudgetBytesPerSec).append('\n')
        if (shapingMinSize != 64) append("shaping_min_size = ").append(shapingMinSize).append('\n')
        if (shapingMaxSize != 1024) append("shaping_max_size = ").append(shapingMaxSize).append('\n')
        if (shapingStealth) append("shaping_stealth = true\n")
        if (shapingStealthRateMbps != 2) append("shaping_stealth_mbps = ").append(shapingStealthRateMbps).append('\n')
        // Re-emit [logging] verbatim so a desktop/router client.conf survives a mobile save.
        if (!loggingLevel.isNullOrEmpty() || !loggingFile.isNullOrEmpty() || !loggingTimeFormat.isNullOrEmpty()) {
            append("\n[logging]\n")
            if (!loggingLevel.isNullOrEmpty()) append("level = ").append(loggingLevel).append('\n')
            if (!loggingFile.isNullOrEmpty()) append("file = ").append(loggingFile).append('\n')
            if (!loggingTimeFormat.isNullOrEmpty()) append("time_format = ").append(loggingTimeFormat).append('\n')
        }
    }

    companion object {
        private const val serialVersionUID = 2L

        /** Wire modes the client can actually dial; same set as the iOS validator. */
        private val WIRE_MODES = setOf("plain", "fake-tls", "obfs", "reality-tls")
        private val FRONTING_MODES = setOf("websocket", "none")
        private val ROUTING_MODES = setOf("split-tunnel", "full-tunnel", "all")

        /**
         * Values of `mtu_probe` that turn probing OFF. Anything else — including an
         * unrecognised word — leaves the default (on), which is what the Rust `bool_or`
         * and the iOS client do. Using the generic truthy `bool()` here would instead read
         * a typo as "off", disabling probing on a config the desktop client accepts.
         */
        private val MTU_PROBE_OFF = setOf("false", "0", "no", "off")

        // ── imported-value ranges (Audit 2026-07-27, C6) ─────────────────────────
        // The SERVER-pushed mtu was already range-checked (QeliService.parseOk clamps to
        // 576..9000), the locally imported one was not: `qeli://…?mtu=99999`, or a
        // hand-written `mtu = 40`, went straight through to VpnService.Builder.setMtu, where
        // establish() fails and the retry loop reconnects forever with an opaque error. An
        // out-of-range padding_max is the same class of bug one layer down — every data
        // record then exceeds PacketCodec.MAX_RECORD_SIZE and the peer drops it. Same ranges
        // as the Rust client (qeli/src/config/client.rs) and the C# port.
        const val MTU_MIN = 576
        const val MTU_MAX = 9000
        private const val PADDING_CEILING = 1400   // the per-packet pad_cap wire ceiling

        /** 0 (auto) or a plausible tunnel MTU. */
        fun mtuInRange(mtu: Int): Boolean = mtu == 0 || mtu in MTU_MIN..MTU_MAX

        /** Explicit TUN MTU from a config FILE (flat-INI or JSON); 0 = auto. REJECTS, like
         *  the Rust `from_ini` and the C# `CheckedMtu`: a bad value in a file the user wrote
         *  by hand is a mistake worth surfacing at import (every import path already reports
         *  the message), not something to silently rewrite behind their back. */
        private fun checkedMtu(mtu: Int): Int =
            if (mtuInRange(mtu)) mtu
            else throw IllegalArgumentException(
                "invalid mtu $mtu — expected 0 (auto) or $MTU_MIN..$MTU_MAX"
            )

        /** Same range for a `qeli://` LINK, but falling back to auto instead of throwing —
         *  mirrors the Rust link importer, which is infallible and only warns. A scanned or
         *  pasted link must still yield a usable profile; the mtu is the one thing in it the
         *  server re-pushes anyway. */
        private fun linkMtuOrAuto(mtu: Int): Int {
            if (mtuInRange(mtu)) return mtu
            warn("qeli:// link mtu $mtu is out of range (expected 0 or $MTU_MIN..$MTU_MAX) — using auto")
            return 0
        }

        /** Clamp imported padding bounds to 0..[PADDING_CEILING] and restore min <= max.
         *  Clamped rather than rejected: unlike mtu these are pure obfuscation knobs, so
         *  narrowing them costs the user nothing, while an oversized max breaks every
         *  packet. */
        private fun checkedPadding(min: Int, max: Int): Pair<Int, Int> {
            val lo = min.coerceIn(0, PADDING_CEILING)
            return lo to max.coerceIn(lo, PADDING_CEILING)
        }

        /** Warn without dragging `android.util.Log` into the JVM unit tests, where the
         *  android.jar stub throws "not mocked" and would fail the link-conformance run
         *  the moment a fixture carries an out-of-range value. */
        private fun warn(msg: String) {
            try { android.util.Log.w("VpnConfig", msg) } catch (_: Throwable) { /* off-device */ }
        }

        /**
         * Parse a profile config in EITHER format: flat-INI (starts with a
         * section header / comment) or legacy JSON (starts with `{`). The app
         * now stores INI; this keeps old JSON profiles working transparently.
         */
        fun parse(text: String): VpnConfig =
            when {
                // A raw qeli:// share link — parity with the C# VpnConfig.Parse. Callers
                // like pingActive/probe pass stored p.text (normally already INI), but a
                // qeli:// here would otherwise fall into fromIni and fail "missing [qeli]".
                text.trimStart().startsWith("qeli://") -> fromQeliUri(text.trim())
                text.trimStart().startsWith("{") -> fromJson(text)
                else -> fromIni(text)
            }

        /**
         * Parse the flat-INI `[qeli]` client config (mirrors the Rust
         * ClientConfig::from_ini). Only connection essentials live in the file;
         * everything else is defaulted and overwritten by the server at
         * handshake. `dns`/`mtu` are optional app extras.
         */
        fun fromIni(text: String): VpnConfig {
            val ini = parseIni(text)
            val q = ini["qeli"] ?: throw IllegalArgumentException("config: missing [qeli] section")
            val log = ini["logging"]
            val server = q["server"]?.takeIf { it.isNotBlank() }
                ?: throw IllegalArgumentException("[qeli] missing required key 'server' (host:port)")
            val ci = server.lastIndexOf(':')
            require(ci > 0) { "'server' must be host:port, got '$server'" }
            val host = server.substring(0, ci)
            require(host.isNotEmpty()) { "'server' has empty host" }
            val port = server.substring(ci + 1).toIntOrNull()
                ?: throw IllegalArgumentException("'server' has invalid port: '$server'")
            // Accepts the same spellings as the Rust client's `bool_or`. An unrecognised value
            // is RECORDED (see `unparsedBooleanKeys`) and falls back to the caller's default,
            // rather than silently reading as `false`.
            val badBools = mutableListOf<String>()
            fun boolAt(key: String, default: Boolean): Boolean {
                val raw = q[key]?.trim()?.lowercase() ?: return default
                return when (raw) {
                    "true", "1", "yes", "on" -> true
                    "false", "0", "no", "off" -> false
                    else -> { badBools.add(key); default }
                }
            }
            // Routing: full-tunnel by default on phones (a VPN should carry ALL traffic);
            // `gateway = false` opts into split-tunnel (only the tunnel subnet + pushed
            // routes). Mirrors the Rust client's `gateway` key — the only way to pick
            // split-tunnel via INI (there is no UI toggle).
            val fullTunnel = boolAt("gateway", true)
            // DNS: `dns = <ip,ip>` is the Android resolver list. Tolerate the Rust/router
            // MODE values (`off`/`tunnel`/`system`) by falling back to the defaults
            // instead of adding a literal "off" as a resolver (which throws at establish).
            val dnsRaw = q["dns"]?.trim()
            val dns = if (dnsRaw.isNullOrEmpty() || dnsRaw.lowercase() in setOf("off", "tunnel", "system"))
                null
            else
                dnsRaw.split(',').map { it.trim() }.filter { it.isNotEmpty() }
            // Padding bounds are clamped, not rejected — see [checkedPadding]. (C6)
            val pad = checkedPadding(
                q["padding_min"]?.toIntOrNull() ?: 0,
                q["padding_max"]?.toIntOrNull() ?: 255
            )
            return VpnConfig(
                serverAddress = host,
                port = port,
                protocol = q["proto"]?.ifBlank { null } ?: "tcp",
                connectionTimeoutSecs = q["timeout"]?.toLongOrNull() ?: 30L,
                reconnectEnabled = boolAt("reconnect", true),
                reconnectMaxRetries = q["reconnect_retries"]?.toIntOrNull() ?: -1,
                reconnectBaseDelaySecs = q["reconnect_base_delay"]?.toLongOrNull() ?: 1L,
                reconnectMaxDelaySecs = q["reconnect_max_delay"]?.toLongOrNull() ?: 60L,
                username = q["user"]?.ifBlank { null } ?: "client",
                password = q["pass"] ?: "",
                serverPublicKeyHex = q["key"]?.takeIf { it.isNotEmpty() },
                // H-1: on by default; needs a pinned key. `bind_static = false` for TOFU.
                bindStaticToSession = boolAt("bind_static", true),
                routingMode = if (fullTunnel) "full-tunnel" else "split-tunnel",
                addDefaultGateway = fullTunnel,
                wireMode = q["mode"]?.ifBlank { null } ?: "fake-tls",
                sni = q["sni"]?.takeIf { it.isNotEmpty() },
                realityShortId = q["reality_sid"]?.takeIf { it.isNotEmpty() },
                obfsKey = q["obfs_key"] ?: "",
                obfsFronting = q["front"]?.ifBlank { null } ?: "websocket",
                // F2: AmneziaWG junk. `awg = true` + jc/jmin/jmax (caps applied at use).
                awgEnabled = boolAt("awg", false),
                awgJc = q["jc"]?.toIntOrNull() ?: 0,
                awgJmin = q["jmin"]?.toIntOrNull() ?: 40,
                awgJmax = q["jmax"]?.toIntOrNull() ?: 300,
                quicEnabled = boolAt("quic", false),
                routeLocalNetworks = boolAt("route_local", false),
                allowIpv6Leak = boolAt("allow_ipv6_leak", false),
                allowLan = boolAt("allow_lan", false),
                // Explicit per-CIDR routing (comma-separated). exclude carves subnets OUT of
                // the tunnel (VpnService.excludeRoute, API 33+); include forces subnets IN.
                includeRoutes = q["include"]?.split(',')?.map { it.trim() }?.filter { it.isNotEmpty() } ?: emptyList(),
                excludeRoutes = q["exclude"]?.split(',')?.map { it.trim() }?.filter { it.isNotEmpty() } ?: emptyList(),
                dnsServers = if (dns.isNullOrEmpty()) emptyList() else dns,
                // 0 = auto (use server-pushed MTU). Range-checked: see [checkedMtu].
                mtu = checkedMtu(q["mtu"]?.toIntOrNull() ?: 0),
                // Same false-set as the Rust `bool_or` and the iOS client. The old test
                // (`!= "false" && != "0"`) read `mtu_probe = off` / `no` as ON — the exact
                // opposite of what the user wrote, and of what the desktop client does.
                // Through boolAt like every other boolean: the old "anything not in the
                // off-set is ON" reading meant `mtu_probe = ture` silently enabled probing
                // and was never recorded as a typo. (Audit 2026-07-31.)
                mtuProbe = boolAt("mtu_probe", true),
                // Per-app split tunnel (Android extra). Only "include"/"exclude" are honoured;
                // anything else (or a missing key) falls back to "all" = every app tunnelled.
                appsMode = q["apps_mode"]?.trim()?.lowercase()?.takeIf { it == "include" || it == "exclude" } ?: "all",
                apps = q["apps"]?.split(',')?.map { it.trim() }?.filter { it.isNotEmpty() } ?: emptyList(),
                // Local overrides for the normally server-pushed knobs. Key names match iOS.
                paddingEnabled = boolAt("padding", true),
                paddingMin = pad.first,
                paddingMax = pad.second,
                heartbeatEnabled = boolAt("heartbeat", true),
                heartbeatIntervalMs = q["heartbeat_interval"]?.toLongOrNull() ?: 15000L,
                heartbeatDataSize = q["heartbeat_size"]?.toIntOrNull() ?: 16,
                heartbeatJitterMs = q["heartbeat_jitter"]?.toLongOrNull() ?: 2000L,
                shapingEnabled = boolAt("shaping", false),
                shapingGapMeanMs = q["shaping_gap_mean"]?.toLongOrNull() ?: 700L,
                shapingGapMinMs = q["shaping_gap_min"]?.toLongOrNull() ?: 40L,
                shapingGapMaxMs = q["shaping_gap_max"]?.toLongOrNull() ?: 6000L,
                shapingBudgetBytesPerSec = q["shaping_budget"]?.toIntOrNull() ?: 16384,
                shapingMinSize = q["shaping_min_size"]?.toIntOrNull() ?: 64,
                shapingMaxSize = q["shaping_max_size"]?.toIntOrNull() ?: 1024,
                shapingStealth = boolAt("shaping_stealth", false),
                shapingStealthRateMbps = q["shaping_stealth_mbps"]?.toIntOrNull() ?: 2,
                // Carried through untouched so re-saving a desktop config keeps its logging.
                loggingLevel = log?.get("level")?.takeIf { it.isNotEmpty() },
                loggingFile = log?.get("file")?.takeIf { it.isNotEmpty() },
                loggingTimeFormat = log?.get("time_format")?.takeIf { it.isNotEmpty() },
                unparsedBooleanKeys = badBools.toList()
            )
        }

        /** Minimal line-oriented INI parser (mirrors qeli/src/config/format.rs):
         *  `[section]` / `[kind:instance]`, `key = value`, full-line `;`/`#`
         *  comments, surrounding double-quotes stripped. */
        private fun parseIni(text: String): Map<String, MutableMap<String, String>> {
            val out = LinkedHashMap<String, MutableMap<String, String>>()
            var cur: MutableMap<String, String>? = null
            for (raw in text.lineSequence()) {
                val line = raw.trim()
                if (line.isEmpty() || line.startsWith(";") || line.startsWith("#")) continue
                if (line.startsWith("[") && line.endsWith("]")) {
                    val name = line.substring(1, line.length - 1).trim().substringBefore(':').trim()
                    cur = out.getOrPut(name) { LinkedHashMap() }
                } else {
                    val eq = line.indexOf('=')
                    if (eq < 0) continue
                    val k = line.substring(0, eq).trim()
                    var v = line.substring(eq + 1).trim()
                    if (v.length >= 2 && v.startsWith("\"") && v.endsWith("\"")) v = v.substring(1, v.length - 1)
                    if (k.isNotEmpty()) cur?.put(k, v)
                }
            }
            return out
        }

        /**
         * Parse a qeli JSON client config. Unknown fields are ignored; missing
         * fields fall back to the Rust defaults. Supports both the canonical
         * schema and a few legacy aliases.
         */
        fun fromJson(text: String): VpnConfig {
            val root = JSONObject(text)
            // `optBoolean` swallows anything that is not a real JSON boolean and returns the
            // default — the same fail-open the INI path had, reached through a different door.
            // A key that is PRESENT but unreadable is recorded; an absent one is not (that is
            // what the default is for). (Audit 2026-08-01, §8.)
            val badJsonBools = mutableListOf<String>()
            fun jbool(o: JSONObject, key: String, default: Boolean): Boolean {
                if (!o.has(key) || o.isNull(key)) return default
                when (val v = o.get(key)) {
                    is Boolean -> return v
                    is String -> when (v.trim().lowercase()) {
                        "true", "1", "yes", "on" -> return true
                        "false", "0", "no", "off" -> return false
                    }
                }
                badJsonBools.add(key)
                return default
            }
            val server = root.optJSONObject("server") ?: JSONObject()
            val reconnect = server.optJSONObject("reconnect") ?: JSONObject()
            val auth = root.optJSONObject("auth") ?: JSONObject()
            val tun = root.optJSONObject("tun") ?: JSONObject()
            val routing = root.optJSONObject("routing") ?: JSONObject()
            val dns = root.optJSONObject("dns") ?: JSONObject()
            val obf = root.optJSONObject("obfuscation") ?: JSONObject()
            val padding = obf.optJSONObject("padding") ?: JSONObject()
            val heartbeat = obf.optJSONObject("heartbeat") ?: JSONObject()
            val quic = obf.optJSONObject("quic") ?: JSONObject()
            val awg = obf.optJSONObject("awg") ?: JSONObject()
            // Sections the importer used to stop short of. A canonical JSON profile carrying
            // shaping, an explicit `tun.mtu_probe = false` or a [logging] block lost all of it
            // on import and came back with defaults — the profile looked configured and was
            // not, and re-exporting it wrote the loss back out. (Audit 2026-07-29, #6.)
            val shaping = obf.optJSONObject("traffic_shaping") ?: JSONObject()
            val logging = root.optJSONObject("logging") ?: JSONObject()

            val password = when {
                auth.has("password") && !auth.isNull("password") -> auth.optString("password")
                root.has("password") -> root.optString("password")
                else -> ""
            }
            // Padding bounds are clamped, not rejected — see [checkedPadding]. (C6)
            val pad = checkedPadding(padding.optInt("min_bytes", 0), padding.optInt("max_bytes", 255))

            return VpnConfig(
                serverAddress = server.optString("address", root.optString("address", "127.0.0.1")),
                port = server.optInt("port", root.optInt("port", 443)),
                protocol = server.optString("protocol", "tcp"),
                connectionTimeoutSecs = server.optLong("connection_timeout_secs", 30),
                reconnectEnabled = jbool(reconnect, "enabled", true),
                reconnectMaxRetries = reconnect.optInt("max_retries", -1),
                reconnectBaseDelaySecs = reconnect.optLong("base_delay_secs", 1),
                reconnectMaxDelaySecs = reconnect.optLong("max_delay_secs", 60),
                username = auth.optString("username", root.optString("username", "client")),
                password = password,
                serverPublicKeyHex = auth.optStringOrNull("server_public_key"),
                bindStaticToSession = jbool(auth, "bind_static_to_session", true),
                // 0 = auto (use server-pushed MTU). Range-checked: see [checkedMtu].
                mtu = checkedMtu(tun.optInt("mtu", 0)),
                // Default to full-tunnel (a VPN should carry ALL traffic) so a config
                // without a routing section doesn't silently leak outside the tunnel.
                // Explicit "split-tunnel" is still honoured: isFullTunnel only becomes
                // true via add_default_gateway or mode=="full-tunnel".
                routingMode = routing.optString("mode", "full-tunnel"),
                addDefaultGateway = jbool(routing, "add_default_gateway", false),
                includeRoutes = routing.optStringList("include"),
                excludeRoutes = routing.optStringList("exclude"),
                routeLocalNetworks = jbool(routing, "route_local_networks", false),
                allowIpv6Leak = jbool(routing, "allow_ipv6_leak", false),
                // Was missing: a JSON config carrying routing.allow_lan imported with LAN
                // bypass silently off, while the iOS client honoured it.
                allowLan = jbool(routing, "allow_lan", false),
                dnsServers = dns.optStringList("servers"),
                wireMode = obf.optString("mode", "fake-tls"),
                obfsKey = obf.optString("obfs_key", ""),
                obfsFronting = obf.optString("fronting", "websocket"),
                awgEnabled = jbool(awg, "enabled", false),
                awgJc = awg.optInt("jc", 0),
                awgJmin = awg.optInt("jmin", 40),
                awgJmax = awg.optInt("jmax", 300),
                quicEnabled = jbool(quic, "enabled", false),
                sni = obf.optStringOrNull("sni"),
                realityShortId = obf.optStringOrNull("reality_short_id"),
                paddingEnabled = jbool(padding, "enabled", true),
                paddingMin = pad.first,
                paddingMax = pad.second,
                heartbeatEnabled = jbool(heartbeat, "enabled", true),
                heartbeatIntervalMs = heartbeat.optLong("interval_ms", 15000),
                heartbeatDataSize = heartbeat.optInt("data_size_bytes", 16),
                heartbeatJitterMs = heartbeat.optLong("jitter_ms", 2000),
                mtuProbe = jbool(tun, "mtu_probe", true),
                shapingEnabled = jbool(shaping, "enabled", false),
                shapingGapMeanMs = shaping.optLong("idle_gap_mean_ms", 700),
                shapingGapMinMs = shaping.optLong("idle_gap_min_ms", 40),
                shapingGapMaxMs = shaping.optLong("idle_gap_max_ms", 6000),
                shapingBudgetBytesPerSec = shaping.optInt("budget_bytes_per_sec", 16384),
                shapingMinSize = shaping.optInt("min_size", 64),
                shapingMaxSize = shaping.optInt("max_size", 1024),
                shapingStealth = jbool(shaping, "stealth", false),
                shapingStealthRateMbps = shaping.optInt("stealth_rate_mbps", 2),
                loggingLevel = logging.optString("level", "").takeIf { it.isNotEmpty() },
                loggingFile = logging.optString("file", "").takeIf { it.isNotEmpty() },
                loggingTimeFormat = logging.optString("time_format", "").takeIf { it.isNotEmpty() },
                unparsedBooleanKeys = badJsonBools.toList()
            )
        }

        /**
         * Parse a `qeli://` share link (the compact, QR-friendly format produced
         * by the server's `/api/share` and `qeli add-client --link`). Mirrors the
         * Rust `ClientLink::from_uri` (qeli/src/config/share.rs).
         *
         * Shape:
         * `qeli://<user>:<pass>@<host>:<port>?proto=tcp&mode=fake-tls&key=<hex>&sni=<host>&obfs=<key>#<label>`
         *
         * Everything not carried by the link is defaulted here and overwritten by
         * the server at handshake time (routes, DNS, MTU, obfuscation params).
         */
        fun fromQeliUri(uri: String): VpnConfig {
            val trimmed = uri.trim()
            val rest0 = trimmed.removePrefix("qeli://")
            require(rest0.length != trimmed.length) { "not a qeli:// link" }

            // Split off #fragment (label), then ?query.
            val (beforeFrag, _label) = rest0.split("#", limit = 2).let {
                if (it.size == 2) it[0] to pctDecode(it[1]) else it[0] to null
            }
            val (authority, query) = beforeFrag.split("?", limit = 2).let {
                if (it.size == 2) it[0] to it[1] else it[0] to null
            }

            // userinfo@host:port  (rsplit so passwords containing '@' if escaped are safe)
            val atIdx = authority.lastIndexOf('@')
            val userinfo = if (atIdx >= 0) authority.substring(0, atIdx) else null
            val hostPort = if (atIdx >= 0) authority.substring(atIdx + 1) else authority
            val host: String
            val port: Int
            if (hostPort.startsWith('[')) {
                // Bracketed IPv6 literal: [2001:db8::1]:443 — split on ']:' so the
                // colons inside the address aren't mistaken for the port separator.
                val rb = hostPort.indexOf(']')
                require(rb > 0 && rb + 1 < hostPort.length && hostPort[rb + 1] == ':') {
                    "qeli:// authority malformed IPv6 [host]:port"
                }
                host = hostPort.substring(1, rb)
                port = hostPort.substring(rb + 2).toIntOrNull()
                    ?: throw IllegalArgumentException("invalid port in qeli:// link")
            } else {
                val colonIdx = hostPort.lastIndexOf(':')
                require(colonIdx > 0) { "qeli:// authority missing :port" }
                host = hostPort.substring(0, colonIdx)
                port = hostPort.substring(colonIdx + 1).toIntOrNull()
                    ?: throw IllegalArgumentException("invalid port in qeli:// link")
            }
            require(host.isNotEmpty()) { "empty host in qeli:// link" }
            // `toIntOrNull` accepts ANY Int — 0, 99999 and negatives all parsed fine and
            // produced a profile that only failed later with an opaque socket error. Swift
            // and C# already range-checked here; Kotlin and Rust did not. Divergence found
            // by the conformance fixtures (conformance/qeli-links.json).
            require(port in 1..65535) { "port $port out of range in qeli:// link (1..65535)" }

            var user = ""
            var pass = ""
            if (userinfo != null) {
                val sep = userinfo.indexOf(':')
                if (sep >= 0) {
                    user = pctDecode(userinfo.substring(0, sep))
                    pass = pctDecode(userinfo.substring(sep + 1))
                } else {
                    user = pctDecode(userinfo)
                }
            }

            var proto = "tcp"; var mode = "fake-tls"
            var key: String? = null; var sni: String? = null; var obfs = ""
            var front = "websocket"; var quic = false; var rsid: String? = null
            // F2 AmneziaWG junk: awg (=1 when enabled), jc, jmin, jmax.
            var awg = false; var jc = 0; var jmin = 40; var jmax = 300
            // Parsed here so a link emitted by toQeliUri survives a round trip. `mtu` was
            // already being EMITTED but had no case below, so importing dropped it. (C-12)
            var linkMtu = 0; var linkMtuProbe = true; var bindStatic = true
            query?.split("&")?.forEach { pair ->
                if (pair.isEmpty()) return@forEach
                val eq = pair.indexOf('=')
                val k = if (eq >= 0) pair.substring(0, eq) else pair
                val v = pctDecode(if (eq >= 0) pair.substring(eq + 1) else "")
                when (k) {
                    "proto" -> proto = v
                    "mode" -> mode = v
                    "key" -> key = v.ifEmpty { null }
                    "sni" -> sni = v.ifEmpty { null }
                    "rsid" -> rsid = v.ifEmpty { null }
                    "obfs" -> obfs = v
                    "front" -> if (v.isNotEmpty()) front = v
                    "quic" -> quic = v == "1" || v.equals("true", ignoreCase = true)
                    "awg" -> awg = v == "1" || v.equals("true", ignoreCase = true)
                    "jc" -> jc = v.toIntOrNull() ?: 0
                    "jmin" -> jmin = v.toIntOrNull() ?: 40
                    "jmax" -> jmax = v.toIntOrNull() ?: 300
                    // Out-of-range → fall back to auto rather than importing a value the
                    // client can't apply, and SAY SO (a silently dropped mtu looks like the
                    // link never carried one). Matches the Rust from_link fallback; iOS used
                    // to reject the whole link and this app used to import it verbatim, so
                    // `qeli://…?mtu=99999` reached VpnService.Builder.setMtu and turned into
                    // an endless establish-fail → reconnect loop. (Audit 2026-07-27, C6)
                    "mtu" -> linkMtu = linkMtuOrAuto(v.toIntOrNull() ?: 0)
                    // Legacy tolerance only — this app stopped EMITTING these in 0.7.13
                    // (see toQeliUri). Kept so links it issued earlier still import the way
                    // they were shared; no other implementation carries them.
                    "mtu_probe" -> linkMtuProbe = !(v == "0" || v.equals("false", ignoreCase = true))
                    "bind_static" -> bindStatic = !(v == "0" || v.equals("false", ignoreCase = true))
                    // forward-compatible: ignore unknown params
                }
            }

            // Alias convenience: `mode=udp-quic` / `udp-obfs` fold transport+QUIC into the
            // wire mode. Split it back into proto + wire mode + quic — the same mapping the
            // Rust link parser applies (config/share.rs). Android was the only client that
            // did NOT expand these: it kept the alias as the literal wire mode, which no
            // handshake matches, so such a link imported cleanly and then never connected.
            // Applied AFTER the loop because `proto` may come later in the query.
            when (mode) {
                "udp-quic" -> { proto = "udp"; mode = "fake-tls"; quic = true }
                "udp-obfs" -> { proto = "udp"; mode = "obfs" }
            }

            return VpnConfig(
                serverAddress = host,
                port = port,
                protocol = proto,
                username = user,
                password = pass,
                serverPublicKeyHex = key,
                wireMode = mode,
                obfsKey = obfs,
                obfsFronting = front,
                awgEnabled = awg,
                awgJc = jc,
                awgJmin = jmin,
                awgJmax = jmax,
                quicEnabled = quic,
                sni = sni,
                realityShortId = rsid,
                mtu = linkMtu,
                mtuProbe = linkMtuProbe,
                bindStaticToSession = bindStatic
            ).also {
                // A link is untrusted input: validate at the boundary so a forged newline
                // in user/pass/sni can never reach the profile store (and from there the
                // next toIni). Same gate the iOS client applies to an imported link.
                it.validate()
            }
        }

        /** Percent-encode UTF-8 bytes except RFC 3986 unreserved (mirrors C# Uri.EscapeDataString). */
        private fun pctEncode(s: String): String {
            val sb = StringBuilder(s.length)
            for (b in s.toByteArray(Charsets.UTF_8)) {
                val c = (b.toInt() and 0xFF).toChar()
                if (c in 'A'..'Z' || c in 'a'..'z' || c in '0'..'9' || c == '-' || c == '_' || c == '.' || c == '~')
                    sb.append(c)
                else sb.append('%').append("%02X".format(b.toInt() and 0xFF))
            }
            return sb.toString()
        }

        /** Percent-decode; invalid escapes pass through literally (matches Rust). */
        private fun pctDecode(s: String): String {
            if (s.indexOf('%') < 0) return s
            val out = StringBuilder(s.length)
            var i = 0
            val bytes = ArrayList<Byte>(s.length)
            while (i < s.length) {
                val c = s[i]
                if (c == '%' && i + 2 < s.length) {
                    val h = hexVal(s[i + 1]); val l = hexVal(s[i + 2])
                    if (h >= 0 && l >= 0) { bytes.add(((h shl 4) or l).toByte()); i += 3; continue }
                }
                // flush any pending UTF-8 bytes before appending a literal char
                if (bytes.isNotEmpty()) { out.append(String(bytes.toByteArray(), Charsets.UTF_8)); bytes.clear() }
                out.append(c); i++
            }
            if (bytes.isNotEmpty()) out.append(String(bytes.toByteArray(), Charsets.UTF_8))
            return out.toString()
        }

        private fun hexVal(c: Char): Int = when (c) {
            in '0'..'9' -> c - '0'
            in 'a'..'f' -> c - 'a' + 10
            in 'A'..'F' -> c - 'A' + 10
            else -> -1
        }

        private fun JSONObject.optStringOrNull(key: String): String? {
            if (!has(key) || isNull(key)) return null
            val v = optString(key, "")
            return v.ifEmpty { null }
        }

        private fun JSONObject.optStringList(key: String): List<String> {
            val arr = optJSONArray(key) ?: return emptyList()
            return (0 until arr.length()).mapNotNull { arr.optString(it).ifEmpty { null } }
        }
    }
}
