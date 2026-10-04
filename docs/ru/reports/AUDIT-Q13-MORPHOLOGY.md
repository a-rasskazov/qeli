# Q13: recordizer, padding и shaping — пакет исправлений shaping

<!-- normative-sync: audit-q13-shaping-v1 -->

**4 октября 2026. Пакет: PASS. Раздел Q13: IN_PROGRESS.**
Общий план: **12/37 DONE/PASS (32,4%)**. Полный аудит этим пакетом не завершён.
Исходники: `82c1ad770a6fa43302263babd67dab4e41043e9b`; Linux-кандидат: `d68bb6dab55234454821a22da1342469759a5d39aaa2c6915781acddddf4d10b`.
Точные hashes всех входов сборки сверены с этим commit; исходная pre-build identity
сохранена в evidence. Нативные A/B сборки используют чистый commit исходников.

## Исправления

| ID | Проблема и результат |
|---|---|
| Q13-S001 | P1: pacing прекращал ожидание на остатке до 6 мс. Общий планировщик теперь выдерживает весь deadline; медленная запись cover засчитывается в паузу. Исправлены два активных TCP writer; тот же helper используется в двух сейчас выключенных UDP ветвях. |
| Q13-S002 | P2: потоки брали время до общего lock; запоздавший старый timestamp сдвигал refill clock назад и повторно добавлял токены. Часы общего cover budget теперь монотонны. |
| Q13-S003 | P2: клиент отвергал `shaping_stealth_mbps = 0` при выключенном stealth, хотя AuthOK сохранял это dormant значение. INI теперь сохраняет его; активный stealth по-прежнему требует положительную скорость. |
| Q13-S004 | P2: клиент принимал активный cover размером 65535 байт, не помещающийся в общий формат записи. Клиентский INI и AuthOK теперь используют одну проверку активных параметров и ceilings. |
| Q13-S005 | P1: клиент считал data rate отдельно на каждом bonded TCP-потоке. Все writer теперь резервируют один бюджет направления; server rate budget уже был общим. |

Ошибка записи TCP cover теперь завершает writer, вместо выхода только из внутреннего
цикла pacing с последующей попыткой отправить payload. Wire format и ключи INI не менялись.
Общий cover budget независим от data rate и считает bytes padding, а не весь внешний трафик.

## Проверки

- Пять assertion FAIL на исходном коде; **7 новых тестов**. **2359 Linux PASS / 60 ignored**,
  полный и минимальный Clippy, fmt PASS. Ошибки импорта теста и `Send` обвязки сохранены;
  финальные источники прошли повторный полный запуск.
- Campaign через shipping release `.rlib`: **10000 roundtrips, 40000 внутренних пакетов,
  40000 повреждённых records, 622431 assertions PASS**. Проверены fragment/inflight/byte caps,
  дубликаты, конфликт, освобождение budget и expiry; peak RSS **11128 KiB**.
  Это bounded invariant campaign, не ASan/libFuzzer и не доказательство исчерпывающего покрытия.
- **10 сетевых cases / 102 assertions PASS**: TCP off/prefer/required, idle cover, stealth,
  три bonded TCP потока и UDP с recordizer/legacy. IPv4 ping после одинаковой нагрузки
  проходит без потерь; idle cover имеет изменяющиеся интервалы в обе стороны.
- Свежая **18-case матрица / 327 assertions**, aggregate IPv4/IPv6 leak и
  **100 TCP + 100 QUIC path flips / 33 soak checks PASS**; отдельно **24 REALITY-TLS/H2 checks**.
- Windows x64, macOS universal, Android arm64/x64: независимые A/B, consumer copies,
  exports и provenance PASS. Это не новый E2E установленного приложения;
  Mac/router/Windows VM runtime исключены пользователем.
- Рабочие сервисы и executable не заменялись; полные snapshots .10/.11 сохранены.

## Замер на этом стенде

Одинаковый directional iperf workload: 6 секунд, с отдельной секундой warm-up.
Три bonded потока проверены тремя параллельными внутренними TCP flows.

| Режим | Upload, Мбит/с | Download, Мбит/с |
|---|---:|---:|
| TCP required, shaping off | 1041.93 | 1572.58 |
| TCP required, idle cover | 1480.05 | 1563.94 |
| TCP stealth 2 Мбит/с, один поток | 1.89 | 1.92 |
| TCP stealth 2 Мбит/с, три потока суммарно | 1.81 | 1.75 |

Это локальная виртуальная топология, не WAN benchmark. Скорости без cap меняются с
нагрузкой CPU и захвата; сравнение idle cover не доказывает ускорение. Результат
проверки rate: число потоков не умножает cap; возможен стартовый burst токенов.

UDP **намеренно сохраняет только idle cover**: обе стороны выключают stealth.
Первый стенд ошибочно ожидал UDP cap и остановился; восемь PASS cases сохранены,
два оставшихся повторены с документированным TCP-only критерием. Это ошибка fixture,
не регрессия продукта и не включение новой UDP-функции.

PCAP ограничен headers: timestamps, original wire lengths и headers сохранены,
cryptographic payload не нужен этому анализу. Для первых полных captures сохранены
source/derived hashes преобразования; удалены только проверенные неактивные remote
копии, локальное evidence сохранено. Не заявляется отсутствие периодических признаков
для любого классификатора или сопротивление vendor DPI.

## Evidence и следующий шаг

Реестр: `release/certification/evidence/q13-shaping-20261004.json`.
Raw: `../audit-debt-20260924/q13-shaping-20261004` относительно audit-worktree.

Далее в Q13: семантические границы recordizer/reassembly, взаимодействие padding и
normalization, review dormant UDP stealth и экстремальных таймеров. Пять исправлений
этого пакета проверены сразу; открытые части раздела не помечаются DONE.
