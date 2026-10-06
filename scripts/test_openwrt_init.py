"""Real init functions in isolated files, mocked UCI/firewall; never mutate /etc.
Linux: QELI_OPENWRT_TEST_SHELL='/usr/bin/busybox ash' python -m unittest
  discover -s scripts -p test_openwrt_init.py -v
"""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHELL = shlex.split(os.environ.get('QELI_OPENWRT_TEST_SHELL', '/bin/sh'))
PRELUDE = r'''
. "$QELI_TEST_INIT"
RUNDIR="$QELI_TEST_ROOT/run"
CONF="$RUNDIR/client.conf"
PASS_FILE="$RUNDIR/password"
OBFS_KEY_FILE="$RUNDIR/obfs-key"
STATEDIR="$QELI_TEST_ROOT/state"
FIREWALL_INIT="$QELI_TEST_ROOT/firewall"
logger() { :; }
config_get() {
    local value
    value="$(printenv "QELI_TEST_$3")" || value="${4:-}"
    export "$1=$value"
}
config_get_bool() { config_get "$@"; }
config_list_foreach() {
    local item
    for item in ${QELI_TEST_dns_servers:-}; do "$3" "$item"; done
}
config_load() { :; }
config_foreach() { "$1" zone0; }
uci() {
    [ "$1" != -q ] || shift
    local verb="$1" key="$2"
    if [ "$verb" = get ]; then
        case "$key" in
            qeli.main.dev) printf '%s' "${QELI_TEST_dev:-qeli0}" ;;
            firewall.zone0.name) printf qeli ;;
            firewall.zone0.device) cat "$QELI_TEST_ROOT/device" ;;
            firewall.zone0.masq6) cat "$QELI_TEST_ROOT/masq6" ;;
            *) return 1 ;;
        esac
        return
    fi
    printf '%s\n' "$verb" >> "$QELI_TEST_ROOT/calls"
    [ "${QELI_TEST_FAIL:-}" != "$verb" ] || return 17
    case "$verb" in
        delete) : > "$QELI_TEST_ROOT/device" ;;
        add_list) printf '%s' "${key#*=}" > "$QELI_TEST_ROOT/device" ;;
        set) printf 1 > "$QELI_TEST_ROOT/masq6" ;;
    esac
}
'''

@unittest.skipUnless(shutil.which(SHELL[0]), 'requires POSIX shell (run in Linux lab)')
class OpenWrtInitTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='qeli-openwrt-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'run').mkdir(mode=0o700)
        (self.root / 'run/password').write_text('fixture-password')
        (self.root / 'run/client.conf').write_text('previous-config\n')
        (self.root / 'device').write_text('qeli0')
        (self.root / 'masq6').write_text('1')
        firewall = self.root / 'firewall'
        firewall.write_text('#!/bin/sh\nprintf "reload\\n" >> "$QELI_TEST_ROOT/calls"\n[ "${QELI_TEST_FAIL:-}" != reload ]\n')
        firewall.chmod(0o700)
        self.env = dict(os.environ, QELI_TEST_ROOT=str(self.root),
            QELI_TEST_INIT=str(ROOT / 'qeli-openwrt/files/qeli.init'),
            QELI_TEST_server='vpn.example:443', QELI_TEST_user='router1')

    def run_shell(self, body, **values):
        env = dict(self.env)
        env.update({'QELI_TEST_' + k: v for k, v in values.items()})
        return subprocess.run(SHELL + ['-c', PRELUDE + '\n' + body], env=env,
            text=True, capture_output=True, timeout=15)

    def config(self):
        return (self.root / 'run/client.conf').read_text()

    def calls(self):
        p = self.root / 'calls'
        return p.read_text().splitlines() if p.exists() else []

    def test_render_password_reference_permissions_and_router_dns(self):
        result = self.run_shell('render_conf', gateway='1', kill_switch='1', dns='tunnel',
            dns_servers='1.1.1.1 2606:4700:4700::1111', mtu='1280')
        self.assertEqual(result.returncode, 0, result.stderr)
        content = self.config()
        self.assertIn('forward = true\n', content)
        self.assertIn('dns_servers = 1.1.1.1, 2606:4700:4700::1111\n', content)
        self.assertIn('mtu = 1280\n', content)
        self.assertNotIn('fixture-password', content)
        self.assertIn('password_file = ', content)
        self.assertEqual((self.root / 'run/client.conf').stat().st_mode & 0o777, 0o600)
        self.assertFalse(list((self.root / 'run').glob('.config.*')))

    def test_literal_backslashes_and_controls_cannot_inject_ini_keys(self):
        value = r'vpn.example:443\npost_up = touch /tmp/no-execution'
        result = self.run_shell('render_conf', server=value, proto='tcp\npost_down = bad',
            user='user\x7f\r\npassword_command = bad')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('server = ' + value + '\n', self.config())
        lines = self.config().splitlines()
        self.assertFalse(any(line.startswith(('post_up =', 'post_down =', 'password_command =')) for line in lines))
        self.assertNotIn('\x7f', self.config())

    def test_failed_render_preserves_previous_config(self):
        for mtu in ('abc', '575', '16603', '999999999999999999999999999999999'):
            with self.subTest(mtu=mtu):
                result = self.run_shell('render_conf', mtu=mtu)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.config(), 'previous-config\n')
                self.assertFalse(list((self.root / 'run').glob('.config.*')))

    def test_earlier_write_error_is_not_hidden_by_later_logging_write(self):
        result = self.run_shell('ini_kv() { return 17; }; render_conf')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config(), 'previous-config\n')

    def test_publish_failure_preserves_previous_config_and_removes_temp(self):
        result = self.run_shell('mv() { return 17; }; render_conf')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.config(), 'previous-config\n')
        self.assertFalse(list((self.root / 'run').glob('.config.*')))

    def test_secret_literal_roundtrip_and_boundaries(self):
        prefix = "quote'\"$()`\\;"
        value = prefix + 'x' * (4096 - len(prefix))
        result = self.run_shell('write_runtime_secret_value pass "$QELI_TEST_VALUE"', VALUE=value)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / 'run/password').read_text(), value)
        self.assertEqual((self.root / 'run/password').stat().st_mode & 0o777, 0o600)
        for value in ('', 'x' * 4097, 'bad\x7fvalue', 'bad\nvalue'):
            with self.subTest(length=len(value)):
                old = (self.root / 'run/password').read_text()
                result = self.run_shell('write_runtime_secret_value pass "$QELI_TEST_VALUE"', VALUE=value)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((self.root / 'run/password').read_text(), old)

    def test_legacy_secret_migration_noop_does_not_commit(self):
        result = self.run_shell('migrate_legacy_secrets')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [])

    def test_status_reads_current_committed_flag_and_distinguishes_load_error(self):
        self.assertEqual(self.run_shell('status_enabled', enabled='1').returncode, 0)
        self.assertEqual(self.run_shell('status_enabled', enabled='0').returncode, 1)
        self.assertEqual(self.run_shell('status_enabled').returncode, 1)
        self.assertEqual(self.run_shell('config_load() { return 17; }; status_enabled').returncode, 2)

    def test_firewall_noop_does_not_commit_or_reload(self):
        result = self.run_shell('sync_firewall_device')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [])

    def test_firewall_failures_return_error_and_retry_committed_staged_values(self):
        for failure in ('delete', 'add_list', 'set', 'commit', 'reload'):
            with self.subTest(failure=failure):
                (self.root / 'device').write_text('qeli-old')
                (self.root / 'masq6').write_text('0')
                (self.root / 'calls').write_text('')
                result = self.run_shell('sync_firewall_device', FAIL=failure)
                self.assertNotEqual(result.returncode, 0, result.stderr)
                self.assertTrue((self.root / 'run/firewall-pending').exists())
                result = self.run_shell('sync_firewall_device')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((self.root / 'run/firewall-pending').exists())
                self.assertEqual((self.root / 'device').read_text(), 'qeli0')
                self.assertEqual((self.root / 'masq6').read_text(), '1')
                self.assertEqual(self.calls()[-2:], ['commit', 'reload'])

    def test_firewall_reserved_namespace_rejects_before_mutation(self):
        for dev in ('br-lan', 'wan', 'qeli;bad', 'qeli' + 'x' * 12):
            with self.subTest(dev=dev):
                self.assertNotEqual(self.run_shell('sync_firewall_device', dev=dev).returncode, 0)
                self.assertEqual(self.calls(), [])

if __name__ == '__main__':
    unittest.main()
