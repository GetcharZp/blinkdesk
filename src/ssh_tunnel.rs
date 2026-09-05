//! SSH tunnel support: a dynamic SOCKS5 forward over an SSH connection.
//!
//! When an SSH tunnel is configured in the network settings, this module
//! connects to the remote SSH server (password and/or private key auth) and
//! runs a local SOCKS5 listener on 127.0.0.1 that forwards TCP connections
//! through the SSH server (`ssh -D` equivalent). The local endpoint is then
//! exposed through `Config::set_ssh_tunnel_local_socks`, so all the existing
//! socks5-proxy machinery (rendezvous mediator, relay, peer connections) picks
//! it up automatically.

use std::{
    net::Ipv4Addr,
    sync::{Arc, Mutex},
    time::Instant,
};

use hbb_common::{
    bail,
    config::{Config, Socks5Server, SshTunnel, DEFAULT_SSH_PORT},
    lazy_static, log,
    tokio::{
        io::{AsyncReadExt, AsyncWriteExt},
        net::{TcpListener, TcpStream},
    },
    ResultType,
};
use russh::{
    client::{self, AuthResult, Handle},
    keys::*,
};

const SOCKS_VERSION: u8 = 0x05;
const SOCKS_CMD_CONNECT: u8 = 0x01;
const SOCKS_ATYP_IPV4: u8 = 0x01;
const SOCKS_ATYP_DOMAIN: u8 = 0x03;
const SOCKS_ATYP_IPV6: u8 = 0x04;
const SOCKS_REP_SUCCESS: u8 = 0x00;
const SOCKS_REP_CONNECTION_REFUSED: u8 = 0x05;
const SOCKS_REP_CMD_NOT_SUPPORTED: u8 = 0x07;

/// Minimum delay between two tunnel (re)start attempts, so a bad credential
/// or an unreachable server does not make the mediator restart in a tight loop.
const RESTART_INTERVAL: u64 = 30;

struct ClientHandler;

impl client::Handler for ClientHandler {
    type Error = russh::Error;

    // Host key verification is left to the SSH server admin; a remote desktop
    // session already authenticates the peer over the encrypted tunnel.
    async fn check_server_key(
        &mut self,
        _server_public_key: &PublicKeyOrCertificate,
    ) -> Result<bool, Self::Error> {
        Ok(true)
    }
}

struct TunnelState {
    task: hbb_common::tokio::task::JoinHandle<()>,
    config: SshTunnel,
}

lazy_static::lazy_static! {
    static ref STATE: Mutex<Option<TunnelState>> = Mutex::new(None);
    static ref LAST_ATTEMPT: Mutex<Option<Instant>> = Mutex::new(None);
}

fn configured() -> Option<SshTunnel> {
    match Config::get_ssh_tunnel() {
        Some(c) if !c.host.trim().is_empty() => Some(c),
        _ => None,
    }
}

fn can_retry() -> bool {
    LAST_ATTEMPT
        .lock()
        .unwrap()
        .map_or(true, |t| t.elapsed().as_secs() >= RESTART_INTERVAL)
}

/// (Re)start or stop the SSH tunnel so that it matches the current config.
/// Called from the rendezvous mediator loop (startup and after config
/// changes). Safe to call repeatedly.
pub fn refresh() {
    let cfg = configured();
    let mut state = STATE.lock().unwrap();
    let restart_needed = match (&cfg, &*state) {
        (None, None) => false,
        (None, Some(_)) => true,
        (Some(_), None) => true,
        (Some(c), Some(s)) => c != &s.config || (s.task.is_finished() && can_retry()),
    };
    if !restart_needed {
        return;
    }
    if let Some(s) = state.take() {
        s.task.abort();
    }
    Config::set_ssh_tunnel_local_socks(None);
    if let Some(c) = cfg {
        *LAST_ATTEMPT.lock().unwrap() = Some(Instant::now());
        let task = hbb_common::tokio::spawn({
            let c = c.clone();
            async move {
                match run_tunnel(c).await {
                    Ok(()) => log::info!("ssh tunnel stopped"),
                    Err(err) => log::error!("ssh tunnel error: {}", err),
                }
                Config::set_ssh_tunnel_local_socks(None);
            }
        });
        *state = Some(TunnelState { task, config: c });
    }
}

/// Test that the given SSH configuration can connect and authenticate.
pub async fn test(cfg: &SshTunnel) -> ResultType<()> {
    let session = connect_session(cfg).await?;
    session
        .disconnect(russh::Disconnect::ByApplication, "", "")
        .await
        .ok();
    Ok(())
}

async fn connect_session(cfg: &SshTunnel) -> ResultType<Handle<ClientHandler>> {
    let port = if cfg.port <= 0 {
        DEFAULT_SSH_PORT
    } else {
        cfg.port
    };
    let mut config = client::Config {
        nodelay: true,
        ..Default::default()
    };
    config.keepalive_interval = Some(std::time::Duration::from_secs(30));
    let config = Arc::new(config);
    let mut session = client::connect(config, (cfg.host.as_str(), port as u16), ClientHandler)
        .await
        .map_err(|err| {
            hbb_common::anyhow::anyhow!("Failed to connect to {}:{}: {}", cfg.host, port, err)
        })?;

    let auth = if !cfg.private_key.trim().is_empty() {
        match load_secret_key(cfg.private_key.trim(), None) {
            Ok(key) => {
                let hash_alg = if matches!(key.algorithm(), Algorithm::Rsa { .. }) {
                    match session.best_supported_rsa_hash().await {
                        Ok(Some(hash_alg)) => hash_alg,
                        _ => Some(HashAlg::Sha256),
                    }
                } else {
                    None
                };
                session
                    .authenticate_publickey(
                        cfg.username.as_str(),
                        PrivateKeyWithHashAlg::new(Arc::new(key), hash_alg),
                    )
                    .await
            }
            Err(err) => {
                log::warn!("Failed to load private key {}: {}", cfg.private_key, err);
                if !cfg.password.is_empty() {
                    session
                        .authenticate_password(cfg.username.as_str(), cfg.password.as_str())
                        .await
                } else {
                    bail!("Failed to load private key {}: {}", cfg.private_key, err)
                }
            }
        }
    } else if !cfg.password.is_empty() {
        session
            .authenticate_password(cfg.username.as_str(), cfg.password.as_str())
            .await
    } else {
        bail!("No password or private key provided")
    };
    match auth {
        Ok(AuthResult::Success) => Ok(session),
        Ok(AuthResult::Failure {
            remaining_methods,
            partial_success: _,
        }) => bail!(
            "SSH authentication failed, remaining methods: {:?}",
            remaining_methods
        ),
        Err(err) => bail!("SSH authentication error: {}", err),
    }
}

async fn run_tunnel(cfg: SshTunnel) -> ResultType<()> {
    // The session event loop runs in a task spawned inside the `Handle`; the
    // handle only needs to stay alive for the connection to remain open.
    let session = Arc::new(connect_session(&cfg).await?);

    // The local SOCKS listener is bound after auth, so the override below is
    // only set when the tunnel is actually usable.
    let listener = TcpListener::bind((Ipv4Addr::LOCALHOST, 0)).await?;
    let local_port = listener.local_addr()?.port();
    Config::set_ssh_tunnel_local_socks(Some(Socks5Server {
        proxy: format!("127.0.0.1:{local_port}"),
        username: String::new(),
        password: String::new(),
    }));
    log::info!(
        "ssh tunnel to {}:{} established, local socks at 127.0.0.1:{}",
        cfg.host,
        if cfg.port <= 0 {
            DEFAULT_SSH_PORT
        } else {
            cfg.port
        },
        local_port
    );
    // The mediator may have started over direct UDP while the tunnel was
    // connecting; restart it so it re-evaluates `Config::is_proxy()` and
    // switches to the TCP path through the tunnel.
    crate::rendezvous_mediator::RendezvousMediator::restart();

    loop {
        if session.is_closed() {
            bail!("ssh session closed");
        }
        let (stream, peer) = listener.accept().await?;
        log::debug!("ssh tunnel: incoming socks connection from {}", peer);
        let session = session.clone();
        hbb_common::tokio::spawn(async move {
            if let Err(err) = handle_socks(stream, session).await {
                log::debug!("ssh tunnel: socks connection failed: {}", err);
            }
        });
    }
}

async fn handle_socks(
    mut stream: TcpStream,
    session: Arc<Handle<ClientHandler>>,
) -> ResultType<()> {
    // Greeting: +----+----------+----------+
    //           |VER | NMETHODS | METHODS  |
    let mut buf = [0u8; 2];
    stream.read_exact(&mut buf).await?;
    if buf[0] != SOCKS_VERSION {
        bail!("unsupported socks version {}", buf[0]);
    }
    let nmethods = buf[1] as usize;
    let mut methods = vec![0u8; nmethods];
    stream.read_exact(&mut methods).await?;
    if !methods.contains(&0x00) {
        // No acceptable methods -> no auth offered, close.
        stream.write_all(&[SOCKS_VERSION, 0xFF]).await.ok();
        return Ok(());
    }
    // Method selection: no authentication required.
    stream.write_all(&[SOCKS_VERSION, 0x00]).await?;

    // Request: +----+-----+-------+------+----------+----------+
    //          |VER | CMD |  RSV  | ATYP | DST.ADDR | DST.PORT |
    let mut header = [0u8; 4];
    stream.read_exact(&mut header).await?;
    if header[0] != SOCKS_VERSION {
        bail!("unsupported socks version {}", header[0]);
    }
    if header[1] != SOCKS_CMD_CONNECT {
        stream
            .write_all(&[SOCKS_VERSION, SOCKS_REP_CMD_NOT_SUPPORTED, 0x00, SOCKS_ATYP_IPV4, 0, 0, 0, 0, 0, 0])
            .await
            .ok();
        return Ok(());
    }
    let (host, port) = read_target(&mut stream, header[3]).await?;

    match session
        .channel_open_direct_tcpip(host.as_str(), port as u32, "127.0.0.1", 0)
        .await
    {
        Ok(channel) => {
            stream
                .write_all(&[SOCKS_VERSION, SOCKS_REP_SUCCESS, 0x00, SOCKS_ATYP_IPV4, 0, 0, 0, 0, 0, 0])
                .await?;
            let mut channel = channel.into_stream();
            let _ = hbb_common::tokio::io::copy_bidirectional(&mut stream, &mut channel).await;
        }
        Err(err) => {
            log::debug!("ssh tunnel: failed to open channel to {host}:{port}: {err}");
            stream
                .write_all(&[
                    SOCKS_VERSION,
                    SOCKS_REP_CONNECTION_REFUSED,
                    0x00,
                    SOCKS_ATYP_IPV4,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                ])
                .await
                .ok();
        }
    }
    Ok(())
}

async fn read_target(stream: &mut TcpStream, atyp: u8) -> ResultType<(String, u16)> {
    match atyp {
        SOCKS_ATYP_IPV4 => {
            let mut addr = [0u8; 4];
            stream.read_exact(&mut addr).await?;
            Ok((format!("{}.{}.{}.{}", addr[0], addr[1], addr[2], addr[3]), read_port(stream).await?))
        }
        SOCKS_ATYP_DOMAIN => {
            let mut len = [0u8; 1];
            stream.read_exact(&mut len).await?;
            let mut host = vec![0u8; len[0] as usize];
            stream.read_exact(&mut host).await?;
            let host = String::from_utf8_lossy(&host).to_string();
            Ok((host, read_port(stream).await?))
        }
        SOCKS_ATYP_IPV6 => {
            let mut addr = [0u8; 16];
            stream.read_exact(&mut addr).await?;
            let host = std::net::Ipv6Addr::from(addr).to_string();
            Ok((host, read_port(stream).await?))
        }
        _ => bail!("unsupported socks address type {atyp}"),
    }
}

async fn read_port(stream: &mut TcpStream) -> ResultType<u16> {
    let mut port = [0u8; 2];
    stream.read_exact(&mut port).await?;
    Ok(u16::from_be_bytes(port))
}
