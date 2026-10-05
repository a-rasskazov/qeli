# Q29: Android VPN-трафик и lifecycle после Auth

<!-- normative-sync: q29-android-data-v2 -->

**5 октября 2026. Этап PASS; Q29 IN_PROGRESS. План: 28/37 (75,7%), осталось 9 разделов.**

## Что подтверждено

Три новых instrumented-сценария запускают настоящий VpnService и JNI: TCP fake-tls, UDP fake-tls, UDP QUIC. Клиент проверяет pinned server identity и bind_static_to_session; сервер требует client key proof. Каждый режим устанавливает dual-stack TUN и передаёт TCP-поток 16 KiB и UDP-пакеты 32/257/1024 байта в обе стороны по IPv4 и IPv6. Ответчик возвращает обратный TCP payload или UDP payload с отдельным префиксом; проверяются байты, а на сервере сохраняются адреса клиентов и SHA256. Это не benchmark.

После трафика неверный ACTION_CONNECT должен сохранить CONNECTED, negotiated properties, foreground и connection_desired; затем повторный трафик подтверждает сохранение сессии. Ручное отключение завершает сервис и удаляет TUN. TCP дополнительно проходит второй полный запуск после завершённой остановки.

**Новый прогон: 3/3 PASS**, 48 ответов тестового сервера от исправленного APK. Старый APK: 1 тест, 1 ожидаемый FAIL — после успешного IPv4/IPv6-трафика CONNECTED заменён ERROR; это дополнительная проверка уже исправленного F278, без новой правки продукта. Pcap серверного TCP TUN сохранён. Последние тесты явно используют Android VPN Network и ждут выбора kernel source из адресов TUN.

## Стенд и воспроизводимость

scripts/audit_android_data_plane_lab.py запускает Qeli и readonly AVD в новых NET/MNT/PID namespaces на .11, без внешнего uplink и production-профилей. Два INI-профиля используют NAT=false и IPv6 manual: проверяется доставка на адреса самого сервера, без внешней маршрутизации или DNS. Android14/API34 x86_64; memory768MiB/1core. Linux CLI сверяется с ранее квалифицированным SHA256; новой сборки Rust нет.

Product APK побайтно совпадает с предыдущим этапом. 289 прежних входов, JNI и 7 managed DLL неизменны; прежние 167 JVM,28 Android,1248.NET и Release/R8/lint(0errors55warnings) переиспользованы только в своих исходных областях. Они **не** объявляются новыми прогонами. Свежий общий запуск 31 Android теста не выполнялся. Без специальных аргументов приватного стенда три integration-теста пропускаются; обычный emulator job не подтверждает этот этап.

Старые попытки сохранены: неверное сочетание heartbeat/jitter в INI; несовпадающие ADB-порты; ранние Java-сокеты с физическим source и read timeout; отказ TCP-ответчика после EOF; первоначальная проверка счётчика ответов до завершения worker. Эти результаты не выданы за подтверждённую регрессию transport core. Обвязка ждёт фактический выбор source до отправки и продолжает принимать клиентов после EOF. Отдельная проверка EOF → новый запрос проходит для IPv4/IPv6. Обычный выбор сети приложениями сразу после CONNECTED не квалифицирован и остаётся следующим пунктом Q29: LinkProperties/CONNECTED сами по себе не доказывают готовность kernel routes.

Во всех пяти namespace-прогонах и первом config-only отказе userdata AVD сохранён по SHA256/mtime/size; рабочие сеть и qeli.service .11 совпадают до/после. Финальный сервер завершился с кодом0, адреса приватного namespace восстановлены; app service/TUN отсутствуют после force-stop, AndroidRuntime без FATAL EXCEPTION. .10 не затронут. Arm64 только сверяется в APK, не исполняется.

## Что остаётся

Автоматический выбор VPN обычными приложениями, full-tunnel/lockdown, DNS и внешние маршруты, Wi-Fi/LTE roaming/protect, revoke/process-death/redelivery/always-on/Doze, Release runtime и старые API. Нового физического LTE/OEM backup evidence нет. Этап не закрывает весь Q29. Предыдущие [framework lifecycle](AUDIT-Q29-ANDROID-SERVICE.md) и [TUN/JNI](AUDIT-Q29-ANDROID-LIFECYCLE.md) сохраняют собственные области проверки.

Raw: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q29-android-data-20261005.
Evidence: release/certification/evidence/q29-android-data-20261005.json.

## Дополнительный этап: обычные сокеты

Шесть новых сценариев (TCP fake-tls, UDP fake-tls, UDP QUIC × split/full) используют обычные Socket/DatagramSocket, без Network.bindSocket/socketFactory и без привязки процесса. **6/6 PASS,72 серверных ответа**: IPv4/IPv6, TCP16KiB, UDP32/257/1024, неверный CONNECT после трафика и ручной stop. Native NetworkPlan подтверждает три mode=full и три mode=split. Адреса назначения принадлежат TUN самого сервера: проверка full-конфига ещё не доказывает захват внешнего/default трафика.

Обнаружено окно готовности: в **5/6 запусков первый IPv4-сокет после наблюдаемого CONNECTED выбрал физический source10.0.2.16**. Выбор TUN появился за1–111ms от момента наблюдения статуса; IPv6 при последующей проверке уже выбирал TUN. Это замер с polling25ms, двумя вызовами predicate при успехе и затратами проверок, не точное время применения netd. Диагностический UDP-сокет не отправляет данные. Payload передаётся только после bounded source preflight. Поэтому 6PASS подтверждают передачу после готовности, **не немедленный первый пакет после CONNECTED и не отсутствие утечки при kill_switch=false**. Причина и возможная корректировка публикации статуса остаются открыты; новая регрессия Rust не доказана.

Product APK/JNI неизменны, новых исправлений продукта нет. Свежая сборка test APK и шесть debug-тестов; прежние результаты используются только в исходных областях, общего нового запуска37Android нет. Без private fixture новые шесть тестов skip. Для scripts/audit_android_data_plane_lab.py добавлен --suite ordinary; стандартный explicit выбирает только прежние три метода.

Один прогон занял109,19s, тесты18,913s. Readonly API34 x86_64, отдельные NET/MNT/PID на.11, серверexit0, namespace addresses восстановлены, userdata SHA/mtime/size и рабочая сеть/service неизменны, app service/TUN отсутствуют, AndroidRuntime безFATAL. .10 не затронут. Raw: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q29-android-default-20261005; evidence: release/certification/evidence/q29-android-default-20261005.json. Q29 остаётся IN_PROGRESS; далее внешние маршруты/DNS/kill-switch, ранний первый пакет и системный lifecycle.
