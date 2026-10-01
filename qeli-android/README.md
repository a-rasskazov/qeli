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
| **Бэкап профилей** | Экспорт/импорт JSON; **с парольной фразой** — шифрованный контейнер (PBKDF2-HMAC-SHA256 + AES-256-GCM), совместимый с десктопом. Пустая фраза = **открытый JSON с паролями** |
| **Формат времени в логе** | Пять вариантов, совпадают с серверным `[logging] time_format` — удобно сверять логи |
| **Проверка обновлений** | Opt-in, выключена по умолчанию |

## Разрешения и зачем они

| Разрешение | Зачем |
|---|---|
| `INTERNET`, `ACCESS_NETWORK_STATE`, `ACCESS_WIFI_STATE` | сеть, выбранный физический carrier и реакция на его смену (Wi-Fi ⇄ LTE) |
| `NEARBY_WIFI_DEVICES`, `ACCESS_FINE_LOCATION` | чтение текущего SSID для доверенного Wi-Fi; без runtime-разрешения SSID считается неизвестным и VPN остаётся включённым |
| `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_SPECIAL_USE` + `FOREGROUND_SERVICE_LOCATION` | туннель и проверка доверенного SSID продолжают работать в foreground-сервисе без открытой Activity; location-тип включается только при активной функции и выданном разрешении |
| `POST_NOTIFICATIONS` | уведомление активного туннеля (Android 13+) |
| `WAKE_LOCK` | не терять соединение в глубоком сне |
| `RECEIVE_BOOT_COMPLETED` | автоподключение после перезагрузки (если включено) |
| `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` | чтобы система не убивала туннель |
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
