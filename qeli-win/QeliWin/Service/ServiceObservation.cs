using System.ServiceProcess;
using Qeli.Shared.Vpn;

namespace QeliWin.Service;

internal readonly record struct ServiceObservation(VpnStatus Status, string? Extra, ServiceStatus? Snapshot)
{
    internal static ServiceObservation Resolve(ServiceControllerStatus state, ServiceStatus? snapshot, DateTime now)
    {
        // Stopped confirms only SCM state. Retain the worker's terminal failure,
        // especially incomplete cleanup, until a new worker publishes its outcome.
        if (state == ServiceControllerStatus.Stopped)
            return snapshot?.Status == nameof(VpnStatus.Error)
                ? new(VpnStatus.Error, snapshot.Extra, null) : new(VpnStatus.Disconnected, null, null);
        if (state == ServiceControllerStatus.StartPending) return new(VpnStatus.Connecting, null, null);
        if (state != ServiceControllerStatus.Running)
            return new(VpnStatus.Error, $"Service state: {state}", null);
        if (snapshot == null) return new(VpnStatus.Error, "Service status is unavailable", null);
        if (!Qeli.Shared.Model.DesktopServiceStatus.Fresh(snapshot, now, TimeSpan.FromSeconds(10)))
            return new(VpnStatus.Error, "Service status is stale; tunnel state is unknown", null);
        if (!Enum.TryParse<VpnStatus>(snapshot.Status, out var status) || !Enum.IsDefined(status)
            || snapshot.Status != status.ToString())
            return new(VpnStatus.Error, "Service status is invalid", null);
        return new(status, snapshot.Extra, snapshot);
    }
}
