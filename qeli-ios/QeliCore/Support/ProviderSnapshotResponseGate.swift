/// Orders asynchronous provider replies and invalidates replies across tunnel transitions.
/// The container's MainActor owns this value; no provider callback mutates it directly.
struct ProviderSnapshotResponseGate {
    struct Token {
        fileprivate let epoch: UInt64
        fileprivate let sequence: UInt64
    }

    private var epoch: UInt64 = 0
    private var issued: UInt64 = 0
    private var accepted: UInt64 = 0

    mutating func invalidate() {
        epoch &+= 1
        issued = 0
        accepted = 0
    }

    mutating func issue() -> Token {
        issued &+= 1
        return Token(epoch: epoch, sequence: issued)
    }

    mutating func accept(_ token: Token) -> Bool {
        guard token.epoch == epoch, token.sequence > accepted,
              token.sequence <= issued else { return false }
        accepted = token.sequence
        return true
    }
}
