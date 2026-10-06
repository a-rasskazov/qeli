# Installing the qeli client on OpenWrt

> **Tested integration.** The full-IPv6 line uses public version 0.8.0; there is no
> public 0.7.17 release. The client has been verified on real OpenWrt hardware and works.
> Install an artifact from the exact release tag and verify the target architecture,
> TUN support and firewall/interface names for your router.

Two ways to install: **A) prebuilt binary** (fastest — hand-install + opkg deps) or
**B) from source** (proper feed package + `.ipk`). Both end with the same UCI/LuCI
config and a procd service.

---

## 0. Prerequisites (on the router)

```sh
opkg update
opkg install kmod-tun ip-full iptables ip6tables ca-bundle
ls -l /dev/net/tun        # must exist (kmod-tun provides it)
```

- **Disk space:** the client binary is ~2.5–8 MB depending on arch. On 8/16 MB-flash
  devices use **extroot** or install to a USB/`/opt` overlay.
- **Wire mode by CPU:** low-end **mipsel** (MT7621/7628) → `fake-tls` / `obfs` / `plain`
  (ChaCha20). `reality-tls` (double AEAD) is sane only on **aarch64** routers.

---

## A. Prebuilt binary (quick)

1. Pick your arch (`opkg print-architecture` / `uname -m`) and download the matching
   prebuilt `qeli-client-openwrt-<arch>` binary from **GitHub Releases** (aarch64 /
   x86_64 / mipsel / armv7, static musl), then copy it to the router:

   > `build/build_openwrt.py` is a **maintainer-internal** helper (it cross-builds on a
   > private lab host over SSH) — don't run it yourself; use the release binary here, or
   > build from source via the SDK (section B).
   >
   > This step used to `scp` out of `qeli-openwrt/dist/`, which is a **local build output
   > directory and is gitignored** — so it does not exist in a fresh checkout at all, and in
   > a maintainer's tree it holds whatever was built last (it was still carrying 0.7.13
   > binaries during 0.7.14). Take the binary from the Release you downloaded. Maintainers:
   > the published set for a version lives in `release/dist/v<version>/`, and that path is
   > version-explicit precisely so it cannot go quietly stale. (Audit 2026-08-01, §7.)

   ```sh
   # from your PC, from wherever you saved the download:
   scp qeli-client-openwrt-aarch64 root@192.168.1.1:/usr/bin/qeli-client
   # and the integration files, from a checkout of this repo:
   scp qeli-openwrt/files/qeli.init   root@192.168.1.1:/etc/init.d/qeli
   scp qeli-openwrt/files/qeli.config root@192.168.1.1:/etc/config/qeli
   scp qeli-openwrt/files/qeli.firewall.uci-defaults root@192.168.1.1:/etc/uci-defaults/99-qeli-firewall
   ```

2. On the router, fix perms and run the firewall-zone defaults once:

   ```sh
   chmod 755 /usr/bin/qeli-client /etc/init.d/qeli /etc/uci-defaults/99-qeli-firewall
   chmod 600 /etc/config/qeli
   sh /etc/uci-defaults/99-qeli-firewall      # creates the `qeli` fw zone (or runs on next boot)
   ```

3. Go to **§3 Configure**.

---

## B. From source (feed package + .ipk)

On a build host with the **OpenWrt SDK** for your target (23.05 recommended):

```sh
# 1. Add the rust + luci feeds (rust is needed to compile the client).
./scripts/feeds update -a && ./scripts/feeds install -a

# 2. Drop the package into the tree (symlink or copy this dir).
cp -r /path/to/qeli-openwrt            package/qeli
cp -r /path/to/qeli-openwrt/luci-app-qeli package/luci-app-qeli

# 3. Select and build.
make menuconfig        # Network → VPN → <*> qeli ;  LuCI → Applications → luci-app-qeli
make package/qeli/compile V=s
make package/luci-app-qeli/compile V=s

# 4. The .ipk lands in bin/packages/<arch>/…  — install on the router:
opkg install ./qeli_<ver>-1_<arch>.ipk ./luci-app-qeli_<ver>-1_all.ipk
```

> **Where's the Rust crate / Cargo.toml?** You don't place it — the package fetches it.
> `package/qeli/Makefile` clones the whole repo (`PKG_SOURCE_PROTO:=git`) and the Cargo
> project lives in the repo's `qeli/` subdir (`qeli/Cargo.toml`); the build cd's into it
> automatically. So `package/qeli/` only needs the `Makefile` + `files/` — the crate comes
> from the git source, not from your local copy. (To build a LOCAL/modified crate instead,
> point `PKG_SOURCE_URL`/`PKG_SOURCE_VERSION` at your fork, or use `PKG_SOURCE_PROTO` with a
> local mirror.)

`opkg install` pulls `kmod-tun`/`ip-full`/`iptables` automatically and runs the
firewall-zone uci-default.

---

## 3. Configure

Get the connection bits from the server's link and the key from the server:

```sh
# on the SERVER:
qeli add-client router1 --link --host vpn.example.com   # prints a qeli:// link
qeli show-identity                                       # prints the public key to pin
```

Set non-secret options via **UCI** (or LuCI → Services → qeli VPN). Credentials are
write-only per-boot tmpfs secrets and are deliberately never committed to UCI/flash:

```sh
uci set qeli.main.server='vpn.example.com:443'
uci set qeli.main.user='router1'
printf '%s\n' '<password>' | /etc/init.d/qeli set_secret pass
uci set qeli.main.key='<64-hex server identity>'   # zero/empty = TOFU
uci set qeli.main.bind_static='1'                  # keep on with a real key (drop to 0 for TOFU)
uci set qeli.main.mode='fake-tls'
uci set qeli.main.sni='www.cloudflare.com'
uci set qeli.main.gateway='1'                      # 1 = route the WHOLE LAN through the tunnel
uci set qeli.main.dns='off'                        # leave the router's resolver alone
uci set qeli.main.enabled='1'
uci commit qeli
```

`gateway = 1` turns the router into a **full-tunnel gateway**: the firewall zone `qeli`
NATs the LAN out the tunnel. `gateway = 0` is split-tunnel (only the tunnel subnet +
pushed routes).

---

## 4. Run

```sh
/etc/init.d/qeli enable        # start on boot
/etc/init.d/qeli start
/etc/init.d/qeli status

logread -e qeli                # watch for "Auth OK"
ip addr show qeli0             # the tun should have an address
ip route                       # full-tunnel: 0.0.0.0/1 + 128.0.0.0/1 via qeli0
```

Verify egress from a LAN client (full-tunnel): its public IP should now be the server's.

```sh
# from a LAN PC:
curl -s https://api.ipify.org ; echo      # == server IP when gateway=1
```

---

## 5. Troubleshooting

| Symptom | Check |
|---|---|
| `/dev/net/tun missing` | `opkg install kmod-tun` |
| Stuck handshake on **LTE/4G WAN** | already mitigated (0.7.4 UDP fragmentation); confirm `proto`/`mode` match the server |
| `Auth` fails | `user`/`pass`/`key` mismatch; check `qeli show-identity` on the server |
| LAN has tunnel but no internet | firewall zone — `uci show firewall | grep qeli` should show `name 'qeli'`, `masq '1'`, and a `lan → qeli` forwarding; `fw4 reload` |
| Reconnect loops | check time sync (`ntpd`); the server log for the disconnect reason |
| Router DNS broken | set `dns='off'` so the client doesn't touch `resolv.conf` (dnsmasq owns it) |

Logs: `logread -e qeli`. Raise detail with `uci set qeli.main.log_level='debug'; /etc/init.d/qeli restart`.

`log_time_format` controls the timestamp the client itself prints (`none` |
`datetime` | `rfc3339` | `time` | `epoch`). It ships as `none` on purpose: procd
sends stderr to syslog, which already stamps each line, so any other value gives
you two timestamps per line in `logread`. Set `rfc3339` only if you forward these
logs off the router and need UTC that lines up with the server's.

## Configuration and service failure handling (development0.8.2)

Save & Apply edited fields before using the status controls. Connect/Disconnect
await UCI commit/confirmation before changing service state; Restart joins the same
queue in this page. Apply can include other staged UCI packages. A service error
is reported; it does not undo already committed autostart intent.

The init renderer publishes a complete0600 tmpfs INI by atomic rename. A normal
render failure keeps the previous file; MTU must be0(auto) or576..16602. A failed
firewall mutation/commit/reload stops startup and leaves a root-only tmpfs pending
marker so the next start retries; a successful no-op does not reload firewall.
Partial UCI changes are not rolled back automatically. After correcting the error,
restart qeli. This behavior is covered by shell/JavaScript fixtures; the historical
public0.8.0 hardware result above does not qualify these development changes on a
real router. See [Q31 audit evidence](../docs/eng/reports/AUDIT-Q31-OPENWRT-CONTROLS.md).

Development status polling reads init-visible UCI through the scoped service_status
RPC; it preserves staged form edits and displays unknown when the read fails.
Maintainer cross-build helpers reject target typos and setup/transfer failures;
Every run uploads this checkout into a fresh private directory. SHA256/ELF-checked
atomic artifact transfer does not qualify full ABI or real router runtime. Development tests execute pinned OpenWrt24.10/25.12 ucode/fs on a Linux host;
The native24.10 rpcd/ubus/UCI/session ACL path is tested in a private Linux chroot;
procd, SDK installation, HTTP serving and firmware runtime remain unqualified.


The first-install firewall defaults use named package-owned sections. An existing
qeli zone is preserved. Failed UCI creation/commit or live firewall reload returns
failure and keeps /var/run/qeli/firewall-install-pending. Qeli start is blocked
while it exists: fix the reported error, rerun
`sh /etc/uci-defaults/99-qeli-firewall` successfully, then start qeli. Do not remove
the marker as a substitute for repair. Retry completes those sections without
duplicating devices/forwarding; this does not roll back partial UCI changes.
The marker is tmpfs state, not a persistent reboot recovery guarantee.

Each helper run allocates a private0700 directory under
/var/tmp/qeli-router-keenetic-XXXXXX or /var/tmp/qeli-router-openwrt-XXXXXX, uploads
the current checkout and uses its own target directory. --sync remains a
compatibility option; upload also happens without it. The old /opt/qeli-src and
shared Cargo.toml backup are no longer used. Manifest restriction to rlib affects
only that private copy. Upload/close failure leaves .router-sync-incomplete and
stops the run; retry creates a new checkout. Runs retain their directories for
diagnosis; after the run finishes, review and remove only its printed owned path.
They are not automatically removed. Qeli compilation uses --locked, --jobs1 and no incremental
cache. Separate runs may still share installed toolchains and Cargo download cache.

Before atomic publication, the same SHA256-bound snapshot must be a little-endian
ELF executable of the requested class/machine, with a file-backed executable entry,
no PT_INTERP or DT_NEEDED; ARMv7 must declare EABI5 hard-float. Failure preserves
the previous local binary, including when its hash would match the remote cache.
These checks do not prove musl identity, CPU ISA, full MIPS float ABI, reproducible
builds or firmware runtime. The shared router policy now selects Rust1.97.0, nightly-2026-06-10 for MIPS,
Zig0.13.0 and cargo-zigbuild0.23.0. Wrong identities fail; missing named components
are installed without changing the default Rust. Encoded/ambient Rust flags cannot
override the Qeli recipe; explicit MIPS soft-float is retained, compiler overrides
cleared and wrappers disabled. Global Cargo config/PATH/shared installations and
upload races remain outside a hermetic/reproducible-build guarantee. This policy
applies to maintainer helpers; the SDK retains its own Rust feed/toolchain. See [Q31](../docs/eng/reports/AUDIT-Q31-OPENWRT-CONTROLS.md).

The SDK package requires Cargo.lock before compilation and checks the client-only
graph with cargo metadata --locked before cargo install --locked --jobs1.
Missing/outdated lockfiles fail before installation. Keep the source SHA and
PKG_MIRROR_HASH release-cut steps; this check does not validate a real SDK package.

Secret deletion reports filesystem failure through both CLI and LuCI; an absent
file is a successful no-op. Removing the stored file does not stop the current
VPN or erase credentials already loaded by it; restart applies changes.
Legacy UCI migration retains /var/run/qeli/secret-migration-pending through failed
commit and retries on the next start even if staged options are already absent.
After fixing the storage/UCI error, retry start; this does not guarantee reboot
transactions or erase old flash blocks. Rotate migrated credentials.
Failed UCI loads or multiple qeli firewall zones reject start preparation. Standard
rc.common hooks return preparation/cleanup failures to the service caller; failed
stop cleanup blocks the next start within the same restart/reload call. Daemon
acceptance, join and connectivity are separate from this command result.

The development init renderer quotes string values and escapes double quotes
according to the shared INI parser. Literal quotes, backslashes and significant
edge whitespace in usernames or volatile obfs keys survive rendering. Enter raw
values through UCI/LuCI or the stdin secret command; do not add INI escaping there.
ASCII control characters remain rejected for secrets and stripped from ordinary
UCI values. This formatting rule does not make an invalid endpoint, logging mode
or other setting valid; the client still validates the resulting configuration.

The development secret RPC uses fixed init commands and passes credentials only
through stdin, compatible with the tested OpenWrt24.10/25.12 ucode revisions.
Secrets must contain 1..4096 UTF-8 bytes and no ASCII C0/DEL controls; the limit
counts bytes, not characters. Enter literal values without shell/INI escaping
into LuCI. A secret status of configured requires a readable regular file of
that size in the real runtime directory. Empty/oversize files, directories,
FIFOs and symlinks do not count. Linked runtime directories and non-regular or
linked secret destinations reject writes. Clearing secrets also rejects a linked
runtime directory to avoid deleting outside files; an absent directory is a no-op. Correct the unexpected filesystem
object before retrying; do not treat a failed write as an applied credential.
Host tests cover real ucode/fs and native24.10 rpcd/ubus/UCI/session ACL in a
private chroot. They do not confirm procd, SDK installation, HTTP serving or
router firmware behavior. Administrator path replacement
between checks and publication is outside this guarantee.

The LuCI package explicitly requires luci-base, rpcd-mod-ucode and ucode-mod-fs
along with qeli. An installation missing fs cannot register the Qeli RPC object.
Both secret fields validate ASCII controls, the UTF-8 byte limit and Unicode
before sending RPC. NUL is unsupported by ubus C-string transport: external RPC
producers must reject it before serialization, as it may otherwise truncate a
value before the Qeli handler receives it. Use valid text without control bytes.
LuCI session staging remains separate from init-visible configuration until
commit; administrative global CLI UCI staging is a different context and can be
init-visible before commit. Save & Apply the form before service controls.
