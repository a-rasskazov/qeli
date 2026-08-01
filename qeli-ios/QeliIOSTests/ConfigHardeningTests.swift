import XCTest
@testable import Qeli

/// Config values that used to be resolved SILENTLY instead of reported.
///
/// The pattern each of these guards is the same, and it is the one the cross-port audits keep
/// finding: parsing never fails, so a config the user plainly did not mean still connects —
/// with a security setting off, or to a different server than the one the file names. Parsing
/// must still SUCCEED (an editor has to be able to open a bad profile in order to fix it);
/// ``VPNConfig/validate()`` is what refuses. Same split as the Kotlin, C# and Rust ports.
final class ConfigHardeningTests: XCTestCase {

    private func ini(_ extra: String...) -> String {
        var out = "[qeli]\nserver = vpn.example.com:443\nuser = alice\npass = secret\n"
        for line in extra { out += line + "\n" }
        return out
    }

    /// A number that is present but unreadable must be refused, not replaced by the default.
    ///
    /// `server`'s port has always thrown here, which is why the worst case never bit this port —
    /// but every other numeric key fell back in silence, so `padding_min = abc` quietly became
    /// 0. The C# port had it worse (`server = host:notnum` became `host:443`, a different
    /// server), and all four must now agree. (Audit 2026-08-01, §P2.)
    func testAnUnreadableNumberIsRefusedNotReplacedByTheDefault() throws {
        let cfg = try VPNConfig.fromINI(ini("padding_min = abc"))
        XCTAssertTrue(cfg.unparsedNumericKeys.contains("padding_min"),
                      "the bad number must be recorded, got \(cfg.unparsedNumericKeys)")
        XCTAssertThrowsError(try cfg.validate()) { error in
            XCTAssertTrue("\(error)".contains("padding_min"), "message must name the key: \(error)")
        }

        // An ABSENT key keeps its default silently — that is what a default is for.
        XCTAssertTrue(try VPNConfig.fromINI(ini()).unparsedNumericKeys.isEmpty)
        // ...and a readable one records nothing, so the check above cannot pass vacuously.
        let good = try VPNConfig.fromINI(ini("padding_min = 10", "padding_max = 200"))
        XCTAssertTrue(good.unparsedNumericKeys.isEmpty)
        XCTAssertNoThrow(try good.validate())

        // The port was already strict and must stay that way — an outright throw, not a record.
        XCTAssertThrowsError(try VPNConfig.fromINI("[qeli]\nserver = 1.2.3.4:notnum\n"))
    }

    /// A key written twice must be refused, not silently resolved.
    ///
    /// The ports disagreed on which line wins: this parser folds entries into a dictionary and
    /// keeps the LAST, while the Rust client (`config/format.rs` `Section::get`) takes the
    /// FIRST. Two `server` lines therefore sent the Rust client to one host and every GUI
    /// client to another, out of one file, with nothing reported anywhere.
    /// (Audit 2026-08-01, §7.)
    func testAKeyWrittenTwiceIsRefusedNotSilentlyResolved() throws {
        let dup = try VPNConfig.fromINI(ini("server = other.example.com:8443"))
        XCTAssertTrue(dup.duplicateKeys.contains("qeli.server"),
                      "the duplicate must be recorded, got \(dup.duplicateKeys)")
        XCTAssertThrowsError(try dup.validate()) { error in
            // The message must name the key, so this cannot pass because validate() happened
            // to dislike something else about the fixture.
            XCTAssertTrue("\(error)".contains("qeli.server"), "message must name the key: \(error)")
        }

        // Duplicates are found per SECTION — the same key name in two different sections is not
        // a duplicate, and a clean file must stay clean. Without this the check above would
        // pass just as well against a parser that flagged everything.
        let clean = try VPNConfig.fromINI(ini("mtu = 1400") + "[logging]\nlevel = debug\n")
        XCTAssertTrue(clean.duplicateKeys.isEmpty, "clean config recorded \(clean.duplicateKeys)")
        XCTAssertNoThrow(try clean.validate())

        // Recorded ONCE however many times the key repeats, and the last value still wins, so a
        // file that already had a duplicate parses exactly as it always did.
        let thrice = try VPNConfig.fromINI(ini("mtu = 1400", "mtu = 1300", "mtu = 1200"))
        XCTAssertEqual(thrice.duplicateKeys, ["qeli.mtu"])
        XCTAssertEqual(thrice.mtu, 1200)
    }

    /// A boolean nobody could parse must not read as `false`.
    ///
    /// Every unknown value used to be falsey, so `bind_static = ture` silently dropped the
    /// static-key binding and `gateway = ture` silently turned a full tunnel into a split one —
    /// a security downgrade with no message anywhere, and unrecoverable after parse because the
    /// original string is gone. (Audit 2026-07-31.)
    func testATypoInABooleanIsRefusedNotReadAsFalse() throws {
        for key in ["gateway", "bind_static", "reconnect", "padding", "heartbeat", "quic"] {
            let cfg = try VPNConfig.fromINI(ini("\(key) = ture"))
            XCTAssertTrue(cfg.unparsedBooleanKeys.contains(key), "\(key): the typo must be recorded")
            XCTAssertThrowsError(try cfg.validate(), "\(key): validate() must refuse") { error in
                XCTAssertTrue("\(error)".contains(key), "message must name \(key): \(error)")
            }
        }

        // A typo must NOT be resolved to the falsey reading it used to get.
        XCTAssertTrue(try VPNConfig.fromINI(ini("gateway = ture")).isFullTunnel,
                      "gateway = ture must not silently become split-tunnel")
        XCTAssertTrue(try VPNConfig.fromINI(ini("bind_static = ture")).bindStaticToSession,
                      "bind_static = ture must not silently disable key binding")

        // Every spelling the Rust client accepts must still work, both ways, and leave the
        // config valid.
        for yes in ["true", "1", "yes", "on", "TRUE", "On"] {
            let c = try VPNConfig.fromINI(ini("quic = \(yes)"))
            XCTAssertTrue(c.quicEnabled, "\(yes) must be true")
            XCTAssertTrue(c.unparsedBooleanKeys.isEmpty)
        }
        for no in ["false", "0", "no", "off", "FALSE", "Off"] {
            let c = try VPNConfig.fromINI(ini("quic = \(no)"))
            XCTAssertFalse(c.quicEnabled, "\(no) must be false")
            XCTAssertTrue(c.unparsedBooleanKeys.isEmpty)
        }
    }
}
