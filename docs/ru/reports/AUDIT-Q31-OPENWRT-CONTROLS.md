# Q31: управление LuCI, публикация INI и ошибки firewall

<!-- normative-sync: q31-openwrt-controls-v11 -->

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

## F322: снимок forwarding и ошибка восстановления теряли состояние для повтора

Оба init-шаблона Keenetic записывали непроверенный снимок прямо в конечный файл.
Ошибка чтения sysctl могла превратиться в пустое сохранённое значение, а функция
сохранения всё равно возвращала успех. Ошибка запроса WAN-маршрута скрывалась
pipeline. Восстановление игнорировало ошибки записи и удаляло checkpoint даже при
незавершённой очистке. Сравнение старого и исправленного кода воспроизводит эти
случаи на моделях. Проверка ошибки чтения вызывает функцию сохранения отдельно:
старый nat_up впоследствии падал на записи, уже успев создать некорректный снимок.

Теперь оба шаблона проверяют чтение, допустимые значения sysctl и результат запроса
WAN, затем публикуют checkpoint0600 переименованием соседнего временного файла.
Читаются только согласованные семейства: IPv4-only plan не требует IPv6 sysctl/WAN
query, IPv6-only plan не требует IPv4 sysctl/iptables. Checkpoint version2 хранит исходные
значения, имена TUN/LAN и семейства и RA, отмеченные до изменения. Применение отклоняет
состояние для других интерфейсов. Восстановление проверяет сохранённые поля, меняет
только отмеченные семейства и проверяет чтение/запись. После ошибки checkpoint
остаётся для повтора; удаляется только после успешного восстановления. Значения,
изменённые с установленных шаблоном1/2 на другие, сохраняются; изменения администратором
на те же значения отличить невозможно. Это не межпроцессная блокировка, fsync/
power-loss transaction или владение глобальными kernel sysctl.

## F323: legacy-очистка удаляла правила администратора и скрывала отказы

Старые правила не имели тега владельца: nat_up использовал совпадающее правило
администратора, а nat_down удалял его. Ошибки firewall игнорировались, после чего
сохранённое состояние могло удалиться. Смена GATEWAY/OPKGTUN полностью пропускала
восстановление. Original-source модели воспроизводят удаление совпадающих admin
rules, ложное завершение после ошибки delete/check, оставшийся checkpoint после
смены режима и переход restart к start после незавершённого восстановления.

Новые правила получают comment qeli-keenetic-legacy. Проверяемые add/delete helpers
отличают модельный check status1 (правило отсутствует) от более высоких кодов ошибки;
ошибки add/delete возвращаются вызывающему. Удаляются только правила с тегом для
отмеченных семейств и сохранённых интерфейсов. Checkpoint определяет необходимость
восстановления даже после смены GATEWAY/OPKGTUN/TUN/LAN; без него правила не удаляются.
После частичной очистки состояние сохраняется для повтора. Start отклоняет неудачное
восстановление до очистки плана и запуска; stop/restart передают отказ очистки.
Новому legacy-режиму требуется iptables comment capability; настоящие Entware/kernel
и особенности кодов ошибки NOT_RUN.

Versionless/unknown старый checkpoint блокирует автоматическую очистку и сохраняется
для ручной сверки. Перед заменой работающего legacy-шаблона остановить его старым
скриптом и проверить правила/sysctl. Если checkpoint остался, сохранить исходные
значения и установить владельца старых правил перед ручным восстановлением.
Не удалять состояние как автоматическую миграцию: новый код намеренно не угадывает
владельца старых нетегированных правил. На реальном роутере такая миграция не проводилась.

По22 изолированных state cases на каждый шаблон (44 новых): capture/publication,
WAN failure, family/interface admission, journal failures, точное совпадение admin
rules, повторное применение, check/add/delete/missing-command failures и retry,
ошибки чтения/записи восстановления, corrupt/old checkpoints, смена режима и gating
start/stop/restart через настоящий dispatcher шаблона. Вместе с20 предыдущими cases
установщика/хука64 теста на BusyBox ash/dash PASS. Общие блоки функций обоих шаблонов
сверены на идентичность. Proc/sys заменены файлами, firewall/ip — модели, все возможные
сигналы перехвачены. Настоящие процесс клиента, kernel forwarding/firewall и служба
роутера не запускались. Начальные fixture TUN expectation FAIL и reproduction-scope
assertion FAIL сохранены с объяснениями; финальное сравнение использует одинаковую
исправленную изоляцию для обоих исходников. Native recipes37/docs/bindings/diff PASS.

Пакет F322–F323: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-keenetic-forwarding-state-20261006.
Evidence: release/certification/evidence/q31-keenetic-forwarding-state-20261006.json.
Настоящие router/iptables/comment module/sysctl runtime и cross-build NOT_RUN;
router USER_EXCLUDED. PID identity, TERM/join ordering, мгновенный отказ запуска,
INI/core semantic parity, OpkgTun idempotence/concurrency и широкий build/source
review остаются OPEN. Предыдущие runtime statuses/artifacts/dates/acceptance_basis
и Q29/Q30/D06 observations сохранены. Q31 IN_PROGRESS,28/37(75.7%),9 осталось.

## F324: PID-файл мог направить сигнал чужому процессу или группе

Оба init-шаблона доверяли cat(PIDFILE) и kill -0/kill без проверки процесса. Старый
скрипт принимал и завершал специально созданный sleep victim по устаревшему PID.
Неверный PID0 доходил до попытки группового сигнала; в этом сравнении kill всегда
перехватывался, групповой сигнал не посылался.

Новый приватный PID record содержит десятичный PID и время старта из Linux proc в
тиках. Перед приёмом процесса/сигналом проверяются оба значения, точный формат,
положительный не-системный PID и executable identity. Суффикс deleted после замены
бинарника допускается для исходного процесса. Start ticks отличают повторно выданный
PID в пределах одной загрузки; пробелы/скобки в comm не ломают stat parser. Corrupt/legacy single-PID records,
чужой executable и неверные ticks блокируют start/stop и сохраняют состояние для
сверки. Status:0 live,3 stopped,4 unverified. Это best-effort shell/proc checks:
окно между проверкой и kill не закрыто атомарно через pidfd. Interprocess locking,
PID namespace/reboot identity и настоящий router proc/readlink не квалифицированы;
атомарная защита PID identity не заявляется.

PID публикуется файлом0600 через соседний временный файл и rename. При отказе
известный запущенный процесс завершается с ожиданием, если identity подтверждена.
Если termination/publication не закончены, pending record остаётся, start/stop
отказывают до ручной сверки. Установщик теперь отклоняет существующий PID/pending
record до зависимостей/замены файлов: сначала остановить установленный шаблон и
проверить завершение. Старый single-PID формат автоматически не мигрирует. Ошибка
proc-read после запуска может оставить неполный pending record и напечатанный PID;
не удалять его и не запускать новую генерацию вслепую.

## F325: после TERM сеть очищалась до выхода, ошибка запуска выглядела успехом

Старый stop выполнял compatibility cleanup до TERM, сразу удалял PID/plan и TUN без
ожидания. EXIT native helper с задержкой видел уже удалённые файлы; игнорируемый TERM
давал успешный stop и забытое состояние. Старый core-managed start сообщал успех при
мгновенном выходе executable или PID path, являющемся каталогом. Старый unwind после
NAT failure также очищал до выхода helper. Безопасное original/current сравнение
воспроизводит каждый случай.

Теперь оба шаблона требуют executable/config/readlink, проверяют каталоги, восстанавливают
старое compatibility state, готовят/публикуют record и проверяют post-exec liveness.
Это process admission, не подтверждение authenticated NetworkPlan readiness для
core-managed/OpkgTun старта. TERM адресуется проверенному процессу с ожиданием выхода
до15 итераций по одной секунде. Matching zombie считается завершившимся: это наблюдение
выхода, не waitpid reaping процесса, созданного другой оболочкой. Signal/identity/
timeout failure сохраняет PID/plan/marker и пропускает network cleanup; restart не
запускает новый клиент. После выхода выполняется compatibility recovery, затем
проверяемое удаление plan/markers/PID. Ошибки startup plan/NAT/marker проходят через
тот же joined stop. PID-removal/cleanup failure допускает повтор.

Шаблон больше не выполняет ip link del: временем жизни TUN управляют kernel/core/ndm,
нельзя вслепую удалять persistent или повторно используемый интерфейс. Это не новое
подтверждение настоящего Qeli thread drain, kill-switch lifetime или connectivity.
Точные wall-clock deadlines, SIGKILL/power loss, одновременно работающий wan.d handler
и все service/admin операции под межпроцессной блокировкой остаются OPEN.

Linux native test executable: process-fixture.c в raw packet, однократная сборка cc
с сохранённым hash; release-бинарник Qeli не пересобирался.43 native-process cases
(21 base,22 OpkgTun),44 state-file models и21 installer/hook cases: всего108 на
BusyBox ash/dash PASS;44 новых, включая installer upgrade gate. Helper публикует
подставной plan, задерживает выход или игнорирует TERM. Уникальный per-test executable
и отдельно созданные sleep children ограничивают цели сигналов/очистки. Network
callbacks подменены; настоящий kernel network/firewall/router service не менялся.
Polling сокращён до3*50ms (startup50ms, plan timeout2 polls): проверяет control flow,
не production15-second duration. Старые state fixtures теперь моделируют proc и
имеют executable/readlink, чтобы проверять stale-recovery admission с новым форматом.
Сохранён начальный original-source harness assertion FAIL: выбор первого nat_up
добавлял новый lifecycle code. Исправленный воспроизводитель добавляет только
последние fixture callbacks, оставляя старую реализацию. Invalid/group PID scenario
всегда моделирует сигналы, не посылает групповой сигнал.
Native recipes37/docs/bindings/diff PASS; настоящий router/core-OS integration NOT_RUN.

Пакет F324–F325: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-keenetic-process-lifecycle-20261006.
Evidence: release/certification/evidence/q31-keenetic-process-lifecycle-20261006.json.
INI/core semantic parity, OpkgTun idempotence/generation/concurrency, packaging и
широкий source/build ABI/provenance остаются OPEN. Предыдущие runtime statuses/artifacts/
dates/acceptance_basis и Q29/Q30/D06 observations сохранены. Router USER_EXCLUDED;
Q31 IN_PROGRESS,28/37(75.7%),9 осталось.

## F326: OpkgTun пропускал изменение MTU и незавершённую настройку

Connected и совпадение подстроки адреса не подтверждали полное применение плана.
Сравнение старого/нового исходника воспроизводит пропуск изменения MTU, принятие
IPv4 .20 вместо .2 и строк с подстановками регулярного выражения, IPv6 ::20 вместо
::2, а также тихий выход без текущего плана. Совпавшие адреса сами по себе не
подтверждают успешные global/MSS/security/save.

Теперь для пропуска команд нужна приватная запись qeli.opkgtun.applied с точным
именем интерфейса и полным снимком плана. Файл0600 публикуется через соседний
временный файл и rename после всех успешных команд и save. Нет записи или план
изменился — настройка повторяется. Изменение только MTU применяется, следующее
событие при совпадении становится no-op. Connected и адреса сравниваются буквально,
проверяется код show. Пустой план не допускает no-op. Ошибка публикации записи или
удаления pending сохраняет повторную попытку и не сообщает успех. Stop удаляет
запись после завершения клиента.

Запись подтверждает выполненные команды, а не поколение клиента, блокировку или
чтение всех параметров ndm. Внешние изменения MTU/MSS/security, устаревший обработчик
после stop, удаление семейства адресов, эквивалентная запись IPv6 и формат/события
реальной прошивки остаются непроверенными. Команды удаления адресов для прошивки
не придумываются. Согласованность одного снимка сохранена; он не обязательно
последний при параллельном обновлении плана.

## F327: завершение между чтением proc stat и executable принималось за смену владельца

После stat живой процесс может стать zombie до readlink(exe): proc ещё существует,
а executable уже недоступен. Старый код возвращал unverified вместо exited и
сохранял состояние после успешного завершения. Детерминированный тест удерживает
zombie собственного прямого дочернего процесса до waitpid и воспроизводит ошибку
обоих init-шаблонов. Отдельно проверен отказ сигналить живой процесс с недоступным exe.

При отказе чтения exe оба шаблона повторно читают stat и принимают Z/X только при
совпадении start ticks. Живой, недоступный, заменённый или непроверенный процесс
по-прежнему отвергается; исчезнувший proc считается завершённым. Общая гонка между
проверкой и сигналом этим не закрывается, pidfd-защита не заявляется.

Итог:120 проверок на каждом BusyBox ash/dash PASS:43 прежних native-process плюс
четыре новых race/live-exe,44 модели состояния,12 installer,17 hook. Восемь hook
тестов новые. Семь методов сравнения hook воспроизводят восемь старых assertion
failures с subtests; новая версия PASS. Детерминированная старая гонка FAIL дважды,
исправление и unreadable-live PASS в обеих оболочках. Первый dash suite FAIL сохранён,
точная причина в том прогоне не инструментировалась. Первый orphan diagnostic не
воспроизвёл гонку из-за reaping PID1; квалификация прямого child записана отдельно.
Native recipes37/docs/bindings/diff PASS. Команды/файлы и network callbacks — модели;
реальны только собственные Linux helper processes. Helper unchanged от F324/F325,
Qeli/router binary не пересобирались. Router USER_EXCLUDED, cross-build NOT_RUN.

Пакет F326–F327: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-keenetic-opkgtun-receipt-20261006.
Evidence: release/certification/evidence/q31-keenetic-opkgtun-receipt-20261006.json.
INI/core parity, поколения/параллелизм OpkgTun и остальная package/build/source
проверка OPEN. Q29 FAIL/ENONET, Q30 skips/drain OPEN и D06 сохранены.
Q31 IN_PROGRESS; общий итог28/37(75.7%),осталось9.

## F328: скрипт проверки сборки останавливал сервисы и использовал общий исходный каталог

keenetic_verify.py безусловно останавливал qeli-server и выполнял pkill -9 qeli,
хотя компиляция и проверка зависимостей не требуют менять работающие сервисы.
Отдельная additive-синхронизация сохраняла удалённые модули и старую Cargo config.
Модели старого pipeline воспроизводят сервисные команды; настоящий file-adapter
в собственном временном каталоге подтверждает stale inputs. Старые сервисные и
компиляторные команды на действующей лабе не выполнялись.

Новая проверка создаёт отдельный0700 mktemp checkout в /var/tmp на каждый запуск,
проверяет путь, задаёт CARGO_TARGET_DIR внутри него и использует общий
router_source/native_lab. Проверки incomplete-sync marker и завершения SFTP
переиспользованы; отдельный sync или INI parser не добавляется. Сервисы не
останавливаются, не убиваются и не перезапускаются. Сборки используют --locked и
одну compiler job, серверный release требует jemalloc; клиент сохраняет client-only
features. Каталог сохраняется для разбора; после использования его нужно удалить.
Общий source/target каталог для параллельных запусков не используется. Pinning
toolchain и полный provenance роутерного артефакта остаются OPEN.

## F329: ошибки проверки могли давать exit0, а текст ошибки подтверждал отсутствие ring

Старый main печатал FAIL, но возвращал None: после отказа сборки скрипт выходил0.
Ненулевой reverse dependency query с текстом did-not-match принимался за отсутствие
ring; отказ поиска артефакта игнорировался. При sync exception SSH не закрывался.
Управляемые старые прогоны подтверждают ложный PASS и exit0 после failed summary.

Каждый этап теперь проверяет exit status. Требуется успешный прямой граф normal/
build dependencies: пакет ring, пустой/чужой root и текст ошибки отвергаются.
Dev-only зависимости исключены. Обязательны nonempty/executable, readelf ELF magic
и проверенный SHA256 артефакта. SSH закрывается в finally после успеха и ошибки,
включая sync failure. Нет credentials — exit2; verification/connect/close failure
— exit1; полный успех — exit0.

19 новых gate-тестов PASS на Windows/Linux: отказ каждой команды, sync/readiness/
hash/metadata/close и отсутствие операций над сервисами.7 shared-sync тестов
используют настоящие shell/files с временным SFTP adapter в Linux и PASS. Настоящий
установленный Cargo выполняет offline-графы локальных fixture crates: client
normal/build исключает dev-only ring, положительный server-граф содержит ring и
отвергается. Компилятор, загрузка зависимостей, настоящий Qeli host/cross build,
артефакт клиента и прошивка этим не квалифицируются.37 recipes/docs/bindings/diff
PASS. Исторические результаты11 июня остаются историческими и не подтверждают
текущий исходник.

Пакет F328–F329: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-keenetic-verification-gate-20261006.
Evidence: release/certification/evidence/q31-keenetic-verification-gate-20261006.json.
INI/core gateway parity, поколения/параллелизм OpkgTun, packaging и остальная
source/build ABI/provenance проверка OPEN. Q29 FAIL/ENONET,Q30 skips/drain OPEN,D06
сохранены. Router USER_EXCLUDED; Q31 IN_PROGRESS,28/37(75.7%),осталось9.

Первый native-recipe FAIL сохранён: прежняя проверка литерала server_build= в
исходнике не совпала с динамическим выводом этапа. Теперь recipe требует именованную
locked server-команду, а execution test проверяет фактический server_build=OK после
успеха. Итоговые recipes PASS; product-команда ради старого assertion не ослаблялась.

## F330: отдельный INI-парсер init расходился с ядром

Оба шаблона содержали awk parser и собственный список true/yes/1. Корректные
кавычки, регистр/BOM и on, принимаемые каноническим клиентским parser, считались
false в wrapper. Сравнение старого/нового кода воспроизводит лишний legacy NAT/
forwarding для quoted gateway_nat, uppercase key и forward=on.

Оба shell-парсера удалены. qeli-client --print-gateway-owner использует существующие
ограниченный config_source loader и строгий общий INI parser; печатает только core
или legacy до logging initialization и запуска клиента. Секреты конфига не
сериализуются, hooks/device identity/TOFU/TUN/network setup не выполняются. API
включён только для Linux AND client-bin. За пределами добавленного блока client/
mod.rs совпадает с baseline. Cargo/native FFI recipes/default features и остальные
native implementations неизменны; новый FFI ABI не вводится.

## F331: exit-node и ошибки определения владельца допускали legacy LAN NAT

Раньше core_manages_gateway проверял только gateway_nat/forward. Допустимый
exit_node=true дополнительно включал противоположный legacy LAN masquerade. Теперь
это core ownership наравне с gateway_nat/forward. Все flags false/отсутствуют —
legacy fallback сохранён. Invalid/duplicate/conflicting config, ненулевой exit
query, unknown/empty/multiline reply запрещают start до запуска и восстановления
сети. Неизвестный владелец не допускает nat_up. Один проверенный pre-launch ответ
сохранён для решений wrapper; GATEWAY=no и активный OpkgTun не требуют legacy
query. Stop recovery не зависит от нынешних INI flags; saved-state rules неизменны.

Standalone binary и шаблон нужно обновлять вместе. Без новой команды binary
отклоняет gateway startup, а не возвращается к старому shell parser. Query —
снимок config, не authentication readiness и не владение работающим поколением.
Процесс затем повторно читает path: параллельная замена config между inspection/
start и параллельные service/wan.d операции остаются OPEN. Atomic config-generation
lock не заявляется.

Свежие Rust1.97.0 offline/locked/jobs1 host client-bin debug build,8 binary unit,
pinned formatter и strict Clippy PASS.155 проверок на каждом BusyBox ash/dash
PASS:47 owned native-helper process,44 state model,12 installer,17 hook,19 verifier,
16 новых owner tests.22 subcases настоящего inspector/INI admission на оболочку
для обоих шаблонов.16 original/current records на оболочку воспроизводят три
syntax mismatches и exit-node legacy ownership. Только new-source query использует
настоящий host inspector; old-source решение — исходный awk. Firewall/proc/sys/
network/service callbacks остаются моделями. C helper моделирует metadata reply
без parser; настоящий core parsing проверен Rust-тестами и host inspector. State
fixture исправлен для допуска metadata query: stale-recovery assertions достигают
recovery, а не раннего unsupported-command failure. Оба final suite перепроверены.
37 recipes/docs/bindings/diff PASS. Windows rustfmt не найден, до компиляции
использован pinned formatter лабы. Qeli release/cross-build, настоящий router/
firmware networking и native FFI artifacts не пересобирались; исторические
статусы/даты сохранены.

Пакет F330–F331: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-keenetic-core-gateway-20261006.
Evidence: release/certification/evidence/q31-keenetic-core-gateway-20261006.json.
Core gateway INI decision parity теперь scoped PASS. Config/generation concurrency,
OpkgTun ownership, packaging и остальная source/build ABI/provenance проверка OPEN.
Q29 FAIL/ENONET,Q30 skips/drain OPEN,D06 сохранены; router USER_EXCLUDED.
Q31 IN_PROGRESS;28/37(75.7%),осталось9.

## F332: init, wan.d и установка выполнялись параллельно

Два hook могли смешать команды ndm и публикацию pending/receipt. Stop удалял marker
и план, пока уже запущенный hook продолжал настройку по старому снимку и заново
создавал служебные файлы. Для start/stop/restart и установки общей блокировки не было.

Теперь все три точки входа используют одну библиотеку lifecycle.sh. Атомарный mkdir
/var/run/qeli.lifecycle.lock допускает одну операцию; конкурент возвращает ошибку
до сетевой настройки, работы службы или публикации и требует повтора. Init держит
lock весь restart и внутреннюю очистку. Hook повторно проверяет marker под lock.
Installer использует библиотеку из комплекта, готовит установленную копию0600 и
публикует её перед бинарником/init. Старые скрипты lock не соблюдают: обновлять
библиотеку, соответствующие init и hook вместе после остановки/сверки старого клиента.

Обычный выход и HUP/INT/TERM освобождают lock. После SIGKILL каталог остаётся для
ручной сверки: автоматического удаления по PID/возрасту и убийства процессов нет.
Lock находится во временном /var/run роутера, а не в постоянном /opt. Убедившись,
что init/hook/installer-владельца больше нет, удалять только пустой каталог через
rmdir, сохраняя PID/plan/forwarding/pending, затем повторять штатную операцию.
Занятые hook-события не стоят в очереди: нужен следующий event или ручной повтор.
Зависший ndmc может удерживать lock; новый firmware timeout здесь не квалифицирован.

## F333: смена плана ядром допускала ложный complete receipt

Hook сравнивает captured marker/целый план перед каждой проверяемой командой L3/save
и после save перед публикацией receipt. Обнаруженная замена прерывает обработку и
сохраняет pending для повтора. Snapshot-тест теперь проверяет отказ от старого плана
и применение нового вместо подтверждения устаревшего результата. Ядро не участвует
в shell-lock: замена после последней проверки, ABA с одинаковыми байтами, привязка
к аутентифицированному поколению и удаление семейства остаются OPEN. Выполненные
команды не откатываются; атомарность всей настройки не заявляется.

## F334: mv в каталог выдавал ложный успех установки

mv source destination-directory успешно помещает временный basename внутрь
каталога. Installer отвергает directory targets бинарника/init/config/helper до
работы с зависимостями. Ошибка подготовки/публикации библиотеки сохраняет старые
binary/init и убирает временный sibling; rollback всего комплекта остаётся OPEN.

Восемь новых lifecycle-методов (оба init внутри одного метода) и два installer-метода:
165 тестов на каждом BusyBox ash/dash —47 owned native-process,44 state models,
14 installer,17 hook,19 verifier,16 owner и8 lifecycle. Настоящие owned shell-процессы
с барьерами воспроизводят три baseline-отказа на каждом shell: перемешивание hook,
stop во время hook и смену плана при save. Исходный installer также проваливает
новый directory admission assertion. Исправленные suites PASS. Network/ndm/opkg/
sysctl — модели команд/файлов. Байты C helper и host debug inspector совпадают с
F330/F331; Rust/core/native implementations, ABI/artifacts/recipes неизменны:
новая Rust/FFI/release/cross-сборка не заявляется.37 recipes/docs/bindings/diff PASS.
Настоящий router runtime USER_EXCLUDED.

Packet F332–F334: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-keenetic-lifecycle-lock-20261006.
Evidence: release/certification/evidence/q31-keenetic-lifecycle-lock-20261006.json.
Общее исключение cooperating shell-операций и отказ при обнаруженной смене плана —
scoped PASS; core/config generations, firmware ordering, packaging/cross ABI/source
provenance и широкий review OPEN. Q29 FAIL/ENONET,Q30 skips/drain OPEN,D06 сохранены.
Q31 IN_PROGRESS;28/37(75.7%),осталось9.

Первый directory baseline дал также две ошибки фикстуры: успешная старая установка повлияла на следующие targets. Raw logs сохранены и не квалифицируют эти targets. Отдельные свежие фикстуры воспроизводят ложный старый успех для binary/init/config и отказ нового кода: шесть old/current records на shell PASS. Код продукта и входы финального165-suite для этого сравнения не менялись.
