import Foundation
import SwiftUI

struct ConnectionView: View {
    @EnvironmentObject private var model: AppModel
    @State private var showingProtectionDetails = false

    var body: some View {
        ScrollView {
            VStack(spacing: 14) {
                connectionCard
                activeProfileCard
                if model.tunnelSnapshot.phase == .connected { statisticsCard }
                protectionCard
                if let error = model.tunnelSnapshot.error, !error.isEmpty {
                    Label(error, systemImage: "exclamationmark.triangle.fill")
                        .font(.footnote)
                        .foregroundStyle(QeliTheme.error)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .qeliCard()
                }
            }
            .padding(16)
        }
        .refreshable {
            model.tunnelManager.refreshSnapshot()
            model.refreshLog()
        }
    }

    private var connectionCard: some View {
        VStack(spacing: 14) {
            Button { Task { await model.toggleConnection() } } label: {
                ZStack {
                    Circle()
                        .stroke(Color.primary.opacity(0.08), lineWidth: 14)
                    Circle()
                        .trim(from: 0.03, to: model.isTunnelBusy ? 0.76 : 0.97)
                        .stroke(
                            AngularGradient(colors: [QeliTheme.primary, QeliTheme.secondary, QeliTheme.primary], center: .center),
                            style: StrokeStyle(lineWidth: 14, lineCap: .round)
                        )
                        .rotationEffect(.degrees(model.isTunnelBusy ? 160 : -90))
                        .animation(.easeInOut(duration: 0.7), value: model.tunnelSnapshot.phase)
                    VStack(spacing: 8) {
                        Image(systemName: "power")
                            .font(.system(size: 42, weight: .semibold))
                        Text(ringHint)
                            .font(.caption2.weight(.semibold))
                            .tracking(1.1)
                    }
                    .foregroundStyle(.primary)
                }
                .frame(width: 190, height: 190)
                .contentShape(Circle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(ringHint)

            HStack(spacing: 9) {
                Circle().fill(statusColor).frame(width: 11, height: 11)
                Text(statusTitle).font(.title3.bold())
                if let address = model.tunnelSnapshot.clientAddress {
                    Text("IP \(address)").font(.caption).foregroundStyle(QeliTheme.primary)
                }
            }
            if !model.tunnelSnapshot.message.isEmpty {
                Text(model.tunnelSnapshot.message)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                    .multilineTextAlignment(.center)
            }
            if model.tunnelSnapshot.phase == .connected {
                Text("↓ \(formatRate(model.tunnelSnapshot.downloadBytesPerSecond))   ↑ \(formatRate(model.tunnelSnapshot.uploadBytesPerSecond))")
                    .font(.caption.monospaced())
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity)
        .qeliCard(padding: 20)
    }

    private var activeProfileCard: some View {
        HStack(spacing: 12) {
            Circle().fill(reachabilityColor).frame(width: 10, height: 10)
            VStack(alignment: .leading, spacing: 2) {
                Text("ACTIVE PROFILE").font(.caption2).foregroundStyle(.secondary)
                Text(model.activeProfile?.name ?? "—").font(.headline).lineLimit(1)
                Text(reachabilityText).font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            Button("Ping") {
                if let profile = model.activeProfile { model.ping(profile) }
            }
            .buttonStyle(.bordered)
            .tint(QeliTheme.primary)
        }
        .qeliCard()
    }

    private var statisticsCard: some View {
        TimelineView(.periodic(from: .now, by: 1)) { _ in
            HStack(spacing: 0) {
                statistic("UPTIME", formatDuration(model.tunnelSnapshot.uptime), color: .primary)
                Divider().frame(height: 42)
                statistic("↓ DOWNLOAD", formatBytes(model.tunnelSnapshot.bytesDownloaded), color: QeliTheme.connected)
                Divider().frame(height: 42)
                statistic("↑ UPLOAD", formatBytes(model.tunnelSnapshot.bytesUploaded), color: QeliTheme.primary)
            }
            .qeliCard()
        }
    }

    /// What the active profile actually protects.
    ///
    /// Mirrors the Android card decision for decision (both read `ProtectionSummary`), with
    /// two platform differences that are real rather than cosmetic: per-app routing needs
    /// MDM on iOS, and there is no Always-On switch an app may offer — VPN On Demand in
    /// Settings is the closest equivalent. Both are stated, not hidden.
    @ViewBuilder
    private var protectionCard: some View {
        let config = model.activeProfile.flatMap { try? VPNConfig(parsing: $0.configText) }
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text("PROTECTION")
                    .font(.system(size: 11, weight: .semibold))
                    .kerning(0.8)
                    .foregroundStyle(.secondary)
                Spacer()
                Image(systemName: "chevron.right").font(.caption2).foregroundStyle(.secondary)
            }
            if let config {
                let summary = ProtectionSummary(config: config)
                let live = model.tunnelSnapshot.phase == .connected
                Text(headline(summary, live: live))
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(live && summary.carriesEverything ? QeliTheme.connected : .primary)
                Text("\(Text(summary.postQuantum ? "Hybrid post-quantum" : "X25519 (no post-quantum)")) · \(Text(summary.dnsThroughTunnel ? "DNS through VPN" : "system DNS"))")
                    .font(.caption).foregroundStyle(.secondary)
                Text("\(config.wireMode) · \(config.protocolName.uppercased())\(config.quicEnabled ? " / QUIC" : "") · \(Text(summary.keyPinned ? "server key pinned" : "server key on trust (TOFU)"))")
                    .font(.caption).foregroundStyle(.secondary)
                if let warning = summary.warnings.first {
                    Text(warningText(warning, count: summary.excludedRouteCount))
                        .font(.caption)
                        .foregroundStyle(QeliTheme.connecting)
                }
            } else {
                Text(model.activeProfile == nil ? "No profile selected" : "Profile config is invalid")
                    .font(.system(size: 15, weight: .semibold))
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .qeliCard()
        .contentShape(Rectangle())
        .onTapGesture { if config != nil { showingProtectionDetails = true } }
        .sheet(isPresented: $showingProtectionDetails) {
            if let config { protectionDetails(config) }
        }
    }

    /// The full picture behind the card. Negotiated rows (DNS, MTU, streams, pushed routes)
    /// come from the tunnel snapshot and are simply omitted while disconnected — never
    /// guessed from the profile.
    private func protectionDetails(_ config: VPNConfig) -> some View {
        let summary = ProtectionSummary(config: config)
        let snapshot = model.tunnelSnapshot
        let live = snapshot.phase == .connected
        return NavigationStack {
            List {
                detailRow("Server", "\(config.serverAddress):\(config.port)")
                detailRow(
                    "Transport",
                    "\(config.wireMode) / \(config.protocolName.uppercased())\(config.quicEnabled ? " + QUIC" : "")"
                )
                detailRow("Encryption", summary.postQuantum
                    ? String(localized: "Hybrid post-quantum") : String(localized: "X25519 (no post-quantum)"))
                detailRow("Server key", summary.keyPinned
                    ? String(localized: "server key pinned") : String(localized: "server key on trust (TOFU)"))
                if live {
                    if let dns = snapshot.pushedDNS ?? config.dnsServers.first {
                        detailRow("DNS", dns)
                    }
                    if let mtu = snapshot.appliedMTU {
                        detailRow("MTU", config.mtu > 0 ? "\(mtu)" : "\(mtu) (auto)")
                    }
                    if snapshot.maxStreams > 1 {
                        detailRow("Multipath", String(
                            format: String(localized: "up to %lld streams"), snapshot.maxStreams))
                    }
                    if snapshot.pushedRoutes > 0 {
                        detailRow("Pushed routes", "\(snapshot.pushedRoutes)")
                    }
                }
                detailRow("Routing", routingText(summary))
                detailRow("Auto-reconnect", config.reconnectEnabled
                    ? String(localized: "On") : String(localized: "Off"))
            }
            .navigationTitle("PROTECTION")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Close") { showingProtectionDetails = false }
                }
            }
        }
    }

    private func detailRow(_ label: LocalizedStringKey, _ value: String) -> some View {
        HStack {
            Text(label).foregroundStyle(.secondary)
            Spacer()
            Text(value).multilineTextAlignment(.trailing)
        }
        .font(.callout)
    }

    private func routingText(_ summary: ProtectionSummary) -> String {
        switch summary.scope {
        case .all: return String(localized: "All apps (default)")
        case .onlySelected: return String(localized: "Only selected apps are protected")
        case .allExcept: return String(localized: "All apps except the selected ones are protected")
        case .splitRoutes: return String(localized: "Split tunnel — only selected routes")
        }
    }

    private func headline(_ summary: ProtectionSummary, live: Bool) -> LocalizedStringKey {
        guard live else { return "Will be used on connect" }
        switch summary.scope {
        case .onlySelected: return "Only selected apps are protected"
        case .allExcept: return "All apps except the selected ones are protected"
        case .splitRoutes: return "Split tunnel — only selected routes"
        case .all:
            // Full scope but something is carved out — the warning line says what, so the
            // headline must not claim "everything".
            return summary.carriesEverything ? "All traffic is protected" : "Split tunnel — only selected routes"
        }
    }

    private func warningText(_ warning: ProtectionWarning, count: Int) -> LocalizedStringKey {
        switch warning {
        case .lanOutside: return "Local network stays outside the tunnel"
        case .ipv6Outside: return "IPv6 bypasses the tunnel"
        case .excludedRoutes: return "\(count) route(s) excluded from the tunnel"
        case .noPinnedKey: return "Without a pinned key the first connection is trusted blindly"
        // Says which way it is wrong: the selection is IGNORED and everything is tunnelled,
        // not "some apps are unprotected". (Audit 2026-08-02, §7.)
        case .perAppNotApplied: return "Per-app selection needs MDM on iOS — every app is tunnelled"
        }
    }

    private func statistic(_ title: LocalizedStringKey, _ value: String, color: Color) -> some View {
        VStack(spacing: 3) {
            Text(title).font(.system(size: 9, weight: .medium)).foregroundStyle(.secondary)
            Text(value).font(.subheadline.bold().monospaced()).foregroundStyle(color).lineLimit(1).minimumScaleFactor(0.65)
        }
        .frame(maxWidth: .infinity)
    }

    private var statusTitle: LocalizedStringKey {
        switch model.tunnelSnapshot.phase {
        case .disconnected: return "Disconnected"
        case .preparing, .connecting: return "Connecting…"
        case .connected: return "Connected"
        case .reconnecting: return "Reconnecting…"
        case .disconnecting: return "Disconnecting…"
        case .error: return "Error"
        }
    }

    private var ringHint: LocalizedStringKey {
        switch model.tunnelSnapshot.phase {
        case .disconnected: return "TAP TO CONNECT"
        case .error: return "TAP TO RETRY"
        case .connected: return "TAP TO DISCONNECT"
        default: return "TAP TO CANCEL"
        }
    }

    private var statusColor: Color {
        switch model.tunnelSnapshot.phase {
        case .connected: return QeliTheme.connected
        case .preparing, .connecting, .reconnecting, .disconnecting: return QeliTheme.connecting
        case .error: return QeliTheme.error
        case .disconnected: return QeliTheme.disconnected
        }
    }

    private var reachabilityText: String {
        guard let id = model.activeProfile?.id else { return "No profile" }
        switch model.reachability[id] ?? .idle {
        case .idle: return "tap Ping to check"
        case .checking: return "checking…"
        case .reachable(let milliseconds): return "reachable · \(milliseconds) ms"
        case .unavailable(let reason): return reason
        }
    }

    private var reachabilityColor: Color {
        guard let id = model.activeProfile?.id else { return .secondary }
        switch model.reachability[id] ?? .idle {
        case .reachable: return QeliTheme.connected
        case .unavailable: return QeliTheme.error
        case .checking: return QeliTheme.connecting
        case .idle: return .secondary
        }
    }

    private func formatRate(_ bytes: UInt64) -> String { "\(formatBytes(bytes))/s" }
    private func formatBytes(_ bytes: UInt64) -> String {
        let units = ["B", "KB", "MB", "GB", "TB"]
        var value = Double(bytes); var unit = 0
        while value >= 1_024, unit < units.count - 1 { value /= 1_024; unit += 1 }
        return unit == 0 ? "\(Int(value)) \(units[unit])" : String(format: "%.1f %@", value, units[unit])
    }
    private func formatDuration(_ interval: TimeInterval) -> String {
        let seconds = Int(interval)
        return String(format: "%02d:%02d:%02d", seconds / 3_600, (seconds / 60) % 60, seconds % 60)
    }
}
