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
    /// <summary>Client→server: what this build is, so `list-clients` and the panel can answer
    /// "who still needs to update?". Body: <c>[verLen(1)][version][platform]</c>.
    ///
    /// SELF-REPORTED, NOT ATTESTED. Any authenticated peer can claim any string, so this is
    /// diagnostics only and must never gate anything.</summary>
    public const byte TypeClientInfo = 2;

    // Caps mirror ctrl.rs. Deliberately small: the value is peer-chosen and ends up in a CLI
    // table, the JSON API, the panel's DOM and the log.
    public const int MaxVersionLen = 32;
    public const int MaxPlatformLen = 16;

    /// <summary>Semver plus the punctuation real builds use. The server refuses anything else
    /// OUTRIGHT rather than scrubbing it, so a frame that would be rejected there must not be
    /// built here either — otherwise the client reports nothing and cannot tell why.</summary>
    private static bool ValidVersion(string s) =>
        s.Length is > 0 and <= MaxVersionLen
        && s.All(c => char.IsAsciiLetterOrDigit(c) || c is '.' or '-' or '+' or '_');

    /// <summary>A short lowercase identifier: linux, windows, macos, android, ios, …</summary>
    private static bool ValidPlatform(string s) =>
        s.Length is > 0 and <= MaxPlatformLen
        && s.All(c => char.IsAsciiLetterLower(c) || char.IsAsciiDigit(c) || c == '-');

    /// <summary>The platform tag this build reports — a closed set, like ctrl.rs. An
    /// unrecognised OS reads as <c>other</c> rather than putting a raw platform string in front
    /// of the operator. qeli-shared is used by both the Windows and macOS apps, so this is a
    /// RUNTIME check, not a compile-time one.</summary>
    public static string PlatformTag()
    {
        if (OperatingSystem.IsWindows()) return "windows";
        if (OperatingSystem.IsMacOS()) return "macos";
        if (OperatingSystem.IsLinux()) return "linux";
        if (OperatingSystem.IsAndroid()) return "android";
        if (OperatingSystem.IsIOS()) return "ios";
        if (OperatingSystem.IsFreeBSD()) return "freebsd";
        return "other";
    }

    /// <summary>Build the client-info frame, or null when either field breaks the caps or the
    /// charset — the caller then sends nothing and the server shows the session as unknown,
    /// which is exactly the pre-feature behaviour.</summary>
    public static byte[]? ClientInfo(string version, string platform)
    {
        if (!ValidVersion(version) || !ValidPlatform(platform)) return null;
        var v = System.Text.Encoding.ASCII.GetBytes(version);
        var p = System.Text.Encoding.ASCII.GetBytes(platform);
        int bodyLen = 1 + v.Length + p.Length;
        if (bodyLen > byte.MaxValue) return null;

        var f = new byte[HdrLen + bodyLen];
        f[0] = Magic[0]; f[1] = Magic[1]; f[2] = TypeClientInfo; f[3] = (byte)bodyLen;
        f[4] = (byte)v.Length;
        Buffer.BlockCopy(v, 0, f, 5, v.Length);
        Buffer.BlockCopy(p, 0, f, 5 + v.Length, p.Length);
        return f;
    }

    /// <summary>This build's own client-info frame: the assembly version stamped by
    /// <c>sync_version.py</c> plus <see cref="PlatformTag"/>. Reads the version off THIS
    /// assembly rather than the entry one, so the Windows app, the macOS app and the CLI all
    /// report the same single project version.</summary>
    public static byte[]? ThisBuild()
    {
        var v = typeof(CtrlFrame).Assembly.GetName().Version;
        return v == null ? null : ClientInfo($"{v.Major}.{v.Minor}.{v.Build}", PlatformTag());
    }

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
