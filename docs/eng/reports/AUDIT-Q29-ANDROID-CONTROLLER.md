# Q29 F282: socket-protection ownership and trusted-Wi-Fi failures

<!-- normative-sync: q29-android-controller-v1 -->

F282 prevents an already-polled JNI socket-protection request from selecting or binding a
carrier after shutdown begins or after its core has been replaced. Each protect attempt
now checks stopping, core identity and active configuration under the service monitor,
before platform side effects. Retry sleeps and the JNI acknowledgement remain outside
that monitor. No INI parameters, Rust/JNI or managed code changed.

## Reproduction and checks

The same freshly built test APK runs against the preceding F281 debug product and the
fixed product. Old: eight tests, exactly three expected failures. Fixed: eight PASS.
The old implementation selected a carrier after stop, allowed an old core to select a
carrier for the current connection, and blocked only inside carrier selection rather
than at the protection owner check.

Three protection cases use actual native socket requests and packaged JNI, with a service
object attached to Context and explicitly injected lifecycle/core ownership. The concurrent
case holds its monitor and verifies the blocked production frame before release. These are
adapter fixtures, not complete framework stop/revoke races or a proof of a kernel FD leak.
The protected socket is real; no replacement transport or fabricated protect event.

Five other cases use the actual framework service, Activity, Wi-Fi/Cellular callbacks and
TCP transport. Two are new: turning Android location visibility off redacts the observed
SSID, restores the tunnel, and turning it back on allows pause again; queued pause then
disconnect does not resurrect the controller and a fresh explicit start works. The latter
checks queued commands, not a deterministic barrier inside the native teardown join.
The three preceding trusted-pause/resume/cancellation/kill-switch refusal cases are repeated.
Permissions are externally granted; SSID settings are set locally by the adapter, rather
than through the settings editor. Four socket kinds explicitly bind to VPN Network.
Seven authenticated stages deliver 28 full IPv4/IPv6 TCP16KiB/UDP257 replies, independently
verified by sink SHA and assigned TUN sources.

Fresh 182 JVM tests, default production R8 Release/debug builds and lint pass (0 errors,
55 existing warnings). No new JVM cases; the five new cases execute on Android. The private
`--suite trusted-wifi --variant debug --transport tcp` helper now selects these eight tests.
Standalone production Release smoke uses the real INI file picker, Android Settings
lockdown and a separate UID Java probe; matching Release instrumentation is NOT RUN.
The qualification evidence records each runtime outcome and exact source/APK hashes.

## Final grouped result

| Run | Outcome | Verified scope |
| --- | --- | --- |
| Preceding debug product, fresh tests | 5 PASS, 3 expected FAIL | Same eight-test APK reproduces F282 |
| Fixed debug product | 8/8 PASS | Three protect-owner fixtures, five framework trusted-Wi-Fi cases; 28 full payloads |
| Production R8 TCP | PASS | Two carrier transitions, 12 full ordinary-UID payloads, 288 socket samples |
| Production R8 UDP | PASS | Two carrier transitions, 12 full ordinary-UID payloads, 288 socket samples |
| Production R8 QUIC | PASS | Two carrier transitions, 12 full ordinary-UID payloads, 288 socket samples |

Together: six Release transitions, 36 Release plus 28 debug full payloads (64), 864 Release
socket samples including 144 blocked post-stop requests. Independent pcap reassembly verifies
all 36 Release tagged payload SHA values and TUN sources. All four physical outgoing probe
kinds are positively calibrated; no new physical request occurs in the qualified windows,
and all three captures report zero kernel drops. This does not claim lossless handover:
away-phase replies are TCP44/48, UDP40/48, QUIC44/48; return is48/48 for each.
All five runtime attempts restore host/service, readonly AVD userdata and namespace addresses,
stop the private server, and leave no Qeli service or TUN.

Provenance covers303 Android/build inputs (four changed),23 auxiliary inputs (one changed),
five unchanged regression inputs,14 unchanged native files,seven managed artifacts and six
APK artifacts. Native/server/managed reuse is explicit; arm64 JNI packaging is checked but
arm64 execution is not performed. Fifteen helper tests and four CLI rejection guards pass.

## Scope and remaining work

Raw: `audit-debt-20260924/q29-android-controller-20261006`.
Evidence: `release/certification/evidence/q29-android-controller-20261006.json`.
[Prior SIGKILL recovery FAIL](AUDIT-Q29-ANDROID-SYSTEM.md) and
[auto/null DnsResolver ENONET](AUDIT-Q29-ANDROID-RESOLVER-DIAGNOSTIC.md) remain open.
Real permission revocation (which can kill the app) is distinct from location-switch
redaction. Actual observer-registration failure, deterministic native pause-in-flight,
remaining lifecycle paths and other API/OEM/arm64 coverage are not closed by these tests.
Q29 stays IN_PROGRESS, overall28/37(75.7%). Physical/OEM long sessions are not qualified by
bounded API34 x86_64 readonly AVD runs. User-skipped platforms and D06 are unchanged.
