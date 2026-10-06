# Shared POSIX lifecycle exclusion for Keenetic init, wan.d and installation.
# A stale directory is deliberately retained after SIGKILL/power loss: never
# guess whether another owner is still active or remove somebody else's lock.
QELI_LOCK_DIR=/var/run/qeli.lifecycle.lock
QELI_LOCK_HELD=0
qeli_lock_acquire() {
  (umask 077; mkdir -p "${QELI_LOCK_DIR%/*}" && mkdir "$QELI_LOCK_DIR") || {
    echo "qeli-client: lifecycle busy or stale lock ($QELI_LOCK_DIR); retry/review required" >&2
    return 1
  }
  QELI_LOCK_HELD=1
}
qeli_lock_release() {
  [ "$QELI_LOCK_HELD" = 1 ] || return 0
  rmdir "$QELI_LOCK_DIR" || {
    echo "qeli-client: lifecycle lock release failed ($QELI_LOCK_DIR)" >&2
    return 1
  }
  QELI_LOCK_HELD=0
}

# A failed installer may leave a mixed code bundle. Stop remains available;
# admission is only for start/wan.d/install, and older scripts do not cooperate.
QELI_INSTALL_PENDING=/opt/etc/qeli/install-pending
qeli_install_ready() {
  [ ! -e "$QELI_INSTALL_PENDING" ] && [ ! -L "$QELI_INSTALL_PENDING" ] || {
    echo "qeli-client: installation pending; review recovery state ($QELI_INSTALL_PENDING)" >&2
    return 1
  }
}
