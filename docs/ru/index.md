# Документация qeli — карта

Документация организована **по типам документов**. Русское и английское деревья имеют
одинаковую структуру, а каждый актуальный документ доступен из этой карты.

> Новичку: начните с **[Установки с нуля](manuals/GETTING-STARTED.md)**, затем откройте
> **[Конфигурацию](manuals/CONFIG.md)**. Если что-то не работает —
> **[Диагностика](manuals/TROUBLESHOOTING.md)**.

**English version → [../eng/index.md](../eng/index.md)**

## Обзор

| Документ | О чём |
|---|---|
| [README.md](README.md) | Обзор проекта: назначение, wire-режимы, криптостек и состав репозитория |

## Руководства (`manuals/`)

Практические инструкции по установке, настройке и эксплуатации.

| Документ | О чём |
|---|---|
| [GETTING-STARTED.md](manuals/GETTING-STARTED.md) | Установка и первый запуск, пошагово с нуля |
| [CONFIG.md](manuals/CONFIG.md) | Полный справочник flat-INI конфигурации сервера и клиентов |
| [OPERATIONS.md](manuals/OPERATIONS.md) | Совместимость, обновление, откат, резервное копирование и firewall |
| [PANEL.md](manuals/PANEL.md) | Установка и использование веб-панели |
| [IPV6.md](manuals/IPV6.md) | IPv4/IPv6/dual-stack, `off/manual/route/nat66`, NDP proxy и диагностика |
| [OBFUSCATION.md](manuals/OBFUSCATION.md) | Recordizer, совместимость слоёв маскировки и профили тюнинга |
| [TROUBLESHOOTING.md](manuals/TROUBLESHOOTING.md) | Диагностика подключения и справочник ошибок |
| [KEENETIC-DEPLOY.md](manuals/KEENETIC-DEPLOY.md) | Пошаговый деплой клиента на Keenetic |

## Справочники и архитектура (`reference/`)

Технические контракты и описание текущей реализации.

| Документ | О чём |
|---|---|
| [CLIENT-CONFIG-MATRIX.md](reference/CLIENT-CONFIG-MATRIX.md) | Актуальный контракт клиентских ключей по платформам и история миграции |
| [THREAT-MODEL.md](reference/THREAT-MODEL.md) | Модель угроз, границы доверия и уровень проверенности |
| [TRANSPORT-CORE.md](reference/TRANSPORT-CORE.md) | Общее транспортное Rust-ядро, source/ABI-контракт и release gates |
| [KEENETIC-PORT.md](reference/KEENETIC-PORT.md) | Архитектура порта Keenetic и обоснование dual-arch сборки |

## Планы (`plans/`)

Актуальные направления разработки и планы реализации. Это не пользовательские инструкции.

| Документ | О чём |
|---|---|
| [ROADMAP.md](plans/ROADMAP.md) | Продуктовый и технический план развития |
| [ROAMING.md](plans/ROAMING.md) | Нормативный план реализации клиентского роуминга |
| [IPV6-IMPLEMENTATION-PLAN.md](plans/IPV6-IMPLEMENTATION-PLAN.md) | Архитектура IPv6, этапы и release gates |
| [CLIENT-CONFIG-CORE.md](plans/CLIENT-CONFIG-CORE.md) | Единый INI/URI API в Rust-ядре, удаление клиентских дублей и оставшиеся проверки |
| [FULL-SYSTEM-AUDIT.md](plans/FULL-SYSTEM-AUDIT.md) | История аудитов, 37 разделов полного тестового плана, стенды и прогресс |
| [AUDIT-DEBT.md](plans/AUDIT-DEBT.md) | Реестр обязательных исправлений и проверок до новых разделов аудита |

## Отчёты (`reports/`)

Актуальные анализы и результаты измерений. Датированные зафиксированные отчёты находятся в архиве.

| Документ | О чём |
|---|---|
| [AUDIT-Q02-CLIENT-PARSERS.md](reports/AUDIT-Q02-CLIENT-PARSERS.md) | INI/URI и редакторы: 19 находок, общий корпус, тесты Rust/C#/Kotlin и ограничения Swift |
| [AUDIT-Q03-PANEL-STATE.md](reports/AUDIT-Q03-PANEL-STATE.md) | Панель: безопасная загрузка политики и canonical defaults, browser RU/EN и границы проверок |
| [AUDIT-Q19-Q22-NETWORK-PLAN.md](reports/AUDIT-Q19-Q22-NETWORK-PLAN.md) | Общий DNS-план, legacy/v2, CIDR-исключения: исправления, регрессии и границы проверки |
| [AUDIT-Q19-DNS-PROXY.md](reports/AUDIT-Q19-DNS-PROXY.md) | Серверный DNS: CNAME/NODATA, сжатые имена, TCP failover и локальные сетевые тесты |
| [AUDIT-Q19-DNS-CACHE.md](reports/AUDIT-Q19-DNS-CACHE.md) | Лимит памяти DNS-кеша, пересылка TSIG/SIG(0) и проверка запросов |
| [AUDIT-Q19-DNS-EDNS.md](reports/AUDIT-Q19-DNS-EDNS.md) | EDNS, проверка записей, общий TTL ответа и тесты IPv6 upstream |
| [AUDIT-Q14-HOOKS.md](reports/AUDIT-Q14-HOOKS.md) | Ограничение stdout/stderr, timeout/cancellation и потомки lifecycle hooks |
| [AUDIT-Q14-Q15-WORKER-USAGE.md](reports/AUDIT-Q14-Q15-WORKER-USAGE.md) | Владение службами worker, финальное сохранение и учёт коротких сессий |
| [AUDIT-Q14-Q32-NOTIFICATIONS.md](reports/AUDIT-Q14-Q32-NOTIFICATIONS.md) | Ограничение отправок уведомлений, тесты панели и завершение задач |
| [AUDIT-Q14-Q33-CONFIG-TRUST.md](reports/AUDIT-Q14-Q33-CONFIG-TRUST.md) | Доверие прочитанному конфигу, гонки файлов и очистка поколения |
| [AUDIT-Q25-CREDENTIAL-COMMANDS.md](reports/AUDIT-Q25-CREDENTIAL-COMMANDS.md) | Лимиты password_command, ошибки без секретов, ранний stop и изоляция features |
| [AUDIT-Q25-PASSWORD-FILES.md](reports/AUDIT-Q25-PASSWORD-FILES.md) | Лимиты файлов пароля, общий буфер секрета и финальный статус клиента |
| [AUDIT-Q25-NETWORK-CLEANUP.md](reports/AUDIT-Q25-NETWORK-CLEANUP.md) | Сохранение kill-switch при ошибке очистки forwarding |
| [AUDIT-Q25-CORE-LIFECYCLE.md](reports/AUDIT-Q25-CORE-LIFECYCLE.md) | Ошибки запуска/остановки ядра, терминальные hooks и сохранение kill-switch |
| [AUDIT-Q25-DNS-RECOVERY.md](reports/AUDIT-Q25-DNS-RECOVERY.md) | Восстановление старого DNS: проверка операций и сохранение снимка |
| [AUDIT-Q25-TUN-CLEANUP.md](reports/AUDIT-Q25-TUN-CLEANUP.md) | Ошибки очистки TUN/DNS/маршрутов, владение планом и сохранение terminal kick |
| [AUDIT-Q14-OWNED-SHUTDOWN.md](reports/AUDIT-Q14-OWNED-SHUTDOWN.md) | Итоговая проверка DNS/IPv6 sysctl leases и передача ошибок worker/supervisor; Q14-F027 исправлена частично |
| [AUDIT-Q14-RETAINED-CLEANUP.md](reports/AUDIT-Q14-RETAINED-CLEANUP.md) | Точные NAT-правила, отказ старого поколения и подтверждённый Linux lifecycle |
| [AUDIT-Q14-PROFILE-SHUTDOWN.md](reports/AUDIT-Q14-PROFILE-SHUTDOWN.md) | Ошибки задач профиля, TUN queue timeout/panic и удаления TUN в результате остановки; Q14-F027 частично |
| [AUDIT-Q14-SYSCTL-RECOVERY.md](reports/AUDIT-Q14-SYSCTL-RECOVERY.md) | Q14-F029/F030: ошибки восстановления sysctl и сохранение прежнего владельца при повторном acquire |
| [AUDIT-Q14-IPV6-PARTIAL-ACQUIRE.md](reports/AUDIT-Q14-IPV6-PARTIAL-ACQUIRE.md) | Q14-F031: учёт частичного IPv6 acquire и повторный rollback до подтверждённого освобождения |
| [AUDIT-Q05-PREFLIGHT.md](reports/AUDIT-Q05-PREFLIGHT.md) | Q05-F001: ограничения команд preflight и проверка частичного IPv4/IPv6 snapshot |
| [AUDIT-Q05-PANEL-TRANSACTIONS.md](reports/AUDIT-Q05-PANEL-TRANSACTIONS.md) | Async preflight, сроки ожидания config lock и отмена backup/restore |
| [AUDIT-Q05-ARCHIVE-BUDGET.md](reports/AUDIT-Q05-ARCHIVE-BUDGET.md) | Бюджет backup/restore, bounded stdin и полнота rollback snapshot |
| [AUDIT-Q05-HEALTH-PROBES.md](reports/AUDIT-Q05-HEALTH-PROBES.md) | Async-проверки Status/Transport health, общий admission и отзывчивость HTTP-роутера |
| [AUDIT-Q14-NAT-COMMANDS.md](reports/AUDIT-Q14-NAT-COMMANDS.md) | Q14-F032: серверный NAT использует общий runner со сроком и лимитом вывода; ownership после timeout |
| [AUDIT-Q14-NAT-CLEANUP-BUDGET.md](reports/AUDIT-Q14-NAT-CLEANUP-BUDGET.md) | Общий срок очистки NAT, DNS и сохранение неподтверждённых правил |
| [AUDIT-Q14-DNS-INPUT-BUDGET.md](reports/AUDIT-Q14-DNS-INPUT-BUDGET.md) | Сроки DNS INPUT lease и неблокирующее завершение поколения |
| [AUDIT-Q14-NAT-SETUP-BUDGET.md](reports/AUDIT-Q14-NAT-SETUP-BUDGET.md) | Срок установки NAT/forwarding и точного отката |
| [AUDIT-Q14-DNS-OWNERSHIP.md](reports/AUDIT-Q14-DNS-OWNERSHIP.md) | Сохранение DNS rule specs при отказе cleanup/rollback, retry и идентичность поколения |
| [AUDIT-Q14-Q25-FIREWALL-CHECKS.md](reports/AUDIT-Q14-Q25-FIREWALL-CHECKS.md) | Общий разбор firewall-проверок сервера/клиента, точечная очистка DNS и граница 1024 правил |
| [AUDIT-Q14-NAT-CLEANUP.md](reports/AUDIT-Q14-NAT-CLEANUP.md) | Конечная очистка NAT, проверка результата, диагностика и открытые ошибки teardown |
| [AUDIT-Q25-ROUTE-OWNERSHIP.md](reports/AUDIT-Q25-ROUTE-OWNERSHIP.md) | Q25-F025/F026: сохранение заменённых маршрутов и проверка cleanup перед сбросом ownership |
| [AUDIT-Q25-TUNNEL-ROUTES.md](reports/AUDIT-Q25-TUNNEL-ROUTES.md) | Q25-F037–F039: общий TUN/TAP installer, строгий route_local и удаление старых парсеров |
| [AUDIT-Q25-GATEWAY-ROLLBACK.md](reports/AUDIT-Q25-GATEWAY-ROLLBACK.md) | Q25-F040–F042: владение gateway, частичный откат и проверки kill-switch |
| [AUDIT-Q25-GATEWAY-BUDGET.md](reports/AUDIT-Q25-GATEWAY-BUDGET.md) | Общий срок gateway/exit-node и сохранённый rollback |
| [AUDIT-Q25-ROUTE-BUDGET.md](reports/AUDIT-Q25-ROUTE-BUDGET.md) | Общий срок route-транзакций и отдельный verified rollback |
| [AUDIT-Q25-EXIT-OWNERSHIP.md](reports/AUDIT-Q25-EXIT-OWNERSHIP.md) | Q25-F043–F045: независимый exit NAT и допуск конфликтующих kill-switch |
| [AUDIT-Q25-KILL-SWITCH-LIFETIME.md](reports/AUDIT-Q25-KILL-SWITCH-LIFETIME.md) | Q25-F046–F047: lifetime lease Linux kill-switch и fail-closed IPv6 |
| [AUDIT-Q25-CLIENT-NAMESPACE.md](reports/AUDIT-Q25-CLIENT-NAMESPACE.md) | Q25-F048–F049: отключённый IPv6 и общее резервирование клиентского TUN |
| [AUDIT-Q25-SYSCTL-OWNER-EVIDENCE.md](reports/AUDIT-Q25-SYSCTL-OWNER-EVIDENCE.md) | Q25-F050–F051: проверка владельцев sysctl и сохранение незавершённого восстановления |
| [AUDIT-Q25-SYSCTL-JOURNAL-IO.md](reports/AUDIT-Q25-SYSCTL-JOURNAL-IO.md) | Ограниченное чтение journal по fd, FIFO-lock и deadline ожидания sysctl |
| [AUDIT-Q25-SYSCTL-CONTEXT-IO.md](reports/AUDIT-Q25-SYSCTL-CONTEXT-IO.md) | Namespace на границах PID/sysctl I/O и persistence; сохранение evidence после смены контекста |
| [AUDIT-Q25-ATOMIC-STATE.md](reports/AUDIT-Q25-ATOMIC-STATE.md) | Cleanup временных файлов, directory fsync и неопределённый результат публикации |
| [AUDIT-Q25-STATE-DIRECTORY.md](reports/AUDIT-Q25-STATE-DIRECTORY.md) | Доверенный каталог sysctl по fd, root/User=qeli и замена общего lock во время ожидания |
| [AUDIT-Q25-NAMESPACE-PIN.md](reports/AUDIT-Q25-NAMESPACE-PIN.md) | Удержание network/PID/time namespace fd через lock waits и sysctl I/O |
| [AUDIT-Q25-NAMESPACE-GENERATION.md](reports/AUDIT-Q25-NAMESPACE-GENERATION.md) | Поколение network namespace, журнал v4 и закрытие D02 |
| [AUDIT-Q25-SYSCTL-TARGET.md](reports/AUDIT-Q25-SYSCTL-TARGET.md) | Исходный sysctl fd, отказ при rename/replacement/crash и миграция журнала v3 |
| [AUDIT-Q25-DNS-BUDGET.md](reports/AUDIT-Q25-DNS-BUDGET.md) | Общий срок применения DNS и сохранение lease для отдельного rollback |
| [AUDIT-Q25-RESOLVER-CONFIG.md](reports/AUDIT-Q25-RESOLVER-CONFIG.md) | Строгая проверка resolver-конфига и bounded чтение |
| [AUDIT-Q25-RESOLVER-CONTEXT.md](reports/AUDIT-Q25-RESOLVER-CONTEXT.md) | Контекст D-Bus/resolved, прямые вызовы и DNS-порт |
| [AUDIT-Q34-ANDROID-RUNTIME.md](reports/AUDIT-Q34-ANDROID-RUNTIME.md) | Свежий Android JNI, исправление cargo-ndk и 154 JVM + 6 emulator tests |
| [AUDIT-Q34-LINUX-MATRIX.md](reports/AUDIT-Q34-LINUX-MATRIX.md) | Linux: матрица пакетов и RSS soak |
| [AUDIT-Q34-RELEASE-SOAK.md](reports/AUDIT-Q34-RELEASE-SOAK.md) | Память release TCP/UDP при 100 переключениях |
| [AUDIT-Q25-KILL-SWITCH-IDENTITY.md](reports/AUDIT-Q25-KILL-SWITCH-IDENTITY.md) | Владелец namespace, защита reconnect и точная очистка семейств |
| [AUDIT-Q25-KILL-SWITCH-BUDGET.md](reports/AUDIT-Q25-KILL-SWITCH-BUDGET.md) | Общий срок отключения kill-switch, частичная очистка и безопасный повтор |
| [AUDIT-Q25-KILL-SWITCH-REFRESH.md](reports/AUDIT-Q25-KILL-SWITCH-REFRESH.md) | Общий срок refresh и запрет вставки при unknown inspection |
| [AUDIT-Q25-KILL-SWITCH-SETUP.md](reports/AUDIT-Q25-KILL-SWITCH-SETUP.md) | Общий срок установки kill-switch и проверяемый откат |
| [AUDIT-Q25-LINK-OBSERVATION.md](reports/AUDIT-Q25-LINK-OBSERVATION.md) | Общие сведения об интерфейсе текущего namespace: NDP, TAP, hooks, sysctl и панель |
| [AUDIT-Q25-SYSCTL-NAMESPACE.md](reports/AUDIT-Q25-SYSCTL-NAMESPACE.md) | Q25-F052–F053: изоляция sysctl по namespace и миграция журнала v2 |
| [AUDIT-Q25-TUN-ADMISSION.md](reports/AUDIT-Q25-TUN-ADMISSION.md) | Q25-F054–F056: пассивное ожидание TUN и эксклюзивное создание очередей |
| [AUDIT-Q25-TUN-ATTACH.md](reports/AUDIT-Q25-TUN-ATTACH.md) | Q25-F057–F058: запрет создания при attach и сохранение формата TUN |
| [AUDIT-Q25-TUN-LIFETIME.md](reports/AUDIT-Q25-TUN-LIFETIME.md) | Q25-F059–F060: сохранение исходных fd TUN до завершения очистки |
| [AUDIT-Q25-DNS-LEASES.md](reports/AUDIT-Q25-DNS-LEASES.md) | Q25-F061–F062: владение DNS поколением и identity исходного fd |
| [AUDIT-Q25-ROUTE-IDENTITY.md](reports/AUDIT-Q25-ROUTE-IDENTITY.md) | Q25-F063–F064: проверка исходного TUN/namespace перед очисткой маршрутов |
| [AUDIT-Q25-SETUP-IDENTITY.md](reports/AUDIT-Q25-SETUP-IDENTITY.md) | Q25-F065–F066: исходный TUN при setup/roaming и терминальный отказ при потере identity |
| [AUDIT-Q25-GATEWAY-IDENTITY.md](reports/AUDIT-Q25-GATEWAY-IDENTITY.md) | Q25-F067–F068: владение gateway, проверки namespace/TUN и cleanup до закрытия fd |
| [AUDIT-Q25-CLIENT-COMMANDS.md](reports/AUDIT-Q25-CLIENT-COMMANDS.md) | Q25-F035/F036: пределы route/firewall-команд и защита при неизвестном IPv4-пути |
| [AUDIT-Q25-SETUP-FLUSH.md](reports/AUDIT-Q25-SETUP-FLUSH.md) | Q25-F033/F034: общий initial setup и подтверждение IPv4/IPv6 flush |
| [AUDIT-Q25-ROUTE-PENDING.md](reports/AUDIT-Q25-ROUTE-PENDING.md) | Q25-F031/F032: учёт неизвестных операций и освобождение отсутствующих orphan-маршрутов |
| [AUDIT-Q25-ROUTE-POSTCONDITIONS.md](reports/AUDIT-Q25-ROUTE-POSTCONDITIONS.md) | Q25-F029/F030: проверка удаления и восстановления carrier-маршрутов |
| [AUDIT-Q25-ROUTE-SCOPE.md](reports/AUDIT-Q25-ROUTE-SCOPE.md) | Q25-F027/F028: изоляция route journal и запрет commit после начала очистки |
| [AUDIT-Q25-ROUTE-OUTCOME.md](reports/AUDIT-Q25-ROUTE-OUTCOME.md) | Q25-F023/F024: проверка неуспешной мутации маршрута и отказ при неоднозначном снимке |
| [AUDIT-Q25-GATEWAY-WAN.md](reports/AUDIT-Q25-GATEWAY-WAN.md) | Q25-F021/F022: ограничение WAN-запросов и очистка сохранённых интерфейсов без лишнего discovery |
| [AUDIT-Q25-PATH-MONITOR.md](reports/AUDIT-Q25-PATH-MONITOR.md) | Q25-F020: ограниченные read-only команды Linux-монитора и ожидание child при stop |
| [AUDIT-Q25-SYSTEM-COMMANDS.md](reports/AUDIT-Q25-SYSTEM-COMMANDS.md) | Сроки и лимиты вывода команд TUN/resolvectl, завершение процессов и DNS marker |
| [AUDIT-Q25-TCP-TASKS.md](reports/AUDIT-Q25-TCP-TASKS.md) | Владение TCP-задачами, закрытие spawn и ожидание Linux path workers |
| [AUDIT-Q25-UDP-TASKS.md](reports/AUDIT-Q25-UDP-TASKS.md) | Владение UDP-задачами, передача пути и ожидание перед rollback |
| [AUDIT-Q25-TUN-WORKERS.md](reports/AUDIT-Q25-TUN-WORKERS.md) | Общее владение потоками TUN/Wintun при отмене shutdown |
| [AUDIT-Q25-H2-TASKS.md](reports/AUDIT-Q25-H2-TASKS.md) | Владение H2 driver/bridge от connect до завершения TCP-поколения |
| [AUDIT-Q14-H2-TASKS.md](reports/AUDIT-Q14-H2-TASKS.md) | H2-задачи серверного профиля, join перед teardown и удержание pre-auth при отказе |
| [AUDIT-Q14-CONTROL.md](reports/AUDIT-Q14-CONTROL.md) | Владение control socket, границы API, shutdown handlers и парность hooks |
| [AUDIT-Q14-WORKER-NETWORK-LEASE.md](reports/AUDIT-Q14-WORKER-NETWORK-LEASE.md) | Один server worker на network namespace, crash/restart и удалённый профиль |
| [AUDIT-Q14-FIREWALL-JOURNAL.md](reports/AUDIT-Q14-FIREWALL-JOURNAL.md) | Точный журнал server firewall, SIGKILL и recovery без listing |
| [AUDIT-Q25-DNS-MARKER-STORAGE.md](reports/AUDIT-Q25-DNS-MARKER-STORAGE.md) | Доверенное DNS state, namespace cookie v2 и SIGKILL/restart |
| [AUDIT-Q25-KILL-SWITCH-REBUILD.md](reports/AUDIT-Q25-KILL-SWITCH-REBUILD.md) | Защита kill-switch при SIGKILL, отказах перестройки и retry |
| [AUDIT-Q14-SUPERVISOR.md](reports/AUDIT-Q14-SUPERVISOR.md) | Supervisor: stop/retry, владение Child/PID, команды и deadline завершения |
| [AUDIT-Q14-Q19-LIFECYCLE.md](reports/AUDIT-Q14-Q19-LIFECYCLE.md) | Завершение профиля, ранние ошибки запуска, DNS-слушатели и освобождение сокетов |
| [AUDIT-Q01-SERVER-INI.md](reports/AUDIT-Q01-SERVER-INI.md) | Первый проход серверного INI: 7 находок, исправления, тесты и ограничения |
| [AUDIT.md](reports/AUDIT.md) | Актуальная модель безопасности и статус аудита |
| [DPI-AUDIT.md](reports/DPI-AUDIT.md) | Анализ обнаружимости DPI и меры устранения |
| [BENCHMARK.md](reports/BENCHMARK.md) | Методика нагрузочного тестирования и замеры по режимам |
| [Qeli 0.8.0: 34 VPN-режима](reports/benchmarks/vpn_protocol_benchmark_repeat_2026-09-01.md) | Полный датированный сравнительный прогон, CPU/RSS и ограничения интерпретации |
| [COMPARISON.md](reports/COMPARISON.md) | Сравнение с WireGuard, OpenVPN и V2Ray |

## Архив (`archive/`)

Зафиксированные исторические документы сохранены для прослеживаемости и не обновляются как
актуальные инструкции. Начните с **[карты архива](archive/README.md)**.

### Завершённые планы и design logs

| Документ | Зафиксированный контекст |
|---|---|
| [REFACTOR-PLAN.md](archive/plans/REFACTOR-PLAN.md) | Завершённый план и журнал устранения production-дублей |
| [DESIGN-remaining.md](archive/plans/DESIGN-remaining.md) | Снимок разработки REALITY от июня 2026 |
| [RELEASE-FIXES.md](archive/plans/RELEASE-FIXES.md) | Исторический план стабилизации ранних pre-1.0 релизов |

### Исторические аудиты

| Документ | Дата |
|---|---|
| [AUDIT-2026-06-10.md](archive/audits/AUDIT-2026-06-10.md) | 2026-06-10 — аудит безопасности и надёжности |
| [AUDIT-2026-06-11.md](archive/audits/AUDIT-2026-06-11.md) | 2026-06-11 — разбор внешнего аудита и исправления |
| [AUDIT-2026-06-11-external2.md](archive/audits/AUDIT-2026-06-11-external2.md) | 2026-06-11 — разбор второго внешнего аудита |
| [AUDIT-2026-06-12.md](archive/audits/AUDIT-2026-06-12.md) | 2026-06-12 — аудит и исправления для 0.7.1 |

## Документация клиентов (рядом с кодом)

| Клиент | Документ |
|---|---|
| Windows | [qeli-win/README.md](../../qeli-win/README.md) |
| macOS | [qeli-mac/README.md](../../qeli-mac/README.md) |
| iOS ⚠️ | [qeli-ios/README.md](../../qeli-ios/README.md) · MDM: [qeli-ios/MDM/README.md](../../qeli-ios/MDM/README.md) — реализован полностью, но **на устройстве не проверялся** и не выпускается |
| Роутеры (OpenWrt) | [qeli-openwrt/README.md](../../qeli-openwrt/README.md) · Keenetic: [KEENETIC-DEPLOY.md](manuals/KEENETIC-DEPLOY.md) |
| Android | [qeli-android/README.md](../../qeli-android/README.md) |
| Linux CLI | [GETTING-STARTED §8.2](manuals/GETTING-STARTED.md) |

## Вне этого каталога

- **[../../CHANGELOG.md](../../CHANGELOG.md)** — все изменения по версиям.
- **[../../release/RELEASE_NOTES_0.8.1.md](../../release/RELEASE_NOTES_0.8.1.md)** — двуязычное
  описание закрепления архитектуры 0.8, практический результат для пользователей, порядок
  обновления, артефакты и проверка релиза.
- **[../../release/RELEASE_NOTES_0.8.0.md](../../release/RELEASE_NOTES_0.8.0.md)** — dev-миграция
  Reality/H2, значения по умолчанию, порядок обновления и проверка.
- **[../../release/dpi_audit_dev_0.8.0_h2_2026-08-26/REPORT.md](../../release/dpi_audit_dev_0.8.0_h2_2026-08-26/REPORT.md)** — датированный H2 PCAP/DPI-результат и ограничения.
- **[../../release/RELEASE_NOTES_0.7.16.md](../../release/RELEASE_NOTES_0.7.16.md)** — двуязычный
  выпускной документ `0.7.16` и влияние обновления.
- **[../../SECURITY.md](../../SECURITY.md)** — политика безопасности и приём отчётов.
- **[../../CONTRIBUTING.md](../../CONTRIBUTING.md)** — как участвовать в разработке.
- **[../../release/docker/README.md](../../release/docker/README.md)** — запуск сервера в Docker.

- [Q25-F099: владение изменёнными маршрутами Linux](reports/AUDIT-Q25-ROUTE-ATTRIBUTES.md).

- [Q25-F100: журнал физических маршрутов и SIGKILL recovery](reports/AUDIT-Q25-ROUTE-JOURNAL.md).

- [Q25-F101: безопасный отказ от старого глобального DNS recovery](reports/AUDIT-Q25-LEGACY-DNS.md).

- [Q25: runtime-проверка persistent TUN/TAP и ручного recovery](reports/AUDIT-Q25-PERSISTENT-TUN.md).

- [Q14: серверное восстановление mixed nft/legacy/firewalld, 16 сценариев](reports/AUDIT-Q14-MIXED-FIREWALL.md).

- [Q25-F102: клиентский mixed nft/legacy/firewalld и crash recovery](reports/AUDIT-Q25-CLIENT-MIXED-FIREWALL.md).
- [Q25-F103: общий DNS/NSS, отмена и остановка клиента](reports/AUDIT-Q25-SYSTEM-RESOLVER.md).

- [Q25-F104: чтение resolver-файлов, общий парсер и DNS-разрешения](reports/AUDIT-Q25-RESOLVER-FILES.md).

- [Q25-F105: асинхронное применение NetworkPlan и владение откатом](reports/AUDIT-Q25-NETWORK-TASK.md).

- [Q25-F106: асинхронная очистка установленного туннеля](reports/AUDIT-Q25-TUN-TEARDOWN.md).

- [Q25-F107/F108: асинхронный firewall и сохранение цепочки при отказе unhook](reports/AUDIT-Q25-FIREWALL-TASK.md).

- [Q15-F002: локальный адрес UDP wildcard](reports/AUDIT-Q15-UDP-LOCAL-ADDRESS.md)

- [Q25-F109: startup recovery, остановка и сохранение сетевого lease](reports/AUDIT-Q25-STARTUP-RECOVERY-TASK.md)

- [Q25-F110: запуск TUN pump и ранний откат в присоединяемом worker](reports/AUDIT-Q25-PUMP-START.md)

- [Q25-F111: последовательная диагностика клиента и ожидание итоговой записи](reports/AUDIT-Q25-STATUS-WRITER.md)

- [Q25-F112/F113: стабильный device-id, ограниченное чтение и целостность TOFU](reports/AUDIT-Q25-IDENTITY-FILES.md)

- [Q25-F114: TOFU worker и сохранение ошибок при отмене](reports/AUDIT-Q25-IDENTITY-WORKER.md)

- [Q25-F115: серверная очистка в присоединяемом worker](reports/AUDIT-Q25-SERVER-CLEANUP-WORKER.md)

- [Q25-F116: TUN/NAT setup серверного профиля вне executor](reports/AUDIT-Q25-SERVER-SETUP-WORKER.md)

- [Q25-F117: DNS firewall серверного профиля вне executor](reports/AUDIT-Q25-SERVER-DNS-SETUP-WORKER.md)

- [Q25-F118: привязка NDP proxy вне executor](reports/AUDIT-Q25-SERVER-NDP-BIND-WORKER.md)

- [Q25-F119: общий бюджет установки профиля и готовность listeners](reports/AUDIT-Q25-SERVER-SETUP-BUDGET.md)

- [Q25-F120: повторная проверка IPv6 WAN при обновлении exit-node](reports/AUDIT-Q25-GATEWAY-IPV6-ROAM.md)

- [Q25-F121: поздний IPv6 не обходит kill-switch](reports/AUDIT-Q25-KILL-SWITCH-DYNAMIC-IPV6.md)

- [Q25-F122: поздний IPv4-маршрут не обходит kill-switch](reports/AUDIT-Q25-KILL-SWITCH-DYNAMIC-IPV4.md)

- [Q25-F123: TUN attach и расхождение network namespace](reports/AUDIT-Q25-TUN-ATTACH-CONTEXT.md)

- [Q25-F124: защита exit-node от утечки через другой WAN](reports/AUDIT-Q25-EXIT-POLICY-ROUTING.md)

- [Q25-A125: повторное использование имени физического WAN](reports/AUDIT-Q25-WAN-NAME-REUSE.md)

- [Q25-F126: выбор WAN по метрике default route](reports/AUDIT-Q25-WAN-METRIC.md)

- [Q25-F127: монитор exit WAN без VPN path COMMIT](reports/AUDIT-Q25-EXIT-WAN-MONITOR.md)

- [Q25-F128: отказ от собственного exit-TUN как WAN](reports/AUDIT-Q25-EXIT-SELF-WAN.md)

- [Q25-F129: неоднозначный ECMP default WAN](reports/AUDIT-Q25-WAN-ECMP.md)

- [D09: итоговая проверка Linux lifecycle и системных отказов](reports/AUDIT-Q25-LINUX-LIFECYCLE-CLOSURE.md)

- [Q25-F130: удержание server worker lease после принудительной отмены](reports/AUDIT-Q25-SERVER-FORCED-DROP-LEASE.md)

- [Q25-F131: проверка наличия WAN при установке серверных правил](reports/AUDIT-Q25-SERVER-WAN-PRESENCE.md)

- [Q25-F132: отказ от неоднозначного auto-WAN на сервере](reports/AUDIT-Q25-SERVER-WAN-ECMP.md)

- [Q25-F133: исправление client-only Linux сборки](reports/AUDIT-Q25-CLIENT-ONLY-BUILD.md)
- [Q25-F134: NAT66 только через выбранный WAN](reports/AUDIT-Q25-SERVER-NAT66-EGRESS.md)
- [Q25-F135: отказ NAT auto-WAN без списка default routes](reports/AUDIT-Q25-SERVER-AUTO-WAN-FAILURE.md)
- [Q25-F136: граница NAT44 для других интерфейсов и приватных LAN](reports/AUDIT-Q25-SERVER-NAT44-EGRESS.md)
- [Q25-F137: отказ SIGHUP без частичного обновления auth](reports/AUDIT-Q25-SERVER-SIGHUP-AUTH.md)
- [Q25-F138: единый предел 16 МиБ для серверного INI](reports/AUDIT-Q25-SERVER-INI-SIZE.md)
- [Q25-F139: живое состояние панели после сохранения INI](reports/AUDIT-Q25-SERVER-WEB-LIVE.md)
- [Q25-F140: приватная запись серверного INI панелью](reports/AUDIT-Q25-SERVER-INI-PERMISSIONS.md)
- [Q25-F141: согласованный допуск CLI, панели и runtime](reports/AUDIT-Q25-SERVER-CHECK-CONFIG-PARITY.md)
- [Q25-F142: имя профиля и путь серверного identity-ключа](reports/AUDIT-Q25-SERVER-IDENTITY-NAME.md)
- [Q25-F143: доверие к identity_key и logging.file](reports/AUDIT-Q25-SERVER-IDENTITY-TRUST.md)
- [Q25-F144: доверие к нестандартному auth.users_file](reports/AUDIT-Q25-SERVER-USERS-PATH-TRUST.md)
- [Q25-F145: SIGHUP и рестарт при смене users_file](reports/AUDIT-Q25-SERVER-USERS-SIGHUP-RESTART.md)
- [Q25-F146: конкурентная запись серверного INI](reports/AUDIT-Q25-SERVER-CONCURRENT-WRITES.md)
- [Q25-F147: TLS PEM и неполная автопара](reports/AUDIT-Q25-SERVER-TLS-PEM.md)
- [Q25-F148: проверка TLS в check-config](reports/AUDIT-Q25-SERVER-TLS-CHECK-CONFIG.md)
- [Q25-F149: доверие к TLS-путям и Let's Encrypt в панели](reports/AUDIT-Q25-SERVER-TLS-PATH-TRUST.md)
- [Q25-F150: доверие к INI в панельных identity и Share](reports/AUDIT-Q25-SERVER-PANEL-SNAPSHOT-TRUST.md)
- [Q25-F151: панель и доверие к сохраняемому INI](reports/AUDIT-Q25-SERVER-PANEL-SAVE-TRUST.md)
- [Q25-F152: матрица INI и рестарт logging](reports/AUDIT-Q25-SERVER-FIELD-MATRIX-LOGGING.md)
- [Q25-F153: проверка аутентификации панели до сохранения](reports/AUDIT-Q25-SERVER-WEB-AUTH-SAVE.md)
- [Q25-F154: Quick Start и политика блокировок](reports/AUDIT-Q25-SERVER-QUICKSTART-BF-SAVE.md)
- [Q25-F155: предупреждения SIGHUP о настройках, требующих рестарта](reports/AUDIT-Q25-SERVER-SIGHUP-RESTART-HINTS.md)
- [Q25-F156: проверка Argon2-хеша панели при загрузке и live reload](reports/AUDIT-Q25-SERVER-WEB-HASH-VALIDATION.md)
- [Q25-F157: достоверный статус live reload панели](reports/AUDIT-Q25-SERVER-WEB-RELOAD-RESULT.md)
- [Q25-F158: сохранённая и действующая политика блокировок](reports/AUDIT-Q25-SERVER-BLOCKED-LIVE.md)
- [Q25-F159: стабильный порядок динамических полей INI](reports/AUDIT-Q25-SERVER-INI-ORDER.md)
- [D07: глобальные поля серверного INI](reports/AUDIT-Q25-SERVER-GLOBAL-FIELDS.md)
- [D07: базовые поля серверного профиля](reports/AUDIT-Q25-SERVER-PROFILE-FOUNDATION.md)
- [D07: поля obf.* серверного профиля](reports/AUDIT-Q25-SERVER-PROFILE-OBF.md)
- [Q25-F160: ревизия INI для политики блокировок](reports/AUDIT-Q25-SERVER-BLOCKED-REVISION.md)
- [Q25-F161: ошибки перечисления при восстановлении архива](reports/AUDIT-Q25-SERVER-ARCHIVE-SCAN.md)
- [Q25-F162: уведомления только в INI](reports/AUDIT-Q25-SERVER-NOTIFY-INI.md)
- [Q25-F163: конкурентное сохранение уведомлений](reports/AUDIT-Q25-SERVER-NOTIFY-REVISION.md)
- [Q25-F164: ревизии клиентских INI в панели](reports/AUDIT-Q25-CLIENT-PROFILE-REVISION.md)
- [Q25-F165: ограничение автозапуска и диагностики клиента](reports/AUDIT-Q25-CLIENT-PROFILE-BOUNDS.md)
- [Q25-F166: устаревшее удаление и применение клиентского INI](reports/AUDIT-Q25-CLIENT-DELETE-REVISION.md)
- [Q25-F167: точное чтение клиентского INI на Android](reports/AUDIT-Q25-ANDROID-FILE-IMPORT.md)
- [Q25-F168: файловый клиентский INI в desktop CLI](reports/AUDIT-Q25-DESKTOP-CONFIG-FILES.md)
- [Q25-F169: текстовый клиентский INI до общего парсера](reports/AUDIT-Q25-CLIENT-UI-INI-INPUT.md)
- [Q25-F170: предел мобильного клиентского INI](reports/AUDIT-Q25-MOBILE-CONFIG-BUDGET.md)
- [Q25-F171: кодировка desktop-хранилищ профилей](reports/AUDIT-Q25-DESKTOP-STORE-UTF8.md)
- [Q25-F172: отказоустойчивость desktop-хранилищ профилей](reports/AUDIT-Q25-DESKTOP-STORE-RECOVERY.md)
- [Q25-F173: транзакции профилей в desktop UI](reports/AUDIT-Q25-DESKTOP-PROFILE-TRANSACTIONS.md)
- [Q25-F174: подтверждённая запись Android-профилей](reports/AUDIT-Q25-ANDROID-PROFILE-TRANSACTIONS.md)
- [Q25-F175: защита мобильных профилей после отказа загрузки](reports/AUDIT-Q25-MOBILE-STORE-LOAD-FAILURE.md)
- [Q25-F176: строгая загрузка Android profile store](reports/AUDIT-Q25-ANDROID-STORE-DECODING.md)
- [Q25-F177: ревизия клиентского UI и применение активного профиля](reports/AUDIT-Q25-CLIENT-PROFILE-UI-REVISION.md)
- [Q25-F178: межпроцессная запись desktop profile store](reports/AUDIT-Q25-DESKTOP-STORE-CONCURRENCY.md)
- [Q25-F179: Android profile store не принимает устаревшую запись](reports/AUDIT-Q25-ANDROID-STORE-VERSION.md)
- [Q25-F180: пустой iOS profile archive не заменяется шаблоном](reports/AUDIT-Q25-IOS-EMPTY-ARCHIVE.md)
- [Q25-F181: уведомление iOS о применении активного профиля](reports/AUDIT-Q25-IOS-ACTIVE-PROFILE-RECONNECT.md)
- [Q25-F182: снимок iOS-профиля при редактировании и удалении](reports/AUDIT-Q25-IOS-PROFILE-SNAPSHOT.md)
- [Q25-F183: ограничение чтения desktop profile store](reports/AUDIT-Q25-DESKTOP-STORE-BOUNDS.md)
- [Q25-F184: конечное ожидание desktop profile-store lock](reports/AUDIT-Q25-DESKTOP-STORE-LOCK-WAIT.md)
- [Q25-F185: структура desktop profile store](reports/AUDIT-Q25-DESKTOP-STORE-STRUCTURE.md)
- [Q25-F186: индекс активного профиля Android](reports/AUDIT-Q25-ANDROID-ACTIVE-INDEX.md)
- [Q25-F187: индекс активного профиля при iOS restore](reports/AUDIT-Q25-IOS-ACTIVE-INDEX.md)
- [Q25-F188: границы мобильного хранилища и backup](reports/AUDIT-Q25-MOBILE-STORE-BOUNDS.md)
- [Q25-F189: стабильность ID профилей desktop](reports/AUDIT-Q25-DESKTOP-PROFILE-IDENTITY.md)
- [Q25-F190: ошибки истории серверного INI](reports/AUDIT-Q25-SERVER-INI-HISTORY.md)
- [Q25-F191: null в полях desktop-профиля](reports/AUDIT-Q25-DESKTOP-STORE-NULL-FIELDS.md)
- [Q25-F192: общее хранение настроек Windows/macOS](reports/AUDIT-Q25-DESKTOP-SETTINGS-STORE.md)
- [Q25-F193: Android per-app редактор и секции INI](reports/AUDIT-Q25-ANDROID-APPS-INI.md)
- [Q25-F194: переносимый пароль в ссылке и сборка редактора](reports/AUDIT-Q25-CLIENT-SHARE-PASSWORD.md)
- [Q25-F195: ошибки выдачи ссылки в клиентском UI](reports/AUDIT-Q25-CLIENT-SHARE-UI.md)
- [Q25-F196: проверка пароля share URI во всех адаптерах](reports/AUDIT-Q25-CLIENT-SHARE-PARITY.md)
- [Q25-F197: матрица общего INI-редактора](reports/AUDIT-Q25-CLIENT-INI-MATRIX.md)
- [Q25-F198: бюджет прямого импорта qeli://](reports/AUDIT-Q25-CLIENT-URI-BUDGET.md)
- [Q25-F199: входы воспроизводимой native-сборки](reports/AUDIT-Q25-NATIVE-BUILD-INPUTS.md)
- [Q25-F200: структура и языковые пары отчётов аудита](reports/AUDIT-Q25-DOC-PARITY.md)
- [Q25-F201: архив патчей и возраст свидетельств](reports/AUDIT-Q25-PATCH-RECONCILIATION.md)
- [Q25-F202: воспроизводимые native cores и Android runtime](reports/AUDIT-Q25-NATIVE-REBUILD.md)
- [Q25-F203: Android Private DNS, VPN-трафик и смена Wi-Fi](reports/AUDIT-Q25-ANDROID-NETWORK-IDENTITY.md)
- [Q25-F204: ресурсный churn Linux worker](reports/AUDIT-Q25-WORKER-RESOURCE-CHURN.md)

- [Q04: авторизация панели и границы API](reports/AUDIT-Q04-WEB-AUTH.md)

- [Q05: конфигурационные транзакции и restart](reports/AUDIT-Q05-HTTP-TRANSACTIONS.md)

- [Q06: пользователи и отзыв доступа](reports/AUDIT-Q06-USERS-ACCESS.md)

- [Q07: backup, restore и history](reports/AUDIT-Q07-BACKUP-RESTORE.md)

- [Q08: криптография и хранение ключей](reports/AUDIT-Q08-CRYPTO-KEYS.md)
- [Q09: владение UDP AUTH и PMTU до авторизации](reports/AUDIT-Q09-UDP-AUTH.md)
- [Q09: TCP-аутентификация и ClientHello](reports/AUDIT-Q09-TCP-PARSER.md)
- [Q09: UDP handshake и admission](reports/AUDIT-Q09-UDP-CONTRACTS.md)
- [Q09: итоговый аудит и сохранение KICK](reports/AUDIT-Q09-FINAL.md)

- [Q10: PacketCodec, replay и CONTROL_V2](reports/AUDIT-Q10-CODEC-CONTROL.md)

- [Q11: REALITY, TLS 1.3 и HTTP/2](reports/AUDIT-Q11-REALITY-TLS-H2.md)
- [Q12: транспорты и wire-маскировка — завершено](reports/AUDIT-Q12-TRANSPORTS.md)
- [Q13: recordizer, padding и shaping — завершено](reports/AUDIT-Q13-MORPHOLOGY.md)
- [Q14: supervisor, workers и профили — завершено](reports/AUDIT-Q14-CURRENT-LIFECYCLE.md)
