using System.IO;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using QeliWin.Model;
using QeliWin.Vpn;
using Qeli.Shared.Model;
using Qeli.Shared.Vpn;

namespace QeliWin.Service;

/// <summary>Status snapshot the service writes and the GUI polls.</summary>
public sealed class ServiceStatus
{
    public string Status { get; set; } = "Disconnected";
    public string? Extra { get; set; }
    public DateTime Time { get; set; }
    public long BytesUp { get; set; }
    public long BytesDown { get; set; }
    public DateTime? Since { get; set; }
}

/// <summary>
/// Shared state between the Windows Service (writer) and the GUI (reader), stored under
/// %ProgramData%\QeliWin for LocalSystem and elevated administrators only.
/// </summary>
public static class ServiceState
{
    public static readonly string Dir =
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "QeliWin");
    public static string ProfileFile => Path.Combine(Dir, "service-profile.json");
    public static string StatusFile => Path.Combine(Dir, "service-status.json");
    public static string LogFile => Path.Combine(Dir, "service.log");
    public static string DesiredConnectionFile => Path.Combine(Dir, "service-connect.enabled");

    private static readonly object _logLock = new();
    private const long MaxLogBytes = 256 * 1024;
    internal const int MaximumProfileBytes = 4 * 1024 * 1024;
    internal const int MaximumStatusBytes = 64 * 1024;
    private static readonly UTF8Encoding StrictUtf8 = new(false, true);

    public static void EnsureDir()
    {
        // Do not repair/adopt a pre-existing untrusted directory: its files may have
        // been planted before the DACL was tightened. Fail before reading or writing.
        for (var parent = Path.GetDirectoryName(Dir); !string.IsNullOrEmpty(parent);
             parent = Path.GetDirectoryName(parent))
            RequireTrusted(parent, ancestor: true);
        if (!Directory.Exists(Dir))
        {
            var security = new DirectorySecurity();
            security.SetAccessRuleProtection(true, false);
            var admin = new SecurityIdentifier(WellKnownSidType.BuiltinAdministratorsSid, null);
            security.SetOwner(admin);
            var inherit = InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit;
            foreach (var id in new[] { admin, new SecurityIdentifier(WellKnownSidType.LocalSystemSid, null) })
                security.AddAccessRule(new FileSystemAccessRule(id, FileSystemRights.FullControl,
                    inherit, PropagationFlags.None, AccessControlType.Allow));
            new DirectoryInfo(Dir).Create(security); // private from creation, not after writing
        }
        RequireTrusted(Dir, privateFile: true);
    }

    internal static void RequireTrusted(string path, bool ancestor = false, bool privateFile = false)
    {
        string? unsafeAccess = ServiceManager.NonAdminWriterOn(path, ancestor, privateFile);
        if (unsafeAccess != null)
            throw new UnauthorizedAccessException(
                $"Refusing untrusted service storage '{path}': {unsafeAccess}. " +
                "Stop VPN and complete network recovery; archive the unsafe storage, " +
                "then recreate it and re-save a trusted profile from the elevated GUI.");
    }

    internal static void CheckExistingFile(string path)
    {
        // GetAttributes distinguishes missing files from ACL/I/O errors and broken links.
        try { _ = File.GetAttributes(path); }
        catch (FileNotFoundException) { return; }
        RequireTrusted(path, privateFile: true);
    }

    /// <summary>Persist intent atomically; a missing/invalid flag means disconnected.</summary>
    public static void SetDesiredConnected(bool connected)
    {
        EnsureDir();
        AtomicWrite(DesiredConnectionFile, Encoding.UTF8.GetBytes(connected ? "1" : "0"));
    }

    public static bool DesiredConnected()
    {
        try
        {
            EnsureDir();
            CheckExistingFile(DesiredConnectionFile);
            using var file = OpenSnapshot(DesiredConnectionFile);
            return StrictUtf8.GetString(ReadBounded(file, 16)).Trim() == "1";
        }
        catch { return false; }
    }

    // The containing directory is private and verified before calling this helper.
    // Publication is a same-directory rename; readers see the complete old or new file.
    internal static void AtomicWrite(string destination, byte[] bytes)
    {
        CheckExistingFile(destination);
        PublishAtomic(destination, temporary =>
        {
            using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                RequireTrusted(temporary, privateFile: true);
                stream.Write(bytes);
                stream.Flush(flushToDisk: true);
            }
        });
    }

    // Factored to fault-inject an interrupted writer without touching service storage.
    internal static void PublishAtomic(string destination, Action<string> writeTemporary)
    {
        string temporary = destination + $".{Environment.ProcessId}.{Guid.NewGuid():N}.tmp";
        string previous = temporary + ".previous";
        bool published = false;
        try
        {
            writeTemporary(temporary);
            // ReplaceFile preserves an existing reader's handle; MoveFileEx with
            // REPLACE_EXISTING can fail while that handle is open on Windows.
            // Keep a private rollback name: ReplaceFile has rare partial-failure
            // outcomes where the old file has moved but publication did not finish.
            if (File.Exists(destination)) File.Replace(temporary, destination, previous);
            else File.Move(temporary, destination);
            published = true;
        }
        catch (Exception failure)
        {
            if (File.Exists(previous) && !File.Exists(destination))
            {
                try { File.Move(previous, destination); }
                catch (Exception recovery)
                {
                    throw new IOException($"Profile publication failed; previous data retained at '{previous}': {recovery.Message}", failure);
                }
            }
            throw;
        }
        finally
        {
            try { File.Delete(temporary); } catch { }
            if (published) { try { File.Delete(previous); } catch { } }
        }
    }

    // Read a single generation while allowing its atomic replacement, never a writer.
    private static FileStream OpenSnapshot(string path) =>
        new(path, FileMode.Open, FileAccess.Read, FileShare.Read | FileShare.Delete);

    // Enforce the budget during streaming too, not just against an initial Length.
    internal static byte[] ReadBounded(Stream input, int maximumBytes)
    {
        using var output = new MemoryStream();
        var buffer = new byte[64 * 1024];
        try
        {
            while (true)
            {
                int read = input.Read(buffer, 0,
                    (int)Math.Min(buffer.Length, maximumBytes - output.Length + 1));
                if (read == 0) return output.ToArray();
                if (output.Length + read > maximumBytes)
                    throw new InvalidDataException("Service storage exceeds its byte limit");
                output.Write(buffer, 0, read);
            }
        }
        finally { CryptographicOperations.ZeroMemory(buffer); }
    }

    internal static byte[] EncodeProfile(VpnConfig cfg)
    {
        ProfileStorePayload.Validate(cfg);
        var plaintext = StrictUtf8.GetBytes(JsonSerializer.Serialize(cfg));
        try
        {
            if (plaintext.Length > MaximumProfileBytes)
                throw new InvalidDataException("Service profile is too large");
            var encrypted = ProtectedData.Protect(plaintext, null, DataProtectionScope.LocalMachine);
            // The reader limits the stored blob, including DPAPI envelope overhead.
            if (encrypted.Length > MaximumProfileBytes)
                throw new InvalidDataException("Service profile is too large");
            return encrypted;
        }
        finally { CryptographicOperations.ZeroMemory(plaintext); }
    }

    internal static VpnConfig DecodeProfile(byte[] bytes, bool allowLegacy, out bool legacy)
    {
        legacy = false;
        byte[]? plaintext = null;
        try
        {
            try { plaintext = ProtectedData.Unprotect(bytes, null, DataProtectionScope.LocalMachine); }
            catch (CryptographicException)
            {
                if (!allowLegacy)
                    throw new InvalidDataException("Service profile is corrupt or not DPAPI-encrypted; re-save it from the GUI");
                plaintext = bytes; // trusted, elevated GUI legacy migration only
                legacy = true;
            }
            var cfg = JsonSerializer.Deserialize<VpnConfig>(StrictUtf8.GetString(plaintext))
                ?? throw new InvalidDataException("Service profile is empty");
            ProfileStorePayload.Validate(cfg);
            return cfg;
        }
        finally
        {
            if (plaintext != null && !ReferenceEquals(plaintext, bytes))
                CryptographicOperations.ZeroMemory(plaintext);
        }
    }

    public static void SaveProfile(VpnConfig cfg) => PublishProfile(EncodeProfile(cfg));

    internal static void PublishProfile(byte[] encrypted)
    {
        if (encrypted.Length > MaximumProfileBytes)
            throw new InvalidDataException("Service profile is too large");
        EnsureDir();
        AtomicWrite(ProfileFile, encrypted);
    }

    public static VpnConfig? LoadProfile()
    {
        EnsureDir();
        CheckExistingFile(ProfileFile);
        byte[] bytes;
        try
        {
            using var file = OpenSnapshot(ProfileFile);
            bytes = ReadBounded(file, MaximumProfileBytes);
        }
        catch (FileNotFoundException) { return null; } // only absence is "no profile"
        try
        {
            using var identity = WindowsIdentity.GetCurrent();
            var cfg = DecodeProfile(bytes, allowLegacy: !identity.IsSystem, out bool legacy);
            if (legacy) SaveProfile(cfg);
            return cfg;
        }
        finally { CryptographicOperations.ZeroMemory(bytes); }
    }

    public static void WriteStatus(VpnStatus status, string? extra,
        long bytesUp = 0, long bytesDown = 0, DateTime? since = null)
    {
        try
        {
            EnsureDir();
            AtomicWrite(StatusFile, Encoding.UTF8.GetBytes(JsonSerializer.Serialize(new ServiceStatus
            {
                Status = status.ToString(),
                // Bound status even when an upstream error includes a large file/response.
                Extra = extra is { Length: > 2048 } ? extra[..2048] : extra,
                Time = DateTime.Now,
                BytesUp = bytesUp,
                BytesDown = bytesDown,
                Since = since,
            })));
        }
        catch { /* ignore */ }
    }

    public static ServiceStatus? ReadStatus()
    {
        try
        {
            EnsureDir();
            CheckExistingFile(StatusFile);
            using var file = OpenSnapshot(StatusFile);
            return JsonSerializer.Deserialize<ServiceStatus>(StrictUtf8.GetString(
                ReadBounded(file, MaximumStatusBytes)));
        }
        catch { return null; }
    }

    public static void ResetLog()
    {
        try { EnsureDir(); CheckExistingFile(LogFile); File.WriteAllText(LogFile, ""); } catch { }
    }

    public static void AppendLog(string line)
    {
        lock (_logLock)
        {
            try
            {
                EnsureDir();
                CheckExistingFile(LogFile);
                if (File.Exists(LogFile) && new FileInfo(LogFile).Length > MaxLogBytes)
                    File.WriteAllText(LogFile, "");
                File.AppendAllText(LogFile, $"{DateTime.UtcNow:yyyy-MM-ddTHH:mm:ss'Z'}  {line}{Environment.NewLine}");
            }
            catch { /* ignore */ }
        }
    }
}
