# Q08: криптография и ключи — первый пакет

<!-- normative-sync: audit-q08-crypto-keys-v1 -->

Дата: 3 октября 2026. **Пакет: PASS; полный Q08: IN_PROGRESS.**
Конфигурации остаются INI. Формат 32-byte keys, алгоритмы и wire protocol не изменены.

## Найденные проблемы

| ID | Проблема | Исправление |
| --- | --- | --- |
| Q08-F001, P2 | Три загрузчика identity/panel/session keys читали весь файл без ограничения, могли зависнуть на FIFO; dangling identity link считалась отсутствующим ключом и заменялась новой identity. | Общий `crypto/key_file.rs`: проверка открытого regular-file inode и размера, максимум 33 прочитанных байта, nonblocking open FIFO на Unix; dangling link — ошибка, без генерации. Временные секретные буферы — Zeroizing. |
| Q08-F002, P2 | Legacy panel-secret мигрировал до захвата modern FileLock. Повреждённый legacy мог молча привести к новому ключу, несовместимому с прежним password_enc. | Modern load, migration и generation выполняются под одной блокировкой с re-check; современный ключ имеет приоритет, повреждённый/недоступный legacy не заменяется новым. |
| Q08-F003, P2 | Оба client verifiers использовали unchecked X25519 DH для static identity. Для ключей малого порядка proof вычисляется с известным нулевым shared secret. | Checked DH отвергает такие identity до проверки proof и отправки credentials в общем transport core. Правильные nondegenerate pins не имели подтверждённого обхода. |

Read/generation logic трёх загрузчиков объединена; отдельные неограниченные чтения удалены. Запись остаётся штатной atomic-private операцией. Ссылки оператора на существующие обычные файлы сохранены; чтение не изменяет прежние owner/mode, созданные файлы — 0600. Повреждённая identity не ротируется автоматически. Для ошибки session key сохранён прежний fallback на ключ процесса с предупреждением, поэтому такие cookies не переживают restart. CLI reversible password storage остаётся best-effort; Argon2 hash — отдельный механизм входа.

## Воспроизведение и проверки

На предыдущем точном release `ba7d93afc47c71592e2d1d20e18d2c7c6a6cb0eb4248b674cf713e756aa1c712`: **6 FAIL из 19** key-storage checks — FIFO identity, dangling link, migration без lock, замена повреждённого legacy, FIFO panel key и FIFO session key. Независимые probes продолжались, общий baseline FAIL. Исправленная baseline fixture освобождает только собственный FIFO, затем штатно останавливает supervisor; private network и внешние host/service snapshots восстановлены. Первоначальный вариант с принудительным убийством supervisor не принят как baseline из-за orphan-worker cleanup.

На финальном release `0fdcb1a4ed45e850b9d7e6cd1b3bc3965f3775c6682ac59bcc0348a028e1a749`: **19 storage + 25 restore/state = 44 HTTP/system checks PASS** в проверенных private NET/mount/PID namespaces. Проверены восемь одновременных identity readers, длины 0/31/33/4 MiB, сохранение inode FIFO и dangling links, обычные operator links, held modern FileLock и приоритет нового ключа, миграция byte-for-byte с 0600, отказ на corrupt legacy, восстановление после отказов и cookie после свежего supervisor. Q07 regression проверяет reissue, legacy migration, mixed users/groups и настоящих VPN-клиентов с tunnel ping после restore, в том числе без panel-secret на новом сервере.

Unit negative vector строит реально вычислимый proof для public points 0 и 1 при DH=0; оба verifiers теперь отказывают, затем штатный proof проходит. Старое unchecked принятие подтверждено кодом и конструкцией proof; live hostile-peer baseline и обход корректного explicit pin не заявлены. Место вызова общего verifier проверено до сборки/отправки credentials в transport core.

Отдельная Python HMAC-SHA256 реализация проверила **5 HKDF wire vectors / 18 checks** всех четырёх схем, направления, порядок IKM и изменение входа. Она не вызывает Rust generator/helper. Это независимая реализация проверки consistency, не внешний криптоаудит или независимая сертификация примитивов.

Linux: **2270 units PASS / 60 ignored**, full/minimal Clippy и rustfmt PASS. Свежие **18/327 matrix**, aggregate leak и **100 TCP + 100 QUIC / 33 soak checks PASS**. Все четыре native cores прошли независимые A/B builds; ABI/canonical-client copies/provenance PASS. .11 snapshots/service/binary сохранены. Текущая .10 пара и её поля записаны в evidence; историческая неатрибутированная вариативность legacy IPv4 dumps остаётся ограничением, общего host-preservation PASS для .10 нет. Рабочие службы не заменялись, push и новый performance benchmark не выполнялись. Физические advisory rows не изменены.

## Что остаётся в полном Q08

Независимые X25519/ML-KEM/AEAD vectors, дальнейший review static binding/proof-before-credentials, TOFU/RNG/nonce exhaustion/rotation/zeroization и owner/mode/link policies. Текущий пакет исправлений полностью проверен; перечисленное — оставшийся объём раздела, а не отложенные обязательные тесты этих исправлений. Bounded read не обещает жёсткий срок обычного filesystem IO. Sidecar locks координируют текущих writers; power loss, несогласованные root writes и старые binaries не сертифицированы. Ранее принятое ограничение AES expanded schedule zeroization сохраняется.

[Свидетельства пакета](../../../release/certification/evidence/q08-keys-20261003.json).
