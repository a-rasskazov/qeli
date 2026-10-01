# Q25-F202 — reproducible native cores and Android runtime

<!-- normative-sync: audit-q25-native-rebuild-v3 -->

A later [F203 check](AUDIT-Q25-ANDROID-NETWORK-IDENTITY.md) explained
the background packets and closed D12 within the agreed available scope.

Date: 1 October 2026. A/B source: `27db1a22`, digest
`dce152196ab7b13ba42f9808a571ba95ac494c7ccbbd1c69578bd0de90c1979c`.
Verified artifacts were brought to `dev` in commit `08a1823d`.

## Resolved blockers

The native recipe put release output in the client VM's `/tmp`, a tmpfs with
less than 1 GiB available. It now uses disk-backed `/var/tmp` and requires
8 GiB free before building. The old space failure was reproduced on .10;
only regenerable Cargo incremental caches on .10 and .11 were removed.
Running services and binaries were not replaced.

Android `libc::in6_pktinfo.ipi6_ifindex` is signed, whereas Linux uses an
unsigned type. Checked conversions on receive and send fixed cross-compilation;
`Control::send` now propagates errors and batch scratch clears pointers on
failure. Six Linux UDP unit tests and one privileged IPv6 wildcard test passed.
The Android JVM recipe now builds host JNI from the same synchronized source
and provides its path to Gradle; the former 88 `UnsatisfiedLinkError` failures
are gone.

## Artifacts and verification

Two independent release builds, A and B, yielded identical SHA-256 for each target:

| Target | SHA-256 |
|---|---|
| Windows x64 DLL | `c601cffa1ab922552276358ed977445fc6bb1258c37b3c925c06eb437cb84d13` |
| macOS universal2 dylib | `1f5037414c5c19e040094bfb7d3bb2f6064a4e0781718f83e4ead267a3c2034d` |
| Android arm64-v8a so | `d3ccc2389600c9559d612c9deea4f03eeda73963dd5af2aea07a835f8a18bbca` |
| Android x86_64 so | `6c4db7c9ac12c482c6d62fe74347e9abec891042acd0daaca44ed3135b53077e` |

Windows/macOS export six REALITY and 22 client symbols; Android also exports
21 TransportCore JNI symbols. The universal2 library contains both Mach-O
architectures. All canonical and consumed copies were refreshed.
`native-libs/verify.sh` (14 entries) and `provenance.py --check` pass after
cherry-picking the artifact commit. The 71 local native-recipe tests pass.

The Windows .NET build passed without errors or warnings; selftest with the
fresh DLL reported 143 PASS, 0 FAIL. Android Gradle built a debug APK and
167 JVM tests passed without errors. The APK is version 0.8.2 (code 722),
SHA-256 `9ec9967bc691bd7b575572a85c7fd28d6478728d6395f89b47e5bbb678eb9968`.
Both embedded `.so` files match the A/B artifacts byte for byte.

On a read-only Android 14/API 34 x86_64 AVD, direct
`adb shell am instrument` yielded **11/11 PASS**: INI/JNI, JSON config and
forged-link rejection, diagnostic journal, encrypted store/version/bounds, and
TUN builder. The temporary emulator was stopped. Gradle
`connectedDebugAndroidTest --offline` could not resolve UTP 32.2.1, absent
from its cache; that was a Gradle launch failure, not a test failure. The
first emulator hung while Gradle ran concurrently; the tests passed separately
on a memory-limited instance.

## Bounded two-VM Android VPN E2E

An existing dedicated `e2e` profile (`tcp://0.0.0.0:8503`, `e2e0`,
REALITY) ran on .10 separately from the normal service under a 240-second
`timeout`; after it expired, it was restarted for 180 seconds solely to
check reverse ICMP. On .11, the same APK was installed on a read-only
Android 14 AVD; a test **INI** was imported through the supported legacy
store migration and Connect was tapped in the UI. The service JSON store
container is not the config format.

Android logcat recorded `Auth OK`, assigned `10.60.0.2`,
`Native NetworkPlan 1 APPLIED`, and `Rust owns the TUN payload`; the UI
showed `Connected`/`Tunnel active`. Server → client over `e2e0`:
**4/4 ICMP, 0% loss**. After the bounded server stopped, the client
automatically reconnected: a second `Auth OK` and
`NetworkPlan 2 APPLIED`. Client → server after reconnect:
**4/4 ICMP** with the default source and **2/2** with explicit
`10.60.0.2`. A 0/3 probe performed after the first server had already
expired is retained as a timing control, not counted as a tunnel failure.

After app `force-stop` and AVD shutdown, the owned test process ended;
`:8503` and `e2e0` were gone. The regular `qeli-server.service` stayed
active and kept listening on `:443`; its files and service were untouched.

The server log also contained rejected inner packets with the emulator's
physical address `10.0.2.16` rather than assigned `10.60.0.2`.
The tested Android shell ICMP used the correct source and passed. The
source of the background packets is unknown; server anti-spoofing
correctly rejected them. Targeted checks of another Android UID,
background traffic, and VPN lifecycle across network changes remain
under D12. This is not proof of a main-tunnel defect.

## Scope

D11 is complete for current native cores, A/B, ABI, copies, provenance, and
available packages. D12 remains open for the background inner-packet anomaly and untested
lifecycle scenarios; basic Android VPN handshake and bidirectional ICMP pass. Windows VM, Mac/Xcode/iOS, and router runtime were
excluded by user decision; the macOS dylib was structurally checked but the
Mac app and its behavior were not validated. This APK is a debug build, not a
published release.

[Debt register](../plans/AUDIT-DEBT.md) · [Native recipes](../../../native-libs/README.md)
