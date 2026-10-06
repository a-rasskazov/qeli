"""⚠️  MAINTAINER-INTERNAL — это НЕ способ собрать qeli под Keenetic самому.

Скрипт кросс-собирает на ПРИВАТНОМ лаб-хосте по SSH (`LAB_SRV`, креды из `QELI_LAB_PASS`)
— работает только в сети мейнтейнера. Если запустил и получил `Error reading SSH protocol
banner` / ошибку подключения — причина в этом (ты не в сети того хоста). Чтобы получить
клиент под Keenetic: возьми готовый per-arch бинарь из GitHub Releases (aarch64/mipsel
-unknown-linux-musl), см. docs/*/manuals/KEENETIC-DEPLOY.md.

Кросс-сборка client-only бинаря qeli под роутеры Keenetic — обе арки за прогон.

  aarch64-unknown-linux-musl  — новые ARM-кинетики (Cortex-A53); stable + zig-линкер.
  mipsel-unknown-linux-musl   — основной парк (MT7621/7628); tier-3 → nightly -Zbuild-std.

Линкер/cc для обеих арок — zig (уже стоит на .10) через cargo-zigbuild. Сборка
client-only (`--no-default-features --features client-bin`) → без `ring` (нет MIPS).
Скрипт idempotent: ставит недостающие компоненты тулчейна, потом собирает; не падает
на первой ошибке — печатает оба результата. Готовые бинари тянет в release/keenetic/.

Креды из QELI_LAB_PASS. Запуск:
    $env:QELI_LAB_PASS="..."; python scripts/build_keenetic.py
"""
import argparse
import os, sys, posixpath
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))
from native_lab import LabConnection, remote_sha256, pull_verified_artifact
from lab_common import connect, LAB_SRV

REMOTE_ROOT = "/opt/qeli-src"
REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_SRC = REPO_ROOT / "qeli"
LOCAL_OUT = REPO_ROOT / "release" / "keenetic"
ROUTER_MANIFEST_BACKUP = f"{REMOTE_ROOT}/Cargo.toml.router-backup"
PINNED_CARGO_ZIGBUILD = "0.23.0"
TARGETS = {
    "aarch64": "aarch64-unknown-linux-musl",
    "mipsel": "mipsel-unknown-linux-musl",
}
CLIENT_FEATURES = "--no-default-features --features client-bin"
BIN = "qeli-client"


def run(c, cmd, t=120):
    """Выполнить команду; вернуть (rc, combined_out). lab_common.run отдаёт только
    строку — а здесь нужен реальный exit-код, чтобы судить об успехе сборки."""
    _i, o, e = c.exec_command(cmd, timeout=t)
    out = o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")
    rc = o.channel.recv_exit_status()
    return rc, out.strip()


def checked(c, command, timeout=120):
    rc, output = run(c, command, t=timeout)
    if rc != 0:
        raise RuntimeError(f"router command failed (rc={rc}): {command}\n{output}")
    return output


def tail(s, n=25):
    return "\n".join(s.splitlines()[-n:])

def restrict_router_crate_types(c):
    """Build only the rlib dependency needed by qeli-client.

    The persistent checkout is restored in ``finally`` by main. MIPS Zig cannot
    link the desktop/mobile cdylib and must never be asked to build that unused
    artifact as a side effect of a client-only binary.
    """
    restore_router_manifest(c)
    command = (
        f"cp {REMOTE_ROOT}/Cargo.toml {ROUTER_MANIFEST_BACKUP} && "
        f"sed -i 's/^crate-type = \\[\"rlib\", \"cdylib\", \"staticlib\"\\]$/"
        f"crate-type = [\"rlib\"]/' {REMOTE_ROOT}/Cargo.toml && "
        f"grep -qxF 'crate-type = [\"rlib\"]' {REMOTE_ROOT}/Cargo.toml"
    )
    rc, output = run(c, command, t=30)
    if rc != 0:
        restore_router_manifest(c)
        raise RuntimeError(f"cannot restrict router crate types:\n{output}")


def restore_router_manifest(c):
    rc, output = run(c, f"test ! -f {ROUTER_MANIFEST_BACKUP} || mv -f {ROUTER_MANIFEST_BACKUP} {REMOTE_ROOT}/Cargo.toml", t=30)
    if rc != 0:
        raise RuntimeError(f"cannot restore router Cargo.toml:\n{output}")



def sync_tree(c):
    """SFTP всего qeli/src + Cargo.toml/lock в /opt/qeli-src (как lab_sync_build).
    Сначала стираем remote src/bin (точка входа теперь src/client_main.rs, иначе
    cargo авто-обнаружит stale-бинарь). Возвращает число залитых файлов."""
    checked(c, "rm -rf /opt/qeli-src/src/bin", timeout=30)
    sf = c.open_sftp()
    try:
        made = set()
        def ensure(d):
            if d in made or d in ("", "/"):
                return
            ensure(posixpath.dirname(d))
            try: sf.stat(d)
            except IOError:
                try: sf.mkdir(d)
                except IOError:
                    sf.stat(d)
            made.add(d)
        files = []
        for dp, _dn, fn in os.walk(os.path.join(LOCAL_SRC, "src")):
            for f in fn:
                files.append(os.path.join(dp, f))
        for extra in ("Cargo.toml", "Cargo.lock"):
            p = os.path.join(LOCAL_SRC, extra)
            if not os.path.isfile(p):
                raise RuntimeError(f"missing router build input: {p}")
            files.append(p)
        n = 0
        for lp in files:
            rel = os.path.relpath(lp, LOCAL_SRC).replace("\\", "/")
            rp = posixpath.join(REMOTE_ROOT, rel)
            ensure(posixpath.dirname(rp))
            sf.put(lp, rp); n += 1
        return n
    finally:
        sf.close()


def ensure_toolchain(c, targets):
    if any(arch == "mipsel" for arch in targets):
        installed = checked(c, "rustup toolchain list")
        if not any(line.split()[0].startswith("nightly") for line in installed.splitlines() if line.split()):
            checked(c, "rustup toolchain install nightly --profile minimal -c rust-src", timeout=900)
        checked(c, "rustup component add rust-src --toolchain nightly", timeout=300)
    for target in targets.values():
        if target != "mipsel-unknown-linux-musl":
            checked(c, f"rustup target add {target}", timeout=300)
    expected = f"cargo-zigbuild v{PINNED_CARGO_ZIGBUILD}:"
    installed = checked(c, "cargo install --list")
    if expected not in installed.splitlines():
        checked(c, f"cargo install cargo-zigbuild --version {PINNED_CARGO_ZIGBUILD} --locked --force", timeout=1200)
    verified = checked(c, "cargo install --list")
    if expected not in verified.splitlines():
        raise RuntimeError(f"cargo-zigbuild pin mismatch: {verified}")
    print("zig:", checked(c, "zig version"))


def build(c, arch, target):
    print(f"### Сборка {arch} ({target})")
    if arch == "mipsel":
        # tier-3: nightly + сборка std из исходников. Rust компилит mipsel в soft-float
        # ABI, а zig по умолчанию линкует mips как fpxx → конфликт float-ABI на линковке.
        # Принуждаем линковку к soft-float (бинарь не использует FPU — идёт на любом mips).
        cmd = (f"cd {REMOTE_ROOT} && RUSTFLAGS='-C link-arg=-msoft-float' "
               f"cargo +nightly zigbuild "
               f"-Z build-std=std,panic_abort --locked --release --bin {BIN} "
               f"{CLIENT_FEATURES} --target {target} 2>&1")
    else:
        cmd = (f"cd {REMOTE_ROOT} && cargo zigbuild --locked --release --bin {BIN} "
               f"{CLIENT_FEATURES} --target {target} 2>&1")
    rc, out = run(c, cmd, t=1800)
    print(tail(out, 25))
    print(f"{arch} build rc:", rc)
    if rc == 0:
        _, info = run(c, f"file {REMOTE_ROOT}/target/{target}/release/{BIN}; "
                         f"ls -lh {REMOTE_ROOT}/target/{target}/release/{BIN} | awk '{{print $5}}'")
        print("  artifact:", info)
    print()
    return rc


def pull(c, arch, target):
    src = f"{REMOTE_ROOT}/target/{target}/release/{BIN}"
    destination = os.path.relpath(
        os.path.join(LOCAL_OUT, f"{BIN}-keenetic-{arch}"), REPO_ROOT
    ).replace("\\", "/")
    digest = remote_sha256(LabConnection(c), src)
    if digest == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855":
        raise RuntimeError("router artifact is empty")
    sf = c.open_sftp()
    try:
        size, actual, _changes = pull_verified_artifact(sf, src, digest, REPO_ROOT, [destination])
        print(f"pulled {arch}: {size} bytes, sha256={actual}")
    finally:
        sf.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync", action="store_true", help="upload this checkout before building")
    parser.add_argument("arch", nargs="?", choices=tuple(TARGETS))
    args = parser.parse_args()
    do_sync = args.sync
    targets = {args.arch: TARGETS[args.arch]} if args.arch else TARGETS
    try:
        c = connect(LAB_SRV)
    except Exception as e:
        sys.exit(
            f"\nне достучаться до приватного лаб-хоста мейнтейнера {LAB_SRV[0]}: {type(e).__name__}: {e}\n\n"
            "Это ВНУТРЕННИЙ скрипт мейнтейнера — он собирает на приватном лаб-хосте по SSH,\n"
            "это НЕ способ собрать qeli под Keenetic самому. Возьми готовый per-arch бинарь\n"
            "из GitHub Releases (aarch64 / mipsel -unknown-linux-musl); см. docs/*/manuals/KEENETIC-DEPLOY.md.\n"
        )
    results = {}
    restricted = False
    try:
        # Recover an interrupted previous manifest before --sync overwrites it.
        restore_router_manifest(c)
        if do_sync:
            print("synced", sync_tree(c), "files")
        ensure_toolchain(c, targets)
        restrict_router_crate_types(c)
        restricted = True
        for arch, target in targets.items():
            try:
                results[arch] = build(c, arch, target)
                if results[arch] == 0:
                    pull(c, arch, target)
            except (OSError, RuntimeError) as error:
                results[arch] = 1
                print(f"{arch} failed: {error}")
    finally:
        try:
            if restricted:
                restore_router_manifest(c)
        finally:
            c.close()
    print("\n===== ИТОГ =====")
    for arch in targets:
        print(f"  {arch}: {'OK' if results.get(arch) == 0 else 'FAIL'}")
    passed = all(results.get(arch) == 0 for arch in targets)
    print("KEENETIC_BUILD:", "PASS" if passed else "PARTIAL/FAIL")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
