#!/usr/bin/env python3
"""Check that the committed native cores were built from the source in THIS tree.

WHY. `native-libs/verify.sh` answers "do the two copies of each library match each other".
It cannot answer "does this binary correspond to the Rust source next to it" — and that is
the question that actually went wrong: the cores in this repository were built from the
0.7.12 source and stayed while `qeli/src` moved on, so every GUI client shipped an older
realtls / FFI core than the tree claimed. Nothing in review or CI could see it, because a
`.so` has no readable diff.

The digest below is deliberately over the SOURCE, not the binaries: reproducing a
byte-identical `.dll` needs a pinned toolchain and a reproducible-build setup this project
does not have yet, but "the source changed after the binaries were built" is both cheap to
detect and the failure that actually occurs.

Usage:
  python native-libs/provenance.py --check    # exit 1 if the cores are stale
  python native-libs/provenance.py --update   # after a DELIBERATE rebuild

Run from the repository root.
"""
import hashlib
import os
import subprocess
import sys

PROVENANCE = os.path.join("native-libs", "PROVENANCE")


def source_digest() -> str:
    """SHA256 over `"<path> <sha256>\\n"` for every source that lands in the cdylib."""
    files = []
    for dirpath, _dirnames, filenames in os.walk(os.path.join("qeli", "src")):
        for name in filenames:
            if name.endswith(".rs"):
                files.append(os.path.join(dirpath, name))
    for manifest in ("Cargo.toml", "Cargo.lock"):
        files.append(os.path.join("qeli", manifest))
    files.sort()
    agg = hashlib.sha256()
    for path in files:
        rel = os.path.relpath(path, ".").replace("\\", "/")
        with open(path, "rb") as fh:
            # Normalise CRLF -> LF before hashing. .gitattributes stores these files with
            # LF, but a Windows checkout materialises them with CRLF, so hashing the bytes
            # on disk yields a different digest per platform: a digest recorded on Windows
            # can never match the Linux CI checkout, and the check fails for a reason that
            # has nothing to do with the cores being stale. Line endings do not change what
            # rustc compiles, so they must not change the digest either.
            data = fh.read().replace(b"\r\n", b"\n")
            agg.update(f"{rel} {hashlib.sha256(data).hexdigest()}\n".encode())
    return agg.hexdigest()


def recorded_digest() -> str | None:
    if not os.path.exists(PROVENANCE):
        return None
    with open(PROVENANCE, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("source-digest"):
                return line.split(":", 1)[1].strip()
    return None


def main() -> int:
    if not os.path.isdir(os.path.join("qeli", "src")):
        print("run this from the repository root", file=sys.stderr)
        return 2

    actual = source_digest()
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"

    if mode == "--update":
        # Rewrites only the digest/commit lines; the explanatory text is kept.
        base = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "qeli/src", "qeli/Cargo.toml", "qeli/Cargo.lock"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        with open(PROVENANCE, encoding="utf-8") as fh:
            text = fh.read()
        out = []
        for line in text.splitlines(keepends=True):
            if line.startswith("source-digest"):
                out.append(f"source-digest : {actual}\n")
            elif line.startswith("base-commit"):
                out.append(f"base-commit   : {base}\n")
            elif line.startswith("dirty-sources"):
                n = len(dirty.splitlines())
                out.append(f"dirty-sources : {n} file(s) modified vs base-commit at build time\n")
            else:
                out.append(line)
        with open(PROVENANCE, "w", encoding="utf-8", newline="\n") as fh:
            fh.writelines(out)
        print(f"recorded source-digest {actual}")
        return 0

    expected = recorded_digest()
    if expected is None:
        print(f"MISSING: {PROVENANCE} has no source-digest line", file=sys.stderr)
        return 1
    if expected == actual:
        print("OK: the committed native cores match the source in this tree.")
        return 0
    print(
        "STALE NATIVE CORES.\n"
        f"  recorded : {expected}\n"
        f"  actual   : {actual}\n"
        "\n"
        "qeli/src has changed since the .so/.dll/.dylib were built, so the GUI clients\n"
        "would ship an older realtls/FFI core than this tree describes. Rebuild them:\n"
        "  python scripts/build_native_libs_p4.py   # windows + macos, on lab .10\n"
        "  python scripts/build_android_so_11.py    # android, on lab .11\n"
        "then `bash native-libs/verify.sh --update` and\n"
        "`python native-libs/provenance.py --update`.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
