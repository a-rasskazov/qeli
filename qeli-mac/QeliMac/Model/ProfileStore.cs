using System.IO;
using System.Text;
using System.Text.Json;
using Qeli.Shared.Model;

namespace QeliMac.Model;

/// <summary>Persists the profile list to ~/Library/Application Support/Qeli/profiles.json,
/// encrypted at rest with AES-256-GCM. Profiles carry the server password and
/// obfs_key, so they must not sit in plaintext; the AES key comes from the macOS
/// Keychain (see <see cref="SecureKey"/>). A legacy plaintext file (pre-E1) is read
/// transparently and re-written into a versioned authenticated envelope.
/// See docs/*/archive/plans/RELEASE-FIXES.md E1.</summary>
public static class ProfileStore
{
    private static readonly string Dir = Paths.UserDir;
    private static readonly string FilePath = Path.Combine(Dir, "profiles.json");
    private static readonly JsonSerializerOptions Options = new() { WriteIndented = true };
    private static readonly UTF8Encoding StrictUtf8 = new(false, true);

    public static List<VpnConfig> Load()
    {
        // Absent file = normal first run. Only a PRESENT-but-unreadable file is dangerous.
        if (!File.Exists(FilePath)) return new List<VpnConfig>();
        List<VpnConfig> profiles;
        bool needsMigration;
        try
        {
            var raw = File.ReadAllBytes(FilePath);
            var plaintext = EncryptedEnvelope.Open(
                raw, SecureKey.GetOrCreate(), allowLegacyArray: true, out bool needsEnvelopeMigration);
            string json = StrictUtf8.GetString(plaintext);
            profiles = JsonSerializer.Deserialize<List<VpnConfig>>(json, Options) ?? new List<VpnConfig>();
            // Profiles saved before the stable-Id fix have no "Id" field; the deserializer
            // left each at a fresh-GUID default that would otherwise change on every load
            // (settings reference profiles by Id). Persist once to freeze those Ids.
            bool needsIdMigration = profiles.Count > 0 && !json.Contains("\"Id\":");
            needsMigration = needsEnvelopeMigration || needsIdMigration;
        }
        catch (Exception ex)
        {
            // Keep the unreadable original before attempting .bak recovery. Failure to
            // preserve it must stop loading, rather than allow a later Save to overwrite it.
            var preserved = ProfileStoreRecovery.PreserveUnreadable(FilePath);
            System.Diagnostics.Debug.WriteLine(
                $"ProfileStore: profiles.json unreadable, preserved at {preserved} ({ex.Message})");

            // File.Replace keeps one last authenticated generation. Recover it automatically
            // instead of opening with an empty profile list after a torn/corrupt latest write.
            List<VpnConfig>? recovered = null;
            try
            {
                var backup = FilePath + ".bak";
                if (File.Exists(backup))
                {
                    var plaintext = EncryptedEnvelope.Open(
                        File.ReadAllBytes(backup), SecureKey.GetOrCreate(), true, out _);
                    recovered = JsonSerializer.Deserialize<List<VpnConfig>>(
                        StrictUtf8.GetString(plaintext), Options) ?? new List<VpnConfig>();
                }
            }
            catch (Exception backupError)
            {
                System.Diagnostics.Debug.WriteLine($"ProfileStore: .bak recovery failed ({backupError.Message})");
            }
            if (recovered is null) return new List<VpnConfig>();

            // A write failure must propagate instead of hiding the successfully read backup.
            Save(recovered);
            System.Diagnostics.Debug.WriteLine("ProfileStore: restored profiles from authenticated .bak");
            return recovered;
        }

        // Do not quarantine a readable store if only its migration write fails.
        if (needsMigration) Save(profiles);
        return profiles;
    }

    public static void Save(IEnumerable<VpnConfig> profiles)
    {
        Directory.CreateDirectory(Dir);
        var key = SecureKey.GetOrCreate();
        var pt = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(profiles, Options));
        var blob = EncryptedEnvelope.Seal(pt, key);
        // Atomic write (temp born 0600 + replace): a crash mid-write must not truncate the
        // only copy, and the secret ciphertext must never briefly be world-readable.
        var tmp = FilePath + ".tmp";
        File.WriteAllBytes(tmp, blob);
        if (!OperatingSystem.IsWindows())
            try { File.SetUnixFileMode(tmp, UnixFileMode.UserRead | UnixFileMode.UserWrite); } catch { }
        if (File.Exists(FilePath))
            File.Replace(tmp, FilePath, FilePath + ".bak");
        else
            File.Move(tmp, FilePath);
    }
}
