using System.Security.Cryptography;

namespace Qeli.Shared.Model;

/// <summary>
/// Coordinates one local profile store across app instances. A write is allowed only
/// against the exact bytes observed by the preceding load or successful write.
/// </summary>
public sealed class ProfileStoreFile(string path)
{
    private readonly object _gate = new();
    private byte[]? _expectedHash;
    private bool _observed;

    public byte[]? Read()
    {
        lock (_gate)
        {
            using var fileLock = AcquireLock();
            var bytes = File.Exists(path) ? File.ReadAllBytes(path) : null;
            Remember(bytes);
            return bytes;
        }
    }

    public string PreserveUnreadable()
    {
        lock (_gate)
        {
            using var fileLock = AcquireLock();
            AssertUnchanged();
            var preserved = ProfileStoreRecovery.PreserveUnreadable(path);
            Remember(null);
            return preserved;
        }
    }

    public void Write(byte[] bytes)
    {
        ArgumentNullException.ThrowIfNull(bytes);
        lock (_gate)
        {
            using var fileLock = AcquireLock();
            AssertUnchanged();
            var temporary = path + ".tmp-" + Guid.NewGuid().ToString("N");
            try
            {
                var options = new FileStreamOptions
                {
                    Mode = FileMode.CreateNew,
                    Access = FileAccess.Write,
                    Share = FileShare.None,
                };
                if (!OperatingSystem.IsWindows())
                    options.UnixCreateMode = UnixFileMode.UserRead | UnixFileMode.UserWrite;
                using (var stream = new FileStream(temporary, options))
                {
                    stream.Write(bytes);
                    stream.Flush(flushToDisk: true);
                }

                if (File.Exists(path))
                    File.Replace(temporary, path, path + ".bak");
                else
                    File.Move(temporary, path);
                Remember(bytes);
            }
            finally
            {
                if (File.Exists(temporary)) File.Delete(temporary);
            }
        }
    }

    private FileStream AcquireLock()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        return new FileStream(path + ".lock", FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
    }

    private void AssertUnchanged()
    {
        if (!_observed)
            throw new IOException("Load the profile store before saving it.");
        var currentHash = File.Exists(path) ? SHA256.HashData(File.ReadAllBytes(path)) : null;
        if ((_expectedHash is null) != (currentHash is null)
            || (_expectedHash is not null && currentHash is not null
                && !CryptographicOperations.FixedTimeEquals(_expectedHash, currentHash)))
            throw new IOException("The profile store changed in another app instance. Reopen Qeli before saving.");
    }

    private void Remember(byte[]? bytes)
    {
        _expectedHash = bytes is null ? null : SHA256.HashData(bytes);
        _observed = true;
    }
}
