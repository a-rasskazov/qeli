# Q14: актуальная проверка worker lifecycle

<!-- normative-sync: audit-q14-current-lifecycle-v1 -->

**Пакет PASS; Q14 IN_PROGRESS.** 4 октября 2026.
Исходник `711782d6d1cb6e41889c7c359f964e7242e314fc`, Linux artifact `5605f4b7867cefb0886f14c943c499693fb41a0d0f767f8675292115d5f27c55`.
Evidence: `release/certification/evidence/q14-lifecycle-current-20261004.json`.

На текущем release заново исполнены три существующих изолированных fixture:

- **8/8 worker cases**: TCP/UDP × IPv6 off/manual/route/nat66; ошибочный INI,
  отказ второго worker, отклонённый SIGHUP, работающий control, однократный post_down,
  удаление TUN/NAT/sysctl и before/after snapshots. **80 корректных reload**:
  fd/socket/tasks и выборочный RSS остаются в установленном допуске.
- **22/22 recovery checks**: разные control/state и вложенные mount/PID
  не обходят namespace admission; SIGKILL, удалённый профиль, сохранение чужих правил,
  post_down удерживает lease; startup failure позволяет последующий запуск.
- **14/14 multiprofile checks**: TCP+UDP одновременно, ошибочный и 10 корректных
  reload, stop, SIGKILL и восстановление после удаления соседнего профиля;
  обе hook-команды выполняются однократно, итоговая сеть/control/journal восстановлены.

Обычный Linux unit-набор **2365 PASS / 60 ignored** исполнен заново. В evidence
выделены прошедшие группы supervisor/tasks/control/hooks/shutdown; это выборка
общего запуска, не дополнительные тесты. Privileged ignored этим не объявляются PASS.
Все три fixture имеют собственные NET/mount/PID namespaces и приватный /etc/qeli.
Снимки основного host совпали; рабочий service/executable не заменялся.

Review проверил Child/PID ownership, retry/очередь Restart/Reload, cancel-safe join,
deferred profile resources, control path/IO/drain, доверие загруженному INI,
once-only post_down, process groups и пределы вывода hooks, бюджеты 45/60 секунд.
Новых подтверждённых дефектов в этом пакете нет. Старые D09/D13 и другие evidence
сохраняют исходные SHA и границы: они не объявляются новыми прогонами.

Следующий пакет Q14: полный процесс supervisor с crash/respawn/restart/stop,
занятые bind/TUN с работающим соседним профилем; давление control clients и ошибки/
отмена hooks на границе поколения. Отдельно требуется проверить владение и остановку
фоновых panel/metrics/autostart задач supervisor, включая отмену внешнего future.
Эти остатки мешают итоговому PASS раздела.
Общий план после завершения Q13: **13/37 (35,1%)**.
