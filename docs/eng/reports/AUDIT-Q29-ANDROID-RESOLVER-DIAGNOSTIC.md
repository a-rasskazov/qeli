# Q29: comparing Android DNS APIs

<!-- normative-sync: q29-android-resolver-diagnostic-v1 -->

October5,2026. Q29 IN_PROGRESS;plan28/37(75.7%). One successful readonly API34 x86_64 Release/TCP run on .11 in private NET/MNT/PID;four preserved failed attempts. .10 untouched.

Independent test APK UID10148,Qeli UID10149. Real INI UI import,Always-on/lockdown,dns=tunnel,dns_servers=198.19.0.53. Product APK/JNI/managed unchanged;test receiver/manifest and Python helpers changed. Matching instrumentation not executed;prior Trace FAIL open.

| Variant | Actual result |
| --- | --- |
| `connectivity` | 8 no-payload connectivity checks |
| `auto` | ExecutionException:android.net.DnsResolver$DnsException: android.system.ErrnoException: resNetworkQuery failed: ENONET (Machine is not on the network) |
| `a` | 198.19.0.1 |
| `aaaa` | 2001:db8:29::1 |
| `auto-active` | 198.19.0.1,2001:db8:29::1 |
| `a-active` | 198.19.0.1 |
| `aaaa-active` | 2001:db8:29::1 |

`auto`:automatic-family DnsResolver.query with implicit network;`a`/`aaaa`:typed overload. `-active` passes ConnectivityManager.getActiveNetwork. Fresh unique name per call,cache-bypass flags,7-second wait,CancellationSignal. Errors retained independently of successful ordinary InetAddress.getAllByName.

`connectivity`:8no-payload Os.socket → optional Network.bindSocket → Os.connect(port0) checks,null/active VPN × 8.8.8.8/2000::/two fixture targets. Error phases and ordinary-UID capabilities/LinkProperties retained. Local socket checks,not delivery proof.

Continuous private-host pcap verifies unique questions/answers,TTL0,exact A198.19.0.1/AAAA2001:db8:29::1,sink receipts. All delivered diagnostic questions require TUN source10.86.0.2. API errors without packets do not demonstrate broad DNS compatibility.

288socket samples across6phases,48post-force-stop without reply/receipt/capture,7ordinary DNS operations,4manual recovery payloads,revoke/cleanupPASS;174echo receipts. Immediate first-socket status:`NOT_SAMPLED_AFTER_PLAN`. Diagnostic opt-in records NOT_SAMPLED_AFTER_PLAN if the short burst ends before APPLIED;ordinary startup gate strict. Missing coverage is not readiness PASS;prior failure open.

Four preserved failed attempts:two missing-wait_until NameErrors (first edit did not match;final import verified before run),one burst ended before APPLIED,one uninitialized-list KeyError. Two local mixed-answer/error and wrong-UID checks PASS. Exact executed helpers,same APK pair and cleanup retained. All5host/service/userdata/namespace restoration unchanged,serverexit0;no product preferences injection.

Primary AOSP android14-release DnsResolver/DnsUtils/Network/NetworkUtils/JNI retained,not proven exact image revision. Reference automatic-family overload checks family sockets before DNS;typed overload skips this. Hidden getDnsNetwork selection not directly observed;null/explicit-active differences do not themselves prove a Qeli routing defect.

Localization: auto/null ENONET without questions/receipts;typed/null A/AAAA and auto/active VPN answer. In AOSP getDnsNetwork obtains app_netid via getdnsnetid;getNetworkForConnectLocked chooses physical/unreachable network for secure VPN. Automatic-family overload explicitly binds family-check sockets there,conflicting with lockdown;DNS context separately selects dns_netid. This reference-based explanation matches runtime;the current image's hidden selected network was not directly measured. No justification to alter Qeli routes or weaken lockdown.

Broad DNS API compatibility,immediate startup publication,split/per-app/Private DNS,long power/flapping,SIGKILL recovery FAIL remain. One AVD does not qualify OEM/arm64/otherAPI versions. USER_SKIPPED/D06 unchanged.

Raw:`audit-debt-20260924/q29-android-resolver-diagnostic-20261005`;evidence:`release/certification/evidence/q29-android-resolver-diagnostic-20261005.json`.
