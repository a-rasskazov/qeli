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

            var livePath = Path.Combine(dir, "live-profiles.json");
            var first = new ProfileStoreFile(livePath);
            var second = new ProfileStoreFile(livePath);
            check("profile store: both instances observe an absent initial file",
                first.Read() is null && second.Read() is null);
            first.Write([1, 2, 3]);
            bool staleCreateRejected = false;
            try { second.Write([4]); }
            catch (IOException) { staleCreateRejected = true; }
            check("profile store: stale create cannot replace another instance",
                staleCreateRejected && File.ReadAllBytes(livePath).SequenceEqual(new byte[] { 1, 2, 3 }));

            check("profile store: second instance reloads the current bytes",
                second.Read()?.SequenceEqual(new byte[] { 1, 2, 3 }) == true);
            second.Write([4, 5]);
            bool staleUpdateRejected = false;
            try { first.Write([6]); }
            catch (IOException) { staleUpdateRejected = true; }
            check("profile store: stale update preserves the newer file and backup",
                staleUpdateRejected
                && File.ReadAllBytes(livePath).SequenceEqual(new byte[] { 4, 5 })
                && File.ReadAllBytes(livePath + ".bak").SequenceEqual(new byte[] { 1, 2, 3 }));

            first.Read();
            second.Write([7]);
            bool staleQuarantineRejected = false;
            try { first.PreserveUnreadable(); }
            catch (IOException) { staleQuarantineRejected = true; }
            check("profile store: stale quarantine cannot move a newer valid file",
                staleQuarantineRejected && File.ReadAllBytes(livePath).SequenceEqual(new byte[] { 7 }));

            first.Read();
            var quarantine = first.PreserveUnreadable();
            first.Write([8]);
            check("profile store: quarantine allows a fresh store while preserving original bytes",
                File.ReadAllBytes(quarantine).SequenceEqual(new byte[] { 7 })
                && File.ReadAllBytes(livePath).SequenceEqual(new byte[] { 8 }));

            bool lockRejected = false;
            using (var held = new FileStream(livePath + ".lock", FileMode.Open, FileAccess.ReadWrite, FileShare.None))
            {
                try { first.Write([9]); }
                catch (IOException) { lockRejected = true; }
            }
            check("profile store: sidecar lock prevents a concurrent write",
                lockRejected && File.ReadAllBytes(livePath).SequenceEqual(new byte[] { 8 }));
            first.Write([9]);
            check("profile store: write succeeds after the lock is released",
                File.ReadAllBytes(livePath).SequenceEqual(new byte[] { 9 }));

            var oversizedPath = Path.Combine(dir, "oversized-profiles.json");
            using (var large = File.Create(oversizedPath))
                large.SetLength(ProfileStoreFile.MaximumStoredBytes + 1L);
            var bounded = new ProfileStoreFile(oversizedPath);
            bool oversizedReadRejected = false;
            try { bounded.Read(); }
            catch (IOException) { oversizedReadRejected = true; }
            check("profile store: oversized input is refused before loading and preserved",
                oversizedReadRejected
                && new FileInfo(oversizedPath).Length == ProfileStoreFile.MaximumStoredBytes + 1L);

            File.WriteAllBytes(oversizedPath, [1]);
            bounded.Read();
            using (var large = new FileStream(oversizedPath, FileMode.Open, FileAccess.Write, FileShare.None))
                large.SetLength(ProfileStoreFile.MaximumStoredBytes + 1L);
            bool oversizedRevisionRejected = false;
            try { bounded.Write([2]); }
            catch (IOException) { oversizedRevisionRejected = true; }
            check("profile store: an oversized replacement blocks a stale write",
                oversizedRevisionRejected
                && new FileInfo(oversizedPath).Length == ProfileStoreFile.MaximumStoredBytes + 1L);

            bool oversizedOutputRejected = false;
            try { bounded.Write(new byte[ProfileStoreFile.MaximumStoredBytes + 1]); }
            catch (IOException) { oversizedOutputRejected = true; }
            check("profile store: oversized output is refused without changing the file",
                oversizedOutputRejected
                && new FileInfo(oversizedPath).Length == ProfileStoreFile.MaximumStoredBytes + 1L);
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }
}
