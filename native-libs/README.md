# native-libs — нативные зависимости сборок qeli-клиентов

Централизованная копилка нативных библиотек, которые встраиваются в клиентские
приложения. Раньше они лежали по разным местам (`qeli-android/.../jniLibs`,
`qeli-win/QeliWin/native`, `qeli-mac/QeliMac/native`, `wintun/`) — здесь собраны
в одном месте для обзора и переиспользования.

> **Это копии.** Каждый build-стек читает либу из СВОЕЙ папки (см. колонку
> «потребляется»). При обновлении либы клади и туда, и сюда (либо синкай отсюда).
> Источник Rust-кода — локальная `qeli/`; штатные скрипты каждый раз полностью синхронизируют
> его в `/opt/qeli-src` на .10 и `/root/qeli-src` на .11 перед сборкой.

## Содержимое

Текущий ABI общего Rust-клиента — **1.16** (`qeli/src/transport_core/mod.rs`).
Проверяемые SHA-256 каждой canonical/consumed пары записаны в
[SHA256SUMS](SHA256SUMS), соответствие исходникам — в
[PROVENANCE](PROVENANCE), а два независимых прохода сборки — в
`reproducibility/{desktop,android}.json`. После любой правки Rust-исходников
или build-рецептов эти проверки обязаны выполняться заново.

| Файл | Таргет | Потребляется |
|---|---|---|
| `android/arm64-v8a/libqeli.so` | aarch64-linux-android | `qeli-android/app/src/main/jniLibs/arm64-v8a/` → APK |
| `android/x86_64/libqeli.so` | x86_64-linux-android | `qeli-android/app/src/main/jniLibs/x86_64/` → APK |
| `windows-x64/qeli.dll` | x86_64-pc-windows-gnu | `qeli-win/QeliWin/native/qeli.dll` → EmbeddedResource |
| `macos-universal/libqeli.dylib` | universal2 (arm64+x86_64) | `qeli-mac/QeliMac/native/libqeli.dylib` → `.app` Content |
| `third-party/windows-x64/wintun.dll` | x86_64 | `qeli-win/QeliWin/wintun/wintun.dll` |
| `third-party/windows-x64/windivert/WinDivert.dll` и `WinDivert64.sys` | x86_64 | `qeli-win/QeliWin/windivert/` |

Все четыре first-party библиотеки собираются из одного Rust-крейта `qeli`
с `--no-default-features --features transport-core-ffi`; серверный/web stack
в них не входит. Экспортная поверхность содержит 6 Reality C ABI,
22 `qeli_client_*`, `qeli_config_request` (чистый API редактора INI),
а Android дополнительно требует 21 `Java_com_qeli_TransportCore_*`.
Платформенные приложения хранят интерфейс, системные разрешения и TUN;
общее ядро выполняет parsing/policy, transport, handshake и data plane.
Исходный `qeli/src/client` Linux `rp_filter` код компилируется только для Linux
и не меняет API этих библиотек, но изменение общего исходного дерева всё равно
требует новой подтверждённой A/B сборки и provenance. iOS XCFramework
собирается отдельно с macOS/Xcode и не хранится в этом каталоге.

## Как собрать (всё на лаб-сервере .10/.11, на Windows Rust-тулчейна нет)

Штатный путь требует чистых и закоммиченных `qeli/src`, `Cargo.toml` и `Cargo.lock`, а пароль
лабы получает только из `QELI_LAB_PASS` (пользователь — `QELI_LAB_USER`, по умолчанию
`root`). Desktop строится на `.10`, Android — на `.11`:

```powershell
python scripts/build_native_libs_p4.py   # qeli.dll + universal2 libqeli.dylib
python scripts/build_android_so_11.py    # arm64-v8a + x86_64 libqeli.so
```

Оба скрипта используют один контракт `qeli-native-repro-v1`:

1. фиксируют commit, source digest и `SOURCE_DATE_EPOCH`, проверяют чистоту исходников;
2. проверяют exact Rust 1.97.0; дополнительно desktop — Zig 0.13.0,
   cargo-zigbuild 0.23.0, GNU ld 2.44 и apple-codesign 0.29.0, Android — NDK
   26.3.11579264 и cargo-ndk 4.1.2; необходимые Rust targets ставятся идемпотентно;
3. полностью синхронизируют локальный Rust source на соответствующую лабу;
4. дважды собирают `--locked` с `CARGO_INCREMENTAL=0`, `panic=unwind`, remap исходного пути
   и разными чистыми `CARGO_TARGET_DIR` (`a`/`b`); после сохранения конечного файла тяжёлый
   target-кэш прохода удаляется, чтобы A/B укладывался в свободное место лабы;
5. требуют byte-identical SHA256 для A/B и полный export gate (6 Reality + 22 client;
   Android дополнительно 21 JNI). Для macOS до ad-hoc подписи нормализуются случайный
   `LC_UUID` и недопустимый нестабильный Zig 0.13 GOT-index, install name закреплён как
   `@rpath/libqeli.dylib`;
6. только после этого атомарно заменяют canonical/consumed копии и создают
   `native-libs/reproducibility/{desktop,android}.json`.

SSH/SFTP, ограниченный source-sync, проверка удалённого SHA256 и атомарный pull реализованы
один раз в `scripts/native_lab.py`; обязательные A/B-проходы — в `scripts/native_repro.py`.
CI запускает 35 mock/unit-тестов этих контрактов, включая отказ до записи при несовпадении хеша,
запрет destination вне репозитория, строгий toolchain и гарантию, что выполняются оба прохода
`a` и `b`, а также точное совпадение 81 распознаваемого ключа конфигурации Rust/Android/
Windows/macOS/iOS.

Раньше desktop-скрипт не синхронизировал локальный source и не забирал результат: он мог
собрать случайно оставшееся `/opt/qeli-src`, а затем позволить записать текущий digest против
чужих бинарников. Теперь `provenance.py --update` проверяет обе A/B-evidence, финальные файлы,
source digest и закреплённые версии и отказывается менять [PROVENANCE](PROVENANCE), если хотя
бы одно условие нарушено. После **обоих** lab-скриптов:

```
bash native-libs/verify.sh --update
python native-libs/provenance.py --update
```

APK после native gate собирается `scripts/rebuild_apk.py [--release]`: он использует уже
проверенные `jniLibs/*.so`, одним удалённым preflight создаёт каталоги синхронизации,
собирает unit tests + APK, проверяет подпись release-варианта и забирает файл только после
сверки удалённого SHA256, не затирая native cores. `scripts/build_mac_universal.py` так же
проверяет canonical dylib, пакетно подписывает и инспектирует каждый Mach-O и атомарно
забирает universal ZIP по SHA256. Крупные self-contained tar.gz кэшируются на лабе только
после сверки с локальным SHA256, поэтому неизменившийся повторный прогон не загружает их заново.
Если verified remote SHA256 уже совпадает со всеми локальными копиями, итоговый бинарник/ZIP
также не передаётся повторно.

### wintun.dll
Сторонняя, официальный Wintun **0.14.1** с https://www.wintun.net (WireGuard),
SHA-256 `E5DA8447DC2C320EDC0FC52FA01885C103DE8C118481F683643CACC3220DAFCE`.
Не пересобираем. Windows CI выполняет `scripts/verify_windows_drivers.ps1`: проверяет
FileVersion обеих копий, SHA-256 и валидную Authenticode-подпись `WireGuard LLC`
(certificate thumbprint `DF98E075A012ED8C86FBCF14854B8F9555CB3D45`). Замена бинарника требует
явного обновления версии, хеша и signer pin после проверки официального upstream archive.

### WinDivert (WinDivert.dll + WinDivert64.sys)
Сторонняя, официальный релиз 2.2.2 с https://reqrypt.org/windivert.html
(LGPL-3.0 OR GPL-2.0). Не пересобираем. NOTICE/LICENSE находятся в
`third-party/windows-x64/windivert/`. После замены обеих копий выполнить
`bash native-libs/verify.sh --update`.
