import Foundation

/// In-tunnel control frames — small typed messages carried as ordinary AEAD records alongside
/// the IP packets. Port of `qeli/src/protocol/ctrl.rs`.
///
/// Why in-tunnel: the one thing that needs sending — the tunnel MTU this client settled on — is
/// only known AFTER the handshake (on UDP it comes out of the path-MTU probe), so no handshake
/// field can carry it. Riding inside the tunnel also means the frame inherits the session's AEAD
/// and replay protection, instead of being a bare datagram whose only identity is a source
/// address anyone could spoof.
///
/// Wire: `[0xC1][0x9B][type(1)][len(1)][body(len)]`. The tunnel's plaintext is otherwise an IP
/// packet (or empty, for the heartbeat); `0xC1`'s high nibble is `0xC`, which is neither 4 nor 6,
/// so a control frame can never be confused with IPv4/IPv6 in either direction.
///
/// Additive: a server that predates this has no branch for the frame and discards it as a
/// malformed packet, keeping its profile MTU — exactly its old behaviour. Nothing waits for a
/// reply.
enum CtrlFrame {
    static let magic: [UInt8] = [0xC1, 0x9B]
    /// magic(2) + type(1) + len(1)
    static let headerLength = 4
    /// Client→server MTU report. Body: `[mtu(2 BE)]`.
    static let typeMTUReport: UInt8 = 1

    /// Build the MTU report frame for `mtu`.
    static func mtuReport(_ mtu: Int) -> Data {
        let clamped = UInt16(min(max(mtu, 0), Int(UInt16.max)))
        var frame = Data(magic)
        frame.append(typeMTUReport)
        frame.append(2)
        frame.append(UInt8(clamped >> 8))
        frame.append(UInt8(clamped & 0xFF))
        return frame
    }

    /// True if a decrypted tunnel plaintext is a control frame, not an IP packet.
    static func isCtrl(_ plaintext: Data) -> Bool {
        plaintext.count >= headerLength
            && plaintext[plaintext.startIndex] == magic[0]
            && plaintext[plaintext.index(plaintext.startIndex, offsetBy: 1)] == magic[1]
    }
}
