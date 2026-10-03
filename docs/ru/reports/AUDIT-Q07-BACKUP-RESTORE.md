# Q07: backup, restore и history — первый пакет

<!-- normative-sync: audit-q07-backup-restore-v1 -->

Дата: 3 октября 2026. **Пакет: PASS; полный Q07: IN_PROGRESS.**
Конфигурации остаются INI; JSON используется для служебных ответов API/evidence.

## Подтверждённые ошибки

| ID | Проблема | Исправление |
| --- | --- | --- |
| Q07-F001, P2 | Portable archive исключает lock-файлы, но exact shape-check требовал вложенный `server.ini.lock`; собственный корректный архив не восстанавливался. | Вложенная проверка допускает сохранённые `.lock`, как publisher и pruner. Inode действующего lock не заменяется. |
| Q07-F002, P1 | Restore принимал отсутствующий identity в overlay и ключ неверной длины; следующий запуск мог создать новый pin или не поднять профиль. | Активные профили требуют обычные 32-byte identity-файлы. Managed paths читаются только из staging даже в overlay; внешние зависимости должны уже существовать. Никакой генерации при проверке. |
| Q07-F003, P1 | Restore принимал HTTPS config без PEM-пары или с невалидными PEM. | Пути remap-ятся в staging, штатный TLS checker проверяет полную согласованную пару без генерации. Внешние пути проверяются по существующим файлам. |
| Q07-F004, P2 | GNU tar сохранял UID/GID загруженного архива; root-сервер затем отвергал custom-path INI как недоверенный. | Extraction использует `--no-same-owner`; содержимое получает владельца пользователя сервера. Прежняя нормализация 0600/0700 сохранена. |

На прежнем release шесть checks FAIL: exact nested lock, отсутствующий identity
в overlay, повреждённый identity, отсутствующая и невалидная TLS-пара, чужой UID.
Missing identity в exact на старом release отказывал по nested lock; этот результат
не считается независимым воспроизведением проверки identity. Все шесть дефектных
случаев прошли на новом release вместе со штатными roundtrip-сценариями.

## Реальная проверка

Финальный release: `d502a58df16f6d86062edaf17d3ee55bc3bb786ae4909bfe9e6d63e56612e7b3`.
38 HTTP/system checks PASS в отдельных NET/mount/PID namespaces:

- Backup с `/etc/qeli/nested/server.ini`, custom users INI и точным profile identity.
- Overlay сохраняет extras; exact удаляет top-level extra и сохраняет nested locks.
- Snapshot не включает предыдущие snapshots/uploads/staging; временные файлы убраны.
- Отказ до публикации при traversal, absolute path, symlink, hardlink, FIFO,
  executable, malformed/missing INI/users/identity/TLS. Прежнее дерево сравнивается
  по SHA, исключая операционные snapshots и sidecars.
- Expanded size >64 MiB и >5000 entries; успешное восстановление после отказов.
- Второй restore сразу получает 409, пока первый ждёт сторонний config FileLock;
  status остаётся отзывчивым, первый успешно заканчивает после unlock.
- Чужой UID/GID становится UID/GID сервера. Custom matching TLS pair проходит
  restore, новый HTTPS-процесс стартует и аутентифицирует администратора.
- Новый обычный worker после roundtrip стартует с тем же identity, без ротации pin.

Дополнительно 75 HTTP checks history/config транзакций PASS на том же release:
точные bytes/revisions/snapshots, 8 writers, ENOSPC, read-only, отказ target rename,
FileLock budget и recovery. Linux: 2265 units PASS / 60 ignored, full/minimal
Clippy и rustfmt PASS. Native и release qualification указаны в evidence ниже.
Это функциональный аудит, не performance benchmark или physical qualification.

## Оставшийся Q07

Полный Q07 пока не закрыт. Следующий пакет: отказы и crash во время multi-file
publication/prune, доказательство ручного recovery из rollback snapshot, внешний
users/identity writer, mixed inline/external users и panel-secret, retention и
запрет подмены операционных snapshots, остальные INI trust boundaries и строгий
разбор exact query. Старый history positive/fault набор проверен, но архивная
публикация всех файлов не является атомарной транзакцией и автоматического rollback
сейчас нет. Это отражено в прежнем [отчёте бюджета](AUDIT-Q05-ARCHIVE-BUDGET.md).

Рабочие службы и binaries не заменялись. Все полные .11 snapshots совпали.
SDK .10 A/B прошёл; default/explicit legacy IPv4 firewall dumps отличаются,
а nft, прочие host-поля, PID/start и binary сохранились. Историческая неатрибутированная
вариативность .10 сохраняется как ограничение: полный network-preservation PASS
для .10 не заявляется. Правила не удалялись/не восстанавливались.
Завершённые исторические debug binaries сохранены losslessly в gzip с проверкой
SHA; завершённый lint cache удалён, исходники и test logs сохранены.

[Свидетельства первого пакета](../../../release/certification/evidence/q07-backup-restore-20261003.json).

Квалификация этого release: свежие 18/327 matrix, aggregate leak и 100 TCP + 100 QUIC / 33 soak checks PASS. Все четыре native cores прошли A/B и побайтно совпали с Q06; canonical/client copies и ABI/provenance согласованы.
