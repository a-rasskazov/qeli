"""Execute router helper failure paths without SSH, toolchain installs or real builds."""
import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

KEEN = load('q31_keen', ROOT / 'scripts/build_keenetic.py')
OPEN = load('q31_open', ROOT / 'qeli-openwrt/build/build_openwrt.py')
MODULES = (KEEN, OPEN)

class RouterBuildTests(unittest.TestCase):
    def selected(self, module, arch='aarch64'):
        return {arch: module.TARGETS[arch]}

    def invoke_main(self, module, argv, **overrides):
        client = Mock()
        changes = dict(connect=Mock(return_value=client), restore_router_manifest=Mock(),
            sync_tree=Mock(return_value=1), ensure_toolchain=Mock(),
            restrict_router_crate_types=Mock(), build=Mock(return_value=0))
        if module is KEEN:
            changes['pull'] = Mock()
        changes.update(overrides)
        with patch.multiple(module, **changes), patch.object(sys, 'argv', [module.__file__, *argv]), contextlib.redirect_stdout(io.StringIO()):
            module.main()
        return client, changes

    def test_invalid_arch_and_extra_arguments_never_connect(self):
        for module in MODULES:
            for args in (['typo'], ['aarch64', 'mipsel'], ['--unknown']):
                with self.subTest(module=module.__name__, args=args):
                    connect = Mock(side_effect=AssertionError('SSH must not be attempted'))
                    with patch.object(module, 'connect', connect), patch.object(sys, 'argv', [module.__file__, *args]), contextlib.redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit) as result: module.main()
                    self.assertEqual(result.exception.code, 2)
                    connect.assert_not_called()

    def test_target_toolchain_and_zig_failures_propagate(self):
        for module in MODULES:
            for failed in ('rustup target add', 'cargo install --list', 'zig version'):
                with self.subTest(module=module.__name__, failed=failed):
                    def run(client, command, t=0):
                        if command.startswith(failed): return 17, 'fixture failure'
                        return 0, 'cargo-zigbuild v0.23.0:'
                    with patch.object(module, 'run', side_effect=run), contextlib.redirect_stdout(io.StringIO()):
                        with self.assertRaisesRegex(RuntimeError, 'rc=17'):
                            module.ensure_toolchain(Mock(), self.selected(module))

    def test_nightly_install_and_rust_src_failure_propagate(self):
        for module in MODULES:
            for failed in ('rustup toolchain install', 'rustup component add'):
                with self.subTest(module=module.__name__, failed=failed):
                    def run(client, command, t=0):
                        if command.startswith(failed): return 17, 'fixture failure'
                        return 0, 'stable-x86_64-unknown-linux-gnu'
                    with patch.object(module, 'run', side_effect=run):
                        with self.assertRaisesRegex(RuntimeError, 'rc=17'):
                            module.ensure_toolchain(Mock(), self.selected(module, 'mipsel'))

    def test_installer_failure_and_wrong_version_after_success_rejected(self):
        for module in MODULES:
            for failed_install in (True, False):
                def run(client, command, t=0):
                    if command.startswith('cargo install cargo-zigbuild'):
                        return (17, 'fixture failure') if failed_install else (0, '')
                    return 0, 'cargo-zigbuild v0.22.0:'
                with self.subTest(module=module.__name__, failed_install=failed_install), patch.object(module, 'run', side_effect=run):
                    with self.assertRaises(RuntimeError): module.ensure_toolchain(Mock(), self.selected(module))

    def test_non_mips_target_does_not_install_nightly(self):
        for module in MODULES:
            run = Mock(return_value=(0, 'cargo-zigbuild v0.23.0:'))
            with patch.object(module, 'run', run), contextlib.redirect_stdout(io.StringIO()):
                module.ensure_toolchain(Mock(), self.selected(module))
            self.assertFalse(any('nightly' in call.args[1] for call in run.call_args_list))

    def test_manifest_recovered_before_sync_and_restored_after_build(self):
        for module in MODULES:
            events = []
            restore = Mock(side_effect=lambda c: events.append('restore'))
            sync = Mock(side_effect=lambda c: events.append('sync') or 1)
            client, _ = self.invoke_main(module, ['--sync', 'aarch64'], restore_router_manifest=restore, sync_tree=sync)
            self.assertEqual(events, ['restore', 'sync', 'restore'])
            client.close.assert_called_once()

    def test_setup_and_sync_failure_always_close_connection(self):
        for module in MODULES:
            for failed in ('restore_router_manifest', 'sync_tree', 'ensure_toolchain'):
                client = Mock()
                with self.subTest(module=module.__name__, failed=failed):
                    with self.assertRaisesRegex(RuntimeError, 'fixture failure'):
                        self.invoke_main(module, ['--sync', 'aarch64'], connect=Mock(return_value=client),
                            **{failed: Mock(side_effect=RuntimeError('fixture failure'))})
                    client.close.assert_called_once()

    def test_cleanup_failure_still_closes_connection(self):
        for module in MODULES:
            client = Mock()
            with self.assertRaisesRegex(RuntimeError, 'restore failed'):
                self.invoke_main(module, ['aarch64'], connect=Mock(return_value=client),
                    restore_router_manifest=Mock(side_effect=[None, RuntimeError('restore failed')]))
            client.close.assert_called_once()

    def test_artifact_failure_cannot_report_success(self):
        for module in MODULES:
            client = Mock()
            failing = 'pull' if module is KEEN else 'build'
            with self.assertRaises(SystemExit) as result:
                self.invoke_main(module, ['aarch64'], connect=Mock(return_value=client),
                    **{failing: Mock(side_effect=IOError('SFTP read failed'))})
            self.assertEqual(result.exception.code, 1)
            client.close.assert_called_once()

    def test_failed_arch_does_not_prevent_other_selected_arch(self):
        for module in MODULES:
            client = Mock(); events = []
            def build(c, arch, *args):
                events.append(arch)
                if arch == 'aarch64': raise RuntimeError('fixture failure')
                return 0
            with self.assertRaises(SystemExit):
                self.invoke_main(module, [], connect=Mock(return_value=client), build=Mock(side_effect=build))
            self.assertEqual(events, list(module.TARGETS))
            client.close.assert_called_once()

    def transfer(self, module, client):
        if module is KEEN: module.pull(client, 'aarch64', module.TARGETS['aarch64'])
        else: module.build(client, 'aarch64', module.TARGETS['aarch64'][0], False)

    def test_verified_pull_success_mismatch_read_failure_and_empty_keep_previous(self):
        for module in MODULES:
            for mode in ('success', 'mismatch', 'read-failure', 'empty'):
                with self.subTest(module=module.__name__, mode=mode), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory); output = root / 'out'; output.mkdir()
                    name = 'qeli-client-keenetic-aarch64' if module is KEEN else 'qeli-client-openwrt-aarch64'
                    destination = output / name; destination.write_bytes(b'previous')
                    payload = b'fixture ELF'; digest = hashlib.sha256(payload).hexdigest()
                    if mode == 'empty': digest = hashlib.sha256(b'').hexdigest()
                    sf = Mock()
                    sf.open.return_value = io.BytesIO(b'different' if mode == 'mismatch' else payload)
                    if mode == 'read-failure': sf.open.side_effect = IOError('read failed')
                    client = Mock(); client.open_sftp.return_value = sf
                    with patch.multiple(module, REPO_ROOT=root, LOCAL_OUT=output), patch.object(module, 'remote_sha256', return_value=digest), patch.object(module, 'run', return_value=(0, '')), contextlib.redirect_stdout(io.StringIO()):
                        if mode == 'success':
                            self.transfer(module, client)
                            self.assertEqual(destination.read_bytes(), payload)
                        else:
                            with self.assertRaises((RuntimeError, IOError)): self.transfer(module, client)
                            self.assertEqual(destination.read_bytes(), b'previous')
                    if mode == 'empty': client.open_sftp.assert_not_called()
                    else: sf.close.assert_called_once()

    def test_sync_command_or_sftp_failure_propagates_and_closes_open_handle(self):
        for module in MODULES:
            client = Mock(); sf = Mock(); client.open_sftp.return_value = sf
            sf.put.side_effect = IOError('put failed')
            with patch.object(module, 'run', return_value=(17, 'cleanup failed')):
                with self.assertRaises(RuntimeError): module.sync_tree(client)
            client.open_sftp.assert_not_called()
            with patch.object(module, 'run', return_value=(0, '')):
                with self.assertRaisesRegex(IOError, 'put failed'): module.sync_tree(client)
            sf.close.assert_called_once()

    def test_sync_mkdir_denied_is_not_silently_accepted(self):
        for module in MODULES:
            client = Mock(); sf = Mock(); client.open_sftp.return_value = sf
            sf.stat.side_effect = IOError('stat denied'); sf.mkdir.side_effect = IOError('mkdir denied')
            with patch.object(module, 'run', return_value=(0, '')):
                with self.assertRaisesRegex(IOError, 'stat denied'): module.sync_tree(client)
            sf.put.assert_not_called(); sf.close.assert_called_once()

    def test_build_uses_locked_client_graph_for_each_target(self):
        for module in MODULES:
            for arch, selected in module.TARGETS.items():
                run = Mock(return_value=(17, 'build failed'))
                with patch.object(module, 'run', run), contextlib.redirect_stdout(io.StringIO()):
                    if module is KEEN: self.assertEqual(module.build(Mock(), arch, selected), 17)
                    else: self.assertEqual(module.build(Mock(), arch, *selected), 17)
                command = run.call_args.args[1]
                self.assertIn('--locked', command)
                self.assertIn('--no-default-features --features client-bin', command)
                self.assertIn('--bin qeli-client', command)

if __name__ == '__main__': unittest.main()
