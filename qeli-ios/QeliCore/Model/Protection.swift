import Foundation

/// How much of the device's traffic the tunnel carries.
enum ProtectionScope: Equatable, Sendable {
    /// Every app, every route.
    case all
    /// Only the apps the user picked (`apps_mode = include`). iOS cannot enforce this
    /// without MDM — the profile still carries it, so it is still reported honestly.
    case onlySelected
    /// Every app except the ones the user picked (`apps_mode = exclude`).
    case allExcept
    /// Split tunnel: only the configured/pushed routes go through the VPN.
    case splitRoutes
}

/// Something that narrows what the tunnel protects, worth telling the user about.
enum ProtectionWarning: Equatable, Sendable {
    /// `allow_lan` — RFC1918 is carved out, so LAN traffic is not in the tunnel.
    case lanOutside
    /// `allow_ipv6_leak` — native IPv6 keeps bypassing the (IPv4) tunnel.
    case ipv6Outside
    /// Explicit `exclude` routes.
    case excludedRoutes
    /// No pinned server key: the first connection trusts whoever answers (TOFU).
    case noPinnedKey
}

/// What a profile actually protects, derived from the profile alone.
///
/// Mirror of the Android `ProtectionSummary`, decision for decision — the two cards must
/// never disagree about the same profile.
///
/// This backs a card that makes SECURITY CLAIMS, so the rule is: state only what the config
/// guarantees, and give anything that narrows the tunnel its own line rather than folding it
/// into a reassuring headline. A card that says "all traffic is protected" when it isn't is
/// worse than no card at all.
///
/// Deliberately a pure function of `VPNConfig` with enum outputs — no view code, no
/// localized text — so the decisions are testable and the wording stays localizable.
/// Runtime facts the profile cannot know (which resolver the server actually pushed, the
/// negotiated MTU) are NOT guessed here; they arrive with the tunnel snapshot.
struct ProtectionSummary: Equatable, Sendable {
    let scope: ProtectionScope
    /// Size of the per-app selection; meaningful for `onlySelected` / `allExcept`.
    let appCount: Int
    let excludedRouteCount: Int
    /// X25519 + ML-KEM-768. True for every wire mode except `plain`.
    let postQuantum: Bool
    let dnsThroughTunnel: Bool
    let keyPinned: Bool
    let warnings: [ProtectionWarning]

    /// True only when nothing narrows what the tunnel carries — the one condition under
    /// which the UI may claim "all traffic is protected".
    ///
    /// `noPinnedKey` is excluded on purpose: pinning decides WHO the client is willing to
    /// talk to, not HOW MUCH traffic it carries. It still gets its own warning line.
    var carriesEverything: Bool {
        scope == .all && warnings.allSatisfy { $0 == .noPinnedKey }
    }

    init(config: VPNConfig) {
        let mode = config.appsMode.lowercased()
        if mode == "include" {
            scope = .onlySelected
        } else if mode == "exclude" {
            scope = .allExcept
        } else if !config.isFullTunnel {
            scope = .splitRoutes
        } else {
            scope = .all
        }
        appCount = config.apps.count
        excludedRouteCount = config.excludeRoutes.count
        // Every mode runs the hybrid PQ ClientHello except `plain`, which uses a raw X25519
        // exchange. obfs and reality-tls are transport wrappers around the SAME PQ
        // handshake, so they count as post-quantum.
        postQuantum = config.wireMode.lowercased() != "plain"
        // Explicit resolvers are reached through the tunnel; a full tunnel captures DNS
        // regardless. Anything narrower cannot be claimed from the profile alone.
        dnsThroughTunnel = !config.dnsServers.isEmpty || config.isFullTunnel
        keyPinned = !(config.serverPublicKeyHex ?? "").isEmpty

        var found: [ProtectionWarning] = []
        if config.allowLAN { found.append(.lanOutside) }
        if config.allowIPv6Leak { found.append(.ipv6Outside) }
        if !config.excludeRoutes.isEmpty { found.append(.excludedRoutes) }
        if (config.serverPublicKeyHex ?? "").isEmpty { found.append(.noPinnedKey) }
        warnings = found
    }
}
