"""Actual OpenWrt procd/rc.common/UCI in an owned rootfs chroot.
Requires root Linux and QELI_OPENWRT_ROOTFS_TEMPLATE (official extracted rootfs).
The client is an inert sleep/receipt adapter; no VPN, real TUN or firewall runs.
Source/archive/runtime identities are recorded by the lab evidence runner.
"""
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = os.environ.get('QELI_OPENWRT_ROOTFS_TEMPLATE', '')
CHROOT = shutil.which('chroot')

@unittest.skipUnless(os.name == 'posix' and hasattr(os, 'geteuid') and
                    os.geteuid() == 0 and CHROOT and TEMPLATE and
                    Path(TEMPLATE).is_dir(), 'requires owned OpenWrt rootfs/chroot')
class ProcdIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='runtime-', dir=Path(TEMPLATE).resolve().parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.jail = self.root/'jail'
        shutil.copytree(TEMPLATE, self.jail, symlinks=True)
        for folder in ['tmp/run/qeli', 'tmp/lock', 'tmp/log', 'dev/net', 'fixture', 'etc/rc.d']:
            (self.jail/folder).mkdir(parents=True, exist_ok=True)
        for name, minor in [('null', 3), ('urandom', 9)]:
            os.mknod(self.jail/'dev'/name, stat.S_IFCHR | 0o600, os.makedev(1, minor))
        (self.jail/'dev/net/tun').touch()  # existence marker, never a real TUN
        self.run = self.jail/'tmp/run/qeli'
        self.fixture = self.jail/'fixture'
        self.init = self.jail/'etc/init.d/qeli'
        self.init.write_bytes((ROOT/'qeli-openwrt/files/qeli.init').read_bytes())
        self.init.chmod(0o700)
        (self.jail/'etc/config/qeli').write_bytes((ROOT/'qeli-openwrt/files/qeli.config').read_bytes())
        (self.jail/'etc/config/firewall').write_text('')  # real UCI; no zones to mutate
        (self.jail/'usr/bin/qeli-client').write_text(CLIENT)
        (self.jail/'usr/bin/qeli-client').chmod(0o700)
        (self.run/'password').write_text('fixture-secret')
        (self.run/'password').chmod(0o600)
        self.processes = []
        self.logs = []
        self.addCleanup(self.stop)
        self.bus = self.launch('/sbin/ubusd', '-s', '/var/run/ubus/ubus.sock')
        self.wait_for(lambda: (self.jail/'tmp/run/ubus/ubus.sock').exists())
        self.procd = self.launch('/sbin/procd', '-s', '/var/run/ubus/ubus.sock', '-S')
        self.wait_for(lambda: self.call('list').returncode == 0)
        self.uci('set', 'qeli.main.enabled=1')
        self.uci('set', 'qeli.main.server=vpn.example:443')
        self.uci('set', 'qeli.main.user=router-fixture')
        self.uci('commit', 'qeli')
    def launch(self, *args):
        log=(self.root/('daemon-'+str(len(self.logs))+'.log')).open('wb')
        self.logs.append(log)
        p=subprocess.Popen([CHROOT, str(self.jail), *args], stdout=log, stderr=log,
                           env={'PATH': '/usr/bin:/usr/sbin:/bin:/sbin', 'LC_ALL': 'C'},
                           start_new_session=True)
        self.processes.append(p)
        return p
    def command(self, *args):
        return subprocess.run([CHROOT, str(self.jail), *args], capture_output=True,
                              text=True, timeout=15,
                              env={'PATH': '/usr/bin:/usr/sbin:/bin:/sbin', 'LC_ALL': 'C'})
    def uci(self, *args):
        result=self.command('/sbin/uci', *args)
        self.assertEqual(result.returncode, 0, result.stderr)
    def invoke(self, action):
        return self.command('/etc/init.d/qeli', action)
    def call(self, method, args=None):
        return self.command('/bin/ubus', 'call', 'service', method, json.dumps(args or {}))
    def state(self):
        result=self.call('list', {'name': 'qeli', 'verbose': True})
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)
    def pid(self):
        return self.state().get('qeli', {}).get('instances', {}).get('qeli', {}).get('pid')
    def wait_for(self, predicate, timeout=3):
        limit=time.monotonic()+timeout
        while time.monotonic()<limit:
            if predicate():return
            time.sleep(0.03)
        self.fail('condition timed out: '+self.log_text())
    def log_text(self):
        return '\n'.join(p.read_text(errors='replace') for p in self.root.glob('daemon-*.log'))
    def owned_pid(self, pid):
        try:return Path(os.readlink('/proc/'+str(pid)+'/root')).resolve()==self.jail.resolve()
        except FileNotFoundError:return False
    def stop(self):
        self.call('delete', {'name': 'qeli'})
        # Stop only receipt-bound children still inside this exact owned chroot.
        for receipt in self.fixture.glob('started-*'):
            pid=int(receipt.name.split('-')[1])
            if self.owned_pid(pid):os.kill(pid, signal.SIGKILL)
        for p in reversed(self.processes):
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:p.kill();p.wait(timeout=3)
        for log in self.logs:log.close()
    def start(self):
        result=self.invoke('start')
        self.assertEqual(result.returncode, 0, result.stderr+self.log_text())
        self.wait_for(lambda: self.pid() is not None)
        pid=self.pid()
        self.wait_for(lambda: (self.fixture/('started-'+str(pid))).exists())
        return pid
    def test_actual_start_receipt_environment_private_ini_and_stop(self):
        pid=self.start()
        receipt=(self.fixture/('started-'+str(pid))).read_text().splitlines()
        self.assertEqual(receipt, ['--config', '/var/run/qeli/client.conf',
                                  '/etc/qeli/device-id', '/etc/qeli/known_hosts'])
        self.assertEqual((self.run/'client.conf').stat().st_mode & 0o777, 0o600)
        self.assertIn('server = "vpn.example:443"', (self.fixture/('config-'+str(pid))).read_text())
        self.assertEqual(self.invoke('running').returncode, 0)
        self.assertEqual(self.invoke('stop').returncode, 0)
        self.wait_for(lambda: not self.owned_pid(pid))
        self.assertFalse((self.run/'client.conf').exists())
        self.assertEqual((self.run/'password').read_text(), 'fixture-secret')
    def test_restart_reload_replace_process_and_config_keep_secrets(self):
        pid=self.start()
        for action,server in [('restart', 'next.example:443'), ('reload', 'reload.example:443')]:
            self.uci('set', 'qeli.main.server='+server);self.uci('commit', 'qeli')
            result=self.invoke(action);self.assertEqual(result.returncode, 0, result.stderr)
            self.wait_for(lambda: self.pid() is not None and self.pid()!=pid)
            self.wait_for(lambda: not self.owned_pid(pid))
            pid=self.pid();self.wait_for(lambda: (self.fixture/('config-'+str(pid))).exists())
            self.assertIn('server = "'+server+'"', (self.fixture/('config-'+str(pid))).read_text())
            self.assertEqual((self.run/'password').read_text(), 'fixture-secret')
    def test_actual_respawn_after_owned_child_sigkill(self):
        pid=self.start();self.assertTrue(self.owned_pid(pid));os.kill(pid, signal.SIGKILL)
        self.wait_for(lambda: self.pid() is not None and self.pid()!=pid, timeout=8)
        new=self.pid();self.wait_for(lambda: (self.fixture/('started-'+str(new))).exists())
        self.assertEqual((self.run/'password').read_text(), 'fixture-secret')
    def test_disabled_start_registers_no_process_and_autostart_links(self):
        self.uci('set', 'qeli.main.enabled=0');self.uci('commit', 'qeli')
        self.assertEqual(self.invoke('start').returncode, 0)
        self.assertIsNone(self.pid());self.assertEqual(self.invoke('running').returncode, 1)
        self.assertEqual(self.invoke('enable').returncode, 0)
        self.assertTrue((self.jail/'etc/rc.d/S99qeli').is_symlink())
        self.assertEqual(self.invoke('enabled').returncode, 0)
        self.assertEqual(self.invoke('disable').returncode, 0)
        self.assertFalse((self.jail/'etc/rc.d/S99qeli').is_symlink())
    def test_missing_secret_or_binary_fails_before_instance(self):
        (self.run/'password').unlink()
        self.assertNotEqual(self.invoke('start').returncode, 0);self.assertIsNone(self.pid())
        (self.run/'password').write_text('fixture-secret')
        (self.jail/'usr/bin/qeli-client').unlink()
        self.assertNotEqual(self.invoke('start').returncode, 0);self.assertIsNone(self.pid())
    def test_missing_bus_is_not_reported_as_success(self):
        self.procd.terminate();self.procd.wait(timeout=3)
        self.bus.terminate();self.bus.wait(timeout=3)
        for action in ['start', 'stop', 'restart', 'reload']:
            with self.subTest(action=action):
                result=self.invoke(action)
                self.assertNotEqual(result.returncode, 0, action+': '+result.stderr)
    def test_missing_procd_is_not_reported_as_success(self):
        self.procd.terminate();self.procd.wait(timeout=3)
        for action in ['start', 'stop', 'restart', 'reload']:
            with self.subTest(action=action):
                result=self.invoke(action)
                self.assertNotEqual(result.returncode, 0, action+': '+result.stderr)

CLIENT = r"""#!/bin/sh
printf '%s\n' "$@" "$QELI_DEVICE_ID_FILE" "$QELI_KNOWN_HOSTS" > /fixture/started-$$
cp /var/run/qeli/client.conf /fixture/config-$$ || exit 17
exec /bin/sleep 600
"""

if __name__ == '__main__':
    unittest.main()
