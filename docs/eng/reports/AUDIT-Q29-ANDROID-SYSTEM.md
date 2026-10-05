# Q29: Android system Always-on, lockdown and process death

<!-- normative-sync: q29-android-system-v1 -->

**5 October 2026. Partial result; Q29 IN_PROGRESS. Plan28/37(75.7%),9 sections remain. The complete system gate is FAIL: automatic redelivery after external SIGKILL is unqualified.**

## Boundaries exercised

One new debug instrumented bootstrap saves the active INI profile through the real encrypted ProfileStore, verifies TCP16KiB/UDP257 over IPv4/IPv6 to off-pool targets, then ends. Android finishes instrumentation by force-stopping its target package: separate am instrument calls cannot leave the VPN running between them. Subsequent actions therefore run in the external driver; UDP probes run in a standalone Java test-APK receiver,UID10148,distinct from Qeli UID10149. It uses ordinary DatagramSocket without Network binding,process binding,protect or root. The receiver is absent from the product APK. Platform Java avoids Kotlin runtime dependencies available from the target only during instrumentation.

The actual Android Settings UI enables Always-on VPN and Block connections without VPN; UI XML is retained. The OS launches the saved kill_switch=true full-tunnel/reconnect profile with pinned identity/client key proof; Auth and native NetworkPlan are observed. Reading secure settings adds evidence; writing those settings does not substitute for enabling the policy.

## Results

| Scenario | Result |
| --- | --- |
| Bootstrap,dual-stack TCP/UDP payload | 1 new instrumented PASS,4 replies |
| Ordinary app probe without VPN | PASS: target reachable over the physical path |
| Actual Always-on+lockdown | PASS:TUN-sourced reply |
| External kill -9 of Qeli | FAIL (issue OPEN):no new process/NetworkPlan within45s |
| Probe after SIGKILL | PASS:socket error,0 sink deliveries |
| User force-stop | PASS:no TUN,probe blocked,0 deliveries |
| Explicit relaunch/system policy toggles | PASS:new Auth/NetworkPlan,foreground,TUN reply |
| Disable policy/Forget VPN in Settings | PASS:service/TUN absent,connection_desired=false,ACTIVATE_VPN=ignore |

A physically reachable baseline distinguishes blocking from an unreachable endpoint. Tagged UDP payloads have independent sink SHA256 receipts. Negative probes attempt to send; they have no source-readiness preflight. These negative cases cover IPv4 UDP to one off-pool target,not a complete TCP/IPv6 leak matrix or physical Internet.

## Open SIGKILL result

Before kill,dumpsys reports isForeground=true,startRequested=true,startCommandResult=3 and a delivered android.net.VpnService intent. Exit info records SIGNALED/status9,rather than force-stop. TUN disappearance triggers Vpn.interfaceRemoved unbinding the dead service and DeadObjectException before ActivityManager processes app death. A stale app=null ServiceRecord remains without a scheduled restart. Several independent readonly runs reproduce the failure. Tested traffic remains blocked under lockdown;manual recovery works.

The [START_REDELIVER_INTENT contract](https://developer.android.com/reference/android/app/Service#START_REDELIVER_INTENT) provides redelivery after process death. [Android14 r1 ActiveServices](https://raw.githubusercontent.com/aosp-mirror/platform_frameworks_base/android-14.0.0_r1/services/core/java/com/android/server/am/ActiveServices.java) calls serviceProcessGoneLocked on an unbind exception;killServicesLocked walks running-service records to schedule restart. This supports a framework bookkeeping race hypothesis;this source is **not established as the exact emulator image source**. No causal product defect is proven. REDELIVER was not arbitrarily replaced by STICKY;no resurrection watchdog was added. Next:an independent minimal VpnService control and another system process-death mechanism. The failure remains open,not PASS/USER_SKIPPED.

## Harness and reproducibility

Only tests/driver changed:singular instrumentation output;bounded timeout instead of nc -w misuse;real separate UID instead of shell/su sockets;platform Java for standalone probes;instrumentation force-stop separation;bounded Wait for SystemUI ANR;already-open management-screen detection;FORGET text selection instead of button1,which is DISMISS here. Failed attempts remain separate and are not called core regressions.

Android14/API34 x86_64,readonly AVD768MiB/1core and Linux Qeli in fresh NET/MNT/PID namespaces on.11,no external uplink. Product APK9af9789d…/JNI are unchanged;no Rust/product fix.290 previous source inputs,14 native hashes and7 managed DLLs match;293 current inputs,fresh test-APK build only. Prior167JVM/28Android/1248.NET/Release-R8-lint and3+6+7 integration stages retain their original scopes,not a fresh combined45Android run. Every attempt checks host network/qeli.service and userdata SHA/mtime/size;.10 untouched;arm64 not executed.

Raw:C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q29-android-system-20261005. Evidence:release/certification/evidence/q29-android-system-20261005.json. Driver --suite system. Previous [off-pool/DNS and data plane](AUDIT-Q29-ANDROID-DATA.md) remain distinct qualifications. Q29 stays open:SIGKILL recovery,Doze,roam/protect,Release runtime,olderAPI,physical/OEM scenarios. Early CONNECTED/source readiness stays open in the earlier report.


Final run213.97s,bootstrap2.421s. The complete gate correctly returned FAIL solely for SIGKILL recovery;all other listed criteria completed. Seven receipts:4 bootstrap,1 physical baseline,1 protected,1 manual recovery;two blocked probes had no delivery. Final service/TUN absent,AndroidRuntime without FATAL. All13 attempts preserve host/service/userdata,serverexit0,namespace addresses restored. Consent is proven revoked after named FORGET and waiting for ACTIVATE_VPN=ignore;onRevoke was observed during the disable-policy/Forget sequence,not an artificial method call.
