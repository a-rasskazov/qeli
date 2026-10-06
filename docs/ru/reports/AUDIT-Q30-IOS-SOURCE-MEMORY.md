# Q30: лимиты памяти, владение probe и итоговая сверка исходников

<!-- normative-sync: q30-ios-source-memory-v1 -->

6 октября 2026. Исправления F303–F306. Критерий Q30 **Review and dead code**
завершён на уровне исходников; весь Q30 остаётся IN_PROGRESS. Runtime и остальные
четыре критерия checklist не объявляются PASS.

## F303: отмена probe зависела от следующего callback ОС

Физический path-probe отменял NWConnection, но Swift ждал callback cancelled или
таймер10s. Отмена до регистрации continuation могла сопровождаться последующей
установкой handler/start. Completion дублировал AsyncResultCompletion; TCP ping
использовал ещё один gate без обработчика отмены Task. Оба handler захватывали
собственный connection.

CancellableProbeCompletion сериализует старт ресурса с terminal completion.
Отмена сразу завершает Swift, включая отмену до park/start. Любой terminal path
снимает handler, отменяет connection и освобождает cleanup captures перед resume.
Поздние callback и синхронный reentry сохраняют один результат/cleanup. Удалены
дублирующие IOSPathProbeCompletion и ProbeGate; таймеры10s/4s сохранены.
Это не ожидание завершения callback ОС и не runtime-доказательство освобождения
Apple-объектов; отложенный timer удерживает только небольшой completion result.

## F304: удалённые/изменённые профили сохраняли ping-очередь и старые результаты

Очередь копировала профиль, а изменение архива не удаляло queued work/reachability/ID.
Старый результат мог заново добавить удалённый профиль или описать его прежний INI.
Повторное удаление/создание удерживало исторические профили, несмотря на лимит256
в актуальном архиве.

Ping принимает только актуальные ID/configText. Commit архива удаляет устаревшие
queued requests и результаты удалённых/изменённых профилей. Освобождаются только
queued ID: активный запрос сохраняет ID/slot до завершения ограниченного вызова.
Публикация повторяет проверку ID/configText. Лимит4 активных worker сохранён;
отмена/ожидание native UDP не объявляются добавленными. Переименование без
изменения INI не отменяет запрос. Сетевой runtime ping не выполнялся.

## F305: лимит числа строк не ограничивал память журнала

500 сообщений произвольной длины создавали большой stored/decoded/encoded архив.
Теперь сообщение ограничено UTF-8-safe префиксом4КиБ с маркером усечения;
готовый JSON-архив ограничен1МиБ и500 строками, сохраняет недавний suffix.
Расширение управляющих символов при JSON escaping входит в бюджет.
Старый oversized архив отклоняется до JSON decode; следующий append записывает
ограниченную замену. UserDefaults может выделить legacy Data до проверки размера.
Локальные lock не гарантируют атомарный append между процессами. Общий RSS/leak
и достаточная память реального PacketTunnel не объявляются подтверждёнными.

## F306: timeout обновлений ограничивал время, но не размер ответа HTTP

URLSession.data целиком буферизовал ответ releases до decode. Проверка теперь
читает URLSession bytes в collector с пределом1МиБ, отклоняет первый лишний байт
и проверяет отмену Task. Сохранены private-path admission,10s time budget,
ephemeral session и cancellation barrier перед teardown. Session инвалидируется
при success/error/size rejection. Это предел collector, не всех внутренних буферов
Foundation/network или измеренного RSS. Реальный streaming/cancellation NOT_RUN.

## Инвентарь исходников и мёртвый код

В текущем инвентаре92 Swift-файла:33 общих production/support,13 app,3 PacketTunnel,
4 widget,29 тестовых и10 test-only wire/crypto. Общие исходники входят не во все
бинарники: membership задаётся исключениями/явными widget-файлами project.yml.
Wire/crypto после F302 остаются в XCTest. ABI/native headers и provenance бинарников
сохранены; устаревший комментарий engine исправлен на compatibility floor1.16.

Воспроизводимый declaration/reference scan и ручная классификация оставили12
single-reference declarations: два @main root, два callback NetworkExtension,
три callback WidgetKit/control provider, четыре UIViewControllerRepresentable
и FileDocument.fileWrapper. Это framework entry points, они сохранены.
Частота имени — консервативный поиск кандидатов, не доказательство выполнения всех
веток или полного отсутствия мёртвого кода. F303 удаляет два конкретных дублирующих
owner; предыдущие удаления F292/F302 сохранены в своих sealed packets.

| Слой | Результат проверки исходников | Неподтверждённая квалификация |
| --- | --- | --- |
| INI/models/core policy adapters | Shared ABI/config bindings и прежняя source review | Реальная интеграция Swift/core |
| Archive/Keychain/MDM/preferences | F290,F292–F294,F298–F299 | Entitlements, interprocess races, настройки ОС |
| App/UI/widgets/import/export/update | F291,F300–F301,F304,F306; framework roots сохранены | Presentation, callbacks, URLSession cancellation |
| Provider/roaming/packet seam | F295–F297,F303; владение и bounded batches | Callback drainage, RSS/leaks, native joins |
| Wire/crypto conformance support | F302 test-only membership; golden helpers сохранены | XCTest/Xcode build |

Source limits: native event/uplink/downlink по256КиБ,64 packets/batch и65 535байт/packet;
uplink handoff256 packets/512КиБ; один blocking DNS resolver; config256КиБ/archive8МиБ/
backup12МиБ/256 профилей; route expansion256 и snapshot sample6. Сумма этих ограничений
не является общим бюджетом памяти: decrypt/validation всего архива и временный encode
могут перекрывать выделения. Реальный запас памяти extension не проверен. Отправленные
OS settings/read удерживают lease до реального callback; никогда не вернувшийся
callback остаётся OPEN.

## Проверки

11 новых XCTest:4 resource-owner,4 log на изолированных UserDefaults,3 update-stream
(exact limit, раннее отклонение размера, отмена до чтения). XCTest, Swift/Xcode
project/build, реальные Network/URLSession/UI/Keychain, simulator, signed IPA,
RSS/leaks и callback/native joins — NOT_RUN. Apple runtime исключён пользователем;
toolchain не устанавливался. Source surrogate не выдаётся за runtime PASS.

Шесть Python IPA-verifier fixtures,10 XML, все9 проверок документации, bindings и diff
PASS. Исторические runtime статусы/даты/артефакты сохранены для неизменных Git inputs;
Linux/Android матрица не повторялась. Итог28/37(75.7%),9 остаются. Q29 SIGKILL FAIL/
auto-null ENONET,D06 и platform skips сохранены. Завершение source review не закрывает
весь Q30 и не устраняет открытые платформенные наблюдения.

Raw packet: C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/q30-ios-source-memory-20261006.
Evidence: release/certification/evidence/q30-ios-source-memory-20261006.json.
