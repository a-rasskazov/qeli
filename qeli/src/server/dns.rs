use crate::config::server::DnsConfig;
use crate::server::ServerState;
use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::net::{TcpListener, UdpSocket};
use tokio::sync::{OwnedSemaphorePermit, RwLock, Semaphore};

/// (response_bytes, inserted_at, ttl), keyed by the txid-normalised query.
///
/// The TTL is PER ENTRY, taken from the record itself (S-14). It used to be one global
/// `dns.timeout_secs` for everything, which is not a caching policy at all: a record the
/// zone says is valid for 5 s was served stale for the whole timeout, and a record valid
/// for a day was re-queried just as often. `timeout_secs` is a network timeout; reusing it
/// as a cache lifetime conflated two unrelated settings.
pub type DnsCache = Arc<RwLock<HashMap<Vec<u8>, (Vec<u8>, Instant, Duration)>>>;

/// Floor/ceiling on a record-derived cache lifetime. The floor keeps a zone that publishes
/// TTL 0/1 from turning the cache into a no-op (and us into an amplifier of upstream
/// load); the ceiling stops a record with a week-long TTL pinning a stale answer after a
/// real IP change.
const MIN_CACHE_TTL: Duration = Duration::from_secs(5);
const MAX_CACHE_TTL: Duration = Duration::from_secs(3600);

/// Advance past a (possibly compressed) name; returns the offset just after it.
///
/// Module-level rather than nested inside `answer_min_ttl`: walking a DNS message is needed by
/// every section-aware helper here (the EDNS0 payload size, the question boundary), and three
/// private copies of a bounds-checked parser is three chances to get one of them wrong.
fn skip_name(msg: &[u8], mut pos: usize) -> Option<usize> {
    // Bounded: a malformed message must not spin here.
    for _ in 0..128 {
        let len = *msg.get(pos)?;
        if len & 0xC0 == 0xC0 {
            return pos.checked_add(2).filter(|p| *p <= msg.len()); // pointer ends the name
        }
        if len == 0 {
            return pos.checked_add(1);
        }
        pos = pos.checked_add(1 + len as usize)?;
    }
    None
}

/// Smallest TTL across the ANSWER section, or `None` when the message carries no answers
/// (NXDOMAIN / NODATA) or is malformed.
///
/// Walks names rather than assuming a fixed offset: DNS names are label sequences that may
/// end in a compression pointer, so the record header is not at a predictable position.
/// Only the ANSWER section is read — the OPT pseudo-record in ADDITIONAL stores extended
/// flags in its TTL field, so including it would produce a nonsense lifetime.
fn answer_min_ttl(msg: &[u8]) -> Option<u32> {
    if msg.len() < 12 {
        return None;
    }
    let qdcount = u16::from_be_bytes([msg[4], msg[5]]) as usize;
    let ancount = u16::from_be_bytes([msg[6], msg[7]]) as usize;
    if ancount == 0 {
        return None;
    }
    let mut pos = 12;
    for _ in 0..qdcount {
        pos = skip_name(msg, pos)?.checked_add(4)?; // QTYPE + QCLASS
    }
    let mut min = u32::MAX;
    for _ in 0..ancount {
        pos = skip_name(msg, pos)?;
        if pos.checked_add(10)? > msg.len() {
            return None;
        }
        let ttl = u32::from_be_bytes([msg[pos + 4], msg[pos + 5], msg[pos + 6], msg[pos + 7]]);
        let rdlen = u16::from_be_bytes([msg[pos + 8], msg[pos + 9]]) as usize;
        min = min.min(ttl);
        pos = pos.checked_add(10)?.checked_add(rdlen)?;
    }
    Some(min)
}

/// Upper bound on in-flight query TASKS. The permit is taken in the accept loop
/// BEFORE spawning (see the loop below), so a flood is bounded by refusing to
/// start work rather than by parking an unbounded number of started tasks.
const MAX_INFLIGHT: usize = 512;

/// Bind the proxy's listen socket, SEPARATELY from serving on it.
///
/// The bind used to happen inside the detached serve task, so a port already taken — the
/// common case, a host resolver on `0.0.0.0:53` covering the TUN address — surfaced as one
/// ERROR line while the profile came up regardless and handed every client the address of a
/// resolver that does not exist. Names then simply stopped resolving with nothing pointing at
/// the cause. Binding here lets the caller fail the profile BEFORE it advertises a resolver it
/// cannot provide. (Audit 2026-08-01, §4.)
pub async fn bind_dns_proxy(dns_cfg: &DnsConfig) -> anyhow::Result<UdpSocket> {
    let bind_addr = crate::util::join_host_port(&dns_cfg.listen, dns_cfg.port);
    UdpSocket::bind(&bind_addr)
        .await
        .map_err(|e| anyhow::anyhow!("DNS proxy cannot bind {bind_addr}: {e}"))
}

/// Bind the TCP half of the resolver, on the same address and port as the UDP one.
///
/// DNS over TCP is not an optional extra: RFC 7766 makes it a REQUIREMENT for every resolver,
/// and it is what a client does after receiving a truncated answer. Without it this proxy could
/// not honestly set TC — telling a client "ask again over TCP" while listening on UDP alone
/// would have turned every oversized answer into a failed lookup, which is why the UDP path
/// used to forward answers whole regardless of size. Binding it is what makes the TC path in
/// `apply_udp_size_limit` truthful. (Audit 2026-08-01, §10.)
pub async fn bind_dns_proxy_tcp(dns_cfg: &DnsConfig) -> anyhow::Result<TcpListener> {
    let bind_addr = crate::util::join_host_port(&dns_cfg.listen, dns_cfg.port);
    TcpListener::bind(&bind_addr)
        .await
        .map_err(|e| anyhow::anyhow!("DNS proxy cannot bind {bind_addr}/tcp: {e}"))
}

/// Serve DNS over TCP: length-prefixed messages (RFC 1035 §4.2.2), one task per connection,
/// sharing the blocklist, cache and upstream policy with the UDP path via [`resolve`].
pub async fn run_dns_proxy_tcp(
    dns_cfg: DnsConfig,
    listener: TcpListener,
    cache: DnsCache,
    pref: Arc<AtomicUsize>,
) -> anyhow::Result<()> {
    use tokio::io::{AsyncReadExt, AsyncWriteExt};

    let cfg = Arc::new(dns_cfg);
    // The same in-flight bound as UDP, for the same reason: a flood must be refused rather
    // than parked. TCP additionally bounds itself by the accept queue.
    let sem = Arc::new(Semaphore::new(MAX_INFLIGHT));
    loop {
        let (mut stream, _peer) = match listener.accept().await {
            Ok(v) => v,
            Err(e) => {
                log::warn!("DNS proxy (tcp) accept error: {} — continuing", e);
                continue;
            }
        };
        let Ok(permit) = sem.clone().try_acquire_owned() else {
            continue; // at capacity: dropping the connection is the bound
        };
        let cache = cache.clone();
        let cfg = cfg.clone();
        let pref = pref.clone();
        tokio::spawn(async move {
            let _permit = permit;
            // One deadline for the whole exchange, so a client that connects and then stalls
            // cannot hold a slot open.
            let deadline = Duration::from_secs(cfg.timeout_secs.max(1));
            let exchange = async {
                // RFC 7766 allows several queries per connection; serve until the peer closes.
                loop {
                    let mut len_buf = [0u8; 2];
                    if stream.read_exact(&mut len_buf).await.is_err() {
                        return; // clean close or a broken peer — either way, done
                    }
                    let qlen = u16::from_be_bytes(len_buf) as usize;
                    if qlen < 12 {
                        return; // shorter than a DNS header
                    }
                    let mut query = vec![0u8; qlen];
                    if stream.read_exact(&mut query).await.is_err() {
                        return;
                    }
                    let Some(resp) = resolve(cache.clone(), cfg.clone(), pref.clone(), &query).await
                    else {
                        return;
                    };
                    // Over TCP the answer goes out WHOLE — no size limit and no TC; that is the
                    // entire point of the client having retried here.
                    let Ok(len) = u16::try_from(resp.len()) else {
                        return;
                    };
                    let mut framed = Vec::with_capacity(2 + resp.len());
                    framed.extend_from_slice(&len.to_be_bytes());
                    framed.extend_from_slice(&resp);
                    if stream.write_all(&framed).await.is_err() {
                        return;
                    }
                }
            };
            let _ = tokio::time::timeout(deadline, exchange).await;
        });
    }
}

pub async fn run_dns_proxy(
    _state: Arc<ServerState>,
    dns_cfg: DnsConfig,
    bound: UdpSocket,
    cache: DnsCache,
    pref: Arc<AtomicUsize>,
) -> anyhow::Result<()> {
    let bind_addr = crate::util::join_host_port(&dns_cfg.listen, dns_cfg.port);
    // Shared listen socket: query tasks send their answers back through it.
    let socket = Arc::new(bound);
    log::info!("DNS proxy listening on {}", bind_addr);

    let cfg = Arc::new(dns_cfg);
    let sem = Arc::new(Semaphore::new(MAX_INFLIGHT));
    // Count of queries refused because the in-flight gate was full (for rate-limited logging).
    let dropped = Arc::new(AtomicU64::new(0));
    // 4 KiB, matching the reply buffer, NOT 1500.
    //
    // `recv_from` on a UDP socket DISCARDS whatever does not fit — silently, with no error and
    // no short-read signal. A client that advertises a larger EDNS0 payload and then sends a
    // query bigger than 1500 (a DNSSEC-signed UPDATE, a large TSIG, a long TXT lookup) had its
    // datagram chopped mid-message and the truncated remains forwarded upstream, which either
    // FORMERRs or answers the wrong question. The reply path was already widened for exactly
    // this reason (S-14); the query path was left at an Ethernet-sized guess.
    // (Audit 2026-08-01, §10.)
    let mut buf = vec![0u8; 4096];
    loop {
        let (n, src) = match socket.recv_from(&mut buf).await {
            Ok(v) => v,
            Err(e) => {
                // A transient recv error must not tear down the whole DNS proxy for the
                // profile (mirrors the UDP data-plane worker's log-and-continue).
                log::warn!("DNS proxy recv error: {} — continuing", e);
                continue;
            }
        };
        // A valid DNS message has at least the 12-byte header.
        if n < 12 {
            continue;
        }
        // Take the in-flight permit HERE, before spawning. Acquiring it inside the task
        // (as this did) bounds only the upstream work: the spawn itself always succeeds,
        // so a flood piles up an unbounded number of tasks, each parked on the semaphore
        // while holding its own copy of the datagram — memory grows without limit even
        // though "in-flight" looks capped. Refusing to start the task is the actual bound;
        // a dropped UDP query is retried by the client, an OOM is not. (S-02)
        let permit = match sem.clone().try_acquire_owned() {
            Ok(p) => p,
            Err(_) => {
                // Rate-limited: under a flood this fires on every packet otherwise.
                let n = dropped.fetch_add(1, Ordering::Relaxed) + 1;
                if n % 1000 == 1 {
                    log::warn!(
                        "DNS proxy: {} in-flight queries — dropping (total dropped: {})",
                        MAX_INFLIGHT,
                        n
                    );
                }
                continue;
            }
        };
        let query = buf[..n].to_vec();
        // Each query is handled on its own task so a slow/unreachable upstream
        // can't stall every other client's lookup (the old single-socket loop
        // blocked the whole proxy on each query — head-of-line blocking).
        let socket = socket.clone();
        let cache = cache.clone();
        let cfg = cfg.clone();
        let pref = pref.clone();
        tokio::spawn(async move {
            handle_query(socket, cache, cfg, permit, pref, query, src).await;
        });
    }
}

/// One DNS query over TCP (RFC 1035 §4.2.2: each message is prefixed with its 2-byte
/// big-endian length). Used both when `dns.upstream_protocol = tcp` and as the retry
/// path when a UDP answer comes back truncated. Returns the raw response message, or
/// `None` on any timeout/IO/protocol error — the caller then falls back. (S-14)
///
/// The whole exchange shares one deadline, so a resolver that accepts the connection and
/// then stalls cannot hold the task (and its in-flight permit) open.
async fn query_tcp(addr: &str, query: &[u8], timeout: Duration) -> Option<Vec<u8>> {
    use tokio::io::{AsyncReadExt, AsyncWriteExt};

    let deadline = tokio::time::Instant::now() + timeout;
    let remaining =
        |d: tokio::time::Instant| d.saturating_duration_since(tokio::time::Instant::now());

    let mut stream =
        match tokio::time::timeout(remaining(deadline), tokio::net::TcpStream::connect(addr)).await
        {
            Ok(Ok(s)) => s,
            _ => return None,
        };

    // Length-prefixed request.
    let len = u16::try_from(query.len()).ok()?;
    let mut framed = Vec::with_capacity(2 + query.len());
    framed.extend_from_slice(&len.to_be_bytes());
    framed.extend_from_slice(query);
    if tokio::time::timeout(remaining(deadline), stream.write_all(&framed))
        .await
        .ok()?
        .is_err()
    {
        return None;
    }

    // Length-prefixed response. The 2-byte prefix is what makes the >512-byte answers
    // that triggered the TCP retry readable in the first place.
    let mut len_buf = [0u8; 2];
    if tokio::time::timeout(remaining(deadline), stream.read_exact(&mut len_buf))
        .await
        .ok()?
        .is_err()
    {
        return None;
    }
    let resp_len = u16::from_be_bytes(len_buf) as usize;
    if resp_len < 12 {
        return None; // shorter than a DNS header — not a usable message
    }
    let mut resp = vec![0u8; resp_len];
    if tokio::time::timeout(remaining(deadline), stream.read_exact(&mut resp))
        .await
        .ok()?
        .is_err()
    {
        return None;
    }
    Some(resp)
}

#[allow(clippy::too_many_arguments)]
async fn handle_query(
    socket: Arc<UdpSocket>,
    cache: DnsCache,
    cfg: Arc<DnsConfig>,
    // Held for the whole task and released on return — the caller acquired it before
    // spawning us, so the number of live tasks is what MAX_INFLIGHT actually bounds. (S-02)
    _permit: OwnedSemaphorePermit,
    pref: Arc<AtomicUsize>,
    query: Vec<u8>,
    src: SocketAddr,
) {
    let Some(resp) = resolve(cache, cfg, pref, &query).await else {
        return;
    };
    // Only the UDP path has a size limit to respect; over TCP the answer goes out whole.
    let out = apply_udp_size_limit(&query, resp);
    let _ = socket.send_to(&out, src).await;
}

/// Answer one query, from the blocklist, the cache or an upstream — transport-agnostic.
///
/// Split out of `handle_query` so the TCP listener can share every bit of policy (blocklist,
/// cache, upstream selection and failover, cache admission). The alternative — a second copy
/// for TCP — is how two paths end up disagreeing about which names are blocked.
async fn resolve(
    cache: DnsCache,
    cfg: Arc<DnsConfig>,
    pref: Arc<AtomicUsize>,
    query: &[u8],
) -> Option<Vec<u8>> {
    let query = query.to_vec();
    let query_txid = [query[0], query[1]];

    if is_blocked(&query, &cfg.blocklist) {
        let mut nxdomain = query.clone();
        nxdomain[2] = 0x81;
        nxdomain[3] = 0x83;
        return Some(nxdomain);
    }

    // Cache key ignores the per-query transaction ID (bytes 0..2) so the same
    // question shares one entry regardless of txid.
    let mut cache_key = query.clone();
    cache_key[0] = 0;
    cache_key[1] = 0;

    let ttl = Duration::from_secs(cfg.timeout_secs);
    let cached = {
        let cache_read = cache.read().await;
        cache_read
            .get(&cache_key)
            .and_then(|(resp, time, entry_ttl)| {
                // Per-entry lifetime from the record, not the global network timeout. (S-14)
                if time.elapsed() < *entry_ttl {
                    Some(resp.clone())
                } else {
                    None
                }
            })
    };
    if let Some(mut response) = cached {
        if response.len() >= 2 {
            response[0] = query_txid[0];
            response[1] = query_txid[1];
        }
        return Some(response);
    }

    let upstreams = &cfg.upstream;
    if upstreams.is_empty() {
        return None;
    }

    // (The in-flight permit is already held — acquired by the accept loop before spawn.)
    // A fresh ephemeral socket per query: no cross-query demux, so one slow
    // resolver only delays its own task.
    let upstream_sock = match UdpSocket::bind("0.0.0.0:0").await {
        Ok(s) => s,
        Err(e) => {
            log::debug!("DNS: cannot open upstream socket: {}", e);
            return None;
        }
    };

    // `dns.upstream_protocol` was parsed, serialized back out and shown in the panel, but
    // NOTHING read it — every query went out over UDP regardless. An operator who set
    // `tcp` (e.g. because the network mangles UDP/53) got silent UDP anyway. (S-14)
    let force_tcp = cfg.upstream_protocol.eq_ignore_ascii_case("tcp");

    let start = pref.load(Ordering::Relaxed) % upstreams.len();
    let mut response = None;
    for attempt in 0..upstreams.len() {
        let idx = (start + attempt) % upstreams.len();
        let upstream_addr = format!("{}:53", upstreams[idx]);
        let upstream_ip = match upstream_addr.parse::<SocketAddr>() {
            Ok(sa) => sa.ip(),
            Err(_) => continue,
        };
        if force_tcp {
            if let Some(full) = query_tcp(&upstream_addr, &query, ttl).await {
                // Same anti-spoof txid check as the UDP path (TCP is connection-bound, so
                // the source is implicitly the resolver we dialled).
                if full.len() >= 12 && full[0] == query_txid[0] && full[1] == query_txid[1] {
                    response = Some(full);
                    pref.store(idx, Ordering::Relaxed);
                    break;
                }
            }
            continue;
        }
        if upstream_sock.send_to(&query, &upstream_addr).await.is_err() {
            continue;
        }
        // Accept only a reply that (a) came from the resolver we queried and (b)
        // carries the matching transaction ID — otherwise an off-/on-path spoof
        // could poison the cache. Bound the total wait by the configured timeout.
        let deadline = tokio::time::Instant::now() + ttl;
        // 4 KiB, not 1500: with EDNS0 the client can advertise a larger UDP payload and the
        // resolver will use it. `recv_from` DISCARDS whatever does not fit the buffer, so a
        // 1500-byte buffer silently chopped such a reply and forwarded a malformed answer —
        // no error anywhere, just a broken lookup. 4096 covers the common advertisements
        // (1232/4096); anything beyond still arrives truncated at the DNS level and is
        // handled by the TC path above. (S-14)
        let mut resp_buf = vec![0u8; 4096];
        loop {
            let remaining = deadline.saturating_duration_since(tokio::time::Instant::now());
            if remaining.is_zero() {
                break;
            }
            match tokio::time::timeout(remaining, upstream_sock.recv_from(&mut resp_buf)).await {
                Ok(Ok((m, from))) => {
                    if from.ip() != upstream_ip {
                        continue; // not from the queried resolver — ignore
                    }
                    if m < 12 || resp_buf[0] != query_txid[0] || resp_buf[1] != query_txid[1] {
                        continue; // wrong/short txid — spoof or stale, ignore
                    }
                    // TC (TRUNCATED, bit 1 of byte 2): the answer did not fit in a UDP
                    // datagram and the resolver sent a stub. Forwarding it as-is made the
                    // client see an empty/partial answer set — the classic "big TXT or
                    // DNSSEC record silently resolves to nothing". RFC 1035 §4.2.1 says to
                    // retry over TCP; nothing here did. (S-14)
                    if resp_buf[2] & 0x02 != 0 {
                        log::debug!(
                            "DNS: truncated reply from {} — retrying over TCP",
                            upstream_ip
                        );
                        if let Some(full) = query_tcp(&upstream_addr, &query, ttl).await {
                            response = Some(full);
                            pref.store(idx, Ordering::Relaxed);
                            break;
                        }
                        // TCP retry failed — fall through and use the truncated answer
                        // rather than nothing (a stub reply still carries the header flags).
                    }
                    response = Some(resp_buf[..m].to_vec());
                    pref.store(idx, Ordering::Relaxed);
                    break;
                }
                _ => break, // timeout or socket error → try next upstream
            }
        }
        if response.is_some() {
            break;
        }
    }

    if let Some(resp) = response {
        // Cache lifetime from the record itself, clamped. A TTL of 0 means "do not cache"
        // (RFC 2181 §8) and is honoured by skipping the insert entirely — it is used for
        // things like round-robin load balancing, where caching defeats the point. With no
        // ANSWER section (NXDOMAIN/NODATA) there is no record TTL to read; those fall back
        // to the configured timeout rather than being cached indefinitely. (S-14)
        let entry_ttl = match answer_min_ttl(&resp) {
            Some(0) => {
                return Some(resp); // uncacheable by policy — answer, don't store
            }
            Some(secs) => Duration::from_secs(secs as u64).clamp(MIN_CACHE_TTL, MAX_CACHE_TTL),
            None => ttl,
        };

        let mut cache_write = cache.write().await;
        if cache_write.len() >= cfg.cache_size {
            // Drop expired entries first (cheap win). If the cache is still full of
            // FRESH entries, evict a batch of arbitrary keys so we make real room —
            // otherwise every insert at steady-state saturation would re-scan the
            // whole map (O(n)) and free nothing, stalling all DNS tasks. Batching
            // amortizes the scan over ~cache_size/10 inserts.
            let now = Instant::now();
            cache_write.retain(|_, (_, time, entry_ttl)| now.duration_since(*time) < *entry_ttl);
            if cache_write.len() >= cfg.cache_size {
                let evict = (cfg.cache_size / 10).max(1);
                let victims: Vec<_> = cache_write.keys().take(evict).cloned().collect();
                for k in victims {
                    cache_write.remove(&k);
                }
            }
        }
        if cache_write.len() < cfg.cache_size {
            cache_write.insert(cache_key, (resp.clone(), Instant::now(), entry_ttl));
        }
        return Some(resp);
    }
    None
}

/// The UDP payload size the client said it can accept: its EDNS0 OPT record, or the 512-byte
/// floor from RFC 1035 §4.2.1 when it sent no OPT at all.
fn advertised_udp_size(query: &[u8]) -> usize {
    const FLOOR: usize = 512;
    // OPT lives in the ADDITIONAL section, and its CLASS field carries the payload size
    // (RFC 6891 §6.1.2) rather than a class. Walking there means stepping over every earlier
    // section, so a malformed query simply falls back to the floor.
    let Some(pos) = additional_section_start(query) else {
        return FLOOR;
    };
    let arcount = u16::from_be_bytes([query[10], query[11]]) as usize;
    let mut pos = pos;
    for _ in 0..arcount {
        // An OPT record's NAME is always root (a single 0 byte), but skip_name handles the
        // general case and keeps this honest against a compressed pointer.
        let after_name = match skip_name(query, pos) {
            Some(p) => p,
            None => return FLOOR,
        };
        if after_name + 10 > query.len() {
            return FLOOR;
        }
        let rtype = u16::from_be_bytes([query[after_name], query[after_name + 1]]);
        let class = u16::from_be_bytes([query[after_name + 2], query[after_name + 3]]);
        if rtype == 41 {
            // Clamp: a peer may advertise anything, and this bounds the buffer we honour.
            return (class as usize).clamp(FLOOR, 4096);
        }
        let rdlen = u16::from_be_bytes([query[after_name + 8], query[after_name + 9]]) as usize;
        pos = match after_name.checked_add(10).and_then(|p| p.checked_add(rdlen)) {
            Some(p) => p,
            None => return FLOOR,
        };
    }
    FLOOR
}

/// Offset of the first ADDITIONAL record, stepping over the question, answer and authority
/// sections. `None` on anything malformed.
fn additional_section_start(msg: &[u8]) -> Option<usize> {
    if msg.len() < 12 {
        return None;
    }
    let qdcount = u16::from_be_bytes([msg[4], msg[5]]) as usize;
    let ancount = u16::from_be_bytes([msg[6], msg[7]]) as usize;
    let nscount = u16::from_be_bytes([msg[8], msg[9]]) as usize;
    let mut pos = 12usize;
    for _ in 0..qdcount {
        pos = skip_name(msg, pos)?.checked_add(4)?; // QTYPE + QCLASS
    }
    for _ in 0..(ancount + nscount) {
        pos = skip_name(msg, pos)?;
        if pos.checked_add(10)? > msg.len() {
            return None;
        }
        let rdlen = u16::from_be_bytes([msg[pos + 8], msg[pos + 9]]) as usize;
        pos = pos.checked_add(10)?.checked_add(rdlen)?;
    }
    Some(pos)
}

/// Cut a UDP reply down to what the client said it can take, setting TC so it knows to ask
/// again over TCP.
///
/// This proxy used to forward the answer WHOLE however large it was, because setting TC without
/// a TCP listener would have sent the client to a port where nothing answers — a working lookup
/// turned into a failing one. Now that the listener exists, TC means what it says.
///
/// The truncated message is header + question with all three record counts zeroed, not the
/// original bytes cut short: chopping mid-record leaves counts promising records that are not
/// there, which a resolver reads as a malformed message rather than as "retry over TCP".
fn apply_udp_size_limit(query: &[u8], resp: Vec<u8>) -> Vec<u8> {
    let limit = advertised_udp_size(query);
    if resp.len() <= limit {
        return resp;
    }
    // Question section only; if it cannot be located, fall back to a bare header.
    let q_end = question_section_end(query).unwrap_or(12).min(query.len());
    let mut out = Vec::with_capacity(q_end);
    out.extend_from_slice(&query[..q_end]);
    out[2] |= 0x80; // QR: this is a response
    out[2] |= 0x02; // TC: truncated — ask again over TCP
    out[3] &= 0xF0; // RCODE = NOERROR; the truncation itself is not an error
    // QDCOUNT is left alone on purpose — the question IS carried, and a resolver matches the
    // truncated reply to its outstanding query by it.
    out[6..8].copy_from_slice(&0u16.to_be_bytes()); // ANCOUNT
    out[8..10].copy_from_slice(&0u16.to_be_bytes()); // NSCOUNT
    out[10..12].copy_from_slice(&0u16.to_be_bytes()); // ARCOUNT (the OPT is dropped with it)
    out
}

/// Offset just past the question section.
fn question_section_end(msg: &[u8]) -> Option<usize> {
    if msg.len() < 12 {
        return None;
    }
    let qdcount = u16::from_be_bytes([msg[4], msg[5]]) as usize;
    let mut pos = 12usize;
    for _ in 0..qdcount {
        pos = skip_name(msg, pos)?.checked_add(4)?;
    }
    if pos > msg.len() {
        return None;
    }
    Some(pos)
}

fn is_blocked(query: &[u8], blocklist: &[String]) -> bool {
    if blocklist.is_empty() || query.len() < 12 {
        return false;
    }

    let mut labels = Vec::new();
    let mut pos = 12;

    while pos < query.len() {
        let label_len = query[pos] as usize;
        if label_len == 0 {
            break;
        }
        pos += 1;
        if pos + label_len <= query.len() {
            if let Ok(label) = std::str::from_utf8(&query[pos..pos + label_len]) {
                labels.push(label.to_string());
            }
        }
        pos += label_len;
    }

    let domain = labels.join(".").to_lowercase();
    blocklist.iter().any(|blocked| {
        let blocked_lower = blocked.to_lowercase();
        domain == blocked_lower || domain.ends_with(&format!(".{}", blocked_lower))
    })
}

#[cfg(test)]
mod tests {
    //! Coverage for the answer-TTL parser (S-14). It walks attacker-influenced bytes —
    //! an upstream reply is untrusted input — so the cases that matter are the malformed
    //! ones: it must return None, never panic or loop.
    use super::*;

    /// Build a minimal DNS response: one question, `answers` A-records with the given TTLs.
    fn response(ttls: &[u32], compressed_names: bool) -> Vec<u8> {
        let mut m = vec![0u8; 12];
        m[0] = 0xAB;
        m[1] = 0xCD; // txid
        m[2] = 0x81;
        m[3] = 0x80; // response, no error
        m[4] = 0;
        m[5] = 1; // QDCOUNT = 1
        m[6] = 0;
        m[7] = ttls.len() as u8; // ANCOUNT
                                 // Question: "example.com" A IN
        m.extend_from_slice(&[7]);
        m.extend_from_slice(b"example");
        m.extend_from_slice(&[3]);
        m.extend_from_slice(b"com");
        m.push(0);
        m.extend_from_slice(&[0, 1, 0, 1]); // QTYPE=A, QCLASS=IN
        for ttl in ttls {
            if compressed_names {
                m.extend_from_slice(&[0xC0, 0x0C]); // pointer back to the question name
            } else {
                m.extend_from_slice(&[7]);
                m.extend_from_slice(b"example");
                m.extend_from_slice(&[3]);
                m.extend_from_slice(b"com");
                m.push(0);
            }
            m.extend_from_slice(&[0, 1, 0, 1]); // TYPE=A, CLASS=IN
            m.extend_from_slice(&ttl.to_be_bytes());
            m.extend_from_slice(&[0, 4]); // RDLENGTH
            m.extend_from_slice(&[93, 184, 216, 34]); // RDATA
        }
        m
    }

    #[test]
    fn reads_the_smallest_answer_ttl() {
        assert_eq!(answer_min_ttl(&response(&[300], false)), Some(300));
        assert_eq!(answer_min_ttl(&response(&[300, 60, 900], false)), Some(60));
    }

    #[test]
    fn follows_compressed_names() {
        // The common real-world shape: answers point back at the question's name.
        assert_eq!(answer_min_ttl(&response(&[120, 45], true)), Some(45));
    }

    #[test]
    fn no_answers_yields_none() {
        // NXDOMAIN / NODATA — nothing to derive a lifetime from.
        assert_eq!(answer_min_ttl(&response(&[], false)), None);
    }

    #[test]
    fn malformed_input_never_panics() {
        // Truncated at every possible length: each must be rejected, not crash.
        let full = response(&[300, 60], true);
        for cut in 0..full.len() {
            let _ = answer_min_ttl(&full[..cut]);
        }
        // Header claims answers that are not there.
        let mut lying = response(&[300], false);
        lying[7] = 200;
        assert_eq!(answer_min_ttl(&lying), None);
        // A name length that runs past the buffer.
        let mut runaway = response(&[300], false);
        let qname = 12;
        runaway[qname] = 0xFF;
        assert_eq!(answer_min_ttl(&runaway), None);
        // Compression pointer loop: must terminate (the pointer is not followed, so this
        // is really a check that a pointer always ends the name walk).
        let mut looped = response(&[300], true);
        looped[12] = 0xC0;
        looped[13] = 0x0C;
        let _ = answer_min_ttl(&looped);
        assert_eq!(answer_min_ttl(&[]), None);
        assert_eq!(answer_min_ttl(&[0u8; 11]), None);
    }

    #[test]
    fn ttl_zero_is_distinguishable() {
        // Some(0) must survive to the caller so it can skip caching entirely.
        assert_eq!(answer_min_ttl(&response(&[0], false)), Some(0));
    }

    /// A query with no OPT record, and one advertising `payload` bytes via EDNS0.
    fn query(payload: Option<u16>) -> Vec<u8> {
        let mut m = vec![0u8; 12];
        m[0] = 0xAB;
        m[1] = 0xCD;
        m[5] = 1; // QDCOUNT = 1
        m.extend_from_slice(&[7]);
        m.extend_from_slice(b"example");
        m.extend_from_slice(&[3]);
        m.extend_from_slice(b"com");
        m.push(0);
        m.extend_from_slice(&[0, 1, 0, 1]); // QTYPE=A, QCLASS=IN
        if let Some(size) = payload {
            m[11] = 1; // ARCOUNT = 1
            m.push(0); // OPT NAME = root
            m.extend_from_slice(&[0, 41]); // TYPE = OPT (41)
            m.extend_from_slice(&size.to_be_bytes()); // CLASS carries the payload size
            m.extend_from_slice(&[0, 0, 0, 0]); // TTL (extended rcode + flags)
            m.extend_from_slice(&[0, 0]); // RDLENGTH
        }
        m
    }

    /// The size a client says it can take governs whether the answer is truncated, and RFC 1035
    /// §4.2.1's 512 is the floor when it says nothing at all.
    #[test]
    fn the_advertised_udp_size_comes_from_the_opt_record() {
        assert_eq!(advertised_udp_size(&query(None)), 512);
        assert_eq!(advertised_udp_size(&query(Some(1232))), 1232);
        // Clamped at both ends: a peer may advertise anything, and this bounds what we honour.
        assert_eq!(advertised_udp_size(&query(Some(128))), 512);
        assert_eq!(advertised_udp_size(&query(Some(65535))), 4096);
        // Malformed input falls back to the floor rather than panicking.
        let full = query(Some(4096));
        for cut in 0..full.len() {
            let _ = advertised_udp_size(&full[..cut]);
        }
    }

    /// An answer that fits is forwarded untouched; one that does not comes back as a TC=1
    /// header plus the question, NOT as the original bytes cut short.
    ///
    /// Chopping mid-record would leave the counts promising records that are not present, which
    /// a resolver reads as a malformed message rather than as "retry over TCP" — and retrying
    /// over TCP is the whole point, now that there is a TCP listener to retry against.
    /// (Audit 2026-08-01, §10.)
    #[test]
    fn an_oversized_answer_is_truncated_with_tc_set() {
        let q = query(Some(512));
        // Fits: byte-for-byte the same object comes back.
        let small = response(&[300], true);
        assert!(small.len() <= 512);
        assert_eq!(apply_udp_size_limit(&q, small.clone()), small);

        // Does not fit: 40 A-records is well past 512 bytes.
        let big = response(&[300; 40], true);
        assert!(big.len() > 512);
        let out = apply_udp_size_limit(&q, big);
        assert!(out.len() <= 512, "the reply must fit what the client advertised");
        assert_eq!(&out[0..2], &q[0..2], "the txid must match the query");
        assert_eq!(out[2] & 0x80, 0x80, "QR must say this is a response");
        assert_eq!(out[2] & 0x02, 0x02, "TC must be set");
        assert_eq!(out[3] & 0x0F, 0, "RCODE must stay NOERROR");
        assert_eq!(
            u16::from_be_bytes([out[4], out[5]]),
            1,
            "the question is carried, so QDCOUNT stays 1"
        );
        for (label, off) in [("ANCOUNT", 6), ("NSCOUNT", 8), ("ARCOUNT", 10)] {
            assert_eq!(
                u16::from_be_bytes([out[off], out[off + 1]]),
                0,
                "{label} must be zero — no records are carried"
            );
        }
        // The question section itself survives intact, so a resolver can match the reply.
        assert_eq!(&out[12..], &q[12..12 + (out.len() - 12)]);

        // A client that advertised room for it gets the whole thing instead.
        let big = response(&[300; 40], true);
        let roomy = query(Some(4096));
        assert!(big.len() <= 4096);
        assert_eq!(apply_udp_size_limit(&roomy, big.clone()), big);
    }
}
