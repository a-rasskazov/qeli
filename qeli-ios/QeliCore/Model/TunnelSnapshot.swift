import Foundation

enum TunnelPhase: String, Codable, Sendable {
    case disconnected
    case preparing
    case connecting
    case connected
    case reconnecting
    case disconnecting
    case error

    var isActive: Bool {
        switch self {
        case .preparing, .connecting, .connected, .reconnecting, .disconnecting: return true
        case .disconnected, .error: return false
        }
    }
}

struct TunnelSnapshot: Codable, Equatable, Sendable {
    var phase: TunnelPhase = .disconnected
    var message = ""
    var error: String?
    var clientAddress: String?
    var connectedAt: Date?
    var bytesUploaded: UInt64 = 0
    var bytesDownloaded: UInt64 = 0
    var uploadBytesPerSecond: UInt64 = 0
    var downloadBytesPerSecond: UInt64 = 0
    var profileID: UUID?
    var updatedAt = Date()

    // ── negotiated facts the UI cannot derive from the profile ──
    // The protection card states what is actually in force, and these are only known after
    // the handshake: the server pushes DNS/MTU/routes/streams. Carried here rather than
    // scraped out of the log — log lines are the documented error-catalog surface
    // (docs/*/TROUBLESHOOTING.md), not a data channel. Mirrors the Android `live*` snapshot
    // fields on VpnServiceImpl.

    /// Resolver the server pushed; nil when it pushed none.
    var pushedDNS: String?

    /// MTU actually applied to the tunnel (explicit profile value or the pushed one).
    var appliedMTU: Int?

    /// Bonded streams the server allowed; 1 means single-stream.
    var maxStreams: Int = 1

    /// Routes the server pushed and this client applied.
    var pushedRoutes: Int = 0

    var uptime: TimeInterval {
        connectedAt.map { max(0, Date().timeIntervalSince($0)) } ?? 0
    }
}

struct TunnelLogLine: Codable, Equatable, Identifiable, Sendable {
    var id = UUID()
    var date = Date()
    var message: String
}

