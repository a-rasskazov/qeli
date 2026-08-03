using System.ComponentModel;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

namespace Qeli.Shared.Model;

/// <summary>Reachability of a profile's server, shown as a colored dot on the card.</summary>
public enum ProfileReachability { Unknown, Checking, Reachable, Unreachable }

/// <summary>
/// Full qeli client configuration. Mirrors the relevant fields of the Rust
/// ClientConfig and the Android VpnConfig. Built from the simple UI fields, an
/// imported JSON config (FromJson) or a qeli:// share link (FromQeliUri).
/// </summary>
public sealed class VpnConfig : INotifyPropertyChanged
{
    [field: JsonIgnore]
    public event PropertyChangedEventHandler? PropertyChanged;

    private ProfileReachability _reachability = ProfileReachability.Unknown;
    private int? _latencyMs;

    /// <summary>Live server reachability (UI only); raises change notifications.</summary>
    [JsonIgnore]
    public ProfileReachability Reachability
    {
        get => _reachability;
        set
        {
            if (_reachability == value) return;
            _reachability = value;
            Notify(nameof(Reachability));
            Notify(nameof(LatencyText));
        }
    }

    /// <summary>Last measured TCP latency in ms (UI only).</summary>
    [JsonIgnore]
    public int? LatencyMs
    {
        get => _latencyMs;
        set { _latencyMs = value; Notify(nameof(LatencyText)); }
    }

    /// <summary>Badge text for the profile card: "38 ms" / "offline" / "…" / "".</summary>
    [JsonIgnore]
    public string LatencyText => _reachability switch
    {
        ProfileReachability.Reachable => _latencyMs is int ms ? $"{ms} ms" : "ok",
        ProfileReachability.Unreachable => Qeli.Shared.Loc.T("Offline"),
        ProfileReachability.Checking => "…",
        _ => "",
    };

    private void Notify(string name) => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));

    // server
    public string ServerAddress { get; init; } = "127.0.0.1";
    public int Port { get; init; } = 443;
    public string Protocol { get; init; } = "tcp";       // "tcp" | "udp"
    public long ConnectionTimeoutSecs { get; init; } = 30;
    // OpenVPN-parity outbound-socket binding (issue #69). LocalAddress = bind the carrier
    // socket to a specific local IP (multi-homed host / pick egress NIC; OpenVPN `local`);
    // LocalPort = bind to a fixed local source port (OpenVPN `lport`) for firewall rules.
    // Empty / 0 = OS default (any address, ephemeral port).
    public string? LocalAddress { get; init; }
    public int LocalPort { get; init; }
    // reconnect
    public bool ReconnectEnabled { get; init; } = true;
    public int ReconnectMaxRetries { get; init; } = -1;
    public long ReconnectBaseDelaySecs { get; init; } = 1;
    public long ReconnectMaxDelaySecs { get; init; } = 60;
    // auth
    public string Username { get; init; } = "client";
    public string Password { get; init; } = "";
    public string? ServerPublicKeyHex { get; init; }     // pinned static key (hex), null = TOFU
    // H-1: bind data keys to the server static identity (folds es into the KDF).
    // Must match the server's auth.bind_static_to_session and requires a pinned key.
    // Default TRUE (secure-by-default since 0.7.1); wire-breaking — set false (or
    // pass bind_static=false) to talk to a legacy 0.7.0 / TOFU server.
    public bool BindStaticToSession { get; init; } = true;
    // tun
    // 0 = auto: adopt the MTU the server pushes at auth (falls back to 1400 if the
    // server is too old to push one). A value > 0 is an explicit override.
    public int Mtu { get; init; } = 0;
    // Active UDP path-MTU probing when Mtu == 0 (default on; kill switch = false). No
    // effect on TCP transports (the OS does PMTUD there) or when Mtu > 0 (explicit).
    public bool MtuProbe { get; init; } = true;
    // routing
    public string RoutingMode { get; init; } = "full-tunnel";
    public bool AddDefaultGateway { get; init; } = true;
    public List<string> IncludeRoutes { get; init; } = new();
    public List<string> ExcludeRoutes { get; init; } = new();
    public bool RouteLocalNetworks { get; init; }
    // Extra split-tunnel routes loaded from a FILE of CIDRs (one per line, '#'/';'
    // comments allowed) — OpenVPN's route-include-from-file. Merged with IncludeRoutes at
    // tunnel setup. Empty = none.
    public string? RouteFile { get; init; }
    // TUN interface routing metric (OpenVPN `route-metric` / a lower value = higher
    // priority). 0 = OS default. Applied to the tunnel adapter after addressing.
    public int InterfaceMetric { get; init; }
    // Force a specific TUN adapter name (OpenVPN `dev-node`). Windows: names the Wintun
    // adapter instead of the auto-derived Qeli-<hash>. Empty = auto.
    public string? DevNode { get; init; }
    // OpenVPN-style persist-tun: keep the TUN adapter + routes UP across reconnects
    // (until the user disconnects) instead of tearing them down and recreating them each
    // attempt. Avoids the adapter flicker + the brief route gap on every reconnect, and
    // fails closed (no physical-NIC leak) during the reconnect window. Off by default.
    public bool PersistTun { get; init; }
    // #13: enable OS IP forwarding on THIS node (no NAT) so a LAN behind the client is
    // routable through the tunnel (site-to-site). macOS: net.inet.ip.forwarding=1; Windows:
    // per-interface netsh forwarding (best-effort). Mirrors the Rust client's routing.forward.
    public bool Forward { get; init; }
    // Firewall kill-switch (full-tunnel only): block ALL egress except the tunnel,
    // the server, DNS and DHCP while connected, so a tunnel drop can't leak traffic
    // onto the physical NIC during reconnect. Platform-specific (Win: Windows
    // Firewall default-block + allow rules; mac: pf anchor). Default off.
    public bool KillSwitch { get; init; }
    // Full-tunnel captures IPv6 into the tunnel (the server is IPv4-only, so it is black-holed)
    // to close the classic dual-stack IPv6 leak. Set true to OPT OUT — a dual-stack user who
    // wants native IPv6, accepting that it bypasses the tunnel. Default off (fail-closed);
    // mirrors the Rust client's `allow_ipv6_leak`.
    public bool AllowIpv6Leak { get; init; }
    // dns — empty by default so a config the user never gave DNS round-trips WITHOUT a
    // `dns = 1.1.1.1, 8.8.8.8` line and the server-pushed DNS (dns.push_servers) is honoured.
    // The public-resolver fallback moved to connect time (SetupTun): explicit > server-pushed
    // > 1.1.1.1/8.8.8.8 (full-tunnel only). See the per-platform SetupTun DNS block.
    public List<string> DnsServers { get; init; } = new();

    /// <summary>DNS handling mode, mirroring `dns.mode` in the Rust client: `tunnel` (default —
    /// install resolvers reachable through the tunnel), `off` or `system` (leave the device
    /// resolver alone).
    ///
    /// The flat INI spells the mode and the server list with the SAME key — `dns = off` versus
    /// `dns = 1.1.1.1, 8.8.8.8` — so a shared desktop/router profile carries a value this port
    /// used to discard. Discarding it was not neutral: with no explicit resolvers `SetupTun`
    /// installs the public fallback on a full tunnel, so `off` produced exactly the behaviour
    /// it asks to prevent. (Audit 2026-08-02, §3.)</summary>
    public string DnsMode { get; init; } = "tunnel";
    // obfuscation
    public string WireMode { get; init; } = "fake-tls";  // "fake-tls" | "obfs" | "reality-tls" | "plain"
    public string ObfsKey { get; init; } = "";
    // obfs anti-FET fronting: "websocket" (default) wraps the nonce exchange in a
    // WebSocket Upgrade handshake; "none" is the legacy raw nonce. Must match the
    // server. Mirrors ClientObfuscationConfig::fronting (Rust) / VpnConfig.obfsFronting (Android).
    public string ObfsFronting { get; init; } = "websocket";
    // F2 AmneziaWG-style pre-handshake junk (obfs mode). OFF by default → zero extra
    // bytes on the wire (byte-identical to the pre-F2 wire). Both ends MUST agree on
    // AwgJc (the junk-record count); AwgJmin/AwgJmax bound each record's random length
    // and are sender-only. Mirrors the Rust AwgParams / obf.awg.* config.
    public bool AwgEnabled { get; init; }
    public uint AwgJc { get; init; }              // record count (cap 128); 0 = disabled
    public ushort AwgJmin { get; init; } = 40;    // min junk-record length
    public ushort AwgJmax { get; init; } = 300;   // max junk-record length (jmin<=jmax<=1400)
    public bool QuicEnabled { get; init; }
    public string? Sni { get; init; }
    // REALITY short_id (hex) — pairs with ServerPublicKeyHex to seal the auth
    // token into the realtls ClientHello (WireMode = "reality-tls").
    public string? RealityShortId { get; init; }
    // padding
    public bool PaddingEnabled { get; init; } = true;
    /// <summary>Keys whose boolean value was neither true-ish nor false-ish — `gateway = ture`.
    ///
    /// Carried instead of being resolved at parse time because the ORIGINAL STRING IS LOST once
    /// a bool is produced, so nothing downstream could tell a typo from a deliberate `false`.
    /// That mattered: every unknown value read as `false`, so <c>kill_switch = ture</c> silently
    /// disabled the kill switch and <c>bind_static = ture</c> silently dropped the static-key
    /// binding — a security downgrade with no message anywhere.
    ///
    /// Parsing still SUCCEEDS (an editor must be able to open a bad profile to fix it);
    /// <see cref="Validate"/> is what refuses. (Audit 2026-07-31.)</summary>
    public IReadOnlyList<string> UnparsedBooleanKeys { get; init; } = Array.Empty<string>();

    /// <summary>A key that appears twice and is read as a SINGLE value makes the config ambiguous, and the implementations resolved it differently: this parser folds entries into a map and keeps the LAST, while the Rust client takes the FIRST. Two `server` lines therefore sent the Rust client to one host and every GUI client to another, from one file, with nothing reported. Recorded rather than resolved — picking a winner still leaves the others disagreeing. (Audit 2026-08-01, §7.)</summary>
    public IReadOnlyList<string> DuplicateKeys { get; init; } = Array.Empty<string>();

    /// <summary>Every `[qeli]` key any qeli client understands — the union across the four
    /// ports, NOT just the ones this one reads.
    ///
    /// The distinction is the whole point. A key this port ignores is not necessarily a typo:
    /// `keepalive`, `post_up`, `exit_node` and friends are real settings the Rust client acts
    /// on, and a desktop profile carrying them must still open here (it is preserved verbatim
    /// on re-save via the extra-key carry). Only a name NOTHING understands is a typo, and
    /// that is what gets reported — a misspelled `gatway = true` silently leaving the tunnel
    /// split is the failure this catches.
    ///
    /// Kept in sync by `RoundTripKeysAreAllKnown` in the conformance suite, which asserts that
    /// everything `ToIni` emits appears here.</summary>
    /// <summary>Keys this port ACCEPTS but does not model — read into <see cref="CarriedKeys"/>
    /// and written back verbatim, so opening and saving a profile does not strip them.</summary>
    /// <remarks>
    /// They are on the allowlist because a profile carrying them must open here; they are in
    /// THIS list because accepting a key without keeping it is how the open-and-save round trip
    /// silently deleted hooks, security settings and — for the mobile keys — the whole per-app
    /// selection. Allowlisting alone was the first half of the fix and, on its own, the more
    /// dangerous half: it makes the profile open, which is exactly what leads someone to save
    /// it. (Audit 2026-08-02, §4 of the follow-up; Android got both halves first.)
    /// <para>
    /// Declared BEFORE <c>KnownIniKeys</c>, which folds it in — static initialisers run in
    /// declaration order, so the other way round hands <c>Union</c> a null set at class load.
    /// </para>
    /// </remarks>
    public static readonly HashSet<string> CarriedIniKeys = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
    {
        // Understood by the RUST client only, and documented as such — docs/ru/CONFIG.md
        // "Что пушем НЕ передаётся" lists these as client file-only keys.
        "allow_unpinned_tofu", "autostart", "dev_attach", "dns_servers", "exit_node",
        "gateway_nat", "keepalive", "lan_subnet", "post_down", "post_up", "tcp_nodelay",
        // Socket buffers (Linux-only in the Rust client) and the headless password sources.
        "password_command", "password_file", "recv_buffer_size", "send_buffer_size",
        // Understood by the MOBILE ports only (per-app tunnelling, allow-LAN). Desktop has no
        // per-app split, so `ToIni` never wrote them — which is exactly why
        // `RoundTripKeysAreAllKnown` could not catch their absence: it only checks that what
        // this port WRITES is accepted back. Now they are carried, so a profile that goes
        // phone → desktop → phone keeps its app selection instead of losing it in the middle.
        "allow_lan", "apps", "apps_mode",
    };

    private static readonly HashSet<string> KnownIniKeys = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
    {
        // Read by this port.
        "allow_ipv6_leak", "awg", "bind_static", "dev", "dev_node", "dns", "exclude", "forward",
        "front", "gateway", "heartbeat", "heartbeat_interval", "heartbeat_jitter",
        "heartbeat_size", "include", "jc", "jmax", "jmin", "key", "kill_switch", "local",
        "lport", "metric", "mode", "mtu", "mtu_probe", "name", "obfs_key", "padding",
        "padding_max", "padding_min", "pass", "persist_tun", "proto", "quic", "reality_sid",
        "reconnect", "reconnect_base_delay", "reconnect_max_delay", "reconnect_retries",
        "route_file", "route_local", "server", "shaping", "shaping_budget", "shaping_gap_max",
        "shaping_gap_mean", "shaping_gap_min", "shaping_max_size", "shaping_min_size",
        "shaping_stealth", "shaping_stealth_mbps", "sni", "timeout", "user",
    }.Union(CarriedIniKeys).ToHashSet(StringComparer.OrdinalIgnoreCase);

    /// <summary>`[qeli]` keys no qeli client understands — i.e. misspellings. The setting they
    /// were meant to change silently keeps its default, which is how `gatway = true` left a
    /// tunnel split with nothing said. Reported, not resolved; Validate() refuses.
    /// (Audit 2026-08-01, §14.)</summary>
    public IReadOnlyList<string> UnknownKeys { get; init; } = Array.Empty<string>();

    /// <summary>Numeric fields whose value could not be parsed (or was out of range), which
    /// used to fall back to a default in silence — the same failure mode the boolean handling
    /// already fixed. `server = host:notnum` became `host:443`, i.e. a different server, with
    /// nothing said anywhere. Parsing still succeeds so an editor can open the profile;
    /// Validate() is what refuses. (Audit 2026-08-01, §P2.)</summary>
    public IReadOnlyList<string> UnparsedNumericKeys { get; init; } = Array.Empty<string>();

    /// <summary>`[qeli]` keys accepted but not modelled (<see cref="CarriedIniKeys"/>), kept
    /// verbatim so a save does not delete them. Re-emitted by ToIni() after the modelled
    /// keys.</summary>
    public IReadOnlyDictionary<string, string> CarriedKeys { get; init; }
        = new Dictionary<string, string>();

    public int PaddingMin { get; init; }
    public int PaddingMax { get; init; } = 255;
    // heartbeat
    public bool HeartbeatEnabled { get; init; } = true;
    public long HeartbeatIntervalMs { get; init; } = 15000;
    public int HeartbeatDataSize { get; init; } = 16;
    public long HeartbeatJitterMs { get; init; } = 2000;
    // flow shaping (idle cover traffic; DPI-AUDIT 6.1/6.2). Normally pushed from
    // the server. Defaults mirror the Rust TrafficShapingConfig.
    public bool ShapingEnabled { get; init; }
    public long ShapingGapMeanMs { get; init; } = 700;
    public long ShapingGapMinMs { get; init; } = 40;
    public long ShapingGapMaxMs { get; init; } = 6000;
    public int ShapingBudgetBytesPerSec { get; init; } = 16384;
    public int ShapingMinSize { get; init; } = 64;
    public int ShapingMaxSize { get; init; } = 1024;
    // Stealth (Phase 2): rate-cap the data plane + cover under load. TCP-only.
    public bool ShapingStealth { get; init; }
    public int ShapingStealthRateMbps { get; init; } = 2;

    // Optional display label (UI only).
    public string? Name { get; set; }

    /// <summary>Stable unique profile id (GUID hex). Profiles are referenced by this
    /// in app settings (service / auto-connect) instead of by DisplayName — two
    /// accounts on the SAME server share a DisplayName, so a name-based lookup would
    /// silently pick the wrong one (connect as user2 when user3 was chosen). Persisted;
    /// an old profile without one gets a fresh id on first load and is saved back.</summary>
    public string Id { get; set; } = Guid.NewGuid().ToString("N");

    [JsonIgnore]
    public string DisplayName =>
        // A distinct label wins; otherwise fall back to "server (user)" so two accounts
        // on the same server are DISTINGUISHABLE in the list and settings dropdowns
        // (the bare ServerAddress collided). Imported INI configs default Name to the
        // host, so treat Name == ServerAddress as "no distinct label" too.
        (!string.IsNullOrWhiteSpace(Name) && Name != ServerAddress)
            ? Name!
            : $"{ServerAddress} ({Username})";

    [JsonIgnore]
    public string Endpoint => $"{ServerAddress}:{Port} · {Protocol.ToUpperInvariant()} · {WireMode}";

    [JsonIgnore]
    public bool IsUdp => Protocol.Equals("udp", StringComparison.OrdinalIgnoreCase);

    [JsonIgnore]
    /// <summary>`all` counts too. Validate() accepts `split-tunnel | full-tunnel | all` (the
    /// Rust client's set, see client/route.rs), but this only compared against `full-tunnel` —
    /// so a perfectly valid `routing.mode = "all"` profile validated and then ran as a SPLIT
    /// tunnel, quietly sending everything outside the VPN past it. (Audit 2026-07-31, §2.)</summary>
    public bool IsFullTunnel =>
        AddDefaultGateway
        || RoutingMode.Equals("full-tunnel", StringComparison.OrdinalIgnoreCase)
        || RoutingMode.Equals("all", StringComparison.OrdinalIgnoreCase);

    /// <summary>Clone applying server-pushed heartbeat + flow-shaping params after auth.</summary>
    public VpnConfig WithPushedObf(bool hbEnabled, long hbIntervalMs, long hbJitterMs, int hbDataSize,
        bool shEnabled, long shGapMeanMs, long shGapMinMs, long shGapMaxMs,
        int shBudget, int shMinSize, int shMaxSize,
        bool shStealth, int shStealthRateMbps) => new()
    {
        ServerAddress = ServerAddress, Port = Port, Protocol = Protocol,
        ConnectionTimeoutSecs = ConnectionTimeoutSecs,
        LocalAddress = LocalAddress, LocalPort = LocalPort,
        RouteFile = RouteFile, InterfaceMetric = InterfaceMetric, DevNode = DevNode,
        ReconnectEnabled = ReconnectEnabled, ReconnectMaxRetries = ReconnectMaxRetries,
        ReconnectBaseDelaySecs = ReconnectBaseDelaySecs, ReconnectMaxDelaySecs = ReconnectMaxDelaySecs,
        Username = Username, Password = Password, ServerPublicKeyHex = ServerPublicKeyHex,
        BindStaticToSession = BindStaticToSession,
        Mtu = Mtu, MtuProbe = MtuProbe, RoutingMode = RoutingMode, AddDefaultGateway = AddDefaultGateway,
        IncludeRoutes = IncludeRoutes, ExcludeRoutes = ExcludeRoutes, RouteLocalNetworks = RouteLocalNetworks,
        PersistTun = PersistTun, KillSwitch = KillSwitch, AllowIpv6Leak = AllowIpv6Leak, Forward = Forward,
        DnsServers = DnsServers, DnsMode = DnsMode, WireMode = WireMode, ObfsKey = ObfsKey, ObfsFronting = ObfsFronting,
        AwgEnabled = AwgEnabled, AwgJc = AwgJc, AwgJmin = AwgJmin, AwgJmax = AwgJmax,
        QuicEnabled = QuicEnabled, Sni = Sni,
        RealityShortId = RealityShortId,
        PaddingEnabled = PaddingEnabled, PaddingMin = PaddingMin, PaddingMax = PaddingMax,
        HeartbeatEnabled = hbEnabled, HeartbeatIntervalMs = hbIntervalMs,
        HeartbeatDataSize = hbDataSize, HeartbeatJitterMs = hbJitterMs,
        ShapingEnabled = shEnabled, ShapingGapMeanMs = shGapMeanMs, ShapingGapMinMs = shGapMinMs,
        ShapingGapMaxMs = shGapMaxMs, ShapingBudgetBytesPerSec = shBudget,
        ShapingMinSize = shMinSize, ShapingMaxSize = shMaxSize,
        ShapingStealth = shStealth, ShapingStealthRateMbps = shStealthRateMbps,
        Name = Name, Id = Id,
    };

    /// <summary>Clone applying the fields the profile editor's FORM edits, preserving every
    /// other field from `this` (OpenVPN local/lport/dev_node/metric/route_file/persist_tun,
    /// kill-switch, AWG, reconnect, shaping, Id, …). The editor rebuilds a config on Save;
    /// without this, any field with no form control — e.g. set via the manual INI editor or
    /// import — was silently dropped (issue #69).</summary>
    /// The INI keys whose booleans the editor FORM supplies directly. A value the user picks in
    /// the form replaces whatever unparseable text was there, so its typo marker must be
    /// cleared; every other key keeps its marker because nothing in the form touched it.
    private static readonly string[] EditorControlledBooleanKeys =
    {
        "quic", "gateway", "route_local", "padding", "heartbeat",
    };

    public VpnConfig WithEditorFields(
        string? name, string serverAddress, int port, string protocol, string wireMode,
        string obfsKey, string obfsFronting, string? realityShortId, string? sni, bool quicEnabled,
        string username, string password, string? serverPublicKeyHex,
        string routingMode, bool addDefaultGateway, bool routeLocalNetworks,
        int mtu, List<string> dnsServers,
        bool paddingEnabled, int paddingMin, int paddingMax,
        bool heartbeatEnabled, long heartbeatIntervalMs, long heartbeatJitterMs) => new()
    {
        // ── form-edited fields (from params) ──
        ServerAddress = serverAddress, Port = port, Protocol = protocol, WireMode = wireMode,
        ObfsKey = obfsKey, ObfsFronting = obfsFronting, RealityShortId = realityShortId,
        Sni = sni, QuicEnabled = quicEnabled,
        Username = username, Password = password, ServerPublicKeyHex = serverPublicKeyHex,
        RoutingMode = routingMode, AddDefaultGateway = addDefaultGateway, RouteLocalNetworks = routeLocalNetworks,
        Mtu = mtu, DnsServers = dnsServers, DnsMode = DnsMode,
        PaddingEnabled = paddingEnabled, PaddingMin = paddingMin, PaddingMax = paddingMax,
        HeartbeatEnabled = heartbeatEnabled, HeartbeatIntervalMs = heartbeatIntervalMs, HeartbeatJitterMs = heartbeatJitterMs,
        Name = name,
        // ── preserved from `this` (no form control) ──
        Id = Id, ConnectionTimeoutSecs = ConnectionTimeoutSecs,
        LocalAddress = LocalAddress, LocalPort = LocalPort,
        RouteFile = RouteFile, InterfaceMetric = InterfaceMetric, DevNode = DevNode,
        ReconnectEnabled = ReconnectEnabled, ReconnectMaxRetries = ReconnectMaxRetries,
        ReconnectBaseDelaySecs = ReconnectBaseDelaySecs, ReconnectMaxDelaySecs = ReconnectMaxDelaySecs,
        BindStaticToSession = BindStaticToSession, MtuProbe = MtuProbe,
        IncludeRoutes = IncludeRoutes, ExcludeRoutes = ExcludeRoutes,
        PersistTun = PersistTun, KillSwitch = KillSwitch, AllowIpv6Leak = AllowIpv6Leak, Forward = Forward,
        AwgEnabled = AwgEnabled, AwgJc = AwgJc, AwgJmin = AwgJmin, AwgJmax = AwgJmax,
        HeartbeatDataSize = HeartbeatDataSize,
        ShapingEnabled = ShapingEnabled, ShapingGapMeanMs = ShapingGapMeanMs, ShapingGapMinMs = ShapingGapMinMs,
        ShapingGapMaxMs = ShapingGapMaxMs, ShapingBudgetBytesPerSec = ShapingBudgetBytesPerSec,
        ShapingMinSize = ShapingMinSize, ShapingMaxSize = ShapingMaxSize,
        ShapingStealth = ShapingStealth, ShapingStealthRateMbps = ShapingStealthRateMbps,
        // Carried, MINUS whatever this form just rewrote.
        //
        // Carrying it wholesale was wrong in the other direction: the user fixes the offending
        // checkbox, saves, and the profile stays rejected forever with no way out of the UI.
        // Dropping it wholesale is the original bug — the manual editor would LAUNDER a typo,
        // since Save rebuilds the config and Validate() then sees a clean one with the setting
        // silently off. The form supplies real values for the booleans below, so those keys are
        // genuinely resolved and only the rest must survive. (Audit 2026-08-01, §10.)
        UnparsedBooleanKeys = UnparsedBooleanKeys
            .Where(k => !EditorControlledBooleanKeys.Contains(k))
            .ToArray(),
        // DuplicateKeys is deliberately NOT carried (it defaults to empty). Unlike a bool typo,
        // a duplicate cannot survive this call: the parse already collapsed the key to one
        // value, and saving rewrites the file with one line per key. The ambiguity is genuinely
        // gone, so carrying the marker would reject a profile that is now fine.
    };

    // REMOVED: ToConfigJson(). It had no call sites anywhere in the tree, and what it
    // produced was wrong: `routing.mode` was hardcoded to "full-tunnel" with
    // `add_default_gateway: true` regardless of the profile's real routing, and it
    // dropped most of the fields FromJson reads back (kill-switch, persist-tun,
    // include/exclude routes, reconnect, shaping, heartbeat, bind_static, mtu_probe…).
    // Anyone who called it would have silently rewritten a split-tunnel profile into a
    // full-tunnel one. Deleted rather than half-fixed: writing ~30 fields of untested
    // serialization for a method nobody calls just moves the trap. Reinstate it against
    // FromJson field-by-field, with a round-trip test, if a caller ever needs it. (Shared)
    /// <summary>Bracket-wrap a bare IPv6 literal for a URI authority (RFC 3986:
    /// <c>qeli://user@[2001:db8::1]:443</c>); IPv4 / hostnames pass through unchanged.</summary>
    private static string UriHost(string host) =>
        host.Contains(':') && !host.StartsWith('[') ? $"[{host}]" : host;

    /// <summary>Build a compact qeli:// share link (inverse of FromQeliUri).</summary>
    public string ToQeliUri()
    {
        var sb = new StringBuilder("qeli://");
        sb.Append(Uri.EscapeDataString(Username));
        if (!string.IsNullOrEmpty(Password)) sb.Append(':').Append(Uri.EscapeDataString(Password));
        sb.Append('@').Append(UriHost(ServerAddress)).Append(':').Append(Port);

        var q = new List<string> { $"proto={Protocol}", $"mode={WireMode}" };
        if (!string.IsNullOrEmpty(ServerPublicKeyHex)) q.Add($"key={ServerPublicKeyHex}");
        if (!string.IsNullOrEmpty(Sni)) q.Add($"sni={Uri.EscapeDataString(Sni)}");
        if (!string.IsNullOrEmpty(RealityShortId)) q.Add($"rsid={Uri.EscapeDataString(RealityShortId)}");
        if (!string.IsNullOrEmpty(ObfsKey)) q.Add($"obfs={Uri.EscapeDataString(ObfsKey)}");
        // anti-FET fronting. FromQeliUri already read this, but ToQeliUri never wrote it:
        // an obfs profile with `front=none` shared from the desktop came back as the
        // default `websocket` on import — a different framing, so the tunnel never
        // handshakes. Emitted only when it diverges from the default, matching Rust
        // (config/client.rs: `.filter(|s| s != "websocket")`).
        if (!string.IsNullOrEmpty(ObfsFronting) && ObfsFronting != "websocket")
            q.Add($"front={Uri.EscapeDataString(ObfsFronting)}");
        // F2 AmneziaWG junk: emit only when enabled (off = byte-identical, no params).
        if (AwgEnabled)
        {
            q.Add("awg=1");
            q.Add($"jc={AwgJc}");
            q.Add($"jmin={AwgJmin}");
            q.Add($"jmax={AwgJmax}");
        }
        // QUIC masking is required for a udp+quic profile — without it the link
        // round-trips to plain UDP and a quic-mode server stays silent.
        if (QuicEnabled) q.Add("quic=1");
        if (Mtu > 0) q.Add($"mtu={Mtu}");  // 0 = auto, omit
        sb.Append('?').Append(string.Join("&", q));

        if (!string.IsNullOrWhiteSpace(Name)) sb.Append('#').Append(Uri.EscapeDataString(Name!));
        return sb.ToString();
    }

    /// <summary>Serialize to the flat-INI qeli config (inverse of FromIni).</summary>
    /// <summary>
    /// Strip control characters (incl. CR/LF) from a value before it goes into the
    /// flat-INI. This file is line-oriented, so a newline inside any value ends the
    /// line early and everything after it is read back as a NEW key — and the keys that
    /// matter (`password_command`, `post_up`) are executed through a shell by the
    /// client. A profile name or password pasted from elsewhere is enough to smuggle
    /// one in. Mirrors `ini_sanitize` in the OpenWrt init script. (Shared)
    /// </summary>
    private static string IniSafe(string? v) =>
        v is null ? "" : new string(v.Where(c => !char.IsControl(c)).ToArray());

    public string ToIni()
    {
        var sb = new StringBuilder();
        sb.AppendLine("[qeli]");
        if (!string.IsNullOrWhiteSpace(Name)) sb.AppendLine($"name = {IniSafe(Name)}");
        sb.AppendLine($"server = {IniSafe(ServerAddress)}:{Port}");
        sb.AppendLine($"proto = {IniSafe(Protocol)}");
        sb.AppendLine($"user = {IniSafe(Username)}");
        sb.AppendLine($"pass = {IniSafe(Password)}");
        if (!string.IsNullOrEmpty(ServerPublicKeyHex)) sb.AppendLine($"key = {IniSafe(ServerPublicKeyHex)}");
        if (!BindStaticToSession) sb.AppendLine("bind_static = false");  // on by default; emit only when off
        sb.AppendLine($"mode = {IniSafe(WireMode)}");
        if (!string.IsNullOrEmpty(ObfsKey)) sb.AppendLine($"obfs_key = {IniSafe(ObfsKey)}");
        if (!string.IsNullOrEmpty(Sni)) sb.AppendLine($"sni = {IniSafe(Sni)}");
        if (!string.IsNullOrEmpty(RealityShortId)) sb.AppendLine($"reality_sid = {IniSafe(RealityShortId)}");
        // Only emit `front` when it diverges from the default, mirroring Rust to_ini_string.
        if (!string.IsNullOrEmpty(ObfsFronting) && ObfsFronting != "websocket") sb.AppendLine($"front = {IniSafe(ObfsFronting)}");
        // F2 AmneziaWG junk: emit only when enabled (off by default → nothing on the wire).
        if (AwgEnabled)
        {
            sb.AppendLine("awg = true");
            sb.AppendLine($"jc = {AwgJc}");
            sb.AppendLine($"jmin = {AwgJmin}");
            sb.AppendLine($"jmax = {AwgJmax}");
        }
        if (QuicEnabled) sb.AppendLine("quic = true");
        // Routing: emit `gateway = false` only for split-tunnel so the choice survives
        // a save/export round-trip (mirrors the Rust/Android client's `gateway` key).
        if (!IsFullTunnel) sb.AppendLine("gateway = false");
        if (RouteLocalNetworks) sb.AppendLine("route_local = true");
        if (IncludeRoutes.Count > 0) sb.AppendLine($"include = {string.Join(", ", IncludeRoutes.Select(IniSafe))}");
        if (ExcludeRoutes.Count > 0) sb.AppendLine($"exclude = {string.Join(", ", ExcludeRoutes.Select(IniSafe))}");
        if (PersistTun) sb.AppendLine("persist_tun = true");
        if (Forward) sb.AppendLine("forward = true");
        if (KillSwitch) sb.AppendLine("kill_switch = true");
        if (AllowIpv6Leak) sb.AppendLine("allow_ipv6_leak = true");
        if (!string.IsNullOrEmpty(LocalAddress)) sb.AppendLine($"local = {IniSafe(LocalAddress)}");
        if (LocalPort > 0) sb.AppendLine($"lport = {LocalPort}");
        if (!string.IsNullOrEmpty(RouteFile)) sb.AppendLine($"route_file = {IniSafe(RouteFile)}");
        if (InterfaceMetric > 0) sb.AppendLine($"metric = {InterfaceMetric}");
        if (!string.IsNullOrEmpty(DevNode)) sb.AppendLine($"dev_node = {IniSafe(DevNode)}");
        // One key, two meanings — mirroring the Rust client. A non-default MODE wins over the
        // server list: `dns = off` must survive a save/load round-trip, or re-saving a profile
        // would silently turn "leave my resolver alone" back into the public fallback.
        if (DnsMode != "tunnel") sb.AppendLine($"dns = {DnsMode}");
        else if (DnsServers.Count > 0) sb.AppendLine($"dns = {string.Join(", ", DnsServers.Select(IniSafe))}");
        if (Mtu > 0) sb.AppendLine($"mtu = {Mtu}");  // 0 = auto, omit
        if (!MtuProbe) sb.AppendLine("mtu_probe = false");  // default true, emit only when off

        // Reconnect / timeout / padding / heartbeat / shaping.
        //
        // These used to be missing here entirely, and FromIni did not read them either — so
        // an INI round-trip silently reset all five groups to defaults. That is not just an
        // export concern: the Windows and macOS config editors save through
        // BuildFromForm().ToIni(), so merely OPENING a profile and pressing save discarded
        // whatever the user (or an imported iOS/Android profile) had set. Android hit exactly
        // this and fixed it; the key names below are its dialect, so profiles interchange
        // between the mobile and desktop clients unchanged.
        //
        // Emitted only when they differ from the default, keeping a plain profile short —
        // and matching how every other optional key here behaves.
        if (!ReconnectEnabled) sb.AppendLine("reconnect = false");
        if (ReconnectMaxRetries != -1) sb.AppendLine($"reconnect_retries = {ReconnectMaxRetries}");
        if (ReconnectBaseDelaySecs != 1) sb.AppendLine($"reconnect_base_delay = {ReconnectBaseDelaySecs}");
        if (ReconnectMaxDelaySecs != 60) sb.AppendLine($"reconnect_max_delay = {ReconnectMaxDelaySecs}");
        if (ConnectionTimeoutSecs != 30) sb.AppendLine($"timeout = {ConnectionTimeoutSecs}");
        if (!PaddingEnabled) sb.AppendLine("padding = false");
        if (PaddingMin != 0) sb.AppendLine($"padding_min = {PaddingMin}");
        if (PaddingMax != 255) sb.AppendLine($"padding_max = {PaddingMax}");
        if (!HeartbeatEnabled) sb.AppendLine("heartbeat = false");
        if (HeartbeatIntervalMs != 15000) sb.AppendLine($"heartbeat_interval = {HeartbeatIntervalMs}");
        if (HeartbeatDataSize != 16) sb.AppendLine($"heartbeat_size = {HeartbeatDataSize}");
        if (HeartbeatJitterMs != 2000) sb.AppendLine($"heartbeat_jitter = {HeartbeatJitterMs}");
        if (ShapingEnabled) sb.AppendLine("shaping = true");
        if (ShapingGapMeanMs != 700) sb.AppendLine($"shaping_gap_mean = {ShapingGapMeanMs}");
        if (ShapingGapMinMs != 40) sb.AppendLine($"shaping_gap_min = {ShapingGapMinMs}");
        if (ShapingGapMaxMs != 6000) sb.AppendLine($"shaping_gap_max = {ShapingGapMaxMs}");
        if (ShapingBudgetBytesPerSec != 16384) sb.AppendLine($"shaping_budget = {ShapingBudgetBytesPerSec}");
        if (ShapingMinSize != 64) sb.AppendLine($"shaping_min_size = {ShapingMinSize}");
        if (ShapingMaxSize != 1024) sb.AppendLine($"shaping_max_size = {ShapingMaxSize}");
        if (ShapingStealth) sb.AppendLine("shaping_stealth = true");
        if (ShapingStealthRateMbps != 2) sb.AppendLine($"shaping_stealth_mbps = {ShapingStealthRateMbps}");
        // Re-emit the keys this port accepts but does not model, verbatim and in a stable
        // order. Without this, opening a CLI or mobile profile here and saving it deleted its
        // hooks (`post_up`/`post_down`), its TOFU setting, its routing policy and the whole
        // per-app selection — silently, and as a side effect of merely opening it. `IniSafe`
        // applies here too: a value with an embedded newline would otherwise forge config
        // lines on save. (Audit 2026-08-02, §4 of the follow-up.)
        foreach (var key in CarriedKeys.Keys.OrderBy(k => k, StringComparer.Ordinal))
            sb.AppendLine($"{IniSafe(key)} = {IniSafe(CarriedKeys[key])}");
        return sb.ToString();
    }

    /// <summary>Deep copy (for "Duplicate"). Runtime-only fields reset to defaults.
    /// A duplicate is a DISTINCT profile, so it gets a fresh <see cref="Id"/>.</summary>
    public VpnConfig Clone()
    {
        var c = JsonSerializer.Deserialize<VpnConfig>(JsonSerializer.Serialize(this))!;
        c.Id = Guid.NewGuid().ToString("N");
        return c;
    }

    /// <summary>
    /// Parse a config in any supported format, detecting by content: a qeli://
    /// share link, legacy JSON ({…}), or the canonical flat-INI (everything else).
    /// INI is the current format; JSON is only kept for backward compatibility.
    /// Mirrors the Android VpnConfig.parse.
    /// </summary>
    public static VpnConfig Parse(string text)
    {
        var t = text.TrimStart();
        if (t.StartsWith("qeli://", StringComparison.OrdinalIgnoreCase)) return FromQeliUri(text);
        if (t.StartsWith("{")) return FromJson(text);
        return FromIni(text);
    }

    public static VpnConfig FromJson(string text)
    {
        var root = JsonNode.Parse(text)!.AsObject();
        var server = Obj(root, "server");
        var reconnect = Obj(server, "reconnect");
        var auth = Obj(root, "auth");
        var tun = Obj(root, "tun");
        var routing = Obj(root, "routing");
        var dns = Obj(root, "dns");
        var obf = Obj(root, "obfuscation");
        var padding = Obj(obf, "padding");
        var heartbeat = Obj(obf, "heartbeat");
        var shaping = Obj(obf, "traffic_shaping");
        var quic = Obj(obf, "quic");
        var awg = Obj(obf, "awg");

        string password = StrOrNull(auth, "password") ?? StrOrNull(root, "password") ?? "";
        var badJsonBools = new List<string>();
        var pad = CheckedPadding(Int(padding, "min_bytes", 0), Int(padding, "max_bytes", 255));

        return new VpnConfig
        {
            Name = StrOrNull(root, "name"),
            ServerAddress = Str(server, "address", Str(root, "address", "127.0.0.1")),
            Port = Int(server, "port", Int(root, "port", 443)),
            Protocol = Str(server, "protocol", "tcp"),
            ConnectionTimeoutSecs = CheckedTimeout(Long(server, "connection_timeout_secs", 30)),
            ReconnectEnabled = Bool(reconnect, "enabled", true, badJsonBools),
            ReconnectMaxRetries = Int(reconnect, "max_retries", -1),
            ReconnectBaseDelaySecs = Long(reconnect, "base_delay_secs", 1),
            ReconnectMaxDelaySecs = Long(reconnect, "max_delay_secs", 60),
            Username = Str(auth, "username", Str(root, "username", "client")),
            Password = password,
            ServerPublicKeyHex = StrOrNull(auth, "server_public_key"),
            BindStaticToSession = Bool(auth, "bind_static_to_session", true, badJsonBools),
            Mtu = CheckedMtu(Int(tun, "mtu", 0)),  // 0 = auto (use server-pushed MTU)
            RoutingMode = Str(routing, "mode", "full-tunnel"),
            AddDefaultGateway = Bool(routing, "add_default_gateway", false, badJsonBools),
            IncludeRoutes = StrList(routing, "include"),
            ExcludeRoutes = StrList(routing, "exclude"),
            RouteLocalNetworks = Bool(routing, "route_local_networks", false, badJsonBools),
            KillSwitch = Bool(routing, "kill_switch", false, badJsonBools),
            AllowIpv6Leak = Bool(routing, "allow_ipv6_leak", false, badJsonBools),
            DnsServers = StrList(dns, "servers"),
            WireMode = Str(obf, "mode", "fake-tls"),
            ObfsKey = Str(obf, "obfs_key", ""),
            ObfsFronting = Str(obf, "fronting", "websocket"),
            AwgEnabled = Bool(awg, "enabled", false, badJsonBools),
            AwgJc = (uint)Math.Clamp(Int(awg, "jc", 0), 0, 128),
            AwgJmin = (ushort)Math.Clamp(Int(awg, "jmin", 40), 0, 1400),
            AwgJmax = (ushort)Math.Clamp(Int(awg, "jmax", 300), 0, 1400),
            QuicEnabled = Bool(quic, "enabled", false, badJsonBools),
            Sni = StrOrNull(obf, "sni"),
            RealityShortId = StrOrNull(obf, "reality_short_id"),
            PaddingEnabled = Bool(padding, "enabled", true, badJsonBools),
            UnparsedBooleanKeys = badJsonBools,
            PaddingMin = pad.Min,
            PaddingMax = pad.Max,
            HeartbeatEnabled = Bool(heartbeat, "enabled", true, badJsonBools),
            HeartbeatIntervalMs = Long(heartbeat, "interval_ms", 15000),
            HeartbeatDataSize = Int(heartbeat, "data_size_bytes", 16),
            HeartbeatJitterMs = Long(heartbeat, "jitter_ms", 2000),
            // Parsing stopped at heartbeat, so a canonical JSON profile lost its shaping
            // block entirely and `tun.mtu_probe = false` came back as true — the client then
            // probed a path the profile had deliberately told it not to. Section and field
            // names are the canonical Rust ones (`traffic_shaping`, `idle_gap_*`), not the
            // INI shorthand. (Audit 2026-07-29, #7.)
            MtuProbe = Bool(tun, "mtu_probe", true, badJsonBools),
            ShapingEnabled = Bool(shaping, "enabled", false, badJsonBools),
            ShapingGapMeanMs = Long(shaping, "idle_gap_mean_ms", 700),
            ShapingGapMinMs = Long(shaping, "idle_gap_min_ms", 40),
            ShapingGapMaxMs = Long(shaping, "idle_gap_max_ms", 6000),
            ShapingBudgetBytesPerSec = Int(shaping, "budget_bytes_per_sec", 16384),
            ShapingMinSize = Int(shaping, "min_size", 64),
            ShapingMaxSize = Int(shaping, "max_size", 1024),
            ShapingStealth = Bool(shaping, "stealth", false, badJsonBools),
            ShapingStealthRateMbps = Int(shaping, "stealth_rate_mbps", 2),
        };
    }

    /// <summary>
    /// Parse a flat-INI qeli client config (the current format, single [qeli] section):
    /// server=host:port, proto, user, pass, key, mode, obfs_key, sni, route_local.
    /// Matches qeli/src/config/client.rs from_ini. Full-line # / ; comments only.
    /// </summary>
    public static VpnConfig FromIni(string text)
    {
        var q = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var dupKeys = new List<string>();
        string section = "";
        foreach (var raw in text.Replace("\r", "").Split('\n'))
        {
            var line = raw.Trim();
            if (line.Length == 0 || line[0] == '#' || line[0] == ';') continue;
            if (line[0] == '[' && line.EndsWith("]")) { section = line[1..^1].Trim(); continue; }
            int eq = line.IndexOf('=');
            if (eq < 0) continue;
            if (section.Equals("qeli", StringComparison.OrdinalIgnoreCase))
            {
                var iniKey = line[..eq].Trim();
                var iniValue = line[(eq + 1)..].Trim();
                if (!q.TryAdd(iniKey, iniValue))
                {
                    // Second occurrence: keep the map's LAST-wins behaviour, so a config that
                    // never had a duplicate parses exactly as before, and record the ambiguity
                    // for Validate() to refuse.
                    q[iniKey] = iniValue;
                    if (!dupKeys.Contains(iniKey)) dupKeys.Add(iniKey);
                }
            }
        }

        string Get(string k, string def = "") => q.TryGetValue(k, out var v) ? v : def;

        var server = Get("server");
        // Accepts the same spellings as the Rust client's `bool_or`. An unrecognised value is
        // RECORDED (see UnparsedBooleanKeys) and falls back to the caller's default, instead of
        // silently reading as false.
        var badBools = new List<string>();
        bool BoolAt(string key, bool dflt)
        {
            if (!q.TryGetValue(key, out var raw)) return dflt;
            var v = raw.Trim();
            if (v.Length == 0) return dflt;
            if (v.Equals("true", StringComparison.OrdinalIgnoreCase) || v == "1"
                || v.Equals("yes", StringComparison.OrdinalIgnoreCase)
                || v.Equals("on", StringComparison.OrdinalIgnoreCase)) return true;
            if (v.Equals("false", StringComparison.OrdinalIgnoreCase) || v == "0"
                || v.Equals("no", StringComparison.OrdinalIgnoreCase)
                || v.Equals("off", StringComparison.OrdinalIgnoreCase)) return false;
            badBools.Add(key);
            return dflt;
        }
        // A number nobody could parse is a typo, and substituting the default silently is the
        // same failure mode the boolean handling already fixed: the profile connects, just not
        // where the file says. `server = host:notnum` became `host:443` — a different server
        // entirely, with nothing reported. Recorded here and refused by Validate(), while
        // parsing still SUCCEEDS so an editor can open the profile to fix it.
        // (Audit 2026-08-01, §P2.)
        var badNums = new List<string>();
        long LongAt(string key, long dflt)
        {
            var v = Get(key);
            if (v.Length == 0) return dflt;
            if (long.TryParse(v, out var parsed)) return parsed;
            badNums.Add(key);
            return dflt;
        }
        int NumAt(string key, int dflt) => (int)Math.Clamp(LongAt(key, dflt), int.MinValue, int.MaxValue);
        // Out of range is recorded, exactly like unparseable — the Validate() message already
        // says "unparseable OR out-of-range", so this list was simply never being filled.
        //
        // The previous note here called the silent fallback "a documented clamp, not a
        // mistake". It is not a clamp: a clamp would pin the value to the nearest bound,
        // whereas this jumps to the DEFAULT, which is somewhere else entirely. `lport = 99999`
        // became 0 (bind anywhere), a negative heartbeat became 15 s — the setting the user
        // wrote silently replaced by an unrelated one. The `server` port a few lines below had
        // already been fixed this way and the rest were left behind; the C# selftest then
        // pinned the silent behaviour as correct. (Audit 2026-08-02, §11.)
        int RangedNum(string key, int dflt, int lo, int hi)
        {
            int v = NumAt(key, dflt);
            if (v >= lo && v <= hi) return v;
            if (Get(key).Length > 0 && !badNums.Contains(key)) badNums.Add(key);
            return dflt;
        }
        long RangedLong(string key, long dflt, long lo, long hi)
        {
            long v = LongAt(key, dflt);
            if (v >= lo && v <= hi) return v;
            if (Get(key).Length > 0 && !badNums.Contains(key)) badNums.Add(key);
            return dflt;
        }
        var iniPad = CheckedPadding(NumAt("padding_min", 0), NumAt("padding_max", 255));
        string host = "127.0.0.1";
        int port = 443;
        int colon = server.LastIndexOf(':');
        if (colon > 0)
        {
            host = server[..colon];
            if (!int.TryParse(server[(colon + 1)..], out port)) badNums.Add("server (port)");
        }
        else if (server.Length > 0) host = server;
        if (port is < 1 or > 65535)
        {
            // Out of range is as wrong as unparseable: `:0` and `:99999` are not ports, and
            // quietly becoming 443 sends the client somewhere it was never told to go.
            if (server.Length > 0 && colon > 0 && !badNums.Contains("server (port)"))
                badNums.Add("server (port)");
            port = 443;
        }

        string key = new string(Get("key").Where(Uri.IsHexDigit).ToArray()).ToLowerInvariant();
        bool keyValid = key.Length == 64 && key.Any(ch => ch != '0'); // all-zero = TOFU
        string sni = Get("sni");

        // Routing: full-tunnel by default; `gateway = false` opts into split-tunnel.
        // Mirrors the Rust/Android `gateway` key — the only way to pick split-tunnel
        // via an imported INI / qeli:// link (the GUI routing dropdown is a separate path).
        bool fullTunnel = BoolAt("gateway", true);
        // DNS: `dns = <ip,ip>` is the resolver list here, but the SAME key is a MODE in the
        // Rust/router client (`off` / `tunnel` / `system`).
        //
        // Recognising the mode words was only half the job: they were mapped to "no explicit
        // resolvers", and SetupTun then treats that as "nothing chosen" and installs the public
        // fallback on a full tunnel. So `dns = off` — which means LEAVE MY RESOLVER ALONE —
        // sent every lookup to Cloudflare and Google instead. The mode is now KEPT and honoured
        // at connect time. (Audit 2026-08-02, §3.)
        var dnsRaw = Get("dns");
        string dnsMode = dnsRaw.Equals("off", StringComparison.OrdinalIgnoreCase)
                || dnsRaw.Equals("tunnel", StringComparison.OrdinalIgnoreCase)
                || dnsRaw.Equals("system", StringComparison.OrdinalIgnoreCase)
            ? dnsRaw.ToLowerInvariant()
            : "tunnel";
        List<string>? dnsList = (dnsRaw.Length == 0 || dnsMode != "tunnel" || dnsRaw.Equals("tunnel", StringComparison.OrdinalIgnoreCase))
            ? null
            : dnsRaw.Split(',').Select(s => s.Trim()).Where(s => s.Length > 0).ToList();

        // Alias: `mode=udp-quic` / `udp-obfs` fold transport+QUIC into the wire mode.
        var (proto, mode, quic) = NormalizeMode(Get("proto", "tcp"), Get("mode", "fake-tls"), BoolAt("quic", false));

        return new VpnConfig
        {
            Name = Get("name", host),
            ServerAddress = host,
            Port = port,
            Protocol = proto,
            Username = Get("user", "client"),
            Password = Get("pass"),
            ServerPublicKeyHex = keyValid ? key : null,
            // H-1: on by default; needs a pinned key. `bind_static = false` for TOFU.
            BindStaticToSession = BoolAt("bind_static", true),
            WireMode = mode,
            ObfsKey = Get("obfs_key"),
            ObfsFronting = Get("front", "websocket"),
            // F2 AmneziaWG junk (off by default). `awg = true` enables; jc/jmin/jmax
            // bound the junk. Clamped to the wire caps (jc<=128, len<=1400).
            AwgEnabled = BoolAt("awg", false),
            AwgJc = (uint)RangedNum("jc", 0, 0, 128),
            AwgJmin = (ushort)RangedNum("jmin", 40, 0, 1400),
            AwgJmax = (ushort)RangedNum("jmax", 300, 0, 1400),
            QuicEnabled = quic,
            Sni = sni.Length > 0 ? sni : null,
            RealityShortId = Get("reality_sid").Length > 0 ? Get("reality_sid") : null,
            RouteLocalNetworks = BoolAt("route_local", false),
            // Explicit per-CIDR routing (comma-separated). `exclude` carves subnets OUT of
            // the tunnel (routed via the physical gateway, so it works in full-tunnel too);
            // `include` forces subnets IN (split-tunnel). Mirrors the Rust/Android keys.
            IncludeRoutes = SplitCidrs(Get("include")),
            ExcludeRoutes = SplitCidrs(Get("exclude")),
            PersistTun = BoolAt("persist_tun", false),
            Forward = BoolAt("forward", false),
            // Was neither parsed nor emitted here, so an imported/exported flat-INI silently
            // dropped the kill-switch flag — the leak protection the user asked for failed
            // OPEN. Rust reads it (client.rs) and FromJson already did; mirror them.
            KillSwitch = BoolAt("kill_switch", false),
            AllowIpv6Leak = BoolAt("allow_ipv6_leak", false),
            LocalAddress = Get("local").Length > 0 ? Get("local") : null,
            LocalPort = RangedNum("lport", 0, 1, 65535),
            RouteFile = Get("route_file").Length > 0 ? Get("route_file") : null,
            InterfaceMetric = RangedNum("metric", 0, 1, int.MaxValue),
            // Accept the Rust/Android client's `dev` key as an alias for `dev_node` so a
            // shared flat-INI config's TUN interface name transfers across clients.
            DevNode = Get("dev_node").Length > 0 ? Get("dev_node")
                    : Get("dev").Length > 0 ? Get("dev") : null,
            Mtu = CheckedMtu(NumAt("mtu", 0)),  // 0 = auto
            MtuProbe = BoolAt("mtu_probe", true),
            // The counterpart of the block ToIni now emits. Every one of these defaults to
            // the value the property already carries, so an absent key leaves it untouched
            // and a profile without them behaves exactly as before. (Audit 2026-07-29, #7.)
            ReconnectEnabled = BoolAt("reconnect", true),
            ReconnectMaxRetries = NumAt("reconnect_retries", -1),
            ReconnectBaseDelaySecs = RangedLong("reconnect_base_delay", 1, 1, long.MaxValue),
            ReconnectMaxDelaySecs = RangedLong("reconnect_max_delay", 60, 1, long.MaxValue),
            ConnectionTimeoutSecs = CheckedTimeout(LongAt("timeout", 30)),
            PaddingEnabled = BoolAt("padding", true),
            // Through CheckedPadding, like FromJson: on its own each field only checked `>= 0`,
            // so a hand-written INI could set padding_min > padding_max (an inverted range) or a
            // five-digit padding far past PaddingCeiling — records the peer would reject.
            // (Audit 2026-07-30, #11.)
            PaddingMin = iniPad.Min,
            PaddingMax = iniPad.Max,
            HeartbeatEnabled = BoolAt("heartbeat", true),
            HeartbeatIntervalMs = RangedLong("heartbeat_interval", 15000, 1, long.MaxValue),
            HeartbeatDataSize = RangedNum("heartbeat_size", 16, 0, int.MaxValue),
            HeartbeatJitterMs = RangedLong("heartbeat_jitter", 2000, 0, long.MaxValue),
            ShapingEnabled = BoolAt("shaping", false),
            ShapingGapMeanMs = RangedLong("shaping_gap_mean", 700, 1, long.MaxValue),
            ShapingGapMinMs = RangedLong("shaping_gap_min", 40, 1, long.MaxValue),
            ShapingGapMaxMs = RangedLong("shaping_gap_max", 6000, 1, long.MaxValue),
            ShapingBudgetBytesPerSec = RangedNum("shaping_budget", 16384, 1, int.MaxValue),
            ShapingMinSize = RangedNum("shaping_min_size", 64, 1, int.MaxValue),
            ShapingMaxSize = RangedNum("shaping_max_size", 1024, 1, int.MaxValue),
            ShapingStealth = BoolAt("shaping_stealth", false),
            ShapingStealthRateMbps = RangedNum("shaping_stealth_mbps", 2, 1, int.MaxValue),
            UnparsedBooleanKeys = badBools,
            DuplicateKeys = dupKeys,
            UnparsedNumericKeys = badNums,
            UnknownKeys = q.Keys.Where(k => !KnownIniKeys.Contains(k)).OrderBy(k => k).ToArray(),
            // Accepted but not modelled — kept so saving does not delete them.
            CarriedKeys = q.Where(kv => CarriedIniKeys.Contains(kv.Key))
                           .ToDictionary(kv => kv.Key, kv => kv.Value),
            RoutingMode = fullTunnel ? "full-tunnel" : "split-tunnel",
            AddDefaultGateway = fullTunnel,
            DnsServers = dnsList ?? new List<string>(),  // empty when unset; fallback at connect time
            DnsMode = dnsMode,
        };
    }

    // ── imported-value ranges ────────────────────────────────────────────────
    // `port` and the server-pushed `max_streams` were range-checked at import, but `mtu`
    // and the padding bounds were not: a hand-written config or a pasted
    // `qeli://…?mtu=999999` (or a negative) became a profile that failed at connect with
    // an opaque TUN/socket error, and an out-of-range padding_max built records the peer
    // rejects as oversized. Same ranges the Rust client enforces — config/client.rs:
    // mtu is 0 (auto) or 576..=16638; padding is bounded by the 1400-byte wire ceiling the
    // per-packet pad_cap uses. (Audit 2026-07-27, C6)
    private const int MtuMin = 576;
    /// <summary>Derived, in Rust, from the record format (protocol/packet.rs MAX_TUNNEL_MTU): a record holds nonce + counter + payload + padding-length + tag and must fit MAX_RECORD_SIZE, so anything larger the PEER REJECTS. Mirrored here as a literal; the four ports and the two UIs must all carry the same number, because raising it in one place only is worse than not raising it — see Audit 2026-08-01 §1.</summary>
    private const int MtuMax = 16638;
    private const int PaddingCeiling = 1400;

    /// <summary>Range-check an explicit TUN MTU from a config FILE (flat-INI or JSON);
    /// 0 = auto. REJECTS, like the Rust <c>from_ini</c>: a bad value in a file the user
    /// wrote by hand is a mistake worth surfacing at import (both GUI import paths show
    /// the message), not something to silently rewrite. (Audit 2026-07-27, C6)</summary>
    private static int CheckedMtu(int mtu) =>
        mtu == 0 || (mtu >= MtuMin && mtu <= MtuMax)
            ? mtu
            : throw new FormatException($"invalid mtu {mtu} — expected 0 (auto) or {MtuMin}..{MtuMax}");

    /// <summary>Same range for a <c>qeli://</c> link, but falls back to auto instead of
    /// throwing — mirrors the Rust link importer, which is infallible and only warns. A
    /// scanned or pasted link should still yield a usable profile. (Audit 2026-07-27, C6)</summary>
    private static int LinkMtu(int mtu) => mtu == 0 || (mtu >= MtuMin && mtu <= MtuMax) ? mtu : 0;

    /// <summary>Clamp imported padding bounds to 0..1400 and restore min &lt;= max. Clamped
    /// rather than rejected: unlike mtu these are pure obfuscation knobs, so narrowing them
    /// costs the user nothing while an oversized max_bytes would make every data record
    /// exceed PacketCodec.MaxRecordSize. (Audit 2026-07-27, C6)</summary>
    /// <summary>Clamp the connect timeout to the same 1..300 s the Android and iOS clients
    /// enforce. Unbounded before: the INI accepted any positive long, and
    /// <c>VpnTunnelBase</c> then computes <c>(int)ConnectionTimeoutSecs * 1000</c> — so a value
    /// above ~2.1 M seconds overflowed the int multiply into a NEGATIVE timeout, which is not a
    /// long wait but an immediately-expired one. (Audit 2026-07-30, #11.)</summary>
    private const long TimeoutSecsMin = 1;
    private const long TimeoutSecsMax = 300;

    private static long CheckedTimeout(long secs) =>
        secs <= 0 ? 30 : Math.Clamp(secs, TimeoutSecsMin, TimeoutSecsMax);

    private static (int Min, int Max) CheckedPadding(int min, int max)
    {
        min = Math.Clamp(min, 0, PaddingCeiling);
        return (min, Math.Clamp(max, min, PaddingCeiling));
    }

    /// <summary>Reject a config the runtime would then silently reinterpret. The desktop client
    /// had no equivalent of the Rust client's <c>ClientConfig::validate()</c>, so every string
    /// enum fell through to another branch on a typo: an unknown protocol became TCP, an unknown
    /// wire mode became fake-TLS, an unknown <c>front</c> meant raw obfs — and an unparseable
    /// boolean read as false, which disabled the kill switch and the static-key binding.
    ///
    /// Called at CONNECT, not at load: an editor must still be able to open a bad profile in
    /// order to fix it. Same split as the Rust client. (Audit 2026-07-31.)</summary>
    public void Validate()
    {
        if (DuplicateKeys.Count > 0)
        {
            throw new ArgumentException(
                $"key(s) {string.Join(", ", DuplicateKeys)} appear more than once and are read "
                + "as a single value; implementations disagree on which wins — keep one");
        }
        if (UnknownKeys.Count > 0)
        {
            throw new ArgumentException(
                $"unknown key(s), likely misspelled: {string.Join(", ", UnknownKeys)} — nothing "
                + "reads these, so the setting they were meant to change is at its default");
        }
        if (UnparsedNumericKeys.Count > 0)
        {
            throw new ArgumentException(
                $"unparseable or out-of-range number for {string.Join(", ", UnparsedNumericKeys)} "
                + "— the default would have been used instead, which for a port means "
                + "connecting somewhere the config never named");
        }
        if (UnparsedBooleanKeys.Count > 0)
        {
            throw new ArgumentException(
                $"unrecognised boolean value for {string.Join(", ", UnparsedBooleanKeys)} — "
                + "expected true/false, yes/no, on/off or 1/0");
        }

        static void Enum_(string field, string got, params string[] allowed)
        {
            foreach (var a in allowed)
            {
                if (string.Equals(got, a, StringComparison.Ordinal)) return;
            }
            throw new ArgumentException(
                $"unknown {field} '{got}' — expected {string.Join(" or ", allowed.Select(x => $"'{x}'"))}");
        }

        if (Port is < 1 or > 65535) throw new ArgumentException($"'server' port out of range: {Port}");
        // An IPv6 endpoint parses and round-trips, but no core can USE it: the sockets below are
        // created AddressFamily.InterNetwork and the resolver discards AAAA. Accepting it meant
        // a confusing "address family not supported" at connect time instead of a clear refusal
        // here — the same reason the Rust client refuses it. Real support is tracked for 0.8.0.
        // (Audit 2026-08-01, §9.)
        if (System.Net.IPAddress.TryParse(ServerAddress.Trim('[', ']'), out var parsed)
            && parsed.AddressFamily == System.Net.Sockets.AddressFamily.InterNetworkV6)
        {
            throw new ArgumentException(
                $"'server' is an IPv6 address ('{ServerAddress}') — not supported yet: the data "
                + "plane binds IPv4 only. Use an IPv4 address or a hostname that resolves to one.");
        }
        Enum_("proto", Protocol, "tcp", "udp");
        Enum_("mode", WireMode, "fake-tls", "obfs", "plain", "reality-tls");
        Enum_("front", ObfsFronting, "websocket", "none");
        Enum_("routing mode", RoutingMode, "split-tunnel", "full-tunnel", "all");
        if (ConnectionTimeoutSecs is < 1 or > 300)
            throw new ArgumentException($"'timeout' must be 1..300, got {ConnectionTimeoutSecs}");
    }

    private static bool IniBool(string v) =>
        v.Equals("true", StringComparison.OrdinalIgnoreCase) || v == "1" ||
        v.Equals("yes", StringComparison.OrdinalIgnoreCase) || v.Equals("on", StringComparison.OrdinalIgnoreCase);

    /// <summary>Split a comma-separated CIDR list, trimming blanks. Values are validated
    /// again (strict IP literal) before being spliced into route commands.</summary>
    private static List<string> SplitCidrs(string v) =>
        v.Split(',').Select(s => s.Trim()).Where(s => s.Length > 0).ToList();

    /// <summary>
    /// Parse a qeli:// share link. Mirrors Android VpnConfig.fromQeliUri /
    /// qeli/src/config/share.rs:
    /// qeli://user:pass@host:port?proto=tcp&amp;mode=fake-tls&amp;key=hex&amp;sni=host&amp;obfs=key#label
    /// </summary>
    public static VpnConfig FromQeliUri(string uri)
    {
        string trimmed = uri.Trim();
        if (!trimmed.StartsWith("qeli://", StringComparison.Ordinal))
            throw new FormatException("not a qeli:// link");
        string rest0 = trimmed.Substring("qeli://".Length);

        string beforeFrag; string? label = null;
        int hashIdx = rest0.IndexOf('#');
        if (hashIdx >= 0) { beforeFrag = rest0[..hashIdx]; label = PctDecode(rest0[(hashIdx + 1)..]); }
        else beforeFrag = rest0;

        string authority; string? query = null;
        int qIdx = beforeFrag.IndexOf('?');
        if (qIdx >= 0) { authority = beforeFrag[..qIdx]; query = beforeFrag[(qIdx + 1)..]; }
        else authority = beforeFrag;

        int atIdx = authority.LastIndexOf('@');
        string? userinfo = atIdx >= 0 ? authority[..atIdx] : null;
        string hostPort = atIdx >= 0 ? authority[(atIdx + 1)..] : authority;
        string host; int port;
        if (hostPort.StartsWith('['))
        {
            // Bracketed IPv6 literal: [2001:db8::1]:443 — split on the ']:' so the
            // colons inside the address aren't mistaken for the port separator.
            int rb = hostPort.IndexOf(']');
            if (rb < 0 || rb + 1 >= hostPort.Length || hostPort[rb + 1] != ':')
                throw new FormatException("qeli:// authority malformed IPv6 [host]:port");
            host = hostPort[1..rb];
            if (!int.TryParse(hostPort[(rb + 2)..], out port))
                throw new FormatException("invalid port in qeli:// link");
        }
        else
        {
            int colonIdx = hostPort.LastIndexOf(':');
            if (colonIdx <= 0) throw new FormatException("qeli:// authority missing :port");
            host = hostPort[..colonIdx];
            if (!int.TryParse(hostPort[(colonIdx + 1)..], out port))
                throw new FormatException("invalid port in qeli:// link");
        }
        if (host.Length == 0) throw new FormatException("empty host in qeli:// link");
        // FromIni already range-checks the port; this path only checked that it PARSED,
        // so `:0`, `:99999` or a negative value sailed through into a profile that then
        // failed at connect time with an opaque socket error. Reject at import. (Shared)
        if (port is < 1 or > 65535)
            throw new FormatException($"port {port} out of range in qeli:// link (1..65535)");

        string user = "", pass = "";
        if (userinfo != null)
        {
            int sep = userinfo.IndexOf(':');
            if (sep >= 0) { user = PctDecode(userinfo[..sep]); pass = PctDecode(userinfo[(sep + 1)..]); }
            else user = PctDecode(userinfo);
        }

        string proto = "tcp", mode = "fake-tls", obfs = "", front = "websocket";
        string? key = null, sni = null, rsid = null;
        bool quic = false;
        int mtu = 0;  // 0 = auto (use server-pushed MTU)
        // F2 AmneziaWG junk params (off unless awg=1).
        bool awg = false;
        uint awgJc = 0;
        ushort awgJmin = 40, awgJmax = 300;
        if (query != null)
        {
            foreach (var pair in query.Split('&'))
            {
                if (pair.Length == 0) continue;
                int eq = pair.IndexOf('=');
                string k = eq >= 0 ? pair[..eq] : pair;
                string v = PctDecode(eq >= 0 ? pair[(eq + 1)..] : "");
                switch (k)
                {
                    case "proto": proto = v; break;
                    case "mode": mode = v; break;
                    // Same normalisation FromIni applies: keep hex digits only, lowercase,
                    // and treat anything that is not a 64-char non-all-zero key as unpinned
                    // (TOFU) instead of storing junk that only fails at handshake. (Shared)
                    case "key":
                    {
                        var hex = new string(v.Where(Uri.IsHexDigit).ToArray()).ToLowerInvariant();
                        key = hex.Length == 64 && hex.Any(ch => ch != '0') ? hex : null;
                        break;
                    }
                    case "sni": sni = v.Length == 0 ? null : v; break;
                    case "rsid": rsid = v.Length == 0 ? null : v; break;
                    case "obfs": obfs = v; break;
                    case "front": if (v.Length > 0) front = v; break;
                    case "quic": quic = v == "1" || v.Equals("true", StringComparison.OrdinalIgnoreCase); break;
                    case "mtu": int.TryParse(v, out mtu); break;
                    case "awg": awg = v == "1" || v.Equals("true", StringComparison.OrdinalIgnoreCase); break;
                    case "jc": if (uint.TryParse(v, out var jcp)) awgJc = Math.Min(jcp, 128u); break;
                    case "jmin": if (ushort.TryParse(v, out var jminp)) awgJmin = Math.Min(jminp, (ushort)1400); break;
                    case "jmax": if (ushort.TryParse(v, out var jmaxp)) awgJmax = Math.Min(jmaxp, (ushort)1400); break;
                }
            }
        }

        // Alias convenience: some users fold transport+QUIC into the wire mode
        // (`mode=udp-quic` / `udp-obfs`). Split it back into proto + wire mode + quic.
        (proto, mode, quic) = NormalizeMode(proto, mode, quic);

        return new VpnConfig
        {
            Name = label,
            ServerAddress = host, Port = port, Protocol = proto,
            Username = user, Password = pass, ServerPublicKeyHex = key,
            WireMode = mode, ObfsKey = obfs, ObfsFronting = front, Sni = sni, QuicEnabled = quic,
            AwgEnabled = awg, AwgJc = awgJc, AwgJmin = awgJmin, AwgJmax = awgJmax,
            RealityShortId = rsid, Mtu = LinkMtu(mtu),
        };
    }

    /// <summary>Accept convenience aliases where transport/QUIC is folded into the wire
    /// mode: `udp-quic` → (udp, fake-tls, quic on); `udp-obfs` → (udp, obfs). Anything
    /// else passes through unchanged.</summary>
    private static (string proto, string mode, bool quic) NormalizeMode(string proto, string mode, bool quic) =>
        mode.ToLowerInvariant() switch
        {
            "udp-quic" => ("udp", "fake-tls", true),
            "udp-obfs" => ("udp", "obfs", quic),
            _ => (proto, mode, quic),
        };

    // ── JSON helpers ──────────────────────────────────────────────────────────
    private static JsonObject Obj(JsonObject? parent, string key) =>
        parent?[key] as JsonObject ?? new JsonObject();

    private static string Str(JsonObject o, string key, string def) =>
        o[key] is JsonValue v && v.TryGetValue(out string? s) ? s! : def;

    private static string? StrOrNull(JsonObject o, string key)
    {
        if (o[key] is JsonValue v && v.TryGetValue(out string? s) && !string.IsNullOrEmpty(s)) return s;
        return null;
    }

    private static int Int(JsonObject o, string key, int def) =>
        o[key] is JsonValue v && v.TryGetValue(out int i) ? i : def;

    private static long Long(JsonObject o, string key, long def) =>
        o[key] is JsonValue v && v.TryGetValue(out long l) ? l : def;

    /// <summary>A JSON boolean, recording anything that is PRESENT but not a real bool.
    ///
    /// `"kill_switch": "ture"` is a JSON string, so `TryGetValue&lt;bool&gt;` fails and the
    /// default was returned silently — the same fail-open the INI path had, reached through a
    /// different door. A missing key is not an error (that is what the default is for); a key
    /// that is there but unreadable is. (Audit 2026-07-31, §4.)</summary>
    private static bool Bool(JsonObject o, string key, bool def, List<string>? bad = null)
    {
        if (o[key] is not JsonValue v) return def;                 // absent → default
        if (v.TryGetValue(out bool b)) return b;
        // A JSON string still spelling a boolean is accepted, like the INI path.
        if (v.TryGetValue(out string? s) && s != null)
        {
            var t = s.Trim();
            if (t.Equals("true", StringComparison.OrdinalIgnoreCase) || t == "1"
                || t.Equals("yes", StringComparison.OrdinalIgnoreCase)
                || t.Equals("on", StringComparison.OrdinalIgnoreCase)) return true;
            if (t.Equals("false", StringComparison.OrdinalIgnoreCase) || t == "0"
                || t.Equals("no", StringComparison.OrdinalIgnoreCase)
                || t.Equals("off", StringComparison.OrdinalIgnoreCase)) return false;
        }
        bad?.Add(key);
        return def;
    }

    private static List<string> StrList(JsonObject o, string key)
    {
        var result = new List<string>();
        if (o[key] is JsonArray arr)
            foreach (var n in arr)
                if (n is JsonValue v && v.TryGetValue(out string? s) && !string.IsNullOrEmpty(s))
                    result.Add(s!);
        return result;
    }

    private static string PctDecode(string s)
    {
        if (s.IndexOf('%') < 0) return s;
        var bytes = new List<byte>(s.Length);
        var outSb = new StringBuilder(s.Length);
        int i = 0;
        void Flush() { if (bytes.Count > 0) { outSb.Append(Encoding.UTF8.GetString(bytes.ToArray())); bytes.Clear(); } }
        while (i < s.Length)
        {
            char c = s[i];
            if (c == '%' && i + 2 < s.Length)
            {
                int h = HexVal(s[i + 1]); int l = HexVal(s[i + 2]);
                if (h >= 0 && l >= 0) { bytes.Add((byte)((h << 4) | l)); i += 3; continue; }
            }
            Flush();
            outSb.Append(c); i++;
        }
        Flush();
        return outSb.ToString();
    }

    private static int HexVal(char c) => c switch
    {
        >= '0' and <= '9' => c - '0',
        >= 'a' and <= 'f' => c - 'a' + 10,
        >= 'A' and <= 'F' => c - 'A' + 10,
        _ => -1,
    };
}
