use tokio::net::TcpStream;

/// Enable TCP keepalive on `stream` with `secs` idle time.
///
/// The fine-grained idle/interval/count knobs (`TCP_KEEPIDLE`/`TCP_KEEPINTVL`/
/// `TCP_KEEPCNT`) are Linux-only. On other targets this is a best-effort no-op so
/// the crate still compiles — qeli's daemon/CLI ship for Linux (incl. Keenetic
/// musl), and the desktop clients are C# and never reach this path.
#[cfg(target_os = "linux")]
pub fn set_tcp_keepalive(stream: &TcpStream, secs: u64) -> std::io::Result<()> {
    use std::os::fd::AsRawFd;
    // 0 = leave keepalive at the OS default (don't enable). Setting TCP_KEEPIDLE
    // to 0 returns EINVAL, which previously broke every connection when the
    // config's keepalive_secs was missing/zero.
    if secs == 0 {
        return Ok(());
    }
    let fd = stream.as_raw_fd();
    let keepalive: libc::c_int = 1;
    let keepidle: libc::c_int = secs as libc::c_int;
    let keepintvl: libc::c_int = (secs / 3).max(10) as libc::c_int;
    let keepcnt: libc::c_int = 3;
    unsafe {
        if libc::setsockopt(
            fd,
            libc::SOL_SOCKET,
            libc::SO_KEEPALIVE,
            &keepalive as *const _ as *const libc::c_void,
            std::mem::size_of_val(&keepalive) as libc::socklen_t,
        ) != 0
        {
            return Err(std::io::Error::last_os_error());
        }
        if libc::setsockopt(
            fd,
            libc::IPPROTO_TCP,
            libc::TCP_KEEPIDLE,
            &keepidle as *const _ as *const libc::c_void,
            std::mem::size_of_val(&keepidle) as libc::socklen_t,
        ) != 0
        {
            return Err(std::io::Error::last_os_error());
        }
        if libc::setsockopt(
            fd,
            libc::IPPROTO_TCP,
            libc::TCP_KEEPINTVL,
            &keepintvl as *const _ as *const libc::c_void,
            std::mem::size_of_val(&keepintvl) as libc::socklen_t,
        ) != 0
        {
            return Err(std::io::Error::last_os_error());
        }
        if libc::setsockopt(
            fd,
            libc::IPPROTO_TCP,
            libc::TCP_KEEPCNT,
            &keepcnt as *const _ as *const libc::c_void,
            std::mem::size_of_val(&keepcnt) as libc::socklen_t,
        ) != 0
        {
            return Err(std::io::Error::last_os_error());
        }
    }
    Ok(())
}

/// Non-Linux fallback: `TCP_KEEPIDLE`/`INTVL`/`CNT` don't exist, so keepalive
/// tuning is skipped (best-effort). Keeps a non-Linux build compiling.
#[cfg(not(target_os = "linux"))]
pub fn set_tcp_keepalive(_stream: &TcpStream, _secs: u64) -> std::io::Result<()> {
    Ok(())
}

/// Set the socket send/receive buffers (`SO_SNDBUF` / `SO_RCVBUF`).
///
/// `0` for either size leaves the kernel default (and its auto-tuning) alone —
/// that is the sane default, since Linux grows these dynamically. Raising them
/// only helps on a high bandwidth-delay-product path, where the default ceiling
/// caps a single connection's throughput; that is exactly the long-haul case
/// qeli is used for, which is why the knob exists.
///
/// Note the kernel doubles what you ask for (bookkeeping overhead), so reading
/// the value back reports ~2x the requested size. Best-effort: a failure here
/// degrades throughput, never correctness, so callers ignore the result.
#[cfg(target_os = "linux")]
pub fn set_tcp_buffers(stream: &TcpStream, send: u32, recv: u32) -> std::io::Result<()> {
    use std::os::fd::AsRawFd;
    let fd = stream.as_raw_fd();
    for (opt, size) in [(libc::SO_SNDBUF, send), (libc::SO_RCVBUF, recv)] {
        if size == 0 {
            continue;
        }
        let val = size.min(libc::c_int::MAX as u32) as libc::c_int;
        // SAFETY: fd is owned by `stream` and outlives the call; val is a valid
        // c_int and the length matches its size.
        unsafe {
            if libc::setsockopt(
                fd,
                libc::SOL_SOCKET,
                opt,
                &val as *const _ as *const libc::c_void,
                std::mem::size_of_val(&val) as libc::socklen_t,
            ) != 0
            {
                return Err(std::io::Error::last_os_error());
            }
        }
    }
    Ok(())
}

/// Non-Linux fallback — see [`set_tcp_keepalive`].
#[cfg(not(target_os = "linux"))]
pub fn set_tcp_buffers(_stream: &TcpStream, _send: u32, _recv: u32) -> std::io::Result<()> {
    Ok(())
}

/// Same as [`set_tcp_buffers`], for a UDP socket — and far more load-bearing there.
///
/// TCP autotunes its buffers between the `tcp_rmem`/`tcp_wmem` bounds, so leaving it alone
/// is usually right. **UDP has no autotuning at all**: the socket keeps whatever
/// `net.core.rmem_default` was at creation (208 KB on a stock kernel), which at tunnel
/// speeds is only tens of milliseconds of traffic. One scheduling stall and the kernel
/// silently drops datagrams — and each dropped datagram is a lost TCP segment *inside* the
/// tunnel, so the inner connection halves its window. Measured on a live server, that cost
/// half the achievable throughput until the buffer was raised.
///
/// `0` leaves the kernel default. Best-effort, exactly like the TCP version: a failure
/// degrades throughput, never correctness.
#[cfg(target_os = "linux")]
pub fn set_udp_buffers(sock: &tokio::net::UdpSocket, send: u32, recv: u32) -> std::io::Result<()> {
    use std::os::fd::AsRawFd;
    let fd = sock.as_raw_fd();
    for (opt, size) in [(libc::SO_SNDBUF, send), (libc::SO_RCVBUF, recv)] {
        if size == 0 {
            continue;
        }
        let val = size.min(libc::c_int::MAX as u32) as libc::c_int;
        // SAFETY: fd is owned by `sock` and outlives the call; val is a valid c_int and the
        // length matches its size.
        unsafe {
            if libc::setsockopt(
                fd,
                libc::SOL_SOCKET,
                opt,
                &val as *const _ as *const libc::c_void,
                std::mem::size_of_val(&val) as libc::socklen_t,
            ) != 0
            {
                return Err(std::io::Error::last_os_error());
            }
        }
    }
    Ok(())
}

/// Non-Linux fallback — see [`set_udp_buffers`].
#[cfg(not(target_os = "linux"))]
pub fn set_udp_buffers(
    _sock: &tokio::net::UdpSocket,
    _send: u32,
    _recv: u32,
) -> std::io::Result<()> {
    Ok(())
}
