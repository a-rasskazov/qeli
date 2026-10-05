using System.Text;
using System.Text.Json;
using Qeli.Shared.Vpn;

namespace Qeli.Shared.Model;

public class DesktopServiceStatus
{
    public string Status { get; set; } = "Disconnected";
    public string? Extra { get; set; }
    public DateTime Time { get; set; }
    public long BytesUp { get; set; }
    public long BytesDown { get; set; }
    public DateTime? Since { get; set; }
    public static T Decode<T>(byte[] bytes) where T : DesktopServiceStatus
    {
        var snapshot = JsonSerializer.Deserialize<T>(new UTF8Encoding(false, true).GetString(bytes))
            ?? throw new InvalidDataException("Service status is empty");
        Validate(snapshot);
        return snapshot;
    }
    public static void Validate(DesktopServiceStatus snapshot)
    {
        if (!Enum.TryParse<VpnStatus>(snapshot.Status, out var status) || !Enum.IsDefined(status)
            || snapshot.Status != status.ToString() || snapshot.Time == default
            || snapshot.BytesUp < 0 || snapshot.BytesDown < 0 || snapshot.Extra?.Length > 2048)
            throw new InvalidDataException("Invalid service status snapshot");
    }
    public static bool Fresh(DesktopServiceStatus snapshot, DateTime now, TimeSpan maximumAge)
    {
        var age = now.ToUniversalTime() - snapshot.Time.ToUniversalTime();
        return age <= maximumAge && age >= TimeSpan.FromSeconds(-5);
    }
}
