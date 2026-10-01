# Q25-F202 — воспроизводимые native cores и Android runtime

<!-- normative-sync: audit-q25-native-rebuild-v1 -->

Дата: 1 октября 2026. Исходник для A/B: `27db1a22`, digest
`dce152196ab7b13ba42f9808a571ba95ac494c7ccbbd1c69578bd0de90c1979c`.
Проверенные артефакты перенесены в `dev` коммитом `08a1823d`.

## Исправленные блокеры

Рецепт native-сборки помещал release-вывод в `/tmp` клиентской VM, где доступен
tmpfs менее 1 ГиБ. Он теперь использует дисковый `/var/tmp` и до сборки требует
8 ГиБ свободного места. На .10 отказ старого бюджета воспроизведён; после
удаления только пересоздаваемых Cargo incremental caches на .10 и .11
места хватило. Работающие бинарники и службы не заменялись.

Android `libc::in6_pktinfo.ipi6_ifindex` имеет знаковый тип, Linux —
беззнаковый. Проверенные преобразования на приёме и отправке устранили
cross-compile error; `Control::send` теперь возвращает ошибку, а batch scratch
очищает указатели при отказе. Шесть Linux UDP unit и один privileged IPv6
wildcard-тест прошли. Рецепт Android JVM-тестов собирает host JNI из того же
синхронизированного исходника и задаёт путь к нему Gradle; прежние 88
`UnsatisfiedLinkError` исчезли.

## Артефакты и проверки

Два независимых release-прохода A/B дали одинаковые SHA-256 для каждой цели:

| Цель | SHA-256 |
|---|---|
| Windows x64 DLL | `c601cffa1ab922552276358ed977445fc6bb1258c37b3c925c06eb437cb84d13` |
| macOS universal2 dylib | `1f5037414c5c19e040094bfb7d3bb2f6064a4e0781718f83e4ead267a3c2034d` |
| Android arm64-v8a so | `d3ccc2389600c9559d612c9deea4f03eeda73963dd5af2aea07a835f8a18bbca` |
| Android x86_64 so | `6c4db7c9ac12c482c6d62fe74347e9abec891042acd0daaca44ed3135b53077e` |

Windows/macOS экспортируют 6 REALITY и 22 клиентских символа; Android —
дополнительно 21 TransportCore JNI-символ. Universal2 содержит обе архитектуры
Mach-O. Все канонические и потребляемые копии обновлены. Проверки
`native-libs/verify.sh` (14 записей) и `provenance.py --check` проходят после
переноса коммита. Локальные 71 тест рецептов PASS.

Windows .NET-сборка прошла без ошибок и предупреждений; selftest со свежей DLL:
143 PASS, 0 FAIL. Android Gradle debug APK и JVM-тесты: 167 PASS, 0 ошибок.
APK версии 0.8.2 (code 722), SHA-256
`9ec9967bc691bd7b575572a85c7fd28d6478728d6395f89b47e5bbb678eb9968`;
обе `.so` внутри ZIP побайтно совпадают с A/B-артефактами.

На read-only Android 14/API 34 x86_64 AVD прямой `adb shell am instrument`
дал **11/11 PASS**: INI/JNI, отказ JSON-конфига и поддельной ссылки,
диагностический журнал, шифрованное хранилище/версия/границы и TUN builder.
Временный эмулятор остановлен. `connectedDebugAndroidTest --offline` не смог
получить отсутствующий в Gradle cache UTP 32.2.1; это отказ запуска через
Gradle, а не результат тестов. Первый эмулятор завис при одновременной работе
Gradle; тесты прошли отдельно на экземпляре с ограничением памяти.

## Граница результата

D11 закрыт для актуальных native cores, A/B, ABI, копий, provenance и доступных
пакетов. D12 остаётся открытым для Android VPN handshake/трафика и других
runtime-сценариев. Windows VM, Mac/Xcode/iOS и router runtime пропущены по
решению пользователя; macOS dylib структурно проверена, приложение и поведение
на Mac не подтверждены. Сборка APK — debug, не release-публикация.

[Реестр техдолга](../plans/AUDIT-DEBT.md) · [Рецепты native](../../../native-libs/README.md)
