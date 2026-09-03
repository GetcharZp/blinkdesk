<p align="center">
  <img src="res/logo-header.svg" alt="BlinkDesk - LAN Remote Control"><br>
  <a href="#features">Features</a> •
  <a href="#how-to-use">Usage</a> •
  <a href="#roadmap">Roadmap</a> •
  <a href="#build-from-source">Build</a> •
  <a href="#screenshots">Screenshots</a><br>
  [<a href="docs/README-ZH.md">中文</a>] | [<a href="README.md">English</a>]
</p>

# BlinkDesk — LAN Remote Control

BlinkDesk is a **LAN-first remote control tool** forked from [RustDesk](https://github.com/rustdesk/rustdesk).

It is built to fill the gap where dedicated remote-control tools are missing inside a **local area network (LAN)**. Connect to any host in the same network using only:

- **IP address** — LAN IP, e.g. `192.168.1.100`
- **Port** — configurable, default `21118`
- **Username**
- **Password**

No rendezvous server, no relay server, no public network, no cloud account. Everything stays inside your LAN.

> [!CAUTION]
> **Misuse Disclaimer:** The developers do not condone or support any unethical or illegal use of this software. Misuse, such as unauthorized access, control or invasion of privacy, is strictly against our guidelines. Only use it on machines you own or are authorized to control.

## Features

- **LAN-first connection** — connect directly by IP + port + password.
- **Local settings** — configure the listening port (default `21118`) and a required password, and enable or disable remote control at any time under *Settings → Security → Direct IP Access*.
- **Low latency** — remote desktop control over the local network.
- **Mature foundation** — built on the RustDesk codebase: screen capture, input control, clipboard, file transfer, and more.
- **No server required** — peer-to-peer connection inside the LAN, nothing leaves the network.

### Roadmap

- [x] LAN direct connection (IP + port + password)
- [ ] SSH tunnel support
- [ ] SOCKS5 proxy support
- [ ] Connection history & favorites
- [ ] Cross-subnet / VLAN traversal

## Build from source

Prerequisites: Rust toolchain, C++ build environment, and [vcpkg](https://github.com/microsoft/vcpkg) with `VCPKG_ROOT` set.

> This project uses vcpkg **manifest mode**, so run `vcpkg install` **without** package names.

**Windows**

```sh
vcpkg install --triplet x64-windows-static
cargo run
```

**Linux / macOS**

```sh
vcpkg install
cargo run
```

## Screenshots

_Coming soon._

## License

GNU Affero General Public License v3.0 — see [LICENCE](LICENCE).

