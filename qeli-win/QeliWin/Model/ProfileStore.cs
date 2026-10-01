using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Qeli.Shared.Model;

namespace QeliWin.Model;

/// <summary>Persists the profile list to %APPDATA%\QeliWin\profiles.json,
/// encrypted at rest with DPAPI (current-user scope) — profiles carry the server
/// password and obfs_key, so they must not sit in plaintext. A legacy plaintext
/// file (pre-E1) is read transparently and re-written encrypted on load.</summary>
public static class ProfileStore
{
    private static readonly string Dir =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "QeliWin");
    private static readonly string FilePath = Path.Combine(Dir, "profiles.json");

    private static readonly JsonSerializerOptions Options = new() { WriteIndented = true };
    private static readonly UTF8Encoding StrictUtf8 = new(false, true);
    private static readonly ProfileStoreFile StoreFile = new(FilePath);

    public static List<VpnConfig> Load()
    {
        // Absent file = normal first run. Only a PRESENT-but-unreadable file is dangerous.
        var stored = StoreFile.Read();
        if (stored is null) return new List<VpnConfig>();
        List<VpnConfig> profiles;
        bool needsMigration;
        try
        {
            var bytes = stored;
            string json;
            bool wasLegacyPlaintext = false;
            try
            {
                // Encrypted-at-rest (DPAPI, current user).
                var plain = ProtectedData.Unprotect(bytes, null, DataProtectionScope.CurrentUser);
                json = StrictUtf8.GetString(plain);
            }
            catch (CryptographicException)
            {
                // Only a DPAPI decryption failure can select the legacy plaintext path.
                // A malformed decrypted payload must never be reinterpreted as legacy.
                json = StrictUtf8.GetString(bytes);
                wasLegacyPlaintext = true;
            }
            // Persist missing legacy IDs once, including a mixed old/new profile list.
            profiles = ProfileStorePayload.Decode(json, out bool needsIdMigration, Options);
            needsMigration = wasLegacyPlaintext || needsIdMigration;
        }
        catch (Exception ex)
        {
            // Do not expose an empty store while the unreadable file remains at FilePath.
            // A failed quarantine is fatal so a later Save cannot overwrite that file.
            var preserved = StoreFile.PreserveUnreadable();
            System.Diagnostics.Debug.WriteLine(
                $"ProfileStore: profiles.json unreadable, preserved at {preserved} ({ex.Message})");
            return new List<VpnConfig>();
        }

        // A failed migration write does not make an otherwise valid store corrupt.
        // Let it fail without moving the readable source out of the way.
        if (needsMigration) Save(profiles);
        return profiles;
    }

    public static void Save(IEnumerable<VpnConfig> profiles)
    {
        Directory.CreateDirectory(Dir);
        var json = ProfileStorePayload.Encode(profiles, Options);
        var enc = ProtectedData.Protect(Encoding.UTF8.GetBytes(json), null, DataProtectionScope.CurrentUser);
        StoreFile.Write(enc);
    }
}
