# Qeli 0.8.3 Beta — resilient connections, network policy and useful diagnostics

**Draft / Черновик. Not published / Не опубликован.**

> Preparation status: router state fixes below require a refreshed release candidate
> and qualification before publication. / Подготовка: описанные ниже исправления
> состояния роутеров требуют обновления кандидата и проверок перед публикацией.

## English

Qeli 0.8.3 strengthens the behaviour of the network core and clients under real
network changes: long RTT, stalled connections, changing UDP path MTU and temporary
loss of connectivity. It also improves Windows upgrade handling, macOS compatibility
and the diagnostics needed to understand connection problems.

### Transport stability and network efficiency

- TCP server socket buffers now default to OS management instead of fixed sizes.
  This removes an artificial buffer limit on high-RTT paths while preserving explicit
  operator settings. Linux setup enables and verifies receive autotuning without
  changing the global `tcp_mem` budget.
- TCP/TLS/WebSocket writers and genuine HTTP/2 DATA/PING handling have bounded
  no-progress deadlines. A stalled carrier can be terminated rather than reused
  after a partially written record. Idle server readers no longer reserve a shared
  packet-pool slot before the first byte arrives.
- UDP PMTU checks track the current path and budget revision, reject stale replies
  and safely re-fragment unsent records after a budget decrease. A manually selected
  tunnel MTU no longer disables outer-path probing; `mtu_probe=false` remains supported.
- TUN dispatch first tries immediate delivery, retaining bounded backpressure when
  full. Additional queue, pool and batch-send metrics help locate congestion without
  increasing the existing memory budgets. This is not a claim that overload losses
  have been eliminated.

### Routing, IPv6 and configuration

- OpenWrt and Keenetic startup no longer fails merely because the firmware exposes
  `/var` as a symlink. Routes, DNS, sysctls and firewall share `STATE_DIRECTORY`;
  updated launchers use the real path to the same existing journals. Child symlinks,
  unsafe permissions and ambiguous recovery are still refused (issue #205).

- `pull_routes=false` declines routes supplied by the server while preserving local
  routes, independent full-tunnel policy and protected tunnel DNS routes. The setting
  round-trips through client editors, INI, backups and new share links.
- IPv6 NDP proxy selects an assigned uplink source, verifies current session ownership
  and joins the relevant solicited-node multicast groups. Administrator-managed routing
  remains administrator-managed in `manual` mode.
- Unused SNI no longer rejects legacy UDP-obfs or non-WebSocket TCP-obfs profiles.
  Validation remains strict where TLS actually uses SNI. Desktop WebSocket profiles
  expose their HTTP Host override; explicit `gateway=false` survives INI serialization.

### Client improvements

**Windows:** native components are stored in directories identified by the hash of
the embedded DLL set, so different builds do not overwrite one another. Private
service data is separated from native libraries. Legacy service storage has an
explicit, guarded migration through the elevated GUI, with a private backup and no
silent import of untrusted files. Active network state or unfinished recovery blocks
migration; a stop timeout is not bypassed.

Windows also gains clearer IPv4/IPv6 address display and copying, remembered editor
dimensions and a bounded traffic graph. Service graph samples use monotonic,
sleep-inclusive timestamps, avoiding false rates after duplicate snapshots or clock
changes. Optional Windows sharing-binding control applies only to Qeli's own adapter.

**Android:** recovery after a connectivity gap no longer relies only on another
`onAvailable` callback. Network changes and MTU-only updates are handled separately.
The diagnostic journal uses bounded asynchronous I/O and supports clearing, manual
structured report export and optional last-error retention. Reports omit free-text
messages, profiles, keys and network addresses. New native diagnostics distinguish
queued, in-flight, locally completed and cancelled TCP work; local completion is not
a peer acknowledgement.

**macOS:** fixes cover Apple Silicon `openat`, old root-owned lock-file permissions,
`launchctl` service detection and disconnect/status reporting. Errors during DNS,
firewall or daemon shutdown are not disguised as a successful disconnect.

### Security and distribution

- Updated crypto/TLS dependencies include ML-KEM 0.3.3, ctutils 0.4.4,
  rustls-webpki 0.103.16 and webpki-roots 1.0.10. The changes address secret-dependent
  operations and the relevant certificate-trust advisories. Tokio is 1.54.1,
  Gradle Wrapper is 9.8.2, Android Tink is 1.24.0; dependency locks and original
  license inventories are synchronized.
- Windows, macOS and Android native cores were rebuilt from the current development
  sources. Independent A/B builds produced byte-identical artifacts, and the
  application-consumed copies are checked against the canonical libraries.
- Windows remains two single-file EXE choices: with the runtime included or requiring
  the .NET 10 Desktop Runtime. No separate native-license ZIP is needed.
- macOS now ships **two self-contained archives**, `Qeli-macos-arm64.tar.gz` for Apple
  Silicon and `Qeli-macos-x86_64.tar.gz` for Intel, requiring **macOS 15 or newer**.
  Its Rust core remains universal2. The ad-hoc packages do not provide a
  Developer-ID-signed per-app Network Extension; such profiles fail closed.
- The distribution also includes the signed Android APK, portable Linux binary and
  `.deb`, Keenetic/OpenWrt clients and installation files. Every payload is covered
  by `SHA256SUMS`. The OpenWrt source pin and SDK archive hash must be refreshed
  together with this candidate before publication.

### Updating

1. Update both server and clients to obtain the new native-core behaviour. Updating
   the server does not update a previously installed APK or EXE.
2. For an existing Linux TCP profile, explicitly choose
   `perf.tcp.send_buffer_size = 0` and `perf.tcp.recv_buffer_size = 0` to use OS-managed
   buffers. Review receive autotuning and the OS buffer limits, validate configuration
   and restart/reconnect to create new sockets. Existing manual values are not forcibly
   overwritten. [Setup guide](https://github.com/litvinovtd/qeli/blob/v0.8.3/docs/eng/manuals/GETTING-STARTED.md).
3. If Windows reports unsafe legacy service storage, stop the VPN and finish network
   recovery, then follow the preparation/migration offered by the elevated GUI.
   Do not delete recovery journals or bypass a stop timeout. Re-save a trusted profile
   and connect explicitly after migration.
4. On macOS choose the archive matching the processor; a separate .NET installation
   is not required. Installation guidance and platform limitations are in the setup guide.

### Verification and scope

Current release admission is recorded in the
[0.8.3 runtime certification manifest](https://github.com/litvinovtd/qeli/blob/v0.8.3/release/certification/0.8.3.json),
including the exact tested artifact hashes and retained evidence. Unavailable physical
device tests remain explicit limitations, not successful results. CI and Linux namespace
tests do not substitute for real-device roaming or a public Internet performance test.

[Earlier targeted transport/PMTU tests](https://github.com/litvinovtd/qeli/blob/v0.8.3/docs/data/benchmarks/network_targeted_083_required_2026-10-23.json)
and [the twelve-profile laboratory comparison](https://github.com/litvinovtd/qeli/blob/v0.8.3/docs/data/benchmarks/release12_083_required_2026-10-23.json)
retain their original candidate hashes, initial failures and interpretation limits.
They are not new measurements of the final packages or a guaranteed speed increase.
The previously documented Android API34 ENONET limitation is not declared fixed.
Links pinned to `v0.8.3` become public when that tag is published.

## Русский

Qeli 0.8.3 повышает устойчивость сетевого ядра и клиентов в реальных условиях:
при большом RTT, зависших соединениях, изменении UDP path MTU и временной потере
сети. Одновременно доработаны обновление Windows-клиента, совместимость macOS
и диагностика, которая помогает понять причину проблем с подключением.

### Устойчивость транспорта и работа с сетью

- TCP-буферы сервера по умолчанию переданы под управление ОС вместо фиксированных
  размеров. Убран искусственный предел буфера на путях с большим RTT; явные настройки
  администратора сохраняются. Linux-установка включает и проверяет receive autotuning,
  не меняя глобальный бюджет `tcp_mem`.
- Для записи TCP/TLS/WebSocket и настоящего HTTP/2 введён ограниченный срок отсутствия
  прогресса, отдельно для DATA и PING. Зависший носитель завершается и не используется
  повторно после частично записанной записи. Ожидающие TCP-читатели сервера больше
  не занимают слот общего пула пакетов до получения первого байта.
- UDP PMTU учитывает текущий путь и ревизию бюджета, отбрасывает устаревшие ответы
  и безопасно переразбивает неотправленные записи при уменьшении доступного размера.
  Ручной MTU туннеля больше не отключает проверку внешнего пути;
  `mtu_probe=false` по-прежнему поддерживается.
- Передача пакетов из TUN сначала пробует немедленную отправку, сохраняя ограниченное
  ожидание при заполнении очереди. Новые метрики очередей, пула и пакетной UDP-отправки
  помогают найти перегрузку без увеличения лимитов памяти. Это не утверждение об
  устранении всех потерь при насыщении канала.

### Маршрутизация, IPv6 и конфигурация

- OpenWrt/Keenetic: запуск больше не ломается лишь из-за системного `/var`-симлинка.
  Маршруты, DNS, sysctl и firewall используют общий `STATE_DIRECTORY`; обновлённые
  шаблоны указывают реальный путь к прежним журналам. Дочерние symlink, небезопасные
  права и неоднозначный recovery по-прежнему отвергаются (issue #205).
- `pull_routes=false` позволяет отказаться от маршрутов сервера, сохранив локальные
  маршруты, независимую full-tunnel-политику и защищённые маршруты tunnel DNS.
  Настройка сохраняется в редакторах клиентов, INI, резервных копиях и новых ссылках.
- IPv6 NDP proxy использует назначенный uplink-адрес, проверяет владельца текущей
  сессии и подписывается на нужные solicited-node multicast-группы. В режиме `manual`
  маршруты и firewall остаются ответственностью администратора.
- Неиспользуемое SNI больше не мешает загрузке старых UDP-obfs и TCP-obfs-профилей
  без WebSocket. Там, где SNI действительно используется TLS, строгая проверка
  сохраняется. В desktop-редакторах WebSocket доступен HTTP Host override;
  явное `gateway=false` корректно сохраняется в INI.

### Доработки клиентов

**Windows:** нативные компоненты размещаются в каталогах по хешу встроенного
комплекта DLL — разные сборки не перезаписывают библиотеки друг друга. Закрытые
данные службы отделены от нативных библиотек. Для старого служебного хранилища
предусмотрена явная защищённая миграция через GUI с повышенными правами: с приватной
резервной копией и без скрытого импорта недоверенных файлов. Активное сетевое
состояние и незавершённое восстановление блокируют переход; тайм-аут остановки
не обходится.

Также улучшены отображение и копирование IPv4/IPv6, сохранение размеров редакторов
и ограниченный график трафика. График службы использует монотонные временные отметки
с учётом сна: повторные снимки и изменение часов не создают ложные значения скорости.
Опциональное управление Windows sharing bindings затрагивает только собственный
адаптер Qeli.

**Android:** восстановление после отсутствия сети больше не зависит только от нового
`onAvailable`. Смена сети отделена от изменения одного MTU. Журнал переведён на
ограниченную асинхронную запись; доступны очистка, ручной структурированный отчёт
и опциональное сохранение последней ошибки. Отчёты не содержат свободного текста
сообщений, профилей, ключей и сетевых адресов. Новая нативная диагностика разделяет
TCP-данные в очереди, в работе, локально записанные и отменённые; локальная запись
не объявляется подтверждением получения другой стороной.

**macOS:** исправлены `openat` на Apple Silicon, права старых root-owned lock-файлов,
определение службы через `launchctl` и отображение результата отключения.
Ошибки DNS, firewall и завершения демона не маскируются успешным статусом.

### Безопасность и комплект поставки

- Обновлены криптографические и TLS-зависимости: ML-KEM 0.3.3, ctutils 0.4.4,
  rustls-webpki 0.103.16 и webpki-roots 1.0.10. Изменения закрывают зависимые от
  секрета операции и соответствующие предупреждения о доверии сертификатам.
  Tokio обновлён до 1.54.1, Gradle Wrapper — до 9.8.2, Android Tink — до 1.24.0.
  Lock-файлы и оригинальные лицензионные тексты согласованы.
- Нативные ядра Windows, macOS и Android пересобраны из актуальных исходников.
  Независимые A/B-сборки дали побайтово одинаковые артефакты; используемые приложениями
  копии проверяются на совпадение с каноническими библиотеками.
- Windows по-прежнему распространяется двумя single-file EXE: со встроенным runtime
  и с требованием установленного .NET 10 Desktop Runtime. Отдельный архив лицензий
  нативных компонентов не нужен.
- Для macOS теперь поставляются **два самостоятельных архива**:
  `Qeli-macos-arm64.tar.gz` для Apple Silicon и `Qeli-macos-x86_64.tar.gz` для Intel.
  Требуется **macOS 15 или новее**. Rust-ядро остаётся universal2. Ad-hoc-пакеты
  не содержат Developer-ID-подписанное per-app Network Extension; такие профили
  отказывают в запуске, а не расширяют выбранный трафик до общего туннеля.
- В комплект также входят подписанный Android APK, переносимый Linux-бинарник и
  `.deb`, клиенты Keenetic/OpenWrt и установочные файлы. Все payload-файлы покрыты
  `SHA256SUMS`. Перед публикацией нужно обновить OpenWrt source pin и SHA256
  SDK-архива вместе с этим кандидатом.

### Порядок обновления

1. Обновите сервер и клиенты: обновление сервера не заменяет нативное ядро внутри
   уже установленного APK или EXE.
2. Для существующего TCP-профиля Linux явно установите
   `perf.tcp.send_buffer_size = 0` и `perf.tcp.recv_buffer_size = 0`, если нужны
   буферы под управлением ОС. Проверьте receive autotuning и системные лимиты буферов,
   провалидируйте конфигурацию и перезапустите соединение для создания новых сокетов.
   Старые ручные значения не заменяются принудительно.
   [Инструкция](https://github.com/litvinovtd/qeli/blob/v0.8.3/docs/ru/manuals/GETTING-STARTED.md).
3. Если Windows сообщает о небезопасном старом хранилище службы, остановите VPN
   и завершите восстановление сети, затем используйте подготовку/миграцию,
   предлагаемую GUI с повышенными правами. Не удаляйте recovery-журналы и не
   обходите тайм-аут остановки. После миграции заново сохраните доверенный профиль
   и подключитесь явно.
4. На macOS выберите архив для своего процессора; отдельно устанавливать .NET
   не требуется. Инструкция установки и ограничения платформ описаны в руководстве.

### Проверки и границы утверждений

Актуальный допуск фиксируется в
[runtime-сертификации 0.8.3](https://github.com/litvinovtd/qeli/blob/v0.8.3/release/certification/0.8.3.json):
с точными SHA проверенных артефактов и сохранёнными результатами. Недоступные проверки
на физических устройствах остаются явными ограничениями, а не успешными тестами.
CI и Linux namespace-проверки не заменяют роуминг на реальных устройствах и замеры
скорости в публичном Интернете.

[Прежние целевые проверки транспорта и PMTU](https://github.com/litvinovtd/qeli/blob/v0.8.3/docs/data/benchmarks/network_targeted_083_required_2026-10-23.json)
и [лабораторное сравнение двенадцати профилей](https://github.com/litvinovtd/qeli/blob/v0.8.3/docs/data/benchmarks/release12_083_required_2026-10-23.json)
сохраняют исходные хеши кандидатов, неудачные попытки и ограничения интерпретации.
Это не новые замеры финальных пакетов и не гарантия прироста скорости.
Ранее описанное ограничение Android API34 ENONET не объявляется исправленным.
Ссылки на `v0.8.3` станут публично доступными при публикации соответствующего тега.
