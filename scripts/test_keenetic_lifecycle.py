"""Real shell/process exclusion in an owned POSIX sandbox; ndm/network are models."""
import os
from pathlib import Path
import shlex
import subprocess
import time
import unittest
import test_keenetic_templates as templates
import test_keenetic_process as processes

class KeeneticLifecycleTests(templates.KeeneticFixture):
    def hook_setup(self, *args, **kwargs):
        folder = super().hook_setup(*args, **kwargs)
        baseline = os.environ.get('QELI_LIFECYCLE_BASELINE')
        if baseline:
            self.copy_template(Path(baseline)/'opkgtun/010-qeli.sh', self.hook)
        return folder

    def wait_file(self, path):
        deadline = time.monotonic()+5
        while not path.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(path.exists(), 'owned subprocess did not reach barrier')

    def pause_hook(self):
        original = (self.bin/'ndmc').read_text().split('\n', 1)[1]
        self.write_command('ndmc', original+"""
if [ "$2" = 'interface OpkgTun0 ip global auto' ]; then
  touch "$QELI_FIXTURE_ROOT/entered"
  n=0
  while [ ! -e "$QELI_FIXTURE_ROOT/release" ] && [ "$n" -lt 500 ]; do
    """+shlex.quote(templates.shutil.which('sleep'))+""" 0.01
    n=$((n+1))
  done
  [ -e "$QELI_FIXTURE_ROOT/release" ] || exit 19
fi
""")
        child = subprocess.Popen(templates.SHELL+[str(self.hook)], env=self.env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def finish():
            (self.root/'release').touch()
            try:
                child.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                child.kill()
                child.communicate()
        self.addCleanup(finish)
        self.wait_file(self.root/'entered')
        return child

    def finish_hook(self, child):
        (self.root/'release').touch()
        out, err = child.communicate(timeout=8)
        self.assertEqual(child.returncode, 0, out+err)
        self.assertFalse((self.opt/'var/run/qeli.lifecycle.lock').exists())

    def test_second_hook_cannot_interleave_mutations(self):
        folder = self.hook_setup()
        first = self.pause_hook()
        before = self.calls('ndmc-calls')
        self.assertNotEqual(self.run_script(self.hook).returncode, 0)
        self.assertEqual(self.calls('ndmc-calls'), before)
        self.finish_hook(first)
        self.assertTrue((folder/'qeli.opkgtun.applied').exists())
        self.assertEqual(self.run_script(self.hook, QELI_CONNECTED='yes').returncode, 0)

    def test_stop_refuses_busy_hook_then_removes_its_state_after_join(self):
        folder = self.hook_setup()
        first = self.pause_hook()
        baseline = os.environ.get('QELI_LIFECYCLE_BASELINE')
        source = Path(baseline)/'opkgtun/S99qeli' if baseline else templates.ROOT/'release/keenetic/opkgtun/S99qeli'
        init = self.copy_template(source, self.root/'init.sh')
        before = self.calls('ndmc-calls')
        stopped = subprocess.run(templates.SHELL+[str(init), 'stop'], env=self.env,
                                 capture_output=True, text=True, timeout=8)
        self.assertNotEqual(stopped.returncode, 0)
        self.assertTrue((folder/'qeli.opkgtun').exists())
        self.assertEqual(self.calls('ndmc-calls'), before)
        self.finish_hook(first)
        stopped = subprocess.run(templates.SHELL+[str(init), 'stop'], env=self.env,
                                 capture_output=True, text=True, timeout=8)
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        for name in ('qeli.opkgtun', 'qeli.tunip', 'qeli.opkgtun.applied', 'qeli.opkgtun.apply-pending'):
            self.assertFalse((folder/name).exists(), name)
        before = self.calls('ndmc-calls')
        self.assertEqual(self.run_script(self.hook).returncode, 0)
        self.assertEqual(self.calls('ndmc-calls'), before)

    def test_installer_refuses_busy_hook_before_dependency_or_publication_work(self):
        self.hook_setup()
        self.seed_installed()
        first = self.pause_hook()
        result = self.installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('opkg update', self.calls())
        self.assertEqual(self.installed('bin/qeli-client').read_text(), 'old binary')
        self.finish_hook(first)

    def test_preexisting_lock_is_retained_without_hook_mutations(self):
        folder = self.hook_setup()
        lock = folder/'qeli.lifecycle.lock'
        lock.mkdir(mode=0o700)
        (lock/'canary').write_text('foreign owner')
        self.assertNotEqual(self.run_script(self.hook).returncode, 0)
        self.assertEqual(self.calls('ndmc-calls'), [])
        self.assertEqual((lock/'canary').read_text(), 'foreign owner')

    def test_missing_shared_library_rejects_active_hook(self):
        self.hook_setup()
        self.installed('etc/qeli/lifecycle.sh').unlink()
        self.assertNotEqual(self.run_script(self.hook).returncode, 0)
        self.assertEqual(self.calls('ndmc-calls'), [])

    def test_signal_releases_lock_without_publishing_complete_receipt(self):
        folder = self.hook_setup()
        first = self.pause_hook()
        first.terminate()
        (self.root/'release').touch()
        first.communicate(timeout=8)
        self.assertNotEqual(first.returncode, 0)
        self.assertFalse((folder/'qeli.lifecycle.lock').exists())
        self.assertFalse((folder/'qeli.opkgtun.applied').exists())
        self.assertTrue((folder/'qeli.opkgtun.apply-pending').exists())

    def test_core_plan_replacement_during_save_retains_retry_and_no_receipt(self):
        folder = self.hook_setup()
        original = (self.bin/'ndmc').read_text().split('\n', 1)[1]
        self.write_command('ndmc', original+"""
if [ "$2" = 'system configuration save' ] && [ ! -e "$QELI_FIXTURE_ROOT/rotated" ]; then
  printf '10.8.0.9\\nipv4=10.8.0.9/32\\nmtu=1280\\n' > """+shlex.quote(str(folder/'qeli.tunip'))+"""
  touch "$QELI_FIXTURE_ROOT/rotated"
fi
""")
        self.assertNotEqual(self.run_script(self.hook).returncode, 0)
        self.assertFalse((folder/'qeli.opkgtun.applied').exists())
        self.assertTrue((folder/'qeli.opkgtun.apply-pending').exists())
        self.assertFalse((folder/'qeli.lifecycle.lock').exists())
        self.assertEqual(self.run_script(self.hook).returncode, 0)
        self.assertEqual((folder/'qeli.opkgtun.applied').read_text(), 'opkgtun0\n10.8.0.9\nipv4=10.8.0.9/32\nmtu=1280\n')

    def test_restart_and_start_stop_admission_share_one_lock_for_both_templates(self):
        if not processes.NATIVE.is_file():
            self.skipTest('requires owned native process fixture')
        for cls in (processes.KeeneticBaseProcessTests, processes.KeeneticOpkgTunProcessTests):
            with self.subTest(template=cls.TEMPLATE):
                fixture = cls()
                fixture.setUp()
                self.addCleanup(fixture.doCleanups)
                script = fixture.script.read_text()
                barrier = """
nat_up() {
  touch "$QELI_FIXTURE_ROOT/admitted"
  n=0
  while [ ! -e "$QELI_FIXTURE_ROOT/admit-release" ] && [ "$n" -lt 500 ]; do
    """+shlex.quote(templates.shutil.which('sleep'))+""" 0.01
    n=$((n+1))
  done
  [ -e "$QELI_FIXTURE_ROOT/admit-release" ]
}
"""
                head, dispatch = script.rsplit('case "$1" in', 1)
                fixture.script.write_text(head+barrier+'case "$1" in'+dispatch)
                child = subprocess.Popen(templates.SHELL+[str(fixture.script), 'start'],
                                         env=fixture.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                def finish(c=child, f=fixture):
                    (f.root/'admit-release').touch()
                    try:
                        c.communicate(timeout=8)
                    except subprocess.TimeoutExpired:
                        c.kill()
                        c.communicate()
                self.addCleanup(finish)
                self.wait_file(fixture.root/'admitted')
                pids = fixture.helper_pids()
                self.assertEqual(len(pids), 1)
                lock = fixture.opt/'var/run/qeli.lifecycle.lock'
                self.assertEqual(lock.stat().st_mode & 0o777, 0o700)
                for action in ('start', 'stop', 'restart'):
                    self.assertNotEqual(fixture.service(action).returncode, 0, action)
                    self.assertEqual(fixture.helper_pids(), pids)
                    self.assertNotIn('CLEANUP', fixture.event_lines())
                (fixture.root/'admit-release').touch()
                out, err = child.communicate(timeout=8)
                self.assertEqual(child.returncode, 0, out+err)
                self.assertFalse(lock.exists())
                self.assertEqual(fixture.service('restart').returncode, 0)
                self.assertEqual(len(fixture.helper_pids()), 2)
                self.assertEqual(fixture.service('stop').returncode, 0)
                self.assertFalse(lock.exists())
                self.assertFalse(fixture.pidfile.exists())

if __name__ == '__main__':
    unittest.main()
