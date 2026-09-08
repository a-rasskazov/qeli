import Foundation
import Security

/// Verifies the effective entitlements embedded in the running app's code signature.
///
/// An unsigned archive can be re-signed by a generic sideloading tool and still launch, while
/// lacking every capability that makes it a VPN. Checking the source `.entitlements` file is
/// insufficient: iOS authorizes only the values in the final signature and provisioning profile.
enum IOSSigningDiagnostics {
    enum Requirement: String, CaseIterable, Equatable {
        case packetTunnel
        case appGroup
        case keychainGroup
    }

    struct Entitlements {
        var networkExtensions: [String]
        var appGroups: [String]
        var keychainGroups: [String]
    }

    static func missingRequirements(
        in entitlements: Entitlements,
        expectedAppGroup: String,
        expectedKeychainGroup: String?
    ) -> [Requirement] {
        var missing: [Requirement] = []
        if !entitlements.networkExtensions.contains("packet-tunnel-provider") {
            missing.append(.packetTunnel)
        }
        if expectedAppGroup.isEmpty || !entitlements.appGroups.contains(expectedAppGroup) {
            missing.append(.appGroup)
        }
        guard let expectedKeychainGroup, !expectedKeychainGroup.isEmpty,
              entitlements.keychainGroups.contains(expectedKeychainGroup) else {
            missing.append(.keychainGroup)
            return missing
        }
        return missing
    }

    static func missingRequirements() -> [Requirement] {
        // Packet Tunnel Providers cannot run in the simulator. Simulator builds are retained
        // for Swift compilation and unit tests, so provisioning is intentionally not a gate.
        #if targetEnvironment(simulator)
        return []
        #else
        guard let task = SecTaskCreateFromSelf(nil) else { return Requirement.allCases }
        let entitlements = Entitlements(
            networkExtensions: stringValues(
                task: task,
                key: "com.apple.developer.networking.networkextension"
            ),
            appGroups: stringValues(
                task: task,
                key: "com.apple.security.application-groups"
            ),
            keychainGroups: stringValues(task: task, key: "keychain-access-groups")
        )
        return missingRequirements(
            in: entitlements,
            expectedAppGroup: AppConstants.appGroupIdentifier,
            expectedKeychainGroup: AppConstants.keychainAccessGroup
        )
        #endif
    }

    private static func stringValues(task: SecTask, key: String) -> [String] {
        SecTaskCopyValueForEntitlement(task, key as CFString, nil) as? [String] ?? []
    }
}
