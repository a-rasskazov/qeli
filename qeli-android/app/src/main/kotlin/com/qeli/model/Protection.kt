package com.qeli.model

/** How much of the device's traffic the tunnel carries. */
enum class ProtectionScope {
    /** Every app, every route. */
    ALL,

    /** Only the apps the user picked (`apps_mode = include`). */
    ONLY_SELECTED,

    /** Every app except the ones the user picked (`apps_mode = exclude`). */
    ALL_EXCEPT,

    /** Split tunnel: only the configured/pushed routes go through the VPN. */
    SPLIT_ROUTES,
}

/** Something that narrows what the tunnel protects, worth telling the user about. */
enum class ProtectionWarning {
    /** `allow_lan` — RFC1918 is carved out, so LAN traffic is not in the tunnel. */
    LAN_OUTSIDE,

    /** `allow_ipv6_leak` — native IPv6 keeps bypassing the (IPv4) tunnel. */
    IPV6_OUTSIDE,

    /** Explicit `exclude` routes. */
    EXCLUDED_ROUTES,

    /** No pinned server key: the first connection trusts whoever answers (TOFU). */
    NO_PINNED_KEY,
}

/**
 * What a profile actually protects, derived from the profile alone.
 *
 * This backs a card that makes SECURITY CLAIMS, so the rule is: state only what the config
 * guarantees, and give anything that narrows the tunnel its own line rather than folding it
 * into a reassuring headline. A card that says "all traffic is protected" when it isn't is
 * worse than no card at all.
 *
 * Deliberately a pure function of [VpnConfig] with enum outputs — no Context, no string
 * resources — so the decisions are unit-testable and the wording stays localizable.
 * Runtime facts the profile cannot know (which resolver the server actually pushed, the
 * negotiated MTU, whether the system lockdown is on) are NOT guessed here; they arrive with
 * the tunnel snapshot.
 */
data class ProtectionSummary(
    val scope: ProtectionScope,
    /** Size of the per-app selection; meaningful for ONLY_SELECTED / ALL_EXCEPT. */
    val appCount: Int,
    val excludedRouteCount: Int,
    /** X25519 + ML-KEM-768. True for every wire mode except `plain`. */
    val postQuantum: Boolean,
    val dnsThroughTunnel: Boolean,
    val keyPinned: Boolean,
    val warnings: List<ProtectionWarning>,
) {
    /**
     * True only when nothing narrows what the tunnel carries — the one condition under
     * which the UI may claim "all traffic is protected".
     *
     * [ProtectionWarning.NO_PINNED_KEY] is excluded on purpose: pinning decides WHO the
     * client is willing to talk to, not HOW MUCH traffic it carries. It still gets its own
     * warning line.
     */
    val carriesEverything: Boolean
        get() = scope == ProtectionScope.ALL &&
            warnings.none { it != ProtectionWarning.NO_PINNED_KEY }

    companion object {
        fun of(config: VpnConfig): ProtectionSummary {
            val apps = config.apps.size
            val scope = when {
                config.appsMode.equals("include", ignoreCase = true) -> ProtectionScope.ONLY_SELECTED
                config.appsMode.equals("exclude", ignoreCase = true) -> ProtectionScope.ALL_EXCEPT
                !config.isFullTunnel -> ProtectionScope.SPLIT_ROUTES
                else -> ProtectionScope.ALL
            }
            val warnings = buildList {
                if (config.allowLan) add(ProtectionWarning.LAN_OUTSIDE)
                if (config.allowIpv6Leak) add(ProtectionWarning.IPV6_OUTSIDE)
                if (config.excludeRoutes.isNotEmpty()) add(ProtectionWarning.EXCLUDED_ROUTES)
                if (config.serverPublicKeyHex.isNullOrEmpty()) add(ProtectionWarning.NO_PINNED_KEY)
            }
            return ProtectionSummary(
                scope = scope,
                appCount = apps,
                excludedRouteCount = config.excludeRoutes.size,
                // Every mode runs the hybrid PQ ClientHello except `plain`, which uses a
                // raw X25519 exchange (QeliService: performHandshakePlain vs
                // performHandshake). obfs and reality-tls are transport wrappers around the
                // SAME PQ handshake, so they count as post-quantum.
                postQuantum = !config.wireMode.equals("plain", ignoreCase = true),
                // Explicit resolvers are reached through the tunnel; a full tunnel captures
                // DNS regardless. Anything narrower cannot be claimed from the profile
                // alone, so it is reported as system DNS until the snapshot says otherwise.
                dnsThroughTunnel = config.dnsServers.isNotEmpty() || config.isFullTunnel,
                keyPinned = !config.serverPublicKeyHex.isNullOrEmpty(),
                warnings = warnings,
            )
        }
    }
}
