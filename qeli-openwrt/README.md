# qeli for OpenWrt (client)

> **Status: tested on real OpenWrt hardware.** The full-IPv6 line uses public version 0.8.0;
> there is no public 0.7.17 release. The client and gateway path have been verified on a
> real router and work. Use artifacts attached to the exact release tag, and still verify
> the target architecture, TUN support and firewall/interface names for your model.

A native **OpenWrt** package for the qeli **client**, so an OpenWrt router can dial
out to a qeli server and route its LAN through the tunnel — managed the OpenWrt way
(procd + UCI + firewall + LuCI), not by hand-editing files.

## Design — what's new and what's reused

The client logic is **not reimplemented**. OpenWrt runs the exact same
`qeli client` binary the Linux/Keenetic clients use, so it **inherits every
core-side fix automatically**:

| Fix (release) | Why it matters on a router |
|---|---|
| Dual-family kill-switch on **iptables**+ip6tables, verified with `-C` | In full-tunnel gateway mode the rendered config also guards FORWARD, so LAN traffic cannot fall back to WAN during reconnect; both TUN directions remain allowed. |
| **UDP handshake + encrypted data-record fragmentation** | Routers on an **LTE / 4G / CGNAT WAN** may drop IP fragments — the PQ handshake and oversized encrypted records are fragmented below the outer budget in the application layer. |
| Native inner IPv4/IPv6/dual NetworkPlan | UCI/LuCI expose `ipv6=auto|required|off` and symmetric `allow_ipv4_leak` / `allow_ipv6_leak`; the firewall zone applies NAT44/NAT66. |
| UDP idle/download **liveness** (0.7.4) | No false reconnects on an idle or download-only router tunnel. |
| `gateway` / `dns` INI keys, `bind_static`/H-1, persistent **device-id** + TOFU `known_hosts` | Router runs headless; these are exactly the keys the init script writes. |

So this package = **integration only**: packaging, a procd service, a UCI schema, a
firewall zone, and a LuCI page. The GUI-only fixes (Android IPv4-fallback at
`establish()`, the C# INI parity, low-res layout) are desktop/phone concerns and do
not apply to the headless router client.

## Layout

```
qeli-openwrt/
├── Makefile                         # OpenWrt feed package "qeli" (binary + service + UCI + fw)
├── files/
│   ├── qeli.init                    # /etc/init.d/qeli — procd service (UCI → INI → qeli client)
│   ├── qeli.config                  # /etc/config/qeli — UCI defaults
│   └── qeli.firewall.uci-defaults   # first-install: create the `qeli` firewall zone (fw4-native)
├── luci-app-qeli/                   # LuCI web UI (modern client-side JS)
│   ├── Makefile
│   ├── root/usr/share/luci/menu.d/luci-app-qeli.json
│   ├── root/usr/share/rpcd/acl.d/luci-app-qeli.json
│   └── htdocs/luci-static/resources/view/qeli/config.js
└── build/build_openwrt.py           # cross-compile the client-only binary per arch (zig), for the .ipk
```

## How it runs

1. **Binary**: the client-only target `qeli-client` (`--no-default-features --features
   client-bin`, no `ring` → works on mips), installed to `/usr/bin/qeli-client` and run
   directly as `qeli-client --config <file>` (no subcommand; the default `qeli` bin with
   subcommands needs the server+client features).
2. **Config and secrets**: non-secret settings live in **UCI** (`/etc/config/qeli`) or LuCI.
   Password and `obfs_key` are never UCI options: they are 0600 files below
   `/var/run/qeli/` (tmpfs). On start, `qeli.init` renders a 0600 flat-INI in the same
   tmpfs and passes the password through `password_file`. Secrets therefore must be
   provisioned again after every reboot, either in LuCI or from a trusted boot-time secret
   provider. On first upgrade, legacy UCI secrets are moved to tmpfs and deleted from the
   live UCI config; rotate them because flash wear levelling may retain older blocks.
3. **Persistence**: `QELI_DEVICE_ID_FILE` + `QELI_KNOWN_HOSTS` live in `/etc/qeli/`
   (persistent overlay; `/tmp` and `/var` are tmpfs and reset on reboot) so the server
   doesn't see a "new device" every boot and the TOFU pin survives.
4. **Gateway (full-tunnel for the LAN)**: handled by an **OpenWrt firewall zone**
   (`config zone … name 'qeli' … masq '1'` + a `lan → qeli` forwarding), created once by
   `qeli.firewall.uci-defaults`. This is fw4-native and survives `/etc/init.d/firewall reload`
   — unlike raw iptables, which fw4 would flush. The qeli kill-switch is a separate layer;
   when both `gateway=1` and `kill_switch=1`, the renderer enables no-NAT core forwarding
   ownership so the switch protects forwarded LAN traffic as well as router-local OUTPUT.

## Quick start (on the router)

```sh
opkg install qeli luci-app-qeli      # from the feed, or `opkg install ./qeli_*.ipk`
uci set qeli.main.server='vpn.example.com:443'
uci set qeli.main.user='router1'
# Read from stdin: the secret does not enter UCI, process argv or persistent flash.
printf '%s\n' 'PASSWORD' | /etc/init.d/qeli set_secret pass
uci set qeli.main.key='<server identity hex from: qeli show-identity>'
# H-1 MUST match the server, and the server default is ON. The shipped UCI default is
# '0' because the shipped key is the all-zero TOFU placeholder — the moment you set a
# real key above, flip this too, or the handshake completes and then every record fails
# to decrypt ("Connection error: decryption failed"), because the two sides derive keys
# from different salts. Nothing is negotiated on the wire.
uci set qeli.main.bind_static='1'
uci set qeli.main.mode='fake-tls'; uci set qeli.main.sni='www.cloudflare.com'
uci set qeli.main.gateway='1'       # route the whole LAN through the tunnel
uci set qeli.main.enabled='1'; uci commit qeli
/etc/init.d/qeli enable; /etc/init.d/qeli start
logread -e qeli                      # look for "Auth OK"
```

Or use **LuCI → Services → qeli VPN**. The password fields are write-only and show only
whether a volatile secret exists; an empty field leaves the current value unchanged.

## Notes / compatibility

- Wire mode by CPU: on low-end **mipsel** prefer `fake-tls` / `obfs` / `plain` (ChaCha20);
  `reality-tls` (double AEAD) is sane only on ARM (aarch64) routers.
- `dns`: resolver **mode**, default `off` (leave the router's dnsmasq/resolver alone).
  Set it to `tunnel` to use the server-pushed resolver, and optionally add IPv4/IPv6
  literals through the repeatable `dns_servers` UCI/LuCI field. Older installations that
  stored a comma list directly in `dns` are migrated by the init renderer at startup.
- The `.ipk` ships per-arch; `build/build_openwrt.py` cross-builds the binary (zig), the
  OpenWrt `Makefile` also builds it from source via the SDK rust feed.
- Real-device validation has passed. OpenWrt models and releases can still differ in
  interface naming, flash layout and fw4 integration, so verify those platform details
  when deploying to a new router model or firmware line.

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
atomic artifact transfer does not qualify full ABI or real router runtime. Current adapter
fixtures do not execute an ucode interpreter/rpcd.


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
