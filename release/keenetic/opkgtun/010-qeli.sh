#!/bin/sh
# /opt/etc/ndm/wan.d/010-qeli.sh — регистрация qeli-tun как нативного OpkgTun-интерфейса
# ndm (KeeneticOS 5.0+), чтобы он был виден в вебморде и доступен в «Приоритетах
# подключений» / статических маршрутах.
#
# Вызывается САМИМ ndm на сетевых событиях → ndmc работает в правильном контексте.
# (Из init.d / non-login shell ndmc падает с `ndmc: system failed [0xcffd0060]`,
# поэтому регистрация живёт здесь, а не в S99qeli.)
#
# ТРЕБУЕТ в client.conf: dev = opkgtun0 И dev_attach = true — qeli ПРИЦЕПЛЯЕТСЯ к
# созданному ndm устройству и НЕ трогает L3. Всё остальное (адрес/линк/маршруты) держит
# ndm — иначе интерфейс залипает в `connected: no` и ndm не маршрутит через него.
#
# МОДЕЛЬ (KeenOS 5.0), критично соблюсти порядок и владение:
#   (1) ndm создаёт интерфейс OpkgTun0 → появляется kernel-device opkgtun0;
#   (2) qeli цепляется к нему (dev_attach), при auth пишет выданный сервером IP в TUNIP;
#   (3) ndm ставит этот IP как /32 + global + up → connected: yes → маршрутизация работает.
# Если L3 поставит qeli, а не ndm — ndm застрянет в `link: pending / connected: no`
# (проверено на устройстве). Если qeli сам СОЗДАСТ opkgtun0 — ndm даст `system failed
# [0xcffd00a9]`. Хук идемпотентен; ndm дёргает wan.d на событиях → регистрация докручивается.

STATE=/opt/var/run/qeli.opkgtun          # маркер: S99qeli пишет сюда имя tun в OpkgTun-режиме
TUNIP=/opt/var/run/qeli.tunip            # qeli пишет сюда выданный сервером IP (attach-режим)
PENDING="$STATE.apply-pending"           # incomplete apply must always retry
APPLIED="$STATE.applied"                 # complete IF + NetworkPlan after checked save
LOG=/opt/var/log/qeli-client.log
export PATH=/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin

[ -f "$STATE" ] || exit 0                 # OpkgTun-режим в S99qeli выключен — выходим тихо
IF="$(cat "$STATE" 2>/dev/null)"          # имя kernel-tun (напр. opkgtun0)
case "$IF" in opkgtun*) ;; *) exit 1 ;; esac
SUFFIX="${IF#opkgtun}"
case "$SUFFIX" in ''|*[!0-9]*) exit 1 ;; esac
[ "${#IF}" -le 15 ] || exit 1
NDM_IF="OpkgTun$SUFFIX"             # opkgtun0 -> OpkgTun0 (ndm капитализирует)

# Разведка формата событий (раскомментируй ОДИН раз на устройстве, потом верни назад):
# { echo "--- wan.d/010-qeli $(date) ---"; env; } >> "$LOG" 2>&1

# Адреса, которые qeli выдал сервер. Новый формат содержит family=address/prefix;
# первая строка остаётся legacy primary address для старых хуков.
# Capture one atomically published file, so its families/MTU are from one read.
read_plan() {
  PLAN="$(cat "$TUNIP" 2>/dev/null)" || PLAN=""
  WANT_IP="$(printf '%s\n' "$PLAN" | sed -n 's/^ipv4=\([^/]*\)\/.*/\1/p' | head -n1)"
  [ -n "$WANT_IP" ] || WANT_IP="$(printf '%s\n' "$PLAN" | grep -oE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -n1)"
  WANT_IP6_CIDR="$(printf '%s\n' "$PLAN" | sed -n 's/^ipv6=//p' | head -n1)"
  WANT_IP6="${WANT_IP6_CIDR%/*}"
}
read_plan

# Only our last complete, saved application can qualify a no-op. Addresses alone
# cannot prove that MTU/MSS/global/security/save completed, or that the plan is new.
# Compare literal address tokens, never regexes or substrings (10.8.0.2 != .20).
address_present() {
  printf '%s\n' "$CUR" | awk -v want="$1" '
    { for (i=1; i<=NF; i++) { split($i, token, "/"); if (token[1]==want) found=1 } }
    END { exit !found }'
}
EXPECTED="$(printf '%s\n%s\n' "$IF" "$PLAN")"
CUR="$(ndmc -c "show interface $NDM_IF" 2>/dev/null)"; SHOW_RC=$?
if [ "$SHOW_RC" -eq 0 ] && [ ! -e "$PENDING" ] \
   && { [ -n "$WANT_IP" ] || [ -n "$WANT_IP6" ]; } \
   && [ "$(cat "$APPLIED" 2>/dev/null)" = "$EXPECTED" ] \
   && printf '%s\n' "$CUR" | awk '$1=="connected:" && $2=="yes" && NF==2 {found=1} END {exit !found}' \
   && { [ -z "$WANT_IP" ] || address_present "$WANT_IP"; } \
   && { [ -z "$WANT_IP6" ] || address_present "$WANT_IP6"; }; then
  exit 0
fi

# (1) Убеждаемся, что интерфейс есть в ndm (заводит kernel-device opkgtun0 для attach'а qeli).
# Создание идемпотентно; если интерфейс УЖЕ существует (персистентный конфиг / ndm его
# пере-инициализирует после реконнекта qeli), ndmc может вернуть не-ноль — это НЕ ошибка,
# поэтому фатально считаем только реальное отсутствие интерфейса (show тоже не находит).
ndmc -c "interface $NDM_IF" >/dev/null 2>&1
if ! ndmc -c "show interface $NDM_IF" >/dev/null 2>&1; then
  echo "wan.d/010-qeli: $NDM_IF недоступен в ndm (KeeneticOS <5.0? не тот контекст?)" >> "$LOG"
  exit 0
fi

# (2) Ждём, пока qeli приатачится и запишет выданный сервером IPv4 в TUNIP-файл.
# В attach-режиме qeli НЕ ставит адрес сам (иначе ndm застрянет в connected:no), поэтому
# IP берём из файла, а не с интерфейса. Таймаут короткий, чтобы не блокировать обработчик
# событий ndm — если qeli ещё в backoff, регистрацию докрутит следующий вызов хука.
i=0; IP="$WANT_IP"; IP6="$WANT_IP6"; IP6_CIDR="$WANT_IP6_CIDR"
while [ -z "$IP" ] && [ -z "$IP6" ] && [ $i -lt 10 ]; do
  read_plan
  IP="$WANT_IP"; IP6="$WANT_IP6"; IP6_CIDR="$WANT_IP6_CIDR"
  if [ -n "$IP" ] || [ -n "$IP6" ]; then
    break
  fi
  i=$((i + 1)); sleep 1
done
[ -n "$IP" ] || [ -n "$IP6" ] || { echo "wan.d/010-qeli: $NDM_IF создан, ждём attach qeli (нет IP в $TUNIP)" >> "$LOG"; exit 0; }

MTU="$(printf '%s\n' "$PLAN" | sed -n 's/^mtu=\([0-9][0-9]*\)$/\1/p' | head -n1)"
case "$MTU" in
  ''|*[!0-9]*) MTU=1400 ;;
  *) [ "$MTU" -ge 576 ] && [ "$MTU" -le 16602 ] || MTU=1400 ;;
esac

# (3) Ставим L3 через ndm — ndm ДОЛЖЕН владеть адресом/линком, иначе connected:no и нет
# маршрутизации. Команды декларативные → повторный вызов с теми же значениями безопасен.
# `ip global auto` = «для выхода в интернет» (без него маршруты через интерфейс не идут).
# `security-level public` = ndm сам делает masquerade/firewall (свой NAT не нужен).
# Глобальный default здесь не ставим: без отдельного bypass для адреса qeli-сервера
# он заворачивает несущее соединение в сам туннель. Policy-routing включается в Keenetic UI,
# где ndm может атомарно учесть приоритеты и исключения.
ndm_apply() {
  ndmc -c "$1" || {
    echo "wan.d/010-qeli: ndm rejected configuration for $NDM_IF; retry required" >> "$LOG"
    return 1
  }
}
# Persist retry intent before the first mutation; normal failure leaves it intact.
(umask 077; : > "$PENDING") || exit 1
ndm_apply "interface $NDM_IF description qeli-VPN" || exit 1
ndm_apply "interface $NDM_IF ip global auto" || exit 1
[ -z "$IP" ] || ndm_apply "interface $NDM_IF ip address $IP 255.255.255.255" || exit 1
[ -z "$IP6_CIDR" ] || ndm_apply "interface $NDM_IF ipv6 address $IP6_CIDR" || exit 1
ndm_apply "interface $NDM_IF ip mtu $MTU" || exit 1
ndm_apply "interface $NDM_IF ip tcp adjust-mss pmtu" || exit 1
ndm_apply "interface $NDM_IF security-level public" || exit 1
ndm_apply "interface $NDM_IF up" || exit 1
ndm_apply "system configuration save" || exit 1
# The private sibling is published only after every mutation and save succeeded.
# A publication/removal failure retains PENDING so matching addresses cannot hide it.
APPLIED_TMP="$(umask 077; mktemp "$APPLIED.XXXXXX")" || exit 1
if [ -d "$APPLIED" ] || ! chmod 600 "$APPLIED_TMP" \
   || ! printf '%s\n%s\n' "$IF" "$PLAN" > "$APPLIED_TMP" \
   || ! mv -f "$APPLIED_TMP" "$APPLIED"; then
  rm -f "$APPLIED_TMP"
  exit 1
fi
rm -f "$PENDING" || exit 1
echo "wan.d/010-qeli: $NDM_IF up (IPv4=${IP:-none}, IPv6=${IP6:-none}, mtu $MTU) — L3 держит ndm" >> "$LOG"
