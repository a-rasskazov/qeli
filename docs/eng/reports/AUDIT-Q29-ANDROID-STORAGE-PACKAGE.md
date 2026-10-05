# Q29: Android storage, manifest and Release package

<!-- normative-sync: q29-android-storage-package-v1 -->

**5 October 2026: stage PASS; Q29 IN_PROGRESS. Plan28/37(75.7%),9 sections remain.**

| Finding | Fix |
|---|---|
| F273 | specialUse used an unknown manifest property instead of android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE. Correct name and purpose description added. API34 PackageManager checks property, privacy/permission and service types. Old APK reproduces NameNotFoundException; this does not prove startForeground fails on every OS. |
| F274 | Failed legacy Tink migration aborted open: Activity could not capture a revision or explicitly restore a backup. Partial keysets could resemble an empty store. Revision remains available; ordinary reads/writes refuse, explicit backup restore authorizes a CAS replacement. Legacy ciphertext survives; failed encrypted migration cannot trigger plaintext/default save. Failed deletion after a verified migration does not block the usable new store. |
| F275 | BigInteger.intValueExact requires API31 despite minSdk28. Direct BigDecimal.intValueExact is available sinceAPI1 and still rejects fractions/overflow. Release lint NewApi error resolved. Old call confirmed in source/initial lint; no Android9–11 runtime claim. |
| F276 | allowBackup=false alone does not cover every OEM D2D transfer. Nine credential/device-protected domains explicitly excluded from cloud/device-transfer; fullBackupContent=false for older OS. Packaged manifest/XML checked; physical OEM/cloud/D2D backup not executed. Explicit user backup export remains available. |

Removed five unreachable SDK<26/<28 branches in boot/tile/widget/Activity. minSdk28 unchanged; no new INI settings. Internal JSON archives/journals are not JSON configuration support; native core still rejects JSON configs.

## Checks/evidence

- **167 JVM PASS,0 failures/errors/skips**, production host ConfigCore JNI. Debug/androidTest and unsigned R8/resource-shrunk Release builds and lintRelease complete. Lint **0 errors,55 warnings**, no new-error baseline/suppression. Warning triage covers dependency notices, UI/layout/plurals, legacy attributes and intentional host-JNI override. AAB language splits unqualified; current distribution uses APK.
- **18/18 debug instrumentation PASS** on temporary Android14/API34 x86_64 AVD. Six new tests against preceding12: specialUse property, private service/types, packaged cloud/D2D rules, unreadable/partial legacy recovery and lost Keystore key. Exact ciphertext preservation, ordinary write/editor refusal, explicit restore, stale restore rejection and reopen checked. Actual JNI INI round-trip/JSON rejection and split/full/dual TUN establish repeated.
- Old production APK baseline: **3 tests,2 expected FAIL**, service privacy/type case PASS. Only tests added; product source unchanged.
- First full run:16 PASS; TUN case failed because the harness omitted ACTIVATE_VPN. Preserved; isolated AVD setup repaired,then18 PASS. Two new-test compile errors (nullable SDK return/hidden ApplicationInfo field), offline lint-cache failure and NewApi lint failure retained; these are not product regression claims.
- A debug test APK against minified Release is not a qualified Release test variant. Crash retained/diagnosed separately from production UI smoke; no3 Release instrumentation PASS claimed.
- Unchanged native digest/14actual hashes and183 preceding managed/Swift inputs/7DLLs. Prior1248 .NET checks reused, not rerun or called fresh Android results. Exact JNI.so hashes packaged; no Rust/native AB rebuild needed.

R8 production UI smoke: **PASS on Android14/API34 x86_64: resolved production launcher, cold start, process alive and not debuggable, no fatal logcat errors. The first launch opens Android battery-optimization permission UI; application startup is checked, not a complete Activity interaction or VPN traffic scenario.**. Release fixture uses only the debug test key in a temporary AVD; no production signing/published APK.

Raw: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q29-android-20261005.
Evidence: release/certification/evidence/q29-android-storage-package-20261005.json.

## Operation and remaining Q29

Unreadable legacy profiles must not trigger automatic app-data/ciphertext deletion. Restart the process to retry transient migration; a lost device-bound key requires a usable previously exported backup. Restore uses the existing explicit UI confirmation and rejects stale revisions. A lost key cannot be recreated without a backup. System encrypted-preference transfer does not transfer the Keystore key; explicit user export/import is the supported path.

Only separate read-only AVD sessions; original userdata SHA/mtime/size preserved. Working qeli.service and host routes/firewall/resolver/.10 unchanged; no push/deploy; primary human WIP retained.

Remaining: full connect/reconnect/cancel/revoke/process-death/always-on/lockdown/Doze, JNI/TUN generation/protect races and TCP/UDP traffic; Release lifecycle, older Android API,arm64/physical LTE and other backup/migration failures. D12 network evidence remains historical. The whole section stays open.

Contracts: [specialUse property](https://developer.android.com/reference/android/content/pm/ServiceInfo), [BigDecimal exact/API1](https://developer.android.com/reference/java/math/BigDecimal), [BigInteger exact/API31](https://developer.android.com/reference/java/math/BigInteger), [Android backup/D2D](https://developer.android.com/identity/data/autobackup).

Release test-variant diagnostic: NoClassDefFoundError for kotlin.jvm.internal.Intrinsics in AndroidJUnitRunner/MonitoringInstrumentation. The debug test APK depends on unminified target classes; ordinary production launcher succeeds without instrumentation. Retained diagnostic is not a Release instrumentation PASS or a client launch defect.
