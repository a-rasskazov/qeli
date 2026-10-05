#!/usr/bin/env python3
"""Offline Android payload gate: disposable readonly AVD and Qeli in fresh NET/MNT/PID.

No working service, host firewall, physical carrier or production profile is used.
The Linux binary and uploaded APK bytes must be supplied by a qualified caller.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
import traceback
from audit_udp_handshake_contracts import hashed, stop


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def userdata():
    result = {}
    for path in sorted(Path("/root/.android/avd/test.avd").glob("userdata*")):
        if path.is_file() and path.suffix in (".img", ".qcow2"):
            info = path.stat()
            result[path.name] = dict(size=info.st_size, mtime_ns=info.st_mtime_ns, sha256=sha(path))
    assert result, "no persistent AVD userdata found"
    return result


class Echo:
    """Independent framed TCP/reversed payload and UDP tagged reply sinks."""
    def __init__(self, output):
        self.output = output
        self.sockets = []
        self.threads = []
        self.closing = threading.Event()
        self.lock = threading.Lock()
        self.rows = []
        for family, host in ((socket.AF_INET, "0.0.0.0"), (socket.AF_INET6, "::")):
            for kind in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
                sock = socket.socket(family, kind)
                if family == socket.AF_INET6:
                    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                sock.bind((host, 26000))
                sock.settimeout(.5)
                if kind == socket.SOCK_STREAM:
                    sock.listen(4)
                self.sockets.append(sock)
                thread = threading.Thread(target=self.serve, args=(sock, kind), daemon=True)
                thread.start()
                self.threads.append(thread)

    def record(self, protocol, peer, payload):
        with self.lock:
            self.rows.append(dict(protocol=protocol, peer=peer[0], bytes=len(payload),
                                  payload_sha256=hashlib.sha256(payload).hexdigest()))
            self.output.write_text(json.dumps(self.rows, indent=2) + "\n")

    def serve(self, sock, kind):
        try:
            while not self.closing.is_set():
                try:
                    if kind == socket.SOCK_DGRAM:
                        payload, peer = sock.recvfrom(65535)
                        sock.sendto(b"Q29:" + payload, peer)
                        self.record("udp", peer, payload)
                    else:
                        client, peer = sock.accept()
                        try:
                            with client:
                                client.settimeout(10)
                                def exact(length):
                                    data = b""
                                    while len(data) < length:
                                        chunk = client.recv(length - len(data))
                                        if not chunk:
                                            raise EOFError("TCP echo client closed early")
                                        data += chunk
                                    return data
                                length = struct.unpack("!I", exact(4))[0]
                                assert 0 < length <= 65536
                                payload = exact(length)
                                client.sendall(struct.pack("!I", length) + payload[::-1])
                                self.record("tcp", peer, payload)
                        except (EOFError, OSError):
                            # A cancelled/failed client must not kill the shared listener.
                            continue
                except socket.timeout:
                    continue
        except (OSError, EOFError):
            if not self.closing.is_set():
                with self.lock:
                    self.rows.append(dict(error=traceback.format_exc()))
                    self.output.write_text(json.dumps(self.rows, indent=2) + "\n")

    def close(self):
        self.closing.set()
        for sock in self.sockets:
            sock.close()
        for thread in self.threads:
            thread.join(12)
            assert not thread.is_alive(), "echo worker remained"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--qeli", type=Path, required=True)
    ap.add_argument("--sha256", required=True)
    ap.add_argument("--inside", action="store_true")
    ap.add_argument("--suite", choices=("explicit", "ordinary"), default="explicit")
    args = ap.parse_args()
    assert os.geteuid() == 0
    root = args.root.resolve(strict=True)
    assert re.fullmatch(r"/var/tmp/qeli-q29-data-[a-z0-9-]+", str(root)), root
    assert sha(args.qeli) == args.sha256
    if not args.inside:
        env = dict(os.environ)
        for kind in ("net", "mnt", "pid"):
            env["Q29_PARENT_" + kind.upper()] = os.readlink("/proc/self/ns/" + kind)
        return subprocess.run(["unshare", "--net", "--mount", "--pid", "--fork", "--kill-child=KILL",
                               "--mount-proc", sys.executable, __file__, "--inside", "--root", str(root),
                               "--qeli", str(args.qeli), "--sha256", args.sha256, "--suite", args.suite], env=env, timeout=650).returncode
    assert all(os.readlink("/proc/self/ns/" + kind) != os.environ["Q29_PARENT_" + kind.upper()]
               for kind in ("net", "mnt", "pid"))
    evidence = root / "evidence"
    evidence.mkdir(mode=0o700)
    result = dict(status="RUNNING", namespace_isolation=True, qeli_sha256=args.sha256, suite=args.suite)
    def dump(name, value):
        (evidence / name).write_text(json.dumps(value, indent=2) + "\n")
    def cmd(*argv, timeout=30):
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        assert proc.returncode == 0, (argv, proc.stdout, proc.stderr)
        return proc.stdout
    cmd("mount", "--make-rprivate", "/")
    cmd("ip", "link", "set", "lo", "up")
    for path in ("/run", "/var/lib", "/var/log"):
        cmd("mount", "-t", "tmpfs", "tmpfs", path)
    Path("/var/lib/qeli").mkdir()
    Path("/var/log/qeli").mkdir()
    private = root / "etc"
    private.mkdir(mode=0o700)
    cmd("mount", "--bind", str(private), "/etc/qeli")
    namespace_before = cmd("ip", "-br", "addr")
    (evidence / "namespace-network-before.txt").write_text(namespace_before)
    before = userdata()
    dump("avd-userdata-before.json", before)
    dump("namespace-identities.json", {kind: os.readlink("/proc/self/ns/" + kind) for kind in ("net", "mnt", "pid")})
    config = "[auth]\nusers_file = " + str(root / "users.ini") + "\nrequire_client_key_proof = true\nbind_static_to_session = true\n[web]\nenabled = false\n[logging]\nlevel = debug\n"
    for profile, port, subnet, v6 in (("tcp", 24966, "10.86.0", "fd86:29:1"), ("udp", 24967, "10.87.0", "fd86:29:2")):
        config += f"""[profile:{profile}]
identity_key = {root}/{profile}.key
bind.address = 127.0.0.1
bind.port = {port}
bind.transport = {profile}
tun.name = q29{profile}
tun.address = {subnet}.1
tun.queues = 1
tun.ip_mode = dual
tun.ipv6_address = {v6}::1
pool.cidr = {subnet}.0/24
pool.ipv6.cidr = {v6}::/120
routing.nat.enabled = false
routing.ipv6.mode = manual
dns.enabled = false
obf.mode = fake-tls
obf.heartbeat.enabled = true
obf.heartbeat.interval_ms = 5000
obf.heartbeat.jitter_ms = 100
obf.traffic_shaping.enabled = false
perf.connection.idle_timeout_secs = 0
perf.connection.max_clients = 8
perf.connection.handshake_timeout_secs = 12
"""
    (root / "server.ini").write_text(config)
    (root / "server.ini").chmod(0o600)
    (root / "users.ini").write_text("[user:fixture]\npassword_hash = " + hashed() + "\nenabled = true\n")
    (root / "users.ini").chmod(0o600)
    temporary = root / "tmp"
    temporary.mkdir(mode=0o700)
    os.environ["TMPDIR"] = str(temporary)
    state = root / "state"
    state.mkdir(mode=0o700)
    env = dict(os.environ, STATE_DIRECTORY=str(state), QELI_CONTROL_SOCKET=str(root / "control.sock"))
    adb = "/root/android-sdk/platform-tools/adb"
    serial = "emulator-5560"
    def arun(*argv, timeout=30, check=True):
        proc = subprocess.run([adb, "-s", serial, *argv], capture_output=True, text=True, timeout=timeout)
        if check:
            assert proc.returncode == 0, (argv, proc.stdout, proc.stderr)
        return proc
    server = emulator = echo = capture = None
    started = time.monotonic()
    try:
        cmd(str(args.qeli), "check-config", "-c", str(root / "server.ini"))
        public = cmd(str(args.qeli), "show-identity", "-c", str(root / "server.ini"))
        (evidence / "server-public-keys.txt").write_text(public)
        keys = dict(re.findall(r"(?m)^(tcp|udp)\s+\S+\s+([0-9a-f]{64})$", public))
        assert len(keys) == 2, public
        server_log = (evidence / "server.log").open("wb")
        server = subprocess.Popen([str(args.qeli), "server", "-c", str(root / "server.ini")], env=env,
                                  stdout=server_log, stderr=subprocess.STDOUT, start_new_session=True)
        until = time.monotonic() + 20
        while time.monotonic() < until:
            assert server.poll() is None, "server exited"
            if "q29tcp" in cmd("ip", "-br", "link") and "q29udp" in cmd("ip", "-br", "link"):
                break
            time.sleep(.1)
        else:
            raise AssertionError("server TUN setup timeout")
        capture = subprocess.Popen(["tcpdump", "-i", "q29tcp", "-U", "-s", "0", "-w", str(evidence / "tcp-tun.pcap")],
                                   stdout=(evidence / "tcpdump.log").open("wb"), stderr=subprocess.STDOUT, start_new_session=True)
        echo = Echo(evidence / "echo-receipts.json")
        command = ["/root/android-sdk/emulator/emulator", "-avd", "test", "-port", "5560", "-read-only",
                   "-no-snapshot-load", "-no-snapshot-save", "-no-window", "-no-audio", "-no-boot-anim",
                   "-gpu", "swiftshader", "-memory", "768", "-cores", "1"]
        dump("emulator-command.json", command)
        cmd(adb, "start-server")
        emulator = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=(evidence / "emulator.log").open("wb"),
                                    stderr=subprocess.STDOUT, start_new_session=True)
        print("PRIVATE_SERVER_AND_READONLY_AVD_STARTED", flush=True)
        until = time.monotonic() + 240
        while time.monotonic() < until:
            assert emulator.poll() is None, "emulator exited"
            proc = arun("shell", "getprop", "sys.boot_completed", timeout=15, check=False)
            if proc.returncode == 0 and proc.stdout.strip() == "1":
                break
            time.sleep(2)
        else:
            raise AssertionError("AVD boot timeout")
        assert not arun("shell", "pm", "list", "packages", "com.qeli").stdout.strip(), "fixture already has Qeli"
        stale = arun("shell", "pm", "list", "packages", "-u", "com.qeli").stdout
        for package in ("com.qeli.test", "com.qeli"):
            if re.search(r"^package:" + re.escape(package) + r"$", stale, re.M):
                arun("uninstall", package, timeout=60)
        result["environment"] = {name: arun("shell", "getprop", name).stdout.strip()
                                 for name in ("ro.build.version.sdk", "ro.build.version.release", "ro.product.cpu.abi")}
        methods = ["tcpDualStackPayloadAndCompletedRestart", "udpDualStackPayload", "quicDualStackPayload"]
        phases = [("baseline", "com.qeli.VpnDataPlaneInstrumentedTest#" + methods[0]),
                  ("fixed", ",".join("com.qeli.VpnDataPlaneInstrumentedTest#" + method for method in methods))]
        expected_tests = 3
        if args.suite == "ordinary":
            methods = [transport + "Ordinary" + mode + "Payload" for transport in ("tcp", "udp", "quic")
                       for mode in ("Split", "Full")]
            phases = [("fixed", ",".join("com.qeli.VpnDataPlaneInstrumentedTest#" + method for method in methods))]
            expected_tests = 6
        for folder, selector in phases:
            manifest = json.loads((root / folder / "manifest.json").read_text())
            result[folder + "_apks"] = manifest
            for name, digest in manifest["apks"].items():
                apk = root / folder / name
                assert sha(apk) == digest
                (evidence / (folder + "-" + name + "-install.log")).write_text(arun("install", "-r", "-t", str(apk), timeout=90).stdout)
            arun("shell", "appops", "set", "com.qeli", "ACTIVATE_VPN", "allow")
            arun("shell", "pm", "grant", "com.qeli", "android.permission.POST_NOTIFICATIONS")
            proc = arun("shell", "am", "instrument", "-w", "-r", "-e", "class", selector,
                        "-e", "q29_private_fixture", "1", "-e", "q29_key_tcp", keys["tcp"],
                        "-e", "q29_key_udp", keys["udp"], "com.qeli.test/androidx.test.runner.AndroidJUnitRunner", timeout=240)
            (evidence / (folder + "-instrumentation.log")).write_text(proc.stdout + proc.stderr)
            result[folder + "_output"] = proc.stdout
            result[folder + "_echo_receipts"] = len(echo.rows)
            (evidence / (folder + "-vpn-logcat.log")).write_text(arun("shell", "logcat", "-d", "-s", "VpnSvc:D", "Q29Traffic:I", "AndroidRuntime:E").stdout)
            if folder == "fixed":
                assert f"OK ({expected_tests} tests)" in proc.stdout, proc.stdout
            print(folder.upper() + "_COMPLETE", flush=True)
        assert not any("error" in row for row in echo.rows), echo.rows
        for profile, subnet, v6 in (("tcp", "10.86.0.", "fd86:29:1:"), ("udp", "10.87.0.", "fd86:29:2:")):
            for family_prefix in (subnet, v6):
                for protocol in ("tcp", "udp"):
                    assert any(row.get("peer", "").startswith(family_prefix) and row.get("protocol") == protocol
                               for row in echo.rows), (profile, family_prefix, protocol, echo.rows)
        arun("shell", "am", "force-stop", "com.qeli")
        links = arun("shell", "su", "0", "ip", "-o", "link", "show").stdout
        (evidence / "android-links-after.txt").write_text(links)
        assert not re.search(r"^\d+: tun\d", links, re.M), links
        for name, command in (("android-services-after.txt", ["shell", "dumpsys", "activity", "services", "com.qeli"]),
                              ("android-runtime.log", ["shell", "logcat", "-d", "-s", "AndroidRuntime:E"])):
            (evidence / name).write_text(arun(*command).stdout)
        assert "FATAL EXCEPTION" not in (evidence / "android-runtime.log").read_text()
        result["status"] = "PASS"
    except BaseException:
        result["status"] = "FAIL"
        result["error"] = traceback.format_exc()
        print(result["error"], flush=True)
        try:
            (evidence / "failure-vpn-logcat.log").write_text(arun("shell", "logcat", "-d", "-s", "VpnSvc:D", "AndroidRuntime:E", timeout=20, check=False).stdout)
        except Exception:
            pass
    finally:
        if echo is not None:
            try:
                echo.close()
            except BaseException:
                result["status"] = "FAIL"
                result["cleanup_error"] = traceback.format_exc()
        stop(capture)
        stop(emulator)
        if server is not None and server.poll() is None:
            os.killpg(server.pid, signal.SIGTERM)
            try:
                server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                stop(server)
        result["server_exit_code"] = None if server is None else server.returncode
        namespace_after = cmd("ip", "-br", "addr")
        (evidence / "namespace-network-after.txt").write_text(namespace_after)
        result["namespace_addresses_restored"] = namespace_after == namespace_before
        if server is not None and (server.returncode != 0 or namespace_after != namespace_before):
            result["status"] = "FAIL"
            result["cleanup_error"] = "server exit/network cleanup failed"
        subprocess.run([adb, "kill-server"], timeout=15, capture_output=True)
        after = userdata()
        dump("avd-userdata-after.json", after)
        result["avd_userdata_unchanged"] = before == after
        if before != after:
            result["status"] = "FAIL"
            result["error"] = "persistent AVD userdata changed"
        result["elapsed_seconds"] = round(time.monotonic() - started, 2)
        dump("result.json", result)
        print("FINISHED " + result["status"] + "; USERDATA_UNCHANGED=" + str(before == after), flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
