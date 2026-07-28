# Contributing to qeli

Спасибо за интерес к проекту! Вклады принимаются через pull request.

## Лицензия вклада (inbound = outbound)

Отправляя вклад, вы соглашаетесь, что он лицензируется на условиях лицензии того
каталога, в который вносится (см. [LICENSING.md](LICENSING.md)):
- `qeli/` (ядро/сервер) → **AGPL-3.0-only**;
- `qeli-android/`, `qeli-win/`, `qeli-mac/`, `qeli-ios/` → **MPL-2.0**.

**CLA / передача авторских прав не требуются.** Вы сохраняете авторство; код входит
под той же открытой лицензией, что и каталог («inbound = outbound»).

## Developer Certificate of Origin (DCO)

Вместо CLA мы используем **DCO** — лёгкое подтверждение, что вы имеете право прислать
этот код. Каждый коммит должен содержать строку `Signed-off-by`:

```
git commit -s -m "ваше сообщение"
```

Это добавляет в конец сообщения коммита:

```
Signed-off-by: Ваше Имя <your.email@example.com>
```

Имя/email должны быть настоящими (`git config user.name` / `user.email`) и совпадать
с автором коммита. Если забыли `-s` — поправьте последний коммит:
`git commit --amend -s --no-edit` (для нескольких — `git rebase --signoff`).
PR без подписи во всех коммитах не пройдёт проверку DCO в CI.

### Текст DCO 1.1

```
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.
1 Letterman Drive
Suite D4700
San Francisco, CA, 94129

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.


Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

## Разработка

### Тулчейн и системные пререквизиты

- **Rust stable.** Заведомо рабочая версия — **rustc 1.96.0** (на ней собирается лаба);
  CI берёт актуальный `stable`. `rust-version` (MSRV) в `qeli/Cargo.toml` не объявлен,
  так что «older stable» не гарантирован — если собираете на более старом тулчейне и
  что-то не компилируется, обновитесь, прежде чем заводить issue.
- **Nightly** нужен только для двух вещей: fuzz-харнесов (`cargo +nightly fuzz`) и
  кросс-сборки под mipsel (tier-3, `-Zbuild-std`). Для обычной работы не требуется.
- **Сборка `.deb`** (`qeli/debian/Makefile`) — Debian/Ubuntu-хост и **`dpkg-deb`**.
  Для публикуемых пакетов цель одна — **`make deb-portable`**, а ей нужны **`zig`** и
  **`cargo-zigbuild`** в `PATH`: они прибивают ABI glibc к 2.28, иначе бинарь
  собирается против glibc хоста и падает на Ubuntu 22.04 с `GLIBC_2.39 not found`
  (так уехали 0.7.8–0.7.11). `make deb` — только для локального использования.
- **Клиенты**: .NET SDK (Windows/macOS), Android SDK + Gradle, Xcode + XcodeGen (iOS).
  Точные версии — в `.github/workflows/ci.yml`, он же источник истины.

### Команды

- Сервер/ядро (Linux), в `qeli/`: `cargo build --release --features jemalloc` +
  `cargo test --workspace` + `cargo clippy --all-targets -- -D warnings`.
  **`--features jemalloc` для СЕРВЕРНОГО бинаря обязателен**: без него RSS воркера
  упирается в ~180 МБ под churn'ом хендшейков (glibc держит освобождённые арены)
  вместо ~40–60 МБ с jemalloc — см.
  [GETTING-STARTED](docs/ru/GETTING-STARTED.md). Клиентской сборке фича не нужна,
  а `qeli/debian/Makefile` включает её сам (`CARGO_FEATURES`).
- Клиенты: см. `.github/workflows/ci.yml` (Android gradle, Windows/macOS `dotnet`).
- Документация — начните с карты: [docs/ru/index.md](docs/ru/index.md) · [docs/eng/index.md](docs/eng/index.md).
- **Правили доки или добавляли ключ конфигурации?** Прогоните `python3 scripts/check_docs.py`
  (это же делает CI). Скрипт проверяет: нет битых ссылок, нет страниц-сирот вне индекса,
  наборы файлов `docs/ru` и `docs/eng` совпадают, каждый INI-ключ, который сервер реально
  эмитит, описан в `CONFIG.md` на **обоих** языках, каждый упомянутый в бэктиках файл
  исходников существует, в GitHub-ссылках не осталось незаполненного `<owner>`, и в
  `CHANGELOG.md` есть секция под разрабатываемую версию.
  Новый документ нужно добавить в оба языковых дерева и в `index.md`.
- **Бампите версию?** Не правьте 22 файла руками — `python3 scripts/sync_version.py --write`.
  Источников истины два и они намеренно разные: **разрабатываемая** версия берётся из
  `qeli/Cargo.toml` (идёт в сборочные файлы и обзорные `README.md`), **выпущенная** — из
  новейшего тега `v*` (идёт в баннер «документация описывает X» в десяти документах).
  Без `--write` скрипт только проверяет и ничего не пишет; это же делает CI.
- Всё локально одной командой: `scripts/ci-check.sh` (доки + сборка + тесты + clippy).
- Перед PR: убедитесь, что сборка/тесты/линт зелёные и каждый коммит подписан (`-s`).
