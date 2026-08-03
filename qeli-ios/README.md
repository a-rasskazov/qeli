# Qeli for iOS

Native iPhone client for the qeli protocol. The project mirrors the Android client's
three primary surfaces (Connection, Profiles, Log) and uses a Packet Tunnel Provider
extension for the VPN data plane.

## Status: feature-complete, unverified

**Neither a preview nor a release.** Not a preview, because the client is not a sketch —
it mirrors the Android client feature for feature, and that logic is proven in the field.
Not a release, because **none of it has been exercised on a device**: no build has been
tested on real hardware, and nothing ships from this directory.

Read the list below as *what is implemented*, not *what is verified*. Every item is
written and reviewed, not run. What it needs before anyone depends on it is a device
pass — install, connect on each wire mode, background/foreground, a Wi-Fi ↔ cellular
switch, and On Demand behaviour — after which this section should say what was actually
observed, not what was built.

The version tracks the rest of the repository (see `MARKETING_VERSION` in `project.yml`,
kept in step by `scripts/sync_version.py`) because the code is the same generation as
every other client, not because a build of it was released.

## Current implementation

- SwiftUI application shell with connection, profile and live-log tabs.
- Encrypted profile storage shared with the tunnel extension (App Group + Keychain).
- INI and `qeli://` profile import/export.
- QR scanning/generation, profile editing, duplication, ordering and sharing.
- Android-compatible encrypted backups (`QELI-ENC-1`, PBKDF2-SHA256, AES-256-GCM).
- Opt-in release checks that run only with a fail-closed full-tunnel route.
- `NETunnelProviderManager` lifecycle, VPN On Demand and status/statistics bridge.
- `NEPacketTunnelProvider` target and Network.framework transport foundation.
- End-to-end plain/TCP, fake-TLS, obfs and REALITY-TLS paths: X25519/ML-KEM,
  static-key binding/TOFU, server and client proofs, credential authentication,
  server-pushed network settings, encrypted uplink/downlink and live counters.
- UDP record transport with mobile-safe ClientHello fragmentation, exact handshake
  retransmission, optional QUIC-shaped masking, stateless obfs, AWG preamble and
  active DF path-MTU discovery. A missed probe window transparently re-authenticates
  without DF and keeps the server-pushed MTU, matching Android's safe fallback.
- Fail-closed reconnect/reassertion, heartbeat/liveness checks, flow-shaping cover,
  TCP JOIN multipath with fixed fan-out or adaptive throughput ramping.
- Protocol primitives already ported to Swift: key derivation, ChaCha20-Poly1305,
  packet framing/anti-replay, UDP fragmentation, QUIC-looking framing and shaping.
- Rust iOS XCFramework build script for REALITY, ML-KEM and canonical fake-TLS hello.
- Home Screen status widget and authenticated connect/disconnect action; iOS 18 adds
  the same action as a Control Center, Lock Screen and Action button control.
- MDM deployment templates, typed managed configuration, enforced profile/On-Demand
  precedence and an App-Group policy gate for managed WidgetKit controls.

The requested protocol paths are now wired into the Packet Tunnel runtime. A real
XCFramework build and interoperability matrix still have to be run on macOS and a
physical iPhone; Windows cannot compile or execute Network Extension targets. See
`PARITY.md` for the remaining validation work and Apple platform boundaries.

## Requirements

- macOS with Xcode 16 or newer.
- Apple Developer team with the Network Extension entitlement enabled.
- Rust 1.85 or newer with the Apple iOS targets (for the native protocol core).
- [XcodeGen](https://github.com/yonaskolb/XcodeGen) (`brew install xcodegen`).

## Generate and open

```sh
cd qeli-ios
sh build_native.sh
sh generate_project.sh
open QeliIOS.xcodeproj
```

Set `DEVELOPMENT_TEAM` and, if needed, `QELI_APP_BUNDLE_ID` in
`Config/Signing.xcconfig` — `DEVELOPMENT_TEAM` ships empty on purpose, and no
provisioning profile is committed. Everything else derives from the app bundle ID and can
still be overridden in CI.

### Signing and capabilities

Three App IDs must be registered, and they do **not** get the same capabilities. This
table is the entitlement files (`Config/*.entitlements`), not a recommendation:

| Target | Bundle ID | Network Extension | App Group | Keychain Sharing |
|---|---|:-:|:-:|:-:|
| `QeliIOS` (app) | `ru.qeli.app` | `packet-tunnel-provider` | ✓ | ✓ |
| `QeliPacketTunnel` (extension) | `…app.PacketTunnel` | `packet-tunnel-provider` | ✓ | ✓ |
| `QeliWidgets` (extension) | `…app.Widgets` | — | ✓ | — |

The shared identifiers are `group.ru.qeli.app` (App Group) and
`$(AppIdentifierPrefix)ru.qeli.app.shared` (Keychain Group).

The widget deliberately has **no** Keychain access: it renders status and requests a
desired state, and must never be able to read profile secrets. Granting it Keychain
Sharing to "make things consistent" would quietly widen the blast radius of a widget
compromise — the two extensions are not interchangeable.

The widget and iOS 18 control read status from the App Group. Their authenticated
App Intents write a short-lived, one-time desired-state request and bring the main
app forward to apply it through `NETunnelProviderManager`; the widget extension
never starts a tunnel directly. The `qeli-control://status` URL is navigation-only.
Any future command URL must carry a fresh opaque token that already exists in the
App Group, so an arbitrary custom URL cannot authorize connect or disconnect.
WidgetKit controls timeline refresh frequency, so status can briefly lag when the
main app is suspended; the app explicitly reloads widgets on tunnel phase changes.
No universal-link domain is fabricated: Apple `OpenURLIntent` accepts universal
links, and one can only be added after an owned HTTPS domain and its association
file are available.

Packet Tunnel Providers do not run in the iOS simulator. Use a physical iPhone for
VPN testing. The first save/start asks the user to approve the VPN configuration.

## The native core

`QeliCore/Native/Qeli.xcframework` is **not committed** — it is `.gitignore`d and built by
`build_native.sh`, while `project.yml` requires it unconditionally. A clean checkout
therefore cannot generate the Xcode project until you run that script once; if
`generate_project.sh` or `xcodebuild` fails complaining about a missing framework, that is
the reason, not a broken project file.

`build_native.sh` compiles the Rust crate three times — `aarch64-apple-ios` for the device,
plus `aarch64-apple-ios-sim` and `x86_64-apple-ios` lipo'd into one simulator slice — and
packages both with the headers from `QeliCore/Native/include` into the XCFramework. It
builds `--no-default-features`: the iOS slice is the protocol core only, with no server,
TUN or CLI code. `QELI_RUST_MANIFEST` and `QELI_CARGO_TARGET_DIR` override the paths for
out-of-tree builds.

The Swift side talks to it through a deliberately small C ABI (`QeliCore/Native/QeliFFI.swift`
over `include/`): `qeli_realtls_new` / `_open` / `_seal` / `_recv` / `_free` / `_buf_free`
for the REALITY TLS session, `qeli_mlkem_keygen` / `_decapsulate` / `_free` for the
post-quantum KEM, and `qeli_build_faketls_clienthello`. Everything else — record framing,
routing, profile storage — is Swift.

Two consequences worth stating plainly. The XCFramework is a **build artefact of a specific
Rust revision**: change anything under `qeli/src/` that the FFI touches and you must re-run
`build_native.sh`, or Xcode will keep linking the stale archive and the mismatch will surface
as a runtime handshake failure rather than a compile error. And because the header set is
the contract, adding a Rust `extern "C"` function without updating `include/` leaves it
invisible to Swift.

## Platform differences

- Android's boot receiver maps to VPN On Demand; consumer iOS has no boot callback.
- Arbitrary per-app include/exclude selection requires managed Per-App VPN (MDM) on
  iOS, so the keys round-trip but the consumer build does not claim to apply them.
- Android's Quick Settings tile maps to the iOS 18 WidgetKit control; iOS 17 uses the
  interactive Home Screen widget.
- TCP bonding mirrors Android's JOIN protocol. UDP remains one logical datagram path,
  matching the Android implementation.

Managed Per-App VPN and Apple's IKEv2-only Always On behavior are documented in
[`MDM/README.md`](MDM/README.md). The examples don't claim consumer or custom-provider
capabilities that iOS doesn't expose.
