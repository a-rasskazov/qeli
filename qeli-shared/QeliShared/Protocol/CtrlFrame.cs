namespace Qeli.Shared.Protocol;

/// <summary>
/// In-tunnel control frames — small typed messages carried as ordinary AEAD records
/// alongside the IP packets. Port of qeli/src/protocol/ctrl.rs.
///
/// Why in-tunnel: the one thing that needs sending — the tunnel MTU this client settled on —
/// is only known AFTER the handshake (on UDP it comes out of the path-MTU probe), so no
/// handshake field can carry it. Riding inside the tunnel also means the frame inherits the
/// session's AEAD and replay protection, instead of being a bare datagram whose only identity
/// is a source address anyone could spoof.
///
/// Wire: <c>[0xC1][0x9B][type(1)][len(1)][body(len)]</c>. The tunnel's plaintext is otherwise
/// an IP packet (or empty, for the heartbeat); 0xC1's high nibble is 0xC, which is neither 4
/// nor 6, so a control frame can never be confused with IPv4/IPv6 in either direction.
///
/// Additive: a server that predates this has no branch for the frame and discards it as a
/// malformed packet, keeping its profile MTU — exactly its old behaviour. Nothing waits for a
/// reply.
/// </summary>
public static class CtrlFrame
{
    public static readonly byte[] Magic = { 0xC1, 0x9B };
    public const int HdrLen = 4;              // magic(2) + type(1) + len(1)
    public const byte TypeMtuReport = 1;      // body: [mtu(2 BE)]

    /// <summary>Build the MTU report frame for <paramref name="mtu"/>.</summary>
    public static byte[] MtuReport(int mtu)
    {
        ushort m = (ushort)System.Math.Clamp(mtu, 0, ushort.MaxValue);
        return new byte[] { Magic[0], Magic[1], TypeMtuReport, 2, (byte)(m >> 8), (byte)(m & 0xFF) };
    }

    /// <summary>True if a decrypted tunnel plaintext is a control frame, not an IP packet.</summary>
    public static bool IsCtrl(byte[] p) =>
        p.Length >= HdrLen && p[0] == Magic[0] && p[1] == Magic[1];
}
