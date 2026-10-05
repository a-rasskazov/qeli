using System.Diagnostics;

namespace QeliMac.Model;

/// <summary>
/// Provides the 256-bit AES key used to encrypt the at-rest profile store
/// (<see cref="ProfileStore"/>). The key lives in the macOS login Keychain,
/// accessed directly through Security.framework with an explicit ACL for the current code-signing
/// identity. A Developer-ID release therefore keeps access across upgrades while
/// unrelated processes cannot reuse `/usr/bin/security` as a trusted proxy. If
/// the Keychain is unavailable we can use an existing local key file with 0600 permissions — still AES-encrypted at rest
/// (no plaintext password/obfs_key on disk), just with a weaker key store.
/// </summary>
public static class SecureKey
{
    private const string Service = "ru.qeli.mac";
    private const string Account = "profile-store-key";
    private static readonly ProfileKeyCoordinator Keys = new(Paths.UserDir,
        () => MacKeychain.Find(Service, Account),
        (key, allowUpdate) => MacKeychain.Store(Service, Account, key, allowUpdate),
        LegacyKeychainFind, LegacyKeychainDelete);

    public static byte[] GetOrCreate() => Keys.GetOrCreate();

    private static byte[]? LegacyKeychainFind()
    {
        var (code, output) = Run($"find-generic-password -s {Service} -a {Account} -w");
        if (code != 0 || output.Length == 0) return null;
        try { return Convert.FromBase64String(output.Trim()); }
        catch { return null; }
    }

    private static bool LegacyKeychainDelete()
    {
        var (code, _) = Run($"delete-generic-password -s {Service} -a {Account}");
        return code == 0;
    }

    private static (int, string) Run(string args, string? stdin = null)
    {
        try
        {
            var psi = new ProcessStartInfo("/usr/bin/security", args)
            {
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                RedirectStandardInput = stdin != null,
                UseShellExecute = false,
            };
            using var p = Process.Start(psi)!;
            // Drain both pipes concurrently and bound the wait: reading stdout to EOF and
            // only then stderr deadlocks if `security` fills the stderr buffer first, and
            // an unbounded WaitForExit lets a Keychain prompt hang the app. (C-19/C-24)
            var so = p.StandardOutput.ReadToEndAsync();
            var se = p.StandardError.ReadToEndAsync();
            if (stdin != null)
            {
                p.StandardInput.Write(stdin);
                p.StandardInput.Close();
            }
            if (!p.WaitForExit(20_000))
            {
                try { p.Kill(entireProcessTree: true); } catch { /* best effort */ }
                return (-1, "");
            }
            _ = se.GetAwaiter().GetResult();
            return (p.ExitCode, so.GetAwaiter().GetResult());
        }
        catch { return (-1, ""); }
    }

}
