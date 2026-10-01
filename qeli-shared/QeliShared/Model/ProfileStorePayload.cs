using System.Text.Json;

namespace Qeli.Shared.Model;

/// <summary>Structural validation of the encrypted desktop profile-list payload.</summary>
public static class ProfileStorePayload
{
    public static List<VpnConfig> Decode(string json, JsonSerializerOptions? options = null)
    {
        var profiles = JsonSerializer.Deserialize<List<VpnConfig>>(json, options)
            ?? throw new JsonException("Profile store must contain an array, not null.");
        if (profiles.Any(profile => profile is null))
            throw new JsonException("Profile store contains a null profile.");
        return profiles;
    }
}
