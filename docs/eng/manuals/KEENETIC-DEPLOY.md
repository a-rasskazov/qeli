# qeli-client on Keenetic — step-by-step deployment

> **Benchmark scope:** any Reality speed or double-framing estimate in this document comes from
> the legacy carrier through 0.7.16. The current genuine H2 carrier needs a separate router benchmark.

Deploying the qeli VPN client on a Keenetic router (Entware) as a gateway for the whole
LAN. The architecture and rationale of the port — [KEENETIC-PORT.md](../reference/KEENETIC-PORT.md).
The bundle files — in `release/keenetic/`.

> 🛜 **On OpenWrt?** The native OpenWrt client (procd service + UCI config + a LuCI page)
> is available and verified on real hardware. It reuses the exact same client core as
> here, so it inherits every fix automatically — the iptables kill-switch and the
> UDP-handshake fragmentation that fixes UDP on an LTE/CGNAT WAN.

> ✅ The client has been tested on a live Keenetic and works. The bundle scripts remain
> **templates**: the commands are universal, but interface names and interaction with the
> KeeneticOS firewall depend on the model and firmware version — verify them on site.

---

## Prerequisites

- **Entware** is installed on the router (the `opkg` package manager, the `/opt`
  directory).
- **SSH** is enabled and you have shell access to the router.
- The **VPN** component is enabled in KeeneticOS (any of WireGuard/OpenVPN/IPsec) — it
  ensures `/dev/net/tun` is present. Added in the web UI: *Management → General settings →
  Change the component set*.
- There's a working **qeli server** with a profile and a client provisioned for the
  router.

---

## Step 0. Router reconnaissance (over SSH to the router)

```sh
opkg print-architecture | grep -E 'aarch64|mipsel|mips'   # the package arch
cat /proc/cpuinfo | grep -E 'cpu model|FPU|system type'   # CPU/FPU
ls -l /dev/net/tun                                         # must exist
df -h /opt                                                 # space (need ~5-10 MB)
```

- `mipsel-…` → the binary `qeli-client-mipsel` (MT7621/7628, etc.).
- `aarch64-…` → the binary `qeli-client-aarch64` (new ARM models).
- No `/dev/net/tun` → go back to the prerequisites and enable the VPN component.

---

## Step 1. Build the binaries (on the dev/lab, not on the router)

```sh
python scripts/build_keenetic.py --sync
# → release/keenetic/qeli-client-keenetic-aarch64   (static ARM aarch64)
# → release/keenetic/qeli-client-keenetic-mipsel    (static-pie MIPS32r2)
```

You can build only the needed arch: `python scripts/build_keenetic.py --sync mipsel`.

The helper is maintainer-internal; --sync uploads this checkout before building.
Without it, the existing remote source is used. Target typos fail before SSH;
setup/transfer errors return failure. Downloaded bytes are SHA256-checked and
atomically replace the previous file. This does not qualify a fresh source snapshot,
reproducibility or real router runtime; see [Q31](../reports/AUDIT-Q31-OPENWRT-CONTROLS.md).

The maintainer --sync now replaces managed src/.cargo, manifests and lockfile,
including deleted modules and current Cargo config, and preserves target cache.
An incomplete upload/close keeps .router-sync-incomplete in the remote source
root. Builds with or without --sync reject that marker; rerun --sync successfully
to repair. Replacement is not atomic or locked, and unmarked cached source is
still reused without --sync. Full provenance and reproducibility remain unqualified.


---

## Step 2. Get the client credentials from the server (on the qeli server)

```sh
# Provision a client and get a qeli:// link right away (and the password — printed ONCE):
qeli add-client router1 --link --host <server_public_address>

# The server public key for pinning (anti-MITM):
qeli show-identity
```

From the link/output you'll need: `server` (host:port), `proto` (tcp/udp), `user`, `pass`,
`key` (the server pubkey), `mode` (fake-tls/obfs/plain/…), `sni`.

---

## Step 3. Copy the bundle to the router (from the dev)

```sh
scp -r release/keenetic <user>@<router-ip>:/opt/tmp/keenetic
# <user> — the router account with access to /opt (usually admin/root). An alternative is USB.
```

---

## Step 4. Installation (on the router)

```sh
cd /opt/tmp/keenetic
sh install-keenetic.sh
```

The script: detects the arch → places the right binary in `/opt/bin/qeli-client`; installs
`ip-full` and `iptables` (Keenetic's busybox `ip` is stripped — no `tuntap`); checks
`/dev/net/tun`; lays out `S99qeli` and a config stub.

Development0.8.2 installer consumes the canonical qeli-client-keenetic-aarch64/mipsel
artifacts; old qeli-client-aarch64/mipsel names remain a fallback. Required package
errors stop publication. Existing INI content is preserved and restricted to0600.
Copies are prepared first and each file is renamed atomically; the bundle is not
an atomic transaction. Correct an installation error and retry; no automatic VPN
restart occurs. Optional ip6tables failure requires checking IPv6 support.
[Q31 fixture evidence](../reports/AUDIT-Q31-OPENWRT-CONTROLS.md) does not qualify real
opkg, ELF/ABI, power-loss or firmware runtime.

---

## Step 5. Fill in the config (on the router)

```sh
vi /opt/etc/qeli/client.conf
```

Substitute the values from Step 2. For a gateway router two keys matter:

```ini
[qeli]
server = vpn.example.com:443
proto  = tcp
user   = router1
pass   = <password>
# Pin the server's static key (anti-MITM). Empty / all-zero = TOFU.
key    = <server pubkey from show-identity>
# H-1 (since 0.7.1, ON by default): binds session keys to the server's static
# identity. REQUIRES a real key. With a TOFU key (zeros) set false; with a real
# key leave the default (you may drop the line). Safest: real key + bind_static=true.
bind_static = false
# Wire mode — must match the server. MIPS: fake-tls | obfs | plain (ChaCha20).
# reality-tls on mipsel is very slow (double AEAD) — ARM only.
mode   = fake-tls
# SNI for fake-tls (front domain). Not needed for obfs.
sni    = www.cloudflare.com
# ONLY for mode = reality-tls (short_id required since 0.7.1)
# reality_sid = <hex>

# ── Router / gateway ─────────────────────────────────────────────────────────
# full-tunnel: all LAN traffic into the tunnel (+ NAT in S99qeli)
gateway = true
# DON'T touch the router's resolver (the firmware owns it)
dns     = off
# kill_switch: leak-blocking via iptables (now works on Keenetic, which ships
# iptables). On a gateway the firewall is handled by S99qeli, so you can leave it off. Default off.
# kill_switch = false

[logging]
level = info
file  = /opt/var/log/qeli-client.log
# timestamp on each line: datetime (default) | rfc3339 | time | epoch | none.
# Here the log goes to its own file rather than syslog, so the timestamp is
# needed; rfc3339 is handy if you later correlate this log with the server's.
time_format = datetime
```

**H-1 / `bind_static` (important on 0.7.1):** by default the client binds the session
to the server's pinned static key. Two working router options:
- **Secure (recommended):** set a real `key` (from `qeli show-identity`) and leave
  `bind_static` at the default (on). The TOFU pin is stored in `QELI_KNOWN_HOSTS`
  (`S99qeli` points it at `/opt/etc/qeli/known_hosts` — survives reboot, unlike `/var`).
- **TOFU (simpler):** `key` = zeros and `bind_static = false` — trust on first use.

---

## Step 6. Check the interfaces for NAT (on the router)

```sh
ip a            # find the LAN bridge (usually br0) and confirm the tun will be vpn0
```

If the LAN bridge isn't `br0` or the tun isn't `vpn0` — fix the variables at the top of
`S99qeli`:

```sh
vi /opt/etc/init.d/S99qeli      # TUN=…, LAN_IF=…, GATEWAY=yes
```

---

## Step 7. Start

```sh
/opt/etc/init.d/S99qeli start
tail -f /opt/var/log/qeli-client.log
```

Wait for the line `Auth OK, assigned IP: 10.x.x.x` — that's a successful connection to the
server. Entware starts an init script with the `S` prefix **automatically when the router
boots**.

---

## Step 8. Check the tunnel

On the router:

```sh
ip a show vpn0                                  # the tun has an address 10.x.x.x
ip route | grep -E 'default|vpn0'               # with gateway=true — default via vpn0
iptables -t nat -L POSTROUTING -n | grep MASQUERADE   # NAT on vpn0 is set
curl -s https://ifconfig.me ; echo             # the external IP = the VPN server address
```

From any LAN client (a phone/PC behind the router):

```sh
# the external IP should become the VPN server address; DNS and sites open
curl -s https://ifconfig.me ; echo
```

---

## Selective mode (only part of the traffic via the VPN)

Instead of full-tunnel (`gateway=true`) you can route only the needed addresses:
`gateway = false` in the config + `ipset` + `iptables` + DNS overrides on the router's
dnsmasq (an approach like the `kvas` / `antizapret` projects for Keenetic). This is more
flexible and doesn't cut the speed on non-VPN traffic, but the setup is manual and outside
this bundle.

---

## Diagnostics

| Symptom | Cause / what to do |
|---|---|
| `no /dev/net/tun` at start | Enable the VPN component in KeeneticOS (prerequisites) |
| `ip: ... tuntap` doesn't work | `opkg install ip-full` (busybox `ip` is stripped) |
| No `Auth OK`, `SERVER KEY MISMATCH` | A wrong `key` — check against `qeli show-identity` on the server |
| No `Auth OK`, error about `bind_static`/all-zero TOFU | H-1 (0.7.1) is ON by default: set a real `key` OR `bind_static = false` for TOFU |
| No `Auth OK`, `auth failed` | Wrong `user`/`pass`, or `mode`/`sni` don't match the server profile |
| `kill-switch: iptables is not installed` | Ensure `iptables` is in PATH (Keenetic ships it); otherwise set `kill_switch = false` |
| LAN without internet, the router with internet | Check `ip_forward`, `MASQUERADE`, the correct `LAN_IF` name in `S99qeli` |
| After a reboot: "new device" / repeated TOFU | `QELI_DEVICE_ID_FILE` and `QELI_KNOWN_HOSTS` must be on `/opt` (in `S99qeli` they are; `/var` is tmpfs) |
| Very slow (mipsel) | The CPU ceiling without AES-NI; set `mode = obfs`/`plain`, not `reality-tls` |
| The tunnel breaks | Auto-reconnect is on; check `/opt/var/log/qeli-client.log` |

---

## Update / removal

```sh
# update the binary: stop, replace, start
/opt/etc/init.d/S99qeli stop
install -m755 qeli-client-<arch> /opt/bin/qeli-client
/opt/etc/init.d/S99qeli start

# remove completely
/opt/etc/init.d/S99qeli stop
rm -f /opt/etc/init.d/S99qeli /opt/bin/qeli-client
rm -rf /opt/etc/qeli /opt/var/log/qeli-client.log
```

## Legacy gateway recovery during template upgrades

Development0.8.2 templates use tagged qeli-keenetic-legacy firewall rules and a
version2 forwarding checkpoint with saved interfaces and touched families. Failed
cleanup retains the checkpoint and blocks start/restart. Correct the cause and
retry; recovery uses the saved interfaces even after template mode changes. The
legacy path requires the iptables comment extension. Actual router compatibility
is unqualified; the audit used isolated command/file models.

Before replacing an active legacy template, stop it with its previous script and
inspect the old rules and forwarding values. An old checkpoint without version2
requires manual ownership review and recovery; the new script preserves it and
refuses automatic cleanup. Keep its original values until recovery is verified.
Do not delete it to bypass the failure. Matching untagged administrator rules are
not automatically removed. See [Q31 evidence and remaining limits](../reports/AUDIT-Q31-OPENWRT-CONTROLS.md).

## Process lifecycle and PID records

Development0.8.2 init templates store `PID start_ticks` in the0600 PID file and
check Linux proc start time/executable before signals. Old single-PID records and
unverified processes require manual identity review; they are not automatically
adopted. Stop with the previously installed template and verify the process/rules
before upgrading. The installer refuses existing PID or pending publication files.

Stop sends TERM and waits up to15 one-second polls before compatibility cleanup.
Timeout or signal failure retains the process record, plan and OpkgTun marker;
restart fails without starting another client. Correct the cause and retry. A
pending publication file requires ownership review, not deletion to bypass the gate.
There is no automatic KILL escalation. Status codes:0 running,3 stopped,4 unverified.
The wrapper delegates TUN lifetime to core/kernel/ndm, including persistent TUNs.
A successful start confirms a live executable, not authentication or connectivity.
Shell/proc checks do not provide atomic pidfd identity or serialize all operations.
Linux native-helper tests qualify the wrapper's order; actual router integration
is excluded. See [Q31](../reports/AUDIT-Q31-OPENWRT-CONTROLS.md).


## OpkgTun plan application receipt

The hook writes `/opt/var/run/qeli.opkgtun.applied` (0600) only after all ndm commands and save succeed. A changed plan, including MTU alone, or missing receipt forces reapplication. Connected/address matches alone cannot skip it. Publication/removal errors preserve `.apply-pending`; correct the cause and retry. Successful stop clears both records after client exit. This is a command receipt, not a lock or full readback: concurrent events, external setting changes and real firmware remain unqualified. See [Q31](../reports/AUDIT-Q31-OPENWRT-CONTROLS.md).


## Maintainer host verification

`python scripts/keenetic_verify.py` uses `QELI_LAB_PASS`, optional `QELI_LAB_SERVER` (default10.66.116.11) and `QELI_LAB_USER` (defaultroot). It builds in a new private `/var/tmp/qeli-keenetic-verify.*` directory with its own target, locked dependencies and one compiler job; services remain running. The printed directory is retained for inspection and should be removed after use. Exit0 means host build/tests/Clippy/graph/ELF/hash passed; exit1 means verification/connect/close failure; exit2 means credentials missing. Host success does not certify MIPS/ARM ABI or firmware. [Audit details](../reports/AUDIT-Q31-OPENWRT-CONTROLS.md).


## Gateway ownership through the core INI parser

The current binary supports:

```sh
qeli-client --config /opt/etc/qeli/client.conf --print-gateway-owner
```

It validates the same INI grammar as runtime and prints only `core` when
`gateway_nat`, `forward` or `exit_node` is enabled, otherwise `legacy`. It exits
without connecting, executing hooks or configuring networking. Both init templates
use this command once before gateway startup. Quoted/case/on/BOM values follow the
core parser; invalid configs or unsupported/invalid replies fail startup. With
`GATEWAY=no` or active OpkgTun, no legacy ownership query is needed.

Update standalone binary and template together; an old binary without the command
cannot start the compatibility gateway path. Core ownership suppresses wrapper
LAN NAT, including exit-node operation. Legacy ownership preserves the fallback
when core flags are absent/false. This snapshot does not lock the config: keep it
stable during start and use stop/update/start to change ownership. Actual router
firmware and concurrent generation handling remain unqualified. [Q31](../reports/AUDIT-Q31-OPENWRT-CONTROLS.md).
