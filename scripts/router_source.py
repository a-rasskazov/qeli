"""Shared managed-source sync for maintainer-only router build helpers.
Source replacement is fail-closed for later helper runs, not atomic or locked.
"""
import posixpath
from pathlib import Path
import shlex
from native_lab import LabConnection, sync_qeli_source


def _marker(remote_root):
    if not remote_root.startswith('/') or remote_root == '/' or '..' in remote_root.split('/'):
        raise ValueError(f'unsafe remote source root: {remote_root!r}')
    return posixpath.join(remote_root, '.router-sync-incomplete')


def require_router_source_ready(client, remote_root):
    marker = _marker(remote_root)
    LabConnection(client).checked(
        f'test ! -e {shlex.quote(marker)}',
        'router source sync incomplete; rerun with --sync', timeout=30)


def sync_router_source(client, local_root, remote_root):
    marker = _marker(remote_root)
    local_root = Path(local_root)
    # Check mandatory local inputs before any destructive remote operation.
    for relative in ('src/client_main.rs', '.cargo/config.toml', 'Cargo.toml', 'Cargo.lock'):
        if not (local_root / relative).is_file():
            raise RuntimeError(f'router build input is missing: {local_root / relative}')
    connection = LabConnection(client)
    connection.checked(
        f'mkdir -p {shlex.quote(remote_root)} && '
        f'(umask 077; : > {shlex.quote(marker)})',
        'mark router source sync incomplete', timeout=30)
    sftp = connection.open_sftp()
    try:
        count = sync_qeli_source(connection, sftp, local_root, remote_root)
    finally:
        sftp.close()
    # Every failure above preserves the marker, including SFTP close failure.
    connection.checked(f'rm -f {shlex.quote(marker)}', 'finish router source sync', timeout=30)
    return count
