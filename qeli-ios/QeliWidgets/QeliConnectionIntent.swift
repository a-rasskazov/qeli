import AppIntents
import Foundation
import NetworkExtension
import WidgetKit

enum QeliWidgetIntentError: LocalizedError {
    case appGroupUnavailable
    case controlsDisabled
    case tunnelNotInstalled

    var errorDescription: String? {
        switch self {
        case .appGroupUnavailable:
            return "Qeli could not write the control request to its shared App Group."
        case .controlsDisabled:
            return "Your organization disabled Qeli widget controls."
        case .tunnelNotInstalled:
            return "Open Qeli once to install the VPN configuration before using the widget."
        }
    }
}

struct QeliToggleConnectionIntent: AppIntent {
    static var title: LocalizedStringResource = "Toggle Qeli VPN"
    static var description = IntentDescription("Connect or disconnect the active Qeli profile.")
    // Toggling must not drag the app to the foreground — the Android widget and
    // Quick Settings tile connect in one silent tap, and this is the surface that has to
    // mirror them. `issue(_:)` drives the tunnel directly and only asks for the app when
    // the extension genuinely cannot do it.
    static var openAppWhenRun = false
    static var isDiscoverable = false
    static var authenticationPolicy: IntentAuthenticationPolicy = .requiresAuthentication

    func perform() async throws -> some IntentResult {
        let current = SharedTunnelStore().snapshot()
        let command: QeliConnectionCommand = current.phase.isActive ? .disconnect : .connect
        try await issue(command)
        return .result()
    }
}

@available(iOS 18.0, *)
struct QeliSetConnectionIntent: SetValueIntent {
    static var title: LocalizedStringResource = "Set Qeli VPN Connection"
    static var description = IntentDescription("Connect or disconnect the active Qeli profile.")
    // Toggling must not drag the app to the foreground — the Android widget and
    // Quick Settings tile connect in one silent tap, and this is the surface that has to
    // mirror them. `issue(_:)` drives the tunnel directly and only asks for the app when
    // the extension genuinely cannot do it.
    static var openAppWhenRun = false
    static var isDiscoverable = false
    static var authenticationPolicy: IntentAuthenticationPolicy = .requiresAuthentication

    @Parameter(title: "Connected")
    var value: Bool

    func perform() async throws -> some IntentResult {
        try await issue(value ? .connect : .disconnect)
        return .result()
    }
}

private func issue(_ command: QeliConnectionCommand) async throws {
    guard WidgetControlBridge.widgetControlsEnabled else {
        throw QeliWidgetIntentError.controlsDisabled
    }
    // Record the request first. If driving the tunnel from here fails (no saved VPN
    // configuration yet, or the system refuses the start), the app applies the queued
    // command the next time it is opened — the pre-existing behaviour, kept as a fallback
    // rather than as the only path.
    guard WidgetControlBridge.issue(command) != nil else {
        throw QeliWidgetIntentError.appGroupUnavailable
    }
    NotificationCenter.default.post(name: .qeliWidgetControlRequestAvailable, object: nil)
    defer { WidgetCenter.shared.reloadTimelines(ofKind: AppConstants.statusWidgetKind) }
    try await applyDirectly(command)
}

/// Start/stop the already-installed tunnel from the widget process, so the toggle takes
/// effect without foregrounding the app. The configuration is created and saved by the
/// app (`TunnelManager.prepare`); this only flips the session on it.
private func applyDirectly(_ command: QeliConnectionCommand) async throws {
    let managers = try await NETunnelProviderManager.loadAllFromPreferences()
    guard let manager = managers.first else { throw QeliWidgetIntentError.tunnelNotInstalled }
    switch command {
    case .connect:
        // A disabled configuration silently refuses to start.
        if !manager.isEnabled {
            manager.isEnabled = true
            try await manager.saveToPreferences()
            try await manager.loadFromPreferences()
        }
        try manager.connection.startVPNTunnel()
    case .disconnect:
        manager.connection.stopVPNTunnel()
    }
}
