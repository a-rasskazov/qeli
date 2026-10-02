# Q25-A125: WAN name reuse

Date: 25 September 2026. Base: `37104b1e`. D06 remains **IN_PROGRESS**.
Priority: P2 (egress through an unselected physical interface; the client address is NATed).

Exit-node MARK, MASQUERADE, and FORWARD permits use `-o <wan>`. The remembered
WAN is a name, not a continuous network-device identity.
[Netfilter documentation](https://www.netfilter.org/documentation/HOWTO/packet-filtering-HOWTO-7.html)
defines `-o` as an interface-name match. The
[nftables manual](https://netfilter.org/projects/nftables/manpage.html)
distinguishes `meta oif` (interface index) from `meta oifname` (name), explicitly
noting that a name rule matches a new interface created with the old name.

Three states were tested on isolated lab server .11 inside private network,
mount, and PID namespaces. The original `wan0` had ifindex 5 and emitted a
packet with NAT source `198.51.100.2`. After replacing the route with `wan1`
(ifindex 7), the guard dropped the packet: its counter reached 1 and the sink
saw no packet. The **new** interface, still ifindex 7, was then given the name
`wan0` and a default route, without a Qeli refresh. The old MARK/MASQUERADE
rules matched again, and the sink received `192.0.2.2 > 203.0.113.9`.
The client address `10.0.0.2` did not escape, but traffic used a different
physical device without WAN requalification. A separate live rename from
`wan0` to `wan-old` preserved both ifindex and the default route under the
new name; the old `-o wan0` selector no longer matched.

Evidence: `C:/Users/litvi/OneDrive/Documents/qeli/audit-debt-20260925/tun-attach-context-phase/wanrename3.log`
and `wanliverename.log`, with `wan-rename-reuse.sh` in the same directory.
Only private namespaces were changed; installed lab services were untouched.

**Contract until the backend is fixed:** do not rename, remove, or replace the
selected WAN while an exit-node profile is active. Stop the profile, verify
successful rule cleanup, change the interface, and then start the profile.
A route change to a distinct interface name is blocked until successful
refresh; reuse of the old name after its former device leaves is not a
protected scenario. The manual now says this explicitly; this audit step
makes no Rust changes.

A complete fix needs to bind egress admission to device identity on each
packet and account for identifier reuse after deletion. `nft meta oif` narrows
simple rename/name-reuse exposure, but an interface index can itself be
reused. Moving an isolated rule to nft without mixed iptables/nft/firewalld
and cleanup validation is not a complete fix. Design and packet/recovery
coverage remain in D06/D10.


## 2 October 2026 continuation: kernel guard selection

On baseline `5bbffe4b`, candidates were qualified; **Qeli was not fixed**:
[runner](../../../scripts/audit_wan_identity_candidates.py) and
[evidence](../../../release/certification/evidence/wan-identity-candidates-20261002.json).
Synthetic exit-shaped MARK/NAT/FORWARD rules use real IPv4/IPv6 UDP packets across
nft/nft, nft/legacy, legacy/nft and legacy/legacy. No worker or VPN runs in this
batch; existing working binaries are only SHA-checked. Rust and INI keys are unchanged.

There are **168 expected-outcome checks**, including reproduction of unsafe variants:
88 probes, 264 datagrams, 168 validated echo replies and 96 expected blocked sends.
In 32 negative checks the specific DROP counter increases by 3. This is not 168
proofs of a security fix.

| Candidate / state | Packet outcome on all four pairs |
|---|---|
| Old WAN name | A new device with the former name inherits MARK/NAT and forwards traffic |
| Preinstalled native nft `meta oif` | A forcibly created device reusing ifindex, name and MAC is also admitted; the native counter sees six packets per cell |
| `devgroup --dst-group` with a separate token | The original retains its token across rename; a new device starts with group 0 after deletion. Name/index/MAC reuse and an incorrect group are blocked |
| Root copies the token to the replacement | The new device is admitted again; the token is neither a secret nor protection against a privileged administrator |
| Foreign `--dst-group 0 -j DROP` rule | Assigning the token instead of group 0 stops this rule from applying to the WAN; restoring group 0 restores blocking |

The kernel `devgroup` matcher reads the outgoing device group:
[Linux source](https://raw.githubusercontent.com/torvalds/linux/master/net/netfilter/xt_devgroup.c).
That group belongs to host network policy. In addition to the demonstrated firewall
conflict, RPDB `suppress_ifgroup` uses it in
[IPv4](https://raw.githubusercontent.com/torvalds/linux/v6.12/net/ipv4/fib_rules.c) and
[IPv6](https://raw.githubusercontent.com/torvalds/linux/v6.12/net/ipv6/fib6_rules.c).
The RPDB effect is established from source, not a separate packet runtime in this
fixture. Automatic group mutation without an administrator ownership contract is
therefore rejected as a transparent fix. A current group of zero does not establish
that foreign rules, masks, sets/maps or route suppression do not use it.

The client monitor was reconciled: `ExitWanSnapshot` in
[gateway.rs](../../../qeli/src/client/gateway.rs) stores only IPv4/IPv6 WAN names.
[spawn_exit_wan_monitor](../../../qeli/src/client/mod.rs) compares snapshots every
five seconds and skips an equal snapshot after successful refresh. Name reuse alone
does not change it. Carrier path observation in
[roaming_linux.rs](../../../qeli/src/client/roaming_linux.rs) can include an index,
but observes a different path and supplies no continuous egress guard. The existing
TCP/UDP [Q25-F127](AUDIT-Q25-EXIT-WAN-MONITOR.md) evidence still covers default WAN
changes to a different name; no fresh monitor E2E is claimed here. Adding an index
to the sampler would still leave the interval before observation and index reuse.

One coherent implementation batch remains: a kernel guard with an explicit ownership
contract for its per-device label, shared IPv4/IPv6 and profile/process leases,
namespace/device witnesses and a unique generation token, journal/rollback/cleanup/
crash recovery that cannot restore labels onto replacements. Then real client/server
packets, established conntrack/marks, mixed backends and recovery must be checked.
The group must not silently change foreign policy; restoration cannot trust only a
name, ifindex or MAC. These requirements have not been implemented.

The intermediate 164 outcomes from r2 are retained separately and not added to the
final 168: r3 installs the ifindex guard on the original WAN and verifies that the
rule stays unchanged across device deletion/recreation.

The first fixture failure is retained: down/up removed its manually assigned IPv6
address and the new default could not be installed. Private `keep_addr_on_down=1`
corrected the fixture; production code is unchanged. Every attempt restores the outer
host snapshot; the final comparison includes link groups, RPDB and no added/removed
kernel modules. Working services and `.10` are untouched. The passing matrix does
not cover a persistent group lease, SIGKILL/recovery or a real firewalld daemon.

**Q25-A125 / D06 remains an open P2.** D10 is closed for its previously supported
firewall composition; a future identity guard will need targeted rechecks of that
composition. The manual restriction on active WAN rename/delete/recreate remains.
