# Q29: Android — хранилище, manifest и Release-пакет

<!-- normative-sync: q29-android-storage-package-v1 -->

**5 октября 2026: этап PASS; Q29 IN_PROGRESS. План 28/37 (75,7%), осталось 9 разделов.**

| Находка | Исправление |
|---|---|
| F273 | `specialUse` объявлял неизвестное manifest-свойство вместо `android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE`. Исправлено имя и добавлено описание назначения. PackageManager на API34 подтверждает свойство, privacy/permission и типы сервиса. Старый APK воспроизводит NameNotFoundException; это не доказательство отказа startForeground на всех ОС. |
| F274 | Ошибка чтения старой Tink-базы прерывала open: Activity не получала version и не могла явно восстановить backup. Частичные keysets могли выглядеть пустым хранилищем. Теперь version доступна, обычные чтение/запись блокируются, backup restore явно разрешает замену через CAS. Старое encrypted state сохраняется; неполная миграция не запускает plaintext/default save. Ошибка удаления уже проверенной legacy-копии не блокирует пригодный новый store. |
| F275 | `BigInteger.intValueExact()` требует API31, а minSdk28. Заменён на точный `BigDecimal.intValueExact()` с API1: дробь/overflow по-прежнему отвергаются. Release lint больше не имеет NewApi error. Старый вызов подтверждён исходником и первым lint-прогоном; runtime Android9–11 не заявлен. |
| F276 | Одного allowBackup=false недостаточно для всех OEM D2D-переносов. Добавлены явные исключения девяти credential/device-protected доменов для cloud/device-transfer и fullBackupContent=false для старых ОС. Проверены packaged XML и manifest; физический OEM/cloud/D2D backup не исполнен. Пользовательский экспорт backup через UI остаётся доступным. |

Удалены пять недостижимых веток SDK<26/<28 в boot/tile/widget/Activity. minSdk остаётся28; дополнительные значения INI не вводились. JSON archive/journal — внутренние контейнеры, JSON-конфиг по-прежнему отвергается ядром.

## Проверки и evidence

- **167 JVM PASS, 0 failures/errors/skips**, production host ConfigCore JNI. Сборки debug/androidTest, unsigned Release с R8/resource shrinking и lintRelease завершены. Lint: **0 errors,55 warnings**, без baseline/suppression новых ошибок. Сохранена классификация предупреждений: версии зависимостей, UI/layout/plurals, legacy attributes и намеренный host-JNI override. AAB language splits не проверены; текущая дистрибуция APK.
- **18/18 debug instrumentation PASS** на временном Android14/API34 x86_64 AVD. Пять новых cases: platform specialUse property, private service/types, cloud/D2D resource contract, unreadable/partial legacy recovery; ещё один новый case проверяет потерю Keystore key. Это **6 новых tests** против прежних12. Проверены exact ciphertext preservation, обычный write/editor refusal, explicit restore, stale restore rejection и reopen; реальные JNI INI round-trip/reject JSON и TUN split/full/dual establish повторены.
- Baseline старого production APK: **3 tests,2 ожидаемых FAIL**, service privacy/type case PASS. Исходники продукта в baseline не изменены; добавлены только проверки.
- Первое полное выполнение:16 PASS, TUN case отказал из-за отсутствующего ACTIVATE_VPN в обвязке. Результат сохранён; исправлена подготовка временного AVD, затем18 PASS. Две ошибки компиляции новых тестов (nullable SDK return и попытка чтения скрытого ApplicationInfo field), offline lint-cache failure и NewApi lint failure также сохранены; они не объявлены регрессиями продукта.
- Debug test APK против minified Release не является квалифицированным Release test variant: падение сохранено и диагностируется отдельно от production UI smoke. Не заявляются3 Release instrumentation PASS.
- Native digest/14 actual artifact hashes и183 предыдущих managed/Swift inputs/7 DLLs неизменны; прежние1248 .NET checks не повторялись и не называются свежим Android результатом. APK содержат точные исходные JNI.so; Rust/native AB пересборка не требовалась.

R8 production UI smoke: **PASS на Android14/API34 x86_64: штатная launcher Activity, холодный запуск, процесс жив и не debuggable, без fatal-ошибок logcat. При первом запуске открывается системный запрос исключения из оптимизации батареи. Проверен запуск приложения, а не полный сценарий взаимодействия с Activity или VPN-трафик.**. Release-fixture подписан только debug test key для временного AVD; это не production signing и не опубликованный APK.

Raw: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q29-android-20261005.
Evidence: release/certification/evidence/q29-android-storage-package-20261005.json.

## Эксплуатация и остаток Q29

Если legacy-профили не читаются, не удаляйте app data/старые encrypted preferences автоматически. Возобновить миграцию после временного отказа можно перезапуском процесса; при потере ключа нужен пригодный ранее экспортированный backup. Восстановление выполняется через существующее подтверждение UI и отказывает устаревшему снимку. Без backup утраченный device-bound key не восстанавливается. Системный перенос encrypted prefs не переносит ключ Keystore; явный экспорт/импорт backup — поддержанный путь.

Только отдельные read-only AVD sessions; исходные userdata SHA/mtime/size сохранены. Работающий qeli.service, host routes/firewall/resolver и .10 не изменялись. Push/deploy не выполнялись; основная ветка сохраняет пользовательский WIP.

Остаток Q29: полноценные connect/reconnect/cancel/revoke/process-death/always-on/lockdown/Doze, JNI/TUN generation/protect races и трафик TCP/UDP; Release lifecycle, старые Android API, arm64/физический LTE, дополнительные backup/миграционные ошибки. Сетевые Android результаты D12 остаются историческими, не заменяют эти проверки. Полный раздел пока не закрыт.

Контракты: [specialUse property](https://developer.android.com/reference/android/content/pm/ServiceInfo), [BigDecimal exact/API1](https://developer.android.com/reference/java/math/BigDecimal), [BigInteger exact/API31](https://developer.android.com/reference/java/math/BigInteger), [Android backup/D2D](https://developer.android.com/identity/data/autobackup).

Диагностика тестового варианта Release: NoClassDefFoundError для kotlin.jvm.internal.Intrinsics в AndroidJUnitRunner/MonitoringInstrumentation. Debug-тестовый APK зависит от классов неминифицированного приложения; штатная production Activity запускается без instrumentation. Этот результат не считается PASS instrumentation Release или дефектом запуска клиента.
