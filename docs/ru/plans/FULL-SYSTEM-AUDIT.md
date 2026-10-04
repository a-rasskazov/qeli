# Полный аудит Qeli: история проверок и пошаговый тестовый план

**Состояние на 3 октября:** [реестр техдолга](AUDIT-DEBT.md) завершён: 14 DONE
и D06 ACCEPTED_LIMITATION по решению пользователя. Полный аудит возобновляется;
статусы 37 разделов ниже сверяются по критериям, без автоматического PASS.


**Режим завершения с 25 сентября:** [четыре пакета и правила выбора проверок](AUDIT-DEBT.md)
заменяют повтор полного набора на каждую правку. Уровни ниже остаются критериями
покрытия раздела; отдельный отчёт на каждый небольшой шаг не обязателен. Новые
некритичные гипотезы ждут полного аудита, текущие обязательства сохраняются.

<!-- normative-sync: full-system-audit-v44 -->

**Текущий итог, 4 октября: 25/37 разделов DONE/PASS (67,6%), осталось 12. Q25 завершён; далее Q26.**

Дата инвентаризации: **22 сентября 2026**. База: ветка `dev`, commit
`fc6f4a5dc8df7f119f2d99a6b72b08916ae7a268`, разработка **0.8.2**.
Рабочее дерево до этой документации было чистым. Предыдущие исправления панели и
`manual + NDP` уже находятся в истории Git. Код продукта в этом этапе не изменялся.

Цель — последовательно проверить все системы Qeli на функциональные ошибки,
небезопасные границы доверия, гонки, утечки ресурсов/трафика, несогласованность
платформ, мёртвый код и расхождения документации. Это исполнимый план нового цикла,
а не заявление, что все системы уже прошли аудит.

## 1. Что удалось восстановить по памяти

Использованы история этой задачи, релевантные задачи «аудит» и «ipv6», локальная
память Qeli, сохранённые отчёты, Git и текущая структура исходников. Старые записи
могут относиться к удалённым реализациям; отметка «исправлено» в памяти не закрывает
регрессию на текущем commit. Независимый внешний криптоаудит этим не подтверждается.

| Источник | Период и восстановленное покрытие | Доказательство и предел |
|---|---|---|
| H01 | 10–12 июня: crypto/KDF/replay, handshake/framing, auth/Argon2, users/sessions, Win storage, DNS/kill switch и INI | [Аудит 10 июня](../archive/audits/AUDIT-2026-06-10.md), [11 июня](../archive/audits/AUDIT-2026-06-11.md), [12 июня](../archive/audits/AUDIT-2026-06-12.md); исторические версии |
| H02 | 18 июня — 5 июля: панель/CSRF, SSRF notify, DNS/DHCP, supervisor/control, NAT cleanup, obfs/WS/AWG и serializers | Память Qeli и [сводка 5 июля](../../archive/audits/AUDIT-FIXES-2026-07-05.md); отдельные старые подозрения были опровергнуты |
| H03 | 11–12 июля: trust boundary hooks/restore/client-save, session teardown, quota/iroute, clients и backup | Запись `project_qeli_audit_2026-07-11.md`; исторические fixes/build gates, не свежий E2E |
| H04 | 23–27 июля: core/data plane, UDP auth/HOL, pool races, max_clients, NAT tags, routes, парсеры, все клиенты и supply chain | Память core/client audits 24/25 июля и [сводка 27 июля](../../archive/audits/AUDIT-2026-07-27-FIXES.md); часть платформенных проверок была compile-only |
| H05 | 4 августа: общий аудит core, клиентов, панели и scripts | Запись `project_qeli_audit_2026-08-04.md`; перечень исторических кандидатов, не реестр текущих дефектов |
| H06 | Август–сентябрь: IPv6/TAP/NetworkPlan/PMTU/DATA_FRAG, roaming/CONTROL_V2, native/core parity | [План IPv6](IPV6-IMPLEMENTATION-PLAN.md), [роуминг](ROAMING.md), [transport core](../reference/TRANSPORT-CORE.md), `release/ipv6_lab_matrix_dev.json`; применимость evidence к текущему SHA перепроверяется |
| H07 | 26 августа — 1 сентября: REALITY/H2 PCAP, обнаружимость и throughput/CPU/RSS | [DPI](../reports/DPI-AUDIT.md), [сравнительный бенчмарк](../reports/benchmarks/vpn_protocol_benchmark_repeat_2026-09-01.md); измерения 0.8.0, не 0.8.2 |
| H08 | 16 сентября: общий многослойный аудит A01–A14 и fixes | Локальные `audit-vpn-20260916/AUDIT.md` и `FIX-VERIFICATION.md`; Rust/managed builds, probes и Linux tests; не физические платформенные E2E |
| H09 | 16–17 сентября: углублённый аудит панели/парсеров A01–A14 | Локальные `audit-panel-20260916/AUDIT.md`, `panel-fixes-20260917/RESULT.md`; Rust/JS probes, сохранение, ACL-поля, секреты, черновики и INI roundtrip |
| H10 | 22 сентября: продолжение панели A15–A22 | Локальные `audit-panel-20260922/AUDIT.md`, `panel-fixes-20260922/RESULT.md`; restart/preflight, staged restore, share transaction, quotes/dev, notify INI; commit `a8c5050b` |
| H11 | 22 сентября: IPv6 manual/NDP и документация | Локальный `ipv6-manual-20260922/RESULT.md`; commit `fc6f4a5d`; 632 portable Rust tests, 25 JS groups, 16 isolated runtime probes; без настоящего Linux NDP/firewall E2E |

Локальные отчёты H08–H11 лежат вне репозитория; их имена оставлены для поиска в
рабочем архиве. Секреты и адреса лабораторных/рабочих серверов сюда не переносятся.
Номера **A01–A14 повторно использованы в двух разных аудитах**: ссылка на находку
обязана включать H08 или H09. Числа тестов разных feature/OS-наборов не складываются
и не сравниваются как показатель роста или уменьшения покрытия.

## 2. Правила нового прохода

У каждого раздела две независимые оценки: **историческое покрытие** и **новый прогон**.
Состояния нового прогона: `TODO`, `IN_PROGRESS`, `PASS`, `FAIL`, `BLOCKED`, `N/A`.
`BLOCKED` требует причины и нужного стенда; `N/A` — подтверждённой неприменимости.
Отсутствующий runtime не превращает проверку в `PASS`. Исправленная находка закрывается
после проверки исправления; нерешённая находка остаётся в очереди независимо от других PASS.

Каждый раздел проходит одни и те же уровни:

1. **Структура:** входы/выходы, владелец состояния, зависимости, trust boundaries и все
   callers; OS/feature gates, FFI/reflection/generated code и потенциально мёртвые ветви.
2. **Контракт:** штатные сценарии, границы, malformed input, defaults и сохранение смысла;
   differential/roundtrip проверки независимыми реализациями.
3. **Отказы:** failure injection при acquire/apply/save, partial I/O, concurrent actions,
   timeout/cancel/crash/restart и корректное восстановление владельцем ресурса.
4. **Интеграция:** настоящий процесс/API/browser/TUN/firewall/OS adapter, затем реальные
   устройства, если поведение зависит от драйвера, ОС или мобильной сети.
5. **Регрессия:** воспроизводитель на исходном дефекте, исправление, повтор затронутых
   проверок, документация и фиксация результата с точным SHA/feature/target.

Для каждого шага нужен отчёт: ID, дата, commit + dirty diff/hash, версии инструментов,
OS/arch/features, команда, fixtures/seed, ожидаемый/фактический результат, stdout/stderr,
exit code, PCAP/host-state при необходимости, finding ID/severity и ограничения.
Гипотеза отделяется от воспроизведённого бага; accepted risk имеет обоснование.
Долгие тесты получают timeout и план остановки; утечки измеряются, а не оцениваются по UI.

До запуска старого lab/E2E-скрипта проверить target, hardcoded endpoints, cleanup,
credentials handling и destructive defaults. Наличие файла теста ниже означает
**точку входа для проверки обвязки**, а не готовый безопасный набор или доказанное
покрытие всех перечисленных сценариев. Результат теста самого harness не равен E2E.
Сетевые/разрушительные сценарии выполняются на отдельном стенде со снимком, не на prod.

## 3. Стенды и обязательная матрица

| Стенд | Назначение |
|---|---|
| Локальный portable | Parser/crypto/protocol/KAT, JS state, Python harness, docs; не Linux server runtime |
| Изолированный Linux | Server/CLI/API/backup/systemd/TUN/routes/DNS/NAT/NDP; iptables и nft/firewalld, multiprofile, crash recovery |
| Windows VM | GUI/LocalSystem/Wintun/WinDivert/ACL/DPAPI, реальные DNS/routes/firewall и восстановление |
| macOS Intel + ARM | launchd/utun/pf/Keychain/Network Extension/per-app; build отдельно от runtime |
| Android устройство | Release APK/JNI/VpnService, Wi-Fi/LTE/Doze/always-on/lockdown, sleep/wake |
| iOS устройство | Signed IPA/PacketTunnel/On Demand/NAT64/per-app/MDM; simulator отдельно |
| OpenWrt/Keenetic | MIPS/ARM и 32-bit ABI, init/UCI/LuCI, реальная сеть и ограниченная память |
| Нагрузочный стенд | Контролируемые bandwidth/RTT/jitter/loss/reorder/MTU, отдельные генератор и наблюдатель |

Сначала составить список **реально поддерживаемых** transport × obfuscation сочетаний
из кода: Quick Start не является полным списком protocol capabilities. Неподдерживаемые
сочетания проверять на понятный отказ, не записывать как недостающий PASS.
Для каждого поддерживаемого режима: соединение/auth, трафик вверх/вниз, DNS,
reconnect и stop/cleanup. Дополнительные оси:

- outer IPv4/IPv6 × inner IPv4/IPv6/dual; IPv6-only uplink/NAT64;
- full/split, TUN/TAP, client-to-client/site-to-site/per-app;
- IPv6 egress `off/manual/route/nat66` × NDP `off/auto/required`, все переходы;
- старый/новый сервер и клиент, несовместимые ABI/capabilities, off/prefer/required;
- single/multiprofile, single/multisession/multipath и пустой/исчерпанный pool;
- clean stop, timeout, revoke, crash, reload/restart, suspend/resume и network change.

Обязательные сочетания безопасности выполняются полностью. Для остальных взаимодействий
допустим pairwise-набор с явной таблицей покрытых комбинаций, а не обещание полного
декартова произведения. Для leak-проверок нужны packet capture на tunnel и physical
интерфейсах; для cleanup — before/after routes/DNS/firewall/sysctl/fd/tasks.

## 4. Этап 00 — исходная точка

**DONE: инвентаризация и ограниченные локальные проверки.** Это не завершение аудита
продукта. Следующий рабочий раздел — **01: серверный INI**, затем 02–07. Linux E2E
для последних административных и IPv6-изменений остаётся обязательным.

| Проверка на `fc6f4a5d` | Результат | Граница |
|---|---|---|
| `check_panel.py` | PASS: 11 шаблонов, 1142 RU строки | Статика |
| `test_panel_editors.cjs` | PASS: 25 групп | Реальные JS-компоненты в Node, не browser E2E |
| `unittest discover -s scripts -p 'test_native_*.py'` | PASS: 67 тестов | Проверяет инструменты/контракты, не пересобирает все native cores |
| `sync_version.py` | PASS: dev/planned 0.8.2, released 0.8.1 | Согласованность версии |
| `native-libs/provenance.py --check` | **FAIL: STALE NATIVE CORES** | Digest исходников отличается от recorded native digest |
| `release_certification.py --quiet` | **FAIL: manifest missing** | Нет `release/certification/0.8.2.json` |

**B00-01:** native digest recorded `85f2f17ed9f58e7ad8d0368b936542f2391961bf0a739c7985a93208d6a1cb80`,
actual `3deb3da9d8306e0eaf4fd3d3505a7ad8f4e822b7bd502e8e748f632a852baa52`.
Не выдавать packaged-библиотеки за проверку текущего Rust. Закрывается в 22/34
пересборкой и проверкой происхождения; простое обновление записи digest не подходит.

**B00-02:** отсутствие manifest не доказывает поломку runtime, но означает отсутствие
полного подтверждения готовности 0.8.2 к выпуску. Закрывается в 34 реальными evidence
из матрицы; создавать формальный файл с `passed` без прогонов нельзя.

## 5. Реестр модулей: что уже аудировали и что повторяем

Ниже полный восстановленный перечень в порядке нового прохода. H-коды ссылаются
на раздел 1; это история review/test, не текущий PASS. Кросс-системные работы 35–37
также применяются к каждому из разделов 01–34.

| ID | Модуль | Предыдущие проверки | Новый проход |
|---|---|---|---|
| 01 | Серверный INI и схема | H01, H04, H08–H10 | PASS |
| 02 | Клиентские парсеры и qeli:// | H04, H06, H08–H10 | PASS |
| 03 | Панель: UI и состояние | H02, H09–H11 | PASS |
| 04 | Web auth и защита API | H01–H03, H08–H09 | PASS |
| 05 | Транзакции конфигурации и restart | H08–H10 | PASS |
| 06 | Пользователи, группы и выдача доступа | H01, H04, H09–H10 | PASS |
| 07 | Backup, restore и history | H03–H04, H08, H10 | PASS |
| 08 | Криптография, identity и ключи | H01, H04, H08 | DONE |
| 09 | Handshake и pre-auth TCP/UDP | H01, H04, H08 | DONE |
| 10 | PacketCodec, replay и control framing | H01, H04, H08 | DONE |
| 11 | REALITY, TLS 1.3 и HTTP/2 | H07–H08 | DONE |
| 12 | Транспорты и wire-маскировка | H02, H07–H08 | PASS |
| 13 | Recordizer, padding и shaping | H02, H07–H08 | PASS |
| 14 | Supervisor, workers и профили | H02–H03, H08 | PASS |
| 15 | Сессии, IP-пулы и лимиты | H01, H03–H04, H08 | PASS |
| 16 | ACL, push routes и site-to-site | H03–H04, H06 | PASS |
| 17 | IPv4 NAT, forwarding и sysctl | H02, H04, H08 | PASS |
| 18 | IPv6 off/manual/route/nat66 и NDP | H06, H11 | PASS |
| 19 | DNS сервера и клиентов | H01–H02, H05–H06 | PASS |
| 20 | DHCP и lease lifecycle | H02, H05 | PASS |
| 21 | TUN/TAP, IP, MTU/PMTU и фрагментация | H06, H08 | IN_PROGRESS |
| 22 | Transport core, FFI/JNI и память | H06, H08 | IN_PROGRESS |
| 23 | Роуминг, resume и CONTROL_V2 | H06, H08 | IN_PROGRESS |
| 24 | Multipath, bonding и общий бюджет | H04, H06, H08 | DONE/PASS |
| 25 | Linux CLI и восстановление сети | H01, H04, H08 | DONE / PASS |
| 26 | Общий C# и managed/native граница | H04, H06, H08 | TODO |
| 27 | Windows: GUI, служба и драйверы | H01, H04, H08 | IN_PROGRESS |
| 28 | macOS: daemon, utun, pf и Network Extension | H04, H08 | TODO |
| 29 | Android: VpnService, JNI и lifecycle | H04, H06, H08 | TODO |
| 30 | iOS: PacketTunnel, Swift и MDM | H04, H06, H08 | TODO |
| 31 | OpenWrt, LuCI и Keenetic | H04, H06, H08 | TODO |
| 32 | Метрики, usage, логи и уведомления | H02–H03, H08, H10 | IN_PROGRESS |
| 33 | Установка, обновление, файловые права и hooks | H01, H04, H08 | IN_PROGRESS |
| 34 | CI, зависимости, native provenance и релиз | H04, H06, H08 | IN_PROGRESS |
| 35 | Fuzzing, concurrency, DoS и soak | H04, H06, H08 | TODO |
| 36 | Бенчмарки и методика измерения | H07 | TODO |
| 37 | Документация, тестовая обвязка и мёртвый код | H06, H08–H09, H11 | TODO |

## 6. Сценарии по каждому разделу

Порядок — 01 → 37. Если проверка требует другого стенда, фиксируется BLOCKED только
для этой части; независимый анализ следующего раздела продолжается, а блокер остаётся
в очереди. Итоговый PASS раздела требует всех обязательных уровней из раздела 2.

### 01. Серверный INI и схема

**Код:** `qeli/src/config`.

Каждый ключ: parse → validate → runtime → serialize; defaults, диапазоны, дубли секций/ключей, unknown keys, кавычки/TAB/Unicode. Неверный ввод отклоняется до записи. INI — единственный формат конфигов; JSON остаётся служебным API.

**Имеющаяся обвязка/fixtures:** `qeli/tests/config_examples.rs`.

- [x] Review и мёртвый код: строгие entry points, serde/function-pointer/OS consumers, документированные неактивные поля; 3 октября.
- [x] Штатные, граничные и негативные сценарии парсера: 12 новых регрессий и существующий набор.
- [x] Отказы и конкуренция: D07/Q25-F209, 201 unit, 4 privileged и 44 runtime checks.
- [x] Linux-интеграция: check-config/startup/SIGHUP/HTTP save/Quick Start, Q25-F209; итоговый D15-кандидат.
- [x] Исправления первого прохода, повторная проверка и evidence (Q01-F001–F007).

**Статус: PASS.**

**Первый проход, 2026-09-22:** [отчёт Q01](../reports/AUDIT-Q01-SERVER-INI.md).
Исправлены 6 дефектов обработки INI и пробел покрытия fixture. 651 переносимый Rust-тест
и 25 JS-групп прошли; Linux all-targets check прошёл. Контроль fixture: 163 имени ключей
и 3 динамических семейства. Проверена изоляция 32 параллельных разборов.

**Сверка 3 октября:** trace полей закрыт матрицами [глобальных ключей](../reports/AUDIT-Q25-SERVER-GLOBAL-FIELDS.md),
[основы профиля](../reports/AUDIT-Q25-SERVER-PROFILE-FOUNDATION.md) и [obf](../reports/AUDIT-Q25-SERVER-PROFILE-OBF.md).
D07/Q25-F209 проверил отказы, конкуренцию и Linux save/reload/import; D15 подтвердил
одинаковые SHA всех 288 Rust-файлов и проверил итоговый release. Старое ограничение
«нет Linux» снято. [Evidence применимости](../../../release/certification/evidence/q01-reconciliation-20261003.json)
сохраняет первоначальный debug SHA и границы, не приписывает новый запуск этим 44 checks.
**Завершение 3 октября:** адресный review закрыт без новых подтверждённых дефектов; fixture check повторён. Все пять критериев раздела 01 закрыты. PASS относится к серверной схеме и путям конфигурации, а не к сетевым реализациям следующих разделов.

### 02. Клиентские парсеры и qeli://

**Код:** `qeli/src/config/client.rs`, `qeli/src/config/share.rs`, `conformance`.

Сверить текущий контракт 81 ключа в Rust/C#/Kotlin/Swift; INI ↔ формы ↔ URI, сохранение чужих полей и секретов. Проверить malformed pin/port/IPv6/MTU и запрет незаметного перехода в TOFU.

**Имеющаяся обвязка/fixtures:** `scripts/test_native_config_keys.py`.

- [x] Review и мёртвый код: INI/editor/URI callers, проекции, C ABI/JNI; 3 октября.
- [x] Штатные, граничные и негативные сценарии: 81 ключ / 84 поля, общий URI/INI корпус, прежние регрессии и свежий DLL audit.
- [x] Отказы и конкуренция: лимиты, сохранение ошибок, 1000 черновиков, 128 параллельных сценариев; D08 storage coordination.
- [x] Доступная интеграция: действующий C ABI, D08 C#/JVM/Android emulator, D15 native A/B; Apple/physical SKIP по решению пользователя.
- [x] Q02-F001–F019, D08/D15 и сверка неизменённых входов; evidence с исходными границами.

**Статус: PASS в согласованном объёме; Apple/physical SKIP.**

**Проход URI, 2026-09-22:** [отчёт Q02](../reports/AUDIT-Q02-CLIENT-PARSERS.md).
Закрыты Q02-F001–F006: неоднозначные query-параметры, scalar/UTF-8/defaults и пропуск
JVM-перепроверки корпуса. 651 Rust-тест, 438 C# checks и 137 JVM-тестов прошли.
Общий корпус: 21 valid + 29 reject; контракт 81 имени ключей сохраняется.

**Текущее состояние, 3 октября:** адресный INI/редакторский review завершён без новых подтверждённых дефектов. D08 уже проверил доступные модели/хранилища и Android-эмулятор; D15 обновил release native A/B и provenance. Apple и недоступные физические стенды исключены по решению пользователя, не получили runtime PASS. [Сверка](../../../release/certification/evidence/q02-reconciliation-20261003.json): 81 ключ, 84 поля редактора, 164 adapter + 288 Rust SHA совпали; шесть статических тестов и генератор проекций прошли. Старые runtime результаты не объявляются новыми.
**Архитектурное предложение пользователя:** [единый конфигурационный модуль](CLIENT-CONFIG-CORE.md)
в существующем Rust core реализован в исходниках (ABI 1.16). Местные парсеры удалены; проекции/defaults генерируются из Rust. Объединены политики маршрутов/reconnect/версий и парсер route_file. Release A/B закрыты D15; Apple runtime исключён пользователем.

**Продолжение 22 сентября — границы конфигурации:** в общем ядре исправлены Q02-F007–F014 — восемь
воспроизведённых сценариев INI/URI: потеря символов и ошибок DNS, недопустимые имена
полей, обход проверки через BOM, маскирование секретов и неверная секция `logging.*`.
Регрессии проверяют сохранение через модели клиентов; подробности и результаты —
в [отчёте общего конфигурационного модуля](CLIENT-CONFIG-CORE.md#аудит-границ-конфигурации--22-сентября-2026).
Это не закрывает весь раздел: Linux E2E и проверки на целевых устройствах остаются открыты.

**Параметры перед runtime, 2026-09-22:** закрыты Q02-F015–F019 — неверный нулевой PIN,
некорректный host, исправление порта без его изменения, старый валидатор панели и ошибки автозаписи dev.
Регрессии и сохранение положительных случаев описаны в [реестре Q02](../reports/AUDIT-Q02-CLIENT-PARSERS.md).

**Продолжение runtime-аудита, 2026-09-22:** в том же плане зафиксированы общий бюджет/задержка
повторов, монотонное время установленной сессии, исправления конечных лимитов и возврата сети,
прерывание Linux-backoff по сигналу. Регрессии Rust/C ABI/JNI и Linux cross-Clippy пройдены.
Проверки реальных устройств/смены сети, Apple runtime и релизных библиотек этим не закрыты.

**Завершение 3 октября:** свежий audit упакованной DLL (`653522e6…`), восемь групп:
84 явных значения полей в runtime-документе, 21 valid + 29 reject URI, 15 INI boundary,
1000 seeded черновиков, сохранение ошибок при unrelated edit, лимиты и 128 параллельных
сценариев изоляции/маскирования. C#/JVM/Android проверки D08 переиспользованы только после
сверки 164 adapter + 288 Rust SHA; это не новые платформенные прогоны. [Результат](../reports/AUDIT-Q02-CLIENT-PARSERS.md#завершение-раздела--3-октября-2026).
PASS относится к конфигурационному контракту; эффекты OS-параметров и настоящая сеть
проверяются в соответствующих платформенных разделах. Apple build/runtime не заявлены.

### 03. Панель: UI и состояние

**Код:** `qeli/src/web/templates`, `qeli/src/web/assets`, `qeli/src/web/pages`.

Загрузка/error/retry, dirty-state, поздние ответы, concurrent edits, Form/INI, удаление полей, маски секретов, даты и квоты. Настоящий браузер: все страницы, RU/EN, клавиатура, мобильный экран; ошибки не превращаются в сохранение defaults.

**Имеющаяся обвязка/fixtures:** `scripts/check_panel.py`, `scripts/test_panel_editors.cjs`.

- [x] Review и мёртвый код: все 11 шаблонов / 10 page wrappers; общий Form/INI lifecycle, Rust defaults/Quick Start.
- [x] Штатные, граничные и негативные сценарии: 116 групп реальных JS-компонентов; секреты, даты, квоты, ревизии и Form/INI.
- [x] Отказы и конкуренция: error/retry всех страниц, старые ответы, владельцы модальных окон и черновиков, повторные отправки, destroy и отмена.
- [x] Доступная интеграция: все страницы в Edge RU/EN, desktop/mobile и клавиатура; общий фокус и настоящий beforeunload. API fixtures подтверждают UI, а не backend protection/persistence.
- [x] Q03-F001–F015 исправлены и проверены; baseline-воспроизведения, raw logs/captures, свежая release-матрица и soak того же артефакта.

**Статус: PASS в области UI/state панели.**

**Завершение 3 октября:** [Подробный отчёт](../reports/AUDIT-Q03-PANEL-STATE.md) и [итоговое evidence](../../../release/certification/evidence/q03-config-20261003.json). Итоговый пакет: 26 новых JS-групп (всего 116), четыре Config Edge-сценария, черновик/ревизия, одна запись, владельцы identity/hash/history/remove, Cancel/Tab/Shift+Tab/Escape/возврат фокуса и переход с правками. Свежий release: 18 изолированных сценариев / 327 checks, aggregate leak и 100 TCP + 100 QUIC / 33 checks PASS. Неизменные Rust/native/budget результаты явно используются как reuse. Пользовательский live-users WIP сохранён отдельно; physical qualification и новые benchmarks не заявляются. Backend auth, транзакции и восстановление остаются обязательствами Q04/Q05/Q07.

### 04. Web auth и защита API

**Код:** `qeli/src/web/auth.rs`, `qeli/src/web/mod.rs`, `qeli/src/web/api`.

Инвентаризировать routes/guards, Basic/cookie/TOTP, logout/expiry, CSRF, reverse proxy, base_path, allowed_ips. Argon2 budget/rate limit под конкуренцией. Запрос без прав не раскрывает секреты и не имеет побочных эффектов.

**Имеющаяся обвязка/fixtures:** `scripts/check_panel.py`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: PASS.**

**3 октября, завершение:** все пять критериев Q04 закрыты в области авторизации и границ API. 2261 Linux units, 116 JS-групп, 293 реальных HTTP checks, pinned full/minimal Clippy PASS. Release-матрица 18/327 и soak 100 TCP + 100 QUIC/33 PASS; HTTP/matrix повторно используются только по побайтному совпадению release SHA. Свежие desktop/Android native A/B и provenance PASS. Web TOTP отсутствует; положительные транзакции и restore остаются Q05/Q07. [Report](../reports/AUDIT-Q04-WEB-AUTH.md), [evidence](../../../release/certification/evidence/q04-web-auth-20261003.json).

### 05. Транзакции конфигурации и restart

**Код:** `qeli/src/web/api/config.rs`, `qeli/src/web/api/control.rs`, `qeli/src/server/preflight.rs`, `qeli/src/util.rs`.

Общий validator/preflight для Form/INI/API/history/Quick Start/worker/full restart. Stale revision, concurrent writers, ENOSPC/EACCES и crash между snapshot/rename/restart. Failed preflight не останавливает рабочий сервис и не публикует плохой конфиг.

**Имеющаяся обвязка/fixtures:** `scripts/test_web_reload.py`, `scripts/test_panel_editors.cjs`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: PASS.**

**3 октября, завершение:** 6 пакетов / 352 реальных HTTP/systemd checks PASS: Form/INI/history, 8 concurrent writers, все 10 Quick Start modes, live password/allowlist, worker replacement, detached restart failures, ENOSPC/read-only/EACCES, SIGKILL до/после rename и fsync uncertainty; настоящий full restart собственного transient unit. Q05-F009: старый live-service тест заменён изолированным launcher. Unchanged Linux 2261 / Clippy / native / matrix / soak явно reused; все 322 compilation inputs совпадают. Power loss и несогласованные внешние root writes не сертифицированы; backup/restore остаётся Q07. [Report](../reports/AUDIT-Q05-HTTP-TRANSACTIONS.md), [evidence](../../../release/certification/evidence/q05-transactions-20261003.json).

### 06. Пользователи, группы и выдача доступа

**Код:** `qeli/src/config/users.rs`, `qeli/src/web/api/users.rs`, `qeli/src/web/api/share.rs`, `qeli/src/web/api/identity.rs`.

Inline + users_file, duplicates/precedence, missing group, неверные типы versus снятие ограничений, static addresses, quota/expiry. Ошибка identity не меняет пароль при выдаче ссылки. Revoke применяется к уже открытым TCP/UDP-сессиям.

**Имеющаяся обвязка/fixtures:** `scripts/test_user_reload.py`, `scripts/test_l3_user_limits.py`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: PASS.**

**3 октября, первый пакет:** исправлены пять подтверждённых проблем API, inline override, routes, live revoke и bandwidth writers. 119 API + 57 TCP/UDP checks PASS; свежие Linux units/lint и 293/75 HTTP regressions PASS. Q06 остаётся открытым для filesystem/concurrency и дополнительных политик. [Отчёт](../reports/AUDIT-Q06-USERS-ACCESS.md).

**3 октября, второй пакет:** Q06-F006 устраняет стартовые inline users/groups в контрольных командах после SIGHUP. 23 новых storage/control checks, повторные 119 API + 57 live, 2264 Linux units и свежая release/native квалификация PASS. Конкуренция и read-only/rename/corrupt INI проверены; crash/lock/final-fsync, ACL и устройства ещё открыты. [Отчёт](../reports/AUDIT-Q06-USERS-ACCESS.md#второй-пакет-ini-хранилище-и-inline-auth-после-sighup).

**3 октября, третий пакет:** исправлены live ACL/group, делегированные источники,
уменьшение лимита устройств, неограниченное ожидание lock и ложный отказ после
публикации INI. 315 checks Q06 (72 storage/durability, 67 policy, 119 API, 57 live)
и 2265 Linux units PASS. Реальные ENOSPC/EACCES, crash до/после rename и все API/control
writers проверены. Опасные legacy drivers заменены изолированными пакетами.
Файловые отказы и конкурентные писатели закрыты; Q06 остаётся IN_PROGRESS для
измерения bandwidth и оставшихся сценариев admission/выдачи доступа.
[Отчёт](../reports/AUDIT-Q06-USERS-ACCESS.md#третий-пакет-live-права-и-отказы-публикации-ini).


**3 октября, завершение:** Q06-F012–F014 исправлены; общий TCP/UDP admission, терминальная замена сессий, effective bandwidth/legacy burst и recovery share-reset. 387 Q06 checks, 2265 Linux units / 60 ignored, 118 JS-групп, свежие matrix 18/327 и soak 100 TCP + 100 QUIC/33 PASS. Native A/B побайтно совпадает; .11 сохранён, .10 SDK PASS с явно сохранённым ограничением firewall snapshots. Physical qualification не заявляется. [Итоговый отчёт](../reports/AUDIT-Q06-USERS-ACCESS.md), [evidence](../../../release/certification/evidence/q06-users-access-complete-20261003.json).

### 07. Backup, restore и history

**Код:** `qeli/src/web/api/backup.rs`, `qeli/src/web/api/backup_listing.rs`, `qeli/src/web/api/config.rs` (history), `qeli/src/web/tls.rs`.

Fresh restore с custom paths, inline+external users, identity и panel-secret. Tar bombs, traversal, links, missing files, overlay/exact, совместимость staged-файлов, concurrent restore. Snapshots не архивируют себя; interrupted publish проверяется восстановлением.

**Имеющаяся обвязка/fixtures:** `scripts/audit_web_auth_lab.py --audit q07 --scenario archives --fixture scripts/audit_web_transactions.py`; общий Q05 `basic` для history/config regression.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: PASS в согласованном доступном Linux/runtime scope.**


**История, 3 октября, первый пакет:** HTTP-воспроизведение выявило отказ exact при вложенных lock-файлах, отсутствие проверки identity/TLS и сохранение чужого UID из tar. Исправления и текущая квалификация описаны в [отчёте Q07](../reports/AUDIT-Q07-BACKUP-RESTORE.md). Полный Q07 остаётся открытым: crash/partial publication и recovery, файловые отказы, cross-process users/identity writers, mixed users и panel-secret, операционные файлы/rotation и дополнительные INI trust boundaries (исторический список до второго пакета).

**История, 3 октября, второй пакет:** Q07-F005–F013: strict exact, INI command trust, operational snapshots/rotation, old/new users/identity FileLocks, absent-directory lock inode, partial-publication metadata и отказ вместо ложного exact success. 17 baseline checks FAIL; текущие 176 HTTP/system checks PASS. SIGKILL до/после первого rename и manual tar recovery проверены. Остаются mixed inline/external users, panel-secret и прямые prepare ENOSPC/read-only/HTTP cancellation для архивного restore. Общий Q07 ещё IN_PROGRESS.

**3 октября, закрытие Q07:** Q07-F014–F015 исправлены: extraction ENOSPC → HTTP 500; только реальный FileLock timeout → 409. Mixed users/groups, real restored VPN clients, same/new-host panel-secret, legacy migration, real archive prepare ENOSPC/read-only и HTTP cancellation проверены. Финальные 226 HTTP/system checks, 2266 units, matrix 18/327, soak 33 и native A/B PASS. Review всех семи слоёв завершён; приватный staging при read-only и per-file publication описаны как принятые ограничения. [Финальный отчёт](../reports/AUDIT-Q07-BACKUP-RESTORE.md). Следующий раздел: Q08.

### 08. Криптография, identity и ключи

**Код:** `qeli/src/crypto`, `qeli/src/server/reality.rs`, `qeli/src/web/api/identity.rs`.

X25519/ML-KEM/HKDF/AEAD KAT и negative vectors; static binding, proof до credentials, pin/TOFU, RNG, nonce exhaustion, rotation и zeroization. Owner/mode/link/atomic-write ключей. Unit tests не заменяют независимый криптоаудит.

**Имеющаяся обвязка/fixtures:** `conformance/hkdf.json`, `conformance/prp-nonce.json`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE.**

**Первый пакет Q08:** Q08-F001–F003, shared bounded key reads, serialized legacy migration, low-order proof refusal. Прежний release воспроизводит шесть файловых отказов; первый пакет и его квалификация сохранены в [отчёте](../reports/AUDIT-Q08-CRYPTO-KEYS.md).


**3 октября, завершение Q08:** Q08-F004–F007, независимые NIST/RFC/AEAD/HKDF vectors, полный review семи направлений, 31 key/rotation + 25 restore/state checks с настоящими pinned-клиентами, 2279 units, matrix18/327, soak33 и native A/B PASS. Все обязательные проверки fixes закрыты. Принятые ограничения и корректная conditional REALITY TLS PQ-защита описаны в [финальном отчёте](../reports/AUDIT-Q08-CRYPTO-KEYS.md). Далее Q09.

### 09. Handshake и pre-auth TCP/UDP

**Код:** `qeli/src/server/handler.rs`, `qeli/src/server/udp_handler.rs`, `qeli/src/protocol/capabilities.rs`, `qeli/src/client/mod.rs`.

Truncation/replay/reorder/slow peer и неверный PQ/proof/password. Permits до spawn, pending caps, anti-amplification, tarpit, deadlines/cancel. Один login не блокирует UDP recv-loop; каждый отказ освобождает ресурсы, downgrade только по контракту.

**Имеющаяся обвязка/fixtures:** `qeli/fuzz/fuzz_targets/clienthello.rs`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE.**

**Серверный H2 и pre-auth, 23 сентября 2026:**
[Q14-F022/F023](../reports/AUDIT-Q14-H2-TASKS.md): профиль ждёт вложенные H2-задачи перед
teardown; flush отказа сохраняет pre-auth slot до освобождения I/O. 13 новых регрессий,
969 Rust tests PASS. H2/ProfileTasks/semaphore проверены на host, production Linux только
кросс-компилирован. Остальные сценарии раздела и live Linux E2E остаются открытыми.

**3 октября, UDP AUTH/PMTU:** [Q09-F001/F002](../reports/AUDIT-Q09-UDP-AUTH.md) исправлены и проверены: handshake reservation/cancel/deadline, PMTU только после AuthOK без revoked. 2283 units, 16 old/new UDP/QUIC + 35 admission checks, fresh matrix/soak/native PASS; общий Q09 остаётся IN_PROGRESS.

**3 октября, TCP/parser:** [Q09-F003–F005](../reports/AUDIT-Q09-TCP-PARSER.md): исходный AUTH-дедлайн, откат AUTH OK, строгий полный ClientHello и JOIN. 2290 units, 8 TCP checks с реальным baseline/fixed и насыщением 256 слотов, bounded ASan/libFuzzer, fresh matrix/soak/native PASS. Остались UDP anti-amplification/replay/reorder и негативные auth/capabilities контракты; общий Q09 IN_PROGRESS.

**3 октября, UDP contracts:** [Q09-F006–F009](../reports/AUDIT-Q09-UDP-CONTRACTS.md): publication/revocation, direction/bounds, reaper revalidation и admission/AuthOK deadline+rollback. 2294 units, 74 live UDP/QUIC +16 PMTU +35 admission, fresh matrix/soak/native PASS. Исходные failures и ограничения лабы сохранены. Остаток: final review, forged client-proof/capabilities/contention и уточнение первого TCP terminal-loss; Q09 IN_PROGRESS.

**3 октября, завершение Q09:** [Q09-F010/F011 и итоговый review](../reports/AUDIT-Q09-FINAL.md): KICK сохраняется при EOF, pipeline drain и ошибке platform delivery. 2301 units;8 live baseline/fixed +66 decrypted proof/capabilities/concurrent +35 admission checks; fresh18/327 matrix,100 TCP+100 QUIC/33 soak и четыре native A/B PASS. Все обязательные проверки исправлений Q09 закрыты; ограничения evidence явно сохранены. Следующий раздел — Q10.

### 10. PacketCodec, replay и control framing

**Код:** `qeli/src/protocol/packet.rs`, `qeli/src/protocol/ctrl.rs`, `qeli/src/protocol/control_v2.rs`.

Lengths 0/min/max/overflow, AEAD tags, sequence около 2^63/2^64, replay-window, unknown types/generation. Malformed пакет не вызывает panic/abort/unbounded allocation; после отказа корректный пакет обрабатывается.

**Имеющаяся обвязка/fixtures:** `conformance/packet-decode.json`, `conformance/replay-window.json`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE.**

**3 октября, Q10 завершён:** [PacketCodec/replay/CONTROL_V2](../reports/AUDIT-Q10-CODEC-CONTROL.md): Q10-F001–F003,2307 units,два bounded ASan fuzz runs,свежая matrix/terminal/soak/native qualification PASS. Общий план:10/37 DONE/PASS (27,0%). Следующий раздел — Q11.

### 11. REALITY, TLS 1.3 и HTTP/2

**Код:** `qeli/src/protocol/realtls`, `qeli/src/protocol/h2_carrier.rs`, `qeli/src/protocol/h2_carrier`.

Transcript/replay/decoy, TLS key budget. H2 zero/small window, SETTINGS/WINDOW_UPDATE/GOAWAY/RST, partial I/O, backpressure. Stop/timeout освобождает task/socket/permit. PCAP/active probing отдельно от работоспособности туннеля.

**Имеющаяся обвязка/fixtures:** `qeli/src/protocol/h2_carrier/hardening_tests.rs`, `scripts/roaming_netns_e2e.sh`, `scripts/audit_realtls_wire.py`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE.**

**Серверный H2 и pre-auth, 23 сентября 2026:**
[Q14-F022/F023](../reports/AUDIT-Q14-H2-TASKS.md): профиль ждёт вложенные H2-задачи перед
teardown; flush отказа сохраняет pre-auth slot до освобождения I/O. 13 новых регрессий,
969 Rust tests PASS. H2/ProfileTasks/semaphore проверены на host, production Linux только
кросс-компилирован. Остальные сценарии раздела и live Linux E2E остаются открытыми.

**3 октября, завершение Q11:** [REALITY/TLS/H2](../reports/AUDIT-Q11-REALITY-TLS-H2.md): пять исправлений общего TLS,2317 Linux units,73 REALITY-TLS/H2 checks,3 PCAP/6 wire-probe результатов,два bounded ASan fuzz,свежие matrix/soak/четыре native A/B PASS. Общий план:11/37 DONE/PASS (29,7%). Следующий раздел — Q12.

### 12. Транспорты и wire-маскировка

**4 октября, Q12 DONE/PASS:** Close/control и wire-матрица завершены; 8 baseline FAIL,17 новых тестов,2352 Linux PASS,13 fresh wire cases,64 probes,два frame/QUIC ASan прогона,свежие matrix/soak/четыре native A/B PASS. [Evidence и границы](../reports/AUDIT-Q12-TRANSPORTS.md). Общий план **12/37 (32,4%)**; далее Q13.

**4 октября, WS writer batch PASS:** [Q12](../reports/AUDIT-Q12-TRANSPORTS.md): четыре исправления общего writer/read,5 baseline FAIL,7 new tests,2324 Linux PASS,10prior +3fresh wire-mode cases,свежие matrix/soak/native A/B PASS. На момент того пакета HTTP/inbound frame/fuzz оставались впереди; тогда Q12 IN_PROGRESS,план11/37 (29,7%).

**Код:** `qeli/src/protocol/tls.rs`, `qeli/src/protocol/obfs.rs`, `qeli/src/protocol/quic.rs`, `qeli/src/transport`.

Получить все допустимые сочетания из runtime/Quick Start: plain/fake-tls/reality/reality-tls/WS/obfs/UDP-QUIC/AWG. WS masking/control caps, junk counters, fallback и запрет несовместимых комбинаций. Protocol compliance и DPI detection не смешивать с goodput.

**Имеющаяся обвязка/fixtures:** `conformance/quic.json`, `qeli/fuzz/fuzz_targets/websocket_head.rs`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE/PASS.**

### 13. Recordizer, padding и shaping

**4 октября, Q13 DONE/PASS:** удалены две выключенные UDP stealth-ветви, сохранена действующая политика TCP. Прошли 2365 Linux-тестов, 7 сетевых сценариев, матрица 18/18, 33 проверки длительного прогона и четыре независимые сборки библиотек A/B. Общий план **13/37 (35,1%)**, осталось 24 раздела; далее Q14. [Итог и границы](../reports/AUDIT-Q13-MORPHOLOGY.md).


**4 октября, morphology batch PASS:** ещё четыре исправления padding/normalization/mux,2365 Linux PASS,6 combined TCP/UDP cases,свежие matrix/soak/native A/B. [Evidence и оставшиеся две UDP ветви](../reports/AUDIT-Q13-MORPHOLOGY.md).


**4 октября, shaping batch PASS:** [пять исправлений и замеры](../reports/AUDIT-Q13-MORPHOLOGY.md):5 baseline FAIL,7 новых тестов,2359 Linux PASS,10 network cases/102 assertions,recordizer campaign,свежие matrix/soak/native A/B. Review recordizer/padding/normalization продолжается;общий итог остаётся12/37 (32,4%).


**Код:** `qeli/src/protocol/recordizer.rs`, `qeli/src/protocol/shaper.rs`, `qeli/src/protocol/obfuscate.rs`.

Off/prefer/required и legacy peer; batch/reassembly caps, flush deadlines, cancellation и общий budget. Junk/heartbeat не вытесняют payload. Сравнить on/off на одинаковом workload; bounded memory, jitter и периодические сигналы в PCAP.

**Имеющаяся обвязка/fixtures:** `scripts/validate_shaping.py`, `scripts/bench_stealth.py`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE/PASS.**

### 14. Supervisor, workers и профили

**4 октября, Q14 DONE/PASS:** исправлен Q14-F039 — supervisor владеет фоновыми задачами и останавливает HTTP/HTTPS-панель. 2368 Linux-тестов, 38 process checks, 4 panel stop/cancel cases, 5 privileged-прогонов, stop во время backoff, матрица 18/18 и native A/B PASS. [Итог и границы](../reports/AUDIT-Q14-CURRENT-LIFECYCLE.md).


**Предыдущий пакет 4 октября, lifecycle PASS:** 8/8 сценариев worker, 80 reload, 22 проверки восстановления и 14 проверок нескольких профилей на текущем release. Состояние лабы и рабочий сервис сохранены. [Разбор и остаток Q14](../reports/AUDIT-Q14-CURRENT-LIFECYCLE.md). Q14 IN_PROGRESS.

**Код:** `qeli/src/server/mod.rs`, `qeli/src/server/tasks.rs`, `qeli/src/server/supervisor.rs`, `qeli/src/server/control.rs`, `qeli/src/server/control_io.rs`, `qeli/src/server/control_socket.rs`, `qeli/src/main.rs`, `qeli/src/hooks.rs`, `qeli/src/hooks/process.rs`.

Start/stop/reload/crash/respawn, занятый bind/TUN, удаление/rename профиля, hook failure и умерший control client. Lock order, backoff, watchdog и tasks. Cleanup идемпотентен, ошибка одного профиля не затрагивает соседний.

**Имеющаяся обвязка/fixtures:** `scripts/test_web_reload.py`, `scripts/test_tun_reclaim.py`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE/PASS.**

**Владение задачами, 23 сентября 2026:**
[проход Q14/Q19](../reports/AUDIT-Q14-Q19-LIFECYCLE.md) исправляет Q14-F001–F002:
ожидание служб после ранней ошибки запуска и барьер конкурентного/отменённого
shutdown. 7 task-ownership тестов, включая гонку 1024 ресурсов; DNS-слушатели
проверены через loopback. Linux E2E TUN/firewall, forced wrapper cancellation,
watch/control, hooks и restart/reload ещё открыты.

**Supervisor и управляющие события, 23 сентября 2026:**
[продолжение Q14](../reports/AUDIT-Q14-SUPERVISOR.md) исправляет Q14-F003–F007:
stop во время ошибок spawn, владение Child/PID, 60-секундный grace deadline,
очередь Restart/Reload и раннюю установку обработчиков сигналов. 13 поведенческих
тестов и дочерний fixture; 812 Rust-тестов суммарно — PASS. Проверены реальные
изолированные host-процессы, не Linux worker с TUN. Control socket, hooks,
Unix-сигналы и rollback на Linux остаются открытыми.

**Control socket и hooks, 23 сентября 2026:**
[проход Q14-F008–F013](../reports/AUDIT-Q14-CONTROL.md): владение Unix-сокетом,
безопасные права runtime-каталога, границы сообщений, deadlines и drain handlers
до teardown профилей, post_down только для готового поколения. 819 host Rust tests
PASS; 12 новых Unix tests только скомпилированы. Linux runtime/systemd/hooks и
forced cancellation остаются открытыми; далее — hook processes/output и startup rollback.

**Процессы hooks, 23 сентября 2026:**
[Q14-F014–F015](../reports/AUDIT-Q14-HOOKS.md): общий server/client runner удерживает
по 8 KiB stdout/stderr и завершает Linux process group при timeout/cancellation,
сохраняя штатные фоновые службы с перенаправленным выводом. 828 host Rust tests PASS;
4 новых Linux group tests только скомпилированы. Следующие участки: startup rollback,
фоновые worker services и связь trusted config с parsed contents. Linux E2E ещё открыт.

**Службы worker и учёт трафика, 23 сентября 2026:**
[Q14-F016–F017 / Q15-F001](../reports/AUDIT-Q14-Q15-WORKER-USAGE.md): владение и контроль
периодических задач, их завершение до очистки профилей, writable accounting только после
захвата права worker, финальное сохранение на обоих путях остановки. Короткие сессии и
последние байты учитываются после удаления из реестра. 848 host Rust tests PASS;
Linux только cross-check. Уведомления, forced outer cancellation и Linux E2E ещё открыты.

**Владение уведомлениями, 23 сентября 2026:**
[Q14-F018 / Q32-F001](../reports/AUDIT-Q14-Q32-NOTIFICATIONS.md): до 128 принятых отправок,
8 активных запросов на процесс, общий лимит проб панели, ограниченные payloads и drain
до 10 секунд после завершения производителей. Detached-обёртки уведомлений удалены.
864 host Rust tests PASS; Linux только all-targets cross-check. Владение panel/metrics/
autostart supervisor, доверие конфигу и Linux E2E ещё открыты.

**Доверие прочитанному конфигу, 23 сентября 2026:**
[Q14-F019 / Q33-F001](../reports/AUDIT-Q14-Q33-CONFIG-TRUST.md): владелец/права и данные
для парсера получаются из одного дескриптора; исходное разрешение не меняется при
повторах профиля и не перепроверяет путь. Очистка готового поколения сохраняет команду
и окружение после удаления/замены конфига. 874 host Rust tests PASS; четыре новых Unix/
Linux-теста только cross-checked. Лимиты password_command, владение startup-задачами,
installer/update/restore и Linux runtime integration ещё открыты.

**Поставщик пароля и изоляция features, 23 сентября 2026:**
[Q25-F001 / Q33-F002 / Q14-F020 / Q34-F001](../reports/AUDIT-Q25-CREDENTIAL-COMMANDS.md):
асинхронный password_command, deadline 30 секунд, полный stdout до 16 KiB, отброшенный
stderr и ошибки без секретов. Ранний SIGINT/SIGTERM отменяет и собирает поставщика;
watchers/sampler клиента имеют владельца. Исправлен server-only TUN gate, обе изолированные
features проверяются в CI. 883 host Rust tests PASS; четыре Linux-теста только cross-check.
Server-only check имеет 23 прежних transport dead-code warnings. Лимиты password_file,
финальный drain клиента и Linux runtime/release checks ещё открыты.

**Файловый пароль и финальный статус, 23 сентября 2026:**
[Q25-F002 / Q14-F021](../reports/AUDIT-Q25-PASSWORD-FILES.md): общий zeroizing-буфер 16 KiB
для файла/команды, одна управляемая blocking-задача чтения обычного файла, поддержка symlink,
отказ FIFO и ожидание активного I/O при штатном stop/deadline. Final пишется после join
watchers/sampler, включая ошибки после инициализации reporter. 895 host Rust tests PASS;
два Unix-теста только cross-check. Неотменяемый I/O может превышать бюджет 30 секунд.
Startup/network rollback, мониторинг фоновых ошибок и Linux E2E ещё открыты.

**Fail-closed очистка сети, 23 сентября 2026:**
[Q25-F003](../reports/AUDIT-Q25-NETWORK-CLEANUP.md): forwarding/NAT cleanup должен
завершиться успешно до снятия включённого kill-switch; ошибка сохраняет защиту и её причину.
899 host Rust tests PASS, включая четыре переносимых fault-injection сценария. Linux
пока только cross-check. Разбор begin_connection записан ниже; live firewall/E2E ещё открыты.

**Ошибки жизненного цикла ядра, 23 сентября 2026:**
[Q25-F004/F005](../reports/AUDIT-Q25-CORE-LIFECYCLE.md): ошибка запуска ядра проходит через
cleanup/post_down; ошибка остановки завершается отказом и сохраняет включённый kill-switch,
при этом очистка forwarding выполняется. Шесть новых host-регрессий, включая реальный отказ
ClientCore при полной очереди. 905 host Rust tests PASS; Linux только cross-check.
Live Linux lifecycle/firewall и полный rollback маршрутов/DNS ещё открыты.


**Передача ошибок очистки TUN/маршрутов/DNS, 23 сентября 2026:**
[Q25-F007–F009](../reports/AUDIT-Q25-TUN-CLEANUP.md): явная очистка и guards отката передают
ошибки в Linux retry loop через общий ограниченный журнал. Ошибка не становится успешной
остановкой по сигналу и не снимает включённый kill-switch. TunnelSetup владеет guard до ACK
ядра; тип terminal kick сохраняется при сопутствующих ошибках. Восемь новых host-тестов
проходят, два Linux adapter-теста только cross-check. 921 host Rust tests PASS. Live Linux
E2E, сроки выполнения команд и полное ожидание задач поколения ещё открыты.

**Серверный H2 и pre-auth, 23 сентября 2026:**
[Q14-F022/F023](../reports/AUDIT-Q14-H2-TASKS.md): профиль ждёт вложенные H2-задачи перед
teardown; flush отказа сохраняет pre-auth slot до освобождения I/O. 13 новых регрессий,
969 Rust tests PASS. H2/ProfileTasks/semaphore проверены на host, production Linux только
кросс-компилирован. Остальные сценарии раздела и live Linux E2E остаются открытыми.

**Системные команды TUN/DNS, 23 сентября 2026:**
[Q25-F016/F017](../reports/AUDIT-Q25-SYSTEM-COMMANDS.md): 15 секунд на команду, полный
вывод с лимитом 16 МиБ на поток, завершение дочернего процесса и сохранение DNS marker
при отказе. Диагностика больше не обещает неподтверждённый rollback. 986 host Rust tests
PASS; два новых Linux process-group теста только cross-check. Маршруты/firewall, live
Linux и общий deadline shutdown остаются открытыми; статус раздела IN_PROGRESS.

**Очистка NAT, 23 сентября 2026:**
[Q14-F024/F025](../reports/AUDIT-Q14-NAT-CLEANUP.md): конечный проход по снимку правил,
проверка после удаления и диагностика ошибок с продолжением остальных правил/цепочек.
13 новых host-тестов, 999 Rust tests PASS; production Linux только cross-check.
Q14-F026 исправлена [следующим проходом](../reports/AUDIT-Q14-Q25-FIREWALL-CHECKS.md).
Q14-F027 (передача ошибок teardown), сроки firewall-команд и live Linux остаются открытыми.

**Общие firewall-проверки, 23 сентября 2026:**
[Q14-F026 / Q25-F018/F019](../reports/AUDIT-Q14-Q25-FIREWALL-CHECKS.md): сервер и Linux
kill-switch используют общий разбор presence/absence/errors; точечная очистка DNS
проверяет границу 1024 и продолжает TCP после отказа UDP. 17 новых host-тестов,
1016 Rust tests PASS; два новых Unix/Linux сценария только cross-check.
Q14-F027, сроки команд и реальные backend/runtime проверки остаются открытыми.

**Владение DNS firewall, 23 сентября 2026:**
[Q14-F028](../reports/AUDIT-Q14-DNS-OWNERSHIP.md): реестр worker сохраняет точные правила
при ошибке Drop/rollback; cleanup и новая установка повторяют очистку. Tokens защищают
новое поколение от старого lease; активные записи не участвуют в точечном retry.
12 новых host-тестов, 1028 Rust tests PASS; три adapter-регрессии отдельно сравнивают
baseline/fix. Q14-F027, persistent journal, deadlines и live Linux остаются открытыми.

**Итог остановки worker, 23 сентября 2026:**
[Q14-F027, частичное исправление](../reports/AUDIT-Q14-OWNED-SHUTDOWN.md): окончательный
retry известных DNS/IPv6 sysctl leases влияет на Result и код выхода worker. Flush
статистики выполняется после ошибки сети; активные DNS leases обнаруживаются без удаления.
14 новых host-тестов, 1042 Rust tests PASS; восемь отдельных process-exit сценариев PASS.
Дополнительный проход передаёт ошибку worker через внешний supervisor при финальной
остановке: nonzero exit и принудительный kill больше не возвращают Ok. Ещё пять
host-тестов, итог этого этапа 1047 Rust tests PASS; три отдельные supervisor-регрессии PASS.
Следующий проход: [задачи профиля и TUN teardown](../reports/AUDIT-Q14-PROFILE-SHUTDOWN.md).
Ошибки shutdown JoinSet, TUN queue timeout/panic и удаления устройства теперь входят в
итог worker; 13 новых host-тестов, матрица этого этапа 1060 Rust tests PASS.
[Q14-F029/F030](../reports/AUDIT-Q14-SYSCTL-RECOVERY.md): исправлены ложный успех
sysctl recovery и потеря существующего owner при неудачном повторном acquire;
1060 Rust tests и 7 отдельных fixture checks PASS.
[Q14-F031](../reports/AUDIT-Q14-IPV6-PARTIAL-ACQUIRE.md): частичный IPv6 acquire теперь
регистрируется до первой попытки; любой отказ вызывает rollback, неуспешный откат
сохраняет scope для итоговой очистки. 11 новых регрессий и перенос одного Linux-only
теста: матрица этого этапа 1072 Rust tests PASS; пять отдельных adapter checks PASS.
[Q14-F032](../reports/AUDIT-Q14-NAT-COMMANDS.md): все пять запусков команд server NAT
переведены на общий runner (15 с; 16 МиБ на каждый поток вывода). Timeout не теряет
DNS ownership; матрица этого этапа 1073 Rust tests и шесть отдельных adapter checks PASS.
Открыты generic NAT outcome, старые поколения/retry backoff, restart policy, persistent
journal, общий срок всей операции, остальные системные команды и live Linux.

**Preflight, 23 сентября 2026:** [Q05-F001](../reports/AUDIT-Q05-PREFLIGHT.md):
четыре host-state probe используют общий runner (15 секунд, по 16 МиБ stdout/stderr).
Fail-open IPv4 и независимый частичный IPv6 snapshot сохранены. 4 новых теста и
20 существующих preflight-тестов включены в host-прогон; 1097 Rust tests и 21
production-adapter сценарий PASS. Linux HTTP/restart/restore, общий срок транзакции
и синхронное ожидание в async handlers остаются открытыми.

[Q25-F050–F051](../reports/AUDIT-Q25-SYSCTL-OWNER-EVIDENCE.md): неизвестные владельцы sysctl сохраняются,
acquire/recovery сообщают ошибку; недостоверное наблюдение sysctl не теряет original
для retry. Восемь baseline-регрессий исправлены, 1362 Rust tests PASS. Namespace
identity журнала, реальный Linux runtime и полный PASS раздела остаются открыты.

[Q25-F052–F053](../reports/AUDIT-Q25-SYSCTL-NAMESPACE.md): sysctl journal v2 разделяет network namespaces,
проверяет PID/time контекст и procfs до prune; непустой v1 текущего boot-id сохраняется
с явной ошибкой миграции. 24 новых теста, 1386 Rust tests PASS. Реальный Linux,
устойчивость namespace identity после уничтожения объекта и полный PASS остаются открыты.

[Q25-F054–F056](../reports/AUDIT-Q25-TUN-ADMISSION.md): удалено разрушающее восстановление TUN
по неполному списку PID. Клиент пассивно ждёт освобождения имени и отказывает при
ошибке lookup/смене ifindex; клиент и сервер создают первую очередь эксклюзивно.
Остальные очереди используют её фактическое имя. 20 новых тестов, 7 baseline FAIL,
1406 Rust tests PASS. Исправлена сборка Linux-тестов без server feature.
Attach/teardown races и реальный Linux остаются открыты.

[Q25-F057–F058](../reports/AUDIT-Q25-TUN-ATTACH.md): attach и дополнительные очереди
не регистрируют замену исчезнувшего TUN; ошибка TUNSETIFINDEX останавливает открытие.
VNET_HDR/неизвестные features отклоняются, поддерживаемые флаги сохраняются.
18 новых host-тестов + прежний parser-тест, 1425 Rust PASS; три новых Linux ioctl
теста только скомпилированы. Следующий проход владения зафиксирован ниже.

[Q25-F059–F060](../reports/AUDIT-Q25-TUN-LIFETIME.md): удаление TUN по имени устранено.
Guards клиента/сервера сохраняют исходные fd до очистки сети; setup rollback заимствует
устройство. 12 сценариев с извлечённым кодом PASS (baseline 7 FAIL / 5 PASS), 1425 Rust PASS.
Три новых native Linux-теста только скомпилированы. Внешние rename/delete,
identity DNS-маркеров/маршрутов и Q14-F027 остаются открытыми.

[Q25-F061–F062](../reports/AUDIT-Q25-DNS-LEASES.md): DNS сбрасывает только владеющее им
поколение. Namespace/index journal и неблокирующий lock заменяют маркеры по имени;
перед числовыми resolver-командами проверяется исходный fd. Startup не сбрасывает живой
link только по сохранённому маркеру. 24 новых host-теста, 1446 Rust PASS; guard harness
baseline 3 FAIL / 3 PASS, fixed 6 PASS. Native namespace-тест только скомпилирован.
Identity маршрутов, namespace resolver-сервиса и reuse индекса после проверки остаются открыты.

### 15. Сессии, IP-пулы и лимиты

**4 октября, Q15 DONE/PASS:** Q15-F003 ограничивает историю освобождённых IPv4/IPv6.
2370 unit-тестов, 148 проверок сессий, 54 проверки доставки через TUN, bonding,
матрица 18/18 и native A/B — PASS. [Отчёт и границы](../reports/AUDIT-Q15-CURRENT-SESSIONS.md).

**Код:** `qeli/src/server/pool.rs`, `qeli/src/server/handler.rs`, `qeli/src/server/udp_handler.rs`, `qeli/src/server/usage.rs`.

Allocate/auth/reconnect/evict/reap/revoke/quota под конкуренцией, atomic v4+v6, static/reservations/excludes, pool exhaustion. Общие caps TCP/UDP/bonding. Нет duplicate IP, leaked lease/token/task/client_subnet после каждого выхода.

**Имеющаяся обвязка/fixtures:** `scripts/test_udp_reap.py`, `scripts/test_maxsessions.py`, `scripts/test_multidevice.py`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE/PASS.**

**Проход учёта трафика:** [Q15-F001](../reports/AUDIT-Q14-Q15-WORKER-USAGE.md) закрывает
короткие TCP/UDP-сессии, последние байты writer, baseline при reset и удаление счётчиков.
14 переносимых тестов учёта проходят. Финальный пакет выше дополняет этот
исторический проход IP-пулами, конкурентными подключениями и фактическим
отключением по quota/expiry/revoke на Linux.

### 16. ACL, push routes и site-to-site

**4 октября, Q16 DONE/PASS:** Q16-F001 закрывает подмену источника через чужой или
незарегистрированный client_subnet; exact/LPM/current-session проверяются в общем ingress.
Q16-F002 сохраняет локальную доставку к TUN-адресу сервера при exit-default /0.
2374 unit-теста, реальные TCP/UDP/QUIC с IPv4/IPv6, матрица и native A/B — PASS.
[Отчёт и границы](../reports/AUDIT-Q16-ACL-ROUTES.md).


**Код:** `qeli/src/server/acl.rs`, `qeli/src/config/users.rs`, `qeli/src/transport_core/network.rs`.

User/group/profile precedence, longest prefix, client_to_client, spoofed source, overlap, /0 и client_subnet return path. Проверить TCP/UDP, v4/v6. Enforcement на сервере; revoke/смена владельца маршрута не сохраняет доступ старой сессии.

**Имеющаяся обвязка/fixtures:** `scripts/test_push_matrix.py`, `scripts/test_route_push.py`, `scripts/test_l3_user_limits.py`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE/PASS.**

### 17. IPv4 NAT, forwarding и sysctl

**4 октября, Q17 DONE/PASS:** 228 свежих packet/gateway checks на текущем кандидате;
319 адресных unit из Q16 и source/hash-qualified прежние backend/recovery проверки.
Q17-F001: старый gateway runner заменён безопасным изолированным. Исторические
открытые статусы ниже относятся к прежним снимкам; текущие результаты и принятые
границы — в [отчёте](../reports/AUDIT-Q17-IPV4-NETWORK.md).


**Код:** `qeli/src/server/nat.rs`, `qeli/src/client/sysctl.rs`, `qeli/src/client/gateway.rs`.

NAT44/forward_private/gateway_nat/MSS и iptables/nft backend errors. Before/after rules/routes/sysctl при нескольких профилях. Точный tag вместо substring, ownership, crash journal/boot-id; чужие правила и значения сохраняются.

**Имеющаяся обвязка/fixtures:** `scripts/test_gateway_nat.py`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE/PASS.**

**Очистка NAT, 23 сентября 2026:**
[Q14-F024/F025](../reports/AUDIT-Q14-NAT-CLEANUP.md): конечный проход по снимку правил,
проверка после удаления и диагностика ошибок с продолжением остальных правил/цепочек.
13 новых host-тестов, 999 Rust tests PASS; production Linux только cross-check.
Q14-F026 исправлена [следующим проходом](../reports/AUDIT-Q14-Q25-FIREWALL-CHECKS.md).
Q14-F027 (передача ошибок teardown), сроки firewall-команд и live Linux остаются открытыми.

**Общие firewall-проверки, 23 сентября 2026:**
[Q14-F026 / Q25-F018/F019](../reports/AUDIT-Q14-Q25-FIREWALL-CHECKS.md): сервер и Linux
kill-switch используют общий разбор presence/absence/errors; точечная очистка DNS
проверяет границу 1024 и продолжает TCP после отказа UDP. 17 новых host-тестов,
1016 Rust tests PASS; два новых Unix/Linux сценария только cross-check.
Q14-F027, сроки команд и реальные backend/runtime проверки остаются открытыми.

**Владение DNS firewall, 23 сентября 2026:**
[Q14-F028](../reports/AUDIT-Q14-DNS-OWNERSHIP.md): реестр worker сохраняет точные правила
при ошибке Drop/rollback; cleanup и новая установка повторяют очистку. Tokens защищают
новое поколение от старого lease; активные записи не участвуют в точечном retry.
12 новых host-тестов, 1028 Rust tests PASS; три adapter-регрессии отдельно сравнивают
baseline/fix. Q14-F027, persistent journal, deadlines и live Linux остаются открытыми.

**Итог остановки worker, 23 сентября 2026:**
[Q14-F027, частичное исправление](../reports/AUDIT-Q14-OWNED-SHUTDOWN.md): окончательный
retry известных DNS/IPv6 sysctl leases влияет на Result и код выхода worker. Flush
статистики выполняется после ошибки сети; активные DNS leases обнаруживаются без удаления.
14 новых host-тестов, 1042 Rust tests PASS; восемь отдельных process-exit сценариев PASS.
Дополнительный проход передаёт ошибку worker через внешний supervisor при финальной
остановке: nonzero exit и принудительный kill больше не возвращают Ok. Ещё пять
host-тестов, итог этого этапа 1047 Rust tests PASS; три отдельные supervisor-регрессии PASS.
Следующий проход: [задачи профиля и TUN teardown](../reports/AUDIT-Q14-PROFILE-SHUTDOWN.md).
Ошибки shutdown JoinSet, TUN queue timeout/panic и удаления устройства теперь входят в
итог worker; 13 новых host-тестов, матрица этого этапа 1060 Rust tests PASS.
[Q14-F029/F030](../reports/AUDIT-Q14-SYSCTL-RECOVERY.md): исправлены ложный успех
sysctl recovery и потеря существующего owner при неудачном повторном acquire;
1060 Rust tests и 7 отдельных fixture checks PASS.
[Q14-F031](../reports/AUDIT-Q14-IPV6-PARTIAL-ACQUIRE.md): частичный IPv6 acquire теперь
регистрируется до первой попытки; любой отказ вызывает rollback, неуспешный откат
сохраняет scope для итоговой очистки. 11 новых регрессий и перенос одного Linux-only
теста: матрица этого этапа 1072 Rust tests PASS; пять отдельных adapter checks PASS.
[Q14-F032](../reports/AUDIT-Q14-NAT-COMMANDS.md): все пять запусков команд server NAT
переведены на общий runner (15 с; 16 МиБ на каждый поток вывода). Timeout не теряет
DNS ownership; матрица этого этапа 1073 Rust tests и шесть отдельных adapter checks PASS.
Открыты generic NAT outcome, старые поколения/retry backoff, restart policy, persistent
journal, общий срок всей операции, остальные системные команды и live Linux.

**Откат gateway и защита, 23 сентября 2026:**
[Q25-F040–F042](../reports/AUDIT-Q25-GATEWAY-ROLLBACK.md): записи TUN/семья/подсеть
заменяют общие флаги и undo по текущему конфигу. Ошибка семьи сохраняет состояние
для повтора; ошибка проверки firewall запрещает вставку, повторно используемый
permit тоже проверяет порядок kill-switch. Router-операции удерживают общую
блокировку процесса до release sysctl. Восемь исходных FAIL → PASS; 25 новых теста
и пять существующих, впервые включённых на host; 1287 Rust tests и девять команд
матрицы PASS. Общий WAN/NAT exit-node, несколько kill-switch chains, межпроцессные
гонки, общий deadline и Linux runtime остаются открытыми.

**Exit NAT и допуск kill-switch, 23 сентября 2026:**
[Q25-F043–F045](../reports/AUDIT-Q25-EXIT-OWNERSHIP.md): NAT-комментарии различают
правила TUN/WAN; cleanup больше не обнаруживает цели без записанного владения.
Запуск kill-switch проверяет обе семьи до изменений и отвергает чужую/старую Qeli
chain. Carrier первого остаётся доступен; конкурентные запуски одного процесса
принимают одну политику. 13 исходных FAIL → PASS; 30 новых тестов, два устаревших
helper-теста удалены. 1315 Rust tests и девять команд матрицы PASS. Межпроцессные
гонки, stale TUN identity, обнаружение IPv6-защиты и Linux runtime остаются открыты.
Продолжение: [Q25-F046–F047](../reports/AUDIT-Q25-KILL-SWITCH-LIFETIME.md) —
межпроцессное владение защищённой сессией и отказ при неизвестном IPv6.
Linux runtime новых lease-тестов остаётся открытым; статус раздела не меняется.

[Q25-F048–F049](../reports/AUDIT-Q25-CLIENT-NAMESPACE.md): положительное доказательство
ipv6.disable=1 разрешает пропустить IPv6 firewall; общий lease резервирует TUN всех
Linux-клиентов, включая gateway/exit без kill-switch и dev_attach. 17 новых host-тестов,
3 исходных FAIL → PASS. Runtime Linux и полный PASS раздела остаются открыты.

[Q25-F050–F051](../reports/AUDIT-Q25-SYSCTL-OWNER-EVIDENCE.md): неизвестные владельцы sysctl сохраняются,
acquire/recovery сообщают ошибку; недостоверное наблюдение sysctl не теряет original
для retry. Восемь baseline-регрессий исправлены, 1362 Rust tests PASS. Namespace
identity журнала, реальный Linux runtime и полный PASS раздела остаются открыты.

[Q25-F052–F053](../reports/AUDIT-Q25-SYSCTL-NAMESPACE.md): sysctl journal v2 разделяет network namespaces,
проверяет PID/time контекст и procfs до prune; непустой v1 текущего boot-id сохраняется
с явной ошибкой миграции. 24 новых теста, 1386 Rust tests PASS. Реальный Linux,
устойчивость namespace identity после уничтожения объекта и полный PASS остаются открыты.

### 18. IPv6 off/manual/route/nat66 и NDP

**4 октября, Q18 DONE/PASS:** Q18-F001/F002 исправлены; baseline → fix на настоящих NS/NA. 184 новых NDP checks и 446 checks матрицы/переходов; 2376 unit PASS, Clippy и четыре native A/B target PASS. [Итог и границы](../reports/AUDIT-Q18-IPV6-NDP.md). Исторические открытые статусы ниже относятся к прежним снимкам.

**Код:** `qeli/src/server/nat.rs`, `qeli/src/server/ndp_proxy.rs`, `qeli/src/config/server.rs`.

Все 4×3 egress/NDP комбинации для ipv4/dual/ipv6; все 16 переходов через stop/restart на dual, отдельная квалификация IPv6-only сохраняет исходную область. Linux E2E: off блокирует transit; manual не добавляет IPv6 firewall/DNS/sysctl; route сохраняет source; nat66 маскирует. RA, exact cleanup, NS validation, live-session ownership/revoke, required failure, DNS 53/5353, независимый IPv4.

**Имеющаяся обвязка/fixtures:** `scripts/test_panel_ipv6_e2e.py`, `scripts/run_ipv6_release_matrix.py`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE/PASS.**

**Очистка NAT, 23 сентября 2026:**
[Q14-F024/F025](../reports/AUDIT-Q14-NAT-CLEANUP.md): конечный проход по снимку правил,
проверка после удаления и диагностика ошибок с продолжением остальных правил/цепочек.
13 новых host-тестов, 999 Rust tests PASS; production Linux только cross-check.
Q14-F026 исправлена [следующим проходом](../reports/AUDIT-Q14-Q25-FIREWALL-CHECKS.md).
Q14-F027 (передача ошибок teardown), сроки firewall-команд и live Linux остаются открытыми.

**Общие firewall-проверки, 23 сентября 2026:**
[Q14-F026 / Q25-F018/F019](../reports/AUDIT-Q14-Q25-FIREWALL-CHECKS.md): сервер и Linux
kill-switch используют общий разбор presence/absence/errors; точечная очистка DNS
проверяет границу 1024 и продолжает TCP после отказа UDP. 17 новых host-тестов,
1016 Rust tests PASS; два новых Unix/Linux сценария только cross-check.
Q14-F027, сроки команд и реальные backend/runtime проверки остаются открытыми.

**Владение DNS firewall, 23 сентября 2026:**
[Q14-F028](../reports/AUDIT-Q14-DNS-OWNERSHIP.md): реестр worker сохраняет точные правила
при ошибке Drop/rollback; cleanup и новая установка повторяют очистку. Tokens защищают
новое поколение от старого lease; активные записи не участвуют в точечном retry.
12 новых host-тестов, 1028 Rust tests PASS; три adapter-регрессии отдельно сравнивают
baseline/fix. Q14-F027, persistent journal, deadlines и live Linux остаются открытыми.

**Итог остановки worker, 23 сентября 2026:**
[Q14-F027, частичное исправление](../reports/AUDIT-Q14-OWNED-SHUTDOWN.md): окончательный
retry известных DNS/IPv6 sysctl leases влияет на Result и код выхода worker. Flush
статистики выполняется после ошибки сети; активные DNS leases обнаруживаются без удаления.
14 новых host-тестов, 1042 Rust tests PASS; восемь отдельных process-exit сценариев PASS.
Дополнительный проход передаёт ошибку worker через внешний supervisor при финальной
остановке: nonzero exit и принудительный kill больше не возвращают Ok. Ещё пять
host-тестов, итог этого этапа 1047 Rust tests PASS; три отдельные supervisor-регрессии PASS.
Следующий проход: [задачи профиля и TUN teardown](../reports/AUDIT-Q14-PROFILE-SHUTDOWN.md).
Ошибки shutdown JoinSet, TUN queue timeout/panic и удаления устройства теперь входят в
итог worker; 13 новых host-тестов, матрица этого этапа 1060 Rust tests PASS.
[Q14-F029/F030](../reports/AUDIT-Q14-SYSCTL-RECOVERY.md): исправлены ложный успех
sysctl recovery и потеря существующего owner при неудачном повторном acquire;
1060 Rust tests и 7 отдельных fixture checks PASS.
[Q14-F031](../reports/AUDIT-Q14-IPV6-PARTIAL-ACQUIRE.md): частичный IPv6 acquire теперь
регистрируется до первой попытки; любой отказ вызывает rollback, неуспешный откат
сохраняет scope для итоговой очистки. 11 новых регрессий и перенос одного Linux-only
теста: матрица этого этапа 1072 Rust tests PASS; пять отдельных adapter checks PASS.
[Q14-F032](../reports/AUDIT-Q14-NAT-COMMANDS.md): все пять запусков команд server NAT
переведены на общий runner (15 с; 16 МиБ на каждый поток вывода). Timeout не теряет
DNS ownership; матрица этого этапа 1073 Rust tests и шесть отдельных adapter checks PASS.
Открыты generic NAT outcome, старые поколения/retry backoff, restart policy, persistent
journal, общий срок всей операции, остальные системные команды и live Linux.

**Откат gateway и защита, 23 сентября 2026:**
[Q25-F040–F042](../reports/AUDIT-Q25-GATEWAY-ROLLBACK.md): записи TUN/семья/подсеть
заменяют общие флаги и undo по текущему конфигу. Ошибка семьи сохраняет состояние
для повтора; ошибка проверки firewall запрещает вставку, повторно используемый
permit тоже проверяет порядок kill-switch. Router-операции удерживают общую
блокировку процесса до release sysctl. Восемь исходных FAIL → PASS; 25 новых теста
и пять существующих, впервые включённых на host; 1287 Rust tests и девять команд
матрицы PASS. Общий WAN/NAT exit-node, несколько kill-switch chains, межпроцессные
гонки, общий deadline и Linux runtime остаются открытыми.

**Exit NAT и допуск kill-switch, 23 сентября 2026:**
[Q25-F043–F045](../reports/AUDIT-Q25-EXIT-OWNERSHIP.md): NAT-комментарии различают
правила TUN/WAN; cleanup больше не обнаруживает цели без записанного владения.
Запуск kill-switch проверяет обе семьи до изменений и отвергает чужую/старую Qeli
chain. Carrier первого остаётся доступен; конкурентные запуски одного процесса
принимают одну политику. 13 исходных FAIL → PASS; 30 новых тестов, два устаревших
helper-теста удалены. 1315 Rust tests и девять команд матрицы PASS. Межпроцессные
гонки, stale TUN identity, обнаружение IPv6-защиты и Linux runtime остаются открыты.
Продолжение: [Q25-F046–F047](../reports/AUDIT-Q25-KILL-SWITCH-LIFETIME.md) —
межпроцессное владение защищённой сессией и отказ при неизвестном IPv6.
Linux runtime новых lease-тестов остаётся открытым; статус раздела не меняется.

[Q25-F048–F049](../reports/AUDIT-Q25-CLIENT-NAMESPACE.md): положительное доказательство
ipv6.disable=1 разрешает пропустить IPv6 firewall; общий lease резервирует TUN всех
Linux-клиентов, включая gateway/exit без kill-switch и dev_attach. 17 новых host-тестов,
3 исходных FAIL → PASS. Runtime Linux и полный PASS раздела остаются открыты.

[Q25-F050–F051](../reports/AUDIT-Q25-SYSCTL-OWNER-EVIDENCE.md): неизвестные владельцы sysctl сохраняются,
acquire/recovery сообщают ошибку; недостоверное наблюдение sysctl не теряет original
для retry. Восемь baseline-регрессий исправлены, 1362 Rust tests PASS. Namespace
identity журнала, реальный Linux runtime и полный PASS раздела остаются открыты.

[Q25-F052–F053](../reports/AUDIT-Q25-SYSCTL-NAMESPACE.md): sysctl journal v2 разделяет network namespaces,
проверяет PID/time контекст и procfs до prune; непустой v1 текущего boot-id сохраняется
с явной ошибкой миграции. 24 новых теста, 1386 Rust tests PASS. Реальный Linux,
устойчивость namespace identity после уничтожения объекта и полный PASS остаются открыты.

### 19. DNS сервера и клиентов

**4 октября, Q19 DONE/PASS:** 105 свежих real DNS/tunnel/resolved/crash checks; Q19-V001 закрывает TCP/TC runtime gap. Новых production-багов не найдено; 32 релевантных source hashes, 61 raw file и 9 архивов сверены; неизменённый Q18 Linux/native reuse. [Итог и границы](../reports/AUDIT-Q19-DNS-FINAL.md). Исторические открытые статусы ниже относятся к прежним снимкам.

**Код:** `qeli/src/server/dns.rs`, `qeli/src/server/dns/resolver.rs`, `qeli/src/client/dns.rs`, `qeli/src/transport_core/network.rs`.

UDP/TCP upstream, truncation fallback, timeouts, malformed packets, cache/eviction/blocklist. Full/split, resolved/resolv.conf и OS resolvers, leak v4/v6, failed apply до Connected, crash restore. Custom port/manual IPv6; DoT не объявляется реализованным при отказе валидатора.

**Имеющаяся обвязка/fixtures:** `scripts/test_dns_test_server.py`, `scripts/test_panel_route_dns.py`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE/PASS.**

**Проход общего сетевого плана, 22–23 сентября 2026:**
[отчёт Q19/Q22](../reports/AUDIT-Q19-Q22-NETWORK-PLAN.md). Исправлены различия legacy/v2 DNS
и зависимость лимита маршрутов от порядка исключений; убрана устаревшая тестовая
реализация Linux DNS. Это проверка общего планировщика, не завершение всего модуля.
DNS proxy/cache, реальные OS apply/rollback и конкурентный lifecycle остаются открыты.

**Серверный DNS, 23 сентября 2026:** [отчёт Q19](../reports/AUDIT-Q19-DNS-PROXY.md).
Исправлены Q19-F004–F006: TTL NODATA после CNAME, проверка сжатых имён и failover
после TCP TC. Один production engine тестируется локально; 22 DNS-теста с UDP/TCP,
754 Rust-теста суммарно — PASS. Linux lifecycle, расширенные DNS-типы и нагрузочные
проверки остаются открытыми; общий статус раздела не закрыт.


**Кеш и подписанные обмены, 23 сентября 2026:**
[Продолжение Q19](../reports/AUDIT-Q19-DNS-CACHE.md) закрывает Q19-F007–F010:
лимит пакетов кеша 16 МиБ на профиль, пересылка TSIG/SIG(0) без изменения байтов
и кеширования, проверка заголовка/opcode запросов. У старого сценария панели
устранён запуск SSH при импорте. 36 DNS-тестов, 768 Rust-тестов
суммарно — PASS. Реальный Linux lifecycle, длительная конкурентная нагрузка/RSS,
расширенные EDNS/RDATA и внешний стенд подписанных обменов остаются открытыми;
раздел 19 сохраняет статус **IN_PROGRESS**.

**EDNS/RDATA, 23 сентября 2026:**
[Следующий проход Q19](../reports/AUDIT-Q19-DNS-EDNS.md) закрывает Q19-F011–F015:
TTL всех возвращаемых секций, структуру распространённых RDATA, проверку OPT/TLV
и BADVERS, сохранение расширенного RCODE при усечении, обход кеша для EDNS-опций
и новый OPT при обычном cache hit. 51 DNS-тест, включая IPv6 loopback UDP/TCP;
783 Rust-теста суммарно — PASS. Linux lifecycle, длительная нагрузка/RSS,
семантика DNSSEC/RRset, внешняя совместимость и OS DNS apply/rollback остаются открытыми.

**DNS-слушатели и cleanup, 23 сентября 2026:**
[проход Q14/Q19](../reports/AUDIT-Q14-Q19-LIFECYCLE.md): production UDP/TCP listeners
доступны host-тестам; удалён неиспользуемый ServerState. 7 listener + 52 resolver
теста: IPv4/IPv6, persistent/pipelined TCP, deadline, предел 512 соединений,
отмена запросов и повторное занятие портов. 798 Rust-тестов суммарно — PASS.
Общий lifecycle исправлен в Q14-F001–F002; реальный Linux runtime и длительная
нагрузка остаются открытыми.

**Восстановление старого resolver, 23 сентября 2026:**
[Q25-F006](../reports/AUDIT-Q25-DNS-RECOVERY.md): ошибки unlink/chmod и некорректный снимок
больше не считаются успешным восстановлением и не приводят к удалению записи восстановления.
Восемь новых Windows host-тестов проходят; три Unix-сценария только cross-check.
913 host Rust tests PASS. Live Linux DNS и передача ошибок нижележащей очистки ещё открыты.

**Передача ошибок очистки TUN/маршрутов/DNS, 23 сентября 2026:**
[Q25-F007–F009](../reports/AUDIT-Q25-TUN-CLEANUP.md): явная очистка и guards отката передают
ошибки в Linux retry loop через общий ограниченный журнал. Ошибка не становится успешной
остановкой по сигналу и не снимает включённый kill-switch. TunnelSetup владеет guard до ACK
ядра; тип terminal kick сохраняется при сопутствующих ошибках. Восемь новых host-тестов
проходят, два Linux adapter-теста только cross-check. 921 host Rust tests PASS. Live Linux
E2E, сроки выполнения команд и полное ожидание задач поколения ещё открыты.

**Системные команды TUN/DNS, 23 сентября 2026:**
[Q25-F016/F017](../reports/AUDIT-Q25-SYSTEM-COMMANDS.md): 15 секунд на команду, полный
вывод с лимитом 16 МиБ на поток, завершение дочернего процесса и сохранение DNS marker
при отказе. Диагностика больше не обещает неподтверждённый rollback. 986 host Rust tests
PASS; два новых Linux process-group теста только cross-check. Маршруты/firewall, live
Linux и общий deadline shutdown остаются открытыми; статус раздела IN_PROGRESS.

**Очистка NAT, 23 сентября 2026:**
[Q14-F024/F025](../reports/AUDIT-Q14-NAT-CLEANUP.md): конечный проход по снимку правил,
проверка после удаления и диагностика ошибок с продолжением остальных правил/цепочек.
13 новых host-тестов, 999 Rust tests PASS; production Linux только cross-check.
Q14-F026 исправлена [следующим проходом](../reports/AUDIT-Q14-Q25-FIREWALL-CHECKS.md).
Q14-F027 (передача ошибок teardown), сроки firewall-команд и live Linux остаются открытыми.

**Общие firewall-проверки, 23 сентября 2026:**
[Q14-F026 / Q25-F018/F019](../reports/AUDIT-Q14-Q25-FIREWALL-CHECKS.md): сервер и Linux
kill-switch используют общий разбор presence/absence/errors; точечная очистка DNS
проверяет границу 1024 и продолжает TCP после отказа UDP. 17 новых host-тестов,
1016 Rust tests PASS; два новых Unix/Linux сценария только cross-check.
Q14-F027, сроки команд и реальные backend/runtime проверки остаются открытыми.

**Владение DNS firewall, 23 сентября 2026:**
[Q14-F028](../reports/AUDIT-Q14-DNS-OWNERSHIP.md): реестр worker сохраняет точные правила
при ошибке Drop/rollback; cleanup и новая установка повторяют очистку. Tokens защищают
новое поколение от старого lease; активные записи не участвуют в точечном retry.
12 новых host-тестов, 1028 Rust tests PASS; три adapter-регрессии отдельно сравнивают
baseline/fix. Q14-F027, persistent journal, deadlines и live Linux остаются открытыми.

**Итог остановки worker, 23 сентября 2026:**
[Q14-F027, частичное исправление](../reports/AUDIT-Q14-OWNED-SHUTDOWN.md): окончательный
retry известных DNS/IPv6 sysctl leases влияет на Result и код выхода worker. Flush
статистики выполняется после ошибки сети; активные DNS leases обнаруживаются без удаления.
14 новых host-тестов, 1042 Rust tests PASS; восемь отдельных process-exit сценариев PASS.
Дополнительный проход передаёт ошибку worker через внешний supervisor при финальной
остановке: nonzero exit и принудительный kill больше не возвращают Ok. Ещё пять
host-тестов, итог этого этапа 1047 Rust tests PASS; три отдельные supervisor-регрессии PASS.
Следующий проход: [задачи профиля и TUN teardown](../reports/AUDIT-Q14-PROFILE-SHUTDOWN.md).
Ошибки shutdown JoinSet, TUN queue timeout/panic и удаления устройства теперь входят в
итог worker; 13 новых host-тестов, матрица этого этапа 1060 Rust tests PASS.
[Q14-F029/F030](../reports/AUDIT-Q14-SYSCTL-RECOVERY.md): исправлены ложный успех
sysctl recovery и потеря существующего owner при неудачном повторном acquire;
1060 Rust tests и 7 отдельных fixture checks PASS.
[Q14-F031](../reports/AUDIT-Q14-IPV6-PARTIAL-ACQUIRE.md): частичный IPv6 acquire теперь
регистрируется до первой попытки; любой отказ вызывает rollback, неуспешный откат
сохраняет scope для итоговой очистки. 11 новых регрессий и перенос одного Linux-only
теста: матрица этого этапа 1072 Rust tests PASS; пять отдельных adapter checks PASS.
[Q14-F032](../reports/AUDIT-Q14-NAT-COMMANDS.md): все пять запусков команд server NAT
переведены на общий runner (15 с; 16 МиБ на каждый поток вывода). Timeout не теряет
DNS ownership; матрица этого этапа 1073 Rust tests и шесть отдельных adapter checks PASS.
Открыты generic NAT outcome, старые поколения/retry backoff, restart policy, persistent
journal, общий срок всей операции, остальные системные команды и live Linux.

### 20. DHCP и lease lifecycle

**Код:** `qeli/src/server/dhcp.rs`, `qeli/src/config/server.rs`.

DISCOVER/OFFER/REQUEST/ACK/NAK/RELEASE, bad requested_ip, duplicate xid/MAC, expiry и malformed options. NAK не расходует lease, пустой пул не underflow. Только поддерживаемая TAP/IPv4 конфигурация; проверить сохранение через панель.

**Имеющаяся обвязка/fixtures:** `qeli/tests/config_examples.rs`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE/PASS.**

**4 октября, Q20 завершён:** [отчёт DHCP](../reports/AUDIT-Q20-DHCP-FINAL.md). Пять исправлений;2383 Linux unit PASS/60 ignored;35 смысловых DHCP-проверок и60 запросов заполнения лимита,13 свежих VPN smoke checks;четыре native A/B target. TAP injection проверяет настоящий worker DHCP, а не VPN AUTH/device E2E. Воспроизведены старые malformed OFFER и64-DNS admission;INI-границы описаны.

### 21. TUN/TAP, IP, MTU/PMTU и фрагментация

**4 октября, Q21 завершён:** [TUN/TAP, IP и MTU/PMTU](../reports/AUDIT-Q21-PACKETS-FINAL.md). Новых production-ошибок не подтверждено; семь новых свойств,61 actual-module test,70 сетевых проверок,3 portable checks и два независимо разобранных carrier PCAP PASS. Текущие full unit/Clippy/release/native Q20 и прежний privileged TUN runtime сверены в пределах реального scope. Итого: 21/37 (56,8%), осталось 16; далее Q22.

[Q25-F067–F068](../reports/AUDIT-Q25-GATEWAY-IDENTITY.md): gateway привязан к RouteOwner;
firewall проверяет namespace/TUN внутри операций, cleanup выполняется до закрытия TUN.
При потере TUN правила очищаются в исходном namespace, sysctl scope сохраняется.
13 новых host tests, 1485 Rust PASS; 9 baseline регрессий воспроизведены. Внутренний
sysctl journal/stale recovery и самостоятельные kill-switch операции ещё открыты.

[Q25-F065–F066](../reports/AUDIT-Q25-SETUP-IDENTITY.md): setup/roaming route commands
проверяют исходный TUN через Weak и удерживаемый namespace; physical rollback независим.
Потеря identity терминальна, включая callback и последний FIB query. 13 новых host tests,
1472 Rust PASS; четыре новых native tests только скомпилированы. Gateway/firewall/sysctl
внутри callback, physical uplinks и гонка после проверки остаются открыты.

[Q25-F063–F064](../reports/AUDIT-Q25-ROUTE-IDENTITY.md): route cleanup проверяет
удерживаемый namespace и исходный TUN перед каждой командой; rename/delete/unknown
сохраняет reservations, physical bypass очищается независимо. 13 новых host tests,
1459 Rust PASS; три native route tests только скомпилированы. Гонка после последней
проверки, setup/roaming TUN identity и физические uplinks остаются открыты.

**Код:** `qeli/src/tun`, `qeli/src/protocol/ip.rs`, `qeli/src/protocol/icmp.rs`, `qeli/src/protocol/data_frag.rs`, `qeli/src/protocol/udp_frag.rs`.

TUN host prefixes, TAP ARP/NDP/RA/DAD, unsupported EtherType/VLAN/multicast. MTU 1280/малый outer PMTU, spoofed PTB и смена пути. Reassembly duplicate/overlap/gap/order/expiry/ID reuse, memory cap; PCAP без непредусмотренной внешней фрагментации.

**Имеющаяся обвязка/fixtures:** `scripts/test_tap_ipv6_control_probe.py`, `qeli/fuzz/fuzz_targets/data_frag.rs`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE/PASS.**

**Отмена shutdown TUN, 23 сентября 2026:** [Q25-F014](../reports/AUDIT-Q25-TUN-WORKERS.md).
Общий TunWorkers сохраняет владение Unix TUN/Wintun потоками до join, включая отмену
начатого shutdown и занятый blocking pool. Семь новых host-регрессий; 947 Rust tests PASS.
Unix-тест дескрипторов только кросс-компилирован. Реальные устройства/драйверы и остальные
сценарии раздела не проверены; полный аудит остаётся открытым.

**Системные команды TUN/DNS, 23 сентября 2026:**
[Q25-F016/F017](../reports/AUDIT-Q25-SYSTEM-COMMANDS.md): 15 секунд на команду, полный
вывод с лимитом 16 МиБ на поток, завершение дочернего процесса и сохранение DNS marker
при отказе. Диагностика больше не обещает неподтверждённый rollback. 986 host Rust tests
PASS; два новых Linux process-group теста только cross-check. Маршруты/firewall, live
Linux и общий deadline shutdown остаются открытыми; статус раздела IN_PROGRESS.

[Q25-F054–F056](../reports/AUDIT-Q25-TUN-ADMISSION.md): удалено разрушающее восстановление TUN
по неполному списку PID. Клиент пассивно ждёт освобождения имени и отказывает при
ошибке lookup/смене ifindex; клиент и сервер создают первую очередь эксклюзивно.
Остальные очереди используют её фактическое имя. 20 новых тестов, 7 baseline FAIL,
1406 Rust tests PASS. Исправлена сборка Linux-тестов без server feature.
Attach/teardown races и реальный Linux остаются открыты.

[Q25-F057–F058](../reports/AUDIT-Q25-TUN-ATTACH.md): attach и дополнительные очереди
не регистрируют замену исчезнувшего TUN; ошибка TUNSETIFINDEX останавливает открытие.
VNET_HDR/неизвестные features отклоняются, поддерживаемые флаги сохраняются.
18 новых host-тестов + прежний parser-тест, 1425 Rust PASS; три новых Linux ioctl
теста только скомпилированы. Следующий проход владения зафиксирован ниже.

[Q25-F059–F060](../reports/AUDIT-Q25-TUN-LIFETIME.md): удаление TUN по имени устранено.
Guards клиента/сервера сохраняют исходные fd до очистки сети; setup rollback заимствует
устройство. 12 сценариев с извлечённым кодом PASS (baseline 7 FAIL / 5 PASS), 1425 Rust PASS.
Три новых native Linux-теста только скомпилированы. Внешние rename/delete,
identity DNS-маркеров/маршрутов и Q14-F027 остаются открытыми.

[Q25-F061–F062](../reports/AUDIT-Q25-DNS-LEASES.md): DNS сбрасывает только владеющее им
поколение. Namespace/index journal и неблокирующий lock заменяют маркеры по имени;
перед числовыми resolver-командами проверяется исходный fd. Startup не сбрасывает живой
link только по сохранённому маркеру. 24 новых host-теста, 1446 Rust PASS; guard harness
baseline 3 FAIL / 3 PASS, fixed 6 PASS. Native namespace-тест только скомпилирован.
Identity маршрутов, namespace resolver-сервиса и reuse индекса после проверки остаются открыты.

### 22. Transport core, FFI/JNI и память

**4 октября, Q22 завершён:** [transport core, FFI/JNI и память](../reports/AUDIT-Q22-CORE-FFI-FINAL.md). Q22-F001/F002 закрывают queued access после panic и отменяют leased runner до удаления handle. Два baseline-отказа воспроизведены; 2402 full-feature units, strict Clippy, 22 Windows C ABI, 23 actual Android JNI, C11/C++11 headers и четыре native A/B PASS. CLI Linux побайтно прежний, сетевые execution сохраняют свой scope. Итого: 22/37 (59,5%), осталось 15; далее Q23.

[Q25-F067–F068](../reports/AUDIT-Q25-GATEWAY-IDENTITY.md): gateway привязан к RouteOwner;
firewall проверяет namespace/TUN внутри операций, cleanup выполняется до закрытия TUN.
При потере TUN правила очищаются в исходном namespace, sysctl scope сохраняется.
13 новых host tests, 1485 Rust PASS; 9 baseline регрессий воспроизведены. Внутренний
sysctl journal/stale recovery и самостоятельные kill-switch операции ещё открыты.

[Q25-F065–F066](../reports/AUDIT-Q25-SETUP-IDENTITY.md): setup/roaming route commands
проверяют исходный TUN через Weak и удерживаемый namespace; physical rollback независим.
Потеря identity терминальна, включая callback и последний FIB query. 13 новых host tests,
1472 Rust PASS; четыре новых native tests только скомпилированы. Gateway/firewall/sysctl
внутри callback, physical uplinks и гонка после проверки остаются открыты.

[Q25-F063–F064](../reports/AUDIT-Q25-ROUTE-IDENTITY.md): route cleanup проверяет
удерживаемый namespace и исходный TUN перед каждой командой; rename/delete/unknown
сохраняет reservations, physical bypass очищается независимо. 13 новых host tests,
1459 Rust PASS; три native route tests только скомпилированы. Гонка после последней
проверки, setup/roaming TUN identity и физические uplinks остаются открыты.

**Код:** `qeli/src/transport_core`, `qeli/include/qeli_transport_core.h`, `native-libs`.

Create/start/PREPARE/APPLY/COMMIT/stop/free, callbacks, buffers, queues, cancellation/generation. Stale handle, double-free, callback после dispose, partial failure, ABI/feature mismatch. Packaged cores должны соответствовать исходникам, а не только успешно загружаться.

**Имеющаяся обвязка/fixtures:** `scripts/test_native_repro.py`, `native-libs/provenance.py`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE/PASS.**

**Проход общего сетевого плана, 22–23 сентября 2026:**
[отчёт Q19/Q22](../reports/AUDIT-Q19-Q22-NETWORK-PLAN.md). Исправлены различия legacy/v2 DNS
и зависимость лимита маршрутов от порядка исключений; убрана устаревшая тестовая
реализация Linux DNS. Это проверка общего планировщика, не завершение всего модуля.
DNS proxy/cache, реальные OS apply/rollback и конкурентный lifecycle остаются открыты.


**Владение задачами TCP и Linux path monitor, 23 сентября 2026:**
[Q25-F010/F011](../reports/AUDIT-Q25-TCP-TASKS.md): общий владелец закрывает создание задач
до abort/join. TCP reader/writer/pipeline и producers завершаются до сетевой очистки;
ошибка управляющего события также проходит teardown. Linux blocking-работы монитора
учитываются для TCP и UDP. 931 host Rust tests PASS; Linux только cross-check. Остальные
UDP-задачи, вложенные transport workers, полная отмена и сроки команд остаются открытыми.

**Владение UDP-задачами и порядок отката, 23 сентября 2026:**
[Q25-F012/F013](../reports/AUDIT-Q25-UDP-TASKS.md): active/candidate/draining receive,
candidate-connect и Linux-монитор принадлежат одной группе. Ошибка управляющего события
проходит штатную очистку; группа завершается до проверки/отката платформенного кандидата.
TaskHandle сохраняет обязанность join при отмене ожидания или переносе пути. Девять новых
регрессий; 940 host Rust tests PASS, Linux только cross-check. Открыты вложенные transport
workers, принудительная отмена, сроки команд и платформенные fault-injection сценарии.

**Отмена shutdown TUN, 23 сентября 2026:** [Q25-F014](../reports/AUDIT-Q25-TUN-WORKERS.md).
Общий TunWorkers сохраняет владение Unix TUN/Wintun потоками до join, включая отмену
начатого shutdown и занятый blocking pool. Семь новых host-регрессий; 947 Rust tests PASS.
Unix-тест дескрипторов только кросс-компилирован. Реальные устройства/драйверы и остальные
сценарии раздела не проверены; полный аудит остаётся открытым.

**Вложенные H2-задачи, 23 сентября 2026:** [Q25-F015](../reports/AUDIT-Q25-H2-TASKS.md).
TCP-группа создаётся до connect и ждёт driver/bridge; native runner сохраняет её при
отмене попытки. Девять новых регрессий, 956 Rust tests PASS; Linux только cross-check.
Серверный H2 проверен далее в [Q14-F022/F023](../reports/AUDIT-Q14-H2-TASKS.md).
Standalone H2, ранний platform rollback, UDP cancellation и deadlines остаются открытыми.

**Серверный H2 и pre-auth, 23 сентября 2026:**
[Q14-F022/F023](../reports/AUDIT-Q14-H2-TASKS.md): профиль ждёт вложенные H2-задачи перед
teardown; flush отказа сохраняет pre-auth slot до освобождения I/O. 13 новых регрессий,
969 Rust tests PASS. H2/ProfileTasks/semaphore проверены на host, production Linux только
кросс-компилирован. Остальные сценарии раздела и live Linux E2E остаются открытыми.

**Команды Linux-монитора, 23 сентября 2026:** [Q25-F020](../reports/AUDIT-Q25-PATH-MONITOR.md):
три read-only запроса маршрутов/адресов используют общий runner со сроком 15 секунд
и лимитами вывода. TaskGroup сохраняет владение blocking-командой при остановке;
ошибка sample не публикует PathUpdate. 1098 Rust tests и 23 production-adapter сценария PASS.
Мутации маршрутов, общий срок остановки и реальный Linux handover остаются открытыми.

**Gateway WAN, 23 сентября 2026:** [Q25-F021/F022](../reports/AUDIT-Q25-GATEWAY-WAN.md):
IPv4/IPv6 default-route и fallback используют общий runner с ограничениями; cleanup
ищет WAN только при отсутствии сохранённых целей семейства. Семь новых переносимых
регрессий, 1105 Rust tests и 33 отдельных adapter-сценария PASS. Реальный Linux firewall
и ownership при неизвестном результате мутации остаются открытыми.

**Неуспешные мутации маршрутов, 23 сентября 2026:**
[Q25-F023/F024](../reports/AUDIT-Q25-ROUTE-OUTCOME.md): failed add/replace/retirement
считается обратимым только после подтверждения неизменности destination; недоступный,
изменённый или многострочный снимок даёт unknown state. 15 новых регрессий и восемь
существующих route-тестов теперь исполняются на host; 1128 Rust tests PASS.
Baseline: 10 ожидаемых отказов и 5 controls. Pending ownership/recovery неопределённого
маршрута, сроки команд и реальный Linux остаются открытыми.

**Владение маршрутами и cleanup, 23 сентября 2026:**
[Q25-F025/F026](../reports/AUDIT-Q25-ROUTE-OWNERSHIP.md): журнал сохраняет переданные
параметры удаления; устаревшая identity не разрешает replace/retirement/rollback.
Очистка подтверждает отсутствие и сохраняет неудачные записи для retry.
16 новых регрессий; 1144 Rust tests PASS. Те же adapter-тесты воспроизводят 15 отказов
baseline и один control. Общий для процесса ownership, неизвестные pending мутации,
атомарная identity, сроки команд и реальный Linux остаются открытыми.

**Изоляция маршрутов, 23 сентября 2026:**
[Q25-F027/F028](../reports/AUDIT-Q25-ROUTE-SCOPE.md): уникальный owner передаётся setup,
guards и roaming; cleanup закрывает приём и обрабатывает только его записи.
Другой Qeli owner не может заимствовать маршрут; повтор имени TUN заблокирован до
завершения прежнего lease. 17 новых регрессий, 1161 Rust tests PASS; baseline — два
целевых отказа. Attach-mode не объявляет managed roaming. Межпроцессная изоляция,
осиротевшие/pending операции, TUN workers, deadlines и Linux runtime остаются открытыми.

**Дополнение 2026-09-23 — результаты retirement/restore:**
[Q25-F029/F030](../reports/AUDIT-Q25-ROUTE-POSTCONDITIONS.md): удаление требует
подтверждённого отсутствия, восстановление — полного прежнего снимка. Потерянный
результат не отменяет подтверждённое действие, ложный успех не подтверждает откат.
16 новых baseline failures → 16 PASS; общий набор 1177 Rust tests, девять команд
матрицы PASS. Linux runtime не запускался. Pending unknown/orphan recovery,
межпроцессные гонки и сроки команд остаются открытыми; статус раздела не изменён.

**Дополнение 2026-09-23 — pending и orphan:**
[Q25-F031/F032](../reports/AUDIT-Q25-ROUTE-PENDING.md): неопределённая roaming-операция
сохраняет reservation без права delete; любой неизвестный commit закрывает admission.
Cleanup/reconnect освобождает pending/orphan только после подтверждения отсутствия,
с отдельными условиями для финального lease и interface flush. 17 новых регрессий/
controls; 1194 Rust tests и девять команд матрицы PASS. Initial setup mutations,
flush postconditions, постоянный crash recovery, deadlines и Linux runtime остаются открытыми.

**Дополнение 2026-09-23 — initial setup и flush:**
[Q25-F033/F034](../reports/AUDIT-Q25-SETUP-FLUSH.md): carrier/exclude/blackhole используют
общие exact pre/post checks и pending при неизвестном результате. Обе семьи interface
flush требуют подтверждения пустого состояния либо отсутствующего интерфейса через
link inventory. 8 baseline failures → PASS, ещё 13 controls; 1214 Rust tests и девять
команд матрицы PASS. Linux runtime, command deadlines, остальные route paths,
постоянный crash recovery и Q14-F027 workers/FD остаются открытыми.

**Дополнение 2026-09-23 — ограниченные route/firewall-команды:**
[Q25-F035/F036](../reports/AUDIT-Q25-CLIENT-COMMANDS.md): route и kill-switch используют
общий runner: 15 секунд на команду, по 16 МиБ stdout/stderr. Gateway наследует пределы
через iptables-helper. Unknown outcome сохраняет pending/проверки; неизвестный IPv4
default route требует защиты при отсутствии явного allow_ipv4_leak.
20 новых тестов; 1234 Rust tests и девять команд матрицы PASS. Общий deadline транзакции,
прочие route ownership paths, gateway rollback и Linux runtime остаются открытыми.

**Дополнение 2026-09-23 — TUN/TAP, pushed и local routes:**
[Q25-F037–F039](../reports/AUDIT-Q25-TUNNEL-ROUTES.md): активный NetworkPlan installer
использует общие exact pre/post checks, проверку метрик и ownership/pending.
Старые невызываемые pushed/local implementations и второй parser удалены.
Повреждённый inventory route_local запрещает мутации. Pending сверяется после
независимого flush принадлежащего Qeli интерфейса. 10 воспроизводящих регрессий и
13 controls; 1257 Rust tests и девять команд матрицы PASS. Gateway rollback, globals,
общий deadline, crash recovery и Linux runtime остаются открытыми.

### 23. Роуминг, resume и CONTROL_V2

**4 октября, Q23 завершён:** [роуминг, resume и CONTROL_V2](../reports/AUDIT-Q23-ROAMING-FINAL.md). Q23-F001 восстанавливает таймер исходного grace после abort подготовленного resume. 2405 units, strict Clippy, 24 целевых теста, 12 свежих Linux сценариев/281 проверок и четыре native A/B PASS. Итого: 23/37 (62,2%), осталось 14; далее Q24.

**Код:** `qeli/src/protocol/roaming.rs`, `qeli/src/protocol/control_v2.rs`, `qeli/src/transport_core`.

TCP make-before-break/UDP migration: proof/path validation, anti-amplification, grace expiry, replay/revoke и candidate races. NAT rebinding, family switch, Wi-Fi/LTE, sleep/wake, server restart/APPLY rollback, PMTU reset. Проверить межсерверные границы; одна константа PUSH_CONFIG не доказывает реализацию.

**Имеющаяся обвязка/fixtures:** `scripts/roaming_tcp_all_modes_netns_e2e.sh`, `scripts/roaming_udp_all_modes_netns_e2e.sh`, `scripts/roaming_mixed_version_netns_e2e.sh`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE/PASS.**

**Владение задачами TCP и Linux path monitor, 23 сентября 2026:**
[Q25-F010/F011](../reports/AUDIT-Q25-TCP-TASKS.md): общий владелец закрывает создание задач
до abort/join. TCP reader/writer/pipeline и producers завершаются до сетевой очистки;
ошибка управляющего события также проходит teardown. Linux blocking-работы монитора
учитываются для TCP и UDP. 931 host Rust tests PASS; Linux только cross-check. Остальные
UDP-задачи, вложенные transport workers, полная отмена и сроки команд остаются открытыми.

**Владение UDP-задачами и порядок отката, 23 сентября 2026:**
[Q25-F012/F013](../reports/AUDIT-Q25-UDP-TASKS.md): active/candidate/draining receive,
candidate-connect и Linux-монитор принадлежат одной группе. Ошибка управляющего события
проходит штатную очистку; группа завершается до проверки/отката платформенного кандидата.
TaskHandle сохраняет обязанность join при отмене ожидания или переносе пути. Девять новых
регрессий; 940 host Rust tests PASS, Linux только cross-check. Открыты вложенные transport
workers, принудительная отмена, сроки команд и платформенные fault-injection сценарии.

**Вложенные H2-задачи, 23 сентября 2026:** [Q25-F015](../reports/AUDIT-Q25-H2-TASKS.md).
TCP-группа создаётся до connect и ждёт driver/bridge; native runner сохраняет её при
отмене попытки. Девять новых регрессий, 956 Rust tests PASS; Linux только cross-check.
Серверный H2 проверен далее в [Q14-F022/F023](../reports/AUDIT-Q14-H2-TASKS.md).
Standalone H2, ранний platform rollback, UDP cancellation и deadlines остаются открытыми.

**Команды Linux-монитора, 23 сентября 2026:** [Q25-F020](../reports/AUDIT-Q25-PATH-MONITOR.md):
три read-only запроса маршрутов/адресов используют общий runner со сроком 15 секунд
и лимитами вывода. TaskGroup сохраняет владение blocking-командой при остановке;
ошибка sample не публикует PathUpdate. 1098 Rust tests и 23 production-adapter сценария PASS.
Мутации маршрутов, общий срок остановки и реальный Linux handover остаются открытыми.

**Неуспешные мутации маршрутов, 23 сентября 2026:**
[Q25-F023/F024](../reports/AUDIT-Q25-ROUTE-OUTCOME.md): failed add/replace/retirement
считается обратимым только после подтверждения неизменности destination; недоступный,
изменённый или многострочный снимок даёт unknown state. 15 новых регрессий и восемь
существующих route-тестов теперь исполняются на host; 1128 Rust tests PASS.
Baseline: 10 ожидаемых отказов и 5 controls. Pending ownership/recovery неопределённого
маршрута, сроки команд и реальный Linux остаются открытыми.

**Владение маршрутами и cleanup, 23 сентября 2026:**
[Q25-F025/F026](../reports/AUDIT-Q25-ROUTE-OWNERSHIP.md): журнал сохраняет переданные
параметры удаления; устаревшая identity не разрешает replace/retirement/rollback.
Очистка подтверждает отсутствие и сохраняет неудачные записи для retry.
16 новых регрессий; 1144 Rust tests PASS. Те же adapter-тесты воспроизводят 15 отказов
baseline и один control. Общий для процесса ownership, неизвестные pending мутации,
атомарная identity, сроки команд и реальный Linux остаются открытыми.

**Изоляция маршрутов, 23 сентября 2026:**
[Q25-F027/F028](../reports/AUDIT-Q25-ROUTE-SCOPE.md): уникальный owner передаётся setup,
guards и roaming; cleanup закрывает приём и обрабатывает только его записи.
Другой Qeli owner не может заимствовать маршрут; повтор имени TUN заблокирован до
завершения прежнего lease. 17 новых регрессий, 1161 Rust tests PASS; baseline — два
целевых отказа. Attach-mode не объявляет managed roaming. Межпроцессная изоляция,
осиротевшие/pending операции, TUN workers, deadlines и Linux runtime остаются открытыми.

**Дополнение 2026-09-23 — результаты retirement/restore:**
[Q25-F029/F030](../reports/AUDIT-Q25-ROUTE-POSTCONDITIONS.md): удаление требует
подтверждённого отсутствия, восстановление — полного прежнего снимка. Потерянный
результат не отменяет подтверждённое действие, ложный успех не подтверждает откат.
16 новых baseline failures → 16 PASS; общий набор 1177 Rust tests, девять команд
матрицы PASS. Linux runtime не запускался. Pending unknown/orphan recovery,
межпроцессные гонки и сроки команд остаются открытыми; статус раздела не изменён.

**Дополнение 2026-09-23 — pending и orphan:**
[Q25-F031/F032](../reports/AUDIT-Q25-ROUTE-PENDING.md): неопределённая roaming-операция
сохраняет reservation без права delete; любой неизвестный commit закрывает admission.
Cleanup/reconnect освобождает pending/orphan только после подтверждения отсутствия,
с отдельными условиями для финального lease и interface flush. 17 новых регрессий/
controls; 1194 Rust tests и девять команд матрицы PASS. Initial setup mutations,
flush postconditions, постоянный crash recovery, deadlines и Linux runtime остаются открытыми.

**Дополнение 2026-09-23 — initial setup и flush:**
[Q25-F033/F034](../reports/AUDIT-Q25-SETUP-FLUSH.md): carrier/exclude/blackhole используют
общие exact pre/post checks и pending при неизвестном результате. Обе семьи interface
flush требуют подтверждения пустого состояния либо отсутствующего интерфейса через
link inventory. 8 baseline failures → PASS, ещё 13 controls; 1214 Rust tests и девять
команд матрицы PASS. Linux runtime, command deadlines, остальные route paths,
постоянный crash recovery и Q14-F027 workers/FD остаются открытыми.

**Дополнение 2026-09-23 — ограниченные route/firewall-команды:**
[Q25-F035/F036](../reports/AUDIT-Q25-CLIENT-COMMANDS.md): route и kill-switch используют
общий runner: 15 секунд на команду, по 16 МиБ stdout/stderr. Gateway наследует пределы
через iptables-helper. Unknown outcome сохраняет pending/проверки; неизвестный IPv4
default route требует защиты при отсутствии явного allow_ipv4_leak.
20 новых тестов; 1234 Rust tests и девять команд матрицы PASS. Общий deadline транзакции,
прочие route ownership paths, gateway rollback и Linux runtime остаются открытыми.

**Дополнение 2026-09-23 — TUN/TAP, pushed и local routes:**
[Q25-F037–F039](../reports/AUDIT-Q25-TUNNEL-ROUTES.md): активный NetworkPlan installer
использует общие exact pre/post checks, проверку метрик и ownership/pending.
Старые невызываемые pushed/local implementations и второй parser удалены.
Повреждённый inventory route_local запрещает мутации. Pending сверяется после
независимого flush принадлежащего Qeli интерфейса. 10 воспроизводящих регрессий и
13 controls; 1257 Rust tests и девять команд матрицы PASS. Gateway rollback, globals,
общий deadline, crash recovery и Linux runtime остаются открытыми.

### 24. Multipath, bonding и общий бюджет

**Код:** `qeli/src/client/mod.rs`, `qeli/src/transport_core/buffer_pool.rs`, `qeli/src/transport_core/carrier.rs`, `qeli/src/transport_core/session.rs`, `qeli/src/server/handler.rs`.

JOIN proof, stream caps, asymmetric RTT/loss, отказ одного/всех путей, ordering/starvation. Bandwidth/quota/buffer cap не умножается на streams. Resume/reconnect/stream close сохраняют корректную сессию и освобождают лишние carriers.

**Имеющаяся обвязка/fixtures:** `scripts/roaming_netns_e2e.sh`, `scripts/roaming_tcp_bonding_netns_case.sh`, `scripts/roaming_tcp_starvation_netns_case.sh`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE/PASS.**

**4 октября — Q24 завершён:** [отчёт](../reports/AUDIT-Q24-BONDING.md). Q24-F001
устраняет starvation общего пула с обеих сторон. 2407 units/60 ignored, строгий
Clippy, release, 12 Linux сценариев/283 проверки, 4 native A/B, 22 Windows ABI
и 23 JNI проверки PASS. Исторический throughput не повторялся. Итог: 24/37 (64,9%); далее Q25.


**Владение задачами TCP и Linux path monitor, 23 сентября 2026:**
[Q25-F010/F011](../reports/AUDIT-Q25-TCP-TASKS.md): общий владелец закрывает создание задач
до abort/join. TCP reader/writer/pipeline и producers завершаются до сетевой очистки;
ошибка управляющего события также проходит teardown. Linux blocking-работы монитора
учитываются для TCP и UDP. 931 host Rust tests PASS; Linux только cross-check. Остальные
UDP-задачи, вложенные transport workers, полная отмена и сроки команд остаются открытыми.

**Владение UDP-задачами и порядок отката, 23 сентября 2026:**
[Q25-F012/F013](../reports/AUDIT-Q25-UDP-TASKS.md): active/candidate/draining receive,
candidate-connect и Linux-монитор принадлежат одной группе. Ошибка управляющего события
проходит штатную очистку; группа завершается до проверки/отката платформенного кандидата.
TaskHandle сохраняет обязанность join при отмене ожидания или переносе пути. Девять новых
регрессий; 940 host Rust tests PASS, Linux только cross-check. Открыты вложенные transport
workers, принудительная отмена, сроки команд и платформенные fault-injection сценарии.

**Вложенные H2-задачи, 23 сентября 2026:** [Q25-F015](../reports/AUDIT-Q25-H2-TASKS.md).
TCP-группа создаётся до connect и ждёт driver/bridge; native runner сохраняет её при
отмене попытки. Девять новых регрессий, 956 Rust tests PASS; Linux только cross-check.
Серверный H2 проверен далее в [Q14-F022/F023](../reports/AUDIT-Q14-H2-TASKS.md).
Standalone H2, ранний platform rollback, UDP cancellation и deadlines остаются открытыми.

### 25. Linux CLI и восстановление сети

**Сверка 4 октября:** [итог Q25](../reports/AUDIT-Q25-LINUX-CLI-FINAL.md). F216/F217 исправлены; 2414 unit, 26 CLI/68 checks, 2 connected/32 checks и четыре fresh A/B пары PASS. Неизменённые сетевые реализации сверены по SHA/точному shared prefix; прежние recovery/soak scopes и D06 accepted limitation сохранены. Исторические открытые формулировки ниже относятся к прежним снимкам.

[Q25-F067–F068](../reports/AUDIT-Q25-GATEWAY-IDENTITY.md): gateway привязан к RouteOwner;
firewall проверяет namespace/TUN внутри операций, cleanup выполняется до закрытия TUN.
При потере TUN правила очищаются в исходном namespace, sysctl scope сохраняется.
13 новых host tests, 1485 Rust PASS; 9 baseline регрессий воспроизведены. Внутренний
sysctl journal/stale recovery и самостоятельные kill-switch операции ещё открыты.

[Q25-F065–F066](../reports/AUDIT-Q25-SETUP-IDENTITY.md): setup/roaming route commands
проверяют исходный TUN через Weak и удерживаемый namespace; physical rollback независим.
Потеря identity терминальна, включая callback и последний FIB query. 13 новых host tests,
1472 Rust PASS; четыре новых native tests только скомпилированы. Gateway/firewall/sysctl
внутри callback, physical uplinks и гонка после проверки остаются открыты.

[Q25-F063–F064](../reports/AUDIT-Q25-ROUTE-IDENTITY.md): route cleanup проверяет
удерживаемый namespace и исходный TUN перед каждой командой; rename/delete/unknown
сохраняет reservations, physical bypass очищается независимо. 13 новых host tests,
1459 Rust PASS; три native route tests только скомпилированы. Гонка после последней
проверки, setup/roaming TUN identity и физические uplinks остаются открыты.

**Код:** `qeli/src/client`, `qeli/src/client_main.rs`, `qeli/src/hooks.rs`.

Endpoint route pin/same-LAN, full/split, include/exclude, leak policy/kill switch. Stop/SIGTERM/SIGKILL/reconnect/failed setup: before/after routes/DNS/firewall без удаления чужого состояния. Trusted hooks/password_command, subprocess deadlines, честный cleanup status.

**Имеющаяся обвязка/fixtures:** `scripts/test_gateway_nat.py`, `scripts/test_tun_reclaim.py`.

- [x] Review и мёртвый код.
- [x] Штатные, граничные и негативные сценарии.
- [x] Отказы и конкуренция.
- [x] Интеграция и целевая платформа.
- [x] Исправления, повторная проверка и evidence.

**Статус: DONE / PASS.**

**Поставщик пароля и изоляция features, 23 сентября 2026:**
[Q25-F001 / Q33-F002 / Q14-F020 / Q34-F001](../reports/AUDIT-Q25-CREDENTIAL-COMMANDS.md):
асинхронный password_command, deadline 30 секунд, полный stdout до 16 KiB, отброшенный
stderr и ошибки без секретов. Ранний SIGINT/SIGTERM отменяет и собирает поставщика;
watchers/sampler клиента имеют владельца. Исправлен server-only TUN gate, обе изолированные
features проверяются в CI. 883 host Rust tests PASS; четыре Linux-теста только cross-check.
Server-only check имеет 23 прежних transport dead-code warnings. Лимиты password_file,
финальный drain клиента и Linux runtime/release checks ещё открыты.

**Файловый пароль и финальный статус, 23 сентября 2026:**
[Q25-F002 / Q14-F021](../reports/AUDIT-Q25-PASSWORD-FILES.md): общий zeroizing-буфер 16 KiB
для файла/команды, одна управляемая blocking-задача чтения обычного файла, поддержка symlink,
отказ FIFO и ожидание активного I/O при штатном stop/deadline. Final пишется после join
watchers/sampler, включая ошибки после инициализации reporter. 895 host Rust tests PASS;
два Unix-теста только cross-check. Неотменяемый I/O может превышать бюджет 30 секунд.
Startup/network rollback, мониторинг фоновых ошибок и Linux E2E ещё открыты.

**Fail-closed очистка сети, 23 сентября 2026:**
[Q25-F003](../reports/AUDIT-Q25-NETWORK-CLEANUP.md): forwarding/NAT cleanup должен
завершиться успешно до снятия включённого kill-switch; ошибка сохраняет защиту и её причину.
899 host Rust tests PASS, включая четыре переносимых fault-injection сценария. Linux
пока только cross-check. Разбор begin_connection записан ниже; live firewall/E2E ещё открыты.

**Ошибки жизненного цикла ядра, 23 сентября 2026:**
[Q25-F004/F005](../reports/AUDIT-Q25-CORE-LIFECYCLE.md): ошибка запуска ядра проходит через
cleanup/post_down; ошибка остановки завершается отказом и сохраняет включённый kill-switch,
при этом очистка forwarding выполняется. Шесть новых host-регрессий, включая реальный отказ
ClientCore при полной очереди. 905 host Rust tests PASS; Linux только cross-check.
Live Linux lifecycle/firewall и полный rollback маршрутов/DNS ещё открыты.


**Восстановление старого resolver, 23 сентября 2026:**
[Q25-F006](../reports/AUDIT-Q25-DNS-RECOVERY.md): ошибки unlink/chmod и некорректный снимок
больше не считаются успешным восстановлением и не приводят к удалению записи восстановления.
Восемь новых Windows host-тестов проходят; три Unix-сценария только cross-check.
913 host Rust tests PASS. Live Linux DNS и передача ошибок нижележащей очистки ещё открыты.

**Передача ошибок очистки TUN/маршрутов/DNS, 23 сентября 2026:**
[Q25-F007–F009](../reports/AUDIT-Q25-TUN-CLEANUP.md): явная очистка и guards отката передают
ошибки в Linux retry loop через общий ограниченный журнал. Ошибка не становится успешной
остановкой по сигналу и не снимает включённый kill-switch. TunnelSetup владеет guard до ACK
ядра; тип terminal kick сохраняется при сопутствующих ошибках. Восемь новых host-тестов
проходят, два Linux adapter-теста только cross-check. 921 host Rust tests PASS. Live Linux
E2E, сроки выполнения команд и полное ожидание задач поколения ещё открыты.

**Владение задачами TCP и Linux path monitor, 23 сентября 2026:**
[Q25-F010/F011](../reports/AUDIT-Q25-TCP-TASKS.md): общий владелец закрывает создание задач
до abort/join. TCP reader/writer/pipeline и producers завершаются до сетевой очистки;
ошибка управляющего события также проходит teardown. Linux blocking-работы монитора
учитываются для TCP и UDP. 931 host Rust tests PASS; Linux только cross-check. Остальные
UDP-задачи, вложенные transport workers, полная отмена и сроки команд остаются открытыми.

**Владение UDP-задачами и порядок отката, 23 сентября 2026:**
[Q25-F012/F013](../reports/AUDIT-Q25-UDP-TASKS.md): active/candidate/draining receive,
candidate-connect и Linux-монитор принадлежат одной группе. Ошибка управляющего события
проходит штатную очистку; группа завершается до проверки/отката платформенного кандидата.
TaskHandle сохраняет обязанность join при отмене ожидания или переносе пути. Девять новых
регрессий; 940 host Rust tests PASS, Linux только cross-check. Открыты вложенные transport
workers, принудительная отмена, сроки команд и платформенные fault-injection сценарии.

**Отмена shutdown TUN, 23 сентября 2026:** [Q25-F014](../reports/AUDIT-Q25-TUN-WORKERS.md).
Общий TunWorkers сохраняет владение Unix TUN/Wintun потоками до join, включая отмену
начатого shutdown и занятый blocking pool. Семь новых host-регрессий; 947 Rust tests PASS.
Unix-тест дескрипторов только кросс-компилирован. Реальные устройства/драйверы и остальные
сценарии раздела не проверены; полный аудит остаётся открытым.

**Вложенные H2-задачи, 23 сентября 2026:** [Q25-F015](../reports/AUDIT-Q25-H2-TASKS.md).
TCP-группа создаётся до connect и ждёт driver/bridge; native runner сохраняет её при
отмене попытки. Девять новых регрессий, 956 Rust tests PASS; Linux только cross-check.
Серверный H2 проверен далее в [Q14-F022/F023](../reports/AUDIT-Q14-H2-TASKS.md).
Standalone H2, ранний platform rollback, UDP cancellation и deadlines остаются открытыми.

**Системные команды TUN/DNS, 23 сентября 2026:**
[Q25-F016/F017](../reports/AUDIT-Q25-SYSTEM-COMMANDS.md): 15 секунд на команду, полный
вывод с лимитом 16 МиБ на поток, завершение дочернего процесса и сохранение DNS marker
при отказе. Диагностика больше не обещает неподтверждённый rollback. 986 host Rust tests
PASS; два новых Linux process-group теста только cross-check. Маршруты/firewall, live
Linux и общий deadline shutdown остаются открытыми; статус раздела IN_PROGRESS.

**Общие firewall-проверки, 23 сентября 2026:**
[Q14-F026 / Q25-F018/F019](../reports/AUDIT-Q14-Q25-FIREWALL-CHECKS.md): сервер и Linux
kill-switch используют общий разбор presence/absence/errors; точечная очистка DNS
проверяет границу 1024 и продолжает TCP после отказа UDP. 17 новых host-тестов,
1016 Rust tests PASS; два новых Unix/Linux сценария только cross-check.
Q14-F027, сроки команд и реальные backend/runtime проверки остаются открытыми.

**Продолжение серверного слоя:**
[Q14-F032](../reports/AUDIT-Q14-NAT-COMMANDS.md): все пять запусков команд server NAT
переведены на общий runner (15 с; 16 МиБ на каждый поток вывода). Timeout не теряет
DNS ownership; матрица этого этапа 1073 Rust tests и шесть отдельных adapter checks PASS.
Открыты generic NAT outcome, старые поколения/retry backoff, restart policy, persistent
journal, общий срок всей операции, остальные системные команды и live Linux.

**Команды Linux-монитора, 23 сентября 2026:** [Q25-F020](../reports/AUDIT-Q25-PATH-MONITOR.md):
три read-only запроса маршрутов/адресов используют общий runner со сроком 15 секунд
и лимитами вывода. TaskGroup сохраняет владение blocking-командой при остановке;
ошибка sample не публикует PathUpdate. 1098 Rust tests и 23 production-adapter сценария PASS.
Мутации маршрутов, общий срок остановки и реальный Linux handover остаются открытыми.

**Gateway WAN, 23 сентября 2026:** [Q25-F021/F022](../reports/AUDIT-Q25-GATEWAY-WAN.md):
IPv4/IPv6 default-route и fallback используют общий runner с ограничениями; cleanup
ищет WAN только при отсутствии сохранённых целей семейства. Семь новых переносимых
регрессий, 1105 Rust tests и 33 отдельных adapter-сценария PASS. Реальный Linux firewall
и ownership при неизвестном результате мутации остаются открытыми.

**Неуспешные мутации маршрутов, 23 сентября 2026:**
[Q25-F023/F024](../reports/AUDIT-Q25-ROUTE-OUTCOME.md): failed add/replace/retirement
считается обратимым только после подтверждения неизменности destination; недоступный,
изменённый или многострочный снимок даёт unknown state. 15 новых регрессий и восемь
существующих route-тестов теперь исполняются на host; 1128 Rust tests PASS.
Baseline: 10 ожидаемых отказов и 5 controls. Pending ownership/recovery неопределённого
маршрута, сроки команд и реальный Linux остаются открытыми.

**Владение маршрутами и cleanup, 23 сентября 2026:**
[Q25-F025/F026](../reports/AUDIT-Q25-ROUTE-OWNERSHIP.md): журнал сохраняет переданные
параметры удаления; устаревшая identity не разрешает replace/retirement/rollback.
Очистка подтверждает отсутствие и сохраняет неудачные записи для retry.
16 новых регрессий; 1144 Rust tests PASS. Те же adapter-тесты воспроизводят 15 отказов
baseline и один control. Общий для процесса ownership, неизвестные pending мутации,
атомарная identity, сроки команд и реальный Linux остаются открытыми.

**Изоляция маршрутов, 23 сентября 2026:**
[Q25-F027/F028](../reports/AUDIT-Q25-ROUTE-SCOPE.md): уникальный owner передаётся setup,
guards и roaming; cleanup закрывает приём и обрабатывает только его записи.
Другой Qeli owner не может заимствовать маршрут; повтор имени TUN заблокирован до
завершения прежнего lease. 17 новых регрессий, 1161 Rust tests PASS; baseline — два
целевых отказа. Attach-mode не объявляет managed roaming. Межпроцессная изоляция,
осиротевшие/pending операции, TUN workers, deadlines и Linux runtime остаются открытыми.

**Дополнение 2026-09-23 — результаты retirement/restore:**
[Q25-F029/F030](../reports/AUDIT-Q25-ROUTE-POSTCONDITIONS.md): удаление требует
подтверждённого отсутствия, восстановление — полного прежнего снимка. Потерянный
результат не отменяет подтверждённое действие, ложный успех не подтверждает откат.
16 новых baseline failures → 16 PASS; общий набор 1177 Rust tests, девять команд
матрицы PASS. Linux runtime не запускался. Pending unknown/orphan recovery,
межпроцессные гонки и сроки команд остаются открытыми; статус раздела не изменён.

**Дополнение 2026-09-23 — pending и orphan:**
[Q25-F031/F032](../reports/AUDIT-Q25-ROUTE-PENDING.md): неопределённая roaming-операция
сохраняет reservation без права delete; любой неизвестный commit закрывает admission.
Cleanup/reconnect освобождает pending/orphan только после подтверждения отсутствия,
с отдельными условиями для финального lease и interface flush. 17 новых регрессий/
controls; 1194 Rust tests и девять команд матрицы PASS. Initial setup mutations,
flush postconditions, постоянный crash recovery, deadlines и Linux runtime остаются открытыми.

**Дополнение 2026-09-23 — initial setup и flush:**
[Q25-F033/F034](../reports/AUDIT-Q25-SETUP-FLUSH.md): carrier/exclude/blackhole используют
общие exact pre/post checks и pending при неизвестном результате. Обе семьи interface
flush требуют подтверждения пустого состояния либо отсутствующего интерфейса через
link inventory. 8 baseline failures → PASS, ещё 13 controls; 1214 Rust tests и девять
команд матрицы PASS. Linux runtime, command deadlines, остальные route paths,
постоянный crash recovery и Q14-F027 workers/FD остаются открытыми.

**Дополнение 2026-09-23 — ограниченные route/firewall-команды:**
[Q25-F035/F036](../reports/AUDIT-Q25-CLIENT-COMMANDS.md): route и kill-switch используют
общий runner: 15 секунд на команду, по 16 МиБ stdout/stderr. Gateway наследует пределы
через iptables-helper. Unknown outcome сохраняет pending/проверки; неизвестный IPv4
default route требует защиты при отсутствии явного allow_ipv4_leak.
20 новых тестов; 1234 Rust tests и девять команд матрицы PASS. Общий deadline транзакции,
прочие route ownership paths, gateway rollback и Linux runtime остаются открытыми.

**Дополнение 2026-09-23 — TUN/TAP, pushed и local routes:**
[Q25-F037–F039](../reports/AUDIT-Q25-TUNNEL-ROUTES.md): активный NetworkPlan installer
использует общие exact pre/post checks, проверку метрик и ownership/pending.
Старые невызываемые pushed/local implementations и второй parser удалены.
Повреждённый inventory route_local запрещает мутации. Pending сверяется после
независимого flush принадлежащего Qeli интерфейса. 10 воспроизводящих регрессий и
13 controls; 1257 Rust tests и девять команд матрицы PASS. Gateway rollback, globals,
общий deadline, crash recovery и Linux runtime остаются открытыми.

**Откат gateway и защита, 23 сентября 2026:**
[Q25-F040–F042](../reports/AUDIT-Q25-GATEWAY-ROLLBACK.md): записи TUN/семья/подсеть
заменяют общие флаги и undo по текущему конфигу. Ошибка семьи сохраняет состояние
для повтора; ошибка проверки firewall запрещает вставку, повторно используемый
permit тоже проверяет порядок kill-switch. Router-операции удерживают общую
блокировку процесса до release sysctl. Восемь исходных FAIL → PASS; 25 новых теста
и пять существующих, впервые включённых на host; 1287 Rust tests и девять команд
матрицы PASS. Общий WAN/NAT exit-node, несколько kill-switch chains, межпроцессные
гонки, общий deadline и Linux runtime остаются открытыми.

**Exit NAT и допуск kill-switch, 23 сентября 2026:**
[Q25-F043–F045](../reports/AUDIT-Q25-EXIT-OWNERSHIP.md): NAT-комментарии различают
правила TUN/WAN; cleanup больше не обнаруживает цели без записанного владения.
Запуск kill-switch проверяет обе семьи до изменений и отвергает чужую/старую Qeli
chain. Carrier первого остаётся доступен; конкурентные запуски одного процесса
принимают одну политику. 13 исходных FAIL → PASS; 30 новых тестов, два устаревших
helper-теста удалены. 1315 Rust tests и девять команд матрицы PASS. Межпроцессные
гонки, stale TUN identity, обнаружение IPv6-защиты и Linux runtime остаются открыты.
Продолжение: [Q25-F046–F047](../reports/AUDIT-Q25-KILL-SWITCH-LIFETIME.md) —
межпроцессное владение защищённой сессией и отказ при неизвестном IPv6.
Linux runtime новых lease-тестов остаётся открытым; статус раздела не меняется.

[Q25-F048–F049](../reports/AUDIT-Q25-CLIENT-NAMESPACE.md): положительное доказательство
ipv6.disable=1 разрешает пропустить IPv6 firewall; общий lease резервирует TUN всех
Linux-клиентов, включая gateway/exit без kill-switch и dev_attach. 17 новых host-тестов,
3 исходных FAIL → PASS. Runtime Linux и полный PASS раздела остаются открыты.

[Q25-F050–F051](../reports/AUDIT-Q25-SYSCTL-OWNER-EVIDENCE.md): неизвестные владельцы sysctl сохраняются,
acquire/recovery сообщают ошибку; недостоверное наблюдение sysctl не теряет original
для retry. Восемь baseline-регрессий исправлены, 1362 Rust tests PASS. Namespace
identity журнала, реальный Linux runtime и полный PASS раздела остаются открыты.

[Q25-F052–F053](../reports/AUDIT-Q25-SYSCTL-NAMESPACE.md): sysctl journal v2 разделяет network namespaces,
проверяет PID/time контекст и procfs до prune; непустой v1 текущего boot-id сохраняется
с явной ошибкой миграции. 24 новых теста, 1386 Rust tests PASS. Реальный Linux,
устойчивость namespace identity после уничтожения объекта и полный PASS остаются открыты.

[Q25-F054–F056](../reports/AUDIT-Q25-TUN-ADMISSION.md): удалено разрушающее восстановление TUN
по неполному списку PID. Клиент пассивно ждёт освобождения имени и отказывает при
ошибке lookup/смене ifindex; клиент и сервер создают первую очередь эксклюзивно.
Остальные очереди используют её фактическое имя. 20 новых тестов, 7 baseline FAIL,
1406 Rust tests PASS. Исправлена сборка Linux-тестов без server feature.
Attach/teardown races и реальный Linux остаются открыты.

[Q25-F057–F058](../reports/AUDIT-Q25-TUN-ATTACH.md): attach и дополнительные очереди
не регистрируют замену исчезнувшего TUN; ошибка TUNSETIFINDEX останавливает открытие.
VNET_HDR/неизвестные features отклоняются, поддерживаемые флаги сохраняются.
18 новых host-тестов + прежний parser-тест, 1425 Rust PASS; три новых Linux ioctl
теста только скомпилированы. Следующий проход владения зафиксирован ниже.

[Q25-F059–F060](../reports/AUDIT-Q25-TUN-LIFETIME.md): удаление TUN по имени устранено.
Guards клиента/сервера сохраняют исходные fd до очистки сети; setup rollback заимствует
устройство. 12 сценариев с извлечённым кодом PASS (baseline 7 FAIL / 5 PASS), 1425 Rust PASS.
Три новых native Linux-теста только скомпилированы. Внешние rename/delete,
identity DNS-маркеров/маршрутов и Q14-F027 остаются открытыми.

[Q25-F061–F062](../reports/AUDIT-Q25-DNS-LEASES.md): DNS сбрасывает только владеющее им
поколение. Namespace/index journal и неблокирующий lock заменяют маркеры по имени;
перед числовыми resolver-командами проверяется исходный fd. Startup не сбрасывает живой
link только по сохранённому маркеру. 24 новых host-теста, 1446 Rust PASS; guard harness
baseline 3 FAIL / 3 PASS, fixed 6 PASS. Native namespace-тест только скомпилирован.
Identity маршрутов, namespace resolver-сервиса и reuse индекса после проверки остаются открыты.

### 26. Общий C# и managed/native граница

**Код:** `qeli-shared/QeliShared`, `qeli-shared/QeliConformance`.

Rust validation parity, import/export/storage, lifetime handles/callbacks. Conformance с обязательными fixtures и platform selftests. Мёртвые managed codecs проверять по OS/features/reflection до удаления; build/selftest не заменяет подключение клиента.

**Имеющаяся обвязка/fixtures:** `conformance/README.md`, `.github/workflows/ci.yml`.

- [ ] Review и мёртвый код.
- [ ] Штатные, граничные и негативные сценарии.
- [ ] Отказы и конкуренция.
- [ ] Интеграция и целевая платформа.
- [ ] Исправления, повторная проверка и evidence.

**Статус: TODO.**

### 27. Windows: GUI, служба и драйверы

**Код:** `qeli-win/QeliWin`, `qeli/src/transport_core/wintun.rs`.

LocalSystem IPC/ACL/SID, DPAPI, protected directories, atomic service profile и DLL loading. В Windows VM: Wintun/WinDivert/per-app, routes/DNS/firewall, stop во время connect, sleep/wake, boot service. Cleanup failures не маскируются; UAF/double-close отсутствуют.

**Имеющаяся обвязка/fixtures:** `scripts/e2e_windows_native.py`, `scripts/verify_windows_drivers.ps1`.

- [ ] Review и мёртвый код.
- [ ] Штатные, граничные и негативные сценарии.
- [ ] Отказы и конкуренция.
- [ ] Интеграция и целевая платформа.
- [ ] Исправления, повторная проверка и evidence.

**Статус: IN_PROGRESS.**

**Отмена shutdown TUN, 23 сентября 2026:** [Q25-F014](../reports/AUDIT-Q25-TUN-WORKERS.md).
Общий TunWorkers сохраняет владение Unix TUN/Wintun потоками до join, включая отмену
начатого shutdown и занятый blocking pool. Семь новых host-регрессий; 947 Rust tests PASS.
Unix-тест дескрипторов только кросс-компилирован. Реальные устройства/драйверы и остальные
сценарии раздела не проверены; полный аудит остаётся открытым.

### 28. macOS: daemon, utun, pf и Network Extension

**Код:** `qeli-mac/QeliMac`, `qeli-mac/per-app`.

Daemon IPC/owner/mode, Keychain, selected profile, Intel/ARM ABI и DNS journal. Реальный Mac: чужие pf/nat/rdr anchors, per-app entitlements, DNS leaks, reconnect, crash и sleep/wake. GUI/daemon/Network Extension проверяются отдельно.

**Имеющаяся обвязка/fixtures:** `qeli-mac/README.md`, `.github/workflows/ci.yml`.

- [ ] Review и мёртвый код.
- [ ] Штатные, граничные и негативные сценарии.
- [ ] Отказы и конкуренция.
- [ ] Интеграция и целевая платформа.
- [ ] Исправления, повторная проверка и evidence.

**Статус: TODO.**

### 29. Android: VpnService, JNI и lifecycle

**Код:** `qeli-android/app`.

Protect/TUN retention/generation при reconnect/cancel/stop. Keystore, INI migration, encrypted backup/lost-key recovery; manifest exports/deep links/boot. Устройство: Wi-Fi/LTE, always-on/lockdown, Doze, process kill, IPv6-only/NAT64, Release/R8.

**Имеющаяся обвязка/fixtures:** `scripts/roaming_android_sleep_wake_gate.py`, `scripts/roaming_android_udp_grace_expiry_gate.py`.

- [ ] Review и мёртвый код.
- [ ] Штатные, граничные и негативные сценарии.
- [ ] Отказы и конкуренция.
- [ ] Интеграция и целевая платформа.
- [ ] Исправления, повторная проверка и evidence.

**Статус: TODO.**

### 30. iOS: PacketTunnel, Swift и MDM

**Код:** `qeli-ios/QeliCore`, `qeli-ios/QeliPacketTunnel`, `qeli-ios/QeliIOS`, `qeli-ios/MDM`, `qeli-ios/QeliIOSTests`.

Exactly-once start/stop completion, generation/cancel, Keychain/app groups, extension memory. Устройство: On Demand, sleep/wake, captive portal, NAT64/DNS, per-app/MDM и rollback settings. Simulator build, signed IPA и physical evidence — разные статусы.

**Имеющаяся обвязка/fixtures:** `qeli-ios/PARITY.md`, `scripts/test_verify_ios_ipa.py`.

- [ ] Review и мёртвый код.
- [ ] Штатные, граничные и негативные сценарии.
- [ ] Отказы и конкуренция.
- [ ] Интеграция и целевая платформа.
- [ ] Исправления, повторная проверка и evidence.

**Статус: TODO.**

### 31. OpenWrt, LuCI и Keenetic

**Код:** `qeli-openwrt`, `scripts/build_keenetic.py`.

UCI → INI escaping/shell injection, LuCI ACL, secrets на flash, init/procd, upgrade/rollback. ARM/MIPS/mipsel, endian/32-bit ABI, client-only features. Реальный router: WAN renewal/reboot, DNS/firewall/hooks, memory/throughput; cross-build не device test.

**Имеющаяся обвязка/fixtures:** `scripts/keenetic_verify.py`.

- [ ] Review и мёртвый код.
- [ ] Штатные, граничные и негативные сценарии.
- [ ] Отказы и конкуренция.
- [ ] Интеграция и целевая платформа.
- [ ] Исправления, повторная проверка и evidence.

**Статус: TODO.**

### 32. Метрики, usage, логи и уведомления

**Код:** `qeli/src/server/metrics.rs`, `qeli/src/server/usage.rs`, `qeli/src/server/notify.rs`, `qeli/src/server/roaming_metrics.rs`, `qeli/src/trace.rs`, `qeli/src/web/api/logs.rs`.

Counters/quota/session accounting при reconnect/reap/crash, corrupt store, bounded log/SSE/backpressure. Notify INI/token/load races, SSRF/DNS rebinding/redirect/timeout/rate limit. Логи не раскрывают credentials, disabled trace не меняет hot path.

**Имеющаяся обвязка/fixtures:** `scripts/test_roaming_control_stats.py`, `scripts/test_blocked_settings.py`.

- [ ] Review и мёртвый код.
- [ ] Штатные, граничные и негативные сценарии.
- [ ] Отказы и конкуренция.
- [ ] Интеграция и целевая платформа.
- [ ] Исправления, повторная проверка и evidence.

**Статус: IN_PROGRESS.**

**Владение уведомлениями, 23 сентября 2026:**
[Q14-F018 / Q32-F001](../reports/AUDIT-Q14-Q32-NOTIFICATIONS.md): до 128 принятых отправок,
8 активных запросов на процесс, общий лимит проб панели, ограниченные payloads и drain
до 10 секунд после завершения производителей. Detached-обёртки уведомлений удалены.
864 host Rust tests PASS; Linux только all-targets cross-check. Владение panel/metrics/
autostart supervisor, доверие конфигу и Linux E2E ещё открыты.

### 33. Установка, обновление, файловые права и hooks

**Код:** `qeli/debian`, `qeli/src/server/update.rs`, `qeli/src/util.rs`, `qeli/src/hooks.rs`, `qeli/src/config_source.rs`, `release/docker`.

Fresh install/upgrade/downgrade/remove, systemd sandbox, identity/users preservation, checksums/attestation, atomic replace. Docker digest/recreate/health/rollback. File locks/symlinks/hardlinks/owners/ENOSPC, PATH hijack, panel/restore command injection и SSH timeouts.

**Имеющаяся обвязка/fixtures:** `scripts/test_ssh_run.ps1`, `scripts/release_preflight.py`.

- [ ] Review и мёртвый код.
- [ ] Штатные, граничные и негативные сценарии.
- [ ] Отказы и конкуренция.
- [ ] Интеграция и целевая платформа.
- [ ] Исправления, повторная проверка и evidence.

**Статус: IN_PROGRESS.**

**Доверие прочитанному конфигу, 23 сентября 2026:**
[Q14-F019 / Q33-F001](../reports/AUDIT-Q14-Q33-CONFIG-TRUST.md): владелец/права и данные
для парсера получаются из одного дескриптора; исходное разрешение не меняется при
повторах профиля и не перепроверяет путь. Очистка готового поколения сохраняет команду
и окружение после удаления/замены конфига. 874 host Rust tests PASS; четыре новых Unix/
Linux-теста только cross-checked. Лимиты password_command, владение startup-задачами,
installer/update/restore и Linux runtime integration ещё открыты.

**Поставщик пароля и изоляция features, 23 сентября 2026:**
[Q25-F001 / Q33-F002 / Q14-F020 / Q34-F001](../reports/AUDIT-Q25-CREDENTIAL-COMMANDS.md):
асинхронный password_command, deadline 30 секунд, полный stdout до 16 KiB, отброшенный
stderr и ошибки без секретов. Ранний SIGINT/SIGTERM отменяет и собирает поставщика;
watchers/sampler клиента имеют владельца. Исправлен server-only TUN gate, обе изолированные
features проверяются в CI. 883 host Rust tests PASS; четыре Linux-теста только cross-check.
Server-only check имеет 23 прежних transport dead-code warnings. Лимиты password_file,
финальный drain клиента и Linux runtime/release checks ещё открыты.

### 34. CI, зависимости, native provenance и релиз

**Код:** `qeli/Cargo.toml`, `qeli/Cargo.lock`, `.github/workflows`, `native-libs`, `release/certification`.

Feature/debug/release/jemalloc matrix, lockfiles, актуальные CVE/licenses и pinned Actions/SDK. Независимая A/B rebuild cores, hashes/ABI/provenance и signatures драйверов/APK/IPA. Certification опирается на реальные evidence текущего SHA, не на ручную замену digest/status.

**Имеющаяся обвязка/fixtures:** `scripts/test_native_recipes.py`, `scripts/test_native_repro.py`, `scripts/test_release_certification.py`, `scripts/release_certification.py`.

- [ ] Review и мёртвый код.
- [ ] Штатные, граничные и негативные сценарии.
- [ ] Отказы и конкуренция.
- [ ] Интеграция и целевая платформа.
- [ ] Исправления, повторная проверка и evidence.

**Статус: IN_PROGRESS.**

**Поставщик пароля и изоляция features, 23 сентября 2026:**
[Q25-F001 / Q33-F002 / Q14-F020 / Q34-F001](../reports/AUDIT-Q25-CREDENTIAL-COMMANDS.md):
асинхронный password_command, deadline 30 секунд, полный stdout до 16 KiB, отброшенный
stderr и ошибки без секретов. Ранний SIGINT/SIGTERM отменяет и собирает поставщика;
watchers/sampler клиента имеют владельца. Исправлен server-only TUN gate, обе изолированные
features проверяются в CI. 883 host Rust tests PASS; четыре Linux-теста только cross-check.
Server-only check имеет 23 прежних transport dead-code warnings. Лимиты password_file,
финальный drain клиента и Linux runtime/release checks ещё открыты.

### 35. Fuzzing, concurrency, DoS и soak

**Код:** `qeli/fuzz`, `scripts/stability_gate.py`.

Fuzz INI/hello/packet/WS/realtls/QUIC/IP/fragments/roaming с сохранением corpus. Failure injection каждой acquire/apply/save, гонки stop/auth/reload/reap. Soak 30–60 мин, перед release ≥8 ч: RSS/fd/tasks/leases/rules с churn; пороги роста задать заранее.

**Имеющаяся обвязка/fixtures:** `qeli/fuzz/README.md`, `scripts/roaming_udp_resource_soak_netns_gate.sh`, `scripts/linux_roaming_release_soak.sh`.

- [ ] Review и мёртвый код.
- [ ] Штатные, граничные и негативные сценарии.
- [ ] Отказы и конкуренция.
- [ ] Интеграция и целевая платформа.
- [ ] Исправления, повторная проверка и evidence.

**Статус: TODO.**

### 36. Бенчмарки и методика измерения

**Код:** `scripts/benchmark.py`, `qeli/src/packet_bench_main.rs`, `test`, `release/benchmark_results.json`.

Зафиксировать SHA/binaries, CPU/governor/affinity/VM contention, MTU/mode и background load. P=1/P=4, up/down/bidir, inner/outer v4/v6, TCP/UDP goodput, p50/p95/p99, loss/jitter, CPU/RSS/auth rate. ≥3 независимых повтора, median+spread/raw results; dev не подменяется числами 0.8.0.

**Имеющаяся обвязка/fixtures:** `scripts/perf_combined_load.py`, `scripts/bench_bonding.py`.

- [ ] Review и мёртвый код.
- [ ] Штатные, граничные и негативные сценарии.
- [ ] Отказы и конкуренция.
- [ ] Интеграция и целевая платформа.
- [ ] Исправления, повторная проверка и evidence.

**Статус: TODO.**

### 37. Документация, тестовая обвязка и мёртвый код

**Код:** `docs`, `qeli/config`, `scripts`, `conformance`, `site`.

Keys/defaults/errors против runtime, полные examples через check-config, RU/EN, stable/dev, ABI/benchmark dates. Legacy JSON config, unused dependencies/helpers/routes/flags и неподключённые тесты. Dead code подтвердить по всем OS/features/FFI/reflection/generators; регрессия должна падать на старом дефекте.

**Имеющаяся обвязка/fixtures:** `scripts/check_docs.py`, `scripts/check_panel.py`, `scripts/test_site_docs.js`, `scripts/sync_version.py`.

- [ ] Review и мёртвый код.
- [ ] Штатные, граничные и негативные сценарии.
- [ ] Отказы и конкуренция.
- [ ] Интеграция и целевая платформа.
- [ ] Исправления, повторная проверка и evidence.

**Статус: TODO.**

## 7. Команды исходной точки и последующих прогонов

Команды ниже выполняются из корня checkout. Использовать toolchain проекта и писать
вывод каждого запуска в отдельный лог. Они не разрешают автоматически запускать
произвольные сетевые/deploy-скрипты из предыдущих разделов.

```text
python scripts/check_docs.py
python scripts/check_panel.py
node scripts/test_panel_editors.cjs
node scripts/test_site_docs.js
python -m unittest discover -s scripts -p "test_native_*.py"
python scripts/sync_version.py
python native-libs/provenance.py --check
python scripts/release_certification.py --quiet
```

Полный серверный набор — **на Linux**; запуск той же команды на Windows имеет другое
cfg-покрытие. Зафиксировать точный target и features:

```text
cargo test --locked --manifest-path qeli/Cargo.toml --workspace -- --test-threads=1
cargo clippy --locked --manifest-path qeli/Cargo.toml --all-targets -- -D warnings
cargo test --locked --manifest-path qeli/Cargo.toml --features transport-core-ffi transport_core -- --test-threads=1
cargo run --locked --manifest-path qeli/Cargo.toml --features conformance-gen --bin gen-conformance -- --check
```

Команды Windows/macOS/Android/iOS builds/selftests брать из текущего
[CI](../../../.github/workflows/ci.yml), сохраняя environment/fixture guards. Старое
исключение Clippy в отчётах не переносить автоматически: указать toolchain и отдельную
причину для каждого исключения. Не называть cross-check выполнением Linux runtime.

## 8. Закрытие раздела и всего цикла

Находки нового цикла именуются `Q<раздел>-F<номер>`, например `Q01-F001`, чтобы не
смешивать их с повторяющимися A-номерами старых аудитов. Для каждой — impact,
предусловия, reachable path, воспроизведение, fix и regression evidence. P0/P1 —
блокеры затронутого выпуска до исправления либо явно зафиксированного решения;
P2/P3 сохраняются как конкретные задачи, не исчезают из-за зелёных сборок.

В конце каждого раздела обновить строку в реестре, приложить результат и назвать
следующий раздел. Изменение зависимого контракта открывает регрессию у его consumers.
Перед итоговым PASS: все обязательные разделы закрыты, блокеры разрешены, все
неприменимые случаи обоснованы, native/source SHA согласованы, физические сценарии
подтверждены, benchmark воспроизводим и docs отражают пределы поддержки.

**Ближайшая работа:** закрывать [реестр техдолга](AUDIT-DEBT.md), не открывая новые
разделы. В D02 остаётся durable namespace identity глобальных записей после crash;
затем D04 crash recovery и оставшиеся D05/D06 network budgets/resource context.
Проверки lock/I/O, доверия к каталогу, отдельного kill-switch и Linux route/TUN
уже выполнены в описанных ниже границах. Runtime-контракты, полная интеграционная
матрица, другие платформы, release A/B, soak и новый benchmark остаются открытыми.
Статусы полных разделов не изменены.

**24 сентября, D05:** [Q05-F002–F004](../reports/AUDIT-Q05-PANEL-TRANSACTIONS.md): async preflight до config lock, общий бюджет проб, отказ устаревшего snapshot, owned guard для отменяемого backup/restore, bounded restart dispatch. Разделы остаются IN_PROGRESS; архивные операции и полный HTTP/systemd E2E не закрыты.

**D05/D09, backup/restore:** [Q05-F005–F007](../reports/AUDIT-Q05-ARCHIVE-BUDGET.md): общий бюджет подготовки, bounded stdin/output, полный pre-restore snapshot, немедленный отказ дубликата и приватный API-handler roundtrip. Crash/ENOSPC/systemd и остальные сетевые бюджеты остаются открытыми.

**D02, Q25-F077:** [контекст внутри sysctl transaction](../reports/AUDIT-Q25-SYSCTL-CONTEXT-IO.md) проверяется вокруг PID/sysctl I/O и persistence; после потери контекста транзакция не может продолжить запись. Остальные критерии D02 остаются открытыми.

D02/D05/D09: [атомарная запись состояния](../reports/AUDIT-Q25-ATOMIC-STATE.md) очищает частичные временные файлы и синхронизирует каталог на Unix; реальные partial-write/fsync fault probes PASS. Остальные критерии этих групп остаются открыты.

D02/D05/D09: [каталог состояния и целостность lock](../reports/AUDIT-Q25-STATE-DIRECTORY.md). Parent trust закрыт в описанных границах; durable namespace identity и исходное поколение интерфейса остаются D02. Группы целиком ещё не закрыты.

D08/D11/D12: [Android JNI и emulator runtime](../reports/AUDIT-Q34-ANDROID-RUNTIME.md): исправлены cwd/API flag cargo-ndk, удалён устаревший JSON-config harness; 154 JVM + 6 instrumentation PASS. Свежий dev x86_64 APK проверен по SHA. Release A/B, полный конфигурационный/runtime контракт и остальные платформы открыты.

D02: [удержание namespace](../reports/AUDIT-Q25-NAMESPACE-PIN.md) открытыми fd действует от admission до конца транзакции; 1922 Linux + 29 privileged + 8 worker E2E PASS. Между транзакциями и после crash durable generation остаётся открытым, как и исходное поколение интерфейса.

D02: [Q25-F083 — исходный sysctl интерфейса](../reports/AUDIT-Q25-SYSCTL-TARGET.md): journal v3 удерживает fd и отказывает при потере свидетельства; 3 дефекта baseline воспроизведены, 5 дополнительных worker E2E PASS. Опасное восстановление по имени и потеря original закрыты. Для global journal durable namespace generation после crash остаётся открытым; автоматическое per-interface crash recovery не обещается.

D05: [Q25-F084 — общий срок DNS](../reports/AUDIT-Q25-DNS-BUDGET.md): dns/domain делят 15 секунд от admission, частичный lease сохраняется для отдельного rollback. 3 новые Linux-регрессии PASS. NAT/routes/kill-switch и остальные lock waits остаются открытыми.

D05/D09: [Q05-F008 — async health probes](../reports/AUDIT-Q05-HEALTH-PROBES.md): Status/Transport health не блокируют executor ожиданием `--version`; четыре общих async-слота, deadline включает очередь. 8 новых обычных + 1 privileged HTTP-router тест PASS; 2 контрольных возврата старого поведения дают ожидаемый FAIL. Общие сроки сетевых мутаций и полный HTTP/systemd/fault охват остаются открытыми.

D05/D09: [Q25-F085 — общий срок очистки kill-switch](../reports/AUDIT-Q25-KILL-SWITCH-BUDGET.md): 15 секунд включают operation mutex и обе семьи; частичный результат сохраняет owner для нового verified retry. 5 регрессий PASS, 2 контрольных FAIL старого поведения. Engage/refresh рассмотрены следующими фазами ниже; NAT/routes/gateway и прочие lock waits ещё открыты.

D05/D09: [Q25-F086/F087 — refresh kill-switch](../reports/AUDIT-Q25-KILL-SWITCH-REFRESH.md): общий срок admission/команд учитывает resolver; unknown не разрешает вставку. 6 новых регрессий и 5 повторных cleanup PASS; 3 контрольных FAIL прежнего поведения. DNS/NSS остаётся синхронным; engage закрыт следующей фазой ниже в части командного срока, NAT/routes/gateway и прочие ожидания открыты.

D05/D09: [Q25-F088/F089 — установка и откат kill-switch](../reports/AUDIT-Q25-KILL-SWITCH-SETUP.md): общий срок установки 15 секунд и отдельный общий срок отката 15 секунд; неполный откат нельзя принять флагами разрешения утечки. 8 новых регрессий PASS; 2 контрольных FAIL, затем 8 setup + 6 refresh + 5 cleanup PASS. Полный снимок: 1962 Linux + 30 privileged + 8 worker E2E PASS. Командные сроки engage/refresh/disengage закрыты в описанных границах; синхронный DNS/NSS, NAT/routes/gateway, прочие ожидания и полные D04/D05/D09 остаются открытыми.

D05/D09: [Q14-F034 — общий срок очистки NAT](../reports/AUDIT-Q14-NAT-CLEANUP-BUDGET.md): profile/startup/final cleanup делят по 15 секунд между очередью, IPv4/IPv6, точными правилами и retired DNS UDP/TCP. Поздние ответы не дают успеха, неподтверждённые записи сохраняются. 8 новых Linux-регрессий PASS; 4 контрольных FAIL, затем 8 регрессий + 1 privileged exact-rule PASS. Полный снимок: 1970 Linux + 30 privileged + 8 worker E2E PASS. Открыты NAT setup/rollback, admission DNS lease в Drop/setup, routes/gateway, внутренние sysctl/I/O и полные D04/D05/D09.

D05/D09: [Q14-F035 — сроки и retirement DNS INPUT lease](../reports/AUDIT-Q14-DNS-INPUT-BUDGET.md): setup и cleanup получают по 15 секунд с очередью/UDP/TCP; отдельный откат после setup, неблокирующая отметка завершения и сохранение pending evidence. 4 новые переносимые + 7 Linux + 1 privileged регрессии PASS; 5 контрольных отказов, затем 20 domain + 7 DNS + 8 NAT + 2 native PASS. Полный снимок: 1981 Linux + 31 privileged + 8 worker E2E PASS. NAT setup/rollback, DNS REDIRECT, routes/gateway, внутренние sysctl/I/O и полные D04/D05/D09 остаются открытыми.

D05/D09: [Q14-F036 — установка NAT/forwarding и DNS REDIRECT](../reports/AUDIT-Q14-NAT-SETUP-BUDGET.md): общие сроки setup и точного rollback; 10 новых регрессий, 7 контрольных отказов, 1991 Linux + 31 privileged + 8 E2E PASS. Client routes/gateway, scheduler isolation и полный D05 остаются открытыми.

D02 закрыт: [Q25-F090 — поколение namespace и журнал v4](../reports/AUDIT-Q25-NAMESPACE-GENERATION.md). D04/D05 и остальные критерии сохраняются. Проверки Windows VM, Mac/iOS и роутера исключены из текущего объёма по решению пользователя; они не объявляются PASS.

D09/D10: [17/17 Linux packet matrix PASS](../reports/AUDIT-Q34-LINUX-MATRIX.md). D13: 100 TCP handover сохранили сессию/fd, но RSS превысил критерий; FAIL сохранён, долг открыт.

D05/D09: [Q25-F091 — общий срок gateway/exit-node](../reports/AUDIT-Q25-GATEWAY-BUDGET.md): 6 регрессий, 6 контрольных FAIL, 107 restored gateway и полный Linux 2001 + 32 privileged + 8 E2E PASS. Route-последовательности, внутренние locks/I/O и scheduler isolation остаются открыты.

D13: [release TCP/UDP по 100 handover](../reports/AUDIT-Q34-RELEASE-SOAK.md): 30/30 утверждений PASS, прирост RSS в прежнем лимите 32 MiB; debug FAIL сохранён. Полный ресурсный/fault охват и итоговый снимок ещё открыты.

D05/D09: [Q25-F092 — общий срок route-транзакций](../reports/AUDIT-Q25-ROUTE-BUDGET.md): 8 регрессий, 6 контрольных FAIL, 196 восстановленных route tests и полный Linux 2009 + 32 privileged + 8 E2E PASS. Executor isolation и внутренний I/O остаются открыты.

D06/D09: [Q25-F093 — строгая проверка resolver-конфига](../reports/AUDIT-Q25-RESOLVER-CONFIG.md): 3 новых теста, 2 контрольных FAIL, 18 восстановленных DNS, полный Linux 2012 + 32 privileged + 8 E2E PASS. Отдельно подтверждена cross-netns мутация через общую D-Bus-шину; bus/service identity ещё требует исправления.

D06/D09/D10: [Q25-F094/F095 — контекст resolved/D-Bus и DNS-порт](../reports/AUDIT-Q25-RESOLVER-CONTEXT.md): direct unique-owner вызовы с AUTH GUID, 2023 Linux + 33 privileged + 8 E2E, 17/17 packet matrix (301 assertion), 4 контрольных FAIL и restored 29 DNS + 1 privileged PASS. Реальные resolved/custom port/чужие netns и PID namespace проверены. Предыдущий пункт о незакрытом bus/service identity закрыт в описанных границах; остальные критерии D06 и D10 открыты.

D04/D06/D09: [Q14-F037 — worker network lease](../reports/AUDIT-Q14-WORKER-NETWORK-LEASE.md): исправлен обход через разные control/state пути; baseline удалял 9 правил работающего worker. 2027 Linux + 34 privileged + 8 lifecycle и 22 crash/admission/recovery проверки PASS. D04 IN_PROGRESS: persistent exact firewall/routes и mixed nft остаются открытыми.

D04/D09/D10: [Q14-F038 — persistent server firewall](../reports/AUDIT-Q14-FIREWALL-JOURNAL.md): точные NAT/routing/DNS INPUT/REDIRECT спецификации записываются до изменения, восстанавливаются после SIGKILL и удаления профиля без listing. Backend/namespace/file errors останавливают startup, evidence сохраняется. 2044 Linux + 35 privileged + 8 lifecycle; 27 recovery checks; 17/17 cases, 301 assertions PASS. D04 остаётся IN_PROGRESS: клиентские route/DNS/kill-switch и полная mixed nft/firewalld матрица открыты.

D04/D06/D09: [Q25-F096/F097 — DNS state v2](../reports/AUDIT-Q25-DNS-MARKER-STORAGE.md): доверенный закреплённый каталог, проверка файлов и SO_NETNS_COOKIE; v1 сохраняется без автоматической миграции. 3 файловых дефекта воспроизведены на baseline. 2055 Linux + 37 privileged + 8 lifecycle; 17/17 cases, 323 assertions PASS. Остаются client route/kill-switch recovery, legacy global DNS, live persistent TUN, mixed nft/firewalld и накопление sidecar-файлов; D04 IN_PROGRESS.

D04/D09/D10: [Q25-F098 — kill-switch после crash](../reports/AUDIT-Q25-KILL-SWITCH-REBUILD.md): временные точные DROP guards сохраняют прежний барьер при setup/rollback и повторном SIGKILL. Baseline реального клиента пропускал 14 IPv4 + 13 IPv6 UDP-проб; fixed — 0. 2057 Linux + 39 privileged + 8 lifecycle; 14 runtime checks; 17/17 cases, 339 assertions PASS. D04 IN_PROGRESS: routes, legacy global DNS/persistent TUN и полная mixed firewall матрица открыты.

D04/D09: [Q25-F099 — атрибуты владения маршрутом](../reports/AUDIT-Q25-ROUTE-ATTRIBUTES.md): пригодность чужого маршрута отделена от delete/replace authority; неявные protocol/metric/source и дополнительные атрибуты проверяются. Baseline удалял 10 операторских замен на ядре и static bypass настоящего клиента. 2068 Linux + 40 privileged + 8 lifecycle; 17/17 cases, 384 assertions PASS. На этом этапе persistent client route journal ещё не был реализован; продолжение Q25-F100 ниже. D04 IN_PROGRESS.

D04/D09: [Q25-F100 — постоянный журнал физических маршрутов](../reports/AUDIT-Q25-ROUTE-JOURNAL.md): durable intent/confirmed ownership, boot/cookie/TUN scope, общая блокировка и terminal roaming при I/O ошибке. Baseline оставлял bypass/blackhole после SIGKILL → reconnect → stop (3 FAIL). 2087 Linux + 43 privileged + 8 lifecycle; 17/17 cases, 489 assertions PASS. Client physical route recovery закрыт в описанных пределах; legacy global DNS, live persistent TUN и mixed firewall остаются D04 IN_PROGRESS.

D04/D05/D09: [Q25-F101 — legacy global DNS](../reports/AUDIT-Q25-LEGACY-DNS.md): unsafe автоматический replay и PID refcount удалены; снимок/holders требуют ручного восстановления без чтения содержимого и ожидания lock. Baseline изменял resolver в 4 сценариях; новый контракт 47/47 PASS. 2078 Linux + 43 privileged + 8 lifecycle; 17/17 cases, 489 assertions PASS. Старое глобальное восстановление закрыто безопасным отказом; D04 IN_PROGRESS — live persistent TUN и mixed firewall остаются.

D04/D09: [persistent TUN/TAP после SIGKILL](../reports/AUDIT-Q25-PERSISTENT-TUN.md): подтверждён безопасный отказ без изменения интерфейса/routes/DNS/firewall и восстановление после ручного удаления проверенного остатка. 17/17 строк, 506 основных утверждений; 17 persistent-сценариев с 199 подробными проверками PASS. Новый дефект не обнаружен, Rust не изменён. Эта часть D04 закрыта в описанных пределах; D04 IN_PROGRESS — полная mixed firewall матрица остаётся.

D04/D09/D10: [серверный mixed nft/legacy/firewalld recovery](../reports/AUDIT-Q14-MIXED-FIREWALL.md): 16/16 сценариев, 476 проверок PASS. Реальная смена backend каждого семейства, native nft parse errors, firewalld reload, partial cleanup и ручное восстановление проверены. Неопределённое отсутствие сохраняет журнал; потерянный WAN sysctl witness остаётся ручной границей D02. Rust не изменён. D04 IN_PROGRESS: mixed firewall packet/recovery для клиентского kill-switch/DNS/routes ещё требуется.

D04 закрыт: [Q25-F102 и клиентская mixed firewall матрица](../reports/AUDIT-Q25-CLIENT-MIXED-FIREWALL.md): 152/152 сетевые ячейки, 136 SIGKILL/recovery, 4880 основных утверждений и 3224 вложенных проверок PASS. Все 4352 прямых UDP-попыток при защите заблокированы; 2624 разрешённых проб получили ответ. Общий распознаватель исправлен для точного legacy advisory; серверные 16/16, 476 checks повторно PASS. Ручные границы persistent TUN/sysctl/legacy DNS сохранены. **Итого техдолг: 4/15 DONE (26,7%), 9 IN_PROGRESS, 2 TODO.** Это не завершение разделов полного аудита; D05/D06 и D09/D10/D13 остаются открытыми.

D05/D09: [Q25-F103 — общий DNS/NSS и остановка](../reports/AUDIT-Q25-SYSTEM-RESOLVER.md): четыре незавершённых вызова, deadline с очередью, сохранение слота после отмены и отсутствие ожидания blocking pool при shutdown. 4 baseline отказа и 4 fixed PASS; 38/38 hostname cells, 34 crash/recovery, 1220 основных и 806 вложенных checks PASS. 1537 host + 71 config; 2089 Linux + 44 privileged + 8 lifecycle PASS. D05 остаётся IN_PROGRESS: scheduler isolation сетевых мутаций, внутренние locks/I/O и цельный NetworkPlan/shutdown. **Техдолг: 4/15 DONE (26,7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F104 — resolver-файлы до firewall](../reports/AUDIT-Q25-RESOLVER-FILES.md): один ограниченный снимок, общий reader/parser со stub, точный keyword, комментарии и сохранение scope. 7 baseline/fixed пар; 2 старых зависания, все 7 fixed очищены. 38/38 cells, 34 crash/recovery, 1220 основных и 806 вложенных checks PASS. 1544 host + 71 config; 2098 Linux + 44 privileged + 8 lifecycle PASS. D05 остаётся IN_PROGRESS: сетевые мутации, внутренние locks/I/O и общий NetworkPlan/shutdown. **Техдолг: 4/15 DONE (26,7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F105 — применение NetworkPlan вне async-потока](../reports/AUDIT-Q25-NETWORK-TASK.md): отдельный поток сохраняет ownership и исходный NET/mount-контекст до принятия результата или завершения отката; native ACK использует async sleep. 7 новых переносимых + 1 Linux + 1 privileged регрессия; контрольный синхронный helper FAIL, исправленный PASS. Реальные TCP/UDP × TUN-create/ip-up: 4/4 PASS с отзывчивым однопоточным runtime, ожиданием отката и точным восстановлением сети. 38/38 cells, 34 crash/recovery, 1220 основных и 806 вложенных checks; 1551 host + 71 config; 2106 Linux + 45 privileged + 8 lifecycle PASS. D05 остаётся IN_PROGRESS: штатная очистка активного туннеля, kill-switch mutations, locks/I/O/диагностика и общий NetworkPlan/shutdown deadline. Принудительный Drop может блокировать поток до join. **Техдолг: 4/15 DONE (26,7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F106 — штатная очистка установленного туннеля](../reports/AUDIT-Q25-TUN-TEARDOWN.md): общий TCP/UDP TunGuard shutdown сохраняет DNS → pump join → routes/forwarding и выполняет сетевую очистку в одном присоединяемом потоке. Worker failures входят в sticky Failures. 5 новых переносимых + 1 privileged тест; baseline TCP/UDP дали 0 heartbeat тиков при задержке cleanup, fixed — 7–8. 4/4 fixed сценария и 2/2 повторных явных запуска после отказа PASS; kill-switch при ошибке сохранён. 38/38 cells, 34 crash/recovery, 1220 основных и 806 вложенных checks; 1556 host + 71 config; 2111 Linux + 46 privileged + 8 lifecycle PASS. D05 остаётся IN_PROGRESS: ранние error/Drop-пути, kill-switch mutations, locks/I/O/диагностика и общий NetworkPlan/shutdown deadline. **Техдолг: 4/15 DONE (26,7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F107/F108 — firewall workers и сохранение DROP](../reports/AUDIT-Q25-FIREWALL-TASK.md): setup/refresh и все шесть терминальных cleanup-путей ждут владеющий worker; неподтверждённый unhook запрещает очистку цепочки. 8 новых регрессий, 8 baseline + 12 fixed runtime-сценариев; baseline пропустил 6 UDP-проб после отказа cleanup, fixed — 0. 38/38 cells, 34 crash/recovery, 1220 основных + 806 вложенных checks; 1564 host + 71 config; 2119 Linux + 46 privileged + 8 lifecycle PASS. Исходный wildcard UDP recovery FAIL сохранён: повтор с явным bind прошёл, multi-IP wildcard остаётся D06/D10. D05 открыт: startup recovery, ранний Drop, locks/I/O/диагностика, общий срок. **Техдолг: 4/15 DONE (26,7%), 9 IN_PROGRESS, 2 TODO.**

D06/D09/D10: [Q15-F002 — адрес ответа UDP wildcard](../reports/AUDIT-Q15-UDP-LOCAL-ADDRESS.md): pktinfo сохраняется от receive до immutable reply/roaming/PMTU path. Baseline — второй IPv4 адрес не подключается, 96 wrong-source replies; fixed — 8/8 подключений IPv4/IPv6 × plain/obfs, 256/256 inner UDP echoes и исходный refresh-fault recovery PASS. 6 новых Linux + 1 privileged регрессия; 1564 host + 71 config; 2125 Linux + 47 privileged + 8 lifecycle; 38/38 cells, 34 crash/recovery, 1220 + 806 checks PASS. Wildcard defect закрыт в границах отчёта, полные D06/D10 и D05 открыты. **Техдолг: 4/15 DONE (26,7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F109 — startup recovery в joined worker](../reports/AUDIT-Q25-STARTUP-RECOVERY-TASK.md): lease → routes → DNS, stop ждёт результат и сохраняет ошибку; успешный stop не начинает подключение. 3 новые Linux-регрессии, 2 baseline + 6 fixed runtime; baseline heartbeat 0, fixed 7–8, конкурентные claims исключены; stale DNS marker удалён, live/busy/foreign/legacy сохранены. 1564 host + 71 config; 2128 Linux + 47 privileged + 8 lifecycle; 38/38 cells, 34 crash/recovery, 1220 + 806 checks PASS. D05 открыт: ранние error/Drop, locks/I/O/диагностика, общий deadline. **Техдолг: 4/15 DONE (26,7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F110 — запуск pump и ранний откат](../reports/AUDIT-Q25-PUMP-START.md): общий Linux worker владеет guard/fd при fcntl/thread failure, partial reader join предшествует освобождению TUN; recordizer/budget checks перенесены до platform apply. 4 baseline + 8 fixed runtime, 4 cleanup faults + 4 recovery PASS; heartbeat 0 → 7–8. 1564 host + 71 config; 2128 Linux + 47 privileged + 8 lifecycle; 38/38 cells, 34 crash/recovery, 1220 + 806 checks PASS. D05 открыт: оставшиеся ранние пути, Drop fallback, locks/I/O/диагностика и общий deadline. **Техдолг: 4/15 DONE (26,7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F111 — последовательный writer диагностики](../reports/AUDIT-Q25-STATUS-WRITER.md): один поток, один ожидающий снимок, join итоговой записи; файловый I/O вне async-потока. 5 новых portable + 1 privileged тест; 2 baseline + 4 fixed fsync-сценария, 2 baseline + 4 fixed TCP/UDP teardown и 2 recovery PASS. 1569 host + 71 config; 2133 Linux + 48 privileged + 8 lifecycle PASS. D05 открыт: остальные locks/I/O, ранний Drop и общий deadline. **Техдолг: 4/15 DONE (26,7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F112/F113 — файлы идентичности](../reports/AUDIT-Q25-IDENTITY-FILES.md): ID загружается один раз в joined worker, временный ID стабилен при reconnect; TOFU ограничен 1 MiB, повреждение/конфликт пинов запрещает новое доверие, запись атомарна. 15 новых тестов; 8 baseline + 8 fixed identity cases, 6 teardown cases и 2 recovery PASS. 1575 host + 71 config; 2148 Linux + 48 privileged + 8 lifecycle PASS. D05 открыт: синхронный TOFU, другие startup I/O/Drop и общий deadline. **Техдолг: 4/15 DONE (26,7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F114 — TOFU worker](../reports/AUDIT-Q25-IDENTITY-WORKER.md): файлы доверия обрабатываются в одном присоединяемом потоке; отмена и timeout не оставляют запись без владельца, поздний отказ сохраняется до terminal result. 9 portable regressions; 16 worker cases + 16 файловых + 6 teardown и 2 recovery PASS. 1584 host + 71 config; 2157 Linux + 48 privileged + 8 lifecycle PASS. Общий deadline и другие startup I/O/Drop остаются D05. **Техдолг: 4/15 DONE (26,7%), 9 IN_PROGRESS, 2 TODO.**

**4 октября, HTTP/WS read batch PASS:** [Q12](../reports/AUDIT-Q12-TRANSPORTS.md): 6 исправлений,9 baseline FAIL,11 новых тестов,2335 Linux PASS,40 live probes+63 transport assertions,request-head ASan/libFuzzer,свежие matrix/soak/четыре native A/B PASS. На момент read-пакета Close/control lifecycle и wire-матрица оставались открытыми; тогда Q12 IN_PROGRESS,план11/37 (29,7%).
