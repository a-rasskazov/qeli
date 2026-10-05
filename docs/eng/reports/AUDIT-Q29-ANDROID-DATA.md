# Q29: Android VPN payload and post-auth lifecycle

<!-- normative-sync: q29-android-data-v1 -->

**5 October 2026. Stage PASS; Q29 IN_PROGRESS. Plan28/37(75.7%),9 sections remain.**

## Qualified behavior

Three new instrumented cases start actual VpnService/JNI:TCP fake-tls,UDP fake-tls,UDP QUIC. Client verifies a pinned identity with bind_static_to_session;server requires client key proof. Each establishes dual-stack TUN and sends a16KiB TCP stream and32/257/1024byte UDP payloads both ways overIPv4/IPv6. The independent sink reverses TCP payload or prefixes UDP replies;exact bytes,server-side source addresses andSHA256 are recorded. This is not a benchmark.

After traffic,invalid ACTION_CONNECT must preserve CONNECTED,negotiated properties,foreground andconnection_desired;further traffic verifies continuity. Manual disconnect removes service/TUN. TCP also completes a second authenticated start after preceding teardown finishes.

**Fresh3/3 PASS**,48 sink replies for the fixedAPK. OldAPK:1test,1expectedFAIL after successfulIPv4/IPv6traffic replaces CONNECTED withERROR;additional coverage of already fixedF278,no new product patch. ServerTCP-TUN pcap retained. Final tests explicitly bind AndroidVPNNetwork and wait for kernel source selection from assignedTUN addresses.

## Fixture and provenance

scripts/audit_android_data_plane_lab.py runs Qeli andreadonlyAVD in freshNET/MNT/PID namespaces on.11,without external uplink orproduction profiles. TwoINI profiles useNAT=false andIPv6manual;traffic targets the server's own tunnel addresses,no external routing orDNS. Android14/API34 x86_64,memory768MiB/1core. LinuxCLI matches a previously qualifiedSHA256,no freshRust build.

ProductAPK matches preceding stage byte-for-byte.289 prior inputs,JNI and7managedDLLs unchanged;prior167JVM,28Android,1248.NET andRelease/R8/lint(0errors55warnings) reused only within their original scopes. These are **not** fresh runs. No fresh combined31Android run. Without private fixture arguments the three integration tests skip;ordinary emulator CI does not qualify this stage.

Earlier attempts retained:invalidINI heartbeat/jitter combination;differentADB ports;early Java sockets selecting physical source/read timeouts;TCP sink terminating onEOF;initial sink-count assertion racing worker completion. They are not presented as a proven transport-core regression. Harness waits for actual kernel source before sending and keeps accepting afterEOF. Independent IPv4/IPv6 EOF → fresh-request check passes. Ordinary apps' immediate default-network selection afterCONNECTED remains unqualified andnext inQ29:LinkProperties/CONNECTED alone do not prove kernel-route readiness.

All five namespace executions and the initial config-only failure preserveAVDuserdata SHA256/mtime/size;working.11 hostnetwork/qeli.service match before/after. Final server exits0,private namespace addresses restored;no app service/TUN afterforce-stop,noAndroidRuntimeFATAL. .10 untouched. Arm64 packaged bytes checked,not executed.

## Remaining scope

Ordinary apps' automaticVPNselection,full-tunnel/lockdown,DNS/external routes,Wi-Fi/LTEroaming/protect,revoke/processdeath/redelivery/always-on/Doze,Release runtime andolderAPIs. No new physicalLTE/OEMbackup evidence. WholeQ29 remains open. Earlier [framework lifecycle](AUDIT-Q29-ANDROID-SERVICE.md) and[TUN/JNI](AUDIT-Q29-ANDROID-LIFECYCLE.md) retain their own scope.

Raw:C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q29-android-data-20261005.
Evidence:release/certification/evidence/q29-android-data-20261005.json.
