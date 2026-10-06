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
    /// Validate INI and print core/legacy gateway ownership, then exit without connecting.
    #[arg(long)]
    print_gateway_owner: bool,
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
    if cli.print_gateway_owner {
        println!("{}", qeli::client::inspect_gateway_owner(&cli.config)?);
        return Ok(());
    }

    let (level, log_file, time_format) = qeli::client::peek_logging(&cli.config);
    init_logging(&level, log_file.as_deref(), &time_format);

    let config_str = cli.config.to_str().ok_or_else(|| {
        anyhow::anyhow!("config path is not valid UTF-8: {}", cli.config.display())
    })?;
    log::info!("Starting qeli client with config: {}", cli.config.display());
    qeli::client::run_client(config_str).await
}

#[cfg(test)]
mod gateway_owner_tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};
    static NEXT: AtomicUsize = AtomicUsize::new(0);
    const BASE: &str = "[qeli]\nserver=192.0.2.1:443\nmode=plain\nbind_static=false\ngateway=false\nuser=fixture\npass=canary-secret\n";
    struct Fixture(PathBuf);
    impl Fixture {
        fn new(text: &str) -> Self {
            let path = std::env::temp_dir().join(format!(
                "qeli-gateway-owner-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
            std::fs::write(&path, text).unwrap();
            Self(path)
        }
        fn owner(&self) -> anyhow::Result<&'static str> {
            qeli::client::inspect_gateway_owner(&self.0)
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }
    #[test]
    fn metadata_cli_flag_is_accepted_without_starting_client() {
        let args = Cli::try_parse_from([
            "qeli-client",
            "--config",
            "fixture.ini",
            "--print-gateway-owner",
        ])
        .unwrap();
        assert!(args.print_gateway_owner);
        assert_eq!(args.config, PathBuf::from("fixture.ini"));
    }
    #[test]
    fn all_core_gateway_flags_suppress_legacy_ownership() {
        for key in ["gateway_nat", "forward", "exit_node"] {
            assert_eq!(
                Fixture::new(&format!("{BASE}{key}=true\n"))
                    .owner()
                    .unwrap(),
                "core",
                "{key}"
            );
        }
    }
    #[test]
    fn quoted_uppercase_bom_and_on_values_use_canonical_parser() {
        for value in ["true", "TRUE", "on", "YES", "1", "\"TrUe\"", "\"ON\""] {
            let text = format!(
                "\u{feff}{}{value}\n",
                BASE.replace("[qeli]", "[QELI]") + "GATEWAY_NAT = "
            );
            assert_eq!(Fixture::new(&text).owner().unwrap(), "core", "{value}");
        }
    }
    #[test]
    fn absent_and_false_flags_keep_explicit_legacy_fallback() {
        assert_eq!(Fixture::new(BASE).owner().unwrap(), "legacy");
        for value in ["false", "OFF", "0", "\"No\""] {
            assert_eq!(
                Fixture::new(&format!("{BASE}gateway_nat={value}\n"))
                    .owner()
                    .unwrap(),
                "legacy"
            );
        }
    }
    #[test]
    fn invalid_bool_unknown_duplicate_and_conflicting_flags_reject() {
        for extra in [
            "gateway_nat=maybe",
            "gateway_nat=true\ngateway_nat=false",
            "unknown_option=true",
            "exit_node=true\nforward=true",
        ] {
            assert!(
                Fixture::new(&format!("{BASE}{extra}\n")).owner().is_err(),
                "{extra}"
            );
        }
    }
    #[test]
    fn file_hooks_are_never_executed_by_inspection() {
        let marker = Fixture::new("");
        std::fs::remove_file(&marker.0).unwrap();
        let config = Fixture::new(&format!("{BASE}post_up=touch {}\n", marker.0.display()));
        assert_eq!(config.owner().unwrap(), "legacy");
        assert!(!marker.0.exists());
    }
    #[test]
    fn missing_file_and_nonregular_directory_reject() {
        let fixture = Fixture::new(BASE);
        std::fs::remove_file(&fixture.0).unwrap();
        assert!(fixture.owner().is_err());
        assert!(qeli::client::inspect_gateway_owner(&std::env::temp_dir()).is_err());
    }
    #[test]
    fn oversized_file_is_rejected_by_shared_bound() {
        let fixture = Fixture::new("");
        std::fs::OpenOptions::new()
            .write(true)
            .open(&fixture.0)
            .unwrap()
            .set_len(qeli::transport_core::MAX_CONFIG_BYTES as u64 + 1)
            .unwrap();
        assert!(fixture.owner().is_err());
    }
}
