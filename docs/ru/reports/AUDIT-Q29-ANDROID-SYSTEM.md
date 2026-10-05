# Q29: системные Always-on, lockdown и смерть процесса Android

<!-- normative-sync: q29-android-system-v1 -->

**5 октября 2026. Частичный результат; Q29 IN_PROGRESS. План28/37(75,7%),9 разделов осталось. Общий системный gate FAIL: автоматическая redelivery после внешнего SIGKILL не подтверждена.**

## Проверяемые границы

Один новый debug instrumented bootstrap сохраняет активный INI-профиль через штатный encrypted ProfileStore, проверяет TCP16KiB и UDP257 по IPv4/IPv6 к off-pool адресам и заканчивается. Android завершает instrumentation через force-stop целевого пакета: оставлять VPN работающим между отдельными am instrument нельзя. Поэтому следующие действия выполняет внешний driver, а UDP-пробы — отдельный Java receiver тестового APK, UID10148, отличный от UID10149 Qeli. Он использует обычный DatagramSocket без bindSocket, привязки процесса, protect или root. Test receiver не попадает в product APK; Java использует только platform classes, поскольку Kotlin runtime тестового APK доступен через target APK только во время instrumentation.

Системная политика включается настоящими Android Settings, с сохранением UI XML: Always-on VPN и Block connections without VPN. Запущенный системой профиль имеет kill_switch=true, full-tunnel, reconnect=true, pinned identity/client key proof; сервер подтверждает Auth и native NetworkPlan. Secure settings читаются как дополнительное свидетельство, их запись не подменяет включение политики.

## Результаты

| Сценарий | Результат |
| --- | --- |
| Bootstrap, dual-stack TCP/UDP payload | 1 новый instrumented PASS,4 ответа |
| Обычная проба без VPN | PASS: цель доступна по физическому пути |
| Настоящий Always-on+lockdown | PASS: ответ с source TUN |
| Внешний kill -9 процесса Qeli | FAIL (вопрос открыт): нет нового процесса/NetworkPlan за45s |
| Проба после SIGKILL | PASS: ошибка сокета,0 доставок на ответчик |
| Пользовательский force-stop | PASS: TUN отсутствует,проба заблокирована,0 доставок |
| Явный повторный запуск и переключение системной политики | PASS: новый Auth/NetworkPlan,foreground и ответ через TUN |
| Отключение политики и Forget VPN в Settings | PASS: сервис/TUN отсутствуют,connection_desired=false,ACTIVATE_VPN=ignore |

Наличие физически доступного ответчика до включения политики отличает блокировку от недоступности сети. Каждый tagged UDP payload имеет независимый SHA256 на ответчике. Отрицательные пробы действительно пытаются отправить пакет; ожидания source/preflight перед отправкой нет. Эти две отрицательные проверки охватывают только IPv4 UDP к одному off-pool назначению; это не полная TCP/IPv6 leak-матрица и не физический Интернет.

## Открытый результат SIGKILL

Перед убийством dumpsys показывает isForeground=true,startRequested=true,startCommandResult=3 и доставленный android.net.VpnService intent. Android фиксирует SIGNALED/status9, а не пользовательский force-stop. Сначала исчезает TUN; системный Vpn.interfaceRemoved пытается unbind уже умершего сервиса и получает DeadObjectException. Затем ActivityManager регистрирует смерть процесса; остаётся ServiceRecord с app=null и без запланированного restart. Отказ повторяется в нескольких независимых readonly запусках. Lockdown при этом продолжает блокировать проверяемый трафик; вручную подключение восстанавливается.

[Документированный контракт START_REDELIVER_INTENT](https://developer.android.com/reference/android/app/Service#START_REDELIVER_INTENT) предусматривает повторную доставку незавершённого intent после смерти процесса. В [ActiveServices Android14 r1](https://raw.githubusercontent.com/aosp-mirror/platform_frameworks_base/android-14.0.0_r1/services/core/java/com/android/server/am/ActiveServices.java) ошибка unbind вызывает serviceProcessGoneLocked, а killServicesLocked обходит running-service записи для restart. Это поддерживает гипотезу о гонке framework bookkeeping. Источник **не является доказанным исходником точного образа эмулятора**; причинная ошибка продукта не установлена. Произвольная замена REDELIVER на STICKY или добавление watchdog не выполнены. Следующее исследование — независимый минимальный VpnService-контроль и другое системное завершение процесса. Этот FAIL не превращён в PASS/USER_SKIPPED.

## Обвязка и воспроизводимость

Исправлены только тесты/driver: singular/plural instrumentation output; ограниченный timeout вместо неверного nc -w; отдельный реальный UID вместо shell/su сокета; Java вместо недоступного Kotlin runtime standalone APK; force-stop после instrumentation; bounded Wait при SystemUI ANR; распознавание уже открытого management экрана вместо поиска отсутствующей шестерёнки; выбор подтверждения FORGET по тексту вместо button1, который здесь означает DISMISS. Все неудачные попытки сохранены отдельно и не объявлены регрессиями ядра.

Стенд Android14/API34 x86_64,readonly AVD768MiB/1core и Linux Qeli в новых NET/MNT/PID namespaces .11,без внешнего uplink. Product APK9af9789d… и JNI побайтно прежние; Rust/продукт не изменены.290 прежних source inputs,14 native hashes и7 managed DLL неизменны; текущие входы293,новая сборка только test APK. Старые167JVM/28Android/1248.NET/Release-R8-lint и3+6+7 integration этапы сохраняют исходные области,не выданы за новый общий запуск45Android. Во всех попытках сверяются host network/qeli.service и userdata SHA/mtime/size; .10 не используется. Arm64 не исполняется.

Raw: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q29-android-system-20261005. Evidence: release/certification/evidence/q29-android-system-20261005.json. Команда driver --suite system. Предыдущие [off-pool/DNS и data plane](AUDIT-Q29-ANDROID-DATA.md) остаются отдельными квалификациями. Q29 открыт: SIGKILL recovery,Doze,roam/protect,Release runtime,старые API и физические/OEM сценарии. Ранний CONNECTED/source selection остаётся открытым в предыдущем отчёте.


Финальный прогон213,97s,bootstrap2,421s. Общий gate корректно вернулFAIL только из-за SIGKILL recovery;остальные перечисленные критерии завершены. Семь ответов:4 bootstrap,1 физический baseline,1 protected,1 manual recovery;две блокируемые пробы не доставлены. Финальные service/TUN отсутствуют,AndroidRuntime безFATAL. Во всех13 попытках host/service/userdata неизменны,серверexit0,адреса namespace восстановлены. Отзыв доказан после FORGET по тексту и ожидания ACTIVATE_VPN=ignore;системный onRevoke наблюдался в последовательности отключения политики/Forget,а не при искусственном вызове метода.
