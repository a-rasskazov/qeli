"""⚠️  MAINTAINER-INTERNAL — NOT the way to build qeli for OpenWrt yourself.

This script cross-builds on a PRIVATE lab host over SSH (`LAB_SRV`, creds from
`QELI_LAB_PASS`); it only works on the maintainer's network. If you ran it and got
`Error reading SSH protocol banner` / a connection error, that is why — you are not on
that host's network. To build the OpenWrt client:
  • from source: OpenWrt SDK/buildroot + the package `Makefile` (rust feed):
        make package/qeli/compile V=s
  • or download a prebuilt per-arch binary from GitHub Releases
        (aarch64 / x86_64 / mipsel / armv7 -unknown-linux-musl).
  See qeli-openwrt/INSTALL.md.

Cross-build the qeli CLIENT-only binary for the common OpenWrt arches, on the
lab build host (.10) via cargo-zigbuild — same toolchain as build_keenetic.py.

These prebuilt binaries are for hand-install / packing a per-arch .ipk without the
full OpenWrt SDK. The proper from-source build is the package `Makefile` (rust feed).

  aarch64-unknown-linux-musl   — ARM routers (Filogic, RPi, x86 ARM)
  x86_64-unknown-linux-musl    — x86_64 routers / VMs / x86 APUs
  mipsel-unknown-linux-musl    — MT7621 / 7628 (tier-3 → nightly -Zbuild-std)
  armv7-unknown-linux-musleabihf — older ARMv7 routers (ipq40xx, mvebu v7)

Client-only (`--no-default-features --features client-bin`) → no `ring`, builds on mips.
Creds from QELI_LAB_PASS. Run:  python qeli-openwrt/build/build_openwrt.py [--sync] [arch]
"""
import argparse
import os
import sys
import posixpath

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# Reuse the lab connection helpers from scripts/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from native_lab import LabConnection, remote_sha256, pull_verified_artifact
from lab_common import connect, LAB_SRV  # noqa: E402

REMOTE_ROOT = "/opt/qeli-src"
ROUTER_MANIFEST_BACKUP = f"{REMOTE_ROOT}/Cargo.toml.router-backup"
PINNED_CARGO_ZIGBUILD = "0.23.0"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOCAL_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "qeli"))
LOCAL_OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dist"))
CLIENT_FEATURES = "--no-default-features --features client-bin"
# The client-only target is `qeli-client` (src/client_main.rs); the default `qeli`
# bin requires server+client features. Invoked directly: `qeli-client --config <f>`.
BIN = "qeli-client"

# arch -> (rust target, needs -Zbuild-std nightly)
TARGETS = {
    "aarch64": ("aarch64-unknown-linux-musl", False),
    "x86_64":  ("x86_64-unknown-linux-musl",  False),
    "mipsel":  ("mipsel-unknown-linux-musl",  True),
    "armv7":   ("armv7-unknown-linux-musleabihf", False),
}


def run(c, cmd, t=1800):
    _i, o, e = c.exec_command(cmd, timeout=t)
    out = o.read().decode("utf-8", "replace") + e.read().decode("utf-8", "replace")
    return o.channel.recv_exit_status(), out.strip()


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
    checked(c, "rm -rf /opt/qeli-src/src/bin", timeout=30)
    sf = c.open_sftp()
    try:
        made = set()

        def ensure(d):
            if d in made or d in ("", "/"):
                return
            ensure(posixpath.dirname(d))
            try:
                sf.stat(d)
            except IOError:
                try:
                    sf.mkdir(d)
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
            sf.put(lp, rp)
            n += 1
        return n
    finally:
        sf.close()


def ensure_toolchain(c, targets):
    if any(build_std for _target, build_std in targets.values()):
        installed = checked(c, "rustup toolchain list")
        if not any(line.split()[0].startswith("nightly") for line in installed.splitlines() if line.split()):
            checked(c, "rustup toolchain install nightly --profile minimal -c rust-src", timeout=900)
        checked(c, "rustup component add rust-src --toolchain nightly", timeout=300)
    for target, build_std in targets.values():
        if not build_std:
            checked(c, f"rustup target add {target}", timeout=300)
    expected = f"cargo-zigbuild v{PINNED_CARGO_ZIGBUILD}:"
    installed = checked(c, "cargo install --list")
    if expected not in installed.splitlines():
        checked(c, f"cargo install cargo-zigbuild --version {PINNED_CARGO_ZIGBUILD} --locked --force", timeout=1200)
    verified = checked(c, "cargo install --list")
    if expected not in verified.splitlines():
        raise RuntimeError(f"cargo-zigbuild pin mismatch: {verified}")
    print("zig:", checked(c, "zig version"))


def build(c, arch, tgt, build_std):
    print(f"### {arch} ({tgt})")
    if build_std:
        # tier-3 mips: nightly + build std; force soft-float (zig links mips fpxx,
        # rust emits soft-float → float-ABI clash on link). Same as keenetic.
        cmd = (f"cd {REMOTE_ROOT} && RUSTFLAGS='-C link-arg=-msoft-float' "
               f"cargo +nightly zigbuild -Z build-std=std,panic_abort --locked --release "
               f"--bin {BIN} {CLIENT_FEATURES} --target {tgt} 2>&1")
    else:
        cmd = (f"cd {REMOTE_ROOT} && cargo zigbuild --locked --release --bin {BIN} "
               f"{CLIENT_FEATURES} --target {tgt} 2>&1")
    rc, out = run(c, cmd, t=1800)
    print(tail(out, 20))
    print(f"{arch} rc: {rc}")
    if rc == 0:
        src = f"{REMOTE_ROOT}/target/{tgt}/release/{BIN}"
        destination = os.path.relpath(
            os.path.join(LOCAL_OUT, f"qeli-client-openwrt-{arch}"), REPO_ROOT
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
    return rc


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
            f"\ncannot reach the maintainer's private build host {LAB_SRV[0]}: {type(e).__name__}: {e}\n\n"
            "This is a MAINTAINER-INTERNAL helper — it cross-builds on a private lab host over SSH,\n"
            "it is NOT how you build qeli for OpenWrt yourself. To build the OpenWrt client:\n"
            "  * from source: OpenWrt SDK/buildroot + the package Makefile (rust feed):\n"
            "        make package/qeli/compile V=s\n"
            "  * or download a prebuilt per-arch binary from GitHub Releases\n"
            "        (aarch64 / x86_64 / mipsel / armv7 -unknown-linux-musl).\n"
            "See qeli-openwrt/INSTALL.md.\n"
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
        for arch, (target, build_std) in targets.items():
            try:
                results[arch] = build(c, arch, target, build_std)
            except (OSError, RuntimeError) as error:
                results[arch] = 1
                print(f"{arch} failed: {error}")
    finally:
        try:
            if restricted:
                restore_router_manifest(c)
        finally:
            c.close()
    print("\n===== SUMMARY =====")
    for a in targets:
        print(f"  {a}: {'OK' if results[a] == 0 else 'FAIL'}")
    passed = all(results.get(arch) == 0 for arch in targets)
    print("OPENWRT_BUILD:", "PASS" if passed else "PARTIAL/FAIL")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
