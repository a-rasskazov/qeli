# Q06: пользователи и отзыв доступа — пакеты 1–2

Дата: 3 октября 2026. **Статус пакета: PASS; Q06 в целом: IN_PROGRESS.**

Исправления проверены на изолированном Linux release `c15280a7f83f185c10014b08ccf1dddbaf6660ef987d6de2799e4e85bf1d2b21`.
**Последняя квалификация — второй пакет ниже: 199 Q06 checks.**
Конфигурации остаются INI. JSON используется только как служебное тело HTTP/control API.

## Подтверждённые ошибки и исправления

| ID | Ошибка | Итог |
| --- | --- | --- |
| Q06-F001 | Scalar/array/null вместо тела объекта снимали bandwidth/quota/expiry; неверные типы enabled/password/bandwidth принимались с успехом. Неверный profile в live bandwidth выбирал все профили. | Общая проверка объекта и строгие типы до hashing, блокировок и записи. Ошибочный запрос сохраняет точные прежние байты users INI. |
| Q06-F002 | Удаление файлового override возвращало inline-пользователя или прежнюю группу из server.conf. | Удаление любой записи, также определённой inline, отклоняется до мутации. Для пользователя доступно Disable; определения inline удаляются в server.conf. |
| Q06-F003 | Неверный тип route.gateway превращался в отсутствующий next hop. | Nullable строка проверяется строго; отсутствующее/null/пустое значение по-прежнему допустимо. |
| Q06-F004 | Delete, enabled=false через Edit и запрет профиля меняли базу, сохраняя рабочие TCP/UDP-сессии. | После успешного SIGHUP права применяются к открытым сессиям через существующий admission/kick/lease teardown. Sweep также перепроверяет текущие права, включая сессию, зарегистрированную после первоначального сканирования. |
| Q06-F005 | После сохранения bandwidth панель посылала второй persist-командный writer; он заменял явный burst_mbps CLI-дефолтом. | Панель сохраняет INI один раз; reload применяет эффективный limit_mbps к существующим сессиям, включая наследование от группы. |

До исправления реальный пакетный прогон воспроизвёл шесть продолжающих работать туннелей:
TCP и UDP × Edit disabled / Delete / profile restriction. Проверяется и список сессий,
и ICMP через клиентский TUN. Приватное INPUT DROP исключает ложный успех через внешний
интерфейс после исчезновения TUN. Disable отдельным endpoint и quota/expiry имели собственные проверки.

## Проверки

- 119 реальных HTTP/API checks PASS: строгие тела/типы, массивы ACL, предел u32, missing group,
  маршруты и семейства gateway, inline/file precedence, статические адреса и коллизии,
  очистка optional fields, quota/expiry, сохранение пароля и лимитов, share/QR.
- 57 checks PASS на реальных Linux TCP/UDP-клиентах: 12 сценариев отзыва доступа,
  fixed IP, group bandwidth 2 → 3 Mbps на живой сессии, expiry и seeded exhausted quota.
  Quota использует приватный usage sidecar с известным счётчиком, а не новый гигабайтный benchmark.
- 293 HTTP checks Q04 и 75 transaction checks Q05 PASS на том же новом release.
- 2263 Linux unit tests PASS, 60 ignored; pinned full/minimal Clippy и rustfmt PASS;
  116 JS-групп редакторов и panel checks PASS.
- Linux release matrix: 18 сценариев / 327 assertions PASS, host_restored=true.
  Свежий soak 100 TCP + 100 QUIC / 33 checks PASS; свежие desktop/Android native A/B,
  SHA256SUMS и provenance PASS. Все четыре клиентские библиотеки побайтно совпали с Q04.

API Users подтверждает сохранение и постановку reload в очередь. Это не синхронная
квитанция готовности авторизации worker. Стенд ждёт появления пользователя в read-only
worker control перед первой авторизацией, чтобы не смешивать проверку revoke с startup
race и brute-force lockout. Исторические ошибки обвязки сохранены отдельно от канонических результатов.

## Границы после первого пакета

Q06 ещё не закрыт: остаются UsersDb filesystem/lock/crash и конкурентные писатели,
актуальность inline auth в worker control, изменения live ACL/group restrictions,
несколько устройств и замена опасных legacy fixtures. `test_user_reload.py` и
`test_l3_user_limits.py` не запускались: они управляют общими службами/фиксированными путями.
`burst_mbps` сохраняется как legacy поле; отдельное burst enforcement data plane не подтверждено.
Новый benchmark и physical qualification не заявляются. Mac, роутер и Windows VM исключены пользователем.

Все новые сетевые проверки работают внутри NET/mount/PID namespaces. Рабочий qeli.service,
его PID/время запуска и бинарник сохранены; источник и все compilation inputs захешированы.
[План](../plans/FULL-SYSTEM-AUDIT.md#06-пользователи-группы-и-выдача-доступа).

На desktop-стенде `.10` за время native-сборки появились три legacy firewall/NAT rules;
`host_restored=false` сохранён в raw evidence. PID/start и рабочий executable не менялись.
Источник изменений не установлен, firewall не восстанавливался. Это отклонение стенда
не выдано за PASS неизменности сети; desktop здесь подтверждает только A/B-артефакты.

[Итоговые свидетельства](../../../release/certification/evidence/q06-users-access-20261003.json).

## Второй пакет: INI-хранилище и inline auth после SIGHUP

**PASS; общий Q06 остаётся IN_PROGRESS.** Новая сборка `dda3c71f6c51e356d3a123f853f64073570ac17ac9c1a21b805f79141ef91e78`.

**Q06-F006:** worker принимал новую базу при SIGHUP, но четыре persist-команды контрольного
сокета объединяли users.conf со стартовыми inline users/groups. Реальный baseline
воспроизвёл восстановление удалённого inline-аккаунта через enable-user и невозможность
отключить добавленный после reload аккаунт через disable-user. Исправление хранит
последнюю принятую auth-конфигурацию; её read lease удерживается до завершения
INI-транзакции и обновления live users. Reload меняет auth и базу под тем же порядком
блокировок. enable-user, disable-user, set-limit и set-bandwidth покрыты регрессией.

- Новый users-storage: 23 checks PASS. Восемь параллельных create без потерь; два
  независимых редактирования одного аккаунта сохраняют оба поля. Повреждённые INI
  (unknown key, плохое число, невалидный UTF-8), read-only storage и отказ rename
  сохраняют прежние байты; последующее штатное сохранение работает.
- API 119 и TCP/UDP live 57 повторно прошли на этой сборке: всего 199 Q06 checks.
- 2264 Linux units, 60 ignored; full/minimal Clippy, rustfmt PASS. Свежие 18/327
  release matrix и 100 TCP + 100 QUIC / 33 soak PASS.
- Свежие native A/B и ABI/provenance PASS; библиотеки побайтно прежние. На .11 сеть и служба сохранены. На .10 raw host_restored=false: первый снимок
  default iptables-save отличается от последующего, тогда как явные legacy/nft
  снимки и остальные поля неизменны. Повторные read-only запросы воспроизвели
  непоследовательность default dump; добавление новых правил в этом прогоне не
  доказано. Источник прежнего отклонения .10 остаётся не установленным.

Файловый пункт ещё не закрыт: нужны ENOSPC/EACCES, lock timeout, crash/durability
и семантика ошибки после опубликованной записи. Также остаются live ACL/groups,
несколько устройств и legacy burst. Наличие этих проверок не означает закрытие Q06.
[Свидетельства второго пакета](../../../release/certification/evidence/q06-users-storage-20261003.json).
