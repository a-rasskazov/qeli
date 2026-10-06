#!/bin/sh
# Install on Keenetic/Entware from the staged release bundle. No automatic restart.
set -e
export PATH=/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin
PKGDIR="$(cd "$(dirname "$0")" && pwd)"
BIN_TMP=""; INIT_TMP=""; CONF_TMP=""; LIB_TMP=""; QELI_LOCK_HELD=0
cleanup() {
  for tmp in "$BIN_TMP" "$INIT_TMP" "$CONF_TMP" "$LIB_TMP"; do
    [ -z "$tmp" ] || rm -f "$tmp"
  done
  [ "$QELI_LOCK_HELD" != 1 ] || qeli_lock_release
}
trap cleanup 0
trap 'exit 1' HUP INT TERM

ARCH="$(opkg print-architecture | awk '{print $2}' | grep -E 'aarch64|mipsel|mips' | head -n1)"
echo "арка пакетов: ${ARCH:-неизвестна} (uname -m: $(uname -m))"
case "$ARCH" in
  *aarch64*) SUFFIX=aarch64 ;;
  *mipsel*) SUFFIX=mipsel ;;
  *) echo "арка '$ARCH' не поддерживается (big-endian mips не собирается)"; exit 1 ;;
esac
# Canonical names match build_keenetic.py; retain old manually prepared bundles.
BINSRC="$PKGDIR/qeli-client-keenetic-$SUFFIX"
[ -f "$BINSRC" ] || BINSRC="$PKGDIR/qeli-client-$SUFFIX"
[ -s "$BINSRC" ] || { echo "нет непустого бинарника для $SUFFIX рядом со скриптом"; exit 1; }
[ -s "$PKGDIR/S99qeli" ] || { echo "нет S99qeli рядом со скриптом"; exit 1; }
[ -s "$PKGDIR/lifecycle.sh" ] || { echo "нет lifecycle.sh рядом со скриптом"; exit 1; }
if [ ! -f /opt/etc/qeli/client.conf ]; then
  [ -s "$PKGDIR/client.conf.example" ] || { echo "нет client.conf.example"; exit 1; }
fi

. "$PKGDIR/lifecycle.sh" || exit 1
qeli_lock_acquire || exit 1

# mv to a directory moves the temp inside it and can falsely report publication.
for target in /opt/bin/qeli-client /opt/etc/init.d/S99qeli /opt/etc/qeli/client.conf /opt/etc/qeli/lifecycle.sh; do
  [ ! -d "$target" ] || { echo "qeli-client: publication target is a directory ($target)"; exit 1; }
done

# Stop using the installed template before replacing a running/uncertain generation.
for state in /opt/var/run/qeli-client.pid /opt/var/run/qeli-client.pid.*; do
  [ -e "$state" ] || continue
  echo "qeli-client: stop/review installed client before upgrade ($state)"; exit 1
done

# Mandatory package errors stop installation; no partial client publication follows.
opkg update
opkg install ip-full iptables
command -v ip >/dev/null 2>&1 && command -v iptables >/dev/null 2>&1 || {
  echo "обязательные команды ip/iptables недоступны после установки"; exit 1;
}
if ! command -v ip6tables >/dev/null 2>&1; then
  opkg install ip6tables || echo "ВНИМАНИЕ: ip6tables не установлен — проверь поддержку IPv6 перед запуском"
fi
[ -e /dev/net/tun ] || echo "ВНИМАНИЕ: нет /dev/net/tun — включи компонент VPN в KeeneticOS"

mkdir -p /opt/bin /opt/etc/init.d /opt/etc/qeli /opt/var/log /opt/var/run
chmod 700 /opt/etc/qeli
# Prepare every copy before replacing installed files. Each rename is atomic;
# publication of the whole bundle is not a transaction.
BIN_TMP="$(mktemp /opt/bin/.qeli-client.XXXXXX)"
INIT_TMP="$(mktemp /opt/etc/init.d/.S99qeli.XXXXXX)"
LIB_TMP="$(mktemp /opt/etc/qeli/.lifecycle.XXXXXX)"
install -m755 "$BINSRC" "$BIN_TMP"
install -m755 "$PKGDIR/S99qeli" "$INIT_TMP"
install -m600 "$PKGDIR/lifecycle.sh" "$LIB_TMP"
if [ ! -f /opt/etc/qeli/client.conf ]; then
  CONF_TMP="$(mktemp /opt/etc/qeli/.client.conf.XXXXXX)"
  install -m600 "$PKGDIR/client.conf.example" "$CONF_TMP"
  mv -f "$CONF_TMP" /opt/etc/qeli/client.conf
  CONF_TMP=""
  echo "положил болванку /opt/etc/qeli/client.conf — ОТРЕДАКТИРУЙ её"
else
  chmod 600 /opt/etc/qeli/client.conf
fi
mv -f "$LIB_TMP" /opt/etc/qeli/lifecycle.sh
LIB_TMP=""
mv -f "$BIN_TMP" /opt/bin/qeli-client
BIN_TMP=""
mv -f "$INIT_TMP" /opt/etc/init.d/S99qeli
INIT_TMP=""

echo
echo "Готово. Дальше:"
echo "  1) vi /opt/etc/qeli/client.conf   # server/user/pass/key/mode + ipv6/gateway/dns"
echo "  2) /opt/etc/init.d/S99qeli start"
echo "  3) tail -f /opt/var/log/qeli-client.log   # ищи 'Auth OK'"
