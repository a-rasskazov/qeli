using System.Text.Json;

namespace Qeli.Shared.Model;

/// <summary>Structural validation and stable identity migration of encrypted desktop profiles.</summary>
public static class ProfileStorePayload
{
    public static List<VpnConfig> Decode(string json, JsonSerializerOptions? options = null)
        => Decode(json, out _, options);

    public static List<VpnConfig> Decode(
        string json,
        out bool needsIdMigration,
        JsonSerializerOptions? options = null)
    {
        using var document = JsonDocument.Parse(json);
        var root = document.RootElement;
        if (root.ValueKind != JsonValueKind.Array)
            throw new JsonException("Profile store must contain an array.");

        needsIdMigration = false;
        var explicitIds = new HashSet<string>(StringComparer.Ordinal);
        foreach (var entry in root.EnumerateArray())
        {
            if (entry.ValueKind != JsonValueKind.Object)
                throw new JsonException("Profile store contains a non-object profile.");
            if (!entry.TryGetProperty("Id", out var id))
            {
                needsIdMigration = true;
                continue;
            }
            if (id.ValueKind != JsonValueKind.String
                || string.IsNullOrWhiteSpace(id.GetString())
                || !explicitIds.Add(id.GetString()!))
                throw new JsonException("Profile store contains an invalid or duplicate profile Id.");
        }

        var profiles = root.Deserialize<List<VpnConfig>>(options)
            ?? throw new JsonException("Profile store must contain an array.");
        ValidateIds(profiles);
        return profiles;
    }

    public static string Encode(IEnumerable<VpnConfig> profiles, JsonSerializerOptions? options = null)
    {
        var entries = profiles.ToList();
        ValidateIds(entries);
        return JsonSerializer.Serialize(entries, options);
    }

    private static void ValidateIds(IEnumerable<VpnConfig> profiles)
    {
        var ids = new HashSet<string>(StringComparer.Ordinal);
        foreach (var profile in profiles)
        {
            if (profile is null || string.IsNullOrWhiteSpace(profile.Id)
                || !ids.Add(profile.Id))
                throw new JsonException("Profile store contains an invalid or duplicate profile.");
        }
    }
}
