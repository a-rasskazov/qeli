# Q31: управление LuCI, публикация INI и ошибки firewall

<!-- normative-sync: q31-openwrt-controls-v5 -->

6 октября 2026. Исправления продукта F307–F309 и сверка теста F310. Q31 переведён
из TODO в IN_PROGRESS; ни полный критерий, ни роутерный runtime не закрыты.
Всего28/37(75.7%),осталось9. Q29 SIGKILL FAIL/auto-null ENONET, исключённые Apple
запуски и callback-drain OPEN Q30, D06 ACCEPTED_LIMITATION сохранены.

## F307: команда службы выполнялась раньше применения UCI

Connect/Disconnect записывали `enabled` через `uci.save()`, вызывали службу и лишь
затем запускали модальное применение. Изменения UCI в сессии отличаются от
применённого конфига, который читает root init. Поэтому Connect отключённого
профиля мог ничего не сделать, а параллельные кнопки перемешивали старый start
и новый stop. Модальный помощник не предоставляет ожидаемый барьер commit.

Три кнопки теперь используют общую очередь Promise. Connect/Disconnect сохраняют
и ждут commit/подтверждение `uci.apply()` перед enable/start либо stop/disable.
Ошибка save/apply останавливает дальнейшие команды; следующий запрос после
ошибки работает. Restart ждёт очередь. Гарантия относится к одной открытой
странице, не к другим вкладкам/RPC-клиентам или сохранению формы. Ошибка службы
после commit не откатывает сохранённое намерение автозапуска и возвращается UI.
Как и прежнее применение, UCI apply может применить другие staged-пакеты.
Несохранённые поля формы сначала требуют Save & Apply.

Поведение сверено с первичными исходниками LuCI:
[UCI save/apply](https://openwrt.github.io/luci/jsapi/uci.js.html) и
[модальный changes.apply](https://openwrt.github.io/luci/jsapi/ui.js.html).
Семь Node-тестов выполняют настоящий модуль с управляемыми UCI/RPC Promise:
порядок commit, отключение, ошибки save/apply, восстановление очереди,
пересечение трёх команд, ошибка enable и неизвестная команда. Настоящие rpcd/procd
эти тесты не запускают.

## F308: ошибки синхронизации firewall скрывались

Live init игнорировал ошибки delete/add-list/set/commit/reload. Одного проброса
ошибки недостаточно: следующий запуск может увидеть staged-значения UCI и
ошибочно пропустить commit/reload. Перед изменениями теперь создаётся root-only
маркер tmpfs `firewall-pending`. Он сохраняется при ошибке и удаляется после
успешного commit/reload. Повторный запуск сверяет текущий желаемый dev и повторяет
незавершённые операции. Чистый no-op не делает commit/reload. Ошибка не допускает
создания procd instance; ошибка создания каталога состояния тоже возвращается.
Тесты не вызывали существующую службу firewall.

Это не транзакция с rollback: частично staged-изменения могут остаться до повтора,
другие администраторы и независимые init-процессы не блокируются. Одноразовые
install defaults и настоящий жизненный цикл fw4 остаются следующей частью Q31.

## F309: неполный INI заменял прежний конфиг

Генерация обнуляла живой файл и скрывала ранние ошибки записи. Некорректный MTU
из UCI мог исчезать вместо отказа, а выход за диапазон доходил до ядра. Теперь
создаётся соседний0600-файл tmpfs, записи проверяются, результат публикуется
атомарным rename. Обычная ошибка удаляет временный файл и сохраняет прежний INI.
MTU допускает десятичный0(auto) либо576..16602, как ядро/LuCI. Убийство процесса
может оставить0600-временный файл до reboot; уборка после SIGKILL и конкурентный
жизненный цикл не квалифицированы.

Пользовательские значения выводятся printf с фиксированным форматом. Обратные
слеши остаются буквальными; C0/DEL удаляются из несекретных INI-значений. CLI
секреты также отклоняют DEL, согласованно с rpcd. Исходный BusyBox уже сохранял
буквальные слеши: воспроизведённая escape-инъекция на OpenWrt не заявляется.
Printf также устраняет интерпретацию echo на других shell, например dash.
Пароль остаётся отдельным0600-файлом tmpfs; JSON-конфиги не добавлены.

Десять Python-тестов вызывают настоящие init-функции с mock UCI/firewall в новом
временном каталоге. BusyBox ash и dash PASS: генерация/DNS/router guard, безопасный
вывод значений, malformed/граничный MTU, ранняя ошибка записи/публикации,
секрет ровно4096байт и неверные секреты, no-op миграции, no-op firewall, пять
путей ошибки/повтора mutation/reload, namespace устройства. Ошибки исходного
BusyBox сохранены отдельно. Настоящий UCI parser OpenWrt, stdin RPC-секретов и
сетевой firewall этими тестами не подменяются. /etc, работающие службы, TUN и
management route не менялись; тесты выполнялись только в отдельном `/var/tmp`
каталоге лабы .11.

## F310: устаревшая проверка Android сломала gate рецептов

Набор37 тестов ожидал старую nullable-цепочку имени пользователя. Уже в базовом
коммите Android один раз захватывает `activeConfig`, проверяет stopping/null/
current core под monitor службы, затем логирует `logValue(config.username)`.
Перед исправлением тест и продукт совпадали с базовым коммитом: сбой появился
раньше Q31. Assertion обновлён на текущий захват/санитайзер; код Android не менялся.
Все37 тестов PASS. Это проверка исходника, не runtime-тест логирования и не новый
фикс Android.

## Границы и оставшаяся работа

Первично разобраны init renderer/live firewall sync, кнопки LuCI, ACL/rpcd транспорт
секретов, package defaults и точки входа роутерных сборок. ACL по-прежнему
ограничивает запись UCI пакетом qeli и собственными командами; service list доступен
только для чтения. RPC-секреты передаются stdin, не argv. Дополнительного удаления
кода этот пакет не обосновал; полный review/dead-code остаётся открытым.

Далее: ошибки install/upgrade и rollback, кэш UI-статуса/несохранённая форма,
межпроцессные гонки секретов/службы, ошибки/provenance build-helper и доступные
cross-build проверки. Артефакты сейчас не пересобирались; реализация Rust/native/
Android/Apple/Windows клиентов не менялась. Реальные роутерные WAN renewal/reboot,
память/throughput и сетевой runtime USER_EXCLUDED; cross-build не будет называться
квалификацией устройства.

Документация/bindings/diff проверяются вместе с fixtures. Исторические статусы,
артефакты, даты и acceptance_basis Linux-кейсов сохранены; source digest обновлён
только с отдельным ограниченным supplement этого изменения.

Raw packet: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-openwrt-controls-20261006.
Evidence: release/certification/evidence/q31-openwrt-controls-20261006.json.

## F311: ошибки подготовки и восстановления manifest обходили cleanup

Команды toolchain скрывали ошибки rustup через tail/true; exit Zig тоже игнорировался.
Оба скрипта теперь проверяют каждую команду и inventory cargo-zigbuild0.23.0. Nightly/
rust-src готовятся только для выбранного MIPS; другим аркам лишний nightly не ставится.
Cargo использует --locked. Неизвестная архитектура, лишний аргумент и неизвестный флаг
отклоняются до SSH: опечатка больше не запускает все сборки. Rolling nightly/stable
этим не закреплены; reproducibility, ABI и текущая поддержка MIPS не квалифицированы.

Всё время жизни подключения теперь покрыто finally-close. Backup прерванной сборки
восстанавливается до --sync: поздний restore больше не заменяет новый загруженный
Cargo.toml прежней версией. После успешного ограничения crate-type manifest
восстанавливается; даже ошибка восстановления не пропускает закрытие соединения.
SFTP закрывается при сбое put/inventory; ошибки cleanup/mkdir пробрасываются,
Cargo.toml/Cargo.lock обязательны. Sync ещё не атомарный и не точный: удалённые
remote modules, .cargo/config.toml, параллельная работа в общем checkout и полная
source provenance остаются OPEN.

## F312: ошибка скачивания не мешала KEENETIC_BUILD PASS

Keenetic pull проглатывал IOError, оставляя результат сборки0. Исходный main
воспроизведён с отказом скачивания: exit0 и PASS. Ошибка подготовки также оставляла
SSH открытым, а ошибки toolchain не возвращались вызывающему коду. Исправленный
main даёт1 при отказе скачивания, закрывает соединение и отклоняет ошибку подготовки.
Оба скрипта используют общий проверяемый атомарный transfer native_lab: SHA256
получается по strict SSH, скачанные байты проверяются до замены файла. Пустой digest
отклоняется до скачивания/публикации. Ошибка чтения, несовпадающий payload и пустой
артефакт сохраняют прежний локальный файл. Ошибка одной арки отмечается, остальные
выбранные арки продолжают работу. Это идентичность передачи, не ELF/ABI/device/
reproducibility attestation. Реальные бинарники не собирались и не публиковались.

Четырнадцать исполняемых Python-тестов загружают оба настоящих скрипта с mock
SSH/SFTP/toolchain: CLI, ошибки toolchain/pin, non-MIPS, manifest/sync order, cleanup,
ошибки отдельных арок, публикация проверенных артефактов и --locked команды. PASS;
воспроизведения исходных ошибок сохранены отдельно. Mock не выдаётся за настоящую
успешную установку toolchain.

## F313: повторный LuCI load читал прежний enabled из кэша

uci.load кэширует пакет: повторный опрос не видел внешних изменений, а unload
уничтожил бы staged-правки формы. Новый read-only service_status RPC вызывает
status_enabled собственного init. Команда читает root UCI, используемый запуском
службы, а не браузерный/сессионный кэш формы. Root CLI deltas могут быть видимы до
commit: это init-visible намерение, а не строгое чтение только применённого файла.
Опрос не делает load/unload формы. Exit0/1 означают enabled/disabled; ошибка load,
отсутствующая служба или неверный RPC дают unknown с явным сообщением. Read ACL
разрешает только service_status; управление и запись секретов остаются write ACL.
Liveness процесса по-прежнему берётся из procd и не означает аутентифицированную
сетевую связность.

Девять LuCI caller fixtures и один status/ACL adapter fixture PASS. Последний
разбирает совместимый adapter в JavaScript с mock system/fs, не интерпретатором
ucode; реальные ucode/rpcd и rc.common dispatch NOT_RUN. Новый init-status case
вместе с прежними сценариями даёт11 тестов для каждого BusyBox ash/dash: оба PASS
в отдельном каталоге .11. Первичные источники:
[кэш LuCI](https://openwrt.github.io/luci/jsapi/uci.js.html),
[exit-коды ucode system](https://ucode-lang.org/module-core.html).

Текущий пакет F311–F313: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-router-build-failures-20261006.
Evidence: release/certification/evidence/q31-router-build-failures-20261006.json.
Прежний packet/seal не менялся. Install defaults/upgrade rollback, полный source
review, гонки секретов/службы и настоящие доступные cross-build остаются OPEN.
Следующая проверка установки должна разобрать прерванное создание и ошибки reload;
одноразовый defaults ещё не квалифицирован тестами live sync. Q31 IN_PROGRESS,
всего28/37(75.7%),осталось9.


## F314: прерванные firewall defaults выдавали успешную установку

Скрипт первой установки игнорировал ошибки отдельных UCI-команд и reload, затем
выходил с0. Если успело появиться лишь имя зоны qeli, следующий запуск видел его и
пропускал восстановление. Baseline fixtures воспроизводят exit0 после ошибок
commit/reload/input: зона не сохраняется при отказе commit, reload не повторяется,
ошибка input оставляет неполную зону. Это shell/UCI model, не настоящие libuci/fw4.

Теперь проверяются load, каждая мутация, commit и reload работающей службы. Перед
изменением создаётся0600 pending marker в0700 tmpfs-каталоге; зона и forwarding
имеют фиксированные package-owned имена. Повтор завершает только собственные
секции, заменяя device list без дубликатов. Существующая зона администратора
сохраняется; collision зарезервированного имени, чужое pending ownership, несколько
зон qeli и неправильный device останавливают мутации. Подготовка образа без службы
firewall допустима. Пока существует firewall-install-pending, init запрещает live
sync/start и указывает повторить /etc/uci-defaults/99-qeli-firewall.

Это восстановление установки, не автоматический rollback или interprocess
transaction. Root CLI staged deltas, конкуренция, process death и reboot моделью не
квалифицированы. Tmpfs marker не переживает boot; частичные изменения требуют
устранить причину ошибки и повторить defaults. Девять новых installation cases и12
init cases PASS отдельно в BusyBox ash и dash на .11. Пути и службы перенаправлены
в temporary fixtures; настоящие /etc/firewall/службы не менялись.

## F315: --sync оставлял удалённые исходники и старый Cargo config

Оба helper удаляли только src/bin, остальные файлы загружались поверх старых.
Удалённый локально модуль оставался на сервере, .cargo/config.toml не обновлялся.
Оба baseline helper воспроизводят эти stale inputs. Общий router_source вызывает
существующий native_lab sync: заменить src/.cargo, загрузить текущие config/assets/
исходники/Cargo.toml/Cargo.lock, сохранить target cache. Обязательные локальные
входы проверяются до первого изменения удалённого checkout.

0600 .router-sync-incomplete появляется до замены и удаляется только после всех
uploads и успешного SFTP close. Оба helper проверяют его до toolchain/build, включая
следующий запуск без --sync. Ошибки open/transfer/close/remote command сохраняют
marker; успешный --sync восстанавливает управляемые входы. Семь real-shell/filesystem
adapter tests PASS в Linux temporary roots,14 router helper fault tests и12
неизменённых shared native-lab tests PASS. Повтор удаляет stale inputs, сохраняет
кэш; отсутствие локальных файлов не вызывает remote commands. Старый hardcoded
cleanup воспроизводится ограниченным адаптером, без изменений настоящего /opt.

Замена не атомарна и не имеет cross-process lock. Без --sync старый checkout без
marker по-прежнему используется намеренно. Конкурирующие процессы, изменяемый
локальный snapshot, полная provenance, воспроизводимость, ELF/ABI и свежая настоящая
cross-build не подтверждены. Текущий Cargo config scope: один .cargo/config.toml.
Первый baseline attempt с отсутствующим Paramiko в Linux fixture сохранён как FAIL;
source-only импорт исправлен lab stub с запретом соединения, пакеты не устанавливались.

Пакет F314–F315: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-install-source-sync-20261006.
Evidence: release/certification/evidence/q31-install-source-sync-20261006.json.
Также PASS37 native recipe checks,10 Node caller/adapter cases, docs/bindings/diff.
Настоящие libuci/fw4/procd/ucode/rpcd/package install и cross-build NOT_RUN; router
runtime USER_EXCLUDED. Старые seals/runtime statuses/artifacts/dates/acceptance_basis
сохранены. Полные upgrade/rollback, lifecycle/secret races между процессами, широкий
review и настоящая build qualification OPEN. Q31 IN_PROGRESS,28/37(75.7%),9 осталось.

## F316–F318: ошибки удаления, миграции и загрузки UCI

clear_secrets сообщал успех после ошибки rm. RPC clear_secret игнорировал null,
возвращаемый fs.unlink при ошибке, и всегда выдавал result=true. CLI теперь
передаёт отказ, включая частичное удаление all; отсутствующий файл удаляется
идемпотентно. RPC проверяет два буквальных имени, делегирует init owner и выдаёт
result=false при ненулевом/неправильном результате команды. Compatible Node fixture
воспроизводит ложный успех с documented null; настоящий ucode не исполняется.
[Первичный контракт fs.unlink](https://ucode-lang.org/module-fs.html#unlink).
Удаление сохранённого файла не останавливает работающий VPN и не стирает уже
загруженные клиентом/отрендеренным obfs-конфигом копии; смена применяется restart.

Legacy migration удаляла staged UCI options до commit. После отказа commit повтор
видел отсутствие опций и возвращал0, хотя старые секреты оставались на постоянном
хранилище. Теперь0600 secret-migration-pending создаётся до staged delete и
сохраняется при отказе. Повтор делает commit даже без staged legacy options;
ошибка удаления marker сохраняет намерение повторить. Значение читается один раз,
непустой текущий runtime secret сохраняется, копирование идёт до удаления; пустые
legacy values также очищаются. Проверены copy/marker/delete/commit/remove failures.
Marker tmpfs: crash/reboot transaction и secure flash erase не подтверждены.
После миграции нужно сменить старые credentials, как было указано ранее.

Оба config_load qeli при старте, загрузка firewall и восстановление qeli context
теперь явно запрещают admission при отказе. Несколько зон qeli отвергаются до
мутации вместо выбора последней. Валидное отсутствие зоны допустимо по-прежнему.
Baseline model probes в обоих interpreter воспроизводят ложный успех clear/load/
ambiguous zone и сохранение persistent credentials после migration retry.

## F319: rc.common скрывал ошибку callback от сервисной команды

Сверка сохранённого [upstream rc.common](https://raw.githubusercontent.com/openwrt/openwrt/master/package/base-files/files/etc/rc.common)
показала: rc_procd вызывает callback, закрывает сервисное сообщение, а start/stop
затем вызывают optional hooks; иначе callback result теряется. Сохранённый dispatcher
с fixture-only lib/functions/procd adapters воспроизводит callback failure при CLI
exit0. Для отделения этого дефекта использован промежуточный F316–F318 source до
hooks, сохранённый отдельно от Git baseline.

Init owner теперь удерживает preparation/cleanup status и возвращает его через
стандартные service_started/service_stopped hooks. После ошибки stop cleanup
запрос procd_kill сохраняется, но последующая подготовка start внутри того же
restart/reload запрещается. Валидный disabled start успешен. Это callback results,
не проверка ubus publication/delete failure, daemon acceptance, native join или
VPN connectivity. flock/admission настоящей procd library только source-reviewed;
собственный механизм блокировок не добавлялся.

Пять saved-dispatcher cases,23 init и9 installation cases дают37 PASS отдельно в
BusyBox ash/dash на .11. Snapshot зафиксирован bytes/hash; тестам нужен явный путь
QELI_OPENWRT_RC_COMMON_FIXTURE, без него skip. Пути/adapters temporary-only: реальные
/etc/firewall/rc.d/daemons не менялись. Два hook cases и9 предшествующих init cases
новые.11 Node fixtures PASS, включая новый compatible RPC clear case. Также PASS
37 native recipes, docs/bindings/diff.

Пакет F316–F319: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-secrets-upgrade-20261006.
Evidence: release/certification/evidence/q31-secrets-upgrade-20261006.json.
Настоящие libuci/fw4/procd/ucode/rpcd/opkg и cross-build NOT_RUN; router USER_EXCLUDED.
Полные package upgrade/rollback, interprocess/daemon failure/lifecycle, широкий
review и build provenance OPEN. Предыдущие seals/runtime statuses/artifacts/dates/
acceptance_basis и Q29/Q30/D06 observations сохранены. Q31 IN_PROGRESS,28/37(75.7%),9 осталось.

## F320: установщик Keenetic искал старые артефакты и скрывал отказ зависимостей

Build helper публикует qeli-client-keenetic-aarch64/mipsel, а установщик искал
только qeli-client-aarch64/mipsel: canonical-only bundle не устанавливался.
Обязательный opkg install ip-full/iptables имел ||true, поэтому после отказа
подготовки установщик публиковал клиент и сообщал готовность. Оба поведения
воспроизведены на исходном Git source с изолированными command models. Инструкции
теперь указывают canonical artifacts и --sync; старые ручные имена поддерживаются
как fallback, canonical имеет приоритет.

До dependency changes проверяются непустые binary/init/new-config inputs. Ошибки
обязательных update/install передаются вызывающему, проверяется наличие ip/iptables;
отказ необязательного ip6tables даёт явное предупреждение. Копии binary/init/config
готовятся до публикации; обычные temporary files убираются при выходе, каждый файл
публикуется sibling rename. Existing INI content сохранён, mode ограничен0600,
credential directory0700. Copy/preparation failure сохраняет старые binary/init.
Publication failure может оставить частичный bundle: несколько rename не являются
транзакцией; нужно устранить ошибку и повторить установку. Автоматический restart,
concurrent-installer lock, fsync/power-loss и настоящие architecture/ELF/opkg проверки
не заявляются.

Одиннадцать installer cases: canonical/legacy names, обе архитектуры выбора,
existing config, required/optional dependency errors, missing command, incomplete
bundle/unsupported arch, copy failure и publication retry. Артефакты — маленькие
fixture files, VPN binary не запускается. Первый baseline attempt использовал
ambient PATH и завершился harness FAIL, запись сохранена. В final fixtures PATH
ограничен для обоих source; lab inventory подтверждает отсутствие настоящего opkg.

## F321: OpkgTun игнорировал ошибки ndm и смешивал чтения NetworkPlan

Каждая ndmc mutation продолжалась после отказа, затем выполнялся save и выводилось
interface up. Original-source model injection воспроизводит exit0/up/save после
неудачного ip global. Теперь проверяются все L3/configuration-save mutations;
отказ возвращается вызывающему, выводится retry required, ложный up не печатается.
Перед первой mutation создаётся pending checkpoint0600, который удаляется только
после успешного save. При повторе незавершённого apply address-only no-op обходится,
даже если ndm уже показывает matching connected addresses. Ошибки создания/удаления
checkpoint не дают сообщить completion; это не cross-process lock или fsync transaction.
Ранее успешные изменения ndm не откатываются автоматически: устранить причину,
повторить hook или manual registration, проверяя результат каждой команды.
Отсутствующий interface/plan по-прежнему даёт0 с диагностикой ожидания, без up.

Interface marker теперь требует opkgtun + непустой только десятичный suffix,
максимум15 символов. Старый glob принимал opkgtun0garbage, что доходило до ndm в
модели. Неправильный marker не вызывает ndm commands. Это исправление локальной
грамматики, не доказанный server-to-ndm exploit. План читается одним снимком, все
IPv4/IPv6/MTU извлекаются из него. Принудительная замена после первого чтения
воспроизвела old IPv4 из A при IPv6/MTU из B; corrected команды используют только A.
Это не сериализация concurrent stop, не generation ownership и не второй полный
клиентский parser NetworkPlan.

Девять hook cases: dual-stack apply, все девять mutation failures/connected retry,
ошибки создания/удаления checkpoint, invalid marker,
missing plan/interface, existing address no-op и forced replacement. Старые optimistic
address/status idempotence, MTU-only updates, process ownership/join, legacy NAT/sysctl
recovery и wan.d concurrency OPEN. Настоящие ndmc error/status output, event recursion,
ndm rollback и firmware compatibility не квалифицированы. Настоящие network/proc/sys/
службы роутера не менялись.

Пакет F320–F321: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-keenetic-install-hook-20261006.
Evidence: release/certification/evidence/q31-keenetic-install-hook-20261006.json.
20 cases на BusyBox ash/dash PASS в .11 temporary roots с подставными /opt/PATH/
opkg/ndmc. Также PASS37 native recipes/docs/bindings/diff; native implementation,
OpenWrt adapters и build helpers неизменны. Настоящие opkg/ndm/cross-build NOT_RUN;
routers USER_EXCLUDED. Предыдущие seals/runtime statuses/artifacts/dates/acceptance_basis
и Q29/Q30/D06 observations сохранены. Q31 IN_PROGRESS,28/37(75.7%),9 осталось.
