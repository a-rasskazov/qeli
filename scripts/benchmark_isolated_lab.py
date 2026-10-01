#!/usr/bin/env python3
"""Two-VM Qeli benchmark in private IPvlan network and mount namespaces.

Requires pre-staged identical release binaries and QELI_LAB_PASS. Reuses the
historical 12-mode INI builders without invoking their host-wide orchestration.
"""
from concurrent.futures import ThreadPoolExecutor
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time

import benchmark as modes
from native_lab import connect_lab
from native_repro import source_digest

SAMPLER = r'''
import json,os,sys,time
from pathlib import Path
pid,seconds=int(sys.argv[1]),float(sys.argv[2])
proc=Path('/proc')/str(pid)
def read():
    fields=(proc/'stat').read_text().rsplit(')',1)[1].split()
    rss=next(x for x in (proc/'status').read_text().splitlines() if x.startswith('VmRSS:'))
    cpu=[int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    return dict(t=time.monotonic(),ticks=int(fields[11])+int(fields[12]),
                start=fields[19],rss_kib=int(rss.split()[1]),host_total=sum(cpu),host_steal=cpu[7])
first=read();samples=[first]
while time.monotonic()-first['t']<seconds:
    time.sleep(min(.5,max(.01,seconds-(time.monotonic()-first['t']))))
    value=read()
    if value['start']!=first['start']:raise RuntimeError('sampled PID identity changed')
    samples.append(value)
last=samples[-1];elapsed=last['t']-first['t']
print(json.dumps(dict(pid=pid,cpu_avg_pct=100*(last['ticks']-first['ticks'])/os.sysconf('SC_CLK_TCK')/elapsed,
    rss_peak_kib=max(x['rss_kib'] for x in samples),elapsed=elapsed,
    host_steal_pct=100*(last['host_steal']-first['host_steal'])/max(1,last['host_total']-first['host_total']),samples=samples)))
'''


CONTROL = r'''
import json,socket,sys
with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as control:
    control.settimeout(5);control.connect(sys.argv[1])
    control.sendall(b'{"cmd":"list-clients"}\n');control.shutdown(socket.SHUT_WR)
    data=b''
    while True:
        chunk=control.recv(65536)
        if not chunk:break
        data+=chunk
        if len(data)>1048576:raise RuntimeError('oversized control response')
response=json.loads(data)
if response.get('ok') is not True:raise RuntimeError('control query refused')
clients=response.get('clients')
if not isinstance(clients,list) or len(clients)!=1:raise RuntimeError('expected one benchmark session')
client=clients[0]
if client.get('username')!='bench' or client.get('profile')!='bench':raise RuntimeError('wrong benchmark session')
result={key:client[key] for key in ('dropped','bytes_sent','bytes_recv','connected_secs')}
if not all(type(value) is int and value>=0 for value in result.values()):raise RuntimeError('invalid counter')
print(json.dumps(result))
'''


class Fixture:
    def __init__(self, lab, namespace, address, binary, remote):
        self.lab, self.namespace, self.address = lab, namespace, address
        self.binary, self.remote = binary, remote
        self.cookie = None

    def checked(self, command):
        return self.lab.checked(command, self.namespace + ': ' + command, timeout=60)

    def create(self):
        self.checked('ip netns add ' + self.namespace)
        self.cookie = self.checked('stat -Lc %d:%i /var/run/netns/' + self.namespace)
        self.checked('ip link add link ens18 name qd14v type ipvlan mode l2')
        self.checked('ip link set qd14v netns ' + self.namespace)
        self.checked('ip -n ' + self.namespace + ' link set lo up')
        self.checked('ip -n ' + self.namespace + ' addr add ' + self.address + ' dev qd14v')
        self.checked('ip -n ' + self.namespace + ' link set qd14v up')
        self.checked('mkdir -p -m 700 ' + self.remote + '/etc/identity ' + self.remote + '/state ' + self.remote + '/run')
        self.put('users.conf', '')
        self.put('sample.py', SAMPLER, config=False)
        self.put('control.py', CONTROL, config=False)

    def put(self, name, text, config=True):
        path = self.remote + ('/etc/' if config else '/') + name
        sftp = self.lab.open_sftp()
        try:
            with sftp.open(path, 'wb') as output:
                output.write(text.encode('utf-8'))
            sftp.chmod(path, 0o600)
        finally:
            sftp.close()

    def run_in(self, command):
        return 'ip netns exec ' + self.namespace + ' ' + command

    def mounted(self, command):
        setup = ('set -e; mount --bind ' + self.remote + '/etc /etc/qeli; '
                 'mount -t tmpfs tmpfs /var/lib; mkdir -p /var/lib/qeli; '
                 'mount -t tmpfs tmpfs /var/log; mkdir -p /var/log/qeli; ')
        return self.run_in('unshare --mount --propagation private bash -c ' + shlex.quote(setup + command))

    def start(self, command, log, mounted=False):
        inner = self.mounted(command) if mounted else self.run_in(command)
        self.checked('nohup ' + inner + ' >' + self.remote + '/' + log + ' 2>&1 </dev/null & echo $!')

    def wait(self, command, seconds=35):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self.lab.run(command, timeout=20)[1] == 0:
                return
            time.sleep(.3)
        raise RuntimeError('readiness timeout: ' + command)

    def process(self):
        pids = self.checked('ip netns pids ' + self.namespace).split()
        found = []
        for pid in pids:
            if not pid.isdecimal():
                raise RuntimeError('invalid namespace PID')
            exe, code = self.lab.run('readlink /proc/' + pid + '/exe')
            if code == 0 and exe == self.binary:
                found.append(int(pid))
        if len(found) != 1:
            raise RuntimeError('expected one exact Qeli process: ' + str(found))
        return found[0]

    def close(self):
        if self.cookie is None:
            return
        current, code = self.lab.run('stat -Lc %d:%i /var/run/netns/' + self.namespace)
        if code or current != self.cookie:
            raise RuntimeError('refusing cleanup of replaced namespace ' + self.namespace)
        for sig in ('TERM', 'KILL'):
            pids = self.checked('ip netns pids ' + self.namespace).split()
            if not all(pid.isdecimal() for pid in pids):
                raise RuntimeError('invalid cleanup PID list')
            if pids:
                self.lab.run('kill -' + sig + ' ' + ' '.join(pids) + ' 2>/dev/null || true')
            time.sleep(.5)
        self.checked('ip netns del ' + self.namespace)
        self.cookie = None



def cleanup_fixtures(*fixtures):
    errors = []
    for fixture in fixtures:
        try:
            fixture.close()
        except Exception as error:
            errors.append(str(error))
    if errors:
        raise RuntimeError('benchmark cleanup: ' + '; '.join(errors))


def host_snapshot(lab):
    return {label: lab.checked(command, label) for label, command in {
        'addresses': 'ip -br -4 addr', 'routes': 'ip -4 route show table all',
        'qeli_listener': 'ss -lntp | grep :443',
    }.items()}


def configs(mode, key):
    server = modes.server_ini(mode)
    server = server.replace('[auth]\n', '[auth]\nusers_file = /etc/qeli/users.conf\n')
    server = server.replace('file = /var/log/qeli/server.log\n', '')
    server = server.replace('bind.address = 0.0.0.0', 'bind.address = 10.255.42.1')
    server = re.sub(r'tun.name = vpn[01]', 'tun.name = qbench0', server)
    server = server.replace('obf.tls.reality_proxy.target = www.cloudflare.com', 'obf.tls.reality_proxy.target = 10.255.42.1')
    server = server.replace('obf.tls.reality_proxy.target_port = 443', 'obf.tls.reality_proxy.target_port = 9443')
    if mode.get('real_tls'):
        server = server.replace('obf.tls.reality_proxy.real_tls = true', 'obf.tls.reality_proxy.real_tls = true\nobf.tls.reality_proxy.handrolled = true')
    server += '\n[web]\nenabled = false\n'
    client = modes.client_ini(mode, key).replace('server = ' + modes.SERVER[0] + ':', 'server = 10.255.42.1:')
    client = client.replace('[logging]', 'dev = qbench0\ngateway = false\ndns = off\nallow_ipv6_leak = true\ntimeout = 5\n\n[logging]')
    return server, client


def udp_kernel(fixture):
    lines = fixture.checked(fixture.run_in('cat /proc/net/snmp')).splitlines()
    for index, line in enumerate(lines[:-1]):
        if line.startswith('Udp:') and lines[index + 1].startswith('Udp:'):
            return dict(zip(line.split()[1:], map(int, lines[index + 1].split()[1:])))
    raise RuntimeError('UDP kernel counters missing')


def application_stats(fixture):
    return json.loads(fixture.checked('python3 ' + fixture.remote + '/control.py ' + fixture.remote + '/run/control.sock'))


def measure(server, client, server_pid, client_pid, ip, name, flags, seconds, local):
    receiver = client if '-R' in flags.split() else server
    before_kernel = udp_kernel(receiver)
    before_app = application_stats(server)
    duration = seconds + 1
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(fixture.lab.checked,
                   'python3 ' + fixture.remote + '/sample.py ' + str(pid) + ' ' + str(duration),
                   'process CPU/RSS sample', duration + 20)
                   for fixture, pid in ((server, server_pid), (client, client_pid))]
        output = client.lab.checked(client.run_in('timeout ' + str(duration + 15) +
                 ' iperf3 -c ' + ip + ' -p 5203 -t ' + str(seconds) +
                 ' -i 0 ' + flags + ' --json'), 'iperf ' + name, duration + 20)
        raw = json.loads(output)
        (local / (name + '-iperf.json')).write_text(json.dumps(raw, indent=2) + '\n')
        samples = [json.loads(future.result()) for future in futures]
    (local / (name + '-processes.json')).write_text(json.dumps(samples, indent=2) + '\n')
    if 'error' in raw:
        raise RuntimeError(raw['error'])
    end = raw['end']
    received = end.get('sum_received') or end['sum']
    after_kernel = udp_kernel(receiver)
    after_app = application_stats(server)
    return dict(mbps=received['bits_per_second'] / 1e6,
                retransmits=end.get('sum_sent', {}).get('retransmits'),
                lost_percent=received.get('lost_percent'),
                jitter_ms=received.get('jitter_ms'), server=samples[0], client=samples[1],
                kernel_rcvbuf_drops=after_kernel['RcvbufErrors'] - before_kernel['RcvbufErrors'],
                server_session_drops=after_app['dropped'] - before_app['dropped'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-bin', default='/var/tmp/qeli-d14-bin/qeli')
    parser.add_argument('--client-bin', default='/root/qeli-src/target/release/qeli')
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=8)
    parser.add_argument('--modes', nargs='+', choices=[mode['name'] for mode in modes.MODES])
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}', args.sha256) or not 5 <= args.seconds <= 30:
        parser.error('requires a full SHA256 and 5-30 measurement seconds')
    if not all(re.fullmatch('/[A-Za-z0-9_./-]+', path) and '..' not in path.split('/')
               for path in (args.server_bin, args.client_bin)):
        parser.error('binary paths must be absolute safe shell paths')
    password = os.environ.get('QELI_LAB_PASS')
    if not password:
        parser.error('QELI_LAB_PASS is required')
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    modes.RECORDIZER_POLICY = 'off'
    server_lab = connect_lab(os.environ.get('QELI_LAB_SERVER', '10.66.116.10'), 'root', password)
    client_lab = connect_lab(os.environ.get('QELI_LAB_CLIENT', '10.66.116.11'), 'root', password)
    remote = '/var/tmp/qeli-benchmark-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = dict(meta=dict(date=dt.datetime.now(dt.timezone.utc).isoformat(),
        binary_sha256=args.sha256, source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        native_source_digest=source_digest(Path(__file__).resolve().parent.parent),
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        tracked_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], text=True).strip()),
        seconds=args.seconds, tcp_parallel=1, recordizer='off',
        throughput='receiver bits_per_second; UDP offered rates 100/500 Mbps',
        topology='two VM, isolated IPvlan network and private mount namespaces, local TLS target'), modes={})
    before = None
    try:
        before = [host_snapshot(lab) for lab in (server_lab, client_lab)]
        output['host_before'] = before
        for index, (lab, binary) in enumerate(((server_lab, args.server_bin), (client_lab, args.client_bin))):
            sha = lab.checked('sha256sum ' + binary, 'exact binary SHA').split()[0]
            if sha != args.sha256:
                raise RuntimeError('binary SHA mismatch')
            output['meta']['server' if index == 0 else 'client'] = {
                label: lab.checked(command, label) for label, command in {
                    'kernel': 'uname -srmo', 'cpu': 'lscpu',
                    'iperf': 'iperf3 --version | head -1', 'version': binary + ' --version',
                }.items()}
            lab.checked('mkdir -m 700 ' + remote, 'unique remote artifact directory')
        direct_server = Fixture(server_lab, 'qeli-bench-s', '10.255.42.1/30', args.server_bin, remote + '/direct')
        direct_client = Fixture(client_lab, 'qeli-bench-c', '10.255.42.2/30', args.client_bin, remote + '/direct')
        direct_local = args.output / 'direct'
        direct_local.mkdir()
        output['baseline'] = {}
        try:
            direct_server.create(); direct_client.create()
            direct_server.start('iperf3 -s -B 10.255.42.1 -p 5203', 'iperf.log')
            direct_server.wait(direct_server.run_in("ss -lnt | grep -q ':5203'"))
            for name, flags, seconds in (('tcp_up', '', args.seconds), ('tcp_down', '-R', args.seconds), ('udp_500', '-u -b 500M -l 1200', 5)):
                text = direct_client.checked(direct_client.run_in('timeout 45 iperf3 -c 10.255.42.1 -p 5203 -t ' + str(seconds) + ' -i 0 ' + flags + ' --json'))
                raw = json.loads(text)
                (direct_local / (name + '-iperf.json')).write_text(json.dumps(raw, indent=2) + '\n')
                if 'error' in raw:
                    raise RuntimeError('direct baseline: ' + raw['error'])
                end = raw['end']
                received = end.get('sum_received') or end['sum']
                output['baseline'][name] = dict(mbps=received['bits_per_second'] / 1e6,
                    lost_percent=received.get('lost_percent'), retransmits=end.get('sum_sent', {}).get('retransmits'))
            print('BASELINE', output['baseline'], flush=True)
        finally:
            cleanup_fixtures(direct_client, direct_server)
        for mode in modes.MODES:
            if args.modes and mode['name'] not in args.modes:
                continue
            name = mode['name']
            local = args.output / name
            local.mkdir()
            server = Fixture(server_lab, 'qeli-bench-s', '10.255.42.1/30', args.server_bin, remote + '/' + name)
            client = Fixture(client_lab, 'qeli-bench-c', '10.255.42.2/30', args.client_bin, remote + '/' + name)
            result = {}
            print('START', name, flush=True)
            try:
                server.create(); client.create()
                for fixture in (server, client):
                    result[fixture.namespace + '_rmem_max'] = int(fixture.checked(fixture.run_in('sysctl -n net.core.rmem_max')))
                if result['qeli-bench-s_rmem_max'] < 4194304:
                    raise RuntimeError('server UDP receive capacity below 4 MiB')
                server_ini, _ = configs(mode, '')
                server.put('server.conf', server_ini)
                server.checked(server.mounted(args.server_bin + ' check-config -c /etc/qeli/server.conf'))
                identity = server.checked(server.mounted(args.server_bin + ' show-identity -c /etc/qeli/server.conf'))
                match = re.search(r'[0-9a-f]{64}', identity)
                if not match:
                    raise RuntimeError('public identity key missing')
                _, client_ini = configs(mode, match.group(0))
                client.put('client.conf', client_ini)
                if mode.get('reality'):
                    server.checked('openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj /CN=www.cloudflare.com -keyout ' + server.remote + '/target.key -out ' + server.remote + '/target.crt >/dev/null 2>&1')
                    server.start('openssl s_server -4 -accept 10.255.42.1:9443 -cert ' + server.remote + '/target.crt -key ' + server.remote + '/target.key -www -quiet', 'target.log')
                    server.wait(server.run_in("ss -lnt | grep -q ':9443'"))
                environment = 'env STATE_DIRECTORY=' + server.remote + '/state QELI_CONTROL_SOCKET=' + server.remote + '/run/control.sock '
                server.start(environment + args.server_bin + ' _worker -c /etc/qeli/server.conf', 'server.log', mounted=True)
                server.wait(server.run_in("ss -ln" + ('u' if mode['transport'] == 'udp' else 't') + " | grep -q ':" + str(mode['port']) + "'"))
                client.start('env STATE_DIRECTORY=' + client.remote + '/state ' + args.client_bin + ' client -c /etc/qeli/client.conf', 'client.log', mounted=True)
                client.wait("grep -q 'Auth OK' " + client.remote + '/client.log')
                ip = '10.10.0.1' if mode['transport'] == 'udp' else '10.9.0.1'
                result['ping'] = client.checked(client.run_in('ping -n -c 10 -i .2 -W 2 ' + ip))
                server_pid, client_pid = server.process(), client.process()
                result['pids'] = dict(server=server_pid, client=client_pid)
                server.start('iperf3 -s -B ' + ip + ' -p 5203', 'iperf.log')
                server.wait(server.run_in("ss -lnt | grep -q ':5203'"))
                for direction, flags in (('up', ''), ('down', '-R')):
                    result['tcp_' + direction] = measure(server, client, server_pid, client_pid,
                        ip, 'tcp_' + direction, flags, args.seconds, local)
                if mode['transport'] == 'udp':
                    for rate in (100, 500):
                        result['udp_' + str(rate)] = measure(server, client, server_pid, client_pid,
                            ip, 'udp_' + str(rate), '-u -b ' + str(rate) + 'M -l 1200', 5, local)
                result['status'] = 'COMPLETED'
                print('COMPLETED', name, 'TCP Mbps up/down', round(result['tcp_up']['mbps'], 1),
                      round(result['tcp_down']['mbps'], 1), flush=True)
            except Exception as error:
                result.update(status='FAIL', error=str(error))
                print('FAIL', name, str(error)[:500], flush=True)
            finally:
                for fixture, log in ((server, 'server.log'), (client, 'client.log')):
                    text, _ = fixture.lab.run('cat ' + fixture.remote + '/' + log + ' 2>/dev/null || true')
                    (local / log).write_text(text, encoding='utf-8')
                cleanup_fixtures(client, server)
                output['modes'][name] = result
                (args.output / 'results.json').write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
        after = [host_snapshot(lab) for lab in (server_lab, client_lab)]
        output['host_after'] = after
        output['host_restored'] = before == after
        if before != after:
            raise RuntimeError('host state changed after benchmark')
    finally:
        (args.output / 'results.json').write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
        server_lab.close(); client_lab.close()
    return 0 if all(result['status'] == 'COMPLETED' for result in output['modes'].values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
