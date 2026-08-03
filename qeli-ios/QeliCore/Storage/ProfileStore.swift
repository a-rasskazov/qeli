import CryptoKit
import Foundation

final class ProfileStore: @unchecked Sendable {
    private let defaults: UserDefaults
    private let keychain: KeychainStore
    private let blobKey = "profiles.encrypted.v1"
    private let masterKeyAccount = "profile-master-key-v1"

    init(
        suiteName: String? = AppConstants.appGroupIdentifier,
        keychain: KeychainStore = KeychainStore()
    ) {
        self.defaults = suiteName.flatMap(UserDefaults.init(suiteName:)) ?? .standard
        self.keychain = keychain
    }

    func load() throws -> ProfileArchive {
        guard let encoded = defaults.string(forKey: blobKey) else {
            let archive = ProfileArchive.initial
            try save(archive)
            return archive
        }
        guard let combined = Data(base64Encoded: encoded) else {
            throw ProfileStoreError.corruptStore
        }
        let key = try keychain.loadOrCreateSymmetricKey(account: masterKeyAccount)
        let sealed = try AES.GCM.SealedBox(combined: combined)
        let plaintext = try AES.GCM.open(sealed, using: key)
        var archive = try JSONDecoder.qeli.decode(ProfileArchive.self, from: plaintext)
        archive.normalize()
        return archive
    }

    func save(_ input: ProfileArchive) throws {
        var archive = input
        archive.normalize()
        let plaintext = try JSONEncoder.qeli.encode(archive)
        let key = try keychain.loadOrCreateSymmetricKey(account: masterKeyAccount)
        let sealed = try AES.GCM.seal(plaintext, using: key)
        guard let combined = sealed.combined else { throw ProfileStoreError.encryptionFailed }
        defaults.set(combined.base64EncodedString(), forKey: blobKey)
    }

    /// Android-compatible plaintext backup schema. Unknown `id` metadata is harmless to
    /// Android, while retaining it lets two iOS restores preserve profile identity.
    func exportJSON(_ archive: ProfileArchive) throws -> Data {
        let active = archive.profiles.firstIndex(where: { $0.id == archive.activeProfileID }) ?? 0
        let profiles: [[String: Any]] = archive.profiles.map { profile in
            [
                "id": profile.id.uuidString,
                "name": profile.name,
                "cfg": profile.configText
            ]
        }
        return try JSONSerialization.data(
            withJSONObject: ["active": active, "profiles": profiles],
            options: [.prettyPrinted, .sortedKeys]
        )
    }

    func importJSON(_ data: Data) throws -> ProfileArchive {
        guard let root = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let rawProfiles = root["profiles"] as? [[String: Any]] else {
            throw ProfileStoreError.notQeliBackup
        }
        let profiles = try rawProfiles.map { raw -> Profile in
            let name = (raw["name"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines)
            let configText: String
            if let cfg = raw["cfg"] as? String, !cfg.isEmpty {
                configText = cfg
            } else if let stored = raw["json"] as? String, !stored.isEmpty {
                // A profile written by an app version that stored the CONFIG as JSON. That
                // format is retired, so `parsing:` refuses it and names it — the restore fails
                // with "export the profile again" rather than with a syntax error. The BACKUP
                // envelope around it is still JSON and is unaffected; only the config text is.
                configText = try VPNConfig(parsing: stored).toINI(label: name)
            } else {
                // Legacy old-multi-profile entry: the fields sit directly on the row. It used
                // to be re-serialized to JSON and handed to the config parser purely to reuse
                // it; built through the model instead, so the key names come from `toINI` and
                // cannot drift from what the INI reader expects.
                guard let address = (raw["address"] as? String).nonEmpty else {
                    throw ProfileStoreError.notQeliBackup
                }
                var legacy = VPNConfig(serverAddress: address, port: raw["port"] as? Int ?? 443)
                legacy.username = (raw["username"] as? String).nonEmpty ?? "phone"
                configText = try legacy.toINI(label: name)
            }
            _ = try VPNConfig(parsing: configText)
            return Profile(
                id: (raw["id"] as? String).flatMap(UUID.init(uuidString:)) ?? UUID(),
                name: name.nonEmpty ?? "profile",
                configText: configText
            )
        }
        guard !profiles.isEmpty else { throw ProfileStoreError.notQeliBackup }
        let activeIndex = min(max((root["active"] as? NSNumber)?.intValue ?? 0, 0), profiles.count - 1)
        return ProfileArchive(activeProfileID: profiles[activeIndex].id, profiles: profiles)
    }
}

enum ProfileStoreError: LocalizedError {
    case corruptStore
    case encryptionFailed
    case notQeliBackup

    var errorDescription: String? {
        switch self {
        case .corruptStore: return "The encrypted profile store is corrupt."
        case .encryptionFailed: return "Could not encrypt the profile store."
        case .notQeliBackup: return "The file is not a Qeli profile backup."
        }
    }
}

private extension JSONEncoder {
    static var qeli: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.sortedKeys]
        return encoder
    }
}

private extension JSONDecoder {
    static var qeli: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }
}

private extension Optional where Wrapped == String {
    var nonEmpty: String? {
        guard let self, !self.isEmpty else { return nil }
        return self
    }
}

