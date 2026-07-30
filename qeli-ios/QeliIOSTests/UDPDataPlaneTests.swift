import XCTest
@testable import Qeli

final class UDPDataPlaneTests: XCTestCase {
    func testFragmentQUICObfsRoundTripOutOfOrder() throws {
        let key = ObfsDatagramCipher.deriveKey("udp-test")
        let sender = try UDPDatagramCodec(
            quicEnabled: true,
            connectionID: Data([1, 2, 3, 4]),
            obfsKey: key
        )
        let receiver = try UDPDatagramCodec(
            quicEnabled: true,
            connectionID: Data([1, 2, 3, 4]),
            obfsKey: key
        )
        let record = tlsRecord(body: Data((0..<4_000).map { UInt8($0 & 0xff) }))
        let datagrams = try sender.encode(record: record, longHeader: true)
        XCTAssertGreaterThan(datagrams.count, 1)

        var received: [Data] = []
        for datagram in datagrams.reversed() {
            if case .records(let records) = try receiver.ingest(datagram: datagram) { received = records }
        }
        XCTAssertEqual(received, [record])
    }

    func testBundledRecordsAreSliced() throws {
        let codec = try UDPDatagramCodec(quicEnabled: false, connectionID: Data(repeating: 0, count: 4))
        let first = tlsRecord(body: Data("one".utf8))
        let second = tlsRecord(body: Data("two".utf8))
        XCTAssertEqual(try codec.ingest(datagram: first + second), .records([first, second]))
    }

    func testAWGPreambleUsesRecognizableJunkEnvelope() throws {
        let codec = try UDPDatagramCodec(quicEnabled: false, connectionID: Data(repeating: 0, count: 4))
        let datagrams = try codec.encodeAWGJunkPreamble(count: 3, minimumSize: 40, maximumSize: 40)
        XCTAssertEqual(datagrams.count, 3)
        for datagram in datagrams {
            XCTAssertEqual(datagram.count, UDPFragmentation.headerLength + 40)
            XCTAssertEqual(try codec.ingest(datagram: datagram), .junk)
        }
    }

    func testControlDatagramDoesNotPoisonHandshakeReassembly() throws {
        let sender = try UDPDatagramCodec(
            quicEnabled: false,
            connectionID: Data(repeating: 0, count: 4)
        )
        let receiver = try UDPDatagramCodec(
            quicEnabled: false,
            connectionID: Data(repeating: 0, count: 4)
        )
        let record = tlsRecord(body: Data(repeating: 0x5a, count: 2_000))
        let fragments = try sender.encode(record: record, longHeader: true)
        XCTAssertEqual(try receiver.ingest(datagram: fragments[0]), .fragmentPending)
        let junk = try sender.encodeAWGJunkPreamble(count: 1, minimumSize: 40, maximumSize: 40)[0]
        XCTAssertEqual(try receiver.ingest(datagram: junk), .junk)
        XCTAssertEqual(try receiver.ingest(datagram: fragments[1]), .records([record]))
    }

    func testUDPDataPlaneDropsCorruptRecordButAcceptsNextPacket() throws {
        let key = Data(repeating: 0x77, count: 32)
        let encoder = PacketCodec(cipher: try PacketCipher(key: key), paddingEnabled: false)
        let decoder = PacketCodec(cipher: try PacketCipher(key: key), paddingEnabled: false)
        var ipv4 = Data(repeating: 0, count: 20)
        ipv4[0] = 0x45
        let encrypted = try XCTUnwrap(UDPDataPlane.encodeUplink(ipv4, encoder: encoder, mtu: 1_400))
        XCTAssertEqual(UDPDataPlane.decodeDownlink(encrypted, decoder: decoder), ipv4)

        var corrupt = encrypted
        corrupt[corrupt.count - 1] ^= 1
        XCTAssertNil(UDPDataPlane.decodeDownlink(corrupt, decoder: decoder))

        var nextIPv4 = ipv4
        nextIPv4[19] = 1
        let next = try XCTUnwrap(UDPDataPlane.encodeUplink(nextIPv4, encoder: encoder, mtu: 1_400))
        XCTAssertEqual(UDPDataPlane.decodeDownlink(next, decoder: decoder), nextIPv4)
        XCTAssertNil(try UDPDataPlane.encodeUplink(Data([0x60]), encoder: encoder, mtu: 1_400))
    }

    func testPathMTULadder() {
        // Bare IPv4 UDP over a 48-byte record: floor = 1280 - (48+8+20) = 1204.
        let plain = UDPPathMTUProbePolicy(ceiling: 1_400, outerOverhead: 48 + 8 + 20)
        XCTAssertEqual(plain.candidates, [1_400, 1_360, 1_320, 1_280, 1_204])
        XCTAssertEqual(plain.outerProbeSize(for: 1_360), 1_408)
        XCTAssertTrue(plain.accepts(.mtuProbeAck(id: 7, outerSize: 1_408), id: 7))
        XCTAssertFalse(plain.accepts(.mtuProbeAck(id: 8, outerSize: 1_408), id: 7))
    }

    /// The #12 defect: rungs are INNER tunnel MTUs, 1280 is an OUTER path limit. A floor pinned
    /// to 1280 asked a 1280-byte path for 1280 + overhead bytes, so every rung failed on exactly
    /// the narrow paths probing exists for and the caller silently kept the pushed MTU.
    func testLadderFloorFitsTheIPv6MinimumPath() {
        for overhead in [48 + 8 + 20, 48 + 13 + 9 + 8 + 40] {
            let policy = UDPPathMTUProbePolicy(ceiling: 1_400, outerOverhead: overhead)
            let rungs = policy.candidates
            XCTAssertFalse(rungs.isEmpty, "ladder must not be empty (overhead \(overhead))")
            guard let lowest = rungs.last else { continue }
            XCTAssertLessThanOrEqual(lowest + overhead, 1_280,
                                     "lowest rung's wire size must fit a 1280-byte path")
            XCTAssertEqual(rungs, rungs.sorted(by: >), "rungs must be strictly descending")
            XCTAssertEqual(rungs.count, Set(rungs).count, "rungs must be deduped")
        }

        // A ceiling already below the floor must still yield something to try, not an empty
        // ladder (which reports "no result" and silently keeps the pushed MTU).
        let tiny = UDPPathMTUProbePolicy(ceiling: 700, outerOverhead: 48 + 13 + 9 + 8 + 40)
        XCTAssertFalse(tiny.candidates.isEmpty, "a low ceiling still produces a rung")
        XCTAssertLessThanOrEqual(tiny.candidates.first ?? .max, 700)
    }

    private func tlsRecord(body: Data) -> Data {
        var record = Data([0x16, 0x03, 0x03, UInt8((body.count >> 8) & 0xff), UInt8(body.count & 0xff)])
        record.append(body)
        return record
    }
}
