using Qeli.Shared.Model;

namespace Qeli.Conformance;

internal static class ProfileStoreConformance
{
    public static void Run(Action<string, bool> check)
    {
        var dir = Path.Combine(Path.GetTempPath(), "qeli-profile-store-test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        try
        {
            var path = Path.Combine(dir, "profiles.json");
            byte[] original = [0x00, 0xFF, 0x5A];
            File.WriteAllBytes(path, original);
            var preserved = ProfileStoreRecovery.PreserveUnreadable(path);
            check("profile store: quarantine preserves exact bytes before empty recovery",
                !File.Exists(path) && File.ReadAllBytes(preserved).SequenceEqual(original));

            bool failedClosed = false;
            try { ProfileStoreRecovery.PreserveUnreadable(path); }
            catch (IOException) { failedClosed = true; }
            check("profile store: failed quarantine refuses empty recovery", failedClosed);
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }
}
