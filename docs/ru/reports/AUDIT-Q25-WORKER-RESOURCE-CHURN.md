# Q25-F204 — ресурсный churn Linux worker

<!-- normative-sync: audit-q25-worker-resource-churn-v1 -->

Дата: 1 октября 2026. Текущий Rust-исходник, ранее синхронизированный на
лабу .11; `cargo build --offline --locked --bin qeli` с
`CARGO_INCREMENTAL=0`, `CARGO_BUILD_JOBS=1` завершился PASS.
Проверенный debug binary SHA-256:
`ae59962eebe483ad4d312bda34cb5634bf66bcd2ca372869b17b15e8c95e66d9`.
Полный `qeli/src`: 308 файлов, одинаковый digest
`64be415e454438fe2b90129168069e0be9a9caf4a7a467bca24398fd4a6250aa`
в checkout и на .11.

Существующий `scripts/audit_worker_lifecycle.py` получил ограниченный
`--resource-reloads 10`. Каждый кейс выполняется в новых network,
mount и PID namespaces с приватно примонтированным `/etc/qeli`.
После готовности worker проверяется отказ второго владельца и
отвергнутый повреждённый SIGHUP; затем выполняются 10 корректных
SIGHUP с контрольным запросом между ними. Снимки `/proc/<pid>/fd`,
socket fd, `task` и `VmRSS` сохраняются до и после каждого reload.
Заранее заданный критерий: финальный прирост fd/socket fd/tasks не
более 2, максимальный sampled RSS не более +32 МиБ. После SIGTERM
сверяются TUN, routes, firewall, sysctl, control socket и journal.

| Режимы | Результат | Δ fd/socket/tasks | Максимальный Δ RSS |
|---|---:|---:|---:|
| TCP: off/manual/route/nat66 | 4/4 PASS | 0/0/0 во всех | 15 520 КиБ |
| UDP: off/manual/route/nat66 | 4/4 PASS | 0/0/0 во всех | 15 472 КиБ |

Всего **8/8 кейсов и 80 корректных reload PASS**; все восемь
отказов второго worker и восемь повреждённых reload сохранили
действующий worker. После каждой остановки контрольный сокет,
TUN, правила Qeli и `sysctls.state` отсутствуют; полные снимки
сетевых объектов до/после совпали по установленным проверкам.
Верхняя граница RSS — sampled peak, не непрерывный пик между пробами.
`py_compile` и `git diff --check` прошли.

Raw evidence: `C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260924/d13-resource-20261001/`
(`results.json`, 8 × `resource-samples.json`, network-before/after,
активные firewall dumps и worker logs). Identity-ключи не копировались
из изолированного стенда.

D13 остаётся **IN_PROGRESS**: нужны текущий same-session reconnect
soak и многопрофильный stop/fault сценарий. Старые 100 release handover
на `ea87fd49` сохранены отдельно и не считаются подтверждением
нынешнего бинарника.

[Реестр техдолга](../plans/AUDIT-DEBT.md) ·
[Прежний release soak](AUDIT-Q34-RELEASE-SOAK.md)
