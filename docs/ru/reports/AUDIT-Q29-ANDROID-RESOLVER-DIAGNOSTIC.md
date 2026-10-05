# Q29: сравнение Android DNS API

<!-- normative-sync: q29-android-resolver-diagnostic-v1 -->

5 октября 2026. Q29 IN_PROGRESS; план 28/37 (75,7%). Один успешный readonly API34 x86_64 Release/TCP run на .11 в private NET/MNT/PID; четыре сохранённые неуспешные попытки. .10 не использовался.

Независимый test APK UID10148, Qeli UID10149. Реальный UI-импорт INI, Always-on/lockdown, dns=tunnel и dns_servers=198.19.0.53. Product APK/JNI/managed прежние; изменены test receiver/manifest и Python helpers. Matching instrumentation не выполнялась, предыдущий Trace FAIL открыт.

| Вариант | Фактический результат |
| --- | --- |
| `connectivity` | 8 no-payload connectivity checks |
| `auto` | ExecutionException:android.net.DnsResolver$DnsException: android.system.ErrnoException: resNetworkQuery failed: ENONET (Machine is not on the network) |
| `a` | 198.19.0.1 |
| `aaaa` | 2001:db8:29::1 |
| `auto-active` | 198.19.0.1,2001:db8:29::1 |
| `a-active` | 198.19.0.1 |
| `aaaa-active` | 2001:db8:29::1 |

`auto` — automatic-family DnsResolver.query с неявной сетью; `a`/`aaaa` — typed overload. Суффикс `-active` передаёт ConnectivityManager.getActiveNetwork. Новое уникальное имя для каждого вызова, cache-bypass flags, ожидание 7 секунд и CancellationSignal. Ошибки сохранены независимо от успешного обычного InetAddress.getAllByName.

`connectivity`: восемь no-payload проверок Os.socket → optional Network.bindSocket → Os.connect(port0), null/active VPN × 8.8.8.8/2000::/два fixture-адреса. Записаны фазы ошибки и metadata capabilities/LinkProperties обычного UID. Это local socket checks, а не доказательство доставки.

Непрерывный private-host pcap: уникальные questions/answers, TTL0, точные A198.19.0.1/AAAA2001:db8:29::1, sink receipts. Все доставленные диагностические DNS-вопросы имеют TUN source10.86.0.2; API error без пакетов не доказывает общую DNS-совместимость.

288 socket samples по шести фазам, 48 post-force-stop без ответа/receipt/capture, семь обычных DNS operations, четыре manual recovery payloads и revoke/cleanup PASS; 174 echo receipts. Первые post-plan сокеты: `NOT_SAMPLED_AFTER_PLAN`. При окончании короткой серии до APPLIED diagnostic opt-in записывает NOT_SAMPLED_AFTER_PLAN; обычный startup gate строгий. Это отсутствие покрытия, не readiness PASS; прежний FAIL открыт.

Четыре failed attempts сохранены: два NameError отсутствующего wait_until (первый патч не совпал с импортом; финальный импорт проверен до запуска) burst ended before APPLIED и KeyError неинициализированного списка диагностики. Два локальных теста смешанных ответов/ошибок и неверного UID PASS. APK-пара одна и та же. Exact executed helpers и cleanup сохранены. Во всех пяти попытках host/service/userdata/namespace restoration неизменны, serverexit0. Product preferences не инъецировались.

Сохранены первичные AOSP android14-release DnsResolver/DnsUtils/Network/NetworkUtils/JNI. Branch не доказан как точная ревизия image. По reference общий overload проверяет семейные socket checks до DNS, typed overload их пропускает. Скрытая сеть getDnsNetwork напрямую не наблюдалась. Различие null/explicit-active само по себе не доказывает дефект маршрутов Qeli.

Первоначальный ENONET, immediate startup publication, split/per-app/Private DNS, long power/flapping и SIGKILL recovery FAIL остаются. Один AVD не квалифицирует OEM/arm64/другие API. USER_SKIPPED/D06 unchanged.

Raw: `audit-debt-20260924/q29-android-resolver-diagnostic-20261005`; evidence: `release/certification/evidence/q29-android-resolver-diagnostic-20261005.json`.
