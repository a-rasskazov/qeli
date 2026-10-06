# qeli-client на Keenetic (Entware) — IPv4/IPv6 деплой

Запуск qeli-VPN-клиента на роутере Keenetic как шлюза для всего LAN.
**Подробный пошаговый гайд (по шагам, с проверкой туннеля) — [docs/*/manuals/KEENETIC-DEPLOY.md](../../docs/ru/manuals/KEENETIC-DEPLOY.md).**
План и обоснование порта — [docs/*/reference/KEENETIC-PORT.md](../../docs/ru/reference/KEENETIC-PORT.md).

> ✅ Клиент проверен на живом Keenetic и работает. Скрипты в этой папке остаются
> **шаблонами**: проверь имена интерфейсов и поведение firewall под свою
> модель и версию прошивки.

## Предусловия на роутере
- Установлен **Entware** (opkg, `/opt`).
- Включён компонент **VPN** в KeeneticOS (чтобы был `/dev/net/tun`).
- Есть SSH-доступ.

## Сборка бинарей (на лабе .10)
```sh
python scripts/build_keenetic.py --sync
# → release/keenetic/qeli-client-keenetic-aarch64 и qeli-client-keenetic-mipsel
```

## Установка (на роутере)
Скопируй всю папку `release/keenetic/` на роутер (scp) и запусти:
```sh
sh install-keenetic.sh      # определит арку, поставит ip-full/iptables, разложит файлы
vi /opt/etc/qeli/client.conf
/opt/etc/init.d/S99qeli start
tail -f /opt/var/log/qeli-client.log   # ждём 'Auth OK'
```

## Режим шлюза (весь LAN через VPN)
- В `client.conf`: `gateway = true` (full-tunnel) и `dns = off` (не трогать DNS роутера).
- Рекомендуемый конфиг использует `gateway_nat = true`: само ядро qeli ставит и проверяет
  IPv4/IPv6 forwarding, MASQUERADE, FORWARD и MSS clamp, а при остановке восстанавливает
  изменённые sysctl. `S99qeli` сохраняет `GATEWAY=yes` только как fallback для старых
  конфигов без `gateway_nat`/`forward`.
- Legacy fallback ждёт до 60 секунд атомарно опубликованный после AUTH/NetworkPlan файл,
  включает firewall только для реально выданных IPv4/IPv6 и не угадывает семейство по
  `ipv6 = auto`. На RA/SLAAC WAN он сохраняет `accept_ra`, ставит `2` до IPv6 forwarding и
  восстанавливает прежнее значение при остановке.
- Для inner IPv6 оставь `ipv6 = auto`, используй `required` для fail-closed или `off` для
  принудительного IPv4. Для dual-stack router-mode нужен `ip6tables`; без него `auto`
  согласует IPv4, а `required` откажет до настройки интерфейса.
- При необходимости ограничь NAT реальными `lan_subnet` и `lan_subnet_ipv6` своего LAN.
  Имя LAN-бриджа для legacy fallback (`LAN_IF`, обычно `br0`) проверь через `ip a`.

## Выбор режима под железо
- **MIPS** (MT7621/7628, без AES-NI): `fake-tls` / `obfs` / `plain` (ChaCha20). Потолок —
  десятки Мбит. `reality-tls` очень медленный (двойной AEAD).
- **ARM** (Cortex-A53, crypto-ext): можно `reality-tls`; скорость в разы выше.

## Удаление
```sh
/opt/etc/init.d/S99qeli stop
rm -f /opt/etc/init.d/S99qeli /opt/bin/qeli-client
rm -rf /opt/etc/qeli
```

## Ошибки установки (development0.8.2)

Установщик предпочитает canonical имена `qeli-client-keenetic-aarch64/mipsel`,
старые `qeli-client-aarch64/mipsel` поддерживает для ручных bundles. Ошибка установки
обязательных ip-full/iptables прекращает установку; отсутствие ip6tables явно
предупреждается и требует проверить IPv6 перед запуском.

Существующий INI сохраняется, доступ ограничивается0600, каталог —0700. Копии
готовятся до замены; каждый файл публикуется атомарно, но весь bundle не является
транзакцией. После отказа публикации устранить ошибку и повторить установщик.
Работающий VPN автоматически не перезапускается. Это проверено shell/filesystem
fixtures, не настоящим opkg/прошивкой/ELF. См. [Q31](../../docs/ru/reports/AUDIT-Q31-OPENWRT-CONTROLS.md).

Legacy gateway использует правила с тегом `qeli-keenetic-legacy` и forwarding
checkpoint `version=2`. Ошибка очистки сохраняет состояние и блокирует перезапуск.
Старый checkpoint без версии требует ручной сверки; он не удаляется автоматически.
Перед заменой работающего legacy-шаблона остановить его предыдущим скриптом и
проверить правила/sysctl. Подробности: [восстановление при обновлении](../../docs/ru/manuals/KEENETIC-DEPLOY.md).

PID-файл нового шаблона хранит `PID start_ticks`. До обновления остановить клиент
предыдущим установленным шаблоном и проверить завершение: установщик блокирует
существующий PID/pending record. Stop ждёт TERM перед очисткой; при timeout состояние
сохраняется, restart не запускает ещё один клиент. Старые single-PID записи требуют
сверки владельца. Status:0 running,3 stopped,4 unverified. Шаблон не удаляет TUN
напрямую. [Порядок остановки и обновления](../../docs/ru/manuals/KEENETIC-DEPLOY.md).

Gateway fallback больше не разбирает INI в shell. При GATEWAY=yes без OpkgTun
шаблон читает `qeli-client --config ... --print-gateway-owner`: core для
gateway_nat/forward/exit_node, legacy при выключенных flags. Ответ/ошибка
проверяются до запуска; старый binary без команды отказывает. Обновлять binary
и шаблон вместе, сохранять config стабильным во время start. Для OpkgTun или
GATEWAY=no этот compatibility query не нужен. [Подробности](../../docs/ru/manuals/KEENETIC-DEPLOY.md).

## Общий lifecycle (development0.8.2)

Базовый installer доставляет обязательную библиотеку
/opt/etc/qeli/lifecycle.sh (0600). Обновляй её вместе с binary/init и установленным
wan.d hook; старые скрипты общей блокировки не соблюдают. Init, hook и installer
используют /var/run/qeli.lifecycle.lock. Занятый вызов возвращает ошибку — повторить
после завершения владельца. Обычный выход/сигналы освобождают lock; после SIGKILL
нужна сверка отсутствия init/hook/installer-владельца перед rmdir пустого каталога.
Recovery-файлы PID/plan/forwarding/pending не удалять. Hook-события не очередятся;
обнаруженная смена плана прерывает L3/save/receipt и оставляет pending. Атомарность
core-поколений/ABA/firmware этим не доказана.

Maintainer builds now always upload into private0700 /var/tmp/qeli-router-keenetic-XXXXXX
checkouts, with separate target/rlib restriction and one compiler job. --sync is
compatible but optional. Retained directories require reviewed per-run cleanup.
SHA256-bound ELF admission precedes atomic local publication; it checks class,
machine, little endian and absence of interpreter/shared dependencies, not full
ISA/musl/firmware compatibility or reproducibility. Old /opt/qeli-src is unused.
See [deployment manual](../../docs/eng/manuals/KEENETIC-DEPLOY.md) for limits.

Both router helpers now share target aliases, explicit Rust1.97.0/MIPS nightly-2026-06-10,
Zig0.13.0/cargo-zigbuild0.23.0 admission and build commands. Encoded/ambient flags
cannot shadow recipe RUSTFLAGS; MIPS soft-float remains explicit. Wrong identity
stops setup; installer/target false success fails verification. Shared caches/global
Cargo config/PATH and actual cross/firmware behavior remain separately qualified.

Installation now keeps same-directory backups of the previous binary/init/helper
and a0600 /opt/etc/qeli/install-pending recovery record while publishing code.
Ordinary publication failures and a handled termination signal restore old bytes
and modes (or remove new code that was originally absent). A failed restore keeps
remaining backups and the marker. Installer retry, both updated init starts and
the updated active wan.d hook refuse it; stop remains available. Existing INI
contents are preserved. A newly published example and stricter600 config mode
may remain after a late error; package/dependency changes are not rolled back.

If install-pending remains, keep the client stopped and inspect the record and
remaining backups before any start or retry. Verify no init/hook/installer owns
the lifecycle action before repairing the complete compatible binary/init/helper
set. Empty backup fields mean the target was originally absent; a missing named
backup may already have been restored and does not authorize blind file deletion.
After verifying recovery, remove install-pending and, if SIGKILL left it, only the
empty lifecycle lock directory. Do not delete PID/plan/forwarding recovery records.
Older installed scripts may not honor this marker: manual stop/review remains
mandatory. No automatic SIGKILL/power-loss recovery or fsync-backed bundle
transaction is claimed. Symlink/nonregular publication targets and a linked
/opt/etc/qeli directory are rejected before package updates. Root/admin path
replacement during installation remains outside this cooperative protocol.
