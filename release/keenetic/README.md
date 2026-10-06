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
