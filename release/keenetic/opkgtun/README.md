# qeli на Keenetic через OpkgTun (интерфейс в вебморде)

Опциональный режим для **KeeneticOS 5.0+**: qeli-tun отдаётся `ndm` как нативный
интерфейс `OpkgTunN`, который виден в вебморде и доступен в **«Приоритетах подключений»**
и статических маршрутах. Тогда per-device / selective роутинг настраивается мышкой в UI,
без самодельного NAT из `S99qeli`.

Это **аддон**, изолированный в этой папке. Базовый gateway-режим (надёжный, без зависимости
от ndm) — в `release/keenetic/`. Если UI-роутинг не нужен — используй его, он проще и
переживает ребут без нюансов ниже.

> ⚠️ **Честно о зрелости.** OpkgTun-интеграция рабочая, но **хрупкая и полу-ручная**:
> - авто-регистрация через wan.d-хук на раннем бусте **ненадёжна** (ndmc в этом контексте
>   часто не отвечает) — рабочая регистрация делается вручную из ssh-логина;
> - переживание ребута требует **статического IP на сервере** (иначе адрес «уплывает» и
>   сохранённый в ndm конфиг устаревает);
> - нативного тумблера вкл/выкл в «Других подключениях» у OpkgTun нет (фича-реквест Keenetic).
>
> Разумно на ARM-моделях; на mipsel — только лёгкие режимы маскировки.

## Модель владения (ключевое, проверено на устройстве)

На 5.0 устройство `opkgtun0` **создаёт и держит САМ `ndm`**, а приложение к нему
**прицепляется**, и **L3 (адрес + линк) тоже ставит ndm, а не приложение**. Две ловушки:

- qeli сам создаёт `opkgtun0` → `ndm` не заводит интерфейс:
  `Opkg::Interface::Tun error: "OpkgTun0": system failed [0xcffd00a9]`,
  а qeli — `interface 'opkgtun0' already exists … refusing to take it over`.
- qeli сам ставит адрес/поднимает линк → `ndm` навсегда залипает в
  `link: pending / connected: no` и **не маршрутизирует** через интерфейс. Только когда
  адрес ставит ndm (`ip address … /32` + `up`), интерфейс переходит в `connected: yes`.

Поэтому qeli в **attach-режиме** (`dev_attach = true`): открывает существующее
ndm-устройство **только для перекачки пакетов** — не создаёт его, не ставит адрес, не
поднимает линк, не трогает маршруты, не удаляет при выходе. После успешного commit всего
аутентифицированного NetworkPlan qeli атомарно пишет выданные IPv4/IPv6 и MTU в
`$QELI_TUNIP_FILE`; частично применённый и затем откаченный план в файл не попадает. Хук
читает только этот committed-файл (не старые строки лога) и передаёт IPv6 в ndm вместе с
согласованным host-prefix, обычно `/128`.
Адрес/линк/маршруты держит `ndm` (через хук).

> ℹ️ **Про «gvisor only».** Форумные упоминания, что «на OpkgTun разрешён только gvisor»,
> относятся к ВНУТРЕННИМ tun-stack режимам Clash/sing-box (`system`/`gvisor`/`mixed` — опция
> самого приложения), а НЕ к ndm. Обычный kernel-tun через OpkgTun работает (так живёт,
> например, AmneziaWG-Go). Затык `0xcffd00a9` был не в gvisor, а в порядке/владении устройством.

## Файлы в этой папке

- `010-qeli.sh` — wan.d-хук: создаёт `OpkgTun0`, ждёт IPv4 и/или IPv6 и MTU из NetworkPlan qeli, ставит
  dual-stack L3 через ndmc.
- `S99qeli` — init-скрипт с преднастроенным `OPKGTUN=opkgtun0` (в OpkgTun-режиме свой NAT
  выключен; сигналит хуку и экспортит `QELI_TUNIP_FILE`).
- `client.conf.example` — пример (`dev = opkgtun0`, `dev_attach = true`, `gateway = false`,
  `ipv6 = auto`).

## Установка

1. Клиент (общий бинарь) и базовый деплой — по `release/keenetic/README.md`.
2. Скопируй OpkgTun-файлы:
   ```sh
   cp opkgtun/S99qeli            /opt/etc/init.d/S99qeli
   mkdir -p /opt/etc/ndm/wan.d
   cp opkgtun/010-qeli.sh        /opt/etc/ndm/wan.d/010-qeli.sh
   chmod +x /opt/etc/init.d/S99qeli /opt/etc/ndm/wan.d/010-qeli.sh
   ```
3. В `/opt/etc/qeli/client.conf` задай `dev = opkgtun0`, `dev_attach = true`, `gateway = false`
   (см. `opkgtun/client.conf.example`).
4. **Пин статических IPv4/IPv6 на сервере** для этого пользователя (обязательно для
   стабильного сохранённого L3 после ребута) — см. ниже.
5. `/opt/etc/init.d/S99qeli start`.

## Статические IPv4/IPv6 (обязательно для переживания ребута)

Сервер по умолчанию выдаёт адреса из пулов, и после ребута они могут смениться → сохранённый
в ndm L3 устареет. Зафиксируй обе используемые семьи на сервере:

- **веб-панель**: пользователь → поле статического IP;
- **CLI (новый юзер)**: `qeli add-client <user> --static-ip 10.9.0.2 --static-ipv6 fd71:e1:1234:1::2 …`;
- **конфиг сервера**: `static_ip = "10.9.0.2"` в `[user:<name>]`, либо
  `static_ipv6 = "fd71:e1:1234:1::2"`; профильные эквиваленты —
  `pool.reservation.<user>` и `pool.ipv6.reservation.<user>`.

Применяется на следующем коннекте (user db читается на auth в реальном времени).

## Регистрация вручную (надёжный путь)

wan.d-хук на бусте часто не может выполнить ndmc. Рабочий способ — **из ssh-ЛОГИНА**
(не из `exec sh` — иначе `0xcffd0060`), порядок тот же, что в хуке:

```sh
ndmc -c "interface OpkgTun0"                 # 1. ndm создаёт kernel-device opkgtun0
/opt/etc/init.d/S99qeli start                # 2. qeli цепляется, пишет IP в файл
IP=$(sed -n 's/^ipv4=\([^/]*\)\/.*/\1/p' /opt/var/run/qeli.tunip | head -n1)
IP6_CIDR=$(sed -n 's/^ipv6=//p' /opt/var/run/qeli.tunip | head -n1)
MTU=$(sed -n 's/^mtu=\([0-9][0-9]*\)$/\1/p' /opt/var/run/qeli.tunip | head -n1)
[ -n "$MTU" ] || MTU=1400
ndmc -c "interface OpkgTun0 ip global auto"
[ -z "$IP" ] || ndmc -c "interface OpkgTun0 ip address $IP 255.255.255.255"
[ -z "$IP6_CIDR" ] || ndmc -c "interface OpkgTun0 ipv6 address $IP6_CIDR"
ndmc -c "interface OpkgTun0 ip mtu $MTU"
ndmc -c "interface OpkgTun0 ip tcp adjust-mss pmtu"
ndmc -c "interface OpkgTun0 security-level public"
ndmc -c "interface OpkgTun0 up"
ndmc -c "system configuration save"
ndmc -c "show interface OpkgTun0" | grep -E "connected|global|address" # обе семьи должны совпасть
```
Снять интерфейс: `ndmc -c "no interface OpkgTun0"`.

## Маршрутизация

- **Весь трафик устройства → VPN**: «Интернет → Приоритеты подключений» → профиль с
  `OpkgTun0` выше WAN → привязать устройство. Работает для любых адресов/CDN, ndm сам NAT'ит.
- **Точечный маршрут**: `ndmc -c "ip route <сеть> <маска> OpkgTun0"` + `system configuration save`.
  UI-статик ненадёжен: маршрут ложится в table `main`, которую трафик клиента не смотрит
  (сначала `from all lookup 4096`), плюс баг вебморды сбрасывает выбор интерфейса на дефолт.
- Интерфейс обязан быть `connected: yes` и `global: yes` — иначе маршруты не активируются.
- НЕ ставь `ip route default OpkgTun0` для роутера в целом — завернётся и соединение qeli с
  сервером → петля. Заворачивай клиентов через Приоритеты.
- `dev_attach = true` означает, что L3 полностью владеет ndm. Хук автоматически переносит
  адреса и MTU, но server-pushed маршруты и DNS в Keenetic не устанавливает: их нужно задать
  в «Приоритетах подключений»/статических маршрутах и в настройках DNS самого Keenetic.

Проверка exit-IP туннеля (минуя роутинг/DNS): `curl --interface opkgtun0 -s https://api.ipify.org`.

## Диагностика

| Симптом | Причина / что делать |
|---|---|
| `system failed [0xcffd00a9]` + qeli `already exists` | Инверсия владения: поставь `dev_attach = true`, дай ndm создать интерфейс первым |
| Маршрут не идёт; `show interface` = `connected: no` / `link: pending`, `global: no` | L3 должен держать ndm. Проверь `dev_attach = true`, что qeli пишет IP в `/opt/var/run/qeli.tunip`, и что адрес `/32` + `ip global` ставит ndm |
| Хук: `OpkgTun0 недоступен` / `не принял` | ndmc в контексте wan.d (особенно на бусте) не отвечает — зарегистрируй вручную из ssh-логина |
| После ребута маршрут отвалился, адрес сменился | Нет `static_ip`/`static_ipv6` → закрепи используемые семьи на сервере |
| Файла `/opt/var/run/qeli.tunip` нет | `OPKGTUN=` пуст в S99qeli, либо старый бинарь без dual-stack `dev_attach` |
| Нет тумблера вкл/выкл в «Других подключениях» | Штатно не поддерживается (фича-реквест Keenetic); управляй через `ndmc interface OpkgTun0 up/down` + стоп qeli |

## Удаление / откат на gateway

```sh
/opt/etc/init.d/S99qeli stop
ndmc -c "no interface OpkgTun0"                 # из ssh-логина
rm -f /opt/etc/ndm/wan.d/010-qeli.sh
cp ../S99qeli /opt/etc/init.d/S99qeli           # базовый gateway-скрипт
# в client.conf: dev = vpn0, gateway = true, убрать dev_attach
```

## Ошибки регистрации (development0.8.2)

Hook принимает marker только вида `opkgtun` + цифры, максимум15 символов. Каждая
команда изменения ndm и сохранения конфигурации проверяется; после отказа hook
возвращает ошибку и не сообщает interface up. Ранее применённые ndm changes могут
остаться: устранить причину и повторить hook/ручную регистрацию, проверяя результат
каждой команды. Нет interface/плана — диагностическое ожидание следующего события.
IPv4/IPv6/MTU читаются одним snapshot опубликованного файла. Stop/generation races,
параллельные обновления и настоящая firmware behavior этим не квалифицированы.
[Текущий Q31 audit](../../../docs/ru/reports/AUDIT-Q31-OPENWRT-CONTROLS.md).

После частичного отказа хук сохраняет `/opt/var/run/qeli.opkgtun.apply-pending`
до успешного применения и сохранения конфигурации. Следующий вызов повторяет
команды даже при уже совпадающих адресах. Маркер не является блокировкой
параллельных обработчиков; выполненные команды автоматически не откатываются.

Legacy gateway использует правила с тегом `qeli-keenetic-legacy` и forwarding
checkpoint `version=2`. Ошибка очистки сохраняет состояние и блокирует перезапуск.
Старый checkpoint без версии требует ручной сверки; он не удаляется автоматически.
Перед заменой работающего legacy-шаблона остановить его предыдущим скриптом и
проверить правила/sysctl. Подробности: [восстановление при обновлении](../../../docs/ru/manuals/KEENETIC-DEPLOY.md).

PID-файл нового шаблона хранит `PID start_ticks`. До обновления остановить клиент
предыдущим установленным шаблоном и проверить завершение: установщик блокирует
существующий PID/pending record. Stop ждёт TERM перед очисткой; при timeout состояние
сохраняется, restart не запускает ещё один клиент. Старые single-PID записи требуют
сверки владельца. Status:0 running,3 stopped,4 unverified. Шаблон не удаляет TUN
напрямую. [Порядок остановки и обновления](../../../docs/ru/manuals/KEENETIC-DEPLOY.md).

Хук сохраняет приватный `qeli.opkgtun.applied` только после успешных команд и save.
Изменение полного плана, включая только MTU, повторяет настройку. No-op требует
этой записи, connected и буквального совпадения адресов; подстроки не принимаются.
Stop удаляет запись после выхода клиента. Это не блокировка, поколение клиента
или полное чтение настроек ndm. Внешние изменения и параллельные события остаются OPEN.

Gateway fallback больше не разбирает INI в shell. При GATEWAY=yes без OpkgTun
шаблон читает `qeli-client --config ... --print-gateway-owner`: core для
gateway_nat/forward/exit_node, legacy при выключенных flags. Ответ/ошибка
проверяются до запуска; старый binary без команды отказывает. Обновлять binary
и шаблон вместе, сохранять config стабильным во время start. Для OpkgTun или
GATEWAY=no этот compatibility query не нужен. [Подробности](../../../docs/ru/manuals/KEENETIC-DEPLOY.md).

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

Installer сохраняет backup прежних binary/init/helper в тех же каталогах и
recovery record0600 /opt/etc/qeli/install-pending на время публикации кода.
Обычная ошибка публикации и обработанный сигнал завершения возвращают прежние
bytes/modes либо удаляют новый код, которого раньше не было. Если restore не
удался, оставшиеся backup и marker сохраняются. Retry installer, start обоих
обновлённых init и обновлённый активный wan.d hook отказываются работать; stop
доступен. Содержимое существующего INI сохраняется. Уже опубликованная болванка
и ужесточённый mode600 конфига могут остаться после поздней ошибки; изменения
пакетов/зависимостей не откатываются.

Если install-pending остался, не запускай клиент: проверь record и оставшиеся
backup. Перед восстановлением убедись, что init/hook/installer не владеют lifecycle
action, затем восстанови согласованный комплект binary/init/helper. Пустое поле
backup означает, что файла раньше не было; отсутствующий именованный backup мог
уже быть восстановлен и не разрешает слепо удалять текущий файл. После проверки
восстановления удали install-pending и, если SIGKILL оставил lock, только пустой
lifecycle lock directory. PID/plan/forwarding recovery records не удаляй. Старые
установленные скрипты могут не соблюдать marker: остановка/проверка обязательны.
Автоматическое recovery после SIGKILL/power loss и fsync-backed transaction всего
bundle не заявляются. Symlink/nonregular targets и linked /opt/etc/qeli отвергаются
до package updates. Root/admin replacement путей во время установки остаётся вне
этого cooperative protocol.

Перед start/restart обновлённый шаблон проверяет конфигурацию общим парсером
бинарника: dev должен совпадать с TUN в шаблоне, device_type должен быть tun.
Обычный шаблон требует dev_attach=false; активный OpkgTun — dev_attach=true
и совпадение dev с OPKGTUN. В OpkgTun отключи gateway_nat, forward и exit_node:
L3/gateway принадлежат ndm. Проверка действует и при GATEWAY=no.

При несоответствии запуск отвергается до создания процесса и изменения старого
состояния. Согласуй INI и шаблон, затем повтори start. Обновляй binary и template
вместе: старый binary не понимает новые --expect-router-device/
--expect-router-attach и откажет в проверке. Не меняй INI во время start/restart:
проверка читает один снимок, но последующее открытие файла не привязано к нему.
