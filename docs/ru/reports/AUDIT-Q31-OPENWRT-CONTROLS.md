# Q31: управление LuCI, публикация INI и ошибки firewall

<!-- normative-sync: q31-openwrt-controls-v17 -->

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

## F335: общий checkout и backup manifest загрязняли сборки роутеров

Без --sync оба helper использовали старый /opt/qeli-src. Успешная сборка могла
содержать прежние исходники; параллельные запуски изменяли/восстанавливали один
Cargo.toml и делили target. Теперь каждый запуск создаёт проверенный приватный
mktemp-каталог0700, всегда загружает текущие управляемые входы, проверяет завершение
sync и ограничивает только свою копию до rlib. Общие backup/restore удалены.
CARGO_TARGET_DIR принадлежит запуску; CARGO_INCREMENTAL=0 и --jobs1 ограничивают
конкурентность компилятора внутри него. --sync совместим, но необязателен.
Напечатанный каталог сохраняется для диагностики и требует проверенной очистки
после завершения; старые checkout не меняются. Toolchain и download cache Cargo
могут быть общими; конкурентная установка toolchain и локальные изменения файлов
во время upload пока не квалифицированы.

## F336: совпадение SHA допускало несовместимый бинарник и даже не-ELF

Проверенный hash доставки не подтверждал архитектуру или статическую компоновку.
Оба helper используют router_artifact.py: один снимок SFTP читается, транспорт
закрывается, SHA сверяется, проверяется тот же снимок, затем существующий owner
публикует его атомарно. Отказ сохраняет прежний бинарник; совпавший локальный hash
не обходит проверку. Gate проверяет границы headers/segments, little endian,
разрядность/машину target и исполняемую точку входа, запрещает PT_INTERP/DT_NEEDED,
проверяет EABI5 hard-float ARMv7. ET_EXEC/static PIE разрешены; расширенный формат
program headers отвергается. Это metadata admission, а не доказательство musl,
CPU ISA, полного float ABI MIPS, работы kernel/firmware или полной валидности ELF.

## F337: SDK install не обеспечивал graph из сохранённого lockfile

Пакет OpenWrt требует Cargo.lock и проверяет client-only graph через cargo metadata
--locked до cargo install --locked --jobs1. Реальный fixture показал: install
--locked --path сам по себе допускал отсутствующий/устаревший lockfile для локальной
path dependency. Guard отвергает оба случая до публикации. Загрузок зависимостей
не было. Source SHA/mirror hash остаются этапами release-cut. Пустые SDK include
stubs только позволяют GNU make развернуть настоящий Build/Compile; полноценная
SDK/package/cross сборка этим не подтверждается.

На .11 PASS45 router tests:15 helper failure/admission,16 ELF/snapshot,7 private
checkout,7 sync. Три POSIX метода выполняют реальные операции над собственными
каталогами/manifest; compiler/SSH helper проверяются моделями с test-only Paramiko
stub, запрещающим SSH, поскольку Paramiko в лабе отсутствует.20 old/current записей
воспроизводят допуск старого source и неверного ELF с совпадающим SHA в обоих
helper. Пять реальных offline GNU make/Cargo tiny-crate случаев: старый код
принимает missing/stale lock, новый отвергает их и принимает valid lock. Настоящий
маленький x86_64 glibc-static ELF проходит metadata gate; прежний неизменённый GNU
debug Qeli ELF отвергается по PT_INTERP. Это не свежая router Qeli/musl cross сборка
и не выполнение на firmware. Начальные import/fixture-assumption FAIL сохранены
и не квалифицируют результат.37 recipe tests, docs/bindings/diff PASS.

Пакет F335–F337: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-router-build-isolation-20261006.
Evidence: release/certification/evidence/q31-router-build-isolation-20261006.json.
Rust/core/native compile inputs, библиотеки, существующие router binaries и их
историческая квалификация неизменны. Новые Qeli/FFI/release/cross build, фиксация
toolchain/reproducibility и полный ABI не заявляются. Core/config generation,
ABA, last-check replacement, порядок firmware и whole-bundle rollback OPEN.
Q29 FAIL/ENONET,Q30 exclusions/drainOPEN,D06 сохранены. Q31 IN_PROGRESS;
28/37(75.7%),9 осталось; целый checklist-пункт Q31 не закрыт.

Основание metadata: [ELF program headers](https://refspecs.linuxfoundation.org/elf/gabi4%2B/ch5.pheader.html),
[Arm ELF32 ABI](https://github.com/ARM-software/abi-aa/blob/main/aaelf32/aaelf32.rst),
[Cargo install](https://doc.rust-lang.org/cargo/commands/cargo-install.html).

## F338: default Rust, плавающий nightly и непроверенный Zig меняли сборку

Оба helper отдельно настраивали toolchain. Обычные сборки использовали default
Cargo/Rust, MIPS — +nightly; любая версия Zig только печаталась. Свежий read-only
inventory подтверждает default Rust1.96 в обеих лабах, тогда как pinned native
recipes используют1.97.0. router_toolchain.py теперь владеет aliases targets,
настройкой и build commands обоих helper: Rust1.97.0, nightly-2026-06-10 для MIPS,
Zig0.13.0, cargo-zigbuild0.23.0. Дата nightly взята из существующего manifest .10
(compiler commit датирован June9); latest-nightly не выбирается.

Неверный Zig отвергается до установки. Именованные Rust pins/версии, target std и
nightly rust-src проверяются после успешных installer; отсутствие результата
останавливает setup. Inventory cargo-zigbuild и версия его top-level executable
должны совпадать. Install использует explicit Rust и один job; default не меняется.
Удалены мёртвые checked/feature definitions helper и дублирующие OpenWrt build_std
data/argument. У architecture/toolchain/flags теперь один owner.

## F339: внешние encoded/compiler flags перекрывали recipe

CARGO_ENCODED_RUSTFLAGS имеет приоритет над RUSTFLAGS, в том числе прежним MIPS
soft-float assignment. Общая команда Qeli удаляет encoded flags, RUSTC,
CARGO_BUILD_RUSTC и CARGO_BUILD_RUSTFLAGS, задаёт свои RUSTFLAGS (пустые для обычных
targets, явный MIPS linker soft-float), отключает Rust wrappers и использует pin,
приватный target/noincremental/jobs1. Это ограниченный фикс ambient overrides,
а не полная очистка всех Cargo profile/config/PATH/cache inputs.

PASS52 Linux router tests:12 helper,10 shared policy,16 ELF,7 source,7 checkout.
Четыре дублирующих setup test methods заменены одним delegation method и10 общими
semantic failure methods; покрытие перенесено.12 old/current model записей
воспроизводят допуск неверного Zig и unpinned/unisolated команды в обоих helper.
Реальный offline tiny host Cargo/Rust fixture выполняет старый/новый prefix:
старый применяет encoded cfg с default Rust1.96, новый не применяет cfg и выбирает
Rust1.97. Это не cargo-zigbuild/musl/cross/MIPS/nightly/Qeli сборка.37 recipes,
docs/bindings/diff PASS. На .10 только read-only inventory; выполнение на .11.
Global tools/defaults/service/network/установленные бинарники не менялись.

Начальный draft использовал cargo +pin zigbuild --version, который реальный tool
отвергает; итоговая проверка — cargo-zigbuild --version. Временное удаление BIN в
незакоммиченном коде обнаружили helper tests, оно исправлено. Test-only import context также выгружал policy module и нарушал identity
comparison mock; pre-import исправил harness. Начальные FAIL сохранены и не
квалифицируют успех; проверки точного итогового source повторены.
Pinning не доказывает hermeticity, полный ABI/ISA, независимую A/B reproducibility
или router runtime. Shared tool installation/cache, global config/PATH/upload races
остаются. Реальный router USER_EXCLUDED; SDK Rust feed/source/mirror release-cut
проверяются отдельно. Core/native/Rust implementation inputs/artifacts неизменны.

Пакет F338–F339: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-router-toolchain-policy-20261006.
Evidence: release/certification/evidence/q31-router-toolchain-policy-20261006.json.
Generation/ABA/last-check/firmware/whole-bundle rollback OPEN. Q29 FAIL/ENONET,
Q30 exclusions/drainOPEN,D06 сохранены. Q31 IN_PROGRESS;28/37(75.7%),9 осталось;
целый checklist-пункт не закрыт.
Основание политики: [rustup pins](https://rust-lang.github.io/rustup/concepts/toolchains.html),
[Cargo environment](https://doc.rust-lang.org/cargo/reference/environment-variables.html).

## F340: ошибка публикации оставляла смешанное поколение installer

Прежний installer отдельно заменял helper/binary/init. Ошибка последнего init
rename либо TERM после публикации binary оставляли новый executable/helper со
старым init. Теперь до публикации создаются backup старых файлов в тех же
каталогах с сохранением bytes/modes и recovery record0600. Rollback intent задаётся
до rename; неуспешный same-directory rename с сохранившимся source считается
неопубликованным. Обычная ошибка/обработанный сигнал восстанавливают изменённый
код в обратном порядке; отсутствовавшие прежде targets удаляются. Failed restore
сохраняет оставшиеся backup/install-pending вместо потери recovery evidence.

Общий qeli_install_ready проверяет retry, start обоих обновлённых init и активный
wan.d hook. Stop разрешён. Lock освобождается после обработанного rollback.
Pending record, включая dangling symlink, блокирует admission. Старые скрипты
требуют ручной остановки/проверки и не обязательно соблюдают guard: старый init,
восстановленный при частично неуспешном rollback, не считается защищённым.
Crash atomicity всего bundle не заявлена: SIGKILL/power loss требуют owner review
и manual recovery; fsync/automatic stale deletion нет. Существующий INI content
сохраняется; ужесточённый mode600 и новая опубликованная болванка могут остаться
после поздней ошибки. opkg/package changes и root/admin replacement вне code
rollback. Именованный backup мог уже быть использован успешным частичным restore;
проверяй комплект, не удаляй targets/marker вслепую.

## F341: linked/special targets обходили предположения об обычных файлах

Старая directory-проверка допускала symlink/FIFO. chmod600 client.conf проходил
по symlink и менял внешний файл; chmod700 linked config directory менял внешний
каталог. Теперь installed code/config targets — только regular или absent, без
symlink; /opt/etc/qeli не должен быть linked. Отказ до package updates. Root/admin
path races этим не закрываются.

PASS176 tests на каждом BusyBox ash/dash:47 owned native process,44 state,14
installer,17 hook,19 verifier,16 gateway owner,8 lifecycle и11 новых install
rollback/admission methods. Проверены каждый code rename, old/absent/new code,
restore/copy/marker failures, TERM после реального owned rename, regular/dangling
linked targets,FIFO,linked config directory и pending guards обоих init/hook.
Пять old/current сценариев дают10 записей на shell: init rename,TERM,config
symlink,directory symlink,failed restore. Воспроизведены старые mixed code/outside
chmod/отсутствующий recovery marker; новые restore/refusal/retained recovery PASS.

Начальные11-method suites FAIL только из-за fixture assertion: read-only opkg
print-architecture при отказе retry был посчитан как изменение зависимостей.
Теперь сравниваются mutating package calls; все176 повторены на каждом interpreter.
Исходные FAIL logs/inputs сохранены. State function fixtures явно source shared
library, все library paths отображены в owned root; настоящий /opt не используется.
Network/ndm/opkg/proc-sys — модели; выполняются настоящие owned shell/rename/signal/
native helper и существующий host inspector. Reused helper/inspector hashes равны
F330–F331; Rust/core/native inputs/artifacts/recipes неизменны.37 recipes,
docs/bindings/diff PASS; новая Qeli/FFI/release/cross сборка и router runtime не заявлены.

Пакет F340–F341: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-keenetic-install-rollback-20261006.
Evidence: release/certification/evidence/q31-keenetic-install-rollback-20261006.json.
Ordinary executable-bundle failure recovery — scoped PASS. Power-loss transaction,
старые scripts/admin,core/config generation/ABA/last-check,firmware/full ABI и
cross-build qualification OPEN. Q29 FAIL/ENONET,Q30 exclusions/drainOPEN,D06 сохранены;
real router USER_EXCLUDED. Q31 IN_PROGRESS;28/37(75.7%),9 осталось;
целый checklist-пункт не закрыт.

## F342: UCI → INI менял буквальные строки перед общим парсером

Renderer записывал строковые значения без кавычек. Общий INI parser обрезает
крайние пробелы у bare values и снимает одну пару внешних кавычек с unescape
backslash-quote. Поэтому username, окружённый пробелами, или volatile obfs_key,
начинающийся и заканчивающийся кавычками, мог отличаться от заданного оператором.
Сохранение secret-файла само по себе не защищало последующую сериализацию ключа.
Это дефект преобразования данных; VPN handshake в этом пакете не запускался.

Единый ini_write теперь заключает строку в двойные кавычки и экранирует только
двойные кавычки, как serializer общего ядра. Bare backslash остаётся буквальным.
ini_kv сохраняет прежний пропуск отсутствующих необязательных значений; required
server/proto/password_file и logging используют тот же writer. ASCII control
characters по-прежнему удаляются до записи, bool/MTU остаются прежними.
UCI-текст не исполняется; набор параметров/формат конфигурации остаётся INI.

Четыре новые проверки дают40 round-trip операций: по13 вариантов для writer,
user и obfs_key плюс required/logging/control case. Сам файл config/format.rs
без изменения компилируется в отдельный GNU host inspector с существующим log
rlib; fixture подаёт сгенерированный INI через stdin и сверяет UTF-8 bytes из hex.
Это настоящий общий parser, не новая Python реализация. Старый Git init на том
же новом test source воспроизводит13 несовпадений в каждом shell. Текущий полный
набор41 =23 init +9 defaults +5 saved rc.common dispatcher +4 round-trip PASS
отдельно в BusyBox ash и dash. Файлы, функции init и Rust parser выполняются
в собственных temporary paths; UCI/procd/firewall остаются моделями. Saved
dispatcher snapshot/hash прежний, настоящие OpenWrt daemons не запускались.
Первый standalone compile отказал без log dependency; отказ сохранён, затем
подключён существующий GNU log rlib без изменения parser source.

11 LuCI Node fixtures,37 native recipes, docs/bindings/diff PASS. Core/native/
router build recipes и существующие артефакты не менялись; свежая сборка Qeli,
FFI/cross/firmware/ABI и сетевой obfs handshake не заявлены. Форматирование
значения проверено отдельно от его допустимости для ClientConfig.

Пакет: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-openwrt-ini-roundtrip-20261006.
Evidence: release/certification/evidence/q31-openwrt-ini-roundtrip-20261006.json.
Q31 IN_PROGRESS,28/37(75.7%),9 осталось; целый checklist-пункт не закрыт.
Generation/ABA/last-check/firmware ordering и cross qualification остаются OPEN;
Q29 FAIL/ENONET,Q30 exclusions/drainOPEN,D06 сохранены, router USER_EXCLUDED.

## F343: wrapper не сверял dev и владельца L3 до запуска

Оба init templates использовали своё TUN для legacy firewall и marker OpkgTun,
но gateway inspection не проверял соответствие этому имени dev в INI. При
GATEWAY=no или активном OpkgTun inspection вообще пропускался. Поэтому неверный
dev/dev_attach мог запускать иной интерфейс или пытаться создать устройство,
которым должен владеть ndm; gateway flags могли включать дополнительного владельца.

Metadata CLI теперь принимает парные --expect-router-device и
--expect-router-attach только вместе с --print-gateway-owner. Общий bounded loader
и strict core parser одним чтением проверяют совпадение dev, device_type=tun и
dev_attach. Attached router требует gateway_nat/forward/exit_node выключенными,
поскольку ndm владеет L3/gateway. Старый metadata CLI без expectations сохраняет
свою прежнюю функцию; обновлённые templates требуют новый бинарник. Неизвестные
опции у старого binary дают отказ до launch, а не тихий unsafe fallback.

Оба templates делают этот query один раз до cleanup старого state, удаления
NetworkPlan/PID и создания процесса; даже GATEWAY=no не отменяет interface admission.
Shell INI parser не добавлен. Проверка не фиксирует snapshot для дальнейшего
запуска: изменение INI между inspection и startup, generation/ABA остаются OPEN.
Не меняй client.conf во время start/restart. При исправлении имени/режима согласуй
INI и template и повтори start; inspection сам не создаёт TUN и не запускает hooks.

Свежий GNU client-bin debug build Rust1.97.0,12 целевых unit tests (4 новых),
strict Clippy и fmt PASS. 184 shell tests на каждом BusyBox ash/dash PASS:
47 process +44 state +14 installer +17 hook +19 verifier +24 gateway owner
+8 lifecycle +11 rollback. Восемь новых shell методов добавляют34 actual
inspector cells; вместе с прежними22 это56, не сетевые подключения.
Тот же новый test source, старые Git template bodies и старый host inspector
дают20 false admission mismatches в восьми методах на каждом interpreter.

Первый полный прогон с прежним вспомогательным C-процессом завис: argc==4 не
распознал дополнительные CLI flags, metadata query перешёл в модельный lifetime.
Timeout не засчитан как полный результат; собственные helper/suite остановлены
после проверки exe hash/cwd, два своих temp roots очищены, финальный lookup пуст.
Отдельный C helper теперь распознаёт только прежние4 и новые8 аргументов;
его metadata reply остаётся моделью, процессные lifecycle проверки настоящие.
Исходник/hash старого и нового helper сохранены; прежний executable не менялся.
Без rustfmt в Windows PATH применён установленный pinned formatter на .11.

317 compile inputs и17 fixture Git files сверены с фактически переданными
байтами; только приватный Cargo.toml ограничен до rlib, исходный manifest сохранён.
37 native recipes, docs/bindings/diff PASS. Изменения Rust ограничены Linux
client-bin metadata admission/CLI; обычный data plane, FFI/JNI exports/config schema
не менялись. Прежние native/release/router artifacts сохранены; свежая сборка
FFI/release/cross/firmware или router ABI/runtime не заявлена. .10 не затронут,
.11 выполнял только собственные files/compiler/process fixtures.

Пакет: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-keenetic-interface-admission-20261006.
Evidence: release/certification/evidence/q31-keenetic-interface-admission-20261006.json.
Q31 IN_PROGRESS,28/37(75.7%),9 осталось; целый checklist-пункт не закрыт.
Q29 FAIL/ENONET,Q30 exclusions/drainOPEN,D06 сохранены, router USER_EXCLUDED.

## F344–F346: реальная router cross-matrix и compile-регрессии

Прежние host/tiny-crate проверки не подтверждали сборку текущего Qeli на musl.
Все четыре настоящие release client-only сборки старого Git-снимка упали:
statfs.f_type у musl беззнаковый, а PROC_SUPER_MAGIC знаковый. На MIPS дополнительно
не существует std::sync::atomic::AtomicU64 для roaming RPF lease counter.
F344 сравнивает оба значения в lossless i128, сохраняя проверку regular procfs;
F345 использует уже имеющийся portable-atomic. Ширина64бит, Relaxed fetch_update,
checked_add и отказ при исчерпании lease IDs сохранены. Это изменение общего Linux
кода, а не только metadata CLI; новые FFI/native release artifacts не заявлены.

Повторные сборки всех четырёх targets PASS: locked/client-bin/jobs1, private
source/target0700, manifest только rlib. Rust1.97.0; MIPS nightly-2026-06-10,
Zig0.13.0/cargo-zigbuild0.23.0. Каждый полученный SHA-bound SFTP snapshot прошёл
общий ELF admission и readelf: little endian, нужные class/machine, executable
entry, без PT_INTERP/DT_NEEDED; ARM EABI5 hard-float. У MIPS readelf показывает
O32/MIPS32r2/soft-float. Это декларация ABI полученного файла, не проверка исполнения
на firmware, других ISA/ядрах или доказательство воспроизводимости A/B.

| Target | Bytes | SHA-256 |
|---|---:|---|
| aarch64-unknown-linux-musl | 4818040 | 60641ddcdb447c347240e173a341923d3eadc34b9f72fb30954fc4ff00327351 |
| x86_64-unknown-linux-musl | 5574984 | ec567377e46cd8a2ed629bccfb83318fba4e19bf26905df3f49ca77c254a5925 |
| mipsel-unknown-linux-musl | 6846056 | b365638cfc715086052b04ee6a3f5ad3e826077a858387bfc28d3f0d3c8faeaa |
| armv7-unknown-linux-musleabihf | 4981980 | ba223fb91a931aad1c631ae71b111f568cdcb8830a69ece684854e03c591910f |

На .11 GNU build/strict Clippy/fmt PASS;79 sysctl tests PASS,3 inherited ignored,
отдельно настоящий native descriptor recreation test PASS в private network
namespace. Static x86_64-musl executable выполняет24 gateway admission tests на
каждом BusyBox ash/dash без skips, включая56 actual metadata cells на interpreter.
Все52 router helper tests на Linux без skips,37 recipe checks/docs/bindings PASS.

F346 устраняет расхождение CI: четыре targets уже были в матрице, но использовали
плавающие stable/nightly. Теперь те же named pins, явный toolchain в Cargo/rustup,
один job, очищенные compiler overrides и общий static ELF gate вместо одного file.
Workflow разобран PyYAML6.0.3 из отдельного audit-каталога;16 rendered shell steps
прошли bash -n. Точный Python ELF step выполнен на четырёх настоящих binaries и
четырёх усечённых negative copies:8 ожидаемых результатов. GitHub Actions NOT_RUN.

Первый вариант inferred cast as _ не компилировался и сохранён как FAIL;
он заменён lossless преобразованием. Initial library-test harness не передал
conformance siblings; после загрузки12 Git fixtures правильный sysctl:: filter
выполнил79 tests. Два пустых фильтра явно NOT_RUN, не PASS. Windows router helpers
имели10 POSIX skips; квалифицированный итог взят из Linux прогона без пропусков.
317 compile inputs/8 gateway fixture inputs проверены на .10; два317-input source
layouts/12 conformance/16 helper inputs — на .11. Только private Cargo manifest
изменён на rlib. Реквизиты не сохраняются в reproduction scripts.

.10 выполнял собственную последовательную компиляцию и metadata/filesystem
fixtures; добавлены named nightly/rust-src и недостающие pinned std targets,
default toolchains и работающие сервисы не изменялись. .11 — собственная GNU
сборка и private namespace test. Repo binaries/deployment не заменялись.

Текущий остаток Q31 после этой матрицы:

| Область | Состояние |
|---|---|
| Реальная standalone cross-сборка четырёх targets/ELF | DONE в указанном scope |
| UCI/INI, shell lifecycle/rollback и LuCI | Scoped suites PASS; сохранены модельные границы |
| Настоящие ucode/rpcd/UCI/procd/package SDK | OPEN; fixtures не квалифицируют эти платформенные API |
| Preflight→launch config snapshot, core plan generation/ABA | OPEN; текущий exclusion lock не устраняет эти гонки |
| SIGKILL/power-loss installer recovery | Manual recovery; полная bundle transaction не подтверждена |
| Firmware WAN/reboot/DNS/firewall/RSS/throughput | USER_EXCLUDED; cross-build не device test |
| Hermetic shared caches/config/PATH и clean A/B | OPEN; named pins не означают воспроизводимость |

Эта таблица актуализирует исторические cross-build NOT_RUN в предыдущих разделах;
их исходные evidence не переписаны. Пакет:
C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q31-router-cross-matrix-20261006.
Evidence: release/certification/evidence/q31-router-cross-matrix-20261006.json.
Q31 IN_PROGRESS;28/37(75.7%),9 осталось. Q29 SIGKILL FAIL/auto-null ENONET,
Q30 Apple exclusions/callback-drain OPEN и D06 ACCEPTED сохранены.
