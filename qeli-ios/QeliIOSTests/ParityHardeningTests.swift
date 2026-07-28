import XCTest
@testable import Qeli

/// Guards for the Android↔iOS parity pass. Each test pins a divergence that was live in the
/// tree, so a regression shows up red instead of as a profile that quietly behaves
/// differently on one platform.
final class ParityHardeningTests: XCTestCase {

    private func minimalINI(_ extra: String = "") -> String {
        """
        [qeli]
        server = vpn.example.com:443
        user = alice
        pass = s3cret
        \(extra)
        """
    }

    /// The `[logging]` section used to be parsed into the section map and then dropped, so
    /// opening a desktop/router `client.conf` on the phone and saving it deleted the
    /// operator's logging configuration.
    func testLoggingSectionSurvivesRoundTrip() throws {
        let source = """
        [qeli]
        server = vpn.example.com:443
        user = alice
        pass = s3cret

        [logging]
        level = debug
        file = /var/log/qeli/client.log
        time_format = rfc3339
        """
        let first = try VPNConfig(parsing: source)
        XCTAssertEqual(first.loggingLevel, "debug")
        XCTAssertEqual(first.loggingTimeFormat, "rfc3339")

        let second = try VPNConfig(parsing: first.toINI())
        XCTAssertEqual(second.loggingLevel, "debug")
        XCTAssertEqual(second.loggingFile, "/var/log/qeli/client.log")
        XCTAssertEqual(second.loggingTimeFormat, "rfc3339")
    }

    /// Rust clamps an out-of-range link MTU to auto. This client used to reject the whole
    /// link, so one shared `qeli://` imported on Android and failed here.
    func testOutOfRangeLinkMTUFallsBackToAuto() throws {
        let uri = "qeli://alice:s3cret@vpn.example.com:443?proto=tcp&mode=fake-tls&mtu=99999"
        XCTAssertEqual(try VPNConfig(parsing: uri).mtu, 0)
    }

    /// Lists are emitted with ", " to match the Rust and Android writers byte-for-byte.
    func testListSeparatorMatchesOtherClients() throws {
        var config = try VPNConfig(parsing: minimalINI())
        config.dnsServers = ["1.1.1.1", "8.8.8.8"]
        config.includeRoutes = ["10.0.0.0/8", "192.0.2.0/24"]
        let ini = try config.toINI()
        XCTAssertTrue(ini.contains("dns = 1.1.1.1, 8.8.8.8"), ini)
        XCTAssertTrue(ini.contains("include = 10.0.0.0/8, 192.0.2.0/24"), ini)
    }

    /// The UI language is an explicit setting defaulting to English, not the device locale —
    /// a Russian phone must not silently open the app in Russian (Android behaves this way).
    func testLanguageDefaultsToEnglish() {
        XCTAssertEqual(AppSettings().language, .en)
        XCTAssertEqual(AppLanguage.allCases, [.en, .ru])
    }

    /// Settings saved by an older build lack the newer keys. Swift's synthesized decoder
    /// throws on a missing key rather than using the property default, and `SettingsStore`
    /// answers a decode failure by returning fresh defaults — so without a tolerant decoder,
    /// adding one field silently wipes every preference the user had.
    func testSettingsFromAnOlderBuildKeepTheirValues() throws {
        let legacy = Data(#"{"autoConnectOnLaunch":true,"allowLAN":true}"#.utf8)
        let decoded = try JSONDecoder().decode(AppSettings.self, from: legacy)
        XCTAssertTrue(decoded.autoConnectOnLaunch)
        XCTAssertTrue(decoded.allowLAN)
        XCTAssertEqual(decoded.language, .en)
        XCTAssertEqual(decoded.logTimeFormat, .time)
    }

    /// Every option the settings pickers show has to exist as a localization key in BOTH
    /// bundles; a missing entry silently renders the English key to a Russian user.
    func testPickerOptionKeysAreLocalizedInEveryLanguage() throws {
        let keys = LogTimeFormat.allCases.map(\.title) + AppAppearance.allCases.map(\.title)
        for language in AppLanguage.allCases {
            guard let path = Bundle.main.path(forResource: language.rawValue, ofType: "lproj"),
                  let bundle = Bundle(path: path) else {
                XCTFail("missing \(language.rawValue).lproj")
                continue
            }
            for key in keys {
                let sentinel = "\u{0}missing"
                let value = bundle.localizedString(forKey: key, value: sentinel, table: nil)
                XCTAssertNotEqual(value, sentinel, "\(language.rawValue) is missing the key \"\(key)\"")
            }
        }
    }

    /// A reality-tls profile with no pinned key must stay EDITABLE — the connect-time
    /// precondition in `TunnelManager` is what refuses it, so parsing and saving such a
    /// profile has to keep working while the user is still filling it in.
    ///
    /// (The refusal itself isn't covered here: exercising it means driving `TunnelManager`,
    /// which talks to the system VPN stack and isn't safe to touch from a unit test.)
    func testRealityWithoutPinnedKeyStillParsesAndSaves() throws {
        let config = try VPNConfig(parsing: minimalINI("mode = reality-tls"))
        XCTAssertEqual(config.wireMode, "reality-tls")
        XCTAssertNil(config.serverPublicKeyHex)
        XCTAssertNoThrow(try config.toINI())
    }
}
