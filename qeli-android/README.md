# qeli-android

Android-клиент qeli: системный VPN через `VpnService` (весь трафик и DNS на уровне ОС, не
пер-приложенческий прокси). Connect, handshake, обфускация, криптография и packet pumps
выполняются общим Rust-ядром; Kotlin остаётся адаптером Android API и UI.

- Общая карта документации — [docs/ru/index.md](../docs/ru/index.md)
- Подключение «с нуля» (выдача `qeli://` на сервере) — [GETTING-STARTED §8.1](../docs/ru/manuals/GETTING-STARTED.md)
- Все ключи конфигурации — [CONFIG.md](../docs/ru/manuals/CONFIG.md)
- Если не подключается — [TROUBLESHOOTING.md](../docs/ru/manuals/TROUBLESHOOTING.md)

## Технологии

- **Kotlin**, `minSdk 28` (Android 9), `targetSdk 37`, Material Components.
- **`VpnService`** — TUN-интерфейс, маршруты, DNS, per-app split tunnel.
- **JNI к Rust-ядру** (`libqeli.so`, `app/src/main/jniLibs/{arm64-v8a,x86_64}/`) —
  единый TCP/UDP/Reality transport, ML-KEM-768, QUIC/MTU, shaping и bonding. JNI также
  предоставляет credential-free UDP first-flight probe для проверки доступности профиля.
- Foreground-сервис со `specialUse`-типом: туннель живёт, пока приложение свёрнуто.

## Структура

```
app/src/main/kotlin/com/qeli/
├── MainActivity.kt        — UI: профили, импорт (QR/ссылка/файл), лог, настройки, бэкап
├── QeliService.kt         — platform adapter: protect/trust, NetworkPlan/TUN, reconnect
├── TransportCore.kt       — JNI owner общего Rust transport и native UDP diagnostic
├── ProfileStore.kt        — хранилище профилей (AES-GCM + Android Keystore)
├── QeliTileService.kt     — плитка в «Быстрых настройках»
├── QeliWidgetProvider.kt  — виджет на рабочий стол
├── BootReceiver.kt        — автоподключение после перезагрузки
├── UpdateChecker.kt       — проверка обновлений (opt-in)
├── crypto/BackupCrypto.kt — шифрование импорта/экспорта профилей (не transport)
└── model/Config.kt        — разбор/сборка flat-INI и `qeli://`
```

## Возможности

| Возможность | Как работает |
|---|---|
| **Импорт профиля** | QR-код (камера), вставка `qeli://`-ссылки, тап по `qeli://`-ссылке (deep link) или UTF-8 файл в формате flat-INI (не более 256 КиБ). Неверная UTF-8 кодировка отвергается; исходный INI передаётся общему парсеру без обрезки конца. JSON как конфиг намеренно отвергается; JSON остаётся только форматом контейнера бэкапа |
| **Per-app split tunnel** | Выбор приложений в режиме «только эти» (`addAllowedApplication`) или «кроме этих» (`addDisallowedApplication`) |
| **Плитка Quick Settings** | Подключение/отключение из шторки |
| **Виджет** | Статус и переключение с рабочего стола |
| **Автоподключение** | После перезагрузки (`BOOT_COMPLETED`) и/или при запуске приложения |
| **Доверенный Wi-Fi** | Локальный список точных SSID: Qeli снимает VPN в доверенной сети и восстанавливает его после выхода. При Android lockdown/`kill_switch` пауза запрещена, потому что TUN обязан оставаться установленным |
| **Автоопрос профилей** | Opt-in, выключен по умолчанию; после включения проверяет доступность только пока приложение видно и VPN отключён, ручные проверки доступны всегда |
| **Доступ к локальной сети** | Тумблер «разрешить LAN» при full-tunnel (принтеры, NAS, роутер) |
| **Изменение активного профиля** | Если сохранить INI или список приложений при работающем туннеле, текущий сеанс продолжит использовать прежние настройки. Отключитесь и подключитесь снова; приложение покажет напоминание. Если список профилей изменился, пока открыт редактор, откройте его заново |
| **Несколько окон Qeli** | Если одно окно уже сохранило профили, устаревшее окно откажется записывать свой список. Перезапустите его перед повторной правкой; подтверждённый импорт резервной копии тоже проверяет, что хранилище не изменилось с момента открытия |
| **Бэкап профилей** | Экспорт/импорт JSON; **с парольной фразой** — шифрованный контейнер (PBKDF2-HMAC-SHA256 + AES-256-GCM), совместимый с десктопом. Пустая фраза = **открытый JSON с паролями**. JSON ограничен 8 МиБ, шифрованный файл — 12 МиБ; повреждённый UTF-8 отвергается |
| **Формат времени в логе** | Пять вариантов, совпадают с серверным `[logging] time_format` — удобно сверять логи |
| **Проверка обновлений** | Opt-in, выключена по умолчанию |

## Разрешения и зачем они

| Разрешение | Зачем |
|---|---|
| `INTERNET`, `ACCESS_NETWORK_STATE`, `ACCESS_WIFI_STATE` | сеть, выбранный физический carrier и реакция на его смену (Wi-Fi ⇄ LTE) |
| `NEARBY_WIFI_DEVICES`, `ACCESS_FINE_LOCATION` | чтение текущего SSID для доверенного Wi-Fi; без runtime-разрешения SSID считается неизвестным и VPN остаётся включённым |
| `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_SPECIAL_USE` + `FOREGROUND_SERVICE_LOCATION` | туннель и проверка доверенного SSID продолжают работать в foreground-сервисе без открытой Activity; location-тип включается только при активной функции и выданном разрешении |
| `POST_NOTIFICATIONS` | уведомление активного туннеля (Android 13+) |
| `WAKE_LOCK` | ограниченный partial wake lock активного туннеля; системный Doze может игнорировать его |
| `RECEIVE_BOOT_COMPLETED` | автоподключение после перезагрузки (если включено) |
| `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` | запрос исключения из оптимизации батареи; решение принимает пользователь, автоматический перезапуск зависит от Android |
| `CAMERA` | сканирование QR с профилем |
| `QUERY_ALL_PACKAGES` | список приложений для per-app split tunnel |

## Запуск

1. Установите APK со страницы **GitHub Releases** (или соберите, см. ниже).
2. На сервере выдайте ссылку: `qeli add-client <user> --link --host <хост:порт>`.
3. В приложении: **Add profile → Scan QR** или вставьте `qeli://`-ссылку — профиль
   появится со всеми параметрами и **запиненным ключом сервера**.
4. Нажмите кольцо подключения и подтвердите системный запрос VPN.

Full-tunnel, «маршрутизировать локальные сети», LAN-доступ и per-app split tunnel
переключаются в приложении и **не передаются** в `qeli://`-ссылке — это локальные настройки.
Список доверенных SSID также хранится только на устройстве. Совпадение выполняется точно и
регистрозависимо; точка доступа с тем же именем может подделать доверенную сеть, поэтому эту
функцию нельзя считать криптографической проверкой Wi-Fi.

## Сборка из исходников

Нужен Android SDK и JDK 17+.

```bash
cd qeli-android
./gradlew assembleDebug        # APK: app/build/outputs/apk/debug/app-debug.apk
./gradlew testDebugUnitTest    # юнит-тесты config/UI adapters и бэкапа
```

Нативное ядро (`libqeli.so`) в репозитории уже собрано — пересобирать его нужно только при
изменении Rust-кода (см. `scripts/` в корне репозитория).

`reality-tls` H2 реализован именно в `libqeli.so`: установленный APK не получает его после
обновления сервера. Нужны пересборка native core, упаковка нового APK и обновление приложения.

> Инкрементальная сборка иногда раздувает APK — если размер вырос неожиданно, сделайте
> `./gradlew clean` и пересоберите.

## Shared native configuration core

The editor and portable policies require the Rust ABI 1.16 `ConfigCore` JNI service.
For JVM tests, run `python scripts/build_client_core.py --debug` from repository root
and set the printed `QELI_CONFIG_NATIVE_LIBRARY`. For APK builds, build with `--android`
and set `QELI_NATIVE_JNI_DIR` before Gradle. This replaces the jniLibs inputs.
See [shared configuration](../docs/eng/plans/CLIENT-CONFIG-CORE.md) for prerequisites and release A/B gates.


## Проверки JNI и Android runtime

JVM-тесты используют текущую host-библиотеку, указанную через
`QELI_CONFIG_NATIVE_LIBRARY`. Для тестового APK сначала соберите Android-ядро
командой `python scripts/build_client_core.py --android --debug` из корня
репозитория и передайте напечатанный `QELI_NATIVE_JNI_DIR` в окружение Gradle.
Для x86_64 эмулятора можно добавить `--abis x86_64`. Нужны NDK 26.3.11579264
и cargo-ndk 4.1.2; скрипт выбирает Android API 28 через `--platform`.

На выделенном эмуляторе после `installDebug` разрешите VPN для тестового приложения
через `adb shell appops set com.qeli ACTIVATE_VPN allow`, затем выполните
`./gradlew connectedDebugAndroidTest`. Проверяются упакованный ConfigCore JNI
(INI round-trip, отказ от JSON-конфига и поддельной ссылки), Android Keystore,
диагностический журнал и настоящий `VpnService.Builder.establish()` для трёх
сетевых планов. Это ещё не проверка передачи трафика через удалённый VPN-сервер.

Устаревший `e2e_android.py` (каталог `scripts/`), создававший JSON-конфиги и подставлявший старые
plaintext preferences, удалён. Служебные JSON-контейнеры и миграция старого
app-owned хранилища не меняются. Release A/B, arm64 и остальные runtime-режимы
проверяются отдельно от этой тестовой сборки.

Результаты прогона 24 сентября: [154 JVM + 6 Android instrumentation tests](../docs/ru/reports/AUDIT-Q34-ANDROID-RUNTIME.md).

Сверка store 2 октября: [Q25-F210](../docs/ru/plans/AUDIT-DEBT.md). Прямая запись внешнего процесса в encrypted store в обход координации не поддерживается; после правки активного INI требуется явное переподключение.


## Legacy profile recovery и Release проверки

Неудачная миграция старой encrypted/Tink-базы сохраняет ciphertext и доступную revision,
блокирует обычную запись и разрешает только явно подтверждённый backup restore через CAS.
Системный cloud/device-transfer исключён явными правилами; для нового устройства нужен
экспорт/импорт backup. Потерянный Keystore key без backup не восстанавливается.
minSdk28 сохраняется; active index использует совместимый точный BigDecimal conversion.
[Q29 store/manifest/package](../docs/ru/reports/AUDIT-Q29-ANDROID-STORAGE-PACKAGE.md):
167 JVM,18 debug instrumentation PASS;Release/R8 build иlint с0errors/55warnings.
Debug test APK не является подходящим тестовым variant для minified Release. Production
signing,полный Release VPN и другие lifecycle режимы проверяются отдельно.


## Android VPN publication

Native NetworkPlan ACK starts the TUN packet pump; CONNECTED waits for Android's
VPN NetworkCallback matching plan addresses (and MTU on API29+). A fresh observer
also handles reconnect with a retained TUN and an owner excluded by per-app include.
Publication failure stops the native generation and retries while retaining
TUN/system lockdown. minSdk28 is preserved; API28 runtime is not qualified here.

ACK запускает native packet pump, а CONNECTED ждёт Android NetworkCallback с
адресами текущего плана и MTU на API29+. Новый observer работает и на прежнем TUN,
в том числе при исключённом UID владельца. При timeout генерация останавливается
для retry; TUN/системный lockdown сохраняются.
[Q29 F279: проверки и ограничения](../docs/ru/reports/AUDIT-Q29-ANDROID-CONNECTED-GATE.md).


## Инструментированный Release с R8

Для отдельного test APK R8 должен сохранить API общих библиотек, к которым
обращаются AndroidJUnitRunner и тесты. Matching mapping сам по себе не возвращает
удалённые классы. `-PqeliTestBuildType=release` подключает `app/instrumentation-abi.pro`:
это явно выбранный тестовый вариант, с minification/resource shrinking и дополнительным
сохранением ABI. Обычный Release без этого параметра использует прежние production-правила.
`-PqeliLabReleaseSigning=true` разрешён только для лаборатории; он подписывает APK
debug-ключом и не делает приложение debuggable.

После изменения AndroidTest или зависимостей соберите оба APK, получите classpaths,
перегенерируйте правила из pre-R8 классов и повторно соберите оба APK:

```bash
./gradlew -PqeliTestBuildType=release -PqeliLabReleaseSigning=true assembleRelease assembleReleaseAndroidTest
./gradlew -PqeliTestBuildType=release :app:printInstrumentationAbiClasspaths --console=plain > ../abi-classpaths.log
cd ..
python scripts/generate_android_instrumentation_abi.py --classpath-log abi-classpaths.log --r8-jar "$ANDROID_HOME/build-tools/36.0.0/lib/d8.jar" --android-jar "$ANDROID_HOME/platforms/android-37.0/android.jar" --evidence-dir abi-generation
cd qeli-android
./gradlew -PqeliTestBuildType=release -PqeliLabReleaseSigning=true assembleRelease assembleReleaseAndroidTest
cd ..
python scripts/generate_android_instrumentation_abi.py --classpath-log abi-classpaths.log --r8-jar "$ANDROID_HOME/build-tools/36.0.0/lib/d8.jar" --android-jar "$ANDROID_HOME/platforms/android-37.0/android.jar" --evidence-dir abi-verification --check
python scripts/check_android_instrumentation_abi.py --app qeli-android/app/build/outputs/apk/release/app-release.apk --test qeli-android/app/build/outputs/apk/androidTest/release/app-release-androidTest.apk
```

Каталоги evidence должны быть новыми; нужен JDK в `JAVA_HOME` или `PATH`.
Для другого SDK/R8 укажите фактические пути. Генератор отклоняет неизвестные
unresolved references; разрешены только известные отсутствующие platform stubs
runner и D8 bootstrap. Правила сохраняют имена ABI и разрешают R8 расширять
доступность классов: иначе перенос дочернего класса в другой пакет ломает наследование.
DEX-проверка проверяет три метода Trace и доступность superclass, но не заменяет
запуск тестов. Запускайте `connectedReleaseAndroidTest` на выделенном устройстве;
сетевым сценариям Q29 дополнительно нужен изолированный серверный fixture.

[Q29: проверка Release runner и границы результата](../docs/ru/reports/AUDIT-Q29-ANDROID-RELEASE-RUNNER.md).


## Per-app UID и Private DNS: лабораторная проверка

`scripts/build_android_network_probe.py` собирает второй framework-only пакет
из существующего AndroidTest receiver, без отдельной реализации сетевых проб.
Он предназначен только для выделенного стенда. `audit_android_data_plane_lab.py`
поддерживает `--suite app-policy --variant release --apps-mode include|exclude`:
нужны закреплённые `fixed/` APK/manifest и `probe/audit-probe.apk`/`manifest.json`.
Обвязка требует root и свой `/var/tmp/qeli-q29-data-*`, создаёт NET/MNT/PID namespaces
и readonly AVD, восстанавливает состояние. Запуск на рабочем сервере не требуется.

Проверяются два разных ordinary UID, IPv4/IPv6 TCP/UDP/DNS, семь состояний VPN/lockdown,
Private DNS off/Automatic и отрицательный strict-provider сценарий. Профиль этой
матрицы использует `kill_switch=false`, чтобы пользователь мог менять OS lockdown;
это отдельная проверка от `kill_switch=true`. Прямой трафик исключённого UID без
lockdown ожидаем; с lockdown он блокируется. Доверенный strict DoT не квалифицирован.
[Q29: результаты и границы](../docs/ru/reports/AUDIT-Q29-ANDROID-APP-POLICY.md).
