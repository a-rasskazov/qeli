import Foundation

struct VPNConfig: Codable, Equatable, Sendable {
    /// Keys whose boolean value was neither true-ish nor false-ish — `gateway = ture`.
    ///
    /// Carried instead of being resolved at parse time because the ORIGINAL STRING IS LOST once
    /// a `Bool` is produced, so nothing downstream could tell a typo from a deliberate `false`.
    /// That mattered: every unknown value read as `false`, so `bind_static = ture` silently
    /// dropped the static-key binding and `gateway = ture` silently turned a full tunnel into a
    /// split one — with no message anywhere.
    ///
    /// Parsing still SUCCEEDS (an editor must be able to open a bad profile to fix it);
    /// ``validate()`` is what refuses. (Audit 2026-07-31.)
    var unparsedBooleanKeys: [String] = []

    /// Keys that appeared more than once in one section, as `section.key`.
    ///
    /// A key read as a SINGLE value but written twice makes the file ambiguous, and the ports
    /// resolved it differently: this parser folds entries into a dictionary and keeps the LAST,
    /// while the Rust client takes the FIRST. Two `server` lines therefore sent the Rust client
    /// to one host and every GUI client to another, out of one file, with nothing reported.
    ///
    /// Recorded, not resolved — picking a winner still leaves the other implementations
    /// disagreeing, and only the author knows which line was meant. Parsing still SUCCEEDS, as
    /// with ``unparsedBooleanKeys``; ``validate()`` is what refuses. (Audit 2026-08-01, §7.)
    var duplicateKeys: [String] = []

    /// Numeric fields whose value was present but unreadable, which used to fall back to the
    /// default in silence. `server`'s port has always thrown; this covers the rest and keeps
    /// this port as strict as the C# one. Parsing still SUCCEEDS; ``validate()`` refuses.
    /// (Audit 2026-08-01, §P2.)
    var unparsedNumericKeys: [String] = []

    /// `[qeli]` keys no qeli client understands — i.e. misspellings. The setting they were
    /// meant to change silently keeps its default, which is how `gatway = true` left a tunnel
    /// split with nothing said. Reported, not resolved; ``validate()`` refuses.
    /// (Audit 2026-08-01, §14.)
    var unknownKeys: [String] = []

    /// Every `[qeli]` key any qeli client understands — the union across the four ports, NOT
    /// just the ones this one reads.
    ///
    /// The distinction is the whole point. A key this port ignores is not necessarily a typo:
    /// `keepalive`, `post_up`, `exit_node` and friends are real Rust-client file-only settings
    /// (docs/ru/CONFIG.md, "Что пушем НЕ передаётся"), and a CLI profile carrying them must
    /// still open here. Only a name NOTHING understands is a typo.
    static let knownINIKeys: Set<String> = [
        // Read by this port.
        // `allow_lan`, `apps` and `apps_mode` are read AND written a few lines below — leaving
        // them out made this port reject a profile it had exported itself, and every profile
        // carrying per-app tunnelling or allow-LAN from Android. An unknown-key check is only
        // as good as its list: a missing entry does not degrade to "ignored", it rejects the
        // whole config.
        "allow_ipv6_leak", "allow_lan", "apps", "apps_mode",
        "awg", "bind_static", "dev", "dev_node", "dns", "exclude", "forward",
        "front", "gateway", "heartbeat", "heartbeat_interval", "heartbeat_jitter",
        "heartbeat_size", "include", "jc", "jmax", "jmin", "key", "kill_switch", "local",
        "lport", "metric", "mode", "mtu", "mtu_probe", "name", "obfs_key", "padding",
        "padding_max", "padding_min", "pass", "persist_tun", "proto", "quic", "reality_sid",
        "reconnect", "reconnect_base_delay", "reconnect_max_delay", "reconnect_retries",
        "route_file", "route_local", "server", "shaping", "shaping_budget", "shaping_gap_max",
        "shaping_gap_mean", "shaping_gap_min", "shaping_max_size", "shaping_min_size",
        "shaping_stealth", "shaping_stealth_mbps", "sni", "timeout", "user",
    ].union(carriedINIKeys)

    /// Keys this port ACCEPTS but does not model — read into ``carriedKeys`` and written back
    /// verbatim, so opening and saving a CLI profile does not strip them.
    ///
    /// They are on the allowlist because a desktop profile carrying them must open here; they
    /// are in THIS list because accepting a key without keeping it is how the open-and-save
    /// round trip silently deleted hooks and security settings. Allowlisting alone was the
    /// first half of the fix and, on its own, the more dangerous half: it makes the profile
    /// open, which is exactly what leads someone to save it. (Audit 2026-08-02, §4 of the
    /// follow-up; Android got both halves first.)
    static let carriedINIKeys: Set<String> = [
        // Rust-client only, documented as such (docs/ru/CONFIG.md, "Что пушем НЕ передаётся").
        "allow_unpinned_tofu", "autostart", "dev_attach", "dns_servers", "exit_node",
        "gateway_nat", "keepalive", "lan_subnet", "post_down", "post_up", "tcp_nodelay",
        // Socket buffers (Linux-only in the Rust client) and the headless password sources.
        "password_command", "password_file", "recv_buffer_size", "send_buffer_size",
    ]

    /// Accepted tunnel-MTU range. The ceiling is derived, in Rust, from the record format
    /// (`protocol/packet.rs MAX_TUNNEL_MTU`): a record holds nonce + counter + payload +
    /// padding-length + tag and must fit `MAX_RECORD_SIZE`, so anything larger the PEER
    /// REJECTS. Mirrored here as a literal — the four ports and the two UIs must all carry the
    /// same number, because raising it in one place only is worse than not raising it.
    /// (Audit 2026-08-01, §1.)
    static let mtuMin = 576
    static let mtuMax = 16638

    var serverAddress: String
    var port: Int
    var protocolName: String = "tcp"
    var connectionTimeoutSeconds: Int = 30

    var reconnectEnabled = true
    var reconnectMaxRetries = -1
    var reconnectBaseDelaySeconds = 1
    var reconnectMaxDelaySeconds = 60

    var username: String = "client"
    var password: String = ""
    var serverPublicKeyHex: String?
    var bindStaticToSession = true

    var mtu = 0
    var mtuProbe = true
    var routingMode = "full-tunnel"
    var addDefaultGateway = true
    var includeRoutes: [String] = []
    var excludeRoutes: [String] = []
    var routeLocalNetworks = false
    var allowIPv6Leak = false
    var allowLAN = false
    var dnsServers: [String] = []
    /// DNS handling mode, mirroring `dns.mode` in the Rust client: `tunnel` (default — install
    /// resolvers reachable through the tunnel), `off` or `system` (leave the device resolver
    /// alone).
    ///
    /// The flat INI spells the mode and the server list with the SAME key — `dns = off` versus
    /// `dns = 1.1.1.1, 8.8.8.8` — so a shared desktop/router profile carries a value this port
    /// used to discard. Discarding it was not neutral: with no explicit resolvers the engine
    /// installs the public fallback on a full tunnel, so `off` produced exactly the behaviour
    /// it asks to prevent. (Audit 2026-08-02, §3.)
    var dnsMode: String = "tunnel"

    var wireMode = "fake-tls"
    var obfsKey = ""
    var obfsFronting = "websocket"
    var awgEnabled = false
    var awgJunkCount = 0
    var awgJunkMin = 40
    var awgJunkMax = 300
    var quicEnabled = false
    var sni: String?
    var realityShortID: String?

    var paddingEnabled = true
    var paddingMin = 0
    var paddingMax = 255

    /// Largest `padding_max` that can be encoded, mirroring the Rust client's cap.
    ///
    /// Padding rides on EVERY record, so this bounds the record, not a one-off. It applies to
    /// both a local profile (`validate()`) and a server-pushed value (`clampPushedObfuscation`)
    /// — the local one used to go unchecked, and applies FIRST. (Audit 2026-08-02, §9.)
    static let paddingMaxCeiling = 1_400
    var heartbeatEnabled = true
    var heartbeatIntervalMilliseconds = 15_000
    var heartbeatDataSize = 16
    var heartbeatJitterMilliseconds = 2_000

    var shapingEnabled = false
    var shapingGapMeanMilliseconds = 700
    var shapingGapMinMilliseconds = 40
    var shapingGapMaxMilliseconds = 6_000
    var shapingBudgetBytesPerSecond = 16_384
    var shapingMinSize = 64
    var shapingMaxSize = 1_024
    var shapingStealth = false
    var shapingStealthRateMbps = 2

    // Retained for Android/share/backup round-trip. Applying arbitrary app rules on
    // consumer iOS requires MDM and is deliberately not attempted by the app.
    var appsMode = "all"
    var apps: [String] = []

    /// `[qeli]` keys accepted but not modelled (``carriedINIKeys``), kept verbatim so a save
    /// does not delete them. Written back by ``toINI()`` after the modelled keys.
    var carriedKeys: [String: String] = [:]

    // [logging] passthrough. Not used by the app (its own log setting lives in
    // AppSettings); carried so a desktop/router client.conf opened and re-saved here keeps
    // its logging section instead of silently losing it — the Rust client parses AND
    // re-emits these, and the Android client now does too.
    var loggingLevel: String?
    var loggingFile: String?
    var loggingTimeFormat: String?

    var isUDP: Bool { protocolName.caseInsensitiveCompare("udp") == .orderedSame }
    /// `all` counts too. The validator accepts `split-tunnel | full-tunnel | all` (the Rust
    /// client's set, see `client/route.rs`), but this only compared against `full-tunnel` — so a
    /// perfectly valid `routing.mode = "all"` profile validated and then ran as a SPLIT tunnel,
    /// quietly sending everything outside the VPN past it. (Audit 2026-07-31, §2.)
    var isFullTunnel: Bool {
        addDefaultGateway || routingMode == "full-tunnel" || routingMode == "all"
    }

    init(serverAddress: String, port: Int) {
        self.serverAddress = serverAddress
        self.port = port
    }

    init(parsing text: String) throws {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.hasPrefix("qeli://") {
            self = try Self.fromQeliURI(trimmed)
        } else if trimmed.hasPrefix("{") {
            self = try Self.fromJSON(trimmed)
        } else {
            self = try Self.fromINI(trimmed)
        }
        try validate()
    }

    /// Clamp every obfuscation/shaping value the SERVER pushes in AuthOK into a usable
    /// range.
    ///
    /// `validate()` covers what the user types (port, timeout, mtu, padding) but nothing
    /// that arrives over the wire, and the AuthOK parsers assigned these fields straight
    /// from the JSON. Two consequences, both remote and post-authentication:
    ///
    /// * a large `idle_gap_mean_ms` made `TrafficShaper.nextGapMilliseconds` produce a
    ///   `Double` outside `Int`'s range, and `Int(_:)` TRAPS rather than saturating —
    ///   killing the Network Extension process on the first heartbeat tick;
    /// * a large `padding.max_bytes` pushed records past `MaxRecordSize`, so
    ///   `PacketCodec.encrypt` threw, the uplink died, the client reconnected, got the
    ///   same value and looped forever.
    ///
    /// Clamping rather than rejecting: a server that pushes an odd value is far more
    /// likely misconfigured than hostile, and refusing to connect would be a worse
    /// outcome than shaping slightly differently than asked. (Audit 2026-07-27, C10.)
    mutating func clampPushedObfuscation() {
        // Padding must leave room inside one record; the ceiling mirrors the Rust client's.
        paddingMin = min(max(paddingMin, 0), Self.paddingMaxCeiling)
        paddingMax = min(max(paddingMax, paddingMin), Self.paddingMaxCeiling)

        shapingGapMeanMilliseconds = min(max(shapingGapMeanMilliseconds, 1), 60_000)
        shapingGapMinMilliseconds = min(max(shapingGapMinMilliseconds, 0), 60_000)
        shapingGapMaxMilliseconds = min(
            max(shapingGapMaxMilliseconds, shapingGapMinMilliseconds),
            60_000
        )
        shapingMinSize = min(max(shapingMinSize, 0), 1_400)
        shapingMaxSize = min(max(shapingMaxSize, shapingMinSize), 1_400)
        shapingBudgetBytesPerSecond = min(max(shapingBudgetBytesPerSecond, 0), 100_000_000)
        shapingStealthRateMbps = min(max(shapingStealthRateMbps, 1), 10_000)

        heartbeatIntervalMilliseconds = min(max(heartbeatIntervalMilliseconds, 1_000), 600_000)
        heartbeatJitterMilliseconds = min(max(heartbeatJitterMilliseconds, 0), 60_000)
    }

    func validate() throws {
        // A boolean nobody could parse is a typo, and every one of them used to read as `false`
        // — so `bind_static = ture` dropped the static-key binding and `gateway = ture` turned a
        // full tunnel into a split one, silently. Refuse to connect rather than run with a
        // setting the user plainly did not choose. (Audit 2026-07-31.)
        if !unparsedBooleanKeys.isEmpty {
            throw VPNConfigError.invalid(
                "unrecognised boolean value for \(unparsedBooleanKeys.joined(separator: ", ")) — "
                + "expected true/false, yes/no, on/off or 1/0")
        }

        // A misspelled key name is invisible: nothing reads it, so the setting it was meant to
        // change silently keeps its default. (Audit 2026-08-01, §14.)
        if !unknownKeys.isEmpty {
            throw VPNConfigError.invalid(
                "unknown key(s), likely misspelled: \(unknownKeys.joined(separator: ", ")) — "
                + "nothing reads these, so the setting they were meant to change is at its default")
        }

        // A number nobody could parse must not become a default in silence. (Audit 2026-08-01.)
        if !unparsedNumericKeys.isEmpty {
            throw VPNConfigError.invalid(
                "unparseable number for \(unparsedNumericKeys.joined(separator: ", ")) — the "
                + "default would have been used instead")
        }

        // A key written twice is ambiguous, and the ports disagreed on which line wins — the
        // same file reached two different servers depending on the client. (Audit 2026-08-01.)
        if !duplicateKeys.isEmpty {
            throw VPNConfigError.invalid(
                "key(s) \(duplicateKeys.joined(separator: ", ")) appear more than once and are "
                + "read as a single value; implementations disagree on which wins — keep one")
        }

        // String enums the runtime compares against ONE literal, so an unknown value does not
        // error — it silently selects the other branch. `front = webscoket` drops the WebSocket
        // framing and the peer then disagrees about the wire; `routing_mode = full-tunel` with
        // `add_default_gateway = false` quietly becomes a split tunnel. `proto` and `mode` were
        // already checked below. (Audit 2026-07-31, §3.)
        let enums: [(String, String, [String])] = [
            ("front", obfsFronting, ["websocket", "none"]),
            ("routing_mode", routingMode, ["split-tunnel", "full-tunnel", "all"])
        ]
        for (field, value, allowed) in enums where !allowed.contains(value) {
            throw VPNConfigError.invalid(
                "unknown \(field) '\(value)' — expected "
                + allowed.map { "'\($0)'" }.joined(separator: " or "))
        }

        let scalarFields: [(String, String)] = [
            ("server", serverAddress),
            ("proto", protocolName),
            ("user", username),
            ("pass", password),
            ("key", serverPublicKeyHex ?? ""),
            ("routing_mode", routingMode),
            ("mode", wireMode),
            ("obfs_key", obfsKey),
            ("front", obfsFronting),
            ("sni", sni ?? ""),
            ("reality_sid", realityShortID ?? ""),
            ("apps_mode", appsMode)
        ]
        for (field, value) in scalarFields where Self.containsForbiddenINICharacters(value) {
            throw VPNConfigError.invalid("\(field) contains a forbidden line break or NUL character")
        }
        // Carried keys are written back verbatim, so they need the same INI-forgery gate as
        // everything else this port emits — a `post_up` with an embedded newline would
        // otherwise inject arbitrary config lines on save.
        for (field, value) in carriedKeys
        where Self.containsForbiddenINICharacters(field) || Self.containsForbiddenINICharacters(value) {
            throw VPNConfigError.invalid("\(field) contains a forbidden line break or NUL character")
        }
        let listFields: [(String, [String])] = [
            ("include", includeRoutes),
            ("exclude", excludeRoutes),
            ("dns", dnsServers),
            ("apps", apps)
        ]
        for (field, values) in listFields where values.contains(where: Self.containsForbiddenINICharacters) {
            throw VPNConfigError.invalid("\(field) contains a forbidden line break or NUL character")
        }
        guard !serverAddress.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw VPNConfigError.invalid("server host is empty")
        }
        guard (1...65_535).contains(port) else {
            throw VPNConfigError.invalid("server port must be between 1 and 65535")
        }
        guard ["tcp", "udp"].contains(protocolName.lowercased()) else {
            throw VPNConfigError.invalid("proto must be tcp or udp")
        }
        guard (1...300).contains(connectionTimeoutSeconds) else {
            throw VPNConfigError.invalid("timeout must be between 1 and 300 seconds")
        }
        guard ["plain", "fake-tls", "obfs", "reality-tls"].contains(wireMode.lowercased()) else {
            throw VPNConfigError.invalid("unsupported mode: \(wireMode)")
        }
        if mtu != 0 && !(Self.mtuMin...Self.mtuMax).contains(mtu) {
            throw VPNConfigError.invalid("mtu must be 0 or between \(Self.mtuMin) and \(Self.mtuMax)")
        }
        guard paddingMin >= 0, paddingMax >= paddingMin else {
            throw VPNConfigError.invalid("padding range is invalid")
        }
        // Padding is added to EVERY record, so an unbounded maximum is not a large-packet
        // setting — it is a record that cannot be encoded. A server-pushed value is clamped
        // on arrival, but the local profile is applied first: `padding_max = 65535` produced
        // `recordTooLarge` during AUTH or on the first data records, i.e. a tunnel that
        // connects and then dies, from a number the config editor accepted. The ceiling
        // matches the other ports. (Audit 2026-08-02, §9.)
        guard paddingMax <= Self.paddingMaxCeiling else {
            throw VPNConfigError.invalid(
                "padding_max must be at most \(Self.paddingMaxCeiling) — padding rides on every "
                    + "record, and a larger value cannot be encoded")
        }
        // A misspelled `apps_mode` must not resolve to the WIDEST setting in silence.
        // Handled like `proto` and `mode` above: the raw value is kept and refused here,
        // rather than coerced at parse time where the original is lost and `apps_mode =
        // includ` quietly tunnels every app. (Audit 2026-08-02, §10.)
        guard ["all", "include", "exclude"].contains(appsMode.lowercased()) else {
            throw VPNConfigError.invalid(
                "apps_mode must be all, include or exclude — got '\(appsMode)'")
        }
        // Same reasoning: the fallback is "tunnel", so a typo does not fail — it picks the
        // opposite of `off`/`system` and sends every lookup through the VPN.
        guard ["off", "tunnel", "system"].contains(dnsMode.lowercased()) else {
            throw VPNConfigError.invalid("dns mode must be off, tunnel or system — got '\(dnsMode)'")
        }
        // The flat INI spells the MODE and the RESOLVER LIST with the same `dns` key, so a
        // misspelled mode does not fall through to an error — it falls through to being read
        // as an ADDRESS. `dns = of` became a resolver named "of", the tunnel installed it, and
        // every lookup went to something that cannot answer. A resolver must be an IP literal
        // (you cannot resolve a resolver by name), so checking that turns the typo back into
        // an error. (Audit 2026-08-02, follow-up.)
        for server in dnsServers where !Self.isIPLiteral(server) {
            throw VPNConfigError.invalid(
                "dns server '\(server)' is not an IP address — if you meant a mode, it must be "
                    + "off, tunnel or system")
        }
    }

    /// True for a bare IPv4 or IPv6 literal.
    ///
    /// Deliberately not `getaddrinfo`: that RESOLVES anything which is not a literal, which is
    /// a network round trip during config validation for a value that is by definition not
    /// resolvable yet.
    static func isIPLiteral(_ s: String) -> Bool {
        let v = s.trimmingCharacters(in: .whitespaces)
        guard !v.isEmpty else { return false }
        if v.contains(":") {
            // IPv6: hex groups and at most one `::`. Enough to tell an address from a word —
            // the OS rejects a malformed one when the tunnel is built.
            let allowed = CharacterSet(charactersIn: "0123456789abcdefABCDEF:.")
            return v.unicodeScalars.allSatisfy { allowed.contains($0) }
                && v.filter { $0 == ":" }.count >= 2
        }
        let parts = v.split(separator: ".", omittingEmptySubsequences: false)
        guard parts.count == 4 else { return false }
        return parts.allSatisfy { p in
            !p.isEmpty && p.count <= 3 && p.allSatisfy(\.isNumber) && (Int(p) ?? 256) <= 255
        }
    }

    static func fromINI(_ text: String) throws -> VPNConfig {
        var dupKeys: [String] = []
        let sections = parseINI(text, duplicates: &dupKeys)
        guard let qeli = sections["qeli"] else {
            throw VPNConfigError.invalid("config is missing [qeli] section")
        }
        guard let endpoint = qeli["server"], !endpoint.isEmpty else {
            throw VPNConfigError.invalid("[qeli] is missing server = host:port")
        }
        let (host, port) = try parseEndpoint(endpoint)
        // Accepts the same spellings as the Rust client's `bool_or`. An unrecognised value is
        // RECORDED (see `unparsedBooleanKeys`) and falls back to the caller's default, instead
        // of silently reading as `false`.
        // An INI integer, recording the key when the value is present but not a number.
        //
        // Absent keeps the default silently — that is what a default is for. A value that is
        // THERE and unreadable is a typo, and substituting the default without a word is the
        // same failure `boolAt` exists to prevent. (Audit 2026-08-01, §P2.)
        var badNums: [String] = []
        func numAt(_ key: String, default fallback: Int) -> Int {
            guard let raw = qeli[key]?.trimmingCharacters(in: .whitespaces), !raw.isEmpty else {
                return fallback
            }
            guard let parsed = Int(raw) else {
                badNums.append(key)
                return fallback
            }
            return parsed
        }
        var badBools: [String] = []
        func boolAt(_ key: String, default fallback: Bool) -> Bool {
            guard let raw = qeli[key]?.trimmingCharacters(in: .whitespaces), !raw.isEmpty else {
                return fallback
            }
            switch raw.lowercased() {
            case "true", "1", "yes", "on": return true
            case "false", "0", "no", "off": return false
            default:
                badBools.append(key)
                return fallback
            }
        }
        let list: (String?) -> [String] = { value in
            value?.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
                .filter { !$0.isEmpty } ?? []
        }

        var config = VPNConfig(serverAddress: host, port: port)
        config.protocolName = qeli["proto"].nonEmpty ?? "tcp"
        config.connectionTimeoutSeconds = numAt("timeout", default: 30)
        config.reconnectEnabled = boolAt("reconnect", default: true)
        config.reconnectMaxRetries = numAt("reconnect_retries", default: -1)
        config.reconnectBaseDelaySeconds = numAt("reconnect_base_delay", default: 1)
        config.reconnectMaxDelaySeconds = numAt("reconnect_max_delay", default: 60)
        config.username = qeli["user"].nonEmpty ?? "client"
        config.password = qeli["pass"] ?? ""
        config.serverPublicKeyHex = qeli["key"].nonEmpty
        config.bindStaticToSession = boolAt("bind_static", default: true)
        config.mtu = numAt("mtu", default: 0)
        // Through boolAt like every other boolean: the old "anything not in the off-set is ON"
        // reading meant `mtu_probe = ture` silently enabled probing and was never recorded as a
        // typo. (Audit 2026-07-31.)
        config.mtuProbe = boolAt("mtu_probe", default: true)

        let fullTunnel = boolAt("gateway", default: true)
        config.routingMode = fullTunnel ? "full-tunnel" : "split-tunnel"
        config.addDefaultGateway = fullTunnel
        config.includeRoutes = list(qeli["include"])
        config.excludeRoutes = list(qeli["exclude"])
        config.routeLocalNetworks = boolAt("route_local", default: false)
        config.allowIPv6Leak = boolAt("allow_ipv6_leak", default: false)
        config.allowLAN = boolAt("allow_lan", default: false)
        // `dns` is a resolver LIST here and a MODE in the Rust/router client (`off` / `tunnel`
        // / `system`). Recognising the mode words was only half the job: they were mapped to
        // "no explicit resolvers", and the tunnel engine then treats that as "nothing chosen"
        // and installs the public fallback on a full tunnel — so `dns = off`, which means LEAVE
        // MY RESOLVER ALONE, sent every lookup to Cloudflare and Google instead. The mode is
        // now KEPT and honoured at connect time. (Audit 2026-08-02, §3.)
        if let raw = qeli["dns"], ["off", "system"].contains(raw.lowercased()) {
            config.dnsMode = raw.lowercased()
        }
        if let dns = qeli["dns"], !["off", "system", "tunnel"].contains(dns.lowercased()) {
            config.dnsServers = list(dns)
        }

        // Carried through untouched so re-saving a desktop config keeps its logging section.
        if let logging = sections["logging"] {
            config.loggingLevel = logging["level"].nonEmpty
            config.loggingFile = logging["file"].nonEmpty
            config.loggingTimeFormat = logging["time_format"].nonEmpty
        }

        config.wireMode = qeli["mode"].nonEmpty ?? "fake-tls"
        config.sni = qeli["sni"].nonEmpty
        config.realityShortID = qeli["reality_sid"].nonEmpty
        config.obfsKey = qeli["obfs_key"] ?? ""
        config.obfsFronting = qeli["front"].nonEmpty ?? "websocket"
        config.awgEnabled = boolAt("awg", default: false)
        config.awgJunkCount = numAt("jc", default: 0)
        config.awgJunkMin = numAt("jmin", default: 40)
        config.awgJunkMax = numAt("jmax", default: 300)
        config.quicEnabled = boolAt("quic", default: false)

        config.paddingEnabled = boolAt("padding", default: true)
        config.paddingMin = numAt("padding_min", default: 0)
        config.paddingMax = numAt("padding_max", default: 255)
        config.heartbeatEnabled = boolAt("heartbeat", default: true)
        config.heartbeatIntervalMilliseconds = numAt("heartbeat_interval", default: 15_000)
        config.heartbeatDataSize = numAt("heartbeat_size", default: 16)
        config.heartbeatJitterMilliseconds = numAt("heartbeat_jitter", default: 2_000)

        config.shapingEnabled = boolAt("shaping", default: false)
        config.shapingGapMeanMilliseconds = numAt("shaping_gap_mean", default: 700)
        config.shapingGapMinMilliseconds = numAt("shaping_gap_min", default: 40)
        config.shapingGapMaxMilliseconds = numAt("shaping_gap_max", default: 6_000)
        config.shapingBudgetBytesPerSecond = numAt("shaping_budget", default: 16_384)
        config.shapingMinSize = numAt("shaping_min_size", default: 64)
        config.shapingMaxSize = numAt("shaping_max_size", default: 1_024)
        config.shapingStealth = boolAt("shaping_stealth", default: false)
        config.shapingStealthRateMbps = numAt("shaping_stealth_mbps", default: 2)

        // Kept RAW, not coerced: `validate()` refuses an unknown value, the same way it does
        // for `proto` and `mode`. Coercing here silently turned `apps_mode = includ` into
        // "all" — the widest setting — so a typo broadened the tunnel instead of failing.
        // (Audit 2026-08-02, §10.)
        config.appsMode = qeli["apps_mode"]?.lowercased() ?? "all"
        config.apps = list(qeli["apps"])
        config.unparsedBooleanKeys = badBools
        config.duplicateKeys = dupKeys
        config.unparsedNumericKeys = badNums
        config.unknownKeys = qeli.keys
            .filter { !Self.knownINIKeys.contains($0.lowercased()) }
            .sorted()
        // Accepted but not modelled — kept so saving does not delete them.
        config.carriedKeys = qeli.filter { Self.carriedINIKeys.contains($0.key.lowercased()) }
        return config
    }

    static func fromJSON(_ text: String) throws -> VPNConfig {
        guard let data = text.data(using: .utf8),
              let root = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw VPNConfigError.invalid("profile JSON is invalid")
        }
        func dict(_ key: String, in parent: [String: Any] = root) -> [String: Any] {
            parent[key] as? [String: Any] ?? [:]
        }
        func string(_ key: String, in parent: [String: Any], default fallback: String = "") -> String {
            parent[key] as? String ?? fallback
        }
        // Numbers had the same door left open, and only booleans were closed.
        //
        // `(parent[key] as? NSNumber)?.intValue ?? fallback` swallowed anything that is not an
        // NSNumber and handed back the default, so `"port": "bad"` became 443 — a DIFFERENT
        // SERVER — and an unreadable limit became whatever the default happens to be, in
        // silence. That is exactly the failure the INI path was hardened against; the JSON
        // importer reaches it through another door. Present-but-unreadable is recorded, absent
        // is not. (Audit 2026-08-02, §6 of the follow-up.)
        var badJSONNumbers: [String] = []
        func int(_ key: String, in parent: [String: Any], default fallback: Int) -> Int {
            guard let raw = parent[key], !(raw is NSNull) else { return fallback }
            if let n = raw as? NSNumber, CFGetTypeID(n) != CFBooleanGetTypeID() {
                return n.intValue
            }
            // A JSON string holding digits is accepted: hand-written and
            // exported-from-elsewhere profiles quote numbers, and rejecting those would refuse
            // configs that have always worked.
            if let s = raw as? String, let parsed = Int(s.trimmingCharacters(in: .whitespaces)) {
                return parsed
            }
            badJSONNumbers.append(key)
            return fallback
        }
        // `(as? NSNumber)?.boolValue` accepted ANY number — `2` read as true — and silently
        // returned the default for a string or anything else: the same fail-open the INI path
        // had, through a different door. A key PRESENT but unreadable is recorded; an absent one
        // is not, which is what the default is for. (Audit 2026-08-01, §8.)
        var badJSONBools: [String] = []
        func bool(_ key: String, in parent: [String: Any], default fallback: Bool) -> Bool {
            guard let raw = parent[key], !(raw is NSNull) else { return fallback }
            if let n = raw as? NSNumber, CFGetTypeID(n) == CFBooleanGetTypeID() {
                return n.boolValue
            }
            if let s = raw as? String {
                switch s.trimmingCharacters(in: .whitespaces).lowercased() {
                case "true", "1", "yes", "on": return true
                case "false", "0", "no", "off": return false
                default: break
                }
            }
            badJSONBools.append(key)
            return fallback
        }
        func strings(_ key: String, in parent: [String: Any]) -> [String] {
            parent[key] as? [String] ?? []
        }

        let server = dict("server")
        let reconnect = dict("reconnect", in: server)
        let auth = dict("auth")
        let tun = dict("tun")
        let routing = dict("routing")
        let dns = dict("dns")
        let obfuscation = dict("obfuscation")
        let padding = dict("padding", in: obfuscation)
        let heartbeat = dict("heartbeat", in: obfuscation)
        let quic = dict("quic", in: obfuscation)
        let awg = dict("awg", in: obfuscation)
        // Canonical name is `traffic_shaping` with `idle_gap_*` fields — what the Rust
        // client, the server's AuthOK push and every exported profile use. This read
        // `shaping` / `gap_*`, which matches nothing the rest of the project emits, so a
        // canonical JSON profile imported here silently came back with shaping DEFAULTS: the
        // feature looked configured and was not. The short spelling is still accepted so
        // profiles written by older builds of this client keep loading.
        // (Audit 2026-07-29, #8.)
        let shaping: [String: Any] = {
            let canonical = dict("traffic_shaping", in: obfuscation)
            return canonical.isEmpty ? dict("shaping", in: obfuscation) : canonical
        }()

        var config = VPNConfig(
            serverAddress: string("address", in: server, default: string("address", in: root, default: "127.0.0.1")),
            port: int("port", in: server, default: int("port", in: root, default: 443))
        )
        config.protocolName = string("protocol", in: server, default: "tcp")
        config.connectionTimeoutSeconds = int("connection_timeout_secs", in: server, default: 30)
        config.reconnectEnabled = bool("enabled", in: reconnect, default: true)
        config.reconnectMaxRetries = int("max_retries", in: reconnect, default: -1)
        config.reconnectBaseDelaySeconds = int("base_delay_secs", in: reconnect, default: 1)
        config.reconnectMaxDelaySeconds = int("max_delay_secs", in: reconnect, default: 60)
        config.username = string("username", in: auth, default: string("username", in: root, default: "client"))
        config.password = string("password", in: auth, default: string("password", in: root))
        config.serverPublicKeyHex = string("server_public_key", in: auth).nonEmpty
        config.bindStaticToSession = bool("bind_static_to_session", in: auth, default: true)
        config.mtu = int("mtu", in: tun, default: 0)
        config.routingMode = string("mode", in: routing, default: "full-tunnel")
        config.addDefaultGateway = bool("add_default_gateway", in: routing, default: config.routingMode == "full-tunnel")
        config.includeRoutes = strings("include", in: routing)
        config.excludeRoutes = strings("exclude", in: routing)
        config.routeLocalNetworks = bool("route_local_networks", in: routing, default: false)
        config.allowIPv6Leak = bool("allow_ipv6_leak", in: routing, default: false)
        config.allowLAN = bool("allow_lan", in: routing, default: false)
        config.dnsServers = strings("servers", in: dns)
        // JSON keeps mode and servers apart, so it never had the flat INI's ambiguity — but
        // the mode still has to survive the import.
        // Kept RAW, not filtered: `validate()` refuses an unknown value. Silently dropping it
        // left `dnsMode` at "tunnel", so `"mode": "of"` sent every lookup through the tunnel
        // when the user asked for the exact opposite — a typo choosing the other branch, which
        // is the failure the INI path was hardened against. (Audit 2026-08-02, §6 of the
        // follow-up.)
        if let m = (dns["mode"] as? String)?.lowercased() {
            config.dnsMode = m
        }
        config.wireMode = string("mode", in: obfuscation, default: "fake-tls")
        config.obfsKey = string("obfs_key", in: obfuscation)
        config.obfsFronting = string("fronting", in: obfuscation, default: "websocket")
        config.sni = string("sni", in: obfuscation).nonEmpty
        config.realityShortID = string("reality_short_id", in: obfuscation).nonEmpty
        config.paddingEnabled = bool("enabled", in: padding, default: true)
        config.paddingMin = int("min_bytes", in: padding, default: 0)
        config.paddingMax = int("max_bytes", in: padding, default: 255)
        config.heartbeatEnabled = bool("enabled", in: heartbeat, default: true)
        config.heartbeatIntervalMilliseconds = int("interval_ms", in: heartbeat, default: 15_000)
        config.heartbeatDataSize = int("data_size_bytes", in: heartbeat, default: 16)
        config.heartbeatJitterMilliseconds = int("jitter_ms", in: heartbeat, default: 2_000)
        config.quicEnabled = bool("enabled", in: quic, default: false)
        config.awgEnabled = bool("enabled", in: awg, default: false)
        config.awgJunkCount = int("jc", in: awg, default: 0)
        config.awgJunkMin = int("jmin", in: awg, default: 40)
        config.awgJunkMax = int("jmax", in: awg, default: 300)
        config.shapingEnabled = bool("enabled", in: shaping, default: false)
        config.shapingGapMeanMilliseconds = int("idle_gap_mean_ms", in: shaping, default: int("gap_mean_ms", in: shaping, default: 700))
        config.shapingGapMinMilliseconds = int("idle_gap_min_ms", in: shaping, default: int("gap_min_ms", in: shaping, default: 40))
        config.shapingGapMaxMilliseconds = int("idle_gap_max_ms", in: shaping, default: int("gap_max_ms", in: shaping, default: 6_000))
        config.shapingBudgetBytesPerSecond = int("budget_bytes_per_sec", in: shaping, default: 16_384)
        config.shapingMinSize = int("min_size", in: shaping, default: 64)
        config.shapingMaxSize = int("max_size", in: shaping, default: 1_024)
        config.shapingStealth = bool("stealth", in: shaping, default: false)
        config.shapingStealthRateMbps = int("stealth_rate_mbps", in: shaping, default: 2)
        config.unparsedBooleanKeys = badJSONBools
        config.unparsedNumericKeys = badJSONNumbers
        return config
    }

    static func fromQeliURI(_ uri: String) throws -> VPNConfig {
        guard uri.hasPrefix("qeli://") else { throw VPNConfigError.invalid("not a qeli:// link") }
        var remainder = String(uri.dropFirst("qeli://".count))
        if let hash = remainder.firstIndex(of: "#") { remainder = String(remainder[..<hash]) }

        let query: String?
        if let question = remainder.firstIndex(of: "?") {
            query = String(remainder[remainder.index(after: question)...])
            remainder = String(remainder[..<question])
        } else {
            query = nil
        }

        let at = remainder.lastIndex(of: "@")
        let userInfo = at.map { String(remainder[..<$0]) }
        let endpoint = at.map { String(remainder[remainder.index(after: $0)...]) } ?? remainder
        let (host, port) = try parseEndpoint(endpoint)

        var config = VPNConfig(serverAddress: host, port: port)
        if let userInfo {
            if let colon = userInfo.firstIndex(of: ":") {
                config.username = percentDecode(String(userInfo[..<colon]))
                config.password = percentDecode(String(userInfo[userInfo.index(after: colon)...]))
            } else {
                config.username = percentDecode(userInfo)
            }
        }

        for item in query?.split(separator: "&", omittingEmptySubsequences: true) ?? [] {
            let parts = item.split(separator: "=", maxSplits: 1, omittingEmptySubsequences: false)
            let key = String(parts[0])
            let value = percentDecode(parts.count == 2 ? String(parts[1]) : "")
            switch key {
            case "proto": config.protocolName = value
            case "mode": config.wireMode = value
            case "key": config.serverPublicKeyHex = value.nonEmpty
            case "sni": config.sni = value.nonEmpty
            case "rsid": config.realityShortID = value.nonEmpty
            case "obfs": config.obfsKey = value
            case "front": config.obfsFronting = value.nonEmpty ?? "websocket"
            case "quic": config.quicEnabled = value == "1" || value.lowercased() == "true"
            case "awg": config.awgEnabled = value == "1" || value.lowercased() == "true"
            case "jc": config.awgJunkCount = Int(value) ?? 0
            case "jmin": config.awgJunkMin = Int(value) ?? 40
            case "jmax": config.awgJunkMax = Int(value) ?? 300
            // Out-of-range → auto, rather than rejecting the whole link in validate()
            // below. Matches the Rust `from_link` clamp; the Android client now does the
            // same, so one shared link no longer imports on one platform and fails on
            // another over a value the client would have ignored anyway.
            case "mtu": config.mtu = Int(value).flatMap { $0 == 0 || (Self.mtuMin...Self.mtuMax).contains($0) ? $0 : 0 } ?? 0
            default: break
            }
        }

        // Alias convenience: `mode=udp-quic` / `udp-obfs` fold transport+QUIC into the
        // wire mode. Split it back into proto + wire mode + quic — the same mapping the
        // Rust link parser applies (config/share.rs). Done AFTER the loop, not inside the
        // `mode` case, because `proto` may arrive later in the query and would otherwise
        // overwrite the transport the alias just implied.
        switch config.wireMode {
        case "udp-quic":
            config.protocolName = "udp"
            config.wireMode = "fake-tls"
            config.quicEnabled = true
        case "udp-obfs":
            config.protocolName = "udp"
            config.wireMode = "obfs"
        default:
            break
        }

        // Validate before handing the config back. Parsing alone accepted anything an
        // `Int` could hold, so `:0` and `:65536` produced a config that only failed much
        // later — and the reject tests, which call this method directly, passed them.
        try config.validate()
        return config
    }

    static func label(fromQeliURI uri: String) -> String? {
        guard let hash = uri.firstIndex(of: "#") else { return nil }
        return percentDecode(String(uri[uri.index(after: hash)...])).nonEmpty
    }

    func toINI(label: String? = nil) throws -> String {
        try validate()
        if let label, Self.containsForbiddenINICharacters(label) {
            throw VPNConfigError.invalid("profile label contains a forbidden line break or NUL character")
        }
        let endpoint = Self.formatEndpoint(host: serverAddress, port: port)
        var lines: [String] = []
        if let label = label?.trimmingCharacters(in: .whitespacesAndNewlines), !label.isEmpty {
            lines.append("# \(label.replacingOccurrences(of: "\n", with: " "))")
        }
        lines += [
            "[qeli]",
            "server = \(endpoint)",
            "proto = \(protocolName)",
            "user = \(username)",
            "pass = \(password)",
            "mode = \(wireMode)"
        ]
        if let value = serverPublicKeyHex { lines.append("key = \(value)") }
        if !bindStaticToSession { lines.append("bind_static = false") }
        if let value = sni { lines.append("sni = \(value)") }
        if let value = realityShortID { lines.append("reality_sid = \(value)") }
        if !obfsKey.isEmpty { lines.append("obfs_key = \(obfsKey)") }
        if obfsFronting != "websocket" { lines.append("front = \(obfsFronting)") }
        if quicEnabled { lines.append("quic = true") }
        if awgEnabled {
            lines += ["awg = true", "jc = \(awgJunkCount)", "jmin = \(awgJunkMin)", "jmax = \(awgJunkMax)"]
        }
        if mtu != 0 { lines.append("mtu = \(mtu)") }
        if !mtuProbe { lines.append("mtu_probe = false") }
        if !isFullTunnel { lines.append("gateway = false") }
        if !includeRoutes.isEmpty { lines.append("include = \(includeRoutes.joined(separator: ", "))") }
        if !excludeRoutes.isEmpty { lines.append("exclude = \(excludeRoutes.joined(separator: ", "))") }
        if routeLocalNetworks { lines.append("route_local = true") }
        if allowIPv6Leak { lines.append("allow_ipv6_leak = true") }
        if allowLAN { lines.append("allow_lan = true") }
        // One key, two meanings — mirroring the Rust client. A non-default MODE wins over the
        // server list: `dns = off` must survive a save/load round-trip, or re-saving a profile
        // would silently turn "leave my resolver alone" back into the public fallback.
        if dnsMode != "tunnel" {
            lines.append("dns = \(dnsMode)")
        } else if !dnsServers.isEmpty {
            lines.append("dns = \(dnsServers.joined(separator: ", "))")
        }
        if !paddingEnabled { lines.append("padding = false") }
        if paddingMin != 0 { lines.append("padding_min = \(paddingMin)") }
        if paddingMax != 255 { lines.append("padding_max = \(paddingMax)") }
        if !heartbeatEnabled { lines.append("heartbeat = false") }
        if heartbeatIntervalMilliseconds != 15_000 { lines.append("heartbeat_interval = \(heartbeatIntervalMilliseconds)") }
        if heartbeatDataSize != 16 { lines.append("heartbeat_size = \(heartbeatDataSize)") }
        if heartbeatJitterMilliseconds != 2_000 { lines.append("heartbeat_jitter = \(heartbeatJitterMilliseconds)") }
        if shapingEnabled { lines.append("shaping = true") }
        if shapingGapMeanMilliseconds != 700 { lines.append("shaping_gap_mean = \(shapingGapMeanMilliseconds)") }
        if shapingGapMinMilliseconds != 40 { lines.append("shaping_gap_min = \(shapingGapMinMilliseconds)") }
        if shapingGapMaxMilliseconds != 6_000 { lines.append("shaping_gap_max = \(shapingGapMaxMilliseconds)") }
        if shapingBudgetBytesPerSecond != 16_384 { lines.append("shaping_budget = \(shapingBudgetBytesPerSecond)") }
        if shapingMinSize != 64 { lines.append("shaping_min_size = \(shapingMinSize)") }
        if shapingMaxSize != 1_024 { lines.append("shaping_max_size = \(shapingMaxSize)") }
        if shapingStealth { lines.append("shaping_stealth = true") }
        if shapingStealthRateMbps != 2 { lines.append("shaping_stealth_mbps = \(shapingStealthRateMbps)") }
        if appsMode != "all" { lines.append("apps_mode = \(appsMode)") }
        if !apps.isEmpty { lines.append("apps = \(apps.joined(separator: ", "))") }
        if !reconnectEnabled { lines.append("reconnect = false") }
        if reconnectMaxRetries != -1 { lines.append("reconnect_retries = \(reconnectMaxRetries)") }
        if reconnectBaseDelaySeconds != 1 { lines.append("reconnect_base_delay = \(reconnectBaseDelaySeconds)") }
        if reconnectMaxDelaySeconds != 60 { lines.append("reconnect_max_delay = \(reconnectMaxDelaySeconds)") }
        if connectionTimeoutSeconds != 30 { lines.append("timeout = \(connectionTimeoutSeconds)") }
        // Re-emit the keys this port accepts but does not model, verbatim and in a stable
        // order. Without this, opening a CLI profile here and saving it deleted its hooks
        // (`post_up`/`post_down`), its TOFU setting and its routing policy — silently, and as
        // a side effect of merely opening it. (Audit 2026-08-02, §4 of the follow-up.)
        for key in carriedKeys.keys.sorted() {
            if let value = carriedKeys[key] { lines.append("\(key) = \(value)") }
        }
        // Re-emit [logging] so a desktop/router client.conf survives an edit on the phone.
        if loggingLevel?.nonEmpty != nil || loggingFile?.nonEmpty != nil || loggingTimeFormat?.nonEmpty != nil {
            lines.append("")
            lines.append("[logging]")
            if let value = loggingLevel?.nonEmpty { lines.append("level = \(value)") }
            if let value = loggingFile?.nonEmpty { lines.append("file = \(value)") }
            if let value = loggingTimeFormat?.nonEmpty { lines.append("time_format = \(value)") }
        }
        return lines.joined(separator: "\n") + "\n"
    }

    func toQeliURI(label: String? = nil) -> String {
        let auth = "\(Self.percentEncode(username)):\(Self.percentEncode(password))@"
        var query = ["proto=\(Self.percentEncode(protocolName))", "mode=\(Self.percentEncode(wireMode))"]
        if let key = serverPublicKeyHex { query.append("key=\(Self.percentEncode(key))") }
        if let sni { query.append("sni=\(Self.percentEncode(sni))") }
        if let realityShortID { query.append("rsid=\(Self.percentEncode(realityShortID))") }
        if !obfsKey.isEmpty { query.append("obfs=\(Self.percentEncode(obfsKey))") }
        if obfsFronting != "websocket" { query.append("front=\(Self.percentEncode(obfsFronting))") }
        if quicEnabled { query.append("quic=1") }
        if awgEnabled {
            query += ["awg=1", "jc=\(awgJunkCount)", "jmin=\(awgJunkMin)", "jmax=\(awgJunkMax)"]
        }
        if mtu != 0 { query.append("mtu=\(mtu)") }
        let fragment = label?.nonEmpty.map { "#\(Self.percentEncode($0))" } ?? ""
        return "qeli://\(auth)\(Self.formatEndpoint(host: serverAddress, port: port))?\(query.joined(separator: "&"))\(fragment)"
    }

    private static func parseINI(
        _ text: String, duplicates: inout [String]
    ) -> [String: [String: String]] {
        var result: [String: [String: String]] = [:]
        var section: String?
        for rawLine in text.components(separatedBy: .newlines) {
            let line = rawLine.trimmingCharacters(in: .whitespaces)
            if line.isEmpty || line.hasPrefix("#") || line.hasPrefix(";") { continue }
            if line.hasPrefix("["), line.hasSuffix("]") {
                let body = line.dropFirst().dropLast().trimmingCharacters(in: .whitespaces)
                section = body.split(separator: ":", maxSplits: 1).first.map(String.init)
                if let section, result[section] == nil { result[section] = [:] }
                continue
            }
            guard let section, let equals = line.firstIndex(of: "=") else { continue }
            let key = line[..<equals].trimmingCharacters(in: .whitespaces)
            var value = line[line.index(after: equals)...].trimmingCharacters(in: .whitespaces)
            if value.count >= 2, value.hasPrefix("\""), value.hasSuffix("\"") {
                value = String(value.dropFirst().dropLast())
            }
            if !key.isEmpty {
                // Keep LAST-wins, so a file that never had a duplicate parses exactly as it did
                // before, and record the ambiguity for validate() to refuse.
                let qualified = "\(section).\(key)"
                if result[section, default: [:]][key] != nil, !duplicates.contains(qualified) {
                    duplicates.append(qualified)
                }
                result[section, default: [:]][key] = value
            }
        }
        return result
    }

    private static func parseEndpoint(_ endpoint: String) throws -> (String, Int) {
        if endpoint.hasPrefix("[") {
            guard let close = endpoint.firstIndex(of: "]"),
                  endpoint.index(after: close) < endpoint.endIndex,
                  endpoint[endpoint.index(after: close)] == ":",
                  let port = Int(endpoint[endpoint.index(close, offsetBy: 2)...]) else {
                throw VPNConfigError.invalid("IPv6 endpoint must be [host]:port")
            }
            return (String(endpoint[endpoint.index(after: endpoint.startIndex)..<close]), port)
        }
        guard let colon = endpoint.lastIndex(of: ":"),
              colon > endpoint.startIndex,
              let port = Int(endpoint[endpoint.index(after: colon)...]) else {
            throw VPNConfigError.invalid("server must be host:port")
        }
        return (String(endpoint[..<colon]), port)
    }

    private static func formatEndpoint(host: String, port: Int) -> String {
        host.contains(":") && !host.hasPrefix("[") ? "[\(host)]:\(port)" : "\(host):\(port)"
    }

    private static let unreserved: CharacterSet = {
        var set = CharacterSet.alphanumerics
        set.insert(charactersIn: "-._~")
        return set
    }()

    private static let forbiddenINICharacters = CharacterSet(charactersIn: "\r\n\0")

    private static func containsForbiddenINICharacters(_ value: String) -> Bool {
        value.rangeOfCharacter(from: forbiddenINICharacters) != nil
    }

    private static func percentEncode(_ value: String) -> String {
        value.addingPercentEncoding(withAllowedCharacters: unreserved) ?? value
    }

    private static func percentDecode(_ value: String) -> String {
        value.removingPercentEncoding ?? value
    }
}

enum VPNConfigError: LocalizedError, Equatable {
    case invalid(String)

    var errorDescription: String? {
        switch self { case .invalid(let message): return message }
    }
}

private extension Optional where Wrapped == String {
    var nonEmpty: String? {
        guard let self, !self.isEmpty else { return nil }
        return self
    }
}

private extension String {
    var nonEmpty: String? { isEmpty ? nil : self }
}
