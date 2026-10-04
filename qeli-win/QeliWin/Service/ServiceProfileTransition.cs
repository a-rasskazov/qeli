using System.IO;
using System.Text;
using System.Text.Json;
using Qeli.Shared.Model;

namespace QeliWin.Service;

// One process coordinates settings/profile writes and service lifecycle off the dispatcher.
// OS adapters stay injectable so failures are tested without controlling installed SCM.
internal sealed class ServiceProfileTransition(
    Func<bool> installed, Func<bool> desiredConnected, Func<VpnConfig?> readProfile,
    Action stop, Action<byte[]> publish, Action install, Action start, Action uninstall)
{
    internal static readonly ServiceProfileTransition Current = new(
        ServiceManager.IsInstalled, ServiceState.DesiredConnected, ServiceState.LoadProfile,
        ServiceManager.Stop, ServiceState.PublishProfile, ServiceManager.Install,
        ServiceManager.Start, ServiceManager.Uninstall);
    private readonly object _gate = new();

    internal void Apply(VpnConfig? profile, bool connectRequested)
    {
        lock (_gate)
        {
            bool exists = installed();
            if (profile is null)
            {
                if (exists) uninstall();
                return;
            }
            // Validate/encode before stopping any existing tunnel or publishing its replacement.
            byte[] encrypted = ServiceState.EncodeProfile(profile);
            bool resume = !exists || connectRequested || desiredConnected();
            VpnConfig? previous = null;
            if (exists)
            {
                try { previous = readProfile(); }
                catch (Exception error) when (error is InvalidDataException or JsonException or DecoderFallbackException)
                {
                    // A trusted GUI may replace a malformed payload. ACL/I/O failures still refuse.
                }
            }
            bool changed = previous is null || JsonSerializer.Serialize(previous) != JsonSerializer.Serialize(profile);
            if (exists && changed) stop(); // must complete before the worker can load a new generation
            if (changed) publish(encrypted);
            if (!exists) install();
            if (resume) start();
            // An unchanged profile with intent=false stays disconnected on ordinary Settings Save.
        }
    }

    internal bool UsesProfile(string id)
    {
        lock (_gate) return installed() && readProfile()?.Id == id;
    }

    internal static VpnConfig Snapshot(VpnConfig profile, string logLevel)
    {
        var copy = JsonSerializer.Deserialize<VpnConfig>(JsonSerializer.Serialize(profile))!;
        copy.LoggingLevel = logLevel;
        return copy; // Keep stable Id; do not mutate the GUI's persisted profile instance.
    }
}
