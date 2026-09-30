# Техдолг начатых аудитов

<!-- normative-sync: audit-debt-v31 -->

Дата сверки: 25 сентября 2026. По запросу пользователя новые разделы полного аудита
приостановлены до закрытия этого реестра. Это **15 групп обязательств**, а не 15 найденных
багов и не процент готовности всех 37 разделов. Источник: 57 исходных `AUDIT-Q*.md`
и план `CLIENT-CONFIG-CORE.md`; повторяющиеся ограничения объединены.

`DONE` допустим только после исправления/обоснования и нужной проверки. `BLOCKED`
обозначает недоступную внешнюю предпосылку, а не успех. Стенд Linux и Android-эмулятор
пользователь предоставил 24 сентября; старое ограничение «нет Linux» больше не действует.
Подключение к двум Linux VM подтверждено; работающий сервер и его файлы не заменялись.

[Полный план](FULL-SYSTEM-AUDIT.md) · [Общее конфигурационное ядро](CLIENT-CONFIG-CORE.md)

| ID | Разделы | Статус | Долг | Критерий закрытия / текущее свидетельство |
|---|---|---|---|---|
| D01 | 14/17/18/25 | DONE | Ошибки NAT и старого поколения | Точные спецификации правил до изменения firewall; retry и итоговая ошибка; запрет restart после неполной очистки; возврат IPv4 forwarding. Unit/cross, 18 native и 8 worker E2E PASS; baseline IPv4 leak воспроизведён. [Отчёт](../reports/AUDIT-Q14-RETAINED-CLEANUP.md). |
| D02 | 14/25 | DONE | Внутренние границы sysctl | Lock/I/O/context, trusted directory, namespace fd pins, исходный per-interface fd/witness и network_cookie v4 проверены. 1995 Linux + 32 privileged + 8 lifecycle и SIGKILL/mismatch worker E2E PASS. Потерянный interface witness сохраняется для ручного recovery; общий persistent firewall/DNS/routes остаётся D04. [Отчёт](../reports/AUDIT-Q25-NAMESPACE-GENERATION.md). |
| D03 | 22/25 | DONE | Самостоятельный kill-switch | Закреплённый namespace, сохранённый владелец точных семейств, fail-closed reconnect и безопасная смена адреса. 11 portable + 2 native регрессии, реальные счётчики IPv4/IPv6 и 2 отказа baseline. [Отчёт](../reports/AUDIT-Q25-KILL-SWITCH-IDENTITY.md). |
| D04 | 14/19/22/25 | DONE | Восстановление после crash | Persistent server firewall, DNS v2, kill-switch и physical routes проверены; legacy global DNS, persistent TUN и потерянный sysctl witness имеют явные безопасные ручные границы. [Клиентская mixed матрица](../reports/AUDIT-Q25-CLIENT-MIXED-FIREWALL.md): 152/152 ячейки, 136 crash/recovery; [серверная](../reports/AUDIT-Q14-MIXED-FIREWALL.md): 16/16, 476 checks повторно PASS. Произвольные zones/policies и multiprofile остаются D10; накопление состояния — D13. |
| D05 | 05/14/25 | IN_PROGRESS | Срок всей операции и блокировки | Panel preflight/health/backup, DNS/NSS, resolver-файлы, startup INI/identity, TOFU/status writers и сетевые workers проверены. В пакете A ниже закрыта композиция команд: 15 секунд NetworkPlan и отдельные общие 15 секунд cleanup через Drop и terminal firewall. Сверены Linux early-Drop/внутренние waits; файловая подготовка hooks/backup закрыта продолжением ниже; штатные server startup/final cleanup и profile teardown вынесены в присоединяемые потоки; TUN/NAT и DNS firewall setup профиля теперь также в присоединяемых потоках; NDP bind теперь также выполняется в worker с регистрацией AsyncFd в исходном runtime; установка до готовности всех listeners получила общий бюджет 120 секунд; повторный допуск после отмены закрыт [Q25-F130](../reports/AUDIT-Q25-SERVER-FORCED-DROP-LEASE.md); остаются async join при forced Drop и общий срок shutdown. [Серверная установка](../reports/AUDIT-Q25-SERVER-SETUP-WORKER.md), [DNS firewall](../reports/AUDIT-Q25-SERVER-DNS-SETUP-WORKER.md), [NDP bind](../reports/AUDIT-Q25-SERVER-NDP-BIND-WORKER.md), [готовность и бюджет](../reports/AUDIT-Q25-SERVER-SETUP-BUDGET.md). Произвольные kernel/fs I/O и forced join не прерываются. [Серверная очистка](../reports/AUDIT-Q25-SERVER-CLEANUP-WORKER.md). [Worker ownership](../reports/AUDIT-Q25-IDENTITY-WORKER.md). |
| D06 | 15/21/22/23/25 | IN_PROGRESS | Контекст внешних сетевых ресурсов | Проверить WAN identity, resolved/bus context, sysfs/procfs и attach/name-контракт; process-global DNS/carrier state, dynamic IPv6. Зафиксировать поддерживаемые комбинации. [Q15-F002](../reports/AUDIT-Q15-UDP-LOCAL-ADDRESS.md) закрывает multi-IP wildcard UDP: локальный endpoint сохранён в receive/reply/roaming/PMTU; [Q25-F131](../reports/AUDIT-Q25-SERVER-WAN-PRESENCE.md) запрещает установку управляемых IPv4/IPv6 правил для отсутствующего WAN; проверка не привязывает активное правило к идентичности устройства. [Q25-F132](../reports/AUDIT-Q25-SERVER-WAN-ECMP.md) использует общий клиентский парсер default routes на сервере и отвергает неоднозначный auto-WAN до forwarding/новых правил. [Q25-F134](../reports/AUDIT-Q25-SERVER-NAT66-EGRESS.md) блокирует off-WAN транзит NAT66: packet-level baseline/fixed и реальный worker проверены. [Q25-F135](../reports/AUDIT-Q25-SERVER-AUTO-WAN-FAILURE.md) запрещает NAT44/NAT66 auto-WAN fallback к одному `route get` при ошибке списка default routes; baseline/fixed worker 2+2 PASS. Packet-тест подтвердил off-WAN утечку NAT44 и то, что blanket DROP ломает LAN за сервером. [Q25-F136](../reports/AUDIT-Q25-SERVER-NAT44-EGRESS.md) добавляет обязательный NAT44 DROP для выхода не через выбранный WAN к назначениям вне RFC1918, сохраняя политику firewall для приватных LAN; nft/legacy packet и worker lifecycle проверены. RFC1918 off-WAN, другие LAN-адресные планы, идентичность активного WAN и runtime-смена маршрутов остаются открыты. Прочие критерии D06 открыты. |
| D07 | 01/05/09/11 | IN_PROGRESS | Серверный конфиг в runtime | Таблица field → parse/validate/runtime/serialize; malformed/oversized input; check-config/startup/SIGHUP/HTTP save/Quick Start с сохранением действующего состояния при отказе. [Q25-F137](../reports/AUDIT-Q25-SERVER-SIGHUP-AUTH.md) закрывает частичное обновление VPN-auth при неверном профиле или users.conf: 1 адресный async-тест с двумя отказами и успешным применением. [Q25-F138](../reports/AUDIT-Q25-SERVER-INI-SIZE.md) вводит общий предел серверного INI 16 МиБ для worker, CLI, панели и restore; 16 loader + 33 editor + 1 backup тест, строгий Clippy и CLI отказ проверены. [Q25-F139](../reports/AUDIT-Q25-SERVER-WEB-LIVE.md) согласует startup-only web-поля и живой CSRF, применяет панельный BF при обычном сохранении и сохраняет lockout при неизменных порогах. [Q25-F140](../reports/AUDIT-Q25-SERVER-INI-PERMISSIONS.md) переводит пять панельных записей INI на приватную атомарную публикацию `0600`; 34 теста редактора, строгий Clippy и проверка mode `0644` → `0600` прошли. [Q25-F141](../reports/AUDIT-Q25-SERVER-CHECK-CONFIG-PARITY.md) согласует отсутствие users.conf и all-disabled для CLI, панели и старта. [Q25-F142](../reports/AUDIT-Q25-SERVER-IDENTITY-NAME.md) запрещает path traversal через имя профиля в default identity-ключе. Остаются полная матрица полей и путей, а также гонка между последним чтением и записью. |
| D08 | 02/24/27 | IN_PROGRESS | Общие клиентские конфиги | Проверить весь контракт 81+3 полей, INI/import/URI/QR/form/store/reconnect через реальные адаптеры; fuzz/budget и конкурентное редактирование. |
| D09 | 14/15/25/32/33 | DONE | Linux lifecycle и системные отказы | [Итоговая сверка](../reports/AUDIT-Q25-LINUX-LIFECYCLE-CLOSURE.md): на текущем SHA 2175 Linux unit, 8 control, 15 hook-process и 8/8 реальных worker lifecycle PASS; сохранены exit/SHA и сетевые снимки до/после. Ранее 48 privileged и реальные DNS/route/firewall матрицы применимы к неизменённым путям. Полные install/upgrade и сетевые сочетания остаются D11/D10, общий shutdown — D05. |
| D10 | 17/18/19/21/22/23 | IN_PROGRESS | Сетевая интеграционная матрица | Проверить off/manual/route/nat66 × NDP, DNS UDP/TCP, multiprofile, iptables/nft/firewalld, setup rollback/stop/restart и сохранение чужих ресурсов. |
| D11 | 00/24/27/34 | IN_PROGRESS | Актуальные native cores и provenance | Из чистого commit пересобрать изменённые ядра по закреплённым рецептам, сравнить A/B, обновить копии и настоящие provenance; проверить ABI/exports и пакеты. [Q25-F133](../reports/AUDIT-Q25-CLIENT-ONLY-BUILD.md) устраняет два client-only compile errors у Linux WAN monitor; client-only, server-only и router binary проверены, но общий D11 ещё открыт. |
| D12 | 24/25/27/34 | IN_PROGRESS | Платформенное подтверждение | Android: 154 JVM + 6 API 34/x86_64 instrumentation PASS со свежим JNI; итоговый снимок ещё требуется. Windows VM, Mac/Xcode/iOS и router runtime **SKIPPED по решению пользователя 24 сентября 2026**: стендов не будет. Эти платформы не сертифицированы; это исключение из текущего объёма, не PASS. |
| D13 | 14/19/22/25 | IN_PROGRESS | Удержание ресурсов под нагрузкой | Измерить fd/tasks/threads/TUN/routes/firewall/journals/RSS до и после churn/reconnect/stop, включая отказы и несколько профилей; конечный deadline и критерии отсутствия роста. |
| D14 | 00/34 | TODO | Текущий benchmark и certification | После корректности выполнить воспроизводимый benchmark нужных режимов с текущим SHA, окружением и метриками; собрать certification только из фактических результатов. Старые результаты 0.8.0 не закрывают 0.8.2. |
| D15 | Все начатые разделы | IN_PROGRESS | Согласование evidence и документации | Сопоставить старые открытые пункты с поздними fixes; проверить применимость патчей, diff/commit и RU/EN ссылки. Каждый долг закрывать отдельным результатом, не числом коммитов. |

## Завершение техдолга: порядок с 25 сентября

По запросу пользователя работа ведётся пакетами, с проверками по риску изменения.
Опорный проверенный снимок — `a8aba986`: 1584 host, 71 config, 2157 Linux,
48 privileged, 8 lifecycle, 38 native cases и 2 recovery; см.
[TOFU worker](../reports/AUDIT-Q25-IDENTITY-WORKER.md). Это результаты указанного
снимка, а не автоматический PASS для будущих изменений.

| Пакет | Группы | Конкретный остаток и условие завершения |
|---|---|---|
| A. Запуск, остановка и системный контекст | D05/D06/D09 | Одним проходом разобрать startup `config_source::load`/metadata/canonicalize, составной бюджет NetworkPlan/cleanup и оставшиеся ранние Drop; закрыть таблицу WAN/resolved/attach/dynamic IPv6. Для каждого пути зафиксировать результат: исправлен и проверен, уже покрыт ссылкой или обоснованное ограничение. Завершить адресными Linux-проверками затронутых границ. |
| B. Конфиги и оставшаяся сетевая совместимость | D07/D08/D10 | Завершить серверную field → parse/validate/runtime/serialize таблицу и клиентский контракт 81+3; покрыть save/reload/import, malformed input и конкурентное редактирование. Выполнить только незакрытые сочетания IPv6/NDP, DNS, multiprofile и firewall; известные исправления включать в один пакет. |
| C. Сборки, Android и ресурсы | D11/D12/D13 | На согласованном чистом commit пересобрать изменённые cores, проверить A/B/ABI/provenance и Android. Один ограниченный прогон churn/reconnect/fault с заранее записанными циклами и критериями роста fd/tasks/threads/RSS/сетевых объектов. Платформенные SKIPPED сохраняются. |
| D. Итоговый прогон и измерения | D14/D15 | Один общий регрессионный прогон итогового кандидата, актуальный benchmark и сверка пакетов/документации. Каждое обязательство получает evidence либо явный нерешённый остаток; непроверенное не объявляется закрытым. |

Пакеты задают последовательность завершения, а не обещание четырёх запусков или срок
в календарных днях. Исправления и короткие проверки выполняются внутри пакета;
переход к следующему не требует нового разрешения пользователя.

### Выбор проверок

- На каждое изменение — тест воспроизведённого дефекта, затронутые тесты модуля и
  необходимая сборка. Docs-only — только docs/link/diff checks, без Rust и лабы.
- Связанные исправления проверяются одним набором. Полный Linux/host набор выполняется
  на границе пакета; полная feature/platform матрица — на итоговом кандидате либо
  раньше при изменении cfg/features/ABI/зависимостей.
- Новые реальные fault/cancel/crash сценарии обязательны при изменении владения
  сетью, ключами или сохраняемым состоянием. Проверять неизменённые транспортные и
  firewall-матрицы после каждого локального исправления не требуется.
- Воспроизведение на старом бинарнике выполняется один раз. Сохранённый baseline
  используется повторно с его SHA; его повтор нужен только при изменении самого
  сценария, предпосылок или обнаруженной неоднозначности.
- Старое evidence переиспользуется только после сверки затронутого кода/зависимостей
  и условий стенда, с указанием исходного SHA и причины применимости. Сборка нового
  бинарника сама по себе не обнуляет все независимые проверки. Финальный кандидат
  всё равно проходит общий прогон.
- Независимые сборки и тесты запускаются параллельно; изменяющие одни и те же
  исходники, target или сетевые ресурсы — последовательно. Успешный прогон без
  последующего релевантного изменения не повторяется.

### Границы и отчётность

Существующие обязательства D01–D15 сохраняются. Новые некритичные улучшения и
неподтверждённые гипотезы записываются в очередь дальнейшего полного аудита и не
расширяют текущий пакет. Подтверждённый дефект безопасности, потери данных/трафика
или основного рабочего сценария включается в пакет с конкретным воспроизводителем.

Непрерываемый системный вызов и принудительный Drop требуют описания поддерживаемой
границы и поведения владельца; сами по себе они не запускают новый цикл аудита.
Обычное зависание, потеря ошибки или оставленная без владельца мутация остаются
обязательными дефектами. Пункт нельзя закрыть простым переименованием в ограничение.

Одна запись результата пакета в этом реестре; отдельный отчёт на каждую небольшую
правку не требуется. Логи, команды и хеши сохраняются машинно, в итоговом тексте —
изменение поведения, закрытые критерии и конечный остаток. Показатель 4/15 относится
к целиком закрытым группам; он не используется как оценка времени или выполненной
работы. Статусы меняются только по результату, не вследствие перестройки плана.

Начальная сверка пакета A на `a8aba986`: `config_source` уже отвергает специальные
файлы через NONBLOCK + fstat и сверяет один открытый снимок. Повторный аудит этих
свойств не нужен без их изменения. Открыты синхронный вызов загрузчика до регистрации
сигналов, отсутствие общего лимита размера в самом загрузчике и startup metadata/
canonicalize. Это конкретные точки проверки; отдельные DNS/route/gateway/kill-switch
бюджеты и joined workers уже имеют evidence. Осталось проверить их композицию и
ранние пути выхода, а не повторять все предыдущие сценарии.

Изменение privileged-ресурса сторонним root между проверкой и записью не обещает
атомарной защиты; это предел интерфейса ОС, а не автоматически новый функциональный
дефект. Однако потеря identity, ошибка команды и неопределённый исход должны сохранять
сведения для восстановления и не давать ложный успешный результат.


### Пакет A — проверенный результат запуска, 25 сентября

Закрыта стартовая часть D05/D09: обработчики stop установлены до чтения INI,
клиентский предел 256 КиБ применяется до чтения/выделения содержимого; загрузка,
capability probes и hook canonicalize выполняются в joined worker. Предупреждение
о правах использует тот же открытый снимок. Stop дожидается принятой операции;
поздняя ошибка не скрывается, credential-команда и подключение не начинаются.

Адресные проверки: 12 host + 32 Linux tests (15 config source, 8 lifecycle,
9 prepared worker), Linux Clippy и standalone client build. На frozen baseline
`a8aba986` воспроизведены блокировка runtime, выход по SIGTERM до обработчика и чтение
oversized-файла. Три исправленных startup-сценария и TCP/UDP startup → post_up → stop
прошли в отдельных NET/mount/PID namespaces; маршруты и operator firewall сохранены.
Первый stop-сценарий ошибочно использовал `pass_cmd`: отказ строгого парсера сохранён,
исправленная фикстура с `password_command` проверена повторно. Регрессия сохранена в
[scripts/audit_client_startup.py](../../../scripts/audit_client_startup.py) и
[test shim](../../../scripts/audit_client_startup_shim.c). Команды, manifests, SHA и логи:
`audit-debt-20260924/batch-a-startup/` в каталоге артефактов `qeli`.

Переиспользован сервер `a8aba986` (SHA256 `c53dec6b…83c97`) и неизменённая teardown-фикстура;
серверная логика этого изменения не касается. Общие прошлые матрицы не объявляются
новым прогоном. D05/D06/D09 пока IN_PROGRESS: остались составной бюджет NetworkPlan/
cleanup, таблица системного контекста и ранние Drop. Установленная граница: невозможно
безопасно оборвать произвольный kernel/filesystem I/O; принудительный Drop сохраняет join.
Это ограничение не закрывает оставшуюся задачу общего командного бюджета.


**Общий командный бюджет (продолжение пакета A).** TUN/gateway/routes/DNS настройки
делят 15 секунд. Rollback/cleanup получает отдельный общий срок; deadline сохраняется
через pump join, worker threads, fallback Drop и terminal firewall cleanup. Ошибки
остаются sticky, а новая попытка после завершения прежних владельцев получает новый бюджет.
Имена владельцев, namespace guards и условие снятия kill-switch не ослаблены.

Проверены 1594 host-теста, 471 адресный Linux-тест и 18 privileged; Linux Clippy,
client-only и server-only builds. В восьми native baseline/fixed сценариях TCP/UDP
последовательные задержки 9+9 секунд на старом `efc9f949` давали 19–20 секунд операции.
Исправленный setup прерывает команды к общему сроку и завершает rollback примерно за
15,9 секунды от первого маркера; cleanup — примерно за 14,8 секунды от маркера первой
мутации (его бюджет начался раньше). Setup оставляет чистую сеть, ошибка cleanup
сохраняет DROP обеих семей и `failed`; чужие правила/routes не изменены. Четыре обычных
TCP/UDP clean/fault shutdown и два явных recovery также PASS. Сценарий:
[audit_network_budget.py](../../../scripts/audit_network_budget.py). Evidence:
`audit-debt-20260924/batch-a-budget/`, source manifest 359 файлов, driver SHA256
`ef126a15…934a4f7`. Сервер `a8aba986` переиспользован; его runtime не объявляется новой сборкой.

Отдельная проверка restart после **timeout gateway** подтвердила границу D02:
утраченный per-interface sysctl witness запрещает автоматическое завершение очистки.
Первое ожидание автоматического recovery дало 2 FAIL и сохранено в `ab3`; это не PASS
восстановления. Проверяется сохранение исходной записи, отсутствие TUN/routes и DROP
обеих семей; ручная процедура — [§6.64](../manuals/TROUBLESHOOTING.md#664-потерян-исходный-sysctl-интерфейса).
Успешные два recovery выше относятся к прежнему route-fault сценарию без утраты witness.

Командная композиция закрыта в этих границах; жёсткий timeout произвольного kernel I/O
не обещается. D05 остаётся IN_PROGRESS до конечной сверки ранних Drop и остальных
внутренних ожиданий; D06 — до проверок ниже. Общий итог групп не изменён: 4/15 DONE.

Сверка D06 с текущим кодом (без заявления новых runtime PASS):

| Граница | Существующее свидетельство / остаток |
|---|---|
| resolved / system bus | GUID/unique owner/network/PID context уже проверены в [resolver context](../reports/AUDIT-Q25-RESOLVER-CONTEXT.md); DNS-маркеры v2 и crash — D04. |
| procfs / sysfs | Namespace pins, cookie и sysctl witness — D02/D04. IPv6 module-disabled читается ограниченно и строго; это не гарантия отсутствия IPv6 в будущем. |
| TUN attach / имена | [Attach](../reports/AUDIT-Q25-TUN-ATTACH.md), lease и route/TUN identity имеют отдельные проверки. `dev_attach` читает `tun_flags` из `/sys/class/net`, который может остаться от прежнего network namespace. [Netlink-снимок ядра](https://github.com/torvalds/linux/blob/master/drivers/net/tun.c) не содержит всех `TUN_FEATURES`, а первый `TUNSETIFF` может их переписать; простой перенос на netlink небезопасен. [Q25-F123](../reports/AUDIT-Q25-TUN-ATTACH-CONTEXT.md) добавляет native same-name/different-netns проверку и отклоняет доказанное расхождение `ifindex` до `TUNSETIFF`. Совпадение индексов не доказывает общий namespace; до namespace-aware чтения полного набора флагов эта комбинация не сертифицирована. |
| Физический WAN | `gateway/wan.rs` возвращает имя из маршрута, firewall сохраняет selector имени. [Q25-F120](../reports/AUDIT-Q25-GATEWAY-IPV6-ROAM.md) повторно проверяет IPv6 default route после rule batch при roaming COMMIT. [Q25-F124](../reports/AUDIT-Q25-EXIT-POLICY-ROUTING.md) воспроизводит off-WAN выход без NAT при policy routing и добавляет fail-closed DROP до установки MARK/NAT, а также lockdown на время cleanup. [Q25-A125](../reports/AUDIT-Q25-WAN-NAME-REUSE.md) подтвердил: смена на другое имя блокируется, но новое устройство со старым именем наследует MARK/NAT без refresh. [Q25-F126](../reports/AUDIT-Q25-WAN-METRIC.md) выбирает default route с минимальной метрикой; отдельную смену exit WAN без VPN COMMIT теперь обрабатывает монитор [Q25-F127](../reports/AUDIT-Q25-EXIT-WAN-MONITOR.md), проверенный на TCP/UDP вместе с cleanup. До identity-bound backend rename/reuse активного WAN не поддерживается; перенос и mixed-backend packet/recovery остаются D06/D10. [Q25-F128](../reports/AUDIT-Q25-EXIT-SELF-WAN.md) запрещает выбирать собственный exit-TUN как WAN до установки правил. [Q25-F129](../reports/AUDIT-Q25-WAN-ECMP.md) отклоняет ECMP и равноприоритетные default routes на разных WAN вместо одного адресного hash bucket; клиентский IPv6 gateway также отказывает до изменения forwarding/RA. |
| DNS / carrier globals | DNS per-link; process-global carrier/cycle защищён одним run_client на процесс до terminal cleanup. Forced Drop закрывает повторный допуск до перезапуска процесса; проверка ниже. |
| Динамический IPv4 | [Q25-F122](../reports/AUDIT-Q25-KILL-SWITCH-DYNAMIC-IPV4.md) запрещает допуск без `iptables` по пустому текущему списку default route; поздний маршрут не обходит отсутствующий firewall. Другие WAN/route сценарии остаются D06/D10. |
| Динамический IPv6 | [Q25-F121](../reports/AUDIT-Q25-KILL-SWITCH-DYNAMIC-IPV6.md) запрещает незащищённый допуск по пустому текущему списку адресов; поздний IPv6 не обходит отсутствующий firewall. Реальная сетевая матрица появления адреса и прочие динамические пути остаются D06/D10. |



**Допуск Linux runtime и сверка ранних выходов (продолжение пакета A).** Устранено
пересечение process-global carrier/cycle state при двух `run_client`: второй вызов
отвергается до конфигурации/сигналов, допуск удерживается до завершения cleanup и
итогового writer. Возвращённая ошибка допускает следующий запуск с обычными проверками
ресурсов. Forced Drop всей future закрывает допуск до перезапуска процесса: вложенные
TaskGroup не гарантируют async join при Drop. Это явная граница отмены, а не заявление
успешной сетевой очистки. [Контракт](../manuals/OPERATIONS.md#один-linux-клиент-на-процесс).

На исходном entry point `b307c913` проверка отказа до чтения отсутствующего INI дала
ожидаемый FAIL: старый вызов дошёл до открытия файла при занятом process gate.
Исправленный entry point и проверки simultaneous admission, terminal ownership,
отмены с работающим ребёнком и panic прошли: 7 host + 85 Linux tests, Linux Clippy.
Три privileged-теста неизменённых namespace workers оставлены ignored в этом адресном
прогоне; новый privileged PASS не заявляется. Окончательные команды/коды/manifest: `audit-debt-20260925/batch-a-instance/`.

Сверка ранних путей Linux-клиента с текущим кодом и прежним evidence:

| Путь / ожидание | Результат и граница |
|---|---|
| Startup/NetworkPlan до adoption | `network_task::Job::Drop` отклоняет результат и присоединяет исходный поток; частичный guard откатывает на нём же. [Network worker](../reports/AUDIT-Q25-NETWORK-TASK.md), startup и бюджет выше. |
| Pump-start / частичный план | При отказе writer reader останавливается и присоединяется; непринятый `(pump, guard)` уничтожается в этом порядке. [Pump start](../reports/AUDIT-Q25-PUMP-START.md). |
| Установленный TUN / обычная ошибка | `TunGuard::shutdown` ждёт DNS → pump → routes/gateway; fallback Drop удерживает TUN fd и общий cleanup deadline. [Teardown](../reports/AUDIT-Q25-TUN-TEARDOWN.md), бюджет выше. |
| TCP/H2/UDP дочерние задачи | Обычные выходы выполняют TaskGroup finish до terminal cleanup; Drop только закрывает admission/запрашивает abort. Forced cancellation всего run_client теперь запрещает повторный запуск в процессе. [TCP](../reports/AUDIT-Q25-TCP-TASKS.md), [H2](../reports/AUDIT-Q25-H2-TASKS.md), [UDP](../reports/AUDIT-Q25-UDP-TASKS.md). |
| TOFU/status / файловый I/O | finish ждёт worker; fallback Drop синхронно join. Sender/queue mutex не удерживается во время файловой операции. [TOFU](../reports/AUDIT-Q25-IDENTITY-WORKER.md), [status](../reports/AUDIT-Q25-STATUS-WRITER.md). |
| Внутренние locks / ожидания | Carrier/core/diagnostic state меняется под короткими mutex без await; очереди writer освобождают mutex перед внешним I/O. TunWorkers удерживает join lock до всех потоков специально, чтобы отмена не оставляла fd без владельца. [TUN workers](../reports/AUDIT-Q25-TUN-WORKERS.md). Непрерываемые kernel/fs I/O и forced join остаются описанной границей, не обещанием 15-секундного process exit. |

Это закрывает сверку перечисленных Linux early-Drop путей и process-global допуска.
На этом этапе D05/D06/D09 не закрывались: файловая подготовка hooks и backup
требовала runtime воспроизведения. Она закрывается следующим продолжением пакета ниже;
серверные setup/cleanup ещё требуют проверки.
WAN/dynamic IPv6 остаются в D06; никакие новые платформенные или сетевые packet PASS не заявляются.



**Файловый I/O hooks и backup (продолжение пакета A).** Подтверждены и исправлены
блокировки executor при записи/удалении hook context и чтении активного INI для backup.
Hooks владеют подготовкой, command runtime и cleanup в одном присоединяемом потоке;
отмена до запуска не выполняет команду, отмена работающего shell ждёт terminate/reap
до удаления context. Backup preflight выполняется в существующем blocking worker с
config lease; отмена HTTP-запроса не освобождает её раньше операции. Общий загрузчик
отвергает FIFO и проверяет стабильность исходного файла. Права исполнения hooks и
форматы INI/API не менялись.

Проверки: **37 host + 77 Linux tests, 8 native-сценариев PASS**, Linux Clippy и отдельные
client/server builds. Воспроизводитель задерживает настоящий write/unlink/read на 2 секунды:
исходные обработчики `0645a8b0` дают 0/0/2 heartbeat тика (3 ожидаемых FAIL), исправленные —
178/178/179. Отмена подготовки не создаёт marker запуска; отмена работающего hook подтверждает
reap/отсутствие процесса и удаление context. Отменённый backup удерживает config lease,
сохраняет конфиг и даёт 178 тиков. Backup → overlay/exact restore и отказ неполного rollback
snapshot проверены в приватных NET/mount/PID namespace и tmpfs `/etc/qeli`, `/tmp`.
Shim: [audit_hook_backup_io_shim.c](../../../scripts/audit_hook_backup_io_shim.c).
Логи/команды/manifest 362 исходных файлов:
`audit-debt-20260925/batch-a-file-io/`; fixed test binary SHA256 `208e91b7…500bba`.
Baseline — исходные обработчики с новым тестовым harness, не старый выпущенный бинарник.

Этот остаток hooks/backup закрыт; D05 целиком остаётся IN_PROGRESS. Сверка server-кода
уточнила следующий пакет: `run_worker` вызывает `nat::cleanup_all` синхронно;
`run_profile_generation` выполняет TUN/NAT setup, а штатный `run_profile` вызывает
`drop(ProfileTeardown)` с NAT cleanup/worker joins на async-пути. Компонентные сроки NAT
уже проверены; scheduler isolation и составной срок профиля ещё требуют проверки.
Непрерываемые kernel/fs вызовы и forced join не объявляются жёстко ограниченными таймером.
D06 WAN/dynamic IPv6 и остальные группы сохраняются; итог **4/15 DONE**.

### Q25-F115 — серверная очистка вне async executor

Синхронные `nat::cleanup_all`, штатный `ProfileTeardown::drop`, итоговые
NAT sweep/ownership check и `usage.flush` выполняются в присоединяемых потоках.
Отмена ожидающего async-кода ждёт рабочий поток, поэтому network namespace lease и
профильные ресурсы не освобождаются до завершения принятой очистки. Порядок
остановки дочерних задач, удаления регистрационной записи, NAT и TUN сохранён;
ошибка worker входит в `Outcome`. [Отчёт](../reports/AUDIT-Q25-SERVER-CLEANUP-WORKER.md).

На host: 1602 теста PASS, 1 заранее ignored; Linux cross-check и all-targets Clippy
PASS. В лабе `.11` 10 адресных Linux-тестов и восемь реальных TCP/UDP ×
`off`/`manual`/`route`/`nat66` lifecycle-сценариев и 2 bind-failure/rollback/retry сценария PASS в частных пространствах
NET/mount/PID. Точный manifest/логи: `audit-debt-20260925/server-cleanup-phase/`.
D05 остаётся IN_PROGRESS: синхронная TUN/NAT setup, аварийный Drop, составной
срок профиля и непрерываемые системные вызовы ещё требуют отдельного решения.
Итого по реестру **4/15 DONE**.

### Q25-F116 — установка TUN/NAT серверного профиля вне executor

Создание и настройка TUN выполняются в первом присоединяемом worker: до
передачи результата непостоянный TUN принадлежит его исходным fd. После принятия
очередей `ProfileTeardown` владеет ими, и только затем отдельный worker запускает
NAT/IPv6 setup. Отмена ожидания присоединяет выполняющийся поток перед Drop
внешнего guard. [Отчёт](../reports/AUDIT-Q25-SERVER-SETUP-WORKER.md).

1603 host-теста PASS, 1 заранее ignored; 11 адресных Linux-тестов, Linux
all-targets Clippy и реальные 8 штатных + 2 bind-failure/retry сценария в
приватных пространствах `.11` PASS. Снимок/логи:
`audit-debt-20260925/server-setup-phase/`. D05 остаётся IN_PROGRESS: DNS INPUT
firewall, NDP bind, аварийный Drop и составной срок всех операций не закрыты.
Реестр: **4/15 DONE**.

### Q25-F117 — DNS firewall серверного профиля вне executor

Обе установки DNS INPUT/REDIRECT выполняются на присоединяемом worker.
Отменённое ожидание закрывает канал принятия; непринятый `DnsInputLease`
уничтожается в исходном namespace до Drop внешнего guard. Принятый lease
передаётся `ProfileTeardown`. [Отчёт](../reports/AUDIT-Q25-SERVER-DNS-SETUP-WORKER.md).

1603 host-теста PASS, 1 заранее ignored; 11/11 Linux адресных тестов,
22/22 recovery/ownership/SIGKILL checks, 4/4 TCP/UDP × IPv6 `manual`/`route`
DNS сценария в приватных пространствах `.11` PASS. Логи и manifest:
`audit-debt-20260925/server-dns-setup-phase/`. D05 остаётся IN_PROGRESS:
NDP bind, аварийный Drop и общий срок установки открыты. Реестр: **4/15 DONE**.

### Q25-F118 — NDP bind вне executor

`AF_PACKET` bind и socket-local multicast выполняются в присоединяемом
worker; после принятия `OwnedFd` регистрируется как `AsyncFd` в исходном
Tokio runtime. Отмена закрывает непринятый fd до уничтожения внешнего guard.
[Отчёт](../reports/AUDIT-Q25-SERVER-NDP-BIND-WORKER.md).

В `.11`: 5 NDP unit, 1 privileged namespace, 8 lifecycle и 22 recovery checks
PASS; Linux Clippy для library/binary и rustfmt PASS. Исходник и логи:
`audit-debt-20260925/server-ndp-bind-phase/`. D05 остаётся IN_PROGRESS:
общий срок, принудительный Drop и непредсказуемые kernel/fs I/O.
Реестр: **4/15 DONE**.

### Q25-F119 — общий срок server setup и готовность всех listeners

120-секундный бюджет действует от начала поколения до подтверждения bind
основного и всех дополнительных listeners; после готовности профиль служит
без этого таймера. UDP сообщает готовность после всей группы SO_REUSEPORT.
Ошибки bind передаются только установке, не маскируются под ошибку cleanup.
[Отчёт](../reports/AUDIT-Q25-SERVER-SETUP-BUDGET.md).

На `.11`: 2 новых + 11 worker-тестов, 8 lifecycle, 4 occupied-bind
rollback/retry/stop и 22 recovery checks PASS; Linux Clippy library/binary,
rustfmt и docs checks PASS. Первый отказ и исправленный прогон сохранены в
`audit-debt-20260925/server-setup-budget-phase/`. D05 остаётся IN_PROGRESS:
forced Drop, общий срок shutdown и непрерываемый kernel/fs I/O.
Реестр: **4/15 DONE**.

### D09 — итоговая Linux lifecycle сверка, 25 сентября

[Отчёт](../reports/AUDIT-Q25-LINUX-LIFECYCLE-CLOSURE.md) связывает текущий полный
Linux-набор (2175 PASS), 8 control и 15 hook-process тестов с восемью реальными
worker-сценариями. У каждого сохранены raw-снимки firewall/routes/links/forwarding
до и после, бинарный и сценарный SHA, stdout и exit. Первый дополнительный
снимок ложно сработал на пустые builtin таблицы xtables-nft; исходные дампы
сохранены, правило сравнения исправлено. Первый полный набор упал с EMFILE при
nofile=1024 на тесте 512 TCP-соединений; неизменённый код прошёл при nofile=4096.
Предыдущие privileged/DNS/route/crash прогоны сверены с неизменёнными путями.
**D09 DONE; реестр: 5/15 DONE (33,3%), 8 IN_PROGRESS, 2 TODO.**
Установка/обновление и systemd runtime остаются отдельными пунктами полного аудита
и D11; D05/D06/D10 не меняют статус.

### Q25-F130 — допуск server worker после отмены

После первой сетевой мутации forced Drop или неподтверждённый terminal result
удерживает network-namespace lease до выхода процесса. Ранний отказ и успешная
штатная остановка освобождают его; новый worker не допускается поверх
незавершённого поколения. [Отчёт и проверки](../reports/AUDIT-Q25-SERVER-FORCED-DROP-LEASE.md).
Это частичное закрытие D05: async join дочерних задач при forced Drop и общий
срок shutdown остаются открытыми. Реестр: **5/15 DONE**.

### Q25-F131 — наличие WAN при серверной установке

Выбранный IPv4 NAT или управляемый IPv6 uplink теперь проверяется через ioctl
в network namespace worker до включения forwarding и добавления правил.
[Отчёт и 1 unit + 8 штатных + 2 отрицательных Linux-прогона](../reports/AUDIT-Q25-SERVER-WAN-PRESENCE.md).
Открыты повторное использование имени активного WAN, атомарная привязка правил
к устройству и mixed-backend recovery. D06 остаётся IN_PROGRESS; реестр **5/15 DONE**.

### Q25-F132 — неоднозначный auto-WAN на сервере

Общий с клиентом парсер default routes обнаруживает ECMP и равную лучшую метрику
разных WAN. Серверный auto-режим отказывает до forwarding и новых правил;
[отчёт: 11 parser + 1 WAN unit, 8 обычных и 2 отрицательных Linux-сценария](../reports/AUDIT-Q25-SERVER-WAN-ECMP.md).
Явный WAN, отдельные policy routes и runtime-смена остаются D06/D10;
реестр **5/15 DONE**.

### Q25-F133 — сборка клиентского ядра без roaming feature

Монитор exit WAN работает на Linux независимо от experimental-roaming, но имя
TUN в TCP и UDP объявлялось только под этим feature. Сборка client-only
падала с двумя E0425; область объявления расширена до Linux.
[Отчёт, baseline FAIL и исправленные feature-сборки](../reports/AUDIT-Q25-CLIENT-ONLY-BUILD.md).
Клиентский router binary собран и запущен с --help; платформенный runtime
и provenance остаются D11/D12. Реестр **5/15 DONE**.

### Q25-F134 — NAT66 только через выбранный WAN

При разрешающем хостовом FORWARD прежний пакет из TUN мог выйти через другой
WAN без MASQUERADE. Обязательный per-profile DROP ставится до разрешений и
охватывает весь TUN. [Отчёт: 16 NAT tests, Clippy/build, packet baseline/fixed,
1 реальный worker с точной очисткой](../reports/AUDIT-Q25-SERVER-NAT66-EGRESS.md).
IPv4 NAT44 и server-side LAN требуют отдельного решения контракта; повторное
использование WAN-имени и mixed backend остаются D06/D10. Реестр **5/15 DONE**.

### Q25-F135 — NAT auto-WAN без списка default routes

NAT44/NAT66 больше не переходят к одному `route get` при ошибке или отсутствии
пригодного списка default routes: это был обход отказа от ECMP. [Отчёт:
18 NAT tests, 2/2 baseline startup и 2/2 fixed refusal до сетевых мутаций](../reports/AUDIT-Q25-SERVER-AUTO-WAN-FAILURE.md).
Пакетный опыт отдельно подтвердил незакрытую NAT44 off-WAN утечку и нужный
LAN-путь, который безусловный DROP также блокирует. Контракт LAN-исключений,
явный `eth0`, runtime WAN identity и mixed backend остаются D06/D10;
реестр **5/15 DONE**.


### Q25-F136 — NAT44 вне выбранного WAN и приватные сети

[Отчёт](../reports/AUDIT-Q25-SERVER-NAT44-EGRESS.md): обязательный guard
отсекает не-RFC1918 трафик из TUN на чужом интерфейсе до разрешений хоста,
не меняя firewall-политику RFC1918 LAN. Пакетный прогон на nft/legacy
подтверждает DROP, LAN без NAT и MASQUERADE на выбранном WAN; реальный
worker проверяет установку и точную очистку. RFC1918 off-WAN, LAN вне
RFC1918, policy WAN и смена идентичности интерфейса остаются D06/D10;
реестр **5/15 DONE**.


### Q25-F137 — SIGHUP применяет VPN-auth только после общей проверки

[Отчёт](../reports/AUDIT-Q25-SERVER-SIGHUP-AUTH.md): сначала
`validate_profiles` и загрузка эффективной базы пользователей, затем
обновление пользователей и brute-force порогов. Ошибка любого источника
оставляет обе живые части прежними. Прямой async-тест охватил неверный
`tun.mtu`, повреждённый `users.conf` и успешное применение; D07 остаётся
**IN_PROGRESS** до полной матрицы путей и size bounds. Реестр **5/15 DONE**.

### Q25-F138 — единый предел серверного INI

[Отчёт](../reports/AUDIT-Q25-SERVER-INI-SIZE.md): worker, CLI и панель
отказывают в чтении server INI свыше 16 МиБ; форма, raw INI, Quick Start,
настройки brute-force и restore не публикуют сверхлимитный результат.
При ошибке чтения активного файла редактор не подставляет стартовую копию.
16 loader + 33 editor + 1 backup тест, строгий Clippy и фактический
`check-config` на 16 МиБ + 1 байт прошли. D07 остаётся **IN_PROGRESS**;
реестр **5/15 DONE**.

### Q25-F139 — согласованное живое состояние панели

[Отчёт](../reports/AUDIT-Q25-SERVER-WEB-LIVE.md): при сохранении нового
`web.port`/`bind`/TLS текущий listener и проверки CSRF остаются на стартовых
значениях до полного рестарта. Изменение `[web] brute_force` через общую форму
или INI применяет новые пороги сразу; прежний lockout сохраняется при
неизменной политике. Прямой async-тест и строгий Clippy прошли. D07 остаётся
**IN_PROGRESS**; реестр **5/15 DONE**.

### Q25-F140 — права активного серверного INI после сохранения панели

[Отчёт](../reports/AUDIT-Q25-SERVER-INI-PERMISSIONS.md): все пять путей
панельной записи публикуют серверный INI с режимом `0600` независимо от
старых прав. Прямой Linux-тест с исходным `0644`, 34 теста редактора и строгий
Clippy прошли. D07 остаётся **IN_PROGRESS**; реестр **5/15 DONE**.

### Q25-F141 — одинаковый допуск серверного INI

[Отчёт](../reports/AUDIT-Q25-SERVER-CHECK-CONFIG-PARITY.md): baseline на
лабе `.11` выявил расхождение `check-config` с runtime при отсутствующем
`users.conf` и ложный `OK` при всех выключенных профилях. CLI, supervisor,
worker и панель используют согласованные правила; адресный unit-тест, CLI и
startup-проверки, строгий Clippy прошли. D07 остаётся **IN_PROGRESS**; реестр
**5/15 DONE**.

### Q25-F142 — имя профиля и default identity-путь

[Отчёт](../reports/AUDIT-Q25-SERVER-IDENTITY-NAME.md): baseline `check-config`
принял `[profile:../escape]`, что вывело бы путь приватного ключа из
`/etc/qeli/identity`. Парсер, панель и прямые key-helper'ы теперь отвергают
разделители пути. Два unit-теста, серверный INI-аудит, строгий Clippy и CLI
пара на лабе `.11` прошли. D07 остаётся **IN_PROGRESS**; реестр **5/15 DONE**.

## Источники

- [AUDIT-Q01-SERVER-INI](../reports/AUDIT-Q01-SERVER-INI.md)
- [AUDIT-Q02-CLIENT-PARSERS](../reports/AUDIT-Q02-CLIENT-PARSERS.md)
- [AUDIT-Q05-PREFLIGHT](../reports/AUDIT-Q05-PREFLIGHT.md)
- [AUDIT-Q14-CONTROL](../reports/AUDIT-Q14-CONTROL.md)
- [AUDIT-Q14-DNS-OWNERSHIP](../reports/AUDIT-Q14-DNS-OWNERSHIP.md)
- [AUDIT-Q14-H2-TASKS](../reports/AUDIT-Q14-H2-TASKS.md)
- [AUDIT-Q14-HOOKS](../reports/AUDIT-Q14-HOOKS.md)
- [AUDIT-Q14-IPV6-PARTIAL-ACQUIRE](../reports/AUDIT-Q14-IPV6-PARTIAL-ACQUIRE.md)
- [AUDIT-Q14-NAT-CLEANUP](../reports/AUDIT-Q14-NAT-CLEANUP.md)
- [AUDIT-Q14-NAT-COMMANDS](../reports/AUDIT-Q14-NAT-COMMANDS.md)
- [AUDIT-Q14-OWNED-SHUTDOWN](../reports/AUDIT-Q14-OWNED-SHUTDOWN.md)
- [AUDIT-Q14-PROFILE-SHUTDOWN](../reports/AUDIT-Q14-PROFILE-SHUTDOWN.md)
- [AUDIT-Q14-Q15-WORKER-USAGE](../reports/AUDIT-Q14-Q15-WORKER-USAGE.md)
- [AUDIT-Q14-Q19-LIFECYCLE](../reports/AUDIT-Q14-Q19-LIFECYCLE.md)
- [AUDIT-Q14-Q25-FIREWALL-CHECKS](../reports/AUDIT-Q14-Q25-FIREWALL-CHECKS.md)
- [AUDIT-Q14-Q32-NOTIFICATIONS](../reports/AUDIT-Q14-Q32-NOTIFICATIONS.md)
- [AUDIT-Q14-Q33-CONFIG-TRUST](../reports/AUDIT-Q14-Q33-CONFIG-TRUST.md)
- [AUDIT-Q14-SUPERVISOR](../reports/AUDIT-Q14-SUPERVISOR.md)
- [AUDIT-Q14-SYSCTL-RECOVERY](../reports/AUDIT-Q14-SYSCTL-RECOVERY.md)
- [AUDIT-Q19-DNS-CACHE](../reports/AUDIT-Q19-DNS-CACHE.md)
- [AUDIT-Q19-DNS-EDNS](../reports/AUDIT-Q19-DNS-EDNS.md)
- [AUDIT-Q19-DNS-PROXY](../reports/AUDIT-Q19-DNS-PROXY.md)
- [AUDIT-Q19-Q22-NETWORK-PLAN](../reports/AUDIT-Q19-Q22-NETWORK-PLAN.md)
- [AUDIT-Q25-CLIENT-COMMANDS](../reports/AUDIT-Q25-CLIENT-COMMANDS.md)
- [AUDIT-Q25-CLIENT-NAMESPACE](../reports/AUDIT-Q25-CLIENT-NAMESPACE.md)
- [AUDIT-Q25-CORE-LIFECYCLE](../reports/AUDIT-Q25-CORE-LIFECYCLE.md)
- [AUDIT-Q25-CREDENTIAL-COMMANDS](../reports/AUDIT-Q25-CREDENTIAL-COMMANDS.md)
- [AUDIT-Q25-DNS-LEASES](../reports/AUDIT-Q25-DNS-LEASES.md)
- [AUDIT-Q25-DNS-RECOVERY](../reports/AUDIT-Q25-DNS-RECOVERY.md)
- [AUDIT-Q25-EXIT-OWNERSHIP](../reports/AUDIT-Q25-EXIT-OWNERSHIP.md)
- [AUDIT-Q25-GATEWAY-IDENTITY](../reports/AUDIT-Q25-GATEWAY-IDENTITY.md)
- [AUDIT-Q25-GATEWAY-ROLLBACK](../reports/AUDIT-Q25-GATEWAY-ROLLBACK.md)
- [AUDIT-Q25-GATEWAY-WAN](../reports/AUDIT-Q25-GATEWAY-WAN.md)
- [AUDIT-Q25-H2-TASKS](../reports/AUDIT-Q25-H2-TASKS.md)
- [AUDIT-Q25-KILL-SWITCH-LIFETIME](../reports/AUDIT-Q25-KILL-SWITCH-LIFETIME.md)
- [AUDIT-Q25-NETWORK-CLEANUP](../reports/AUDIT-Q25-NETWORK-CLEANUP.md)
- [AUDIT-Q25-PASSWORD-FILES](../reports/AUDIT-Q25-PASSWORD-FILES.md)
- [AUDIT-Q25-PATH-MONITOR](../reports/AUDIT-Q25-PATH-MONITOR.md)
- [AUDIT-Q25-ROUTE-IDENTITY](../reports/AUDIT-Q25-ROUTE-IDENTITY.md)
- [AUDIT-Q25-ROUTE-OUTCOME](../reports/AUDIT-Q25-ROUTE-OUTCOME.md)
- [AUDIT-Q25-ROUTE-OWNERSHIP](../reports/AUDIT-Q25-ROUTE-OWNERSHIP.md)
- [AUDIT-Q25-ROUTE-PENDING](../reports/AUDIT-Q25-ROUTE-PENDING.md)
- [AUDIT-Q25-ROUTE-POSTCONDITIONS](../reports/AUDIT-Q25-ROUTE-POSTCONDITIONS.md)
- [AUDIT-Q25-ROUTE-SCOPE](../reports/AUDIT-Q25-ROUTE-SCOPE.md)
- [AUDIT-Q25-SETUP-FLUSH](../reports/AUDIT-Q25-SETUP-FLUSH.md)
- [AUDIT-Q25-SETUP-IDENTITY](../reports/AUDIT-Q25-SETUP-IDENTITY.md)
- [AUDIT-Q25-SYSCTL-NAMESPACE](../reports/AUDIT-Q25-SYSCTL-NAMESPACE.md)
- [AUDIT-Q25-SYSCTL-OWNER-EVIDENCE](../reports/AUDIT-Q25-SYSCTL-OWNER-EVIDENCE.md)
- [AUDIT-Q25-SYSTEM-COMMANDS](../reports/AUDIT-Q25-SYSTEM-COMMANDS.md)
- [AUDIT-Q25-TCP-TASKS](../reports/AUDIT-Q25-TCP-TASKS.md)
- [AUDIT-Q25-TUN-ADMISSION](../reports/AUDIT-Q25-TUN-ADMISSION.md)
- [AUDIT-Q25-TUN-ATTACH](../reports/AUDIT-Q25-TUN-ATTACH.md)
- [AUDIT-Q25-TUN-CLEANUP](../reports/AUDIT-Q25-TUN-CLEANUP.md)
- [AUDIT-Q25-TUN-LIFETIME](../reports/AUDIT-Q25-TUN-LIFETIME.md)
- [AUDIT-Q25-TUN-WORKERS](../reports/AUDIT-Q25-TUN-WORKERS.md)
- [AUDIT-Q25-TUNNEL-ROUTES](../reports/AUDIT-Q25-TUNNEL-ROUTES.md)
- [AUDIT-Q25-UDP-TASKS](../reports/AUDIT-Q25-UDP-TASKS.md)

D02/D05: [чтение sysctl-журнала и lock waits](../reports/AUDIT-Q25-SYSCTL-JOURNAL-IO.md) исправлены в описанных границах; остальные критерии строк остаются открыты.

D03: [kill-switch namespace / reconnect](../reports/AUDIT-Q25-KILL-SWITCH-IDENTITY.md).

D02/D06: [namespace-aware link observation](../reports/AUDIT-Q25-LINK-OBSERVATION.md).

D05: [async preflight и время жизни транзакции панели](../reports/AUDIT-Q05-PANEL-TRANSACTIONS.md). Бюджет backup/restore закрыт следующим этапом; остальные сетевые последовательности открыты.

Обновление D05/D09: [бюджет backup/restore и полнота снимка](../reports/AUDIT-Q05-ARCHIVE-BUDGET.md). Остальные сетевые последовательности и filesystem fault E2E остаются открытыми.

D02: [guard внутренних границ sysctl](../reports/AUDIT-Q25-SYSCTL-CONTEXT-IO.md); durable namespace identity и исходный интерфейс ещё открыты; parent trust закрыт последующим этапом.

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

D05/D09: [Q25-F111 — последовательный writer диагностики](../reports/AUDIT-Q25-STATUS-WRITER.md): один поток, один ожидающий снимок, join итоговой записи; файловый I/O вне async-потока. 5 новых portable + 1 privileged тест; 2 baseline + 4 fixed fsync-сценария, 2 baseline + 4 fixed TCP/UDP teardown и 2 recovery PASS. 1569 host + 71 config; 2133 Linux + 48 privileged + 8 lifecycle PASS. D05 открыт: остальные locks/I/O, ранний Drop и общий deadline. **Техдолг: 4/15 DONE (26,7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F112/F113 — файлы идентичности](../reports/AUDIT-Q25-IDENTITY-FILES.md): ID загружается один раз в joined worker, временный ID стабилен при reconnect; TOFU ограничен 1 MiB, повреждение/конфликт пинов запрещает новое доверие, запись атомарна. 15 новых тестов; 8 baseline + 8 fixed identity cases, 6 teardown cases и 2 recovery PASS. 1575 host + 71 config; 2148 Linux + 48 privileged + 8 lifecycle PASS. D05 открыт: синхронный TOFU, другие startup I/O/Drop и общий deadline. **Техдолг: 4/15 DONE (26,7%), 9 IN_PROGRESS, 2 TODO.**

D05/D09: [Q25-F114 — TOFU worker](../reports/AUDIT-Q25-IDENTITY-WORKER.md): файлы доверия обрабатываются в одном присоединяемом потоке; отмена и timeout не оставляют запись без владельца, поздний отказ сохраняется до terminal result. 9 portable regressions; 16 worker cases + 16 файловых + 6 teardown и 2 recovery PASS. 1584 host + 71 config; 2157 Linux + 48 privileged + 8 lifecycle PASS. Общий deadline и другие startup I/O/Drop остаются D05. **Техдолг: 4/15 DONE (26,7%), 9 IN_PROGRESS, 2 TODO.**
