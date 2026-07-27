#!/usr/bin/env python3
"""Keep every version string in the repo in sync. Run from anywhere:

    python3 scripts/sync_version.py            # check only (CI / pre-release)
    python3 scripts/sync_version.py --write     # stamp the versions into every file

There are TWO versions in this repo and they are deliberately different:

  * the DEVELOPMENT version — what the tree currently builds. Source of truth:
    `qeli/Cargo.toml`. It is mirrored into ten build files plus the two overview
    READMEs ("Rust 2021, version X").
  * the RELEASED version — the newest published package. Source of truth: the
    newest `v*` git tag. It is quoted by the "these docs describe X" banner in
    ten documents, because a reader installing from a `.deb` gets that version,
    not whatever HEAD happens to be.

Bumping by hand means editing 22 files, which is how docs once ended up claiming
0.7.11 while the crate was already 0.7.12. Markdown on GitHub has no variable
substitution, so the only way to templatise this is to stamp at commit time —
which is what `--write` does.

Exit code 0 = everything agrees, 1 = something drifted (or was rewritten).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (path, regex with ONE capturing group around the version, human label).
# Each regex must match exactly the occurrences that carry the version — a group
# that is too greedy would rewrite unrelated strings, so they are anchored on the
# surrounding key rather than on the bare number.
DEV_TARGETS: list[tuple[str, str, str]] = [
    ("qeli/Cargo.lock", r'(?s)(?<=\[\[package\]\]\nname = "qeli"\nversion = ")([^"]+)', "crate lock"),
    ("qeli-android/app/build.gradle.kts", r'versionName\s*=\s*"([^"]+)"', "Android versionName"),
    ("qeli-mac/Info.plist.in", r"(?<=<key>CFBundleVersion</key>\n    <string>)([^<]+)", "macOS CFBundleVersion"),
    ("qeli-mac/Info.plist.in", r"(?<=<key>CFBundleShortVersionString</key>\n    <string>)([^<]+)", "macOS CFBundleShortVersionString"),
    ("qeli-mac/QeliMac/QeliMac.csproj", r"<Version>([^<]+)</Version>", "macOS csproj"),
    ("qeli-win/QeliWin/QeliWin.csproj", r"<Version>([^<]+)</Version>", "Windows csproj"),
    ("qeli-shared/QeliShared/QeliShared.csproj", r"<Version>([^<]+)</Version>", "shared csproj"),
    # iOS keeps both numbers in project.yml; the plists only reference the variables.
    ("qeli-ios/project.yml", r"MARKETING_VERSION:\s*(\S+)", "iOS MARKETING_VERSION"),
    ("qeli-openwrt/Makefile", r"PKG_VERSION:=(\S+)", "OpenWrt package"),
    ("qeli-openwrt/luci-app-qeli/Makefile", r"PKG_VERSION:=(\S+)", "LuCI package"),
    ("qeli/debian/control", r"^Version: (\S+)", "deb control"),
    ("docs/ru/README.md", r"Rust 2021, версия (\S+) \(бета\)", "overview README (ru)"),
    ("docs/eng/README.md", r"Rust 2021, version (\S+) \(beta\)", "overview README (eng)"),
]

# The "these docs describe X" banner. Ten documents, two wordings.
BANNER_DOCS = ("CONFIG", "GETTING-STARTED", "PANEL", "TROUBLESHOOTING", "OPERATIONS")
BANNER_RE = {
    "ru": r"\*\*Документация описывает (\S+)\*\*",
    "eng": r"\*\*These docs describe (\S+)\*\*",
}

problems: list[str] = []


def released_version() -> str | None:
    """Newest `v*` tag, without the `v`. Tags are what a release actually is."""
    out = subprocess.run(
        ["git", "tag", "--sort=-v:refname", "--list", "v*"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    tags = [t.strip() for t in out.stdout.splitlines() if t.strip()]
    return tags[0].lstrip("v") if tags else None


def dev_version() -> str | None:
    m = re.search(
        r'^version\s*=\s*"([^"]+)"',
        (ROOT / "qeli" / "Cargo.toml").read_text(encoding="utf-8"),
        re.M,
    )
    return m.group(1) if m else None


def apply(targets: list[tuple[str, str, str]], want: str, write: bool) -> None:
    """Check (or rewrite) every occurrence the regexes select."""
    for rel, pattern, label in targets:
        path = ROOT / rel
        if not path.exists():
            problems.append(f"{rel}: missing — cannot carry the version ({label})")
            continue
        # Normalise line endings for matching (patterns embed plain \n), but remember
        # what the file actually uses so --write can put them back byte-for-byte.
        raw = path.read_bytes()
        newline = "\r\n" if b"\r\n" in raw else "\n"
        text = raw.decode("utf-8").replace("\r\n", "\n")
        found = re.findall(pattern, text, re.M)
        if not found:
            # A silently unmatched pattern is worse than a mismatch: it would let a
            # file drift forever while the script reports success.
            problems.append(f"{rel}: pattern for {label} matched nothing — it needs updating")
            continue
        stale = [v for v in found if v != want]
        if not stale:
            continue
        if write:
            # Replace ONLY the captured group, keeping the syntax around it. A plain
            # re.sub(pattern, want, ...) substitutes the whole match, which turns
            # `versionName = "0.7.13"` into a bare `0.7.13` and breaks the build file.
            def swap(m: re.Match[str]) -> str:
                whole, base = m.group(0), m.start()
                return whole[: m.start(1) - base] + want + whole[m.end(1) - base :]

            new = re.sub(pattern, swap, text, flags=re.M)
            with open(path, "w", encoding="utf-8", newline=newline) as fh:
                fh.write(new)
            print(f"  stamped {want:>8}  {rel}  ({label}, was {', '.join(sorted(set(stale)))})")
        else:
            problems.append(f"{rel}: {label} is {', '.join(sorted(set(stale)))}, expected {want}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="rewrite the files instead of only checking")
    args = ap.parse_args()

    dev = dev_version()
    rel = released_version()
    if not dev:
        print("cannot read the version from qeli/Cargo.toml", file=sys.stderr)
        return 1
    if not rel:
        print("no v* git tag found — cannot tell which version is released", file=sys.stderr)
        return 1
    print(f"development version {dev} (qeli/Cargo.toml) · released version {rel} (newest v* tag)")
    if args.write:
        print("writing:")

    apply(DEV_TARGETS, dev, args.write)

    # Build numbers are monotonic counters, not a function of the version, so they are
    # not derived from Cargo.toml. But iOS and Android have always been released as a
    # pair (both 715 at 0.7.12), and iOS is the one that gets forgotten because nothing
    # ships from it — so Android's counter is the source and iOS must match it.
    gradle = ROOT / "qeli-android" / "app" / "build.gradle.kts"
    if gradle.exists():
        vc = re.search(r"versionCode\s*=\s*(\d+)", gradle.read_text(encoding="utf-8"))
        if vc:
            apply(
                [("qeli-ios/project.yml", r"CURRENT_PROJECT_VERSION:\s*(\S+)", "iOS build number")],
                vc.group(1),
                args.write,
            )
    banners = [
        (f"docs/{lang}/{doc}.md", BANNER_RE[lang], f"docs banner ({lang})")
        for lang in ("ru", "eng")
        for doc in BANNER_DOCS
    ]
    apply(banners, rel, args.write)

    if problems:
        print(f"\n{len(problems)} problem(s):\n")
        for p in problems:
            print("  " + p)
        print("\nRun `python3 scripts/sync_version.py --write` to stamp them.")
        return 1
    print("OK — every version string agrees with its source of truth.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
