//! Standalone qeli **client** binary for routers (Keenetic / Entware) and any
//! headless Linux client. It drives only the `client` data plane — no server, no
//! web admin, no `rustls`/`ring` — so it cross-compiles to mipsel/aarch64 musl.
//!
//! Built ONLY under the off-by-default `client-bin` feature (see Cargo.toml and
//! docs/*/reference/KEENETIC-PORT.md):
//!
//! ```sh
//! cargo build --release --bin qeli-client \
//!   --no-default-features --features client-bin --target <TARGET>
//! ```
//!
//! The full `qeli` daemon (server + client + web) is still `src/main.rs`.

#[cfg(not(target_os = "linux"))]
compile_error!("qeli-client is Linux-only (it creates a TUN device via /dev/net/tun)");

use clap::Parser;
use qeli_core as qeli;
use std::path::PathBuf;

#[derive(Parser)]
#[command(
    name = "qeli-client",
    about = "Obfuscated VPN client (router/headless build)",
    version
)]
struct Cli {
    /// Client config (flat-INI, `[qeli]` section). Default suits Entware layout.
    #[arg(short, long, default_value = "/opt/etc/qeli/client.conf")]
    config: PathBuf,
}

fn init_logging(level: &str, file: Option<&str>, time_format: &str) {
    let mut builder =
        env_logger::Builder::from_env(env_logger::Env::default().default_filter_or(level));
    // Same line shape as the server, and the same `[logging] time_format` values.
    // On a router `time_format = none` is the useful one: procd/logread already
    // stamps every line, so the app timestamp is duplicated noise.
    let tf = time_format.to_string();
    builder.format(move |buf, record| {
        use std::io::Write;
        let ts = qeli::util::log_timestamp(&tf);
        if ts.is_empty() {
            writeln!(
                buf,
                "{:<5} {}: {}",
                record.level(),
                record.target(),
                record.args()
            )
        } else {
            writeln!(
                buf,
                "{} {:<5} {}: {}",
                ts,
                record.level(),
                record.target(),
                record.args()
            )
        }
    });
    if let Some(path) = file {
        match qeli::client::open_log_file(std::path::Path::new(path)) {
            Ok(f) => {
                builder.target(env_logger::Target::Pipe(Box::new(f)));
            }
            Err(e) => {
                eprintln!("qeli-client: cannot open log file {path}: {e} — logging to stderr")
            }
        }
    }
    builder.init();
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    let (level, log_file, time_format) = qeli::client::peek_logging(&cli.config);
    init_logging(&level, log_file.as_deref(), &time_format);

    let config_str = cli.config.to_str().ok_or_else(|| {
        anyhow::anyhow!("config path is not valid UTF-8: {}", cli.config.display())
    })?;
    log::info!("Starting qeli client with config: {}", cli.config.display());
    qeli::client::run_client(config_str).await
}
