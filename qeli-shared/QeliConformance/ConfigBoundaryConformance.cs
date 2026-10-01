using System.Text;
using System.Text.Json;
using Qeli.Shared.Model;

namespace Qeli.Conformance;

internal static class ConfigBoundaryConformance
{
    internal static void Run(Action<string, bool> check)
    {
        string? path = null;
        for (var dir = new DirectoryInfo(AppContext.BaseDirectory); dir != null; dir = dir.Parent)
        {
            var candidate = Path.Combine(dir.FullName, "conformance", "config-boundary.json");
            if (File.Exists(candidate)) { path = candidate; break; }
        }
        check("config boundary corpus present", path != null);
        if (path == null) return;
        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        var root = doc.RootElement;
        foreach (var item in root.GetProperty("cases").EnumerateArray())
        {
            bool valid;
            try
            {
                VpnConfig.FromIni(root.GetProperty("base").GetString() + item.GetProperty("ini").GetString()).Validate();
                valid = true;
            }
            catch (ArgumentException) { valid = false; }
            catch (FormatException) { valid = false; }
            check("config boundary: " + item.GetProperty("name").GetString(),
                valid == item.GetProperty("valid").GetBoolean());
        }
        var configPath = Path.Combine(Path.GetTempPath(), $"qeli-config-input-{Guid.NewGuid():N}.conf");
        try
        {
            var validIni = root.GetProperty("base").GetString() + "server = vpn.example.com:443\n";
            File.WriteAllText(configPath, validIni, new UTF8Encoding(false, true));
            check("config file: valid UTF-8 INI loads", VpnConfig.ParseFile(configPath).ServerAddress == "vpn.example.com");

            File.WriteAllBytes(configPath, [.. Encoding.UTF8.GetBytes(validIni), 0xff]);
            bool invalidUtf8Rejected = false;
            try { _ = VpnConfig.ParseFile(configPath); }
            catch (DecoderFallbackException) { invalidUtf8Rejected = true; }
            check("config file: malformed UTF-8 is rejected", invalidUtf8Rejected);

            File.WriteAllBytes(configPath, new byte[256 * 1024 + 1]);
            bool oversizedRejected = false;
            try { _ = VpnConfig.ParseFile(configPath); }
            catch (ArgumentException) { oversizedRejected = true; }
            check("config file: over-budget input is rejected before parsing", oversizedRejected);
        }
        finally { File.Delete(configPath); }
    }
}
