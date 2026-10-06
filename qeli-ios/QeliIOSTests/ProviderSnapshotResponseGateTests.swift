import XCTest
@testable import Qeli

final class ProviderSnapshotResponseGateTests: XCTestCase {
    func testLateReplyCannotReplaceANewerAcceptedSnapshot() {
        var gate = ProviderSnapshotResponseGate()
        let old = gate.issue()
        let new = gate.issue()
        XCTAssertTrue(gate.accept(new))
        XCTAssertFalse(gate.accept(old))
        XCTAssertFalse(gate.accept(new))
    }

    func testPendingNewerRequestDoesNotStarveAnOlderValidResponse() {
        var gate = ProviderSnapshotResponseGate()
        let old = gate.issue()
        let new = gate.issue()
        XCTAssertTrue(gate.accept(old))
        XCTAssertTrue(gate.accept(new))
    }

    func testStopAndAutomaticRestartRejectRepliesFromPreviousEpoch() {
        var gate = ProviderSnapshotResponseGate()
        let old = gate.issue()
        gate.invalidate()
        let current = gate.issue()
        XCTAssertFalse(gate.accept(old))
        XCTAssertTrue(gate.accept(current))
        gate.invalidate()
        XCTAssertFalse(gate.accept(current))
        let restarted = gate.issue()
        XCTAssertTrue(gate.accept(restarted))
    }
}
